"""Serve the production frontend from the same origin as the API."""

from pathlib import Path

from fastapi import FastAPI
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles


class FrontendFiles(StaticFiles):
    async def get_response(self, path, scope):
        # Only actual client routes receive the SPA shell. Missing assets and
        # API URLs must retain their normal 404 response.
        if path in {".", "host", "join", "play", "index.html"}:
            response = await super().get_response("index.html", scope)
            response.headers["Cache-Control"] = "no-cache"
            return response
        if path.replace("\\", "/").split("/", 1)[0] in {
            "api", "ws", "health", "docs", "redoc", "openapi.json"
        }:
            raise HTTPException(status_code=404)
        return await super().get_response(path, scope)


def mount_frontend(app: FastAPI, directory: str) -> None:
    """Enable static serving only when a production build is configured."""
    if not directory:
        return

    build = Path(directory)
    if not build.is_dir() or not (build / "index.html").is_file():
        raise RuntimeError(
            f"FRONTEND_DIST must contain a built frontend with index.html: {directory}"
        )

    # This must be registered after API/health routes. An HTTP-only catch-all
    # also leaves unknown WebSocket paths to the router's normal close handler.
    app.add_route(
        "/{path:path}",
        FrontendFiles(directory=build),
        methods=["GET", "HEAD"],
        include_in_schema=False,
        name="frontend",
    )
