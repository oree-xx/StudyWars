"""Vercel's Python entrypoint; the frontend is served separately by its CDN."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "server"))

from app.main import app  # noqa: E402, F401
