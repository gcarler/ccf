"""Direct Message endpoints — conversations and private messaging.

Sprint 3 — Axioma 3 defense-in-depth
------------------------------------
- ``_assert_conversation_sede_aligned`` valida que los participantes de
  una Conversation pre-existente estén en la misma ``sede_id`` que el
  actor cuando éste tiene sede asignada. Conversation no tiene
  ``sede_id`` propio: el tenant scope se infiere de la intersección
  de las sedes de sus participantes (validado en ``create_conversation``
  cuando el actor tiene sede, rechaza cross-tenant con 403).
- ``_assert_sender_sede_matches_actor`` complementa al participant
  check en el mutador ``delete_chat_message``. En el flujo canónico es
  tautológico, pero previene sender-id cross-tenant en escenarios
  futuros (bots/forwards, migración de logs creados en el sistema
  anterior donde sender_id era FK integer).
"""

from __future__ import annotations

import json
import logging
import uuid as _uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.crud._utils import _coerce_uuid_or_404
from backend.crud.crm import get_user_sede_id, resolve_persona_id_for_user
from backend.mesh_websockets import manager
from backend.models_shared import _utcnow
from backend.services.comment_notifications import notify_mention

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Helpers de persona ────────────────────────────────────────────────────────


def _get_persona_id(db: Session, current_user: models.User):
    """Resuelve Persona.id (UUID) desde el usuario autenticado."""
    return resolve_persona_id_for_user(db, getattr(current_user, "id", None))


def _get_persona(db: Session, current_user: models.User):
    persona_id = _get_persona_id(db, current_user)
    if not persona_id:
        return None
    return db.query(models.Persona).filter(models.Persona.id == persona_id).first()


def _persona_display_name(persona: models.Persona | None) -> str:
    if not persona:
        return "Usuario"
    return persona.nombre_completo or getattr(persona, "full_name", None) or "Usuario"


# ── Helpers defense-in-depth Axioma 3 ───────────────────────────────────────


def _assert_conversation_sede_aligned(
    db: Session,
    conv: models.Conversation,
    current_user: models.User,
) -> None:
    """Axioma 3 — defense-in-depth: confirma que los otros participantes
    comparten ``sede_id`` con el actor cuando éste tiene sede asignada.

    Conversation no tiene ``sede_id`` propio porque su tenant scope se
    deduce de la intersección de las sedes de sus participantes
    (validado en ``create_conversation``). Este helper cubre el caso
    donde un Conversation pre-existente podría tener participantes de
    distintas sedes — owner-mismatch anterior que ``create_conversation``
    no atrapa. Retorna silenciosamente cuando:

      - El actor no tiene sede (superadmin sin atribución) — alcance global.
      - El actor es el único participante restante (self-DM, válido).

    En caso contrario, si uno o más participantes tienen ``sede_id``
    distinta al actor, retorna 403 existence-leak safe.

    Performance: el batch ``Persona.id.in_([...])`` evita N+1 cuando el
    grupo tiene >2 participantes. Costo: 1 query independiente del
    tamaño del grupo.
    """
    actor_sede = get_user_sede_id(db, current_user.id)
    if actor_sede is None:
        return  # superadmin sin atribución — alcance global

    other_participants = [cp for cp in conv.participants if str(cp.user_id) != str(current_user.id)]
    if not other_participants:
        return  # self-DM

    actor_sede_str = str(actor_sede)
    other_ids = [cp.user_id for cp in other_participants if cp.user_id]
    if not other_ids:
        return
    # Batch lookup: 1 query para todos los otros participantes.
    other_sedes = db.query(models.Persona.id, models.Persona.sede_id).filter(models.Persona.id.in_(other_ids)).all()
    for _pid, sede_id in other_sedes:
        if sede_id is None:
            continue  # orphan — permitido mismo que create_conversation
        if str(sede_id) != actor_sede_str:
            # Existence-leak safe: 404 (no 403) con detail neutro
            # indistinguible del caso "conversation no existe" — evita
            # que un atacante enumerando IDs distinga "existe cross-sede"
            # de "no existe". Mismo contrato que el resto del CRM/CMS.
            raise HTTPException(
                status_code=404,
                detail="Conversation not found",
            )


def _assert_sender_sede_matches_actor(
    db: Session,
    msg: models.ChatMessage,
    current_user: models.User,
) -> None:
    """Axioma 3 — defense-in-depth: confirma que el sender del mensaje
    comparte ``sede_id`` con el actor cuando éste tiene sede asignada.

    En el flujo canónico este check es tautológico porque el caller
    ya pasó el guard anterior (``msg.sender_id != current_user.id``
    retorna 404). Lo conservamos como segunda capa explícita para
    anticipar escenarios donde sender_id y actor se desacoplan:

    - Mensajes generados por bots/forwards con sender distinto al
      deleter.
    - Migración de logs creados en el sistema anterior donde sender_id
      apuntaba a FK integer y se reasignó a persona UUID de otra sede.
    - Tests con mocks que inyectan sender_id cross-tenant.

    La query es un solo ``SELECT sede_id`` y solo dispara si el caller
    tiene sede asignada.
    """
    actor_sede = get_user_sede_id(db, current_user.id)
    if actor_sede is None:
        return  # superadmin sin atribución
    sender_sede = db.query(models.Persona.sede_id).filter(models.Persona.id == msg.sender_id).scalar()
    if sender_sede is None:
        return  # orphan — permitido mismo que create_conversation
    if str(sender_sede) != str(actor_sede):
        # Existence-leak safe: 404 (no 403) con detail neutro
        # para no filtrar la existencia del msg al atacante. La API
        # ya retorna 404 cuando el msg no existe; mantener el mismo
        # contrato aquí evita el vector de enumeración por status code.
        raise HTTPException(
            status_code=404,
            detail="Message not found",
        )


