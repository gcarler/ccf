"""Mensajería interna, notificaciones y broadcast en tiempo real.

Este módulo expone el router ``/api/messaging/*`` agrupado bajo tres categorías
funcionales, NO canónicas para outbound:

1. **Real-time + presencia** — ``GET /messaging/ws/{client_id}`` (WebSocket),
   ``GET /messaging/presence/{room}`` y ``POST /messaging/notifications``
   (broadcast push al mesh). Auth: ``require_module_access("messaging","read")``.

2. **Bandeja de notificaciones por usuario** — ``GET /messaging/notifications``,
   ``PATCH /messaging/notifications/{id}`` y
   ``POST /messaging/notifications/mark-all-read``. Modelo: ``Notification``
   (alimentada por eventos del sistema, no por envíos ministeriales).
   Auth: ``require_module_access("messaging","read")`` (scope per-user —
   cada usuario ve sólo su propia bandeja).

3. **Chat interno (inbox app)** — ``GET /messaging/history`` y
   ``POST /messaging/send``. Modela un hilo conversacional dentro de la
   plataforma con ``channel='internal'`` en ``CommunicationLog``. Soporta la
   bandeja ``/plataforma/inbox/messages`` y el sidebar CRM de la persona.
   Auth: ``require_staff_or_admin`` (scope cross-user — staff ve logs
   completos de la plataforma).

Notas operativas:

- **Sin outbound**: este router no envía WhatsApp/SMS/Email. Esas
  comunicaciones se canalizan vía
  ``backend.services.messaging.MessagingGateway`` (real o stub según
  ``settings.stub_comms``) en ``/api/crm/messaging/send`` (alias deprecado:
  ``/api/evangelism/messaging/send``). ``POST /messaging/send`` sólo escribe una
  entrada de ``CommunicationLog`` y **no** dispara gateway.

- **Outcome ``"sent"`` es sentinela histórica**: en este log interno significa
  "registrado en CommunicationLog", **no** "entregado al destinatario externo".
  Reportes agregados por canal pueden sumar ambos tipos (outbound real +
  inbound log interno) — NO usar ``outcome='sent'`` como evidencia de entrega
  outbound. Para outbound real, consultar ``CommunicationLog`` con
  ``outcome in OUTBOUND_OUTCOMES`` (exportado en ``backend.services.messaging``).

- **``GET /messaging/history`` sin filtro por persona/sede**: retorna los
  últimos ``limit`` registros globales. Es staff-only; cualquier staff puede
  leer el log completo de la plataforma. Para historia filtrada por persona,
  usar ``GET /api/crm/messaging/history`` (con JOIN sobre ``personas`` y
  filtro por ``persona_id``/``sede_id``).

- **Multi-Tenant (Axioma 3) no aplicado en este router**: ``POST /messaging/send``
  y ``GET /messaging/history`` no filtran por ``sede_id`` del staff — staff de
  una sede podrían escribir/leer logs de personas de otras sedes. Si Multi-Tenant
  estricto es requerido, agregar ``.filter(Persona.sede_id == staff_sede_id)``
  en ``crud.get_communication_logs`` y propagar ``sede_id`` al insert.

- **Broadcast con auth mínima**: ``POST /messaging/notifications`` acepta
  ``event``+``body``+``room`` arbitrarios y los reenvía al mesh WebSocket
  con sólo ``require_module_access("messaging","read")``. La auth existe,
  pero NO hay allowlist de tipos de evento, ni validación de room, ni
  rate limit. Invocar sólo desde flujos internos del backend; exponer de
  forma amplia requiere auth + validación adicionales.
"""

from typing import List, Optional

from fastapi import (APIRouter, Depends, HTTPException, WebSocket,
                     WebSocketDisconnect)
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.core.permissions import require_module_access, require_staff_or_admin
from backend.core.database import get_db
from backend.mesh_websockets import manager
from backend.crud.crm import resolve_persona_id_for_user
from backend.services.messaging import CommunicationOutcome


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
    persona_id = resolve_persona_id_for_user(db, getattr(current_user, "id", None))
    if persona_id is None:
        return []
    return crud.get_user_notifications(
        db, user_id=persona_id, limit=limit
    )


@router.patch(
    "/messaging/notifications/{notification_id}", response_model=schemas.Notification
)
def update_notification(
    notification_id: str,
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
    persona_id = resolve_persona_id_for_user(db, getattr(current_user, "id", None))
    if persona_id is not None:
        crud.mark_all_notifications_read(db, user_id=persona_id)
    return {"status": "success"}


@router.get("/messaging/history", response_model=List[schemas.CommunicationLog])
def messaging_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    # Sin filtro por persona ni sede — retorna los últimos `limit` registros
    # globales. Para historia filtrada por persona, usar /api/crm/messaging/history.
    return crud.get_communication_logs(db, limit=limit)


@router.post("/messaging/send", response_model=schemas.CommunicationLog)
def messaging_send(
    payload: MessageSendPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    # Riesgo conocido: persona_id NO se valida contra permisos del staff —
    # cualquier staff/admin puede postear como cualquier persona. Tampoco
    # se filtra por sede_id del staff (Axioma 3). Ver module docstring para
    # semántica de outcome, ausencia de gateway y referencia canónica.
    entry = crud.create_communication_log(
        db,
        schemas.CommunicationLogCreate(
            persona_id=payload.persona_id,
            channel=payload.channel,
            content=payload.content,
            leader_id=resolve_persona_id_for_user(db, getattr(current_user, "id", None))
            or getattr(current_user, "id", None),
            outcome=CommunicationOutcome.INTERNAL_LOG.value,
        ),
    )
    return entry
