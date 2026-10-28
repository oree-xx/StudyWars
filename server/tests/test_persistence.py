"""Durability and concurrency contract; TEST_REDIS_URL enables local Redis integration."""
import asyncio
import json
import os
import unittest
import uuid
from unittest.mock import AsyncMock, patch

from redis.exceptions import ConnectionError as RedisConnectionError

from app.config import Settings, settings
from app.models import Question
from app.persistence import MemoryRoomStore, RedisRoomStore, RoomMissing, StorageUnavailable
from app.rooms import RoomManager, SessionError, snapshot, storage_namespace, token_hash


QUESTION = Question(
    question="What is 2 + 2?", options=["3", "4", "5", "6"],
    correct_index=1, explanation="Two plus two is four.",
)
PLAYER_TOKEN = "a" * 48


class PersistenceContract:
    """Run the same externally observable guarantees against both stores."""

    async def make_room(self):
        room = await self.first.create_room([QUESTION, QUESTION, QUESTION])
        self.code = room["room_code"]
        self.codes.add(self.code)
        self.host_token = room["host_token"]
        await self.first.connect(self.code, "host", self.host_token, "host-first")
        _, self.player_id = await self.second.connect(
            self.code, "player", PLAYER_TOKEN, "player-first", "Ada",
        )

    async def host_command(self, kind, manager=None, connection="host-first"):
        message = {"type": kind}
        if kind in {"reveal_now", "next_question"}:
            message["question_index"] = (await self.first.store.get(self.code))["current_index"]
        return await (manager or self.first).command(
            self.code, "host", None, connection, message,
        )

    async def answer(self, option=1, manager=None, connection="player-first", index=0):
        return await (manager or self.second).command(
            self.code, "player", self.player_id, connection,
            {"type": "answer", "question_index": index, "option_index": option},
        )

    async def test_independent_managers_restore_identity_answers_and_scores(self):
        await self.make_room()
        await self.host_command("start_game")
        room, receipt = await self.answer()
        score = room["players"][self.player_id]["score"]
        self.assertEqual(receipt["type"], "answer_ack")
        await self.second.disconnect(self.code, "player", self.player_id, "player-first")
        replacement = RoomManager(self.first.store)
        restored, player_id = await replacement.connect(
            self.code, "player", PLAYER_TOKEN, "player-resumed", "Changed name",
        )
        self.assertEqual(player_id, self.player_id)
        self.assertEqual(len(restored["players"]), 1)
        self.assertEqual(restored["players"][player_id]["name"], "Ada")
        view = snapshot(restored, player_id)
        self.assertEqual(view["selected_option"], 1)
        self.assertEqual(view["state"], "reveal")
        self.assertEqual(view["leaderboard"][0]["score"], score)

    async def test_tokens_are_hashed_at_rest_and_absent_from_public_state(self):
        await self.make_room()
        room = await self.second.store.get(self.code)
        serialized = json.dumps(room)
        self.assertNotIn(self.host_token, serialized)
        self.assertNotIn(PLAYER_TOKEN, serialized)
        self.assertEqual(room["host_token_hash"], token_hash(self.host_token))
        self.assertEqual(room["players"][self.player_id]["token_hash"], token_hash(PLAYER_TOKEN))
        public = json.dumps(snapshot(room, self.player_id))
        self.assertNotIn("token", public)
        self.assertNotIn("connection", public)
        with self.assertRaises(SessionError) as error:
            await self.second.connect(self.code, "host", "wrong-host-token", "intruder")
        self.assertEqual(error.exception.code, 4001)
        await self.host_command("start_game")
        with self.assertRaises(SessionError) as error:
            await self.second.connect(self.code, "player", "b" * 48, "intruder", "Ada")
        self.assertEqual(error.exception.code, 4003)
        self.assertEqual(len((await self.first.store.get(self.code))["players"]), 1)

    async def test_simultaneous_duplicate_answers_award_points_once(self):
        await self.make_room()
        await self.host_command("start_game")
        results = await asyncio.gather(*[
            self.answer(manager=self.first if index % 2 else self.second)
            for index in range(8)
        ])
        room = await self.first.store.get(self.code)
        player = room["players"][self.player_id]
        self.assertEqual(len(player["answers"]), 1)
        self.assertGreater(player["score"], 0)
        self.assertLessEqual(player["score"], 1000)
        self.assertEqual(player["score"], player["answers"]["0"][1])
        self.assertTrue(all(receipt["option_index"] == 1 for _, receipt in results))
        _, receipt = await self.answer(option=2)
        self.assertEqual(receipt["option_index"], 1)
        self.assertEqual((await self.second.store.get(self.code))["players"][self.player_id]["score"], player["score"])

    async def test_duplicate_host_transitions_and_old_timer_do_not_skip_questions(self):
        await self.make_room()
        await asyncio.gather(self.host_command("start_game"), self.host_command("start_game", self.second))
        room = await self.first.store.get(self.code)
        self.assertEqual((room["state"], room["current_index"]), ("question", 0))
        await asyncio.gather(self.host_command("reveal_now"), self.host_command("reveal_now", self.second))
        await asyncio.gather(self.host_command("next_question"), self.host_command("next_question", self.second))
        room = await self.second.store.get(self.code)
        self.assertEqual((room["state"], room["current_index"]), ("question", 1))
        with patch("app.rooms.time.time", return_value=room["question_ends_at"] + 1):
            unchanged = await self.first.expire(self.code, 0)
        self.assertEqual((unchanged["state"], unchanged["current_index"]), ("question", 1))

    async def test_delayed_host_controls_cannot_change_a_later_question(self):
        await self.make_room()
        await self.host_command("start_game")
        await self.host_command("reveal_now")
        await self.host_command("next_question")
        for kind in ("reveal_now", "next_question"):
            for index in (0, None, True):
                room, _ = await self.second.command(
                    self.code, "host", None, "host-first",
                    {"type": kind, "question_index": index},
                )
                self.assertEqual((room["state"], room["current_index"]), ("question", 1))
        await self.host_command("reveal_now")
        room, _ = await self.second.command(
            self.code, "host", None, "host-first",
            {"type": "next_question", "question_index": 0},
        )
        self.assertEqual((room["state"], room["current_index"]), ("reveal", 1))

    async def test_replaced_connections_cannot_mutate_or_detach_new_sessions(self):
        await self.make_room()
        await self.second.connect(self.code, "host", self.host_token, "host-new")
        await self.first.connect(self.code, "player", PLAYER_TOKEN, "player-new", "Ada")
        with self.assertRaises(SessionError) as error:
            await self.host_command("start_game")
        self.assertEqual(error.exception.code, 4002)
        await self.first.disconnect(self.code, "host", None, "host-first")
        await self.second.disconnect(self.code, "player", self.player_id, "player-first")
        room = await self.first.store.get(self.code)
        self.assertEqual(room["host_connection"]["id"], "host-new")
        self.assertEqual(room["players"][self.player_id]["connection"]["id"], "player-new")
        await self.host_command("start_game", connection="host-new")
        with self.assertRaises(SessionError) as error:
            await self.answer(connection="player-first")
        self.assertEqual(error.exception.code, 4002)
        _, receipt = await self.answer(connection="player-new")
        self.assertEqual(receipt["type"], "answer_ack")

    async def test_live_snapshots_hide_correct_answers_and_current_question_points(self):
        await self.make_room()
        await self.first.connect(self.code, "player", "b" * 48, "other-player", "Ben")
        await self.host_command("start_game")
        room, _ = await self.answer()
        self.assertEqual(room["state"], "question")
        public = snapshot(room, self.player_id)
        self.assertIsNone(public["reveal"])
        self.assertNotIn("correct_index", public["question"])
        self.assertNotIn("explanation", public["question"])
        self.assertEqual(public["selected_option"], 1)
        self.assertTrue(all(player["score"] == 0 for player in public["players"]))
        revealed, _ = await self.host_command("reveal_now")
        self.assertGreater(snapshot(revealed)["leaderboard"][0]["score"], 0)


