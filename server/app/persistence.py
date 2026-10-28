"""Atomic room documents; Pub/Sub carries revisions, never quiz data or secrets."""
import asyncio
import copy
import json
import time
from contextlib import asynccontextmanager

from redis.asyncio import Redis
from redis.backoff import NoBackoff
from redis.exceptions import RedisError, WatchError
from redis.retry import Retry


class StorageUnavailable(Exception):
    """Safe to expose; never include credentials or underlying exception text."""


class RoomMissing(Exception):
    pass


def _decode(raw):
    if raw is None:
        raise RoomMissing()
    try:
        value = json.loads(raw)
        if not isinstance(value, dict) or value.get("version") != 1:
            raise ValueError()
        return value
    except (TypeError, ValueError):
        raise StorageUnavailable("Room storage is temporarily unavailable.") from None


class MemoryRoomStore:
    """Local-only implementation of the same atomic document contract."""

    def __init__(self, ttl=86400):
        self.ttl = ttl
        self.documents = {}
        self.expires = {}
        self.listeners = {}
        self.lock = asyncio.Lock()

    def _get(self, code):
        if self.expires.get(code, 0) <= time.time():
            self.documents.pop(code, None)
            self.expires.pop(code, None)
        document = self.documents.get(code)
        if document is None:
            raise RoomMissing()
        return copy.deepcopy(document)

    async def create(self, code, document):
        async with self.lock:
            try:
                self._get(code)
            except RoomMissing:
                self.documents[code] = copy.deepcopy(document)
                self.expires[code] = time.time() + self.ttl
                return True
            return False

    async def get(self, code):
        async with self.lock:
            return self._get(code)

    async def mutate(self, code, change):
        async with self.lock:
            document = self._get(code)
            before = copy.deepcopy(document)
            result, notify = change(document)
            if document != before:
                document["revision"] += 1
                self.documents[code] = copy.deepcopy(document)
                self.expires[code] = time.time() + self.ttl
                if notify:
                    for queue in self.listeners.get(code, set()):
                        if queue.empty():
                            queue.put_nowait(document["revision"])
            return document, result

    @asynccontextmanager
    async def subscribe(self, code):
        queue = asyncio.Queue(maxsize=1)
        self.listeners.setdefault(code, set()).add(queue)
        try:
            yield queue.get
        finally:
            listeners = self.listeners[code]
            listeners.discard(queue)
            if not listeners:
                del self.listeners[code]

    async def health(self):
        return True

    async def close(self):
        pass


class RedisRoomStore:
    def __init__(self, url, prefix, ttl=86400, client=None):
        # Connections open lazily. Do not retry ambiguous writes: reconnecting
        # clients reload committed state and answer retries are idempotent.
        self.client = client or Redis.from_url(
            url, decode_responses=True, protocol=2, socket_connect_timeout=5,
            socket_timeout=8, retry=Retry(NoBackoff(), 0),
            max_connections=256, health_check_interval=0,
        )
        self.prefix = prefix
        self.ttl = ttl

    def key(self, code):
        return f"{self.prefix}:room:{{{code}}}"

    def channel(self, code):
        return f"{self.prefix}:changes:{{{code}}}"

    async def create(self, code, document):
        try:
            return bool(await self.client.set(
                self.key(code), json.dumps(document), nx=True, ex=self.ttl,
            ))
        except RedisError:
            raise StorageUnavailable("Room storage is temporarily unavailable.") from None

    async def get(self, code):
        try:
            return _decode(await self.client.get(self.key(code)))
        except RedisError:
            raise StorageUnavailable("Room storage is temporarily unavailable.") from None

    async def mutate(self, code, change):
        try:
            for attempt in range(16):
                async with self.client.pipeline(transaction=True) as pipe:
                    try:
                        await pipe.watch(self.key(code))
                        document = _decode(await pipe.get(self.key(code)))
                        before = copy.deepcopy(document)
                        # Pure synchronous changes may safely rerun on WATCH conflicts.
                        result, notify = change(document)
                        if document == before:
                            await pipe.unwatch()
                            return document, result
                        document["revision"] += 1
                        pipe.multi()
                        pipe.set(self.key(code), json.dumps(document), ex=self.ttl)
                        if notify:
                            pipe.publish(self.channel(code), str(document["revision"]))
                        await pipe.execute()
                        return document, result
                    except WatchError:
                        await asyncio.sleep(min(0.002 * (attempt + 1), 0.03))
            raise StorageUnavailable("The room is busy. Please reconnect and try again.")
        except RedisError:
            raise StorageUnavailable("Room storage is temporarily unavailable.") from None

    @asynccontextmanager
    async def subscribe(self, code):
        try:
            async with self.client.pubsub(ignore_subscribe_messages=False) as subscription:
                await subscription.subscribe(self.channel(code))
                # Acknowledgement before GET closes the subscribe/read race.
                async with asyncio.timeout(8):
                    while True:
                        message = await subscription.get_message(timeout=8)
                        if message and message["type"] == "subscribe":
                            break

                async def wait_for_change():
                    while True:
                        message = await subscription.get_message(timeout=30)
                        if message is None:
                            await subscription.ping()
                        elif message["type"] == "message":
                            return message["data"]
                        elif message["type"] == "subscribe":
                            # Auto-resubscribe signals a delivery gap: clients
                            # reconnect and receive authoritative state.
                            raise StorageUnavailable("Room updates were interrupted. Please reconnect.")

                yield wait_for_change
        except (RedisError, TimeoutError):
            raise StorageUnavailable("Room updates are temporarily unavailable.") from None

    async def health(self):
        try:
            return await self.client.ping()
        except RedisError:
            raise StorageUnavailable("Room storage is temporarily unavailable.") from None

    async def close(self):
        await self.client.aclose()
