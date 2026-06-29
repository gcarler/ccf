"""Cross-sede (Multi-Tenant / Axioma 3) isolation tests for /api/messaging/*.

Cubre el gap documentado de ``backend/api/messaging.py`` antes del hardening:
``GET /messaging/history`` retornaba logs globales y ``POST /messaging/send``
permitía postear como persona de otra sede. Ambos endpoints ahora aplican
Axioma 3.

Patrón: dos ``Sede`` con admins distintos; asserts:
  * admin de sede_a NO lee/muta logs de sede_b (404/empty).
  * Same-sede access funciona (regresión).

Mirrors ``tests/test_crm_sede_isolation.py``. Usa helpers de ``tests/conftest``.
"""

from __future__ import annotations

import uuid as _uuid

from backend import models
from tests.conftest import auth_headers, seed_admin


def _seed_two_sedes(db_session):
    admin_a, persona_a, sede_a = seed_admin(
        db_session, email="msgA@example.com", password="testpass123"
    )
    admin_b, persona_b, sede_b = seed_admin(
        db_session, email="msgB@example.com", password="testpass123"
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


def _seed_log_legacy(db, persona, content: str, channel: str = "email"):
    """Sembrado directo vía SQL (bypass de API) para crear el target cross-sede.

    CommunicationLog no tiene ``sede_id`` propio; su ``persona_id`` es la
    única ancla para el scope check. Creamos el row sin pasar por la API
    endurecida para no contaminar el test (queremos probar APENAS el
    hardening del router, no del crud.create_communication_log legacy).
    """
    log = models.CommunicationLog(
        persona_id=persona.id,
        channel=channel,
        content=content,
        outcome="delivered",
    )
    db.add(log)
    db.flush()
    return log


# ── GET /messaging/history ────────────────────────────────────────────────


def test_messaging_history_filters_by_sede_a(
    client, db_session
):
    """Axioma 3 — Multi-Tenant: admin de sede_a sólo ve logs de su sede."""
    (admin_a, _, sede_a), (_, _, sede_b) = _seed_two_sedes(db_session)
    persona_a = _persona_in(db_session, sede_a.id, "msg-history-local-a")
    persona_b = _persona_in(db_session, sede_b.id, "msg-history-target-b")

    # Logs sembrados en sendas sedes.
    log_a = _seed_log_legacy(
        db_session, persona_a, "Mensaje legitimo de sede A"
    )
    log_b = _seed_log_legacy(
        db_session, persona_b, "MENSAJE SECRETO SEDE B"
    )
    db_session.commit()

    headers_a = auth_headers(client, email="msgA@example.com")
    resp = client.get("/api/messaging/history?limit=100", headers=headers_a)
    assert resp.status_code == 200, (
        f"/api/messaging/history no responde 200: {resp.status_code} {resp.text}"
    )
    payload = resp.json()
    returned_ids = {str(item["id"]) for item in payload}

    # log_a debe aparecer; log_b NO.
    assert str(log_a.id) in returned_ids, (
        "Regresión: log de sede_a NO aparece en el historial de admin A"
    )
    assert str(log_b.id) not in returned_ids, (
        f"FUGA: log de sede_b apareció en historial de admin A: {payload}"
    )
    # Defense-in-depth: chequear contenido por strings (no sólo IDs).
    body_text = resp.text
    assert "MENSAJE SECRETO SEDE B" not in body_text, (
        "FUGA CONFIRMADA: contenido de log de sede_b en respuesta a sede_a"
    )


def test_messaging_history_filters_by_sede_b(
    client, db_session
):
    """Axioma 3 — simetría: admin de sede_b NO debe ver logs de sede_a."""
    (admin_a, _, sede_a), (_, _, sede_b) = _seed_two_sedes(db_session)
    persona_a = _persona_in(db_session, sede_a.id, "msg-history-b-view-a")
    persona_b = _persona_in(db_session, sede_b.id, "msg-history-b-view-b")

    log_a = _seed_log_legacy(
        db_session, persona_a, "MENSAJE SECRETO SEDE A"
    )
    log_b = _seed_log_legacy(
        db_session, persona_b, "Mensaje legitimo de sede B"
    )
    db_session.commit()

    headers_b = auth_headers(client, email="msgB@example.com")
    resp = client.get("/api/messaging/history?limit=100", headers=headers_b)
    assert resp.status_code == 200, resp.text
    body_text = resp.text
    returned_ids = {str(item["id"]) for item in resp.json()}

    assert str(log_b.id) in returned_ids, (
        "Regresión: log de sede_b NO aparece en el historial de admin B"
    )
    assert str(log_a.id) not in returned_ids, (
        "FUGA: log de sede_a apareció en historial de admin B"
    )
    assert "MENSAJE SECRETO SEDE A" not in body_text, (
        "FUGA CONFIRMADA: contenido de log de sede_a en respuesta a sede_b"
    )


def test_messaging_history_supports_limit_param_locally(client, db_session):
    """Regresión: el param ``limit`` sigue siendo honored."""
    (_, _, sede_a), _ = _seed_two_sedes(db_session)
    persona_a = _persona_in(db_session, sede_a.id, "msg-history-limit-a")
    for i in range(5):
        _seed_log_legacy(
            db_session,
            persona_a,
            f"msg-{i}",
            channel=f"channel-{i}",
        )
    db_session.commit()

    headers_a = auth_headers(client, email="msgA@example.com")
    resp = client.get("/api/messaging/history?limit=3", headers=headers_a)
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 3, (
        f"limit=3 debe acotar a 3 logs; got {len(resp.json())}"
    )


# ── POST /messaging/send ──────────────────────────────────────────────────


def test_messaging_send_to_local_persona_succeeds(client, db_session):
    """Regresión: staff puede postear logs SOBRE personas de su propia sede."""
    (admin_a, _, sede_a), _ = _seed_two_sedes(db_session)
    persona_a = _persona_in(db_session, sede_a.id, "msg-send-local-a")

    headers_a = auth_headers(client, email="msgA@example.com")
    resp = client.post(
        "/api/messaging/send",
        headers=headers_a,
        json={
            "persona_id": str(persona_a.id),
            "channel": "internal",
            "content": "Mensaje pastoral legitimo de sede A",
        },
    )
    assert resp.status_code == 200, (
        f"Regresión: POST a persona local deberia funcionar "
        f"(status {resp.status_code}): {resp.text}"
    )
    data = resp.json()
    assert data["persona_id"] == str(persona_a.id)
    assert data["content"] == "Mensaje pastoral legitimo de sede A"

    # Sanity: el log se persistió
    persisted = (
        db_session.query(models.CommunicationLog)
        .filter(models.CommunicationLog.persona_id == persona_a.id)
        .first()
    )
    assert persisted is not None
    assert persisted.content == "Mensaje pastoral legitimo de sede A"


def test_messaging_send_to_cross_sede_persona_returns_404(client, db_session):
    """Axioma 3: staff NO puede postear logs sobre personas de otra sede.

    Existence-leak safe: 404 (no 403) para no filtrar si la persona existe
    en otra sede. Mismo contrato que el resto del CRM cross-sede.
    """
    (admin_a, _, sede_a), (_, _, sede_b) = _seed_two_sedes(db_session)
    persona_b = _persona_in(db_session, sede_b.id, "msg-send-target-b")

    headers_a = auth_headers(client, email="msgA@example.com")
    resp = client.post(
        "/api/messaging/send",
        headers=headers_a,
        json={
            "persona_id": str(persona_b.id),
            "channel": "internal",
            "content": "Mensaje cross-sede (deberia fallar)",
        },
    )
    assert resp.status_code == 404, (
        f"Leak: POST a persona de sede_b debería 404 "
        f"(status {resp.status_code}): {resp.text}"
    )

    # Sanity: NO se persistió ningún log de la fuga.
    leaked = (
        db_session.query(models.CommunicationLog)
        .filter(
            models.CommunicationLog.persona_id == persona_b.id
        )
        .first()
    )
    assert leaked is None, (
        "FUGA CONFIRMADA: log cross-sede persistido pese al 404"
    )


def test_messaging_send_to_invalid_uuid_returns_404(client, db_session):
    """Regresión: contract: 404 también para UUID inválido (existence-leak safe)."""
    (admin_a, _, _), _ = _seed_two_sedes(db_session)

    headers_a = auth_headers(client, email="msgA@example.com")
    resp = client.post(
        "/api/messaging/send",
        headers=headers_a,
        json={
            "persona_id": "not-a-uuid",
            "channel": "internal",
            "content": "should fail",
        },
    )
    assert resp.status_code == 404, (
        f"UUID inválido debería 404 (got {resp.status_code}): {resp.text}"
    )


# ── Combinaciones / edge cases ────────────────────────────────────────────


def test_two_post_cross_sede_isolated_on_subsequent_get(client, db_session):
    """End-to-end: cross-sede write 404 + cross-sede read 0 logs.

    Combina ambos vectores en un solo test e2e para reducir setup overhead
    y dejar explícito que ambos extremos del router están hardened.
    """
    (admin_a, _, sede_a), (_, _, sede_b) = _seed_two_sedes(db_session)
    persona_b = _persona_in(db_session, sede_b.id, "msg-e2e-target-b")
    persona_a_local = _persona_in(db_session, sede_a.id, "msg-e2e-local-a")

    headers_a = auth_headers(client, email="msgA@example.com")

    # 1. Intento cross-sede (write) → 404
    resp_write_cross = client.post(
        "/api/messaging/send",
        headers=headers_a,
        json={
            "persona_id": str(persona_b.id),
            "channel": "internal",
            "content": "ataque cross-sede",
        },
    )
    assert resp_write_cross.status_code == 404, resp_write_cross.text

    # 2. POST local (sanity)
    resp_write_local = client.post(
        "/api/messaging/send",
        headers=headers_a,
        json={
            "persona_id": str(persona_a_local.id),
            "channel": "internal",
            "content": "log legitimo en sede A",
        },
    )
    assert resp_write_local.status_code == 200, resp_write_local.text

    # 3. GET sólo ve el local; el cross-sede nunca llegó a la base.
    resp_read = client.get(
        "/api/messaging/history?limit=100", headers=headers_a
    )
    assert resp_read.status_code == 200, resp_read.text
    body = resp_read.text
    assert "ataque cross-sede" not in body, "FUGA cross-sede por write+read"
    assert "log legitimo en sede A" in body, (
        "Regresión: el log local legítimo debe aparecer en el historial"
    )
