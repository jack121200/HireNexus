from __future__ import annotations

import asyncio
import contextlib
import json
from typing import Any, Awaitable, Callable

from redis.asyncio import Redis

from app.core.logging import get_logger


logger = get_logger(__name__)

MessageHandler = Callable[[str, dict[str, Any]], Awaitable[None]]


class RedisPubSubManager:
    def __init__(self, redis_url: str, *, handler: MessageHandler) -> None:
        self.redis = Redis.from_url(redis_url, decode_responses=True)
        self.handler = handler
        self._listener_task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    async def publish(self, *, channel: str, payload: dict[str, Any]) -> None:
        message = json.dumps(payload, separators=(",", ":"))
        await self.redis.publish(channel, message)

    async def start(self) -> None:
        if self._listener_task and not self._listener_task.done():
            return
        self._stop_event.clear()
        self._listener_task = asyncio.create_task(self._listen(), name="redis-pubsub-listener")
        logger.info("redis_listener_started")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._listener_task:
            self._listener_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._listener_task
        await self.redis.close()
        logger.info("redis_listener_stopped")

    async def _listen(self) -> None:
        pubsub = self.redis.pubsub()
        await pubsub.psubscribe("user:*", "conversation:*")

        try:
            while not self._stop_event.is_set():
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if not message:
                    await asyncio.sleep(0.05)
                    continue

                channel = message.get("channel")
                data = message.get("data")
                if not channel or not data:
                    continue

                try:
                    payload = json.loads(data)
                except json.JSONDecodeError:
                    logger.warning("redis_invalid_payload", channel=channel)
                    continue

                await self.handler(channel, payload)
        finally:
            await pubsub.close()