def _assert_actor_still_participant_at_commit_time(
    db: Session,
    conv_id,
    current_user: models.User,
) -> None:
    """Axioma 3 — defense-in-depth al commit time: confirma que el actor
    sigue siendo participante activo de ``conv_id`` JUSTO ANTES del
    CRUD mutador.

    Cierra el vector TOCTOU donde el participant fue removido del conv
    entre la query inicial (``is_participant`` en el head del endpoint)
    y la mutación final (``crud.create_direct_message`` /
    ``crud.mark_conversation_read``). Aunque en el flujo canónico ambos
    páginas de tiempo son sub-segundo, posibles drifts son:

    - Admin remove (race con un moderador detectando abuse y purgando).
    - Bulk migrations concurrentes (sync entre sedes, purges de owners).
    - Workers async que borran participants cross-tenant.
    - Stress / retries de cliente que re-intentan con DELETE queue
      en cola.

    Diferencia con los otros helpers de participation:

    - ``_assert_actor_is_active_participant(msg)``: defensa para
      ``DELETE /api/chat/messages/{id}`` — usa ``msg.room_id`` por
      convención ``"dm_<conv_id>"``.
    - Esta función: defensa para endpoints Conversation-level
      (``POST /messages``, ``POST /read``) donde el ``conv_id``
      viene en el path, no hay msg.

    Existence-leak safe: 404 ``"Conversation not found"`` (uniforme con
    el resto de chat.py). El detalle neutro impide que un atacante
    que descubre message-ids distinga "estabas en el conv y te
    removieron" de "nunca estuviste en el conv".

    Performance: 1 query indexed (lookup pk+uk en ConvParticipant).
    """
    if conv_id is None:
        # Treat None conv_id as "not found" — prevents TypeError from
        # leaking as 500 server error. Existence-leak safe: mismo detail
        # uniforme con el resto de los paths de no-encontrado.
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )
    try:
        target_conv_id = _uuid.UUID(str(conv_id)) if not isinstance(conv_id, _uuid.UUID) else conv_id
    except (TypeError, ValueError):
        # conv_id malformado en el path: tratar como no-existente.
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )
    participant_row = (
        db.query(models.ConversationParticipant.id)
        .filter(
            models.ConversationParticipant.conversation_id == target_conv_id,
            models.ConversationParticipant.user_id == current_user.id,
        )
        .first()
    )
    if participant_row is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )


def _assert_actor_is_active_participant(
    db: Session,
    msg: models.ChatMessage,
    current_user: models.User,
) -> None:
    """Axioma 3 — defense-in-depth: confirma que el actor es participante
    activo de la Conversation que contiene este mensaje.

    La relación ``ChatMessage ↔ Conversation`` es ad-hoc por convención:
    ``ChatMessage.room_id == f"dm_{conversation_id}"``. La verificación
    de participación cubre el vector TOCTOU donde:

    - El actor fue participante, mandó un mensaje, luego fue removido
      del conv (admin action, bulk migration, sync de otra sede, scripts
      antiguos de purge).
    - El actor NO está en el conv pero ``sender_id == current_user.id``
      fue seteado de forma spuria (mutación directa de la fila,
      escenario de prueba, replay/cache corrupto).

    El check se ejecuta **antes** del sender check en el endpoint para
    maximizar la existence-leak safety: un atacante enumerando IDs no
    puede distinguir "msg existe pero no participo" (404) de "msg no
    existe" (404) ni "msg existe pero es de otro sender" (404). Todos
    colapsan al mismo status + detail.

    Edge cases:

    - ``msg.room_id is None`` / ``""`` / no empieza con ``"dm_"``:
      mensajes antiguos o system-broadcast sin scope de conv. La check
      es no-op; el sender check cubre el contrato. Permanece
      back-compat con fixtures pre-migración.
    - ``msg.room_id`` con prefijo ``"dm_"`` pero suffix no es un UUID
      válido: tratar como no-participante. 404 defense-in-depth contra
      tampering de filas raw (anti-crafting).
    - ``msg.room_id`` válido pero el actor NO es participant: 404
      existence-leak safe.
    - ``msg.room_id`` válido y el actor SÍ es participant: return.

    Performance: 1 query indexed (ConvParticipant PK lookup +
    user_id+conv_id filtering). Sin superadmin bypass: la existencia-
    leak safety uniforme es preferible a la excepción de conveniencia.
    El superadmin puede borrar sus propios msgs (sender check) y los
    ajenos vía procesos batch admin no cubiertos por este endpoint.
    """
    if not msg.room_id or not msg.room_id.startswith("dm_"):
        # Antiguo / system room: sin scope de conv implícito.
        # La participation check no aplica; el sender check basta.
        return

    suffix = msg.room_id[len("dm_") :]
    try:
        conv_uuid = _uuid.UUID(suffix)
    except (TypeError, ValueError):
        # Anti-tampering: alguien escribió un suffix no-UUID a la fila
        # directamente. Comportamiento seguro = tratar como no-accessible.
        raise HTTPException(
            status_code=404,
            detail="Message not found",
        )

    participant_row = (
        db.query(models.ConversationParticipant.id)
        .filter(
            models.ConversationParticipant.conversation_id == conv_uuid,
            models.ConversationParticipant.user_id == current_user.id,
        )
        .first()
    )
    if participant_row is None:
        # Existence-leak safe: 404 uniforme con el resto de chat.py.
        raise HTTPException(
            status_code=404,
            detail="Message not found",
        )


# ── Helpers de serialización / lookup ────────────────────────────────────────


