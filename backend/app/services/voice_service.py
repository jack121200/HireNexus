# voice_service.py
# Voice TTS is coming soon via VAPI integration.
# AWS Polly credentials have been removed from .env.
# All call sites are handled by the route which returns HTTP 503.
from __future__ import annotations

from typing import Any


def synthesize_speech_with_marks(*, text: str) -> dict[str, Any]:
    """
    Stub — Voice TTS is coming soon via VAPI.
    Raises NotImplementedError so the route can return a graceful 503.
    """
    raise NotImplementedError(
        "Voice TTS is coming soon via VAPI integration. "
        "AWS Polly credentials have been removed pending the VAPI handoff."
    )
