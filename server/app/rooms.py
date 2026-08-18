import asyncio
import random
import secrets
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from fastapi import WebSocket

from app.models import Question

TIME_LIMIT_SECONDS = 20
BASE_POINTS = 1000
MIN_POINTS = 100

# Avoids visually ambiguous characters (0/O, 1/I) so codes are easy to read aloud/type.
ROOM_CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _new_room_code() -> str:
    return "".join(random.choices(ROOM_CODE_CHARS, k=6))


def _points_for(is_correct: bool, elapsed: float, time_limit: float) -> int:
    if not is_correct:
        return 0
    fraction_remaining = max(0.0, 1 - (elapsed / time_limit))
    return int(MIN_POINTS + (BASE_POINTS - MIN_POINTS) * fraction_remaining)


@dataclass
class Player:
    id: str
    name: str
    websocket: WebSocket
    score: int = 0
    # question index -> (option_index, points_earned)
    answers: Dict[int, Tuple[int, int]] = field(default_factory=dict)

    def to_public(self) -> dict:
        return {"id": self.id, "name": self.name, "score": self.score}


@dataclass
class Room:
    code: str
    host_token: str
    questions: List[Question]
    host_ws: Optional[WebSocket] = None
    players: Dict[str, Player] = field(default_factory=dict)
    state: str = "lobby"  # lobby | question | reveal | ended
    current_index: int = -1
    question_started_at: float = 0.0
    _timer_task: Optional[asyncio.Task] = None

    def leaderboard(self) -> List[dict]:
        ranked = sorted(self.players.values(), key=lambda p: p.score, reverse=True)
        return [p.to_public() for p in ranked]

    def current_question(self) -> Optional[Question]:
        if 0 <= self.current_index < len(self.questions):
            return self.questions[self.current_index]
        return None

    def _cancel_timer(self):
        """Cancel the pending question timer, guarding against self-cancellation
        when this is called from inside the timer's own coroutine."""
        task = self._timer_task
        self._timer_task = None
        if task and task is not asyncio.current_task():
            task.cancel()

    async def broadcast(self, message: dict):
        dead_player_ids = []
        for player in list(self.players.values()):
            try:
                await player.websocket.send_json(message)
            except Exception:
                dead_player_ids.append(player.id)
        for pid in dead_player_ids:
            self.players.pop(pid, None)

        if self.host_ws is not None:
            try:
                await self.host_ws.send_json(message)
            except Exception:
                self.host_ws = None

    async def start_game(self):
        if self.state != "lobby" or not self.questions:
            return
        await self.advance_question()

    async def advance_question(self):
        self._cancel_timer()
        self.current_index += 1

        question = self.current_question()
        if question is None:
            self.state = "ended"
            await self.broadcast({"type": "game_over", "leaderboard": self.leaderboard()})
            return

        self.state = "question"
        self.question_started_at = time.monotonic()
        await self.broadcast(
            {
                "type": "question",
                "index": self.current_index,
                "total": len(self.questions),
                "question": question.question,
                "options": question.options,
                "time_limit": TIME_LIMIT_SECONDS,
            }
        )
        self._timer_task = asyncio.create_task(self._question_timer())

    async def _question_timer(self):
        try:
            await asyncio.sleep(TIME_LIMIT_SECONDS)
            await self.reveal_answer()
        except asyncio.CancelledError:
            pass

    async def submit_answer(self, player_id: str, option_index: int):
        if self.state != "question":
            return
        player = self.players.get(player_id)
        if player is None or self.current_index in player.answers:
            return

        elapsed = min(time.monotonic() - self.question_started_at, TIME_LIMIT_SECONDS)
        question = self.current_question()
        is_correct = option_index == question.correct_index
        points = _points_for(is_correct, elapsed, TIME_LIMIT_SECONDS)

        player.answers[self.current_index] = (option_index, points)
        player.score += points

        if self.host_ws is not None:
            answered_count = sum(1 for p in self.players.values() if self.current_index in p.answers)
            try:
                await self.host_ws.send_json(
                    {
                        "type": "player_answered",
                        "answered_count": answered_count,
                        "total_players": len(self.players),
                    }
                )
            except Exception:
                self.host_ws = None

        if self.players and all(self.current_index in p.answers for p in self.players.values()):
            await self.reveal_answer()

    async def reveal_answer(self):
        if self.state != "question":
            return
        self._cancel_timer()
        self.state = "reveal"
        question = self.current_question()
        await self.broadcast(
            {
                "type": "reveal",
                "correct_index": question.correct_index,
                "explanation": question.explanation,
                "leaderboard": self.leaderboard(),
            }
        )


class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, Room] = {}

    def create_room(self, questions: List[Question]) -> Room:
        code = _new_room_code()
        while code in self.rooms:
            code = _new_room_code()
        room = Room(code=code, host_token=secrets.token_urlsafe(16), questions=questions)
        self.rooms[code] = room
        return room

    def get(self, code: str) -> Optional[Room]:
        return self.rooms.get(code.upper())


room_manager = RoomManager()
