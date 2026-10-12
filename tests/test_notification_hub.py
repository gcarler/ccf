"""Tests Fase 2 — Notification Hub (PLAN_NOTIFICACIONES_EMAIL_CCF.md).

Cubre:
  1. notify() crea in-app + fila pending en notification_deliveries respetando
     preferencias por canal.
  2. dedupe_key evita duplicados.
  3. deliver_pending() envía con SMTP stub (monkeypatch) y marca sent; regresó
     a failed tras agotar los intentos si el envío falla siempre.
  4. suppress_pending_for_notification marca suppressed los pendientes.
  5. Preferencias OFF: no se crea in-app ni email para ese evento/canal.
"""

from __future__ import annotations

from tests.conftest import seed_admin as _seed_admin


def _mk_admin(db_session):
    admin, persona, sede = _seed_admin(db_session)
    return admin, persona, sede


def test_notify_creates_in_app_and_pending_delivery(db_session):
    from backend.models_auth import NotificacionUsuario
    from backend.models_notifications import NotificationDelivery
    from backend.services.notification_hub import notify

    admin, persona, sede = _mk_admin(db_session)
    user_id = persona.id

    stats = notify(
        db_session,
        [user_id],
        event_type="task_assigned",
        title="Nueva tarea asignada: T1",
        content="Detalle",
        target_url="/plataforma/tasks/123",
        dedupe_key="task:123",
    )
    assert stats["created"] == 1
    assert stats["emails_queued"] == 1

    notif = db_session.query(NotificacionUsuario).filter(NotificacionUsuario.user_id == user_id).first()
    assert notif is not None
    delivery = db_session.query(NotificationDelivery).filter(NotificationDelivery.user_id == user_id).first()
    assert delivery is not None
    assert delivery.status == "pending"
    assert delivery.notification_id == notif.id


def test_notify_dedupe_skips_second_same_key(db_session):
    from backend.models_auth import NotificacionUsuario
    from backend.services.notification_hub import notify

    admin, persona, sede = _mk_admin(db_session)
    user_id = persona.id

    first = notify(
        db_session,
        [user_id],
        event_type="mention",
        title="Mención en comentario",
        content="x",
        target_url="/plataforma/chat",
        dedupe_key="comment:abc",
    )
    second = notify(
        db_session,
        [user_id],
        event_type="mention",
        title="Mención en comentario",
        content="x",
        target_url="/plataforma/chat",
        dedupe_key="comment:abc",
    )
    assert first["created"] == 1
    assert second["deduped"] == 1
    assert second["created"] == 0
    count = db_session.query(NotificacionUsuario).filter(NotificacionUsuario.user_id == user_id).count()
    assert count == 1


def test_notify_respects_silenced_channels(db_session):
    from backend.models_auth import NotificacionUsuario
    from backend.services.notification_hub import notify
    from backend.services.notification_preferences import get_or_create_user_preferences, set_preference

    admin, persona, sede = _mk_admin(db_session)
    user_id = persona.id
    get_or_create_user_preferences(db_session, user_id=user_id, sede_id=sede.id if sede else None)

    # Silenciar ambos canales para broadcast
    set_preference(db_session, user_id=user_id, channel="in_app", event_type="broadcast", enabled=False)
    set_preference(db_session, user_id=user_id, channel="email", event_type="broadcast", enabled=False)

    stats = notify(
        db_session,
        [user_id],
        event_type="broadcast",
        title="Anuncio",
        content="cuerpo",
    )
    assert stats["created"] == 0
    assert stats["emails_queued"] == 0
    assert db_session.query(NotificacionUsuario).filter(NotificacionUsuario.user_id == user_id).count() == 0


def test_deliver_pending_send_success(db_session, monkeypatch):
    from backend.models_notifications import NotificationDelivery
    from backend.services import email as email_svc
    from backend.services.notification_hub import deliver_pending, notify

    admin, persona, sede = _mk_admin(db_session)
    user_id = persona.id
    notify(
        db_session,
        [user_id],
        event_type="task_assigned",
        title="Task X",
        content="Detalle",
        dedupe_key="task:X",
    )

    sent_payload: dict = {}

    def _stub_send(to, subject, html, text=""):
        sent_payload["to"] = to
        sent_payload["subject"] = subject
        return True

    monkeypatch.setattr(email_svc, "send_email", _stub_send)

    out = deliver_pending(db_session, max_batch=10)
    assert out["sent"] == 1
    assert sent_payload["to"] == admin.email
    row = db_session.query(NotificationDelivery).filter(NotificationDelivery.user_id == user_id).first()
    assert row.status == "sent"
    assert row.delivered_at is not None
    assert row.attempts == 1
    assert row.recipient == admin.email


def test_deliver_pending_exhausts_attempts_and_fails(db_session, monkeypatch):
    from backend.models_notifications import NotificationDelivery
    from backend.services import email as email_svc
    from backend.services.notification_hub import deliver_pending, notify

    admin, persona, sede = _mk_admin(db_session)
    user_id = persona.id
    notify(
        db_session,
        [user_id],
        event_type="event_reminder",
        title="Recordatorio",
        content="cuerpo",
        dedupe_key="event:R1",
    )

    monkeypatch.setattr(email_svc, "send_email", lambda *a, **k: False)

    # 3 attempts máximo. Backoff exige 2^n*30s de edad — manipulamos
    # created_at/attempt para forzar reintentos inmediatos.
    for _ in range(3):
        rows = db_session.query(NotificationDelivery).filter(
            NotificationDelivery.status == "pending"
        ).all()
        for r in rows:
            import datetime as _dt
            r.created_at = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=1)
        out = deliver_pending(db_session, max_batch=10)

    row = db_session.query(NotificationDelivery).filter(
        NotificationDelivery.user_id == user_id
    ).first()
    assert row.status == "failed"
    assert row.attempts == 3


def test_suppress_pending_marks_read(db_session):
    from backend.models_notifications import NotificationDelivery
    from backend.services.notification_hub import notify, suppress_pending_for_notification

    admin, persona, sede = _mk_admin(db_session)
    user_id = persona.id
    stats = notify(
        db_session,
        [user_id],
        event_type="mention",
        title="Mención",
        content="x",
        dedupe_key="comment:suppress",
    )
    delivery = (
        db_session.query(NotificationDelivery)
        .filter(NotificationDelivery.user_id == user_id)
        .first()
    )
    n = suppress_pending_for_notification(db_session, delivery.notification_id)
    assert n == 1
    db_session.refresh(delivery)
    assert delivery.status == "suppressed"
    assert delivery.read_before_send is True
