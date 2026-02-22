from __future__ import annotations

import asyncio
import json
import uuid
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from fastapi import WebSocket

from app.core.logging import get_logger


logger = get_logger(__name__)


def user_channel(user_id: int) -> str:
    return f"user:{user_id}"


def conversation_channel(conversation_id: int) -> str:
    return f"conversation:{conversation_id}"


class WebSocketManager:
    """Tracks active WebSocket connections and delivers local broadcasts."""

    def __init__(self) -> None:
        self.worker_id = str(uuid.uuid4())
        self._user_connections: dict[int, set[WebSocket]] = defaultdict(set)
        self._conversation_connections: dict[int, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect_user(self, *, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._user_connections[user_id].add(websocket)
        logger.info("ws_connect_user", user_id=user_id)

    async def disconnect_user(self, *, user_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            self._user_connections[user_id].discard(websocket)
        logger.info("ws_disconnect_user", user_id=user_id)

    async def connect_conversation(self, *, conversation_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._conversation_connections[conversation_id].add(websocket)
        logger.info("ws_connect_conversation", conversation_id=conversation_id)

    async def disconnect_conversation(self, *, conversation_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            self._conversation_connections[conversation_id].discard(websocket)
        logger.info("ws_disconnect_conversation", conversation_id=conversation_id)

    async def _send_many(self, sockets: Iterable[WebSocket], payload: dict[str, Any]) -> None:
        to_remove: list[WebSocket] = []
        for socket in sockets:
            try:
                await socket.send_json(payload)
            except Exception:  # noqa: BLE001 - connection may already be closed
                to_remove.append(socket)
        if to_remove:
            logger.info("ws_cleanup", count=len(to_remove))

    async def send_user_local(self, *, user_id: int, payload: dict[str, Any]) -> None:
        async with self._lock:
            sockets = list(self._user_connections.get(user_id, set()))
        if sockets:
            await self._send_many(sockets, payload)

    async def send_conversation_local(self, *, conversation_id: int, payload: dict[str, Any]) -> None:
        async with self._lock:
            sockets = list(self._conversation_connections.get(conversation_id, set()))
        if sockets:
            await self._send_many(sockets, payload)

    async def handle_pubsub_message(self, *, channel: str, payload: dict[str, Any]) -> None:
        # Prevent echoing messages originating from this worker.
        if payload.get("_worker_id") == self.worker_id:
            return

        if channel.startswith("user:"):
            user_id = int(channel.split(":", maxsplit=1)[1])
            await self.send_user_local(user_id=user_id, payload=payload)
            return

        if channel.startswith("conversation:"):
            conversation_id = int(channel.split(":", maxsplit=1)[1])
            await self.send_conversation_local(conversation_id=conversation_id, payload=payload)
            return

        logger.warning("ws_unknown_channel", channel=channel)

    def attach_worker_metadata(self, payload: dict[str, Any]) -> dict[str, Any]:
        enriched = dict(payload)
        enriched["_worker_id"] = self.worker_id
        return enriched

    @staticmethod
    def encode(payload: dict[str, Any]) -> str:
        return json.dumps(payload, separators=(",", ":"))

    @staticmethod
    def decode(payload: str) -> dict[str, Any]:
        return json.loads(payload)