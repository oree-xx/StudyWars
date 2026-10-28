"""Exercise socket recovery, timer delivery, fencing, and receipt ordering."""
import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.models import Question
from app.persistence import MemoryRoomStore, StorageUnavailable
from app.rooms import RoomManager
from app.routers.ws import serve_socket

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
        self.close_reason = ""
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
        self.close_reason = reason
        self.application_state = WebSocketState.DISCONNECTED
        await self.incoming.put(WebSocketDisconnect(code))

    async def event(self, event_type):
        async def find():
            while True:
                item = await self.outgoing.get()
                if item["type"] == event_type:
                    return item
        return await asyncio.wait_for(find(), 2)


class SocketTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.store = MemoryRoomStore()
        self.manager = RoomManager(self.store)
        self.created = await self.manager.create_room([QUESTION, QUESTION])
        self.code = self.created["room_code"]
        self.tasks = []
        self.host = None

    async def asyncTearDown(self):
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)

    async def connect(self, role="player", token="a" * 48, name="Ada", manager=None, socket=None):
        socket = socket or Socket()
        if role == "host":
            token = self.created["host_token"]
        task = asyncio.create_task(serve_socket(
            socket, self.code, role, token, name, manager or self.manager,
        ))
        self.tasks.append(task)
        state = await socket.event("room_state")
        return socket, task, state

    async def start(self):
        if self.host is None:
            self.host, _, _ = await self.connect("host")
        await self.host.incoming.put({"type": "start_game"})
        return await self.host.event("question")

    async def test_player_resumes_identity_answer_and_score_on_another_manager(self):
        socket, task, first = await self.connect()
        await self.start()
        await socket.incoming.put({"type": "answer", "question_index": 0, "option_index": 1})
        await socket.event("answer_ack")
        await socket.event("reveal")
        await socket.close()
        await task
        document = await self.store.get(self.code)
        score = document["players"][first["player_id"]]["score"]
        self.assertGreater(score, 0)
        self.assertIsNone(document["players"][first["player_id"]]["connection"]["id"])
        resumed, _, state = await self.connect(manager=RoomManager(self.store))
        self.assertEqual(state["player_id"], first["player_id"])
        self.assertEqual(state["state"], "reveal")
        self.assertEqual(state["selected_option"], 1)
        self.assertEqual(state["leaderboard"][0]["score"], score)
        await resumed.incoming.put({"type": "ping"})
        await resumed.event("pong")
        self.assertEqual(len((await self.store.get(self.code))["players"]), 1)

    async def test_replacing_player_closes_old_socket_and_cleanup_preserves_new(self):
        old, old_task, first = await self.connect()
        new, _, state = await self.connect(manager=RoomManager(self.store))
        await asyncio.wait_for(old_task, 2)
        self.assertEqual(old.close_code, 4002)
        self.assertEqual(first["player_id"], state["player_id"])
        document = await self.store.get(self.code)
        self.assertIsNotNone(document["players"][first["player_id"]]["connection"]["id"])
        await new.incoming.put({"type": "ping"})
        await new.event("pong")

    async def test_new_player_cannot_join_started_game_or_impersonate_by_name(self):
        await self.connect()
        await self.start()
        stranger = Socket()
        await serve_socket(stranger, self.code, "player", "b" * 48, "Ada", self.manager)
        self.assertEqual(stranger.close_code, 4003)
        self.assertEqual(len((await self.store.get(self.code))["players"]), 1)

    async def test_invalid_room_and_credentials_have_terminal_close_codes(self):
        cases = [
            ("MISSING", "player", "a" * 48, 4004),
            (self.code, "player", "short", 4001),
            (self.code, "host", "wrong", 4001),
        ]
        for code, role, token, expected in cases:
            socket = Socket()
            await serve_socket(socket, code, role, token, manager=self.manager)
            self.assertTrue(socket.accepted)
            self.assertEqual(socket.close_code, expected)

    async def test_host_reconnect_restores_absolute_deadline_and_fences_old_host(self):
        self.host, old_task, _ = await self.connect("host")
        question = await self.start()
        new, _, state = await self.connect("host", manager=RoomManager(self.store))
        await asyncio.wait_for(old_task, 2)
        self.assertEqual(self.host.close_code, 4002)
        self.assertEqual(state["state"], "question")
        self.assertEqual(state["question"]["ends_at"], question["ends_at"])
        self.assertGreater(question["ends_at"], 1_000_000_000_000)
        await new.incoming.put({"type": "ping"})
        await new.event("pong")

    async def test_answer_receipt_precedes_reveal_and_duplicate_never_rescores(self):
        player, _, first = await self.connect()
        await self.start()
        await player.event("question")
        await player.incoming.put({"type": "answer", "question_index": 0, "option_index": 1})
        await player.event("reveal")
        types = [event["type"] for event in player.events]
        self.assertLess(types.index("answer_ack"), types.index("reveal"))
        before = (await self.store.get(self.code))["players"][first["player_id"]]["score"]
        await player.incoming.put({"type": "answer", "question_index": 0, "option_index": 2})
        self.assertEqual((await player.event("answer_ack"))["option_index"], 1)
        self.assertEqual((await self.store.get(self.code))["players"][first["player_id"]]["score"], before)

    async def test_invalid_answers_rejected_without_scoring(self):
        player, _, first = await self.connect()
        await self.start()
        for option, index in [(1, 9), (-1, 0), (4, 0), (True, 0), (1, True)]:
            await player.incoming.put({"type": "answer", "option_index": option, "question_index": index})
            await player.event("answer_rejected")
        document = await self.store.get(self.code)
        self.assertEqual(document["players"][first["player_id"]]["answers"], {})

    async def test_automatic_timer_delivers_reveal_without_client_polling(self):
        def shorter(room):
            room["time_limit"] = 0.04
            return None, False
        await self.store.mutate(self.code, shorter)
        player, _, _ = await self.connect()
        await self.start()
        reveal = await player.event("reveal")
        self.assertEqual(reveal["correct_index"], 1)
        self.assertEqual((await self.store.get(self.code))["state"], "reveal")

    async def test_other_players_answers_and_live_correctness_never_leak(self):
        player, _, first = await self.connect()
        other, _, _ = await self.connect(token="b" * 48, name="Ben")
        await self.start()
        await player.incoming.put({"type": "answer", "question_index": 0, "option_index": 1})
        await player.event("answer_ack")
        # Read until the remote authoritative snapshot includes the answer count.
        while True:
            state = await other.event("room_state")
            if state["answered_count"] == 1:
                break
        self.assertIsNone(state["selected_option"])
        self.assertIsNone(state["reveal"])
        self.assertNotIn("correct_index", state["question"])
        self.assertNotIn("explanation", state["question"])
        self.assertEqual(next(p for p in state["players"] if p["id"] == first["player_id"])["score"], 0)
        for player in state["players"]:
            self.assertEqual(set(player), {"id", "name", "score", "connected"})

    async def test_storage_outage_closes_retryably_without_exposing_details(self):
        player, task, _ = await self.connect()
        await self.start()
        with patch.object(self.store, "mutate", new=AsyncMock(side_effect=StorageUnavailable("redis://secret@private"))):
            await player.incoming.put({"type": "answer", "question_index": 0, "option_index": 1})
            await asyncio.wait_for(task, 2)
        self.assertEqual(player.close_code, 1013)
        self.assertNotIn("secret", player.close_reason)

    async def test_failed_socket_delivery_keeps_durable_player_identity(self):
        player, task, first = await self.connect()
        player.send_json = AsyncMock(side_effect=RuntimeError("socket dropped"))
        await player.incoming.put({"type": "ping"})
        with self.assertRaisesRegex(RuntimeError, "socket dropped"):
            await asyncio.wait_for(task, 2)
        _, _, resumed = await self.connect()
        self.assertEqual(resumed["player_id"], first["player_id"])

    async def test_unrelated_runtime_errors_are_not_hidden(self):
        for role in ("host", "player"):
            socket, task, _ = await self.connect(role)
            await socket.incoming.put(RuntimeError("unexpected application failure"))
            with self.assertRaisesRegex(RuntimeError, "unexpected application failure"):
                await asyncio.wait_for(task, 2)

    async def test_fast_pings_do_not_write_room_storage(self):
        socket, _, _ = await self.connect()
        # Let the initial join notification drain before counting mutations.
        await asyncio.sleep(0)
        with patch.object(self.manager, "command", wraps=self.manager.command) as command:
            for _ in range(3):
                await socket.incoming.put({"type": "ping"})
                await socket.event("pong")
            command.assert_not_called()


if __name__ == "__main__":
    unittest.main()
