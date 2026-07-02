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

import asyncio
import uuid as _uuid
from collections import Counter
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.crud.crm import get_user_sede_id, resolve_persona_id_for_user
from backend.mesh_websockets import manager
from backend.models_shared import _utcnow

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

    other_participants = [
        cp for cp in conv.participants if str(cp.user_id) != str(current_user.id)
    ]
    if not other_participants:
        return  # self-DM

    actor_sede_str = str(actor_sede)
    other_ids = [cp.user_id for cp in other_participants if cp.user_id]
    if not other_ids:
        return
    # Batch lookup: 1 query para todos los otros participantes.
    other_sedes = (
        db.query(models.Persona.id, models.Persona.sede_id)
        .filter(models.Persona.id.in_(other_ids))
        .all()
    )
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
    sender_sede = (
        db.query(models.Persona.sede_id)
        .filter(models.Persona.id == msg.sender_id)
        .scalar()
    )
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

    suffix = msg.room_id[len("dm_"):]
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


def _serialize_conversation(
    db: Session,
    conv: models.Conversation,
    current_user_id: _uuid.UUID,
    current_persona_id,
) -> schemas.ConversationRead:
    # Batch-fetch all participant personas in one query (avoid N+1)
    participant_persona_ids = [cp.user_id for cp in conv.participants]
    user_map: dict = {}
    if participant_persona_ids:
        personas = db.query(models.Persona).filter(
            models.Persona.id.in_(participant_persona_ids)
        ).all()
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
    """Check if a 2-person DM conversation already exists."""
    cps = (
        db.query(models.ConversationParticipant)
        .filter(models.ConversationParticipant.user_id.in_([user_id1, user_id2]))
        .all()
    )
    conv_ids = {cp.conversation_id for cp in cps}
    counts: Counter = Counter()
    if conv_ids:
        all_cps = (
            db.query(models.ConversationParticipant)
            .filter(models.ConversationParticipant.conversation_id.in_(conv_ids))
            .all()
        )
        for cp in all_cps:
            counts[cp.conversation_id] += 1
    for conv_id, cnt in counts.items():
        if cnt == 2:
            pids = {cp.user_id for cp in all_cps if cp.conversation_id == conv_id}
            if pids == {user_id1, user_id2}:
                return db.query(models.Conversation).filter(
                    models.Conversation.id == conv_id
                ).first()
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
            "username": persona.nombre_completo,
            "email": persona.email or usuario.email or "",
            "avatar_url": None,
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
    return [_serialize_conversation(db, c, current_user.id, persona_id) for c in convs]


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

    payload_personas = db.query(models.Persona).filter(
        models.Persona.id.in_(payload.participant_ids)
    ).all()

    # Cross-sede guard — existence-leak safe: 404 (no 403) para no
    # filtrar al atacante la naturaleza del rechazo cuando ``foreign``
    # existe. El detail es neutro porque previamente el caller validó
    # que el participant_id existe vía el select de payload_personas;
    # un 403 vs 404 diferenciaría "existe cross-sede" de "no existe".
    actor_sede = get_user_sede_id(db, current_user.id)
    if actor_sede is not None:
        foreign = [
            p for p in payload_personas
            if p.sede_id is not None and str(p.sede_id) != str(actor_sede)
        ]
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
    """List messages in a conversation (paginated, newest first)."""
    persona_id = _get_persona_id(db, current_user)
    if not persona_id:
        raise HTTPException(status_code=404, detail="Persona not found")
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
        raise HTTPException(status_code=403, detail="Not a participant of this conversation")
    _assert_conversation_sede_aligned(db, conv, current_user)
    rows = crud.get_conversation_messages(db, conv_id, limit=limit, before_id=before)
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
            is_read=(r.sender_id == current_user.id or (
                last_read is not None and r.created_at <= last_read
            )),
        )
        for r in rows
    ]


@router.post(
    "/chat/conversations/{conv_id}/messages",
    response_model=schemas.DirectMessageItem,
    status_code=status.HTTP_201_CREATED,
)
def send_direct_message(
    conv_id: str,
    payload: schemas.DirectMessageCreate,
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
    msg = crud.create_direct_message(db, conv_id, current_user.id, payload.content)
    persona = _get_persona(db, current_user)
    sender_name = _persona_display_name(persona)
    # Broadcast via WebSocket (safe no-op if no event loop available)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(
                manager.broadcast_event(
                    {
                        "event": "direct_message",
                        "conversation_id": conv_id,
                        "message": {
                            "id": msg.id,
                            "sender_id": str(current_user.id),
                            "sender_name": sender_name,
                            "content": msg.content,
                            "created_at": str(msg.created_at),
                        },
                    },
                    room=f"dm_{conv_id}",
                )
            )
    except RuntimeError:
        pass
    return schemas.DirectMessageItem(
        id=msg.id,
        sender_id=current_user.id,
        sender_name=sender_name,
        content=msg.content,
        created_at=msg.created_at,
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
    msg = db.query(models.ChatMessage).filter(models.ChatMessage.id == message_id).first()
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
