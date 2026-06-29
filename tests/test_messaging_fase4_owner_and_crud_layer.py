"""Axioma 3 — Fase 4: defense-in-depth en CRUD layer + ownership en notificaciones.

Cubre dos gaps identificados en code review de Fase 3:

1. ``crud.create_communication_log`` debe aceptar ``actor_user_id`` y
   re-validar scope (cierra TOCTOU donde un caller no-API — worker,
   script de seeding, llamada directa al CRUD — bypasea el check
   del API-layer). Mismo patrón que ``_crud_scope_re_check_task``.

2. ``PATCH /api/messaging/notifications/{id}`` debe validar ownership
   (BOLA-style leak prevention): el caller SÓLO puede modificar SUS
   PROPIAS notifications. 404 cross-user (existence-leak safe).

Patrón: dos ``Sede`` con admins distintos; asserts:
  * El CRUD rechaza el cross-sede WRITE con 404 pre-add.
  * El CRUD preserva back-compat para callers legacy (sin actor).
  * El CRUD respeta el superadmin bypass (actor sin sede).
  * El API rechaza el PATCH cross-user con 404.
  * El API permite el PATCH al dueño de la notificación.

Mirrors ``tests/test_crm_sede_isolation.py``. Usa ``tests/conftest``.
"""

from __future__ import annotations

import uuid as _uuid

from fastapi import HTTPException

from backend import crud, models, schemas
from tests.conftest import auth_headers, seed_admin


# ── Helpers (re-usan patrón de test_messaging_sede_isolation.py) ───────────


def _seed_two_sedes(db_session):
    admin_a, persona_a, sede_a = seed_admin(
        db_session, email="msgF4A@example.com", password="testpass123"
    )
    admin_b, persona_b, sede_b = seed_admin(
        db_session, email="msgF4B@example.com", password="testpass123"
    )
    assert sede_a.id != sede_b.id
    return (admin_a, persona_a, sede_a), (admin_b, persona_b, sede_b)


def _persona_in(db, sede_id, email_suffix):
    p = models.Persona(
        id=_uuid.uuid4(),
        first_name=f"User-{email_suffix}",
        last_name="Test",
        email=f"{email_suffix}@example.com",
        sede_id=sede_id,
        estado_vital="ACTIVO",
    )
    db.add(p)
    db.flush()
    return p


def _seed_notification(db, owner_user_id, title: str = "Notif Test"):
    """Sembrado directo vía SQL de una Notification para el owner_user_id."""
    notif = models.Notification(
        user_id=owner_user_id,
        title=title,
        content=f"Contenido de {title}",
        is_read=False,
    )
    db.add(notif)
    db.flush()
    return notif


# ── CRUD defense-in-depth: create_communication_log ───────────────────────


def test_crud_create_communication_log_blocks_cross_sede_when_actor_in_sede(db_session):
    """Axioma 3 — defense-in-depth: si el actor en sede_a intenta crear
    un log sobre persona de sede_b vía CRUD directo (bypass API-layer),
    el helper re-levanta 404 pre-flush.
    """
    (admin_a, _persona_a, _sede_a), (_, _, sede_b) = _seed_two_sedes(db_session)
    persona_b = _persona_in(db_session, sede_b.id, "crud-comm-cross-b")

    count_before = db_session.query(models.CommunicationLog).count()

    raised = False
    try:
        crud.create_communication_log(
            db_session,
            schemas.CommunicationLogCreate(
                persona_id=persona_b.id,  # cross-sede
                channel="internal",
                content="ataque cross-sede via CRUD directo",
            ),
            actor_user_id=str(admin_a.id),
        )
    except HTTPException as exc:
        raised = True
        assert exc.status_code == 404, (
            f"Cross-sede write en CRUD debe 404, got {exc.status_code}"
        )
        # Mensaje genérico (sin nombre del anchor) → no info leak
        assert "cross-sede" not in (exc.detail or "").lower(), (
            f"detail filtra anchor: {exc.detail!r}"
        )

    assert raised, (
        "El CRUD NO emitió HTTPException al validar scope — defense-in-depth falló"
    )
    db_session.rollback()
    count_after = db_session.query(models.CommunicationLog).count()
    assert count_after == count_before, (
        f"FUGA: log cross-sede persistido pese al 404 (Δ={count_after - count_before})"
    )


