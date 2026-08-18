import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.rooms import Player, room_manager

router = APIRouter()


@router.websocket("/ws/host/{room_code}")
async def host_socket(websocket: WebSocket, room_code: str, token: str):
    room = room_manager.get(room_code)
    if room is None or room.host_token != token:
        await websocket.close(code=4001)  # invalid room or token
        return

    await websocket.accept()
    room.host_ws = websocket
    await websocket.send_json({"type": "room_state", "state": room.state, "players": room.leaderboard()})

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "start_game":
                await room.start_game()
            elif msg_type == "next_question" and room.state == "reveal":
                await room.advance_question()
            elif msg_type == "reveal_now" and room.state == "question":
                await room.reveal_answer()
    except WebSocketDisconnect:
        room.host_ws = None


@router.websocket("/ws/player/{room_code}")
async def player_socket(websocket: WebSocket, room_code: str, name: str):
    room = room_manager.get(room_code)
    if room is None:
        await websocket.close(code=4004)  # room not found
        return
    if room.state != "lobby":
        await websocket.close(code=4003)  # game already in progress
        return

    await websocket.accept()
    player_name = name.strip()[:20] or "Player"
    player = Player(id=str(uuid.uuid4()), name=player_name, websocket=websocket)
    room.players[player.id] = player

    await websocket.send_json({"type": "joined", "player_id": player.id, "room_code": room.code})
    await room.broadcast({"type": "player_joined", "players": room.leaderboard()})

    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "answer":
                option_index = data.get("option_index")
                if isinstance(option_index, int):
                    await room.submit_answer(player.id, option_index)
    except WebSocketDisconnect:
        room.players.pop(player.id, None)
        await room.broadcast({"type": "player_left", "players": room.leaderboard()})
