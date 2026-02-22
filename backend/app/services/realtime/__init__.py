from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.realtime.redis_pubsub import RedisPubSubManager
from app.services.realtime.ws_manager import WebSocketManager, conversation_channel, user_channel


settings = get_settings()
logger = get_logger(__name__)

ws_manager = WebSocketManager()
redis_manager = RedisPubSubManager(settings.redis_url, handler=ws_manager.handle_pubsub_message)
_redis_enabled = True


async def start_realtime() -> None:
    global _redis_enabled
    try:
        await redis_manager.start()
        _redis_enabled = True
    except Exception as exc:  # noqa: BLE001 - realtime must never block app startup
        _redis_enabled = False
        logger.warning("realtime_start_failed", error=str(exc))
    logger.info("realtime_started", worker_id=ws_manager.worker_id, redis_enabled=_redis_enabled)


async def stop_realtime() -> None:
    try:
        if _redis_enabled:
            await redis_manager.stop()
    except Exception as exc:  # noqa: BLE001
        logger.warning("realtime_stop_failed", error=str(exc))
    logger.info("realtime_stopped", worker_id=ws_manager.worker_id, redis_enabled=_redis_enabled)


async def broadcast_user(*, user_id: int, event: str, data: dict[str, Any]) -> None:
    payload = ws_manager.attach_worker_metadata({"event": event, "data": data})
    await ws_manager.send_user_local(user_id=user_id, payload=payload)
    if _redis_enabled:
        try:
            await redis_manager.publish(channel=user_channel(user_id), payload=payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning("redis_publish_failed", channel=user_channel(user_id), error=str(exc))


async def broadcast_conversation(*, conversation_id: int, event: str, data: dict[str, Any]) -> None:
    payload = ws_manager.attach_worker_metadata({"event": event, "data": data})
    await ws_manager.send_conversation_local(conversation_id=conversation_id, payload=payload)
    if _redis_enabled:
        try:
            await redis_manager.publish(channel=conversation_channel(conversation_id), payload=payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "redis_publish_failed",
                channel=conversation_channel(conversation_id),
                error=str(exc),
            )
