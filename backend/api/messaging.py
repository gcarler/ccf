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
   bandeja ``/plataforma/messages`` (ruta canónica unificada) y el sidebar CRM de la persona.
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

Rutas de compatibilidad (redirect 307):
  - ``/plataforma/inbox/messages`` → ``/plataforma/messages``
  - ``/plataforma/community/messages`` → ``/plataforma/messages``
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

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
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
from backend.crud._utils import _coerce_uuid_or_404
from backend.crud.crm import get_user_sede_id, resolve_persona_id_for_user
from backend.mesh_websockets import manager
from backend.schemas.notifications import MessagingChannel
from backend.services.messaging import CommunicationOutcome

# M-04: Allowlist de patrones de room name válidos.
# ``room_*`` fue removido de la allowlist (fail-closed): ningún endpoint lo
# emite hoy y no tiene un guard de participación, por lo que hubiera sido un
# canal cross-sede sin autorización.
_VALID_ROOM_RE = re.compile(
    r"^(global|project_[0-9a-f-]{36}|dm_[0-9a-f-]{36}|general|staff)$",
    re.IGNORECASE,
)

# Límite de tamaño por frame de texto enviado por el cliente WS (bytes).
_WS_MAX_TEXT_BYTES = 64 * 1024

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
    channel: MessagingChannel
    content: str


router = APIRouter()


def _resolve_project_access(db: Session, current_user: models.User, actor_sede: object | None, project_id: _uuid.UUID) -> bool:
    """Return True if the actor may access the project room (Axioma 3).

    Mirrors ``projects._ensure_project`` + ``_is_assigned_to_project`` so the
    realtime channel cannot bypass the sede/assignment guards enforced by the
    HTTP project routes. The actor must be the project owner or the assignee
    of at least one non-deleted task, and the project must belong to the
    actor's sede (superadmin with no sede bypasses scope).
    """
    project = (
        db.query(models.Project)
        .filter(models.Project.id == project_id, models.Project.deleted_at.is_(None))
        .first()
    )
    if project is None:
        return False
    # Axioma 3 strict scope: projects with NULL sede_id are hidden from
    # seated actors, mirroring ``_ensure_project``.
    if actor_sede is not None:
        if project.sede_id is None or str(project.sede_id) != str(actor_sede):
            return False
    persona_id = resolve_persona_id_for_user(db, current_user.id)
    if persona_id is None:
        return False
    if project.owner_id is not None and str(project.owner_id) == str(persona_id):
        return True
    task = (
        db.query(models.ProjectTask.id)
        .filter(
            models.ProjectTask.project_id == project_id,
            models.ProjectTask.assignee_id == persona_id,
            models.ProjectTask.deleted_at.is_(None),
        )
        .first()
    )
    return task is not None


