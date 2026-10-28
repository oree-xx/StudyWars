"""Room transitions are pure document changes committed atomically by the store."""
import hashlib
import os
import re
import secrets
import time
import uuid

from app.config import settings
from app.persistence import MemoryRoomStore, RedisRoomStore, RoomMissing, StorageUnavailable

TIME_LIMIT_SECONDS = 20
CONNECTION_LEASE_SECONDS = 90
RENEW_INTERVAL_SECONDS = 30
BASE_POINTS = 1000
MIN_POINTS = 100
ROOM_CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
ROOM_CODE = re.compile(r"[A-Z2-9]{6}\Z")
PLAYER_TOKEN = re.compile(r"[A-Za-z0-9_-]{32,128}\Z")


class SessionError(Exception):
    def __init__(self, code, reason):
        self.code = code
        self.reason = reason
        super().__init__(reason)


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _new_room_code():
    return "".join(secrets.choice(ROOM_CODE_CHARS) for _ in range(6))


def _points_for(is_correct, elapsed, time_limit):
    if not is_correct:
        return 0
    fraction_remaining = max(0.0, min(1.0, 1 - elapsed / time_limit))
    return int(MIN_POINTS + (BASE_POINTS - MIN_POINTS) * fraction_remaining)


def _expire_question(room, now):
    if room["state"] == "question" and now >= room["question_ends_at"]:
        room["state"] = "reveal"
        return True
    return False


def _connection(room, role, player_id):
    return room["host_connection"] if role == "host" else room["players"][player_id]["connection"]


def verify_connection(room, role, player_id, connection_id, now=None):
    connection = _connection(room, role, player_id)
    if connection["id"] != connection_id:
        raise SessionError(4002, "Session opened in another connection.")
    if connection["expires_at"] <= (time.time() if now is None else now):
        raise SessionError(1013, "Session connection expired. Please reconnect.")


def public_players(room, now):
    players = []
    for player in room["players"].values():
        score = player["score"]
        # Live points disclose whether an answer was right before reveal.
        if room["state"] == "question":
            score -= player["answers"].get(str(room["current_index"]), [0, 0])[1]
        connection = player["connection"]
        players.append({
            "id": player["id"], "name": player["name"], "score": score,
            "connected": bool(connection["id"] and connection["expires_at"] > now),
        })
    return sorted(players, key=lambda player: player["score"], reverse=True)


def snapshot(room, player_id=None, now=None):
    now = time.time() if now is None else now
    index = room["current_index"]
    question = room["questions"][index] if 0 <= index < len(room["questions"]) else None
    players = public_players(room, now)
    answer = room["players"][player_id]["answers"].get(str(index)) if player_id else None
    result = {
        "type": "room_state", "room_code": room["code"], "state": room["state"],
        "players": players, "leaderboard": players, "question": None, "reveal": None,
        "selected_option": answer[0] if answer else None,
        "answered_count": sum(str(index) in p["answers"] for p in room["players"].values()),
        "total_players": len(players),
    }
    if question:
        result["question"] = {
            "type": "question", "index": index, "total": len(room["questions"]),
            "question": question["question"], "options": question["options"],
            "time_limit": room["time_limit"],
            "ends_at": room["question_ends_at"] * 1000, "server_time": now * 1000,
        }
        if room["state"] == "reveal":
            result["reveal"] = {
                "type": "reveal", "correct_index": question["correct_index"],
                "explanation": question["explanation"], "leaderboard": players,
            }
    if player_id:
        result["player_id"] = player_id
    return result


def storage_namespace():
    prefix = settings.redis_key_prefix
    if not re.fullmatch(r"[A-Za-z0-9:_-]{1,80}", prefix):
        raise StorageUnavailable("REDIS_KEY_PREFIX is not configured correctly.")
    environment = os.getenv("VERCEL_ENV", "local")
    if environment == "production":
        return f"{prefix}:production"
    # Preview branches cannot read or overwrite production rooms.
    branch = os.getenv("VERCEL_GIT_COMMIT_REF") or os.getenv("VERCEL_URL") or "local"
    scope = hashlib.sha256(f"{environment}:{branch}".encode()).hexdigest()[:16]
    return f"{prefix}:isolated:{scope}"


