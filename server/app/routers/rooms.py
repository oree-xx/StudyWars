from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models import Question
from app.rooms import room_manager
from app.persistence import StorageUnavailable

router = APIRouter(prefix="/api", tags=["rooms"])


class CreateRoomRequest(BaseModel):
    questions: List[Question] = Field(min_length=1, max_length=20)


class CreateRoomResponse(BaseModel):
    room_code: str
    host_token: str


@router.post("/rooms", response_model=CreateRoomResponse)
async def create_room(payload: CreateRoomRequest):
    try:
        return CreateRoomResponse(**await room_manager.create_room(payload.questions))
    except StorageUnavailable as error:
        raise HTTPException(503, str(error)) from None
