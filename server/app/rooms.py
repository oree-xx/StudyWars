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
ROOM_CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _new_room_code() -> str:
    return "".join(random.choices(ROOM_CODE_CHARS, k=6))


def _points_for(is_correct: bool, elapsed: float, time_limit: float) -> int:
    if not is_correct:
        return 0
    fraction_remaining = max(0.0, min(1.0, 1 - elapsed / time_limit))
    return int(MIN_POINTS + (BASE_POINTS - MIN_POINTS) * fraction_remaining)


@dataclass
class Player:
    id: str
    name: str
    websocket: Optional[WebSocket] = None
    token: str = ""
    score: int = 0
    # question index -> (option_index, points_earned)
    answers: Dict[int, Tuple[int, int]] = field(default_factory=dict)

    def to_public(self) -> dict:
        return {
            "id": self.id, "name": self.name, "score": self.score,
            "connected": self.websocket is not None,
        }


@dataclass
class Room:
    code: str
    host_token: str
    questions: List[Question]
    host_ws: Optional[WebSocket] = None
    players: Dict[str, Player] = field(default_factory=dict)
    state: str = "lobby"
    current_index: int = -1
    question_started_at: float = 0.0
    _timer_task: Optional[asyncio.Task] = None
    # Serialize game transitions, joins and answer acceptance across sockets.
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def leaderboard(self) -> List[dict]:
        ranked = sorted(self.players.values(), key=lambda p: p.score, reverse=True)
        return [p.to_public() for p in ranked]

    def current_question(self) -> Optional[Question]:
        if 0 <= self.current_index < len(self.questions):
            return self.questions[self.current_index]
        return None

    def player_with_token(self, token: str) -> Optional[Player]:
        return next((p for p in self.players.values() if secrets.compare_digest(p.token, token)), None)

    def answered_count(self) -> int:
        return sum(self.current_index in player.answers for player in self.players.values())

    def question_payload(self) -> Optional[dict]:
        question = self.current_question()
        if question is None:
            return None
        server_time = time.time() * 1000
        remaining = max(0.0, TIME_LIMIT_SECONDS - (time.monotonic() - self.question_started_at))
        return {
            "type": "question", "index": self.current_index, "total": len(self.questions),
            "question": question.question, "options": question.options,
            "time_limit": TIME_LIMIT_SECONDS,
            "ends_at": server_time + remaining * 1000, "server_time": server_time,
        }

    def reveal_payload(self) -> Optional[dict]:
        question = self.current_question()
        if question is None or self.state != "reveal":
            return None
        return {
            "type": "reveal", "correct_index": question.correct_index,
            "explanation": question.explanation, "leaderboard": self.leaderboard(),
        }

    def snapshot(self, player: Optional[Player] = None) -> dict:
        answer = player.answers.get(self.current_index) if player else None
        snapshot = {
            "type": "room_state", "room_code": self.code, "state": self.state,
            "players": self.leaderboard(), "question": self.question_payload(),
            "selected_option": answer[0] if answer else None,
            "reveal": self.reveal_payload(), "leaderboard": self.leaderboard(),
            "answered_count": self.answered_count(), "total_players": len(self.players),
        }
        if player:
            snapshot["player_id"] = player.id
        return snapshot

    def _cancel_timer(self):
        task = self._timer_task
        self._timer_task = None
        if task and task is not asyncio.current_task():
            task.cancel()

    async def _send_player(self, player: Player, message: dict):
        socket = player.websocket
        if socket is None:
            return
        try:
            await socket.send_json(message)
        except Exception:
            if player.websocket is socket:
                player.websocket = None

    async def _send_host(self, message: dict):
        socket = self.host_ws
        if socket is None:
            return
        try:
            await socket.send_json(message)
        except Exception:
            if self.host_ws is socket:
                self.host_ws = None

    async def broadcast(self, message: dict):
        await asyncio.gather(
            *(self._send_player(player, message) for player in list(self.players.values())),
            self._send_host(message),
        )

    async def start_game(self, websocket: Optional[WebSocket] = None):
        async with self.lock:
            if websocket is not None and self.host_ws is not websocket:
                return
            if self.state == "lobby" and self.questions:
                await self._advance_question()

    async def advance_question(self, websocket: Optional[WebSocket] = None):
        async with self.lock:
            if websocket is not None and self.host_ws is not websocket:
                return
            if self.state == "reveal":
                await self._advance_question()

    async def _advance_question(self):
        self._cancel_timer()
        self.current_index += 1
        if self.current_question() is None:
            self.state = "ended"
            await self.broadcast({"type": "game_over", "leaderboard": self.leaderboard()})
            return
        self.state = "question"
        self.question_started_at = time.monotonic()
        self._timer_task = asyncio.create_task(self._question_timer(self.current_index))
        await self.broadcast(self.question_payload())

    async def _question_timer(self, question_index: int):
        try:
            remaining = max(0.0, TIME_LIMIT_SECONDS - (time.monotonic() - self.question_started_at))
            await asyncio.sleep(remaining)
            async with self.lock:
                if self.current_index == question_index:
                    await self._reveal_answer()
        except asyncio.CancelledError:
            pass

    async def submit_answer(self, player_id: str, option_index: int, question_index: int, websocket: Optional[WebSocket] = None):
        async with self.lock:
            player = self.players.get(player_id)
            if player is None:
                return
            if websocket is not None and player.websocket is not websocket:
                return

            async def reject(reason):
                await self._send_player(player, {
                    "type": "answer_rejected", "question_index": question_index, "reason": reason,
                })

            if type(question_index) is not int or question_index != self.current_index:
                await reject("That question is no longer active.")
                return
            if type(option_index) is not int or not 0 <= option_index < 4:
                await reject("Choose one of the four answers.")
                return
            # Retries return the accepted receipt without rescoring.
            previous = player.answers.get(question_index)
            if previous is not None:
                await self._send_player(player, {
                    "type": "answer_ack", "question_index": question_index,
                    "option_index": previous[0],
                })
                return
            if self.state != "question":
                await reject("Answers are closed for this question.")
                return
            elapsed = time.monotonic() - self.question_started_at
            if elapsed >= TIME_LIMIT_SECONDS:
                await reject("Time is up for this question.")
                await self._reveal_answer()
                return

            points = _points_for(option_index == self.current_question().correct_index, elapsed, TIME_LIMIT_SECONDS)
            player.answers[question_index] = (option_index, points)
            player.score += points
            await self._send_player(player, {
                "type": "answer_ack", "question_index": question_index, "option_index": option_index,
            })
            await self._send_host({
                "type": "player_answered", "answered_count": self.answered_count(),
                "total_players": len(self.players),
            })
            if self.players and self.answered_count() == len(self.players):
                await self._reveal_answer()

    async def reveal_answer(self, websocket: Optional[WebSocket] = None):
        async with self.lock:
            if websocket is not None and self.host_ws is not websocket:
                return
            await self._reveal_answer()

    async def _reveal_answer(self):
        if self.state != "question":
            return
        self._cancel_timer()
        self.state = "reveal"
        await self.broadcast(self.reveal_payload())


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