def test_crud_create_communication_log_blocks_orphan_when_actor_in_sede(db_session):
    """CRUD defense-in-depth: para un editor en sede, un CREATE con
    ``persona_id`` válido pero que NO existe en la DB es tratado como
    orphan (anchors irresolubles) y debe REJECUTAR 404. Esto prueba la
    rama ``_resolve_anchor_sede() returns None``.

    NOTA: ``schema.CommunicationLogCreate.persona_id: UUID`` (non-optional),
    por lo que ``None`` no llega al helper. El caso realista vía bypass
    API es un UUID válido pero sin fila correspondiente en ``personas``;
    ``_resolve_anchor_sede`` retorna ``None`` y el editor en sede es
    rechazado. Si el actor no tiene sede (superadmin), bypassea — cubierto
    por test_crud_create_communication_log_superadmin_bypass.
    """
    (admin_a, _, _), _ = _seed_two_sedes(db_session)

    raised = False
    ghost_persona_id = _uuid.uuid4()  # UUID válido, persona NO existe en DB
    try:
        crud.create_communication_log(
            db_session,
            schemas.CommunicationLogCreate(
                persona_id=ghost_persona_id,
                channel="internal",
                content="log con persona inexistente",
            ),
            actor_user_id=str(admin_a.id),
        )
    except HTTPException as exc:
        raised = True
        assert exc.status_code == 404, (
            f"Unresolvable persona_id anchor en CRUD debe 404, got {exc.status_code}"
        )

    assert raised, (
        "CRUD CREATE con persona inexistente bypasseó el scope re-check"
    )


def test_crud_create_communication_log_allows_local_persona_when_actor_in_sede(db_session):
    """Sanity regression: el path normal (actor + persona misma sede) funciona."""
    (admin_a, persona_a, _sede_a), _ = _seed_two_sedes(db_session)

    log = crud.create_communication_log(
        db_session,
        schemas.CommunicationLogCreate(
            persona_id=persona_a.id,
            channel="internal",
            content="log legitimo mismo-sede CRUD directo",
        ),
        actor_user_id=str(admin_a.id),
    )
    db_session.commit()
    assert log.id is not None
    assert log.persona_id == persona_a.id


def test_crud_create_communication_log_legacy_no_actor_allows_orphan(db_session):
    """Back-compat: callers legacy sin actor (bulk import, seed script,
    worker async) pueden crear filas aunque la persona sea cross-sede o
    no exista en DB. Esto preserva los seeds existentes y los workers.

    NOTA: ``schema.CommunicationLogCreate.persona_id: UUID`` (non-optional)
    rechaza ``None``. Por eso el \"orphan\" se modela como UUID válido
    pero sin fila ``Persona`` correspondiente — caso equivalente en
    términos del scope re-check (anchor irresoluble).
    """
    (admin_a, persona_a, _sede_a), (_, _, sede_b) = _seed_two_sedes(db_session)
    persona_b = _persona_in(db_session, sede_b.id, "crud-comm-legacy-b")

    # 1. Cross-sede + no actor → pasa (legacy)
    log_cross = crud.create_communication_log(
        db_session,
        schemas.CommunicationLogCreate(
            persona_id=persona_b.id,
            channel="internal",
            content="bulk import cross-sede",
        ),
    )
    db_session.commit()
    assert log_cross.id is not None
    assert log_cross.persona_id == persona_b.id

    # 2. Unresolvable anchor (UUID válido sin fila Persona) + no actor
    #    → pasa (legacy: el actor=None bypassea el scope re-check completo)
    log_orphan = crud.create_communication_log(
        db_session,
        schemas.CommunicationLogCreate(
            persona_id=_uuid.uuid4(),  # NO existe en DB
            channel="internal",
            content="bulk import unresolvable anchor",
        ),
    )
    db_session.commit()
    assert log_orphan.id is not None


