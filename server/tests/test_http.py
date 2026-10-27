"""Exercise the actual ASGI routes and WebSocket wire messages."""
import unittest

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.rooms import room_manager


QUESTION = {
    "question": "What is 2 + 2?", "options": ["3", "4", "5", "6"],
    "correct_index": 1, "explanation": "Two plus two is four.",
}


def receive_type(socket, expected):
    for _ in range(10):
        message = socket.receive_json()
        if message["type"] == expected:
            return message
    raise AssertionError(f"No {expected} message received")


class HttpIntegrationTests(unittest.TestCase):
    def test_game_with_player_and_host_refresh(self):
        with TestClient(app) as client:
            response = client.post("/api/rooms", json={"questions": [QUESTION]})
            self.assertEqual(response.status_code, 200)
            room = response.json()
            code = room["room_code"]
            host_url = f"/ws/host/{code}?token={room['host_token']}"
            player_url = f"/ws/player/{code}?name=Ada&player_token={'a' * 48}"
            try:
                with client.websocket_connect(host_url) as host:
                    self.assertEqual(host.receive_json()["state"], "lobby")
                    with client.websocket_connect(player_url) as player:
                        joined = player.receive_json()
                        self.assertEqual(joined["type"], "room_state")
                        host.send_json({"type": "start_game"})
                        question = receive_type(player, "question")
                        self.assertGreater(question["ends_at"], question["server_time"])
                        self.assertNotIn("correct_index", question)
                        player.send_json({"type": "answer", "question_index": 0, "option_index": 1})
                        self.assertEqual(receive_type(player, "answer_ack")["option_index"], 1)
                        self.assertEqual(receive_type(player, "reveal")["correct_index"], 1)
                    with client.websocket_connect(player_url) as resumed:
                        state = resumed.receive_json()
                        self.assertEqual(state["player_id"], joined["player_id"])
                        self.assertEqual(state["selected_option"], 1)
                        self.assertEqual(state["state"], "reveal")
                        self.assertGreater(state["leaderboard"][0]["score"], 0)
                        host.send_json({"type": "next_question"})
                        final = receive_type(resumed, "game_over")
                        self.assertEqual(final["leaderboard"][0]["id"], joined["player_id"])
                with client.websocket_connect(host_url) as refreshed_host:
                    self.assertEqual(refreshed_host.receive_json()["state"], "ended")
                    refreshed_host.send_json({"type": "ping"})
                    self.assertEqual(refreshed_host.receive_json()["type"], "pong")
            finally:
                room_manager.rooms.pop(code, None)

    def test_bad_host_credentials_deliver_terminal_close_code(self):
        with TestClient(app) as client:
            with client.websocket_connect("/ws/host/NOTFOUND?token=wrong") as socket:
                with self.assertRaises(WebSocketDisconnect) as error:
                    socket.receive_json()
                self.assertEqual(error.exception.code, 4001)


if __name__ == "__main__":
    unittest.main()
