"""Mensajería interna, notificaciones y broadcast en tiempo real.

Este módulo expone el router ``/api/messaging/*`` agrupado bajo tres categorías
 funcionales, NO canónicas para outbound:

1. **Real-time + presencia** — ``GET /messaging/ws/{client_id}`` (WebSocket),
   ``GET /messaging/presence/{room}`` y ``POST /messaging/notifications``
   (broadcast push al mesh). Auth: ``require_module_access("messaging","read")``.
   Rate limit: 10 broadcasts/usuario/minuto. Room names validados contra allowlist.

2. **Bandeja de notificaciones por usuario** — ``GET /messaging/notifications``,
   ``PATCH /messaging/notifications/{id}`` y
   ``POST /messaging/notifications/mark-all-read``. Modelo: ``Notification``
   (alimentada por eventos del sistema, no por envíos ministeriales).
   Auth: ``require_module_access("messaging","read")`` (scope per-user —
   cada usuario ve sólo su propia bandeja). Soporta ``offset`` para paginación.

3. **Chat interno (inbox app)** — ``GET /messaging/history`` y
   ``POST /messaging/send``. Modela un hilo conversacional dentro de la
   plataforma con ``channel='internal'`` en ``CommunicationLog``. Soporta la
   bandeja ``/plataforma/inbox/messages`` y el sidebar CRM de la persona.
   Auth: ``require_staff_or_admin``. Soporta ``offset`` para paginación.

Seguridad (Fase 1 de auditoría):
  - **C-03**: WebSocket valida permisos ``messaging:read`` antes de conectar.
  - **C-04**: ``presence_join`` sincronizado cross-instancia vía Redis.
  - **C-05**: ``POST /crm/messaging/send`` valida sede del destinatario.
  - **A-01**: ``GET /messaging/presence/{room}`` enriquece client_id → persona_id.
  - **A-06**: ``POST /notifications/mark-all-read`` retorna ``marked_count``.
  - **M-04**: Room names validados contra allowlist (``global``, ``project_{uuid}``,
    ``dm_{uuid}``, ``general``, ``staff``).
  - **M-05**: Rate limit en ``POST /messaging/notifications`` (10/min/usuario).

Multi-Tenant (Axioma 3):
  - ``GET /messaging/history`` filtra por ``Persona.sede_id == user_sede``.
  - ``POST /messaging/send`` rechaza 404 si ``persona_id`` es cross-sede.
  - ``PATCH /notifications/{id}`` requiere ownership (BOLA-style leak prevention).

Notas operativas:
  - **Sin outbound**: este router no envía WhatsApp/SMS/Email. Ver
    ``backend.services.messaging.MessagingGateway`` para outbound real.
  - **Outcome ``"sent"`` es sentinela histórica**: significa "registrado en
    CommunicationLog", **no** "entregado al destinatario externo".
"""

import re
import time
import uuid as _uuid
from collections import defaultdict
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from jose import jwt as _jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api.crm._shared import _get_scoped_persona
from backend.core.database import get_db
from backend.core.permissions import (
    ALGORITHM,
    SECRET_KEY,
    check_ws_module_access,
    require_module_access,
    require_staff_or_admin,
)
from backend.crud.crm import get_user_sede_id, resolve_persona_id_for_user
from backend.mesh_websockets import manager
from backend.services.messaging import CommunicationOutcome

# M-04: Allowlist de patrones de room name válidos.
_VALID_ROOM_RE = re.compile(
    r"^(global|project_[0-9a-f-]{36}|dm_[0-9a-f-]{36}|room_[0-9a-f-]{36}|general|staff)$",
    re.IGNORECASE,
)

# M-05: Rate limit en memoria por usuario (broadcast notifications).
_broadcast_rate: dict[str, list[float]] = defaultdict(list)
_BROADCAST_RATE_LIMIT = 10  # max events por ventana
_BROADCAST_RATE_WINDOW = 60.0  # segundos


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
    """WebSocket endpoint para comunicación en tiempo real.

    Autenticación: requiere ``token`` JWT en query params. Valida:
      1. Token presente y decodificable (4001 si falla).
      2. ``sub`` (user ID) no vacío (4001 si falla).
      3. Usuario existe y está activo (4003 si falla).
      4. Permiso ``messaging:read`` del módulo (4003 si falla, C-03).

    Room names: validados contra allowlist (M-04). Patrones válidos:
    ``global``, ``project_{uuid}``, ``dm_{uuid}``, ``general``, ``staff``.

    Post-conexión: el cliente puede enviar mensajes de texto que se
    broadcastean a la room asignada.
    """
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
    # C-03: Validar permiso messaging:read del módulo.
    from sqlalchemy.orm import Session as _Session

    from backend.core.database import SessionLocal

    _db: _Session = SessionLocal()
    try:
        _user = _db.query(models.User).filter(models.User.id == subject).first()
        if not _user or not _user.is_active:
            await websocket.close(code=4003, reason="User not found or inactive")
            return
        if not check_ws_module_access(_db, _user, "messaging", "read"):
            await websocket.close(code=4003, reason="Insufficient permissions")
            return
    finally:
        _db.close()
    rooms_param = websocket.query_params.get("rooms")
    raw_rooms = rooms_param.split(",") if rooms_param else None
    # M-04: Validate room names against allowlist.
    rooms = None
    if raw_rooms:
        rooms = []
        for r in raw_rooms:
            r = r.strip()
            if r and _VALID_ROOM_RE.match(r):
                rooms.append(r)
        rooms = rooms or None
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
    room: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("messaging", "read")),
):
    """Lista clientes conectados en una room con resolución de identidad.

    A-01: cada ``client_id`` se resuelve a ``persona_id`` consultando la
    tabla ``Personas``. Client IDs no-UUID o inexistentes retornan
    ``persona_id: null``. Non-UUID client IDs (ej. ``"client-a"``) se
    retornan sin resolver.
    """
    # A-01: Return enriched client list with persona_id when resolvable.
    # client_id in mesh_websockets is an opaque UUID string provided by
    # the frontend — it does NOT correspond to a User/Usuario column.
    # We attempt to resolve it via the Persona table (which is the kernel
    # entity and does have an `id` that matches the client_id).
    clients = manager.list_room(room)
    enriched = []
    for client_id in clients:
        persona_id = None
        try:
            parsed = _uuid.UUID(str(client_id))
            persona = db.query(models.Persona).filter(models.Persona.id == parsed).first()
            if persona:
                persona_id = str(persona.id)
        except (ValueError, TypeError):
            pass
        enriched.append(
            {
                "client_id": client_id,
                "persona_id": persona_id,
            }
        )
    return {"room": room, "clients": enriched}