def _parse_mentions_raw(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return [str(item) for item in value] if isinstance(value, list) else None


def _protected_attachment_url(msg: models.ChatMessage, conversation_id: str | _uuid.UUID | None) -> str | None:
    """Normalize a chat attachment URL to the authenticated download route."""
    raw_url = msg.attachment_url
    if not raw_url or not conversation_id:
        return raw_url
    if raw_url.startswith("/api/chat/attachments/"):
        return raw_url[len("/api") :]
    prefix = "/static/chat_attachments/"
    if raw_url.startswith(prefix):
        suffix = raw_url[len(prefix) :].split("?", 1)[0]
        parts = suffix.split("/", 1)
        if len(parts) == 2:
            sede_bucket, filename = parts
            return f"/chat/attachments/{conversation_id}/{sede_bucket}/{filename}"
    return raw_url


def _validate_attachment_reference(attachment_url: str | None, conversation_id: str | _uuid.UUID) -> None:
    """Reject protected attachment references that target another conversation.

    External URLs remain supported for older/API clients, but an internal
    protected URL must be bound to the conversation in which it is sent.
    """
    if not attachment_url:
        return
    prefixes = ("/chat/attachments/", "/api/chat/attachments/")
    prefix = next((candidate for candidate in prefixes if attachment_url.startswith(candidate)), None)
    if prefix is None:
        return
    parts = attachment_url[len(prefix) :].split("/", 2)
    if len(parts) != 3:
        raise HTTPException(status_code=422, detail="Invalid attachment reference")
    try:
        referenced_conversation = _uuid.UUID(parts[0])
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Invalid attachment reference")
    if referenced_conversation != _uuid.UUID(str(conversation_id)):
        raise HTTPException(status_code=422, detail="Invalid attachment reference")


def _build_reply_preview(
    db: Session,
    reply_to_id: _uuid.UUID | None,
    room_id: str,
) -> schemas.ReplyPreview | None:
    if not reply_to_id:
        return None
    reply = (
        db.query(models.ChatMessage)
        .filter(
            models.ChatMessage.id == reply_to_id,
            models.ChatMessage.room_id == room_id,
            models.ChatMessage.deleted_at.is_(None),
        )
        .first()
    )
    if not reply:
        return None
    sender = db.query(models.Persona).filter(models.Persona.id == reply.sender_id).first()
    return schemas.ReplyPreview(
        id=reply.id,
        sender_name=_persona_display_name(sender),
        content=reply.content or "",
        attachment_type=reply.attachment_type,
    )


def _build_admin_message(
    current_user: models.User,
    msg: models.ChatMessage,
    is_read: bool = False,
    conv_map: dict | None = None,
    persona_map: dict | None = None,
) -> schemas.ChatMessageAdminRead:
    """Serialize a ChatMessage for the message admin center.

    ``conv_map`` and ``persona_map`` are pre-fetched batch lookups so callers
    can avoid N+1 queries when serializing many messages.
    """
    conv_id = msg.room_id[3:] if msg.room_id and msg.room_id.startswith("dm_") else None
    conversation_id = _uuid.UUID(conv_id) if conv_id else None

    conversation_name = "Chat"
    if conversation_id and conv_map:
        conv = conv_map.get(conversation_id)
        if conv:
            other = next(
                (p for p in conv.participants if str(p.user_id) != str(current_user.id)),
                None,
            )
            if other and persona_map:
                conversation_name = _persona_display_name(persona_map.get(other.user_id))

    sender = persona_map.get(msg.sender_id) if persona_map else None
    mentions = None
    if msg.mentions_raw:
        try:
            mentions = json.loads(msg.mentions_raw)
        except Exception:
            mentions = None

    return schemas.ChatMessageAdminRead(
        id=msg.id,
        conversation_id=conversation_id,
        conversation_name=conversation_name,
        sender_id=msg.sender_id,
        sender_name=_persona_display_name(sender),
        content=msg.content,
        created_at=msg.created_at,
        is_read=is_read,
        attachment_url=_protected_attachment_url(msg, conversation_id),
        attachment_type=msg.attachment_type,
        attachment_name=msg.attachment_name,
        attachment_size=msg.attachment_size,
        reply_to_id=msg.reply_to_id,
        mentions=mentions,
    )


def _serialize_conversation(
    db: Session,
    conv: models.Conversation,
    current_user_id: _uuid.UUID,
    current_persona_id,
    unread_counts: dict | None = None,
) -> schemas.ConversationRead:
    # Batch-fetch all participant personas in one query (avoid N+1)
    participant_persona_ids = [cp.user_id for cp in conv.participants]
    user_map: dict = {}
    if participant_persona_ids:
        personas = db.query(models.Persona).filter(models.Persona.id.in_(participant_persona_ids)).all()
        for p in personas:
            user_map[p.id] = p

    participants = []
    for cp in conv.participants:
        persona = user_map.get(cp.user_id)
        participants.append(
            schemas.ConversationParticipantRead(
                persona_id=cp.user_id,
                username=_persona_display_name(persona),
                last_read_at=cp.last_read_at,
            )
        )

    if unread_counts is not None:
        unread = unread_counts.get(conv.id, 0)
    else:
        unread = crud.get_unread_count_for_conversation(db, conv.id, current_user_id)

    return schemas.ConversationRead(
        id=conv.id,
        participants=participants,
        last_message_content=conv.last_message_content,
        last_message_at=conv.last_message_at,
        last_sender_id=conv.last_sender_id,
        unread_count=unread,
        created_at=conv.created_at,
    )


def _find_existing_dm(db: Session, user_id1: _uuid.UUID, user_id2: _uuid.UUID):
    """Check if a 2-person DM conversation already exists.

    Uses a direct join instead of fetching all participations for both users.
    """
    # Find conversations where both users are participants
    cps = (
        db.query(models.ConversationParticipant.conversation_id)
        .filter(models.ConversationParticipant.user_id.in_([user_id1, user_id2]))
        .group_by(models.ConversationParticipant.conversation_id)
        .having(func.count(models.ConversationParticipant.id) == 2)
        .all()
    )
    for (conv_id,) in cps:
        # Verify these are the ONLY two participants
        total = (
            db.query(models.ConversationParticipant)
            .filter(models.ConversationParticipant.conversation_id == conv_id)
            .count()
        )
        if total == 2:
            return db.query(models.Conversation).filter(models.Conversation.id == conv_id).first()
    return None


# ── Routes ────────────────────────────────────────────────────────────────────


@router.get("/chat/users/search")
def search_chat_users(
    q: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(10, le=50),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("messaging", "read")),
):
    """Search personas with auth account to start a conversation with (excludes self).

    Axioma 3: filtra por sede_id del usuario autenticado.
    """
    user_sede = get_user_sede_id(db, current_user.id)
    current_persona_id = _get_persona_id(db, current_user)

    # Escape LIKE wildcards to prevent unintended pattern matching
    safe_q = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{safe_q}%"
    query = (
        db.query(models.Persona, models.Usuario)
        .join(models.Usuario, models.Usuario.id == models.Persona.id)
        .filter(models.Usuario.is_active.is_(True))
        .filter(
            (models.Persona.first_name.ilike(pattern))
            | (models.Persona.last_name.ilike(pattern))
            | (models.Persona.email.ilike(pattern))
            | (models.Usuario.username.ilike(pattern))
            | (models.Usuario.email.ilike(pattern))
        )
    )
    if user_sede is not None:
        query = query.filter(models.Persona.sede_id == user_sede)
    if current_persona_id:
        query = query.filter(models.Persona.id != current_persona_id)
    users = query.order_by(models.Persona.first_name, models.Persona.last_name).limit(limit).all()
    return [
        {
            "id": str(persona.id),
            "username": persona.nombre_completo or usuario.username or "",
            "email": persona.email or usuario.email or "",
            "avatar_url": getattr(persona, "photo_url", None),
        }
        for persona, usuario in users
    ]