class RoomManager:
    def __init__(self, store=None):
        self._store = store

    @property
    def store(self):
        if self._store is None:
            mode = settings.room_storage.lower().strip()
            url = settings.redis_url.strip()
            vercel = os.getenv("VERCEL") == "1"
            if mode not in {"auto", "memory", "redis"}:
                raise StorageUnavailable("ROOM_STORAGE is not configured correctly.")
            if vercel and (mode == "memory" or not url.startswith("rediss://")):
                raise StorageUnavailable("Durable room storage requires a TLS REDIS_URL on Vercel.")
            if mode == "redis" and not url:
                raise StorageUnavailable("Durable room storage requires REDIS_URL.")
            if mode != "memory" and url:
                if not url.startswith(("redis://", "rediss://")):
                    raise StorageUnavailable("REDIS_URL must use the Redis protocol.")
                try:
                    self._store = RedisRoomStore(url, storage_namespace(), settings.room_ttl_seconds)
                except (ValueError, TypeError):
                    raise StorageUnavailable("REDIS_URL is not configured correctly.") from None
            else:
                self._store = MemoryRoomStore(settings.room_ttl_seconds)
        return self._store

    async def close(self):
        if self._store is not None:
            await self._store.close()
            self._store = None

    async def create_room(self, questions):
        if not 1 <= len(questions) <= 20:
            raise ValueError("A room needs between 1 and 20 questions.")
        host_token = secrets.token_urlsafe(32)
        for _ in range(10):
            code = _new_room_code()
            document = {
                "version": 1, "revision": 0, "code": code,
                "host_token_hash": token_hash(host_token),
                "host_connection": {"id": None, "expires_at": 0},
                "questions": [question.model_dump() for question in questions],
                "players": {}, "state": "lobby", "current_index": -1,
                "question_started_at": 0, "question_ends_at": 0,
                "time_limit": TIME_LIMIT_SECONDS,
            }
            if await self.store.create(code, document):
                return {"room_code": code, "host_token": host_token}
        raise StorageUnavailable("Could not allocate a room. Please try again.")

    async def connect(self, code, role, token, connection_id, name=""):
        def change(room):
            now = time.time()
            player_id = None
            digest = token_hash(token)
            if role == "host":
                if not secrets.compare_digest(room["host_token_hash"], digest):
                    raise SessionError(4001, "This host session is no longer available.")
                connection = room["host_connection"]
            else:
                player = next((p for p in room["players"].values()
                               if secrets.compare_digest(p["token_hash"], digest)), None)
                if player is None:
                    if room["state"] != "lobby":
                        raise SessionError(4003, "This game has already started.")
                    if len(room["players"]) >= 100:
                        raise SessionError(4003, "This room is full.")
                    player_id = str(uuid.uuid4())
                    player = {
                        "id": player_id, "name": name.strip()[:20] or "Player",
                        "token_hash": digest, "score": 0, "answers": {},
                        "connection": {"id": None, "expires_at": 0},
                    }
                    room["players"][player_id] = player
                player_id = player["id"]
                connection = player["connection"]
            connection.update(id=connection_id, expires_at=now + CONNECTION_LEASE_SECONDS)
            _expire_question(room, now)
            return player_id, True
        return await self.store.mutate(code, change)

    async def disconnect(self, code, role, player_id, connection_id):
        def change(room):
            connection = _connection(room, role, player_id)
            # Old function cleanup cannot detach a replacement connection.
            if connection["id"] == connection_id:
                connection.update(id=None, expires_at=0)
            return None, True
        try:
            await self.store.mutate(code, change)
        except (RoomMissing, StorageUnavailable):
            pass

    async def expire(self, code, expected_index):
        def change(room):
            if room["current_index"] == expected_index:
                _expire_question(room, time.time())
            return None, True
        return (await self.store.mutate(code, change))[0]

    async def command(self, code, role, player_id, connection_id, message):
        def change(room):
            now = time.time()
            verify_connection(room, role, player_id, connection_id, now)
            expired = _expire_question(room, now)
            kind = message.get("type")
            if kind == "ping":
                _connection(room, role, player_id)["expires_at"] = now + CONNECTION_LEASE_SECONDS
                return {"type": "pong"}, expired
            if role == "host":
                if kind in {"next_question", "reveal_now"}:
                    index = message.get("question_index")
                    if type(index) is not int or index != room["current_index"]:
                        return None, expired
                if ((kind == "start_game" and room["state"] == "lobby") or
                        (kind == "next_question" and room["state"] == "reveal")):
                    room["current_index"] += 1
                    if room["current_index"] >= len(room["questions"]):
                        room["state"] = "ended"
                    else:
                        room["state"] = "question"
                        room["question_started_at"] = now
                        room["question_ends_at"] = now + room["time_limit"]
                elif kind == "reveal_now" and room["state"] == "question":
                    room["state"] = "reveal"
                return None, True
            if kind != "answer":
                return None, expired
            index = message.get("question_index")
            option = message.get("option_index")

            def rejected(reason):
                return {"type": "answer_rejected", "question_index": index, "reason": reason}, True

            if type(index) is not int or index != room["current_index"]:
                return rejected("That question is no longer active.")
            if type(option) is not int or not 0 <= option < 4:
                return rejected("Choose one of the four answers.")
            player = room["players"][player_id]
            previous = player["answers"].get(str(index))
            if previous is not None:
                return {"type": "answer_ack", "question_index": index, "option_index": previous[0]}, expired
            if room["state"] != "question":
                return rejected("Time is up for this question." if expired else "Answers are closed for this question.")
            question = room["questions"][index]
            points = _points_for(option == question["correct_index"], now - room["question_started_at"], room["time_limit"])
            player["answers"][str(index)] = [option, points]
            player["score"] += points
            if all(str(index) in p["answers"] for p in room["players"].values()):
                room["state"] = "reveal"
            return {"type": "answer_ack", "question_index": index, "option_index": option}, True
        return await self.store.mutate(code, change)


room_manager = RoomManager()
