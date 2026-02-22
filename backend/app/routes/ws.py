# file name is ws.py
from __future__ import annotations

import asyncio
import json
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from websockets import connect as ws_connect
from websockets.exceptions import WebSocketException
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.user import User
from app.services.chat_service import assert_user_in_conversation, get_conversation
from app.services.realtime import ws_manager


router = APIRouter(tags=["websockets"])
logger = get_logger(__name__)


def _authenticate(token: str, db: Session) -> User | None:
    """Authenticate user from token."""
    try:
        payload = decode_token(token)
        user_id = int(payload.get("sub"))
    except Exception as exc:
        logger.warning("auth_failed", error=str(exc))
        return None
    
    user = db.get(User, user_id)
    if not user or not user.verified:
        logger.warning("user_not_found_or_unverified", user_id=user_id)
        return None
    
    return user


def _clean_transcript(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _parse_transcript_event(payload: dict[str, object]) -> tuple[str, str] | None:
    """Map AssemblyAI payloads to frontend transcript events."""
    msg_type = payload.get("message_type") or payload.get("type")
    msg_type_str = str(msg_type) if msg_type is not None else ""

    # AssemblyAI v3 format_turns=true payload shape.
    if msg_type_str == "Turn":
        text = _clean_transcript(payload.get("transcript") or payload.get("text"))
        if not text:
            return None
        is_final = bool(payload.get("end_of_turn"))
        return ("stt.final" if is_final else "stt.partial", text)

    # Backward-compatible payload support.
    if msg_type_str in {"PartialTranscript", "FinalTranscript"}:
        text = _clean_transcript(payload.get("text") or payload.get("transcript"))
        if not text:
            return None
        return ("stt.final" if msg_type_str == "FinalTranscript" else "stt.partial", text)

    return None


@router.websocket("/ws/notifications")
async def notifications_ws(websocket: WebSocket) -> None:
    """WebSocket endpoint for user notifications."""
    token = websocket.query_params.get("token")
    if not token:
        logger.warning("notifications_ws_no_token")
        await websocket.close(code=1008)
        return

    db = SessionLocal()
    user: User | None = None
    try:
        user = _authenticate(token, db)
        if not user:
            await websocket.close(code=1008)
            return

        await ws_manager.connect_user(user_id=user.id, websocket=websocket)
        await websocket.send_json({"event": "ws.connected", "data": {"user_id": user.id}})
        logger.info("notifications_ws_connected", user_id=user.id)

        while True:
            # Keep the connection alive; clients may send pings.
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    except WebSocketDisconnect:
        logger.info("notifications_ws_disconnected", user_id=user.id if user else None)
    except Exception as exc:
        logger.error("notifications_ws_error", user_id=user.id if user else None, error=str(exc))
    finally:
        if user:
            await ws_manager.disconnect_user(user_id=user.id, websocket=websocket)
        db.close()


@router.websocket("/ws/chat/{conversation_id}")
async def chat_ws(websocket: WebSocket, conversation_id: int) -> None:
    """WebSocket endpoint for chat conversations."""
    token = websocket.query_params.get("token")
    if not token:
        logger.warning("chat_ws_no_token", conversation_id=conversation_id)
        await websocket.close(code=1008)
        return

    db = SessionLocal()
    user: User | None = None
    try:
        user = _authenticate(token, db)
        if not user:
            await websocket.close(code=1008)
            return

        try:
            conversation = get_conversation(db, conversation_id=conversation_id)
            assert_user_in_conversation(conversation=conversation, user=user)
        except Exception as exc:
            logger.warning("chat_ws_access_denied", conversation_id=conversation_id, user_id=user.id, error=str(exc))
            await websocket.close(code=1008)
            return

        await ws_manager.connect_conversation(conversation_id=conversation.id, websocket=websocket)
        await websocket.send_json(
            {"event": "ws.connected", "data": {"conversation_id": conversation.id, "user_id": user.id}}
        )
        logger.info("chat_ws_connected", conversation_id=conversation.id, user_id=user.id)

        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    except WebSocketDisconnect:
        logger.info("chat_ws_disconnected", conversation_id=conversation_id, user_id=user.id if user else None)
    except Exception as exc:
        logger.error("chat_ws_error", conversation_id=conversation_id, user_id=user.id if user else None, error=str(exc))
    finally:
        await ws_manager.disconnect_conversation(conversation_id=conversation_id, websocket=websocket)
        db.close()


@router.websocket("/ws/stt")
async def stt_ws(websocket: WebSocket) -> None:
    """WebSocket endpoint for speech-to-text streaming."""
    token = websocket.query_params.get("token")
    if not token:
        logger.warning("stt_ws_no_token")
        await websocket.close(code=1008)
        return

    db = SessionLocal()
    settings = get_settings()
    user: User | None = None
    stt_socket = None

    try:
        user = _authenticate(token, db)
        if not user:
            await websocket.close(code=1008)
            return

        await websocket.accept()
        logger.info("stt_ws_connected", user_id=user.id)

        if not settings.assemblyai_api_key:
            logger.error("stt_not_configured")
            await websocket.send_json({"event": "stt.error", "message": "STT not configured"})
            await websocket.close(code=1011)
            return

        ws_url = (
            f"{settings.assemblyai_realtime_base}"
            f"?sample_rate={settings.assemblyai_sample_rate}"
            f"&format_turns=true"
        )

        try:
            stt_socket = await ws_connect(
                ws_url,
                extra_headers={"Authorization": settings.assemblyai_api_key},
                max_size=2**22,
                ping_interval=20,
                ping_timeout=10,
            )
        except Exception as exc:
            logger.error("stt_connection_failed", user_id=user.id, error=str(exc))
            await websocket.send_json({"event": "stt.error", "message": "Failed to connect to STT service"})
            await websocket.close(code=1011)
            return

        # Wait for AssemblyAI's ready message
        try:
            ready_msg = await asyncio.wait_for(stt_socket.recv(), timeout=5.0)
            logger.info("stt_ready", user_id=user.id, message=ready_msg[:100] if isinstance(ready_msg, str) else "binary")
        except asyncio.TimeoutError:
            logger.error("stt_ready_timeout", user_id=user.id)
            await websocket.send_json({"event": "stt.error", "message": "STT server not ready"})
            return
        except Exception as exc:
            logger.error("stt_ready_error", user_id=user.id, error=str(exc))
            await websocket.send_json({"event": "stt.error", "message": "STT server not ready"})
            return

        await websocket.send_json({"event": "stt.ready"})

        async def _client_to_stt() -> None:
            """Forward audio from client to STT service."""
            bytes_per_second = max(settings.assemblyai_sample_rate * 2, 1)  # 16-bit mono PCM
            min_chunk_ms = max(int(settings.stt_min_chunk_ms), 1)
            max_chunk_ms = max(int(settings.stt_max_chunk_ms), min_chunk_ms)
            target_chunk_ms = max(min(int(settings.stt_forward_chunk_ms), max_chunk_ms), min_chunk_ms)
            flush_interval_secs = max(float(settings.stt_flush_interval_ms) / 1000.0, 0.02)
            min_chunk_bytes = max(int(bytes_per_second * (min_chunk_ms / 1000.0)), 1)
            max_chunk_bytes = max(int(bytes_per_second * (max_chunk_ms / 1000.0)), min_chunk_bytes)
            target_chunk_bytes = max(int(bytes_per_second * (target_chunk_ms / 1000.0)), min_chunk_bytes)

            incoming_frames = 0
            forwarded_chunks = 0
            buffered = bytearray()

            async def _forward_chunk(raw: bytes, *, reason: str) -> bool:
                nonlocal forwarded_chunks
                if not raw:
                    return True
                duration_ms = round((len(raw) / bytes_per_second) * 1000, 2)
                try:
                    await stt_socket.send(raw)
                    forwarded_chunks += 1
                    logger.info(
                        "stt_chunk_forwarded",
                        user_id=user.id,
                        bytes=len(raw),
                        duration_ms=duration_ms,
                        reason=reason,
                    )
                    return True
                except Exception as exc:
                    logger.error("failed_to_send_audio", user_id=user.id, error=str(exc))
                    return False

            async def _flush_buffer(*, reason: str, force: bool = False) -> bool:
                while len(buffered) >= target_chunk_bytes:
                    chunk = bytes(buffered[:target_chunk_bytes])
                    del buffered[:target_chunk_bytes]
                    if not await _forward_chunk(chunk, reason=reason):
                        return False

                if force:
                    while len(buffered) >= min_chunk_bytes:
                        size = min(len(buffered), max_chunk_bytes)
                        chunk = bytes(buffered[:size])
                        del buffered[:size]
                        if not await _forward_chunk(chunk, reason=f"{reason}.force"):
                            return False

                return True

            try:
                while True:
                    try:
                        message = await asyncio.wait_for(websocket.receive(), timeout=flush_interval_secs)
                    except asyncio.TimeoutError:
                        if len(buffered) >= min_chunk_bytes:
                            if not await _flush_buffer(reason="interval", force=True):
                                break
                        continue
                    
                    if message.get("type") == "websocket.disconnect":
                        logger.info("client_disconnected", user_id=user.id, chunks_sent=forwarded_chunks)
                        break
                    
                    if message.get("bytes"):
                        incoming_frames += 1
                        buffered.extend(message["bytes"])
                        if not await _flush_buffer(reason="buffer"):
                            break
                    elif message.get("text"):
                        # Handle control messages
                        try:
                            control = json.loads(message["text"])
                            if control.get("type") == "terminate":
                                logger.info("terminate_requested", user_id=user.id)
                                break
                        except json.JSONDecodeError:
                            # Not JSON, send as-is
                            pass
                        
                        try:
                            await stt_socket.send(message["text"])
                        except Exception as exc:
                            logger.error("failed_to_send_control", user_id=user.id, error=str(exc))
                            
            except WebSocketDisconnect:
                logger.info("client_to_stt_disconnected", user_id=user.id)
            except Exception as exc:
                logger.error("client_to_stt_error", user_id=user.id, error=str(exc))
            finally:
                await _flush_buffer(reason="shutdown", force=True)
                if buffered:
                    dropped_duration_ms = round((len(buffered) / bytes_per_second) * 1000, 2)
                    logger.info(
                        "stt_chunk_dropped_too_small",
                        user_id=user.id,
                        bytes=len(buffered),
                        duration_ms=dropped_duration_ms,
                    )
                    buffered.clear()
                logger.info(
                    "client_to_stt_ended",
                    user_id=user.id,
                    total_chunks=forwarded_chunks,
                    incoming_frames=incoming_frames,
                )

        async def _stt_to_client() -> None:
            """Forward transcription from STT service to client."""
            transcripts_received = 0
            transcripts_forwarded_partial = 0
            transcripts_forwarded_final = 0
            last_unknown_log_at = 0.0
            try:
                async for message in stt_socket:
                    try:
                        data = json.loads(message)
                    except json.JSONDecodeError:
                        logger.warning("invalid_stt_message", user_id=user.id)
                        continue

                    if not isinstance(data, dict):
                        if settings.stt_log_unknown_messages:
                            now = time.monotonic()
                            if now - last_unknown_log_at >= 5.0:
                                last_unknown_log_at = now
                                logger.debug("stt_unknown_message_shape", user_id=user.id, payload_type=type(data).__name__)
                        continue

                    msg_type = data.get("message_type") or data.get("type")
                    msg_type_str = str(msg_type) if msg_type is not None else ""

                    transcript_event = _parse_transcript_event(data)
                    if transcript_event:
                        event, text = transcript_event
                        await websocket.send_json({"event": event, "text": text})
                        if event == "stt.final":
                            transcripts_received += 1
                            transcripts_forwarded_final += 1
                            logger.debug("final_transcript", user_id=user.id, text=text[:80])
                        else:
                            transcripts_forwarded_partial += 1
                        continue

                    if msg_type_str in {"SessionTerminated", "SessionEnded"}:
                        logger.info("stt_session_ended", user_id=user.id, type=msg_type_str)
                        break

                    if msg_type_str.lower() == "error":
                        error_msg = _clean_transcript(data.get("message")) or "Unknown STT error"
                        logger.error("stt_error_message", user_id=user.id, error=error_msg)
                        await websocket.send_json({"event": "stt.error", "message": error_msg})
                        continue

                    if settings.stt_log_unknown_messages:
                        now = time.monotonic()
                        if now - last_unknown_log_at >= 5.0:
                            last_unknown_log_at = now
                            logger.debug(
                                "stt_unknown_message",
                                user_id=user.id,
                                message_type=msg_type_str or None,
                                keys=sorted(str(key) for key in data.keys()),
                            )
                        
            except WebSocketDisconnect:
                logger.info("stt_to_client_disconnected", user_id=user.id)
            except WebSocketException as exc:
                logger.error("stt_to_client_ws_error", user_id=user.id, error=str(exc))
            except Exception as exc:
                logger.error("stt_to_client_error", user_id=user.id, error=str(exc))
            finally:
                logger.info(
                    "stt_to_client_ended",
                    user_id=user.id,
                    transcripts=transcripts_received,
                    transcripts_forwarded_partial=transcripts_forwarded_partial,
                    transcripts_forwarded_final=transcripts_forwarded_final,
                )

        # Run both directions concurrently
        done, pending = await asyncio.wait(
            [
                asyncio.create_task(_client_to_stt()),
                asyncio.create_task(_stt_to_client())
            ],
            return_when=asyncio.FIRST_COMPLETED,
        )
        
        # Cancel remaining tasks
        for task in pending:
            task.cancel()
        
        # Send terminate signal to STT service
        try:
            await asyncio.wait_for(
                stt_socket.send(json.dumps({"terminate_session": True})),
                timeout=2.0
            )
        except Exception:
            pass
        
        # Wait for tasks to finish
        await asyncio.gather(*pending, return_exceptions=True)
        
        logger.info("stt_session_completed", user_id=user.id)
        
    except WebSocketDisconnect:
        logger.info("stt_ws_disconnected", user_id=user.id if user else None)
    except Exception as exc:
        logger.error("stt_ws_failed", user_id=user.id if user else None, error=str(exc), exc_type=type(exc).__name__)
        try:
            await websocket.send_json({"event": "stt.error", "message": "STT session failed"})
        except Exception:
            pass
    finally:
        if stt_socket:
            try:
                await stt_socket.close()
            except Exception:
                pass
        db.close()
