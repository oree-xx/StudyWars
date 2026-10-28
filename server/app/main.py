from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.frontend import mount_frontend
from app.persistence import StorageUnavailable
from app.rooms import room_manager
from app.routers import questions, rooms, ws


@asynccontextmanager
async def lifespan(_app):
    try:
        yield
    finally:
        await room_manager.close()


app = FastAPI(title="StudyWars API", lifespan=lifespan)

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
async def health_check():
    try:
        await room_manager.store.health()
    except StorageUnavailable as error:
        raise HTTPException(503, str(error)) from None
    return {"status": "ok"}


mount_frontend(app, settings.frontend_dist)
