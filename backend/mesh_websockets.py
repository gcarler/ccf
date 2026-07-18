from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Dict, List, Optional, Set

from fastapi import WebSocket

from backend.core.cache import get_redis
from backend.core.config import get_settings

settings = get_settings()


class RedisPubSubManager:
    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}
        self.rooms: Dict[str, Set[str]] = defaultdict(set)
        self._redis = None
        self.channel = f"{settings.environment}:ws"
        self.listener_task: Optional[asyncio.Task] = None
        self.listener_lock = asyncio.Lock()

    @property
    def redis(self):
        if self._redis is None:
            self._redis = get_redis()
        return self._redis

    async def _ensure_listener(self) -> None:
        if self.listener_task and not self.listener_task.done():
            return
        async with self.listener_lock:
            if self.listener_task and not self.listener_task.done():
                return
            loop = asyncio.get_running_loop()
            self.listener_task = loop.create_task(self._listen_for_events())

    async def _listen_for_events(self) -> None:
        pubsub = getattr(self.redis, "pubsub", None)
        if pubsub is None:
            return
        subscription = pubsub()
        subscription.subscribe(self.channel)
        try:
            while True:
                message = await asyncio.to_thread(
                    subscription.get_message,
                    True,
                    1.0,
                )
                if not message:
                    await asyncio.sleep(0.1)
                    continue
                data = message.get("data")
                if not data:
                    continue
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                try:
                    payload = json.loads(data)
                except json.JSONDecodeError:
                    continue
                await self._dispatch(payload)
        except asyncio.CancelledError:  # pragma: no cover
            subscription.unsubscribe()
            raise

    async def _dispatch(self, payload: dict) -> None:
        event_type = payload.get("type")
        room = payload.get("room")
        if event_type in {"broadcast", "notify"}:
            await self._send_local(payload.get("data"), room=room)
        elif event_type == "presence_leave":
            client_id = payload.get("client_id")
            if client_id:
                self._remove_client(client_id)

    async def connect(
        self, client_id: str, websocket: WebSocket, rooms: Optional[List[str]] = None
    ) -> None:
        await websocket.accept()
        self.active_connections[client_id] = websocket
        for room in rooms or ["global"]:
            self.rooms[room].add(client_id)
        await self._ensure_listener()
        await self._publish(
            {
                "type": "presence_join",
                "client_id": client_id,
                "rooms": rooms or ["global"],
            }
        )

    async def disconnect(self, client_id: str) -> None:
        self._remove_client(client_id)
        await self._publish({"type": "presence_leave", "client_id": client_id})

    def _remove_client(self, client_id: str) -> None:
        self.active_connections.pop(client_id, None)
        for room, participants in list(self.rooms.items()):
            if client_id in participants:
                participants.discard(client_id)
            if not participants:
                self.rooms.pop(room, None)

    async def send_personal_message(self, message: str, client_id: str) -> None:
        connection = self.active_connections.get(client_id)
        if connection:
            await connection.send_text(message)

    async def broadcast(self, message: str, room: Optional[str] = None) -> None:
        payload = {"type": "broadcast", "room": room, "data": message}
        await self._publish(payload)
        await self._send_local(message, room)

    async def broadcast_event(self, event: dict, room: Optional[str] = None) -> None:
        payload = {"type": "notify", "room": room, "data": event}
        await self._publish(payload)
        await self._send_local(event, room)

    async def _send_local(self, data, room: Optional[str] = None) -> None:
        message = data if isinstance(data, str) else json.dumps(data)
        targets = (
            self.rooms.get(room, set()) if room else set(self.active_connections.keys())
        )
        for client_id in targets:
            connection = self.active_connections.get(client_id)
            if not connection:
                continue
            try:
                await connection.send_text(message)
            except Exception:  # pragma: no cover
                self._remove_client(client_id)

    async def _publish(self, payload: dict) -> None:
        await asyncio.to_thread(self.redis.publish, self.channel, json.dumps(payload))

    def list_room(self, room: str) -> List[str]:
        return sorted(self.rooms.get(room, set()))


manager = RedisPubSubManager()
