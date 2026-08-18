from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models import Question
from app.rooms import room_manager

router = APIRouter(prefix="/api", tags=["rooms"])


class CreateRoomRequest(BaseModel):
    questions: List[Question]


class CreateRoomResponse(BaseModel):
    room_code: str
    host_token: str


@router.post("/rooms", response_model=CreateRoomResponse)
def create_room(payload: CreateRoomRequest):
    if not payload.questions:
        raise HTTPException(400, "At least one question is required to create a room.")
    room = room_manager.create_room(payload.questions)
    return CreateRoomResponse(room_code=room.code, host_token=room.host_token)
