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
   Auth: ``require_staff_or_admin``. **Axioma 3 aplicado (Fase 3 — API
   Layer + Fase 4 — CRUD Layer)**: ``GET /messaging/history`` filtra los
   logs por ``Persona.sede_id == user_sede`` (vía
   ``crud.get_communication_logs(sede_id=...)``); ``POST /messaging/send``
   rechaza con 404 si el ``persona_id`` pertenece a otra sede (vía
   ``_get_scoped_persona``) Y propaga ``actor_user_id`` al CRUD
   ``create_communication_log``, que re-valida ``persona_id`` en el CRUD
   layer (defense-in-depth, cierra TOCTOU). Staff-admins sin sede
   asignada (superadmin/anterior) ven TODO y pueden postear a cualquier
   persona, consistente con el resto de la plataforma.

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

- **Multi-Tenant (Axioma 3) — APLICADO en ``/messaging/history`` y
  ``/messaging/send``**:

  - ``GET /messaging/history`` filtraba los últimos ``limit`` registros
    globales. Ahora acepta ``sede_id`` opcional y, cuando el caller tiene
    sede asignada (``get_user_sede_id`` retorna string), restringe el
    historial via JOIN con ``Persona.sede_id``. Staff sin sede siguen
    viendo el log global por su alcance administrativo canónico.

  - ``POST /messaging/send`` validaba el cuerpo pero no el target. Ahora
    llama a ``_get_scoped_persona`` antes de crear el log: si el
    ``persona_id`` pertenece a otra sede, devuelve ``404`` (existence-leak
    safe, mismo patrón que el resto del CRM cross-sede). El ``leader_id``
    interno del staff no expone la sede del autor. **Defense-in-depth**:
    además del check API-layer, propaga ``actor_user_id`` al CRUD
    ``create_communication_log``, que re-valida el ``persona_id`` antes
    del ``db.add`` — cierra el TOCTOU gap donde un caller no-API podría
    omitir el check API-layer. El actor canónico es obligatorio.

  - ``PATCH /messaging/notifications/{id}`` validaba cualquier
    ``notification_id``. Ahora requiere ownership: el caller sólo puede
    marcar como leídas sus PROPIAS notifications. BOLA-style leak
    prevention — 404 cross-user (existence-leak safe). Implementado via
    ``owner_persona_id`` en ``crud.mark_notification_as_read``.

  Para historia filtrada por persona, usar ``GET /api/crm/messaging/history``
  (con JOIN sobre ``personas`` y filtro por ``persona_id``/``sede_id``).

- **Broadcast con auth mínima**: ``POST /messaging/notifications`` acepta
  ``event``+``body``+``room`` arbitrarios y los reenvía al mesh WebSocket
  con sólo ``require_module_access("messaging","read")``. La auth existe,
  pero NO hay allowlist de tipos de evento, ni validación de room, ni
  rate limit. Invocar sólo desde flujos internos del backend; exponer de
  forma amplia requiere auth + validación adicionales.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from jose import jwt as _jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api.crm._shared import _get_scoped_persona
from backend.core.database import get_db
from backend.core.permissions import ALGORITHM, SECRET_KEY, require_module_access, require_staff_or_admin
from backend.crud.crm import get_user_sede_id, resolve_persona_id_for_user
from backend.mesh_websockets import manager
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
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return
    try:
        payload_data = _jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        subject = str(payload_data.get("sub") or "")
        if not subject:
            await websocket.close(code=4001, reason="Invalid token")
            return
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return
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
    # Axioma 3 — ownership (defense-in-depth): el caller SÓLO puede marcar
    # como leídas SUS PROPIAS notifications. BOLA-style leak prevention:
    # sin este check, cualquier usuario con ``require_module_access``
    # podría PATCH notifications ajenas adivinando UUIDs. 404 (no 403,
    # no 200) para evitar existence leaks. Notification.user_id == Persona.id
    # (via Usuario), por eso resolvemos persona_id del current_user.
    current_persona_id = resolve_persona_id_for_user(
        db, getattr(current_user, "id", None)
    )
    updated = crud.mark_notification_as_read(
        db,
        notification_id=notification_id,
        owner_persona_id=current_persona_id,
    )
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
    # Axioma 3 — Multi-Tenant: el historial se filtra por sede del staff.
    # CommunicationLog NO tiene sede_id propio; el scope se aplica vía JOIN
    # con Persona (FK persona_id). Staff sin sede (superadmin) ven el log
    # global. Defense-in-depth contra cross-sede leak: un staff de sede_a
    # NO puede leer logs de comunicación de personas de sede_b. Para
    # historia filtrada por persona, usar /api/crm/messaging/history.
    user_sede = get_user_sede_id(db, current_user.id)
    return crud.get_communication_logs(db, limit=limit, sede_id=user_sede)


@router.post("/messaging/send", response_model=schemas.CommunicationLog)
def messaging_send(
    payload: MessageSendPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    # Axioma 3 — Multi-Tenant: el target (persona_id) debe pertenecer a la
    # sede del staff. Defense-in-depth contra escritura cross-sede:
    # un staff de sede_a ya no puede postear logs en CommunicationLog de
    # personas de sede_b. _get_scoped_persona retorna 404 (no 403) para
    # evitar existence-leaks. Ver module docstring para semántica de
    # outcome, ausencia de gateway y referencia canónica.
    _get_scoped_persona(db, current_user, payload.persona_id)
    actor_user_id = current_user.id
    entry = crud.create_communication_log(
        db,
        schemas.CommunicationLogCreate(
            persona_id=payload.persona_id,
            channel=payload.channel,
            content=payload.content,
            leader_id=resolve_persona_id_for_user(db, actor_user_id) or actor_user_id,
            outcome=CommunicationOutcome.INTERNAL_LOG.value,
        ),
        actor_user_id=str(actor_user_id),
    )
    return entry
