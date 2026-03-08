from typing import Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from backend.auth import require_active_user
from backend import models
from backend.mesh_websockets import manager


class NotificationPayload(BaseModel):
    event: str
    body: dict
    room: Optional[str] = None


router = APIRouter()


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    rooms_param = websocket.query_params.get("rooms")
    rooms = rooms_param.split(",") if rooms_param else None
    await manager.connect(client_id, websocket, rooms=rooms)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast_event({"event": "message", "client": client_id, "data": data}, room=rooms[0] if rooms else None)
    except WebSocketDisconnect:
        await manager.disconnect(client_id)


@router.get("/messaging/presence/{room}")
async def get_room_presence(room: str, current_user: models.User = Depends(require_active_user)):
    return {"room": room, "clients": manager.list_room(room)}


@router.post("/messaging/notifications")
async def send_notification(
    payload: NotificationPayload,
    current_user: models.User = Depends(require_active_user),
):
    await manager.broadcast_event({"event": payload.event, "body": payload.body}, room=payload.room)
    return {"status": "queued"}