@router.get(
    "/chat/conversations",
    response_model=List[schemas.ConversationRead],
)
def list_conversations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("messaging", "read")),
):
    """List all DM conversations for the current user."""
    persona_id = _get_persona_id(db, current_user)
    if not persona_id:
        return []
    convs = crud.get_user_conversations(db, current_user.id)
    conv_ids = [c.id for c in convs]
    unread_counts = crud.get_unread_counts_batch(db, current_user.id, conv_ids)
    return [_serialize_conversation(db, c, current_user.id, persona_id, unread_counts=unread_counts) for c in convs]


@router.post(
    "/chat/conversations",
    response_model=schemas.ConversationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    payload: schemas.ConversationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("messaging", "edit")),
):
    """Create a DM conversation with other users.

    Axioma 3 (defense-in-depth): valida que cada participante pertenezca a
    la sede del actor. Conversation NO tiene ``sede_id`` propio porque su
    tenant scope se define por la intersección de las sedes de sus
    participantes. Si cualquiera de los participantes es de otra sede, la
    conversación sería cross-tenant — rechazado con 403.
    """
    persona_id = _get_persona_id(db, current_user)
    if not persona_id:
        raise HTTPException(status_code=404, detail="Persona not found for current user")

    payload_personas = db.query(models.Persona).filter(models.Persona.id.in_(payload.participant_ids)).all()

    # Cross-sede guard — existence-leak safe: 404 (no 403) para no
    # filtrar al atacante la naturaleza del rechazo cuando ``foreign``
    # existe. El detail es neutro porque previamente el caller validó
    # que el participant_id existe vía el select de payload_personas;
    # un 403 vs 404 diferenciaría "existe cross-sede" de "no existe".
    actor_sede = get_user_sede_id(db, current_user.id)
    if actor_sede is not None:
        foreign = [p for p in payload_personas if p.sede_id is not None and str(p.sede_id) != str(actor_sede)]
        if foreign:
            raise HTTPException(
                status_code=404,
                detail="Participant not found",
            )
        # Orphan participant: aunque ``auth_users.sede_id`` es NOT NULL
        # por auth_v3, conservamos el branch para defensa contra
        # estados inconsistentes heredados (e.g. seeds antiguos, fixtures
        # pre-backfill). Existence-leak safe: 404 neutro.
        orphans = [p for p in payload_personas if p.sede_id is None]
        if orphans:
            raise HTTPException(
                status_code=404,
                detail="Participant not found",
            )

    participant_user_ids = [p.id for p in payload_personas]
    if current_user.id not in participant_user_ids:
        participant_user_ids.append(current_user.id)

    if len(participant_user_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="A conversation needs at least 2 participants",
        )
    if len(participant_user_ids) == 2:
        existing = _find_existing_dm(db, participant_user_ids[0], participant_user_ids[1])
        if existing:
            return _serialize_conversation(db, existing, current_user.id, persona_id)
    conv = crud.create_conversation(db, participant_user_ids)
    return _serialize_conversation(db, conv, current_user.id, persona_id)


