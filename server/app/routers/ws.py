import re
import secrets
import time
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.rooms import Player, TIME_LIMIT_SECONDS, room_manager

router = APIRouter()
PLAYER_TOKEN = re.compile(r"[A-Za-z0-9_-]{32,128}\Z")


async def close_invalid(websocket: WebSocket, code: int, reason: str):
    # Complete the handshake so browsers receive the application close code.
    await websocket.accept()
    await websocket.close(code=code, reason=reason)


async def close_replaced(websocket: WebSocket | None):
    if websocket is not None:
        try:
            await websocket.close(code=4002, reason="Session opened in another connection.")
        except Exception:
            pass


@router.websocket("/ws/host/{room_code}")
async def host_socket(websocket: WebSocket, room_code: str, token: str = ""):
    room = room_manager.get(room_code)
    if room is None or not secrets.compare_digest(room.host_token, token):
        await close_invalid(websocket, 4001, "This host session is no longer available.")
        return

    await websocket.accept()
    try:
        async with room.lock:
            if room.state == "question" and time.monotonic() - room.question_started_at >= TIME_LIMIT_SECONDS:
                await room._reveal_answer()
            previous = room.host_ws
            room.host_ws = websocket
            await close_replaced(previous)
            await websocket.send_json(room.snapshot())
        while True:
            try:
                data = await websocket.receive_json()
            except ValueError:
                continue
            if room.host_ws is not websocket or not isinstance(data, dict):
                continue
            msg_type = data.get("type")
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg_type == "start_game":
                await room.start_game(websocket)
            elif msg_type == "next_question":
                await room.advance_question(websocket)
            elif msg_type == "reveal_now":
                await room.reveal_answer(websocket)
    except WebSocketDisconnect:
        pass
    except RuntimeError:
        # Closing a replaced Starlette socket locally can make the next receive
        # raise RuntimeError before its remote disconnect event is consumed.
        if websocket.application_state != WebSocketState.DISCONNECTED and room.host_ws is websocket:
            raise
    finally:
        async with room.lock:
            if room.host_ws is websocket:
                room.host_ws = None


@router.websocket("/ws/player/{room_code}")
async def player_socket(
    websocket: WebSocket, room_code: str, name: str = "", player_token: str = "",
):
    room = room_manager.get(room_code)
    if room is None:
        await close_invalid(websocket, 4004, "Room not found.")
        return
    if not PLAYER_TOKEN.fullmatch(player_token):
        await close_invalid(websocket, 4001, "A valid player session is required.")
        return

    await websocket.accept()
    player = None
    try:
        async with room.lock:
            player = room.player_with_token(player_token)
            if player is None:
                if room.state != "lobby":
                    await websocket.close(code=4003, reason="This game has already started.")
                    return
                player = Player(
                    id=str(uuid.uuid4()), name=name.strip()[:20] or "Player",
                    token=player_token,
                )
                room.players[player.id] = player
            if room.state == "question" and time.monotonic() - room.question_started_at >= TIME_LIMIT_SECONDS:
                await room._reveal_answer()
            previous = player.websocket
            player.websocket = websocket
            await close_replaced(previous)
            await websocket.send_json(room.snapshot(player))
            await room.broadcast({"type": "player_joined", "players": room.leaderboard()})

        while True:
            try:
                data = await websocket.receive_json()
            except ValueError:
                continue
            if player.websocket is not websocket or not isinstance(data, dict):
                continue
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif data.get("type") == "answer":
                await room.submit_answer(
                    player.id, data.get("option_index"), data.get("question_index"), websocket,
                )
    except WebSocketDisconnect:
        pass
    except RuntimeError:
        replaced = player is not None and player.websocket is not websocket
        if websocket.application_state != WebSocketState.DISCONNECTED and not replaced:
            raise
    finally:
        async with room.lock:
            # An older socket closing must not detach a newly resumed session.
            if player is not None and player.websocket is websocket:
                player.websocket = None
                await room.broadcast({"type": "player_left", "players": room.leaderboard()})
