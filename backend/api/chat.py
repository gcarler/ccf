"""Direct Message endpoints — conversations and private messaging."""

from __future__ import annotations

import asyncio
from collections import Counter
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.auth import require_module_access
from backend.core.database import get_db
from backend.mesh_websockets import manager

router = APIRouter()


def _serialize_conversation(
    db: Session, conv: models.Conversation, current_user_id: int
) -> schemas.ConversationRead:
    participants = []
    for cp in conv.participants:
        user = db.query(models.User).filter(models.User.id == cp.user_id).first()
        participants.append(
            schemas.ConversationParticipantRead(
                user_id=cp.user_id,
                username=user.username if user else "Usuario",
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


def _find_existing_dm(db: Session, uid1: int, uid2: int):
    """Check if a 2-person DM conversation already exists."""
    cps = (
        db.query(models.ConversationParticipant)
        .filter(models.ConversationParticipant.user_id.in_([uid1, uid2]))
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
            pids = {
                cp.user_id
                for cp in all_cps
                if cp.conversation_id == conv_id
            }
            if pids == {uid1, uid2}:
                return (
                    db.query(models.Conversation)
                    .filter(models.Conversation.id == conv_id)
                    .first()
                )
    return None


@router.get(
    "/chat/conversations",
    response_model=List[schemas.ConversationRead],
)
def list_conversations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_module_access("messaging", "read")
    ),
):
    """List all DM conversations for the current user."""
    convs = crud.get_user_conversations(db, current_user.id)
    return [
        _serialize_conversation(db, c, current_user.id) for c in convs
    ]


@router.post(
    "/chat/conversations",
    response_model=schemas.ConversationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    payload: schemas.ConversationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_module_access("messaging", "edit")
    ),
):
    """Create a DM conversation with other users."""
    all_ids = list(set(payload.participant_ids + [current_user.id]))
    if len(all_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="A conversation needs at least 2 participants",
        )
    # Deduplicate for 2-person DMs
    if len(all_ids) == 2:
        existing = _find_existing_dm(db, all_ids[0], all_ids[1])
        if existing:
            return _serialize_conversation(db, existing, current_user.id)
    conv = crud.create_conversation(db, all_ids)
    return _serialize_conversation(db, conv, current_user.id)


@router.get(
    "/chat/conversations/{conv_id}/messages",
    response_model=List[schemas.DirectMessageItem],
)
def list_direct_messages(
    conv_id: int,
    limit: int = Query(50, le=200),
    before: Optional[int] = Query(None, alias="before"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_module_access("messaging", "read")
    ),
):
    """List messages in a conversation (paginated, newest first)."""
    conv = (
        db.query(models.Conversation)
        .filter(models.Conversation.id == conv_id)
        .first()
    )
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
        raise HTTPException(
            status_code=403, detail="Not a participant of this conversation"
        )
    rows = crud.get_conversation_messages(
        db, conv_id, limit=limit, before_id=before
    )
    sender_ids = {r.sender_id for r in rows}
    users = (
        db.query(models.User)
        .filter(models.User.id.in_(sender_ids))
        .all()
        if sender_ids
        else []
    )
    user_map = {u.id: u.username for u in users}
    return [
        schemas.DirectMessageItem(
            id=r.id,
            sender_id=r.sender_id,
            sender_name=user_map.get(r.sender_id, "Usuario"),
            content=r.content,
            created_at=r.created_at,
            is_read=r.is_read,
        )
        for r in rows
    ]


@router.post(
    "/chat/conversations/{conv_id}/messages",
    response_model=schemas.DirectMessageItem,
    status_code=status.HTTP_201_CREATED,
)
def send_direct_message(
    conv_id: int,
    payload: schemas.DirectMessageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_module_access("messaging", "edit")
    ),
):
    """Send a message in a conversation."""
    conv = (
        db.query(models.Conversation)
        .filter(models.Conversation.id == conv_id)
        .first()
    )
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
        raise HTTPException(
            status_code=403, detail="Not a participant"
        )
    msg = crud.create_direct_message(
        db, conv_id, current_user.id, payload.content
    )
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
                            "sender_id": msg.sender_id,
                            "sender_name": getattr(
                                current_user, "username", "Usuario"
                            ),
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
        sender_id=msg.sender_id,
        sender_name=getattr(current_user, "username", "Usuario"),
        content=msg.content,
        created_at=msg.created_at,
    )


@router.post("/chat/conversations/{conv_id}/read")
def mark_conversation_read_endpoint(
    conv_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_module_access("messaging", "read")
    ),
):
    """Mark all messages as read in a conversation."""
    crud.mark_conversation_read(db, conv_id, current_user.id)
    return {"ok": True}


@router.delete("/chat/messages/{message_id}")
def delete_chat_message_endpoint(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_module_access("messaging", "edit")
    ),
):
    """Delete a chat message (own only)."""
    msg = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.id == message_id)
        .first()
    )
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    if msg.sender_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Cannot delete another user's message"
        )
    db.delete(msg)
    db.commit()
    return {"ok": True}