@router.get(
    "/chat/conversations/{conv_id}/messages",
    response_model=List[schemas.DirectMessageItem],
)
def list_direct_messages(
    conv_id: str,
    limit: int = Query(50, le=200),
    before: Optional[str] = Query(None, alias="before"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("messaging", "read")),
):
    """List messages in a conversation (paginated, newest first).

    ``before`` accepts an ISO datetime string (preferred) for cursor-based
    pagination, or a UUID string for backward compatibility.
    """
    persona_id = _get_persona_id(db, current_user)
    if not persona_id:
        raise HTTPException(status_code=404, detail="Persona not found")
    conv_id = _coerce_uuid_or_404(conv_id, detail="Conversation not found")
    conv = db.query(models.Conversation).filter(models.Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    is_participant = (
        db.query(models.ConversationParticipant)
        .filter(
            models.ConversationParticipant.conversation_id == conv_id,
            models.ConversationParticipant.user_id == current_user.id,
        )
        .first()
    )
    if not is_participant:
        # Existence-leak safe: 404 uniforme con el resto de chat.py endpoints.
        raise HTTPException(status_code=404, detail="Conversation not found")
    _assert_conversation_sede_aligned(db, conv, current_user)

    before_created_at = None
    before_id = None
    if before:
        try:
            before_created_at = datetime.fromisoformat(before)
        except (ValueError, TypeError):
            try:
                before_id = _uuid.UUID(before)
            except (ValueError, TypeError):
                pass

    rows = crud.get_conversation_messages(
        db, conv_id, limit=limit, before_id=before_id, before_created_at=before_created_at
    )
    sender_ids = {r.sender_id for r in rows}

    # Map sender UUIDs to Personas (batch lookup)
    personas = db.query(models.Persona).filter(models.Persona.id.in_(sender_ids)).all() if sender_ids else []
    persona_map = {p.id: p for p in personas}

    last_read = is_participant.last_read_at
    return [
        schemas.DirectMessageItem(
            id=r.id,
            sender_id=r.sender_id,
            sender_name=_persona_display_name(persona_map.get(r.sender_id)),
            content=r.content,
            created_at=r.created_at,
            is_read=(r.sender_id == current_user.id or (last_read is not None and r.created_at <= last_read)),
            attachment_url=_protected_attachment_url(r, conv_id),
            attachment_type=r.attachment_type,
            attachment_name=r.attachment_name,
            attachment_size=r.attachment_size,
            reply_to_id=r.reply_to_id,
            reply_preview=_build_reply_preview(db, r.reply_to_id, f"dm_{conv_id}"),
            mentions=_parse_mentions_raw(r.mentions_raw),
        )
        for r in rows
    ]


@router.get(
    "/chat/my-messages",
    response_model=List[schemas.ChatMessageAdminRead],
)
def list_my_chat_messages(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("messaging", "read")),
):
    """List all direct messages sent by the current user.

    Axioma 3: only messages from conversations where the current user is a
    participant are returned, which also keeps the result within the same
    tenant scope.
    """
    if not current_user.id:
        return []
    convs = crud.get_user_conversations(db, current_user.id)
    if not convs:
        return []
    room_ids = [f"dm_{c.id}" for c in convs]
    msgs = (
        db.query(models.ChatMessage)
        .filter(
            models.ChatMessage.sender_id == current_user.id,
            models.ChatMessage.room_id.in_(room_ids),
            models.ChatMessage.deleted_at.is_(None),
        )
        .order_by(models.ChatMessage.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Batch lookup: one query for all related conversations and one for all personas.
    conv_map = {c.id: c for c in convs}
    persona_ids: set = set()
    for msg in msgs:
        if msg.sender_id:
            persona_ids.add(msg.sender_id)
    for c in convs:
        for p in c.participants:
            if p.user_id:
                persona_ids.add(p.user_id)
    personas = db.query(models.Persona).filter(models.Persona.id.in_(persona_ids)).all() if persona_ids else []
    persona_map = {p.id: p for p in personas}

    return [
        _build_admin_message(current_user, msg, is_read=True, conv_map=conv_map, persona_map=persona_map)
        for msg in msgs
    ]


@router.get(
    "/chat/mentions",
    response_model=List[schemas.ChatMessageAdminRead],
)
def list_my_chat_mentions(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("messaging", "read")),
):
    """List chat messages where the current user has been mentioned.

    Axioma 3: only messages from conversations where the current user is a
    participant are returned.
    """
    persona_id = _get_persona_id(db, current_user)
    if not persona_id:
        return []
    convs = crud.get_user_conversations(db, current_user.id)
    if not convs:
        return []
    room_ids = [f"dm_{c.id}" for c in convs]
    my_id = str(persona_id)
    msgs = (
        db.query(models.ChatMessage)
        .filter(
            models.ChatMessage.room_id.in_(room_ids),
            models.ChatMessage.mentions_raw.isnot(None),
            models.ChatMessage.mentions_raw.ilike(f"%{my_id}%"),
            models.ChatMessage.deleted_at.is_(None),
        )
        .order_by(models.ChatMessage.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Batch lookup of last_read_at per conversation to compute is_read
    # without N+1 queries.
    last_read_map = {
        str(row.conversation_id): row.last_read_at
        for row in db.query(
            models.ConversationParticipant.conversation_id,
            models.ConversationParticipant.last_read_at,
        )
        .filter(
            models.ConversationParticipant.conversation_id.in_([c.id for c in convs]),
            models.ConversationParticipant.user_id == current_user.id,
        )
        .all()
    }

    # Pre-filter messages that actually mention the current user so we only
    # batch-load data for relevant messages.
    result_msgs = []
    for msg in msgs:
        mentions = []
        if msg.mentions_raw:
            try:
                mentions = json.loads(msg.mentions_raw)
            except Exception as exc:  # pragma: no cover - skip msg with bad mentions payload
                logger.debug("chat: skip msg %s, malformed mentions_raw: %s", msg.id, exc)
                continue
        if my_id not in mentions:
            continue
        result_msgs.append(msg)

    # Batch lookup: one query for all related conversations and one for all personas.
    conv_map = {c.id: c for c in convs}
    persona_ids: set = set()
    for msg in result_msgs:
        if msg.sender_id:
            persona_ids.add(msg.sender_id)
    for c in convs:
        for p in c.participants:
            if p.user_id:
                persona_ids.add(p.user_id)
    personas = db.query(models.Persona).filter(models.Persona.id.in_(persona_ids)).all() if persona_ids else []
    persona_map = {p.id: p for p in personas}

    result = []
    for msg in result_msgs:
        conv_id = msg.room_id[3:] if msg.room_id and msg.room_id.startswith("dm_") else None
        read_at = last_read_map.get(conv_id)
        is_read = bool(read_at) and msg.created_at <= read_at
        result.append(
            _build_admin_message(
                current_user,
                msg,
                is_read=is_read,
                conv_map=conv_map,
                persona_map=persona_map,
            )
        )
    return result


@router.post(
    "/chat/conversations/{conv_id}/messages",
    response_model=schemas.DirectMessageItem,
    status_code=status.HTTP_201_CREATED,
)
def send_direct_message(
    conv_id: str,
    payload: schemas.DirectMessageCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("messaging", "edit")),
):
    """Send a message in a conversation.

    Order of guards (existence-leak-safe, defense-in-depth):

    1.  ``msg exists?`` of conv  — 404 si no existe.
    2.  ``actor has persona?``   — 404 si actor sin persona.
    3.  Early ``is_participant?`` — 404 si actor no estaba en el conv
        al momento del fetch (uniform 404 con el resto de chat.py;
        cierra el vector de cross-conv leak por ID guessing).
    4.  ``_assert_conversation_sede_aligned`` — defense-in-depth al
        nivel de Axioma 3 (sede de los otros participantes).
    5.  ``_assert_actor_still_participant_at_commit_time`` (NEW) — TOCTOU
        defense al commit time: re-valida participación del actor
        justo antes del CRUD mutador. Cierra el drift entre fetch
        y commit (bulk migrations, admin removals concurrentes).
    6.  ``crud.create_direct_message`` — la mutación.
    """
    persona_id = _get_persona_id(db, current_user)
    if not persona_id:
        raise HTTPException(status_code=404, detail="Persona not found")
    conv_id = _coerce_uuid_or_404(conv_id, detail="Conversation not found")
    conv = db.query(models.Conversation).filter(models.Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    is_participant = (
        db.query(models.ConversationParticipant)
        .filter(
            models.ConversationParticipant.conversation_id == conv_id,
            models.ConversationParticipant.user_id == current_user.id,
        )
        .first()
    )
    if not is_participant:
        # Existence-leak safe: 404 uniforme con el resto del endpoint.
        # Antes del hardening era 403 con detail "Not a participant",
        # pero el 404 impide que un atacante distinga "el conv existe
        # y NO participas" de "el conv no existe" — vector BOLA.
        raise HTTPException(status_code=404, detail="Conversation not found")
    _assert_conversation_sede_aligned(db, conv, current_user)
    # TOCTOU defense (#5): re-validar participación al commit time.
    _assert_actor_still_participant_at_commit_time(db, conv_id, current_user)

    persona = _get_persona(db, current_user)
    sender_name = _persona_display_name(persona)
    _validate_attachment_reference(payload.attachment_url, conv_id)
    if payload.reply_to_id:
        parent = (
            db.query(models.ChatMessage.id)
            .filter(
                models.ChatMessage.id == payload.reply_to_id,
                models.ChatMessage.room_id == f"dm_{conv_id}",
                models.ChatMessage.deleted_at.is_(None),
            )
            .first()
        )
        if parent is None:
            existing_parent = (
                db.query(models.ChatMessage.id)
                .filter(
                    models.ChatMessage.id == payload.reply_to_id,
                    models.ChatMessage.deleted_at.is_(None),
                )
                .first()
            )
            if existing_parent is not None:
                raise HTTPException(status_code=422, detail="Invalid reply reference")

    msg = crud.create_direct_message(db, conv_id, current_user.id, payload.content)

    if payload.attachment_url:
        msg.attachment_url = payload.attachment_url
        msg.attachment_type = payload.attachment_type
        msg.attachment_name = payload.attachment_name
        msg.attachment_size = payload.attachment_size
    if payload.reply_to_id:
        msg.reply_to_id = payload.reply_to_id
    if payload.mentions:
        msg.mentions_raw = json.dumps([str(m) for m in payload.mentions])
        # M-05 hardening: only notify participants of THIS conversation, and
        # only when they belong to the actor's sede. Without this filter a
        # user with ``messaging:edit`` could mention anyone on the platform
        # (other sedes included), generating spam/phishing notifications with
        # arbitrary content.
        conv_participant_ids = {
            str(user_id)
            for (user_id,) in db.query(models.ConversationParticipant.user_id)
            .filter(models.ConversationParticipant.conversation_id == conv_id)
            .all()
            if user_id is not None
        }
        filtered_mentions = [
            mention_id
            for mention_id in payload.mentions
            if str(mention_id) in conv_participant_ids and str(mention_id) != str(current_user.id)
        ]
        # Create in-app notifications for every mentioned user except the sender.
        actor_sede = get_user_sede_id(db, current_user.id)
        notify_mention(
            db,
            mention_ids=filtered_mentions,
            author_id=current_user.id,
            title="Te mencionaron en un chat",
            content=f"{sender_name}: {msg.content[:120]}{'...' if len(msg.content) > 120 else ''}",
            url=f"/plataforma/messages?conv={conv_id}",
            sede_id=actor_sede,
        )
    db.commit()
    db.refresh(msg)

    reply_preview = _build_reply_preview(db, msg.reply_to_id, f"dm_{conv_id}")

    # Broadcast via WebSocket (scheduled as background task to avoid RuntimeError
    # from asyncio.get_running_loop in sync endpoint context)
    ws_payload = {
        "event": "direct_message",
        "conversation_id": str(conv_id),
        "message": {
            "id": str(msg.id),
            "sender_id": str(msg.sender_id),
            "sender_name": sender_name,
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
            "is_read": False,
            "attachment_url": _protected_attachment_url(msg, conv_id),
            "attachment_type": msg.attachment_type,
            "attachment_name": msg.attachment_name,
            "attachment_size": msg.attachment_size,
            "reply_to_id": str(msg.reply_to_id) if msg.reply_to_id else None,
            "reply_preview": reply_preview.model_dump(mode="json") if reply_preview else None,
            "mentions": _parse_mentions_raw(msg.mentions_raw),
        },
    }
    background_tasks.add_task(manager.broadcast_event, ws_payload, room=f"dm_{conv_id}")
    return schemas.DirectMessageItem(
        id=msg.id,
        sender_id=current_user.id,
        sender_name=sender_name,
        content=msg.content,
        created_at=msg.created_at,
        attachment_url=_protected_attachment_url(msg, conv_id),
        attachment_type=msg.attachment_type,
        attachment_name=msg.attachment_name,
        attachment_size=msg.attachment_size,
        reply_to_id=msg.reply_to_id,
        reply_preview=reply_preview,
        mentions=[str(m) for m in payload.mentions] if payload.mentions else None,
    )


@router.post("/chat/conversations/{conv_id}/read")
def mark_conversation_read_endpoint(
    conv_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("messaging", "read")),
):
    """Mark all messages as read in a conversation.

    Order of guards (mismo patrón que ``send_direct_message``):

    1. conv exists?     — 404 si no.
    2. is_participant?  — 404 si actor no estaba al fetch (uniform).
    3. sede aligned?    — 404 si mismatch cross-sede.
    4. STILL participant at commit time? — 404 si drift (TOCTOU).
    5. mark_conversation_read — la mutación.
    """
    persona_id = _get_persona_id(db, current_user)
    if not persona_id:
        raise HTTPException(status_code=404, detail="Persona not found")
    conv_id = _coerce_uuid_or_404(conv_id, detail="Conversation not found")
    conv = db.query(models.Conversation).filter(models.Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    is_participant = (
        db.query(models.ConversationParticipant)
        .filter(
            models.ConversationParticipant.conversation_id == conv_id,
            models.ConversationParticipant.user_id == current_user.id,
        )
        .first()
    )
    if not is_participant:
        # Existence-leak safe: 404 uniforme con el resto del endpoint.
        raise HTTPException(status_code=404, detail="Conversation not found")
    _assert_conversation_sede_aligned(db, conv, current_user)
    # TOCTOU defense: re-validar participación al commit time.
    _assert_actor_still_participant_at_commit_time(db, conv_id, current_user)
    crud.mark_conversation_read(db, conv_id, current_user.id)
    return {"ok": True}


@router.delete("/chat/messages/{message_id}")
def delete_chat_message_endpoint(
    message_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("messaging", "edit")),
):
    """Delete a chat message (own only).

    Order of guards (existence-leak-safe):

    1. ``msg exists?`` — 404.
    2. ``actor has persona?`` — 404.
    3. ``_assert_actor_is_active_participant`` (NEW Sprint 3.5) — TOCTOU
       defense: el actor debe seguir siendo participante activo del conv
       que contiene el msg. 404 si no lo es.
    4. ``msg.sender_id == current_user.id`` — 404 (uniforme con el
       resto del endpoint; contract v3.0.1 cambió de 403 a 404 para
       cerrar el existence-leak cuando actor no es el sender).
    5. ``_assert_sender_sede_matches_actor`` — defense-in-depth Axioma 3
       al nivel de sede. 404 si mismatch.
    6. Soft-delete + commit.
    """
    message_id = _coerce_uuid_or_404(message_id, detail="Message not found")
    msg = (
        db.query(models.ChatMessage)
        .filter(
            models.ChatMessage.id == message_id,
            models.ChatMessage.deleted_at.is_(None),
        )
        .first()
    )
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    persona_id = _get_persona_id(db, current_user)
    if not persona_id:
        raise HTTPException(status_code=404, detail="Persona not found")
    # Step 3: participation check (TOCTOU + cross-conv leak defense).
    _assert_actor_is_active_participant(db, msg, current_user)
    # Step 4: sender self-only. Uniform 404 for existence-leak safety
    # (matches the rest of chat.py contract; differs from a 403).
    if msg.sender_id != current_user.id:
        raise HTTPException(status_code=404, detail="Message not found")
    # Step 5: sede defense-in-depth.
    _assert_sender_sede_matches_actor(db, msg, current_user)
    msg.deleted_at = _utcnow()
    msg.content = "[Mensaje eliminado]"
    db.commit()
    return {"ok": True}


@router.get("/chat/attachments/{conversation_id}/{sede_bucket}/{filename}")
def download_chat_attachment(
    conversation_id: _uuid.UUID,
    sede_bucket: str,
    filename: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("messaging", "read")),
):
    """Serve a direct-chat attachment only to conversation participants.

    Attachments are deliberately not exposed through the public static mount.
    The conversation UUID in the URL is an address, not an authorization
    primitive: access is checked against ``ConversationParticipant`` and the
    file must be referenced by a live message in that conversation.
    """
    import os
    import re as _re

    if not _re.fullmatch(r"[0-9a-fA-F-]{36}", sede_bucket) and sede_bucket != "_global":
        raise HTTPException(status_code=404, detail="Attachment not found")
    if not _re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,254}", filename):
        raise HTTPException(status_code=404, detail="Attachment not found")

    participant = (
        db.query(models.ConversationParticipant.id)
        .filter(
            models.ConversationParticipant.conversation_id == conversation_id,
            models.ConversationParticipant.user_id == current_user.id,
        )
        .first()
    )
    if participant is None:
        raise HTTPException(status_code=404, detail="Attachment not found")

    actor_sede = get_user_sede_id(db, current_user.id)
    if actor_sede is not None and sede_bucket != str(actor_sede):
        raise HTTPException(status_code=404, detail="Attachment not found")

    protected_url = f"/chat/attachments/{conversation_id}/{sede_bucket}/{filename}"
    api_protected_url = f"/api{protected_url}"
    fallback_url = f"/static/chat_attachments/{sede_bucket}/{filename}"
    message = (
        db.query(models.ChatMessage.id)
        .filter(
            models.ChatMessage.room_id == f"dm_{conversation_id}",
            models.ChatMessage.deleted_at.is_(None),
            models.ChatMessage.attachment_url.in_([protected_url, api_protected_url, fallback_url]),
        )
        .first()
    )
    if message is None:
        raise HTTPException(status_code=404, detail="Attachment not found")

    uploads_root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "static", "chat_attachments"))
    filepath = os.path.normpath(os.path.join(uploads_root, sede_bucket, filename))
    if not filepath.startswith(uploads_root + os.sep) or not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="Attachment not found")

    return FileResponse(filepath, filename=filename)


