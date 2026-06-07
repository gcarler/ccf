from typing import List, Optional

from fastapi import (APIRouter, Depends, HTTPException, WebSocket,
                     WebSocketDisconnect)
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.auth import require_module_access, require_staff_or_admin
from backend.core.database import get_db
from backend.mesh_websockets import manager
from backend.crud.crm import resolve_persona_id_for_user


class NotificationPayload(BaseModel):
    event: str
    body: dict
    room: Optional[str] = None


class MessageSendPayload(BaseModel):
    persona_id: str
    channel: str
    content: str


router = APIRouter()


@router.websocket("/messaging/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    rooms_param = websocket.query_params.get("rooms")
    rooms = rooms_param.split(",") if rooms_param else None
    await manager.connect(client_id, websocket, rooms=rooms)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast_event(
                {"event": "message", "client": client_id, "data": data},
                room=rooms[0] if rooms else None,
            )
    except WebSocketDisconnect:
        await manager.disconnect(client_id)


@router.get("/messaging/presence/{room}")
async def get_room_presence(
    room: str, current_user: models.User = Depends(require_module_access("messaging", "read"))
):
    return {"room": room, "clients": manager.list_room(room)}


@router.post("/messaging/notifications")
async def send_notification(
    payload: NotificationPayload,
    current_user: models.User = Depends(require_module_access("messaging", "read")),
):
    await manager.broadcast_event(
        {"event": payload.event, "body": payload.body}, room=payload.room
    )
    return {"status": "queued"}


@router.get("/messaging/notifications", response_model=List[schemas.Notification])
def get_notifications(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("messaging", "read")),
):
    user_id = resolve_persona_id_for_user(db, getattr(current_user, "id", None))
    if user_id is None:
        return []
    return crud.get_user_notifications(
        db, user_id=user_id, limit=limit
    )


@router.patch(
    "/messaging/notifications/{notification_id}", response_model=schemas.Notification
)
def update_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("messaging", "read")),
):
    updated = crud.mark_notification_as_read(db, notification_id=notification_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Notification not found")
    return updated


@router.post("/messaging/notifications/mark-all-read")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("messaging", "read")),
):
    user_id = resolve_persona_id_for_user(db, getattr(current_user, "id", None))
    if user_id is not None:
        crud.mark_all_notifications_read(db, user_id=user_id)
    return {"status": "success"}


@router.get("/messaging/history", response_model=List[schemas.CommunicationLog])
def messaging_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    return crud.get_communication_logs(db, limit=limit)


@router.post("/messaging/send", response_model=schemas.CommunicationLog)
def messaging_send(
    payload: MessageSendPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    # This now calls the updated CRUD which triggers the MessagingService
    entry = crud.create_communication_log(
        db,
        schemas.CommunicationLogCreate(
            persona_id=payload.persona_id,
            channel=payload.channel,
            content=payload.content,
            leader_id=resolve_persona_id_for_user(db, getattr(current_user, "id", None))
            or getattr(current_user, "id", None),
            outcome="sent",
        ),
    )
    return entry