def test_crud_create_communication_log_superadmin_bypass(db_session):
    """Bypass para actor sin sede asignada (típicamente superadmin/legacy).
    ``get_user_sede_id`` retorna ``None`` porque no hay user con ese
    UUID, así que el scope check queda inert.
    """
    (admin_a, _persona_a, _sede_a), (_, _, sede_b) = _seed_two_sedes(db_session)
    persona_b = _persona_in(db_session, sede_b.id, "crud-comm-superadmin-b")

    # UUID válido que NO corresponde a ningún user registrado.
    fake_superadmin_id = str(_uuid.uuid4())

    log = crud.create_communication_log(
        db_session,
        schemas.CommunicationLogCreate(
            persona_id=persona_b.id,  # cross-sede pero actor sin sede
            channel="internal",
            content="superadmin bypass",
        ),
        actor_user_id=fake_superadmin_id,
    )
    db_session.commit()
    assert log.id is not None
    assert log.persona_id == persona_b.id


# ── PATCH /api/messaging/notifications/{id} — ownership ──────────────────


def _seed_notification_for_persona(db_session, persona_user_id_uuid, title: str):
    """Sembrado directo vía SQL — bypass API-layer."""
    return _seed_notification(db_session, persona_user_id_uuid, title=title)


def test_patch_notification_blocks_cross_user_returns_404(client, db_session):
    """Axioma 3 — ownership: admin A intenta marcar como leída una
    notificación de admin B → 404 (existence-leak safe).
    """
    (admin_a, _persona_a, _), (admin_b, persona_b, _) = _seed_two_sedes(db_session)

    notif_b = _seed_notification_for_persona(
        db_session, admin_b.id, "LEAD SECRETO de admin B"
    )
    db_session.commit()

    headers_a = auth_headers(client, email="msgF4A@example.com")
    resp = client.patch(
        f"/api/messaging/notifications/{notif_b.id}",
        headers=headers_a,
    )
    assert resp.status_code == 404, (
        f"Leak: PATCH cross-user debería 404, got {resp.status_code}: {resp.text}"
    )

    # Sanity: la notification NO fue mutada
    db_session.refresh(notif_b)
    assert notif_b.is_read is False, (
        "FUGA: notificación cross-user marcada como leída pese al 404"
    )


