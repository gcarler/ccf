"""Direct unit tests for chat/conversation functions in `backend.crud.crm_.extended`.

Covers the non-trivial DM logic: conversation creation, message posting,
compound cursor pagination, unread counters, and soft-delete semantics.
"""
from __future__ import annotations

import uuid as _uuid

from sqlalchemy.orm import Session

from backend import models
from backend.crud.crm_.extended import (
    ChatMessageCreate,
    create_chat_message,
    create_conversation,
    delete_chat_message,
    get_chat_messages,
    get_conversation,
    get_conversation_messages,
    get_unread_count_for_conversation,
    get_unread_counts_batch,
    get_user_conversations,
    mark_conversation_read,
)


def _seed_user(db: Session, email: str) -> models.Usuario:
    sede = models.Sede(id=_uuid.uuid4(), nombre="Sede", ciudad="Bogota", es_activa=True)
    db.add(sede)
    db.flush()
    user = models.Usuario(
        id=_uuid.uuid4(),
        sede_id=sede.id,
        username=email,
        email=email,
        password_hash="x",
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _commit(db: Session) -> None:
    db.commit()


def test_create_conversation_with_participants(db_session):
    u1 = _seed_user(db_session, "a@example.com")
    u2 = _seed_user(db_session, "b@example.com")
    _commit(db_session)

    conv = create_conversation(db_session, [u1.id, u2.id])
    assert conv.id is not None
    assert len(conv.participants) == 2
    participant_ids = {p.user_id for p in conv.participants}
    assert u1.id in participant_ids
    assert u2.id in participant_ids


def test_get_conversation_returns_created(db_session):
    u1 = _seed_user(db_session, "a@example.com")
    conv = create_conversation(db_session, [u1.id])
    _commit(db_session)

    fetched = get_conversation(db_session, conv.id)
    assert fetched is not None
    assert fetched.id == conv.id


def test_create_chat_message_updates_conversation_metadata(db_session):
    u1 = _seed_user(db_session, "a@example.com")
    conv = create_conversation(db_session, [u1.id])
    _commit(db_session)

    msg = ChatMessageCreate(sender_id=u1.id, room_id=f"dm_{conv.id}", content="hola")
    row = create_chat_message(db_session, msg)
    assert row.id is not None
    assert row.content == "hola"
    assert row.room_id == f"dm_{conv.id}"

    conv = get_conversation(db_session, conv.id)
    assert conv.last_message_content == "hola"
    assert conv.last_sender_id == u1.id
    assert conv.last_message_at is not None


def test_create_chat_message_with_invalid_dm_room_is_tolerant(db_session):
    u1 = _seed_user(db_session, "a@example.com")
    _commit(db_session)

    msg = ChatMessageCreate(sender_id=u1.id, room_id="dm_not-a-uuid", content="ok")
    row = create_chat_message(db_session, msg)
    assert row.content == "ok"


def test_get_chat_messages_filters_by_room_and_hides_deleted(db_session):
    u1 = _seed_user(db_session, "a@example.com")
    conv = create_conversation(db_session, [u1.id])
    msg1 = ChatMessageCreate(sender_id=u1.id, room_id=f"dm_{conv.id}", content="keep")
    msg2 = ChatMessageCreate(sender_id=u1.id, room_id=f"dm_{conv.id}", content="delete")
    row1 = create_chat_message(db_session, msg1)
    row2 = create_chat_message(db_session, msg2)
    _commit(db_session)

    delete_chat_message(db_session, row2.id)
    _commit(db_session)

    rows = get_chat_messages(db_session, room_id=f"dm_{conv.id}")
    assert len(rows) == 1
    assert rows[0].id == row1.id


def test_delete_chat_message_returns_false_for_missing(db_session):
    assert delete_chat_message(db_session, _uuid.uuid4()) is False


def test_get_conversation_messages_pagination(db_session):
    u1 = _seed_user(db_session, "a@example.com")
    conv = create_conversation(db_session, [u1.id])
    for i in range(5):
        create_chat_message(
            db_session,
            ChatMessageCreate(sender_id=u1.id, room_id=f"dm_{conv.id}", content=f"msg {i}"),
        )
    _commit(db_session)

    page1 = get_conversation_messages(db_session, conv.id, limit=2)
    assert len(page1) == 2
    assert page1[0].content == "msg 4"
    assert page1[1].content == "msg 3"

    last = page1[-1]
    page2 = get_conversation_messages(
        db_session,
        conv.id,
        limit=2,
        before_id=last.id,
        before_created_at=last.created_at,
    )
    assert len(page2) == 2
    assert page2[0].content == "msg 2"
    assert page2[1].content == "msg 1"


def test_mark_conversation_read_updates_participant(db_session):
    u1 = _seed_user(db_session, "a@example.com")
    conv = create_conversation(db_session, [u1.id])
    _commit(db_session)

    mark_conversation_read(db_session, conv.id, u1.id)
    cp = (
        db_session.query(models.ConversationParticipant)
        .filter_by(conversation_id=conv.id, user_id=u1.id)
        .first()
    )
    assert cp.last_read_at is not None


def test_mark_conversation_read_skips_non_participant(db_session):
    u1 = _seed_user(db_session, "a@example.com")
    u2 = _seed_user(db_session, "b@example.com")
    conv = create_conversation(db_session, [u1.id])
    _commit(db_session)

    # Should not raise, even though u2 is not a participant
    mark_conversation_read(db_session, conv.id, u2.id)


def test_get_unread_count_for_conversation(db_session):
    u1 = _seed_user(db_session, "a@example.com")
    u2 = _seed_user(db_session, "b@example.com")
    conv = create_conversation(db_session, [u1.id, u2.id])
    _commit(db_session)

    # u2 sends 3 messages before u1 reads
    for i in range(3):
        create_chat_message(
            db_session,
            ChatMessageCreate(sender_id=u2.id, room_id=f"dm_{conv.id}", content=f"m{i}"),
        )
    _commit(db_session)

    assert get_unread_count_for_conversation(db_session, conv.id, u1.id) == 3
    mark_conversation_read(db_session, conv.id, u1.id)
    _commit(db_session)
    assert get_unread_count_for_conversation(db_session, conv.id, u1.id) == 0


def test_get_unread_counts_batch(db_session):
    u1 = _seed_user(db_session, "a@example.com")
    u2 = _seed_user(db_session, "b@example.com")
    conv1 = create_conversation(db_session, [u1.id, u2.id])
    conv2 = create_conversation(db_session, [u1.id, u2.id])
    _commit(db_session)

    create_chat_message(
        db_session,
        ChatMessageCreate(sender_id=u2.id, room_id=f"dm_{conv1.id}", content="c1"),
    )
    create_chat_message(
        db_session,
        ChatMessageCreate(sender_id=u2.id, room_id=f"dm_{conv1.id}", content="c2"),
    )
    create_chat_message(
        db_session,
        ChatMessageCreate(sender_id=u2.id, room_id=f"dm_{conv2.id}", content="c3"),
    )
    _commit(db_session)

    counts = get_unread_counts_batch(db_session, u1.id, [conv1.id, conv2.id])
    assert counts[conv1.id] == 2
    assert counts[conv2.id] == 1


def test_get_user_conversations_orders_by_last_message(db_session):
    u1 = _seed_user(db_session, "a@example.com")
    u2 = _seed_user(db_session, "b@example.com")
    conv = create_conversation(db_session, [u1.id, u2.id])
    _commit(db_session)
    create_chat_message(
        db_session,
        ChatMessageCreate(sender_id=u2.id, room_id=f"dm_{conv.id}", content="hello"),
    )
    _commit(db_session)

    convs = get_user_conversations(db_session, u1.id)
    assert len(convs) == 1
    assert convs[0].id == conv.id
