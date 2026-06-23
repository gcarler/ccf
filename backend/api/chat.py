"""Direct Message endpoints — conversations and private messaging."""

from __future__ import annotations

import asyncio
import uuid as _uuid
from collections import Counter
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.auth import require_module_access
from backend.core.database import get_db
from backend.mesh_websockets import manager
from backend.models_shared import _utcnow
from backend.crud.crm import resolve_persona_id_for_user

router = APIRouter()


def _get_persona_id(db: Session, current_user: models.User):
    """Resuelve Persona.id (UUID) desde el usuario autenticado."""
    persona_id = resolve_persona_id_for_user(db, getattr(current_user, "id", None))
    return persona_id


def _get_persona(db: Session, current_user: models.User):
    persona_id = _get_persona_id(db, current_user)
    if not persona_id:
        return None
    return db.query(models.Persona).filter(models.Persona.id == persona_id).first()


def _persona_display_name(persona: models.Persona | None) -> str:
    if not persona:
        return "Usuario"
    return persona.nombre_completo or getattr(persona, "full_name", None) or "Usuario"


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
    from backend.crud.crm import get_user_sede_id

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


def _serialize_conversation(db: Session, conv: models.Conversation, current_user_id: _uuid.UUID, current_persona_id) -> schemas.ConversationRead:
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
        
    unread = crud.get_unread_count_for_conversation(db, conv.id, current_user_id)
    
    return schemas.ConversationRead(
        id=conv.id,
        participants=participants,
        last_message_content=conv.last_message_content,
        last_message_at=conv.last_message_at,
        last_sender_id=conv.last_sender_id, # Return Persona UUID
        unread_count=unread,
        created_at=conv.created_at,
    )


def _find_existing_dm(db: Session, user_id1: _uuid.UUID, user_id2: _uuid.UUID):
    """Check if a 2-person DM conversation already exists."""
    cps = (
        db.query(models.ConversationParticipant).filter(models.ConversationParticipant.user_id.in_([user_id1, user_id2])).all()
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
                return db.query(models.Conversation).filter(models.Conversation.id == conv_id).first()
    return None


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
    """Create a DM conversation with other users."""
    persona_id = _get_persona_id(db, current_user)
    if not persona_id:
        raise HTTPException(status_code=404, detail="Persona not found for current user")
    
    # Resolve all participant user_ids (UUIDs) from their persona UUIDs
    payload_personas = db.query(models.Persona).filter(models.Persona.id.in_(payload.participant_ids)).all()
    participant_user_ids = [p.id for p in payload_personas]
    if current_user.id not in participant_user_ids:
        participant_user_ids.append(current_user.id)
        
    if len(participant_user_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="A conversation needs at least 2 participants",
        )
    # Deduplicate for 2-person DMs
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
    rows = crud.get_conversation_messages(db, conv_id, limit=limit, before_id=before)
    sender_ids = {r.sender_id for r in rows}
    
    # Map sender UUIDs to Personas
    personas = db.query(models.Persona).filter(models.Persona.id.in_(sender_ids)).all() if sender_ids else []
    persona_map = {p.id: p for p in personas}
    
    last_read = is_participant.last_read_at
    return [
        schemas.DirectMessageItem(
            id=r.id,
            sender_id=r.sender_id, # Return Persona UUID
            sender_name=_persona_display_name(persona_map.get(r.sender_id)),
            content=r.content,
            created_at=r.created_at,
            is_read=(r.sender_id == current_user.id or (last_read is not None and r.created_at <= last_read)),
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
    """Send a message in a conversation."""
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
        raise HTTPException(status_code=403, detail="Not a participant")
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
                            "sender_id": str(current_user.id), # Return Persona UUID
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
        sender_id=current_user.id, # Return Persona UUID
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
    """Mark all messages as read in a conversation."""
    persona_id = _get_persona_id(db, current_user)
    if not persona_id:
        raise HTTPException(status_code=404, detail="Persona not found")
    crud.mark_conversation_read(db, conv_id, current_user.id)
    return {"ok": True}


@router.delete("/chat/messages/{message_id}")
def delete_chat_message_endpoint(
    message_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("messaging", "edit")),
):
    """Delete a chat message (own only)."""
    msg = db.query(models.ChatMessage).filter(models.ChatMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    persona_id = _get_persona_id(db, current_user)
    if not persona_id:
        raise HTTPException(status_code=404, detail="Persona not found")
    if msg.sender_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot delete another user's message")
    msg.deleted_at = _utcnow()
    msg.content = "[Mensaje eliminado]"
    db.commit()
    return {"ok": True}
