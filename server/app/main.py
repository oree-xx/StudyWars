from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import questions, rooms, ws

app = FastAPI(title="StudyWars API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(questions.router)
app.include_router(rooms.router)
app.include_router(ws.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