class MemoryPersistenceTests(PersistenceContract, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.store = MemoryRoomStore()
        self.first = RoomManager(self.store)
        self.second = RoomManager(self.store)
        self.codes = set()

    async def test_utc_deadline_survives_manager_replacement_and_rejects_late_answer(self):
        with patch("app.rooms.time.time", return_value=1_800_000_000):
            await self.make_room()
            await self.host_command("start_game")
            self.assertEqual((await self.store.get(self.code))["question_ends_at"], 1_800_000_020)
        with patch("app.rooms.time.time", return_value=1_800_000_007):
            replacement = RoomManager(self.store)
            room, _ = await replacement.connect(self.code, "player", PLAYER_TOKEN, "resumed")
            view = snapshot(room, self.player_id)
            self.assertEqual(view["question"]["ends_at"] - view["question"]["server_time"], 13_000)
        with patch("app.rooms.time.time", return_value=1_800_000_021):
            room, receipt = await self.answer(manager=replacement, connection="resumed")
            self.assertEqual(room["state"], "reveal")
            self.assertEqual(receipt["type"], "answer_rejected")
            self.assertEqual(room["players"][self.player_id]["score"], 0)

    async def test_rooms_expire_after_24_hours_of_inactivity_and_reads_do_not_extend_ttl(self):
        self.assertEqual(Settings.model_fields["room_ttl_seconds"].default, 86400)
        with patch("app.persistence.time.time", return_value=1_800_000_000):
            await self.make_room()
        with patch("app.persistence.time.time", return_value=1_800_086_399):
            self.assertEqual((await self.store.get(self.code))["state"], "lobby")
        with patch("app.persistence.time.time", return_value=1_800_086_400):
            with self.assertRaises(RoomMissing):
                await self.store.get(self.code)

    async def test_authenticated_activity_renews_inactivity_ttl(self):
        with patch("app.persistence.time.time", return_value=1_800_000_000):
            await self.make_room()
        with patch("app.persistence.time.time", return_value=1_800_000_030):
            await self.host_command("ping")
        self.assertEqual(self.store.expires[self.code], 1_800_086_430)
        with patch("app.persistence.time.time", return_value=1_800_086_400):
            self.assertEqual((await self.store.get(self.code))["state"], "lobby")
        with patch("app.persistence.time.time", return_value=1_800_086_430):
            with self.assertRaises(RoomMissing):
                await self.store.get(self.code)

    async def test_expired_connection_lease_requires_authenticated_reconnect(self):
        with patch("app.rooms.time.time", return_value=1_800_000_000):
            await self.make_room()
        with patch("app.rooms.time.time", return_value=1_800_000_091):
            with self.assertRaises(SessionError) as error:
                await self.host_command("start_game")
            self.assertEqual(error.exception.code, 1013)
            await self.first.connect(self.code, "host", self.host_token, "host-resumed")
            room, _ = await self.host_command("start_game", connection="host-resumed")
            self.assertEqual(room["state"], "question")

    async def test_documents_are_isolated_and_failed_mutations_are_not_committed(self):
        await self.make_room()
        original = await self.store.get(self.code)
        detached = await self.store.get(self.code)
        detached["players"].clear()
        self.assertEqual(await self.store.get(self.code), original)

        def failure(document):
            document["players"].clear()
            raise ValueError("Abort transition")

        with self.assertRaises(ValueError):
            await self.store.mutate(self.code, failure)
        self.assertEqual(await self.store.get(self.code), original)


class StorageConfigurationTests(unittest.IsolatedAsyncioTestCase):
    async def test_vercel_requires_tls_redis_and_never_falls_back_to_memory(self):
        for mode, url in [("auto", ""), ("memory", "rediss://localhost:6379"), ("redis", "redis://localhost:6379")]:
            with self.subTest(mode=mode, url=url), patch.dict(os.environ, {"VERCEL": "1"}, clear=True), patch.multiple(
                settings, room_storage=mode, redis_url=url,
            ):
                with self.assertRaisesRegex(StorageUnavailable, "TLS REDIS_URL"):
                    _ = RoomManager().store

    async def test_bad_modes_urls_and_namespaces_are_safe_configuration_errors(self):
        cases = [("disk", "", "studywars"), ("redis", "", "studywars"),
                 ("redis", "https://user:secret@redis.example", "studywars"),
                 ("redis", "redis://localhost:6379", "unsafe:*namespace")]
        for mode, url, prefix in cases:
            with self.subTest(mode=mode, prefix=prefix), patch.dict(os.environ, {}, clear=True), patch.multiple(
                settings, room_storage=mode, redis_url=url, redis_key_prefix=prefix,
            ):
                with self.assertRaises(StorageUnavailable) as error:
                    _ = RoomManager().store
                self.assertNotIn("secret", str(error.exception))

    async def test_preview_branches_and_production_have_separate_namespaces(self):
        with patch.object(settings, "redis_key_prefix", "studywars"), patch.dict(os.environ, {}, clear=True):
            with patch.dict(os.environ, {"VERCEL_ENV": "production"}):
                production = storage_namespace()
            with patch.dict(os.environ, {"VERCEL_ENV": "preview", "VERCEL_GIT_COMMIT_REF": "feature/one"}):
                first = storage_namespace()
                self.assertEqual(first, storage_namespace())
            with patch.dict(os.environ, {"VERCEL_ENV": "preview", "VERCEL_GIT_COMMIT_REF": "feature/two"}):
                second = storage_namespace()
        self.assertEqual(production, "studywars:production")
        self.assertEqual(len({production, first, second}), 3)
        self.assertNotIn("feature/", first)

    async def test_redis_errors_are_sanitized_and_unreadable_documents_fail_closed(self):
        client = AsyncMock()
        client.get.side_effect = RedisConnectionError("redis://user:super-secret@hostname")
        store = RedisRoomStore("redis://localhost", "owned-test", client=client)
        with self.assertRaises(StorageUnavailable) as error:
            await store.get("ABCDEF")
        self.assertNotIn("super-secret", str(error.exception))
        client.get.side_effect = None
        for raw in ("broken-json", "[]", '{"version":999}'):
            client.get.return_value = raw
            with self.assertRaises(StorageUnavailable):
                await store.get("ABCDEF")
        client.get.return_value = None
        with self.assertRaises(RoomMissing):
            await store.get("ABCDEF")


@unittest.skipUnless(os.getenv("TEST_REDIS_URL"), "Set TEST_REDIS_URL for local Redis integration")
class RedisPersistenceTests(PersistenceContract, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.prefix = "studywars-test-" + uuid.uuid4().hex
        self.first_store = RedisRoomStore(os.environ["TEST_REDIS_URL"], self.prefix)
        self.second_store = RedisRoomStore(os.environ["TEST_REDIS_URL"], self.prefix)
        self.first = RoomManager(self.first_store)
        self.second = RoomManager(self.second_store)
        self.codes = set()
        self.addAsyncCleanup(self.first_store.close)
        self.addAsyncCleanup(self.second_store.close)
        self.addAsyncCleanup(self.clean_owned_keys)
        self.assertTrue(await self.first_store.health())

    async def clean_owned_keys(self):
        keys = [self.first_store.key(code) for code in self.codes]
        if keys:
            await self.second_store.client.delete(*keys)

    async def test_watch_multi_conflicts_preserve_all_simultaneous_updates(self):
        await self.make_room()
        before = await self.first_store.get(self.code)
        changes = 12

        def increment(document):
            document["test_counter"] = document.get("test_counter", 0) + 1
            return None, True

        await asyncio.gather(*[
            (self.first_store if index % 2 else self.second_store).mutate(self.code, increment)
            for index in range(changes)
        ])
        after = await self.first_store.get(self.code)
        self.assertEqual(after["test_counter"], changes)
        self.assertEqual(after["revision"], before["revision"] + changes)

    async def test_pubsub_delivers_committed_revisions_without_quiz_content(self):
        await self.make_room()
        async with self.first_store.subscribe(self.code) as wait_for_change:
            room, _ = await self.host_command("start_game", self.second)
            revision = await asyncio.wait_for(wait_for_change(), 3)
            self.assertEqual(str(revision), str(room["revision"]))
            self.assertEqual((await self.first_store.get(self.code))["state"], "question")

    async def test_real_ttl_reads_do_not_renew_but_authenticated_activity_does(self):
        await self.make_room()
        key = self.first_store.key(self.code)
        self.assertGreaterEqual(await self.first_store.client.ttl(key), 86390)
        await self.first_store.client.pexpire(key, 5000)
        await self.second_store.get(self.code)
        self.assertLessEqual(await self.first_store.client.pttl(key), 5000)
        await self.host_command("ping")
        self.assertGreaterEqual(await self.first_store.client.ttl(key), 86390)
        await self.first_store.client.pexpire(key, 1)
        await asyncio.sleep(0.02)
        with self.assertRaises(RoomMissing):
            await self.second_store.get(self.code)

    async def test_new_redis_client_restores_original_deadline_and_scores(self):
        await self.make_room()
        await self.host_command("start_game")
        original, _ = await self.answer()
        await self.first_store.close()
        restarted_store = RedisRoomStore(os.environ["TEST_REDIS_URL"], self.prefix)
        self.addAsyncCleanup(restarted_store.close)
        restarted = RoomManager(restarted_store)
        room, player_id = await restarted.connect(self.code, "player", PLAYER_TOKEN, "after-restart", "Ada")
        self.assertEqual(room["question_ends_at"], original["question_ends_at"])
        self.assertEqual(room["players"][player_id]["score"], original["players"][player_id]["score"])
        self.assertEqual(snapshot(room, player_id)["selected_option"], 1)


if __name__ == "__main__":
    unittest.main()
