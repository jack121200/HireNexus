# file name is voice_service.py
from __future__ import annotations

import base64
import json
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from app.core.config import get_settings
from app.core.logging import get_logger


logger = get_logger(__name__)


def _parse_speech_marks(payload: bytes) -> list[dict[str, Any]]:
    """Parse speech marks from Polly response."""
    marks: list[dict[str, Any]] = []
    
    if not payload:
        logger.warning("empty_speech_marks_payload")
        return marks
    
    for line in payload.splitlines():
        if not line or not line.strip():
            continue
        try:
            entry = json.loads(line.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning("invalid_speech_mark_line", error=str(exc))
            continue
        
        if entry.get("type") != "word":
            continue
        
        word = str(entry.get("value", "")).strip()
        time = int(entry.get("time", 0) or 0)
        
        if not word:
            continue
        
        marks.append({"word": word, "time": time})
    
    logger.debug("parsed_speech_marks", count=len(marks))
    return marks


def synthesize_speech_with_marks(*, text: str) -> dict[str, Any]:
    """
    Synthesize speech using AWS Polly with word-level timing marks.
    
    Args:
        text: Text to synthesize
        
    Returns:
        Dictionary containing:
            - audio_base64: Base64-encoded MP3 audio
            - word_marks: List of {word, time} dictionaries
            - voice_id: Voice ID used
            - engine: Engine used (neural or standard)
            - language_code: Language code used
    """
    settings = get_settings()
    
    # Validate input
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")
    
    text = text.strip()
    
    if len(text) > 3000:
        logger.warning("text_too_long", length=len(text))
        text = text[:3000]
    
    # Initialize Polly client
    try:
        polly = boto3.client("polly", region_name=settings.aws_region)
    except NoCredentialsError as exc:
        logger.error("aws_credentials_missing")
        raise RuntimeError("AWS credentials not configured") from exc
    except Exception as exc:
        logger.error("polly_client_init_failed", error=str(exc))
        raise RuntimeError("Failed to initialize Polly client") from exc
    
    voice_id = settings.polly_voice_id
    engine = settings.polly_engine
    language_code = settings.polly_language_code
    
    logger.info("synthesizing_speech", voice_id=voice_id, engine=engine, text_length=len(text))

    def _synthesize(engine_name: str):
        """Helper to synthesize with specific engine."""
        try:
            audio_response = polly.synthesize_speech(
                Text=text,
                OutputFormat="mp3",
                VoiceId=voice_id,
                Engine=engine_name,
                LanguageCode=language_code,
                TextType="text",
            )
            marks_response = polly.synthesize_speech(
                Text=text,
                OutputFormat="json",
                VoiceId=voice_id,
                Engine=engine_name,
                LanguageCode=language_code,
                SpeechMarkTypes=["word"],
                TextType="text",
            )
            return audio_response, marks_response
        except (BotoCoreError, ClientError) as exc:
            logger.warning(
                "polly_synthesis_failed",
                error=str(exc),
                voice_id=voice_id,
                engine=engine_name
            )
            raise

    # Try with configured engine first
    audio_response = None
    marks_response = None
    used_engine = engine
    
    try:
        audio_response, marks_response = _synthesize(engine)
    except (BotoCoreError, ClientError) as exc:
        # If neural engine fails, fallback to standard
        if engine == "neural":
            logger.info("falling_back_to_standard_engine", original_error=str(exc))
            try:
                audio_response, marks_response = _synthesize("standard")
                used_engine = "standard"
            except (BotoCoreError, ClientError) as exc2:
                logger.error("polly_standard_fallback_failed", error=str(exc2), voice_id=voice_id)
                raise RuntimeError(f"Polly synthesis failed: {str(exc2)}") from exc2
        else:
            logger.error("polly_synthesis_failed", error=str(exc), voice_id=voice_id, engine=engine)
            raise RuntimeError(f"Polly synthesis failed: {str(exc)}") from exc

    # Extract audio stream
    audio_stream = audio_response.get("AudioStream")
    if not audio_stream:
        raise RuntimeError("Missing audio stream from Polly response")

    # Extract marks stream
    marks_stream = marks_response.get("AudioStream")

    # Read audio data
    try:
        audio_bytes = audio_stream.read()
        if not audio_bytes:
            raise RuntimeError("Empty audio stream from Polly")
        logger.info("audio_synthesized", size_bytes=len(audio_bytes))
    except Exception as exc:
        logger.error("failed_to_read_audio_stream", error=str(exc))
        raise RuntimeError("Failed to read audio stream") from exc
    finally:
        try:
            audio_stream.close()
        except Exception:
            pass

    # Read marks data
    marks_bytes = b""
    if marks_stream:
        try:
            marks_bytes = marks_stream.read()
            logger.debug("marks_read", size_bytes=len(marks_bytes))
        except Exception as exc:
            logger.warning("failed_to_read_marks_stream", error=str(exc))
        finally:
            try:
                marks_stream.close()
            except Exception:
                pass

    # Parse speech marks
    marks = _parse_speech_marks(marks_bytes)
    
    # Validate we got some marks
    if not marks and len(text.split()) > 0:
        logger.warning("no_speech_marks_generated", text_length=len(text))
        # Create simple marks based on words
        words = text.split()
        estimated_duration_ms = len(words) * 400  # ~400ms per word
        marks = [
            {"word": word, "time": int(i * estimated_duration_ms / len(words))}
            for i, word in enumerate(words)
        ]

    result = {
        "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
        "word_marks": marks,
        "voice_id": voice_id,
        "engine": used_engine,
        "language_code": language_code,
    }
    
    logger.info(
        "synthesis_completed",
        voice_id=voice_id,
        engine=used_engine,
        audio_size=len(audio_bytes),
        word_count=len(marks)
    )
    
    return result