@router.post("/chat/upload-attachment")
async def upload_chat_attachment(
    file: UploadFile = File(...),
    conversation_id: Optional[_uuid.UUID] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("messaging", "edit")),
):
    """Upload a file attachment for chat messages.

    Defense-in-depth:
      - Auth: ``require_module_access("messaging", "edit")`` (sin fallback hasattr).
      - Multi-tenant: path aislado por sede ``static/chat_attachments/{sede_id}/``;
        el ``sede_id`` se resuelve del actor. Superadmin sin sede usa ``_global``.
      - Validación de content-type contra allowlist MÁS verificación de magic
        bytes para imágenes/PDF (defensa contra content-type spoof).
      - Extensión saneada: sólo ``[A-Za-z0-9.]``, fallback ``.bin``.
      - Path-traversal guard: el final path debe empezar con el uploads root.
    """
    import os
    import re as _re
    import uuid as _uuid

    # Validate file type
    ALLOWED_TYPES = {
        "image/jpeg": "image",
        "image/png": "image",
        "image/gif": "image",
        "image/webp": "image",
        "image/svg+xml": "image",
        "application/pdf": "pdf",
        "application/msword": "document",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "document",
        "application/vnd.ms-excel": "document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "document",
        "text/plain": "document",
        "text/csv": "document",
        "video/mp4": "video",
        "video/webm": "video",
        "audio/mpeg": "audio",
        "audio/ogg": "audio",
        "audio/wav": "audio",
    }
    # Magic-byte signatures para los content-types más spoofeables. Defensa
    # contra un actor que declara image/jpeg pero sube binario malicioso.
    MAGIC_BYTES = {
        "image/jpeg": [(b"\xff\xd8\xff",)],
        "image/png": [(b"\x89PNG\r\n\x1a\n",)],
        "image/gif": [(b"GIF87a",), (b"GIF89a",)],
        "application/pdf": [(b"%PDF-",)],
    }

    content_type = file.content_type or "application/octet-stream"
    att_type = ALLOWED_TYPES.get(content_type, None)
    if not att_type:
        raise HTTPException(status_code=422, detail=f"Tipo de archivo no permitido: {content_type}")

    # Check file size (max 25MB) WITHOUT buffering the whole stream: read in
    # chunks until MAX_SIZE+1 is exceeded, so an oversized upload cannot cause
    # a memory DoS regardless of the client's advertised size.
    MAX_SIZE = 25 * 1024 * 1024
    contents = bytearray()
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        contents.extend(chunk)
        if len(contents) > MAX_SIZE:
            raise HTTPException(status_code=413, detail="El archivo supera el límite de 25 MB")

    # Magic-byte verification (sólo para tipos spoofeables; skip si no hay sig).
    if content_type in MAGIC_BYTES:
        sigs = MAGIC_BYTES[content_type]
        if not any(contents.startswith(sig) for sig_tuple in sigs for sig in sig_tuple):
            raise HTTPException(
                status_code=422,
                detail="El contenido del archivo no coincide con el tipo declarado",
            )

    # Verify conversation participation BEFORE touching the filesystem so a
    # non-participant never triggers a write+delete cycle (or orphans a file
    # if the cleanup fails).
    if conversation_id is not None:
        try:
            parsed_conversation_id = _uuid.UUID(str(conversation_id))
        except (TypeError, ValueError):
            raise HTTPException(status_code=404, detail="Conversation not found")
        participant = (
            db.query(models.ConversationParticipant.id)
            .filter(
                models.ConversationParticipant.conversation_id == parsed_conversation_id,
                models.ConversationParticipant.user_id == current_user.id,
            )
            .first()
        )
        if participant is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

    # Aislar por sede: el path incluye el sede_id del actor. Superadmin
    # sin atribución (sede_id is None) bucketa en ``_global``.
    actor_sede = get_user_sede_id(db, current_user.id)
    sede_bucket = str(actor_sede) if actor_sede is not None else "_global"

    uploads_root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "static", "chat_attachments"))
    upload_dir = os.path.normpath(os.path.join(uploads_root, sede_bucket))
    os.makedirs(upload_dir, exist_ok=True)

    # Sanear extensión: sólo [A-Za-z0-9.] hasta 10 chars, fallback .bin.
    raw_ext = os.path.splitext(file.filename or "")[1]
    ext = ("." + _re.sub(r"[^A-Za-z0-9]", "", raw_ext.lstrip("."))[:9]) if raw_ext else ".bin"
    if not ext or ext == ".":
        ext = ".bin"

    filename = f"{_uuid.uuid4()}{ext}"
    filepath = os.path.normpath(os.path.join(upload_dir, filename))

    # Path-traversal guard: el filepath final DEBE estar bajo uploads_root.
    # Cierra cualquier crafted filename/ext o sede_bucket malicioso que se
    # colaría si get_user_sede_id devolviera algo raro en el futuro.
    if not filepath.startswith(uploads_root + os.sep) and filepath != uploads_root:
        raise HTTPException(status_code=400, detail="Invalid destination path")

    with open(filepath, "wb") as f:
        f.write(contents)

    if conversation_id is not None:
        url = f"/chat/attachments/{parsed_conversation_id}/{sede_bucket}/{filename}"
    else:
        # Backward-compatible upload response for callers that upload before
        # selecting a conversation. Without a conversation binding there is
        # intentionally no downloadable URL; the canonical chat UI always
        # supplies conversation_id.
        url = ""

    return {
        "url": url,
        "type": att_type,
        "name": file.filename or filename,
        "size": len(contents),
    }