def test_patch_notification_owner_update_succeeds(client, db_session):
    """Sanity regression: el dueño SÍ puede marcar su propia notification."""
    (admin_a, persona_a, _), _ = _seed_two_sedes(db_session)

    notif_a = _seed_notification_for_persona(
        db_session, admin_a.id, "notif legitima de admin A"
    )
    db_session.commit()

    headers_a = auth_headers(client, email="msgF4A@example.com")
    resp = client.patch(
        f"/api/messaging/notifications/{notif_a.id}",
        headers=headers_a,
    )
    assert resp.status_code == 200, (
        f"Regresión: PATCH propio debería 200, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert data["id"] == str(notif_a.id)
    assert data["is_read"] is True, (
        "El owner update debe estampar is_read=True"
    )

    # Sanity persistente
    db_session.refresh(notif_a)
    assert notif_a.is_read is True


def test_patch_notification_nonexistent_returns_404(client, db_session):
    """Regresión: PATCH a notification_id inexistente sigue siendo 404."""
    (admin_a, _, _), _ = _seed_two_sedes(db_session)
    headers_a = auth_headers(client, email="msgF4A@example.com")

    fake_id = str(_uuid.uuid4())
    resp = client.patch(
        f"/api/messaging/notifications/{fake_id}",
        headers=headers_a,
    )
    assert resp.status_code == 404, (
        f"Notification inexistente debería 404, got {resp.status_code}: {resp.text}"
    )


def test_patch_notification_invalid_uuid_returns_404(client, db_session):
    """Regresión: UUID inválido sigue siendo 404."""
    (admin_a, _, _), _ = _seed_two_sedes(db_session)
    headers_a = auth_headers(client, email="msgF4A@example.com")

    resp = client.patch(
        "/api/messaging/notifications/not-a-uuid",
        headers=headers_a,
    )
    assert resp.status_code == 404, (
        f"UUID inválido debería 404, got {resp.status_code}: {resp.text}"
    )


def test_mark_notification_as_read_without_owner_check_allows_backcompat(db_session):
    """Back-compat: callers legacy (sin owner_persona_id) pueden modificar
    notifications ajenas vía CRUD directo. Preserva scripts y bulk imports.
    """
    (admin_a, _persona_a, _), (admin_b, _, _) = _seed_two_sedes(db_session)
    notif_b = _seed_notification(db_session, admin_b.id, "notif legacy target")
    db_session.commit()

    # CRUD directo sin owner_persona_id → legacy bypass
    result = crud.mark_notification_as_read(db_session, notif_b.id)
    db_session.commit()
    assert result is not None, (
        "Sin owner_persona_id, el CRUD legacy debe retornar la notification"
    )
    assert result.is_read is True, "El mark-as-read legacy debe persistir"


# ── Cross-check end-to-end: API CRUD defense-in-depth propagado ──────────


def test_api_messaging_send_propagates_actor_user_id_to_crud(
    client, db_session, monkeypatch
):
    """Defense-in-depth: el router /api/messaging/send propaga
    ``actor_user_id`` (no ``None``) al CRUD de ``create_communication_log``.

    Spy-based: monkeypatcheamos ``crud.create_communication_log`` con un
    wrapper que captura kwargs, verificamos que ``actor_user_id`` recibe
    el valor del staff actual, y luego delegamos al original para que la
    respuesta HTTP siga siendo 200.

    Esto cubre el contrato del router de forma determinista sin
    pelearse con imports transitivos de ``get_user_sede_id`` desde
    ``crm._shared``.
    """
    (admin_a, persona_a, _), (_, _, _) = _seed_two_sedes(db_session)
    headers_a = auth_headers(client, email="msgF4A@example.com")

    captured_kwargs: dict = {}

    import backend.api.messaging as _messaging_module

    original_create = _messaging_module.crud.create_communication_log

    def _spy_create_communication_log(db, payload, **kwargs):
        captured_kwargs.update(kwargs)
        return original_create(db, payload, **kwargs)

    monkeypatch.setattr(
        _messaging_module.crud,
        "create_communication_log",
        _spy_create_communication_log,
    )

    resp = client.post(
        "/api/messaging/send",
        headers=headers_a,
        json={
            "persona_id": str(persona_a.id),
            "channel": "internal",
            "content": "spy: verificar propagacion",
        },
    )
    assert resp.status_code == 200, resp.text

    # Contract: actor_user_id kwarg propagado correctamente.
    assert "actor_user_id" in captured_kwargs, (
        f"El router DEBE propagar actor_user_id al CRUD; kwargs capturados: {captured_kwargs}"
    )
    assert captured_kwargs["actor_user_id"] == str(admin_a.id), (
        f"actor_user_id debe ser el id del staff actual; "
        f"got {captured_kwargs['actor_user_id']!r}, expected {str(admin_a.id)!r}"
    )
    assert captured_kwargs["actor_user_id"] is not None, (
        "actor_user_id NO debe ser None cuando el staff está autenticado"
    )


def _seed_sede_b_quick(db_session):
    """Crea una Sede extra + admin (helper dejado en archivo)."""
    admin_b_extra, persona_b_extra, sede_b_extra = seed_admin(
        db_session, email="msgF4B2@example.com", password="testpass123"
    )
    return admin_b_extra, persona_b_extra, sede_b_extra
