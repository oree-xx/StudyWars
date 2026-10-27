"""Verify production assets and client-side routes share the API origin."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.frontend import mount_frontend


class FrontendTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.build = self.root / "dist"
        self.build.mkdir()
        (self.build / "assets").mkdir()
        (self.build / "index.html").write_text("<html>StudyWars</html>", encoding="utf-8")
        (self.build / "assets" / "app.js").write_text("console.log('quiz')", encoding="utf-8")
        (self.root / "private.txt").write_text("private backend value", encoding="utf-8")

        self.app = FastAPI()

        @self.app.get("/health")
        def health():
            return {"status": "ok"}

        @self.app.post("/api/example")
        def api_example():
            return {"created": True}

        @self.app.websocket("/ws/example")
        async def websocket_example(socket: WebSocket):
            await socket.accept()
            await socket.send_json({"type": "ready"})
            await socket.close()

        mount_frontend(self.app, str(self.build))
        self.client = self.enterContext(TestClient(self.app))

    def test_client_routes_and_refresh_return_the_shell(self):
        for path in ("/", "/host", "/join?room=ABCD", "/play", "/host/"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.text, "<html>StudyWars</html>")
                self.assertIn("text/html", response.headers["content-type"])
                self.assertEqual(response.headers["cache-control"], "no-cache")
        response = self.client.head("/host")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")

    def test_assets_are_served_and_missing_paths_remain_404(self):
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        self.assertIn("console.log", response.text)
        for path in ("/assets/missing.js", "/missing.png", "/unknown", "/api/missing", "/ws/missing"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_health_api_docs_and_websockets_keep_their_routes(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})
        self.assertEqual(self.client.post("/api/example").json(), {"created": True})
        self.assertIn("openapi", self.client.get("/openapi.json").json())
        self.assertEqual(self.client.get("/docs").status_code, 200)
        with self.client.websocket_connect("/ws/example") as socket:
            self.assertEqual(socket.receive_json(), {"type": "ready"})
        with self.assertRaises(WebSocketDisconnect):
            with self.client.websocket_connect("/ws/missing"):
                pass

    def test_cannot_read_files_outside_the_build(self):
        for path in ("/%2e%2e/private.txt", "/assets/%2e%2e/%2e%2e/private.txt", "/%2e%2e%5cprivate.txt"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)
                self.assertNotIn("private backend value", response.text)

    def test_disabled_and_invalid_build_configuration(self):
        api_only = FastAPI()
        mount_frontend(api_only, "")
        with TestClient(api_only) as client:
            self.assertEqual(client.get("/").status_code, 404)
        for directory in (self.root / "missing", self.root):
            with self.subTest(directory=directory):
                with self.assertRaisesRegex(RuntimeError, "FRONTEND_DIST"):
                    mount_frontend(FastAPI(), str(directory))


if __name__ == "__main__":
    unittest.main()
