# file name is ws.py
from __future__ import annotations

import asyncio
import json

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
            audio_chunks_sent = 0
            try:
                while True:
                    message = await websocket.receive()
                    
                    if message.get("type") == "websocket.disconnect":
                        logger.info("client_disconnected", user_id=user.id, chunks_sent=audio_chunks_sent)
                        break
                    
                    if message.get("bytes"):
                        # Send raw PCM bytes to AssemblyAI
                        try:
                            await stt_socket.send(message["bytes"])
                            audio_chunks_sent += 1
                            
                            # Log progress periodically
                            if audio_chunks_sent % 100 == 0:
                                logger.debug("audio_chunks_sent", user_id=user.id, count=audio_chunks_sent)
                        except Exception as exc:
                            logger.error("failed_to_send_audio", user_id=user.id, error=str(exc))
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
                logger.info("client_to_stt_ended", user_id=user.id, total_chunks=audio_chunks_sent)

        async def _stt_to_client() -> None:
            """Forward transcription from STT service to client."""
            transcripts_received = 0
            try:
                async for message in stt_socket:
                    try:
                        data = json.loads(message)
                    except json.JSONDecodeError:
                        logger.warning("invalid_stt_message", user_id=user.id)
                        continue
                    
                    msg_type = data.get("message_type") or data.get("type")
                    
                    if msg_type == "PartialTranscript":
                        text = data.get("text", "").strip()
                        if text:
                            await websocket.send_json({"event": "stt.partial", "text": text})
                            
                    elif msg_type == "FinalTranscript":
                        text = data.get("text", "").strip()
                        if text:
                            await websocket.send_json({"event": "stt.final", "text": text})
                            transcripts_received += 1
                            logger.debug("final_transcript", user_id=user.id, text=text[:50])
                            
                    elif msg_type == "Turn":
                        is_final = bool(data.get("is_final"))
                        text = data.get("text", "").strip()
                        if text:
                            event = "stt.final" if is_final else "stt.partial"
                            await websocket.send_json({"event": event, "text": text})
                            if is_final:
                                transcripts_received += 1
                                
                    elif msg_type in {"SessionTerminated", "SessionEnded"}:
                        logger.info("stt_session_ended", user_id=user.id, type=msg_type)
                        break
                        
                    elif msg_type in {"Error", "error"}:
                        error_msg = data.get("message", "Unknown STT error")
                        logger.error("stt_error_message", user_id=user.id, error=error_msg)
                        await websocket.send_json({"event": "stt.error", "message": error_msg})
                        
            except WebSocketDisconnect:
                logger.info("stt_to_client_disconnected", user_id=user.id)
            except WebSocketException as exc:
                logger.error("stt_to_client_ws_error", user_id=user.id, error=str(exc))
            except Exception as exc:
                logger.error("stt_to_client_error", user_id=user.id, error=str(exc))
            finally:
                logger.info("stt_to_client_ended", user_id=user.id, transcripts=transcripts_received)

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
