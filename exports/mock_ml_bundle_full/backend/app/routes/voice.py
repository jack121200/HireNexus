# file name is voice.py
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.services.voice_service import synthesize_speech_with_marks


router = APIRouter(prefix="/api/voice", tags=["voice"])


class TtsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


@router.post("/tts")
def tts(
    payload: TtsRequest,
    _current_user=Depends(get_current_user),
    _db: Session = Depends(get_db),
) -> dict:
    text = payload.text.strip()
    return synthesize_speech_with_marks(text=text)
