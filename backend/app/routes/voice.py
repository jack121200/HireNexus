# file name is voice.py
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

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
    _db=Depends(get_db),
) -> dict:
    """
    Text-to-Speech endpoint.
    Currently returns 503 — VAPI integration is pending.
    """
    try:
        return synthesize_speech_with_marks(text=payload.text.strip())
    except NotImplementedError as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "coming_soon",
                "message": str(exc),
            },
        )