def _authorize_requested_rooms(db: Session, current_user: models.User, raw_rooms: list[str]) -> list[str]:
    """Return only rooms the authenticated user may subscribe to.

    Generic workspace rooms remain governed by the module permission checked by
    the WebSocket handler. Direct-message rooms require an explicit
    ``ConversationParticipant`` row so knowing a conversation UUID is never
    enough to receive its events. Project rooms require project ownership or
    task assignment within the actor's sede (same guard as the HTTP project
    routes), so an editor from sede A cannot subscribe to a ``project_*`` room
    of sede B.
    """
    authorized: list[str] = []
    actor_sede = get_user_sede_id(db, current_user.id)
    for raw_room in raw_rooms:
        room = raw_room.strip()
        if not room or not _VALID_ROOM_RE.match(room):
            continue
        if room.lower().startswith("project_"):
            try:
                project_id = _uuid.UUID(room[len("project_") :])
            except (TypeError, ValueError):
                continue
            if not _resolve_project_access(db, current_user, actor_sede, project_id):
                continue
            authorized.append(room)
            continue
        if room.lower().startswith("dm_"):
            try:
                conversation_id = _uuid.UUID(room[3:])
            except (TypeError, ValueError):
                continue
            participant = (
                db.query(models.ConversationParticipant.id)
                .filter(
                    models.ConversationParticipant.conversation_id == conversation_id,
                    models.ConversationParticipant.user_id == current_user.id,
                )
                .first()
            )
            if participant is None:
                continue

            # Keep realtime isolation consistent with the HTTP chat guards:
            # inherited conversations containing participants from another
            # sede must not become reachable through the room transport.
            if actor_sede is not None:
                participant_user_ids = [
                    user_id
                    for (user_id,) in db.query(models.ConversationParticipant.user_id)
                    .filter(models.ConversationParticipant.conversation_id == conversation_id)
                    .all()
                    if user_id is not None
                ]
                participant_sede_rows = (
                    db.query(models.Persona.id, models.Persona.sede_id)
                    .filter(models.Persona.id.in_(participant_user_ids))
                    .all()
                    if participant_user_ids
                    else []
                )
                participant_sedes = {str(persona_id): sede_id for persona_id, sede_id in participant_sede_rows}
                # Fail closed for inherited/corrupt rows: every participant
                # must resolve to a Persona with an assigned sede, and all
                # resolved sedes must match the actor's tenant.
                if any(
                    str(participant_id) not in participant_sedes
                    or participant_sedes[str(participant_id)] is None
                    or str(participant_sedes[str(participant_id)]) != str(actor_sede)
                    for participant_id in participant_user_ids
                ):
                    continue
        authorized.append(room)
    return authorized


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

        rooms_param = websocket.query_params.get("rooms")
        raw_rooms = rooms_param.split(",") if rooms_param is not None else None
        # M-04 + BOLA defense: validate names and authorize every private DM
        # and project room. A connection without an explicit room is rejected:
        # broadcasting with ``room=None`` would fan out to EVERY client of ALL
        # instances (mesh_websockets._send_local), a cross-tenant amplifier.
        if not raw_rooms:
            await websocket.close(code=4003, reason="No rooms requested")
            return
        rooms = _authorize_requested_rooms(_db, _user, raw_rooms)
        if not rooms:
            await websocket.close(code=4003, reason="No authorized rooms")
            return
    finally:
        _db.close()
    await manager.connect(client_id, websocket, rooms=rooms)
    try:
        while True:
            data = await websocket.receive_text()
            if len(data.encode("utf-8")) > _WS_MAX_TEXT_BYTES:
                await websocket.close(code=1009, reason="Message too large")
                return
            await manager.broadcast_event(
                {"event": "message", "client": client_id, "data": data},
                room=rooms[0],
            )
    except WebSocketDisconnect:
        pass
    except Exception:  # pragma: no cover - defensive cleanup for any receive error
        pass
    finally:
        # Single cleanup path: also covers timeouts/protocol errors so stale
        # connections never linger in active_connections/rooms (presence).
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

    Private DM rooms are subject to the same participant and tenant guard as
    the WebSocket handshake. A room UUID is an address, never an authorization
    primitive; unauthorized callers receive a neutral 404.
    """
    room = room.strip()
    if not _VALID_ROOM_RE.match(room):
        raise HTTPException(status_code=404, detail="Room not found")
    if room.startswith("dm_") or room.startswith("project_"):
        if not _authorize_requested_rooms(db, current_user, [room]):
            raise HTTPException(status_code=404, detail="Room not found")

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
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("messaging", "read")),
):
    """Broadcast de evento en tiempo real a una room autorizada.

    M-05: rate limit de 10 eventos/minuto/usuario. Exceso → 429.
    El evento se publica vía Redis pub/sub a todas las instancias.

    Seguridad (broadcast hardening):
      - ``payload.room`` es obligatorio (se rechaza el broadcast global
        implícito con ``room=None`` que llegaba a TODOS los clientes de todas
        las instancias).
      - El room debe pasar la allowlist (M-04) y, si es privado
        (``dm_*``/``project_*``), la misma autorización de participación que el
        handshake WS. Así un usuario con ``messaging:read`` no puede inyectar
        eventos falsos en conversaciones o proyectos ajenos (spoofing
        realtime cross-sede).
    """
    if not payload.room:
        raise HTTPException(status_code=422, detail="room is required")
    room = payload.room.strip()
    if not _VALID_ROOM_RE.match(room):
        raise HTTPException(status_code=422, detail="Invalid room")
    authorized = _authorize_requested_rooms(db, current_user, [room])
    if room not in authorized:
        raise HTTPException(status_code=404, detail="Room not found")

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
    await manager.broadcast_event({"event": payload.event, "body": payload.body}, room=room)
    return {"status": "queued"}


@router.get("/messaging/notifications", response_model=List[schemas.Notification])
def get_notifications(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
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
    # Un ``notification_id`` malformado se rechaza antes de tocar la DB
    # (evita un 500 por DataError de UUID en PostgreSQL).
    _coerce_uuid_or_404(notification_id, detail="Notification not found")
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
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
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