@router.post("/messaging/notifications")
async def send_notification(
    payload: NotificationPayload,
    current_user: models.User = Depends(require_module_access("messaging", "read")),
):
    """Broadcast de evento en tiempo real a una room (o todas las rooms).

    M-05: rate limit de 10 eventos/minuto/usuario. Exceso → 429.
    El evento se publica vía Redis pub/sub a todas las instancias.
    """
    # M-05: Rate limit por usuario para broadcast.
    user_id = str(getattr(current_user, "id", ""))
    now = time.time()
    window_start = now - _BROADCAST_RATE_WINDOW
    _broadcast_rate[user_id] = [t for t in _broadcast_rate[user_id] if t > window_start]
    if len(_broadcast_rate[user_id]) >= _BROADCAST_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded for broadcast notifications",
        )
    _broadcast_rate[user_id].append(now)
    await manager.broadcast_event({"event": payload.event, "body": payload.body}, room=payload.room)
    return {"status": "queued"}


@router.get("/messaging/notifications", response_model=List[schemas.Notification])
def get_notifications(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("messaging", "read")),
):
    """Bandeja de notificaciones del usuario actual.

    M-01: soporta paginación ``offset``/``limit``.
    Cada usuario ve SÓLO sus propias notificaciones (ownership via
    ``resolve_persona_id_for_user``).
    """
    persona_id = resolve_persona_id_for_user(db, getattr(current_user, "id", None))
    if persona_id is None:
        return []
    return crud.get_user_notifications(db, user_id=persona_id, limit=limit, offset=offset)


@router.patch("/messaging/notifications/{notification_id}", response_model=schemas.Notification)
def update_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("messaging", "read")),
):
    """Marca una notificación como leída.

    Axioma 3 ownership: el caller sólo puede marcar SUS PROPIAS
    notifications. Si ``notification_id`` no pertenece al caller o no
    existe, retorna 404 (existence-leak safe, BOLA-style).
    """
    # Axioma 3 — ownership (defense-in-depth): el caller SÓLO puede marcar
    # como leídas SUS PROPIAS notifications. BOLA-style leak prevention:
    # sin este check, cualquier usuario con ``require_module_access``
    # podría PATCH notifications ajenas adivinando UUIDs. 404 (no 403,
    # no 200) para evitar existence leaks. Notification.user_id == Persona.id
    # (via Usuario), por eso resolvemos persona_id del current_user.
    current_persona_id = resolve_persona_id_for_user(db, getattr(current_user, "id", None))
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
    """Marca todas las notificaciones no leídas del usuario como leídas.

    A-06: retorna ``{"marked_count": N}`` con el número de notificaciones
    actualizadas.
    """
    persona_id = resolve_persona_id_for_user(db, getattr(current_user, "id", None))
    if persona_id is not None:
        count = crud.mark_all_notifications_read(db, user_id=persona_id)
    else:
        count = 0
    return {"marked_count": count}


@router.get("/messaging/history", response_model=List[schemas.CommunicationLog])
def messaging_history(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    """Historial de comunicaciones internas filtrado por sede.

    M-02: soporta paginación ``offset``/``limit``.
    Axioma 3: filtra por ``Persona.sede_id == user_sede`` vía JOIN.
    Staff sin sede (superadmin) ven el log global. Soft-deleted logs
    excluidos (C-02).
    """
    # Axioma 3 — Multi-Tenant: el historial se filtra por sede del staff.
    # CommunicationLog NO tiene sede_id propio; el scope se aplica vía JOIN
    # con Persona (FK persona_id). Staff sin sede (superadmin) ven el log
    # global. Defense-in-depth contra cross-sede leak: un staff de sede_a
    # NO puede leer logs de comunicación de personas de sede_b. Para
    # historia filtrada por persona, usar /api/crm/messaging/history.
    user_sede = get_user_sede_id(db, current_user.id)
    return crud.get_communication_logs(db, limit=limit, offset=offset, sede_id=user_sede)


@router.post("/messaging/send", response_model=schemas.CommunicationLog)
def messaging_send(
    payload: MessageSendPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    """Registra un mensaje interno en CommunicationLog.

    Axioma 3 defense-in-depth:
      1. API layer: ``_get_scoped_persona`` valida sede del destinatario.
      2. CRUD layer: ``create_communication_log`` re-valida ``persona_id``.

    No dispara gateway de outbound (WhatsApp/SMS/Email).
    Outcome fijo: ``"internal_log"``.
    """
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
