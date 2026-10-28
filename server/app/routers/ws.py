"""WebSocket connections hold no authoritative game state."""
import asyncio
import copy
import os
import secrets
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.persistence import RoomMissing, StorageUnavailable
from app.rooms import (
    PLAYER_TOKEN, ROOM_CODE, RENEW_INTERVAL_SECONDS, SessionError,
    room_manager, snapshot, verify_connection,
)

router = APIRouter()


async def close_socket(websocket, code, reason):
    try:
        if websocket.application_state == WebSocketState.CONNECTING:
            await websocket.accept()
        if websocket.application_state != WebSocketState.DISCONNECTED:
            await websocket.close(code=code, reason=reason)
    except (WebSocketDisconnect, RuntimeError):
        pass


class SocketSession:
    def __init__(self, websocket, manager, code, role, connection_id, player_id, document):
        self.websocket = websocket
        self.manager = manager
        self.code = code
        self.role = role
        self.connection_id = connection_id
        self.player_id = player_id
        self.document = document
        self.last_public = None
        self.lock = asyncio.Lock()
        self.last_renewed = time.monotonic()

    async def sync(self, document):
        # Call under the per-socket lock: the answer receipt must be sent before
        # the notification watcher can send the resulting reveal.
        verify_connection(document, self.role, self.player_id, self.connection_id)
        state = snapshot(document, self.player_id)
        comparable = copy.deepcopy(state)
        if comparable["question"]:
            comparable["question"].pop("server_time")
        previous = self.last_public
        self.document = document
        if comparable == previous:
            return
        if previous is not None:
            previous_index = previous["question"]["index"] if previous["question"] else None
            current_index = state["question"]["index"] if state["question"] else None
            if state["state"] == "question" and (previous["state"] != "question" or previous_index != current_index):
                await self.websocket.send_json(state["question"])
            elif state["state"] == "reveal" and (previous["state"] != "reveal" or previous_index != current_index):
                await self.websocket.send_json(state["reveal"])
            elif state["state"] == "ended" and previous["state"] != "ended":
                await self.websocket.send_json({"type": "game_over", "leaderboard": state["leaderboard"]})
            old_presence = {p["id"]: (p["name"], p["connected"]) for p in previous["players"]}
            new_presence = {p["id"]: (p["name"], p["connected"]) for p in state["players"]}
            if old_presence != new_presence:
                joined = any(player_id not in old_presence or (presence[1] and not old_presence[player_id][1])
                             for player_id, presence in new_presence.items())
                kind = "player_joined" if joined else "player_left"
                await self.websocket.send_json({"type": kind, "players": state["players"]})
            if self.role == "host" and previous["answered_count"] != state["answered_count"]:
                await self.websocket.send_json({
                    "type": "player_answered", "answered_count": state["answered_count"],
                    "total_players": state["total_players"],
                })
        # Snapshots recover coalesced/missed transitions and accepted answers.
        await self.websocket.send_json(state)
        self.last_public = comparable

    async def receive(self):
        while True:
            try:
                data = await asyncio.wait_for(self.websocket.receive_json(), timeout=60)
            except ValueError:
                continue
            except TimeoutError:
                raise SessionError(1013, "Connection timed out. Please reconnect.") from None
            if not isinstance(data, dict):
                continue
            kind = data.get("type")
            allowed = {"ping", "start_game", "next_question", "reveal_now"} if self.role == "host" else {"ping", "answer"}
            if kind not in allowed:
                continue
            async with self.lock:
                if kind == "ping" and time.monotonic() - self.last_renewed < RENEW_INTERVAL_SECONDS:
                    # Socket liveness needs no Redis write every 15 seconds.
                    await self.websocket.send_json({"type": "pong"})
                    continue
                document, receipt = await self.manager.command(
                    self.code, self.role, self.player_id, self.connection_id, data,
                )
                if kind == "ping":
                    self.last_renewed = time.monotonic()
                if receipt is not None:
                    await self.websocket.send_json(receipt)
                await self.sync(document)

    async def watch(self, wait_for_change):
        notification = asyncio.create_task(wait_for_change())
        try:
            while True:
                deadline = self.document["question_ends_at"] if self.document["state"] == "question" else None
                delay = max(0, deadline - time.time()) if deadline is not None else None
                done, _ = await asyncio.wait({notification}, timeout=delay)
                async with self.lock:
                    if done:
                        notification.result()
                        notification = asyncio.create_task(wait_for_change())
                        document = await self.manager.store.get(self.code)
                    else:
                        # Concurrent timers on different instances all attempt the
                        # same conditional transition; only one can commit it.
                        document = await self.manager.expire(self.code, self.document["current_index"])
                    await self.sync(document)
        finally:
            notification.cancel()
            await asyncio.gather(notification, return_exceptions=True)

    async def run(self, wait_for_change):
        await self.sync(self.document)
        tasks = [asyncio.create_task(self.receive()), asyncio.create_task(self.watch(wait_for_change))]
        try:
            # Recycle before Vercel's 300s limit; the next instance resumes Redis.
            timeout = 270 if os.getenv("VERCEL") == "1" else None
            done, _ = await asyncio.wait(tasks, timeout=timeout, return_when=asyncio.FIRST_COMPLETED)
            if not done:
                raise SessionError(1012, "Reconnecting to resume your room.")
            for task in done:
                task.result()
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)


async def serve_socket(websocket, room_code, role, token, name="", manager=None):
    manager = manager or room_manager
    code = room_code.upper()
    if not ROOM_CODE.fullmatch(code):
        await close_socket(websocket, 4001 if role == "host" else 4004, "Room not found.")
        return
    if role == "player" and not PLAYER_TOKEN.fullmatch(token):
        await close_socket(websocket, 4001, "A valid player session is required.")
        return
    if role == "host" and (not token or len(token) > 128):
        await close_socket(websocket, 4001, "This host session is no longer available.")
        return
    connection_id = secrets.token_urlsafe(24)
    player_id = None
    claimed = False
    await websocket.accept()
    try:
        async with manager.store.subscribe(code) as wait_for_change:
            document, player_id = await manager.connect(code, role, token, connection_id, name)
            claimed = True
            session = SocketSession(websocket, manager, code, role, connection_id, player_id, document)
            await session.run(wait_for_change)
    except WebSocketDisconnect:
        pass
    except SessionError as error:
        await close_socket(websocket, error.code, error.reason)
    except RoomMissing:
        await close_socket(websocket, 4001 if role == "host" else 4004, "This room is no longer available.")
    except StorageUnavailable:
        await close_socket(websocket, 1013, "Room storage is temporarily unavailable. Please reconnect.")
    except RuntimeError:
        # Starlette can raise after a local close; unrelated failures stay visible.
        if websocket.application_state != WebSocketState.DISCONNECTED:
            raise
    finally:
        if claimed:
            await manager.disconnect(code, role, player_id, connection_id)


@router.websocket("/ws/host/{room_code}")
async def host_socket(websocket: WebSocket, room_code: str, token: str = ""):
    await serve_socket(websocket, room_code, "host", token)


@router.websocket("/ws/player/{room_code}")
async def player_socket(websocket: WebSocket, room_code: str, name: str = "", player_token: str = ""):
    await serve_socket(websocket, room_code, "player", player_token, name)
