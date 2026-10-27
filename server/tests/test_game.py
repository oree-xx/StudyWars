"""Run with: python -m unittest discover -s tests -v (from server/)."""
import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.models import Question
from app.rooms import Player, Room, TIME_LIMIT_SECONDS, room_manager
from app.routers.ws import host_socket, player_socket


QUESTION = Question(
    question="What is 2 + 2?", options=["3", "4", "5", "6"],
    correct_index=1, explanation="Two plus two is four.",
)


class Socket:
    def __init__(self):
        self.incoming = asyncio.Queue()
        self.outgoing = asyncio.Queue()
        self.events = []
        self.accepted = False
        self.close_code = None
        self.application_state = WebSocketState.CONNECTING

    async def accept(self):
        self.accepted = True
        self.application_state = WebSocketState.CONNECTED

    async def send_json(self, data):
        self.events.append(data)
        await self.outgoing.put(data)

    async def receive_json(self):
        item = await self.incoming.get()
        if isinstance(item, Exception):
            raise item
        return item

    async def close(self, code=1000, reason=""):
        self.close_code = code
        self.application_state = WebSocketState.DISCONNECTED
        await self.incoming.put(WebSocketDisconnect(code))

    async def event(self, event_type):
        async def find():
            while True:
                item = await self.outgoing.get()
                if item["type"] == event_type:
                    return item
        return await asyncio.wait_for(find(), 2)


class LocallyClosedSocket(Socket):
    """Reproduce Starlette's receive_json behavior following a local close."""
    def __init__(self):
        super().__init__()
        self.receive_after_close = False

    async def receive_json(self):
        if self.application_state != WebSocketState.CONNECTED:
            self.receive_after_close = True
            raise RuntimeError('WebSocket is not connected. Need to call "accept" first.')
        return await super().receive_json()

    async def close(self, code=1000, reason=""):
        self.close_code = code
        self.application_state = WebSocketState.DISCONNECTED
        # A frame may already be in flight when another connection closes us.
        await self.incoming.put({})


class RoomTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.host = Socket()
        self.a, self.b = Socket(), Socket()
        self.room = Room(code="ABCDEF", host_token="host-secret", questions=[QUESTION, QUESTION], host_ws=self.host)
        self.room.players = {
            "a": Player(id="a", name="Ada", websocket=self.a, token="a" * 48),
            "b": Player(id="b", name="Ben", websocket=self.b, token="b" * 48),
        }

    async def asyncTearDown(self):
        task = self.room._timer_task
        self.room._cancel_timer()
        if task:
            await asyncio.gather(task, return_exceptions=True)

    async def test_snapshot_restores_remaining_time_without_answers_leaking(self):
        await self.room.start_game()
        self.room.question_started_at -= 7
        snapshot = self.room.snapshot(self.room.players["a"])
        question = snapshot["question"]
        self.assertAlmostEqual((question["ends_at"] - question["server_time"]) / 1000, 13, delta=0.1)
        self.assertNotIn("correct_index", question)
        self.assertNotIn("explanation", question)
        self.assertIsNone(snapshot["reveal"])
        self.assertNotIn("token", snapshot["players"][0])

    async def test_answer_receipt_precedes_reveal_and_duplicate_does_not_rescore(self):
        await self.room.start_game()
        await self.room.submit_answer("a", 1, 0)
        score = self.room.players["a"].score
        await self.room.submit_answer("a", 2, 0)
        self.assertEqual(self.room.players["a"].score, score)
        self.assertEqual(self.a.events[-1]["option_index"], 1)
        await self.room.submit_answer("b", 0, 0)
        self.assertEqual(self.room.state, "reveal")
        self.assertEqual([e["type"] for e in self.b.events[-2:]], ["answer_ack", "reveal"])
        self.assertEqual(self.room.players["b"].score, 0)
        snapshot = self.room.snapshot(self.room.players["a"])
        self.assertEqual(snapshot["selected_option"], 1)
        self.assertEqual(snapshot["reveal"]["correct_index"], 1)

    async def test_rejects_stale_question_and_invalid_options(self):
        await self.room.start_game()
        for option, index in [(1, 9), (-1, 0), (4, 0), (True, 0), (1, True)]:
            await self.room.submit_answer("a", option, index)
            self.assertEqual(self.a.events[-1]["type"], "answer_rejected")
        self.assertEqual(self.room.players["a"].answers, {})

    async def test_deadline_is_enforced_even_before_timer_runs(self):
        await self.room.start_game()
        self.room.question_started_at -= TIME_LIMIT_SECONDS + 1
        await self.room.submit_answer("a", 1, 0)
        self.assertEqual(self.room.players["a"].score, 0)
        self.assertEqual(self.room.players["a"].answers, {})
        self.assertEqual(self.room.state, "reveal")
        self.assertEqual(self.a.events[-2]["type"], "answer_rejected")

    async def test_automatic_timer_reveals(self):
        with patch("app.rooms.TIME_LIMIT_SECONDS", 0.01):
            await self.room.start_game()
            await asyncio.wait_for(self.room._timer_task, 1)
        self.assertEqual(self.room.state, "reveal")

    async def test_stale_host_and_player_connections_cannot_mutate_game(self):
        await self.room.start_game(Socket())
        self.assertEqual(self.room.state, "lobby")
        await self.room.start_game(self.host)
        await self.room.submit_answer("a", 1, 0, Socket())
        self.assertEqual(self.room.players["a"].answers, {})
        await self.room.reveal_answer(Socket())
        self.assertEqual(self.room.state, "question")

    async def test_failed_broadcast_preserves_player_score_and_identity(self):
        self.room.players["a"].score = 123
        self.a.send_json = AsyncMock(side_effect=RuntimeError("socket dropped"))
        await self.room.broadcast({"type": "test"})
        self.assertIsNone(self.room.players["a"].websocket)
        self.assertEqual(self.room.players["a"].score, 123)
        self.assertIs(self.room.player_with_token("a" * 48), self.room.players["a"])

    async def test_finished_snapshot_contains_final_leaderboard(self):
        await self.room.start_game()
        await self.room.reveal_answer()
        await self.room.advance_question()
        await self.room.reveal_answer()
        await self.room.advance_question()
        self.assertEqual(self.room.state, "ended")
        self.assertIsNone(self.room.snapshot()["question"])
        self.assertEqual(len(self.room.snapshot()["leaderboard"]), 2)


class SocketTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.room = room_manager.create_room([QUESTION, QUESTION])
        self.tasks = []

    async def asyncTearDown(self):
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        timer = self.room._timer_task
        self.room._cancel_timer()
        if timer:
            await asyncio.gather(timer, return_exceptions=True)
        room_manager.rooms.pop(self.room.code, None)

    async def connect_player(self, token="a" * 48, name="Ada"):
        socket = Socket()
        task = asyncio.create_task(player_socket(socket, self.room.code, name, token))
        self.tasks.append(task)
        snapshot = await socket.event("room_state")
        return socket, task, snapshot

    async def test_player_resumes_same_identity_answer_and_score_midgame(self):
        socket, task, first = await self.connect_player()
        await self.room.start_game()
        await socket.incoming.put({"type": "answer", "question_index": 0, "option_index": 1})
        await socket.event("answer_ack")
        await socket.close()
        await task
        player = self.room.players[first["player_id"]]
        score = player.score
        self.assertIsNone(player.websocket)
        resumed, _, snapshot = await self.connect_player()
        self.assertEqual(snapshot["player_id"], first["player_id"])
        self.assertEqual(snapshot["state"], "reveal")
        self.assertEqual(snapshot["selected_option"], 1)
        self.assertEqual(player.score, score)
        self.assertIs(player.websocket, resumed)
        self.assertEqual(len(self.room.players), 1)

    async def test_replacing_player_connection_does_not_lose_new_socket(self):
        old, old_task, first = await self.connect_player()
        new, _, snapshot = await self.connect_player()
        await old_task
        self.assertEqual(old.close_code, 4002)
        self.assertEqual(first["player_id"], snapshot["player_id"])
        self.assertIs(self.room.players[first["player_id"]].websocket, new)
        await new.incoming.put({"type": "ping"})
        self.assertEqual((await new.event("pong"))["type"], "pong")

    async def test_new_player_cannot_join_started_game_or_impersonate_by_name(self):
        await self.connect_player()
        await self.room.start_game()
        stranger = Socket()
        await player_socket(stranger, self.room.code, "Ada", "b" * 48)
        self.assertTrue(stranger.accepted)
        self.assertEqual(stranger.close_code, 4003)
        self.assertEqual(len(self.room.players), 1)

    async def test_invalid_room_and_credentials_have_terminal_close_codes(self):
        cases = [
            (player_socket, ("MISSING", "Ada", "a" * 48), 4004),
            (player_socket, (self.room.code, "Ada", "short"), 4001),
            (host_socket, (self.room.code, "wrong"), 4001),
        ]
        for handler, arguments, expected in cases:
            socket = Socket()
            await handler(socket, *arguments)
            self.assertTrue(socket.accepted)
            self.assertEqual(socket.close_code, expected)

    async def test_host_reconnect_restores_question_and_old_cleanup_is_safe(self):
        old, new = Socket(), Socket()
        old_task = asyncio.create_task(host_socket(old, self.room.code, self.room.host_token))
        self.tasks.append(old_task)
        await old.event("room_state")
        await self.room.start_game()
        new_task = asyncio.create_task(host_socket(new, self.room.code, self.room.host_token))
        self.tasks.append(new_task)
        state = await new.event("room_state")
        await old_task
        self.assertEqual(state["state"], "question")
        self.assertEqual(state["question"]["index"], 0)
        self.assertIs(self.room.host_ws, new)
        await new.incoming.put({"type": "ping"})
        await new.event("pong")

    async def test_replaced_host_exits_cleanly_after_local_close_runtime_error(self):
        old, new = LocallyClosedSocket(), Socket()
        old_task = asyncio.create_task(host_socket(old, self.room.code, self.room.host_token))
        self.tasks.append(old_task)
        await old.event("room_state")
        new_task = asyncio.create_task(host_socket(new, self.room.code, self.room.host_token))
        self.tasks.append(new_task)
        await new.event("room_state")
        await asyncio.wait_for(old_task, 2)
        self.assertTrue(old.receive_after_close)
        self.assertEqual(old.close_code, 4002)
        self.assertIs(self.room.host_ws, new)
        await new.incoming.put({"type": "ping"})
        await new.event("pong")

    async def test_replaced_player_exits_cleanly_after_local_close_runtime_error(self):
        old = LocallyClosedSocket()
        old_task = asyncio.create_task(player_socket(old, self.room.code, "Ada", "a" * 48))
        self.tasks.append(old_task)
        first = await old.event("room_state")
        new, _, snapshot = await self.connect_player()
        await asyncio.wait_for(old_task, 2)
        self.assertTrue(old.receive_after_close)
        self.assertEqual(old.close_code, 4002)
        self.assertEqual(first["player_id"], snapshot["player_id"])
        self.assertIs(self.room.players[first["player_id"]].websocket, new)
        await new.incoming.put({"type": "ping"})
        await new.event("pong")

    async def test_unrelated_runtime_errors_on_active_sockets_are_not_hidden(self):
        for role in ("host", "player"):
            with self.subTest(role=role):
                socket = Socket()
                handler = (host_socket(socket, self.room.code, self.room.host_token)
                           if role == "host" else player_socket(socket, self.room.code, "Ada", "a" * 48))
                task = asyncio.create_task(handler)
                self.tasks.append(task)
                await socket.event("room_state")
                await socket.incoming.put(RuntimeError("unexpected application failure"))
                with self.assertRaisesRegex(RuntimeError, "unexpected application failure"):
                    await asyncio.wait_for(task, 2)


if __name__ == "__main__":
    unittest.main()
