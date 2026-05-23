from __future__ import annotations

import json
import logging
from typing import Dict, List

from fastapi import WebSocket

log = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # Maps user_id -> List[WebSocket] (one user can have multiple tabs open)
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        log.info(
            f"User {user_id} connected to WebSocket. Total: {len(self.active_connections[user_id])}"
        )

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        log.info(f"User {user_id} disconnected from WebSocket.")

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            payload = json.dumps(message)
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(payload)
                except Exception as e:
                    log.error(f"Failed to send WS message to {user_id}: {e}")

    async def broadcast(self, message: dict):
        payload = json.dumps(message)
        for connections in self.active_connections.values():
            for connection in connections:
                try:
                    await connection.send_text(payload)
                except Exception:
                    pass


ws_manager = ConnectionManager()
