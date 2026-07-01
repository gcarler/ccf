"""Cross-sede (Multi-Tenant / Axioma 3) isolation tests for hardened CRM endpoints.

We seed two distinct `Sede` records with separate admins, then assert that:

  * An admin of sede_a NEVER reads/mutates entities belonging to sede_b through
    the hardened endpoints below (404, not 403, to avoid existence leaks).
  * Same-sede access still works (regression guard against over-scoping).
  * Counseling, prayer requests, grupos, messaging history, newsletter exports
    y subrutas persona/family están todos hardened por helpers de sede.

Mirrors tests/test_academy_api.py::test_*_isolate_by_sede. Uses
tests/conftest helpers (`seed_admin`, `auth_headers`, `LocalASGITestClient`).
"""

from __future__ import annotations

import uuid as _uuid

import pytest
from fastapi import HTTPException
from backend import models
from backend.models_crm_pipeline import (
    CanalOrigenEnum,
    EstadoCasoEnum,
    TipoPipelineEnum,
)
from tests.conftest import auth_headers, seed_admin


def _seed_two_sedes(db_session):
    admin_a, persona_a, sede_a = seed_admin(
        db_session, email="aboxA@example.com", password="testpass123"
    )
    admin_b, persona_b, sede_b = seed_admin(
        db_session, email="aboxB@example.com", password="testpass123"
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


def test_get_update_patch_delete_persona_blocks_cross_sede(client, db_session):
    """Axioma 3: CRUD persona endpoints leak no cross-sede data (404, no 403)."""
    (admin_a, _, sede_a), (admin_b, _, sede_b) = _seed_two_sedes(db_session)
    persona_b = _persona_in(db_session, sede_b.id, "leak-target-b")

    # Sanity: persona_b is in sede_b, NOT in sede_a
    assert persona_b.sede_id == sede_b.id
    assert persona_b.sede_id != sede_a.id

    headers_a = auth_headers(client, email="aboxA@example.com")
    persona_id_str = str(persona_b.id)

    # GET cross-sede → 404
    resp = client.get(f"/api/crm/personas/{persona_id_str}", headers=headers_a)
    assert resp.status_code == 404, (
        f"Leak: admin de sede_a leyó persona de sede_b (status {resp.status_code}, body={resp.text})"
    )

    # PUT cross-sede → 404
    resp = client.put(
        f"/api/crm/personas/{persona_id_str}",
        headers=headers_a,
        json={"church_role": "Miembro-edit"},
    )
    assert resp.status_code == 404, f"Leak: PUT cross-sede no fue 404 (got {resp.status_code})"

    # PATCH cross-sede → 404
    resp = client.patch(
        f"/api/crm/personas/{persona_id_str}",
        headers=headers_a,
        json={"church_role": "Servidor"},
    )
    assert resp.status_code == 404, f"Leak: PATCH cross-sede no fue 404 (got {resp.status_code})"

    # DELETE cross-sede → 404
    resp = client.delete(f"/api/crm/personas/{persona_id_str}", headers=headers_a)
    assert resp.status_code == 404, f"Leak: DELETE cross-sede no fue 404 (got {resp.status_code})"

    # DELETE timeline cross-sede → 404
    resp = client.get(f"/api/crm/personas/{persona_id_str}/timeline", headers=headers_a)
    assert resp.status_code == 404, f"Leak: timeline cross-sede no fue 404 (got {resp.status_code})"

    # Sanity: la persona NO fue mutada por el admin A cross-sede
    db_session.refresh(persona_b)
    assert persona_b.church_role != "Miembro-edit", "El church_role NO debe mutarse cross-sede"
    assert persona_b.church_role != "Servidor", "El church_role NO debe mutarse cross-sede"
    assert persona_b.estado_vital != "INACTIVO", "La persona NO debe soft-deletearse cross-sede"

    # Sanity: admin_b SÍ puede leer su propia persona (regresión)
    headers_b = auth_headers(client, email="aboxB@example.com")
    resp_ok = client.get(f"/api/crm/personas/{persona_id_str}", headers=headers_b)
    assert resp_ok.status_code == 200, (
        f"Regresión: admin_b no puede leer su propia persona (status {resp_ok.status_code})"
    )


def test_persona_donations_blocks_cross_sede(client, db_session):
    """Axioma 3: persona_donations sólo se expone para personas del scope de sede."""
    (admin_a, _, _), (_, _, _) = _seed_two_sedes(db_session)
    (_, _, sede_b) = seed_admin(db_session, email="sedeB-donations@example.com", password="testpass123")
    persona_b = _persona_in(db_session, sede_b.id, "donations-target-b")
    secret_donation = models.Donation(
        persona_id=persona_b.id,
        amount=9999.99,
        currency="COP",
        sede_id=sede_b.id,
        donation_type="Diezmo",
        status="completed",
        payment_method="Transferencia",
    )
    db_session.add(secret_donation)
    db_session.commit()

    headers_a = auth_headers(client, email="aboxA@example.com")
    resp = client.get(f"/api/crm/personas/{persona_b.id}/donations", headers=headers_a)
    assert resp.status_code == 404, (
        f"Leak: admin A vio donations de sede_b; status {resp.status_code}, body={resp.text}"
    )
    assert "9999" not in resp.text, "FUGA CONFIRMADA: monto de donación cross-sede en respuesta"


def test_persona_subroutes_block_cross_sede(client, db_session):
    """Sub-rutas /personas/{id}/communications, /ministries, /consolidation."""
    (admin_a, _, sede_a), (admin_b, _, sede_b) = _seed_two_sedes(db_session)
    persona_b = _persona_in(db_session, sede_b.id, "subr-target-b")
    fake_comm = models.CommunicationLog(
        persona_id=persona_b.id,
        channel="whatsapp",
        content="secret pastoral content from sede B",
        outcome="delivered",
    )
    db_session.add(fake_comm)
    db_session.commit()

    headers_a = auth_headers(client, email="aboxA@example.com")
    pid = str(persona_b.id)

    resp = client.get(f"/api/crm/personas/{pid}/communications", headers=headers_a)
    assert resp.status_code == 404, (
        f"Leak comunicaciones cross-sede: status {resp.status_code} body={resp.text}"
    )
    assert "secret pastoral" not in resp.text, (
        "FUGA CONFIRMADA: communications de sede_b llegaron a la respuesta"
    )

    resp = client.get(f"/api/crm/personas/{pid}/ministries", headers=headers_a)
    assert resp.status_code == 404, f"Leak ministries cross-sede: {resp.status_code}"

    resp = client.get(f"/api/crm/personas/{pid}/consolidation", headers=headers_a)
    assert resp.status_code == 404, f"Leak consolidation cross-sede: {resp.status_code}"


def test_list_families_scoped_by_sede(client, db_session):
    """Axioma 3: list_families no expone familias de otras sedes indirectamente."""
    (admin_a, _, sede_a), (admin_b, _, sede_b) = _seed_two_sedes(db_session)

    fam_a = models.Family(name="Familia A")
    fam_b = models.Family(name="Familia B (cross-sede target)")
    db_session.add_all([fam_a, fam_b])
    db_session.flush()

    p_a = models.Persona(
        id=_uuid.uuid4(),
        first_name="AnchorA",
        last_name="X",
        email="anchorA@example.com",
        sede_id=sede_a.id,
        family_id=fam_a.id,
        estado_vital="ACTIVO",
    )
    p_b = models.Persona(
        id=_uuid.uuid4(),
        first_name="AnchorB",
        last_name="X",
        email="anchorB@example.com",
        sede_id=sede_b.id,
        family_id=fam_b.id,
        estado_vital="ACTIVO",
    )
    db_session.add_all([p_a, p_b])
    db_session.commit()

    headers_a = auth_headers(client, email="aboxA@example.com")
    headers_b = auth_headers(client, email="aboxB@example.com")

    resp_a = client.get("/api/crm/families/", headers=headers_a)
    assert resp_a.status_code == 200
    names_a = {f["name"] for f in resp_a.json()}
    assert "Familia A" in names_a
    assert "Familia B (cross-sede target)" not in names_a, (
        f"FUGA: admin A ve familia B: {names_a}"
    )

    resp_b = client.get("/api/crm/families/", headers=headers_b)
    assert resp_b.status_code == 200
    names_b = {f["name"] for f in resp_b.json()}
    assert "Familia B (cross-sede target)" in names_b
    assert "Familia A" not in names_b, (
        f"FUGA: admin B ve familia A: {names_b}"
    )


def test_get_family_detail_blocks_cross_sede(client, db_session):
    """get_family/{family_id} devuelve 404 cuando ningún miembro está en la sede del caller."""
    (admin_a, _, sede_a), (admin_b, _, sede_b) = _seed_two_sedes(db_session)
    fam_b = models.Family(name="Familia B")
    db_session.add(fam_b)
    db_session.flush()
    p_b = models.Persona(
        id=_uuid.uuid4(),
        first_name="MemberB",
        last_name="X",
        email="memberB@example.com",
        sede_id=sede_b.id,
        family_id=fam_b.id,
        estado_vital="ACTIVO",
    )
    db_session.add(p_b)
    db_session.commit()

    headers_a = auth_headers(client, email="aboxA@example.com")
    resp = client.get(f"/api/crm/family/{fam_b.id}", headers=headers_a)
    assert resp.status_code == 404, (
        f"Leak: admin A leyó family de sede_b; status {resp.status_code}, body={resp.text}"
    )


def test_regression_admin_block_role_assignment_cross_sede(client, db_session):
    """No se puede asignar role/position a una persona de otra sede (403/404)."""
    (admin_a, _, _), (_, persona_b, _) = _seed_two_sedes(db_session)

    position = models.Position(name="Lider Test", category="Liderazgo")
    db_session.add(position)
    db_session.commit()

    headers_a = auth_headers(client, email="aboxA@example.com")

    resp = client.post(
        f"/api/crm/personas/{persona_b.id}/positions",
        headers=headers_a,
        json={
            "persona_id": str(persona_b.id),
            "position_id": str(position.id),
            "start_date": "2024-01-01",
            "is_active": True,
        },
    )
    assert resp.status_code == 404, (
        f"Leak: admin A asignó position a persona de sede_b; status {resp.status_code} body={resp.text}"
    )


# ── Pastoral endpoints cross-sede (Axioma 3 — Fase 2) ──────────────────────


def test_get_counseling_detail_blocks_cross_sede(client, db_session):
    """get_counseling_detail: ticket está en sede_b ⇒ admin A recibe 404 y
    el contenido pastoral confidencial NO debe llegar a la respuesta.
    """
    (admin_a, _, _), (_, _, sede_b) = _seed_two_sedes(db_session)
    persona_b = _persona_in(db_session, sede_b.id, "counsel-target-b")
    secret_ticket = models.CounselingTicket(
        persona_id=persona_b.id,
        pastor_id=persona_b.id,
        subject="Abuso espiritual confidencial",
        notes="encrypted-not-exported",
        status="open",
        priority_level="URGENT",
    )
    db_session.add(secret_ticket)
    db_session.commit()

    headers_a = auth_headers(client, email="aboxA@example.com")
    resp = client.get(f"/api/crm/counseling/{secret_ticket.id}", headers=headers_a)
    assert resp.status_code == 404, (
        f"Leak counseling cross-sede: status {resp.status_code}, body={resp.text}"
    )
    assert "Abuso espiritual" not in resp.text, (
        "FUGA CONFIRMADA: tema pastoral de sede_b expuesto a sede_a"
    )


def test_create_counseling_ticket_blocks_cross_sede(client, db_session):
    """Axioma 3: create_counseling_ticket rechaza crear tickets con personas
    de otra sede. CounselingTicket no tiene sede_id propio; el scope se aplica
    validando que la FK a Persona pertenece a la sede del editor.
    """
    (admin_a, _, sede_a), (_, _, sede_b) = _seed_two_sedes(db_session)
    persona_b = _persona_in(db_session, sede_b.id, "counsel-create-target-b")
    persona_a = _persona_in(db_session, sede_a.id, "counsel-create-local-a")

    headers_a = auth_headers(client, email="aboxA@example.com")

    # 1. Cross-sede: admin A intenta crear ticket para persona de sede_b → 404
    resp = client.post(
        "/api/crm/counseling/",
        headers=headers_a,
        json={
            "persona_id": str(persona_b.id),
            "subject": "Ticket cross-sede (deberia fallar)",
            "notes": "contenido confidencial de sede_b",
            "priority_level": "NORMAL",
            "status": "open",
        },
    )
    assert resp.status_code == 404, (
        f"Leak create_counseling_ticket cross-sede: status {resp.status_code}, body={resp.text}"
    )

    # Sanity: NO se creó ningún ticket en la base de datos
    leaked = (
        db_session.query(models.CounselingTicket)
        .filter(models.CounselingTicket.persona_id == persona_b.id)
        .first()
    )
    assert leaked is None, (
        "FUGA CONFIRMADA: ticket de sede_b fue persistido a pesar del cross-sede"
    )

    # 2. Sanity positiva: admin A SÍ puede crear ticket para su propia persona
    resp_ok = client.post(
        "/api/crm/counseling/",
        headers=headers_a,
        json={
            "persona_id": str(persona_a.id),
            "subject": "Ticket legitimo en sede_a",
            "notes": "contenido pastoral de sede_a",
            "priority_level": "NORMAL",
            "status": "open",
        },
    )
    assert resp_ok.status_code == 201, (
        f"Regresión: admin A no puede crear ticket en su sede (status {resp_ok.status_code}, body={resp_ok.text})"
    )
    data = resp_ok.json()
    assert data["persona_id"] == str(persona_a.id)
    assert data["topic"] == "Ticket legitimo en sede_a"


def test_create_counseling_ticket_pastor_id_resolves_and_validates_scope(client, db_session):
    """Axioma 3: pastor_id acepta sólo UUID canónico de persona en scope."""
    (admin_a, _, sede_a), (admin_b, persona_b, sede_b) = _seed_two_sedes(db_session)
    persona_a_local = _persona_in(db_session, sede_a.id, "pastor-test-local-a")
    persona_a_target = _persona_in(db_session, sede_a.id, "pastor-test-target-a")
    headers_a = auth_headers(client, email="aboxA@example.com")

    # 1. pastor_id como UUID de persona local (misma sede) → 201
    resp = client.post(
        "/api/crm/counseling/",
        headers=headers_a,
        json={
            "persona_id": str(persona_a_target.id),
            "pastor_id": str(persona_a_local.id),
            "subject": "ticket con pastor local UUID",
            "notes": "test",
            "priority_level": "NORMAL",
            "status": "open",
        },
    )
    assert resp.status_code == 201, (
        f"Regresión: pastor_id como UUID local deberia funcionar (status {resp.status_code}): {resp.text}"
    )

    # 2. El UUID canónico de la persona de otra sede queda fuera de scope.
    resp_cross_user = client.post(
        "/api/crm/counseling/",
        headers=headers_a,
        json={
            "persona_id": str(persona_a_target.id),
            "pastor_id": str(admin_b.id),  # Integer user_id de sede_b
            "subject": "ticket con pastor cross-sede via user_id",
            "notes": "test",
            "priority_level": "NORMAL",
            "status": "open",
        },
    )
    assert resp_cross_user.status_code == 404, (
        f"pastor_id cross-sede debe rechazarse (status {resp_cross_user.status_code}): {resp_cross_user.text}"
    )
    # Sanity: NO se persistió el ticket cross-sede
    leaked_rows = (
        db_session.query(models.CounselingTicket)
        .filter(
            models.CounselingTicket.persona_id == persona_a_target.id,
            models.CounselingTicket.subject == "ticket con pastor cross-sede via user_id",
        )
        .all()
    )
    assert len(leaked_rows) == 0, (
        f"FUGA: {len(leaked_rows)} ticket(s) cross-sede persistido(s) pese al 404"
    )

    # 3. El actor local comparte el UUID canónico de su Persona.
    resp_local_user = client.post(
        "/api/crm/counseling/",
        headers=headers_a,
        json={
            "persona_id": str(persona_a_target.id),
            "pastor_id": str(admin_a.id),  # Integer user_id de sede_a
            "subject": "ticket con pastor local via user_id",
            "notes": "test",
            "priority_level": "NORMAL",
            "status": "open",
        },
    )
    assert resp_local_user.status_code == 201, (
        f"pastor_id local canónico debe funcionar (status {resp_local_user.status_code}): {resp_local_user.text}"
    )

    # 4. Un string no UUID falla en la frontera Pydantic.
    resp_invalid = client.post(
        "/api/crm/counseling/",
        headers=headers_a,
        json={
            "persona_id": str(persona_a_target.id),
            "pastor_id": "not-a-uuid-or-integer",
            "subject": "ticket con pastor inválido",
            "notes": "test",
            "priority_level": "NORMAL",
            "status": "open",
        },
    )
    assert resp_invalid.status_code == 422, (
        f"Pastor_id inválido deberia 422 (status {resp_invalid.status_code}): {resp_invalid.text}"
    )

    # 5. Un entero serializado tampoco forma parte del contrato UUID.
    resp_nonexistent_user = client.post(
        "/api/crm/counseling/",
        headers=headers_a,
        json={
            "persona_id": str(persona_a_target.id),
            "pastor_id": "999999999",  # user_id que no existe
            "subject": "ticket con user_id inexistente",
            "notes": "test",
            "priority_level": "NORMAL",
            "status": "open",
        },
    )
    assert resp_nonexistent_user.status_code == 422, (
        f"Identidad no UUID deberia 422 (status {resp_nonexistent_user.status_code}): {resp_nonexistent_user.text}"
    )


def test_update_counseling_ticket_blocks_cross_sede(client, db_session):
    """Axioma 3: update_counseling_ticket rechaza leer/mutar tickets de otra
    sede (helper _get_scoped_counseling_ticket) y rechaza pastor_id cross-sede
    (helper _resolve_pastor_identity, mismo patrón que create_counseling_ticket).
    """
    (admin_a, persona_a_admin, sede_a), (admin_b, persona_b_admin, sede_b) = _seed_two_sedes(db_session)
    persona_a_local = _persona_in(db_session, sede_a.id, "update-counsel-local-a")
    persona_b_local = _persona_in(db_session, sede_b.id, "update-counsel-target-b")

    # Ticket en sede_b (admin A NO debe poder verlo ni mutarlo)
    secret_ticket = models.CounselingTicket(
        persona_id=persona_b_local.id,
        pastor_id=persona_b_admin.id,
        subject="Tema confidencial sede_b",
        notes="encrypted-not-exported",
        status="open",
        priority_level="NORMAL",
    )
    db_session.add(secret_ticket)
    db_session.commit()

    # Ticket en sede_a (admin A SÍ puede mutarlo)
    local_ticket = models.CounselingTicket(
        persona_id=persona_a_local.id,
        pastor_id=persona_a_admin.id,
        subject="Tema local sede_a",
        notes="local",
        status="open",
        priority_level="NORMAL",
    )
    db_session.add(local_ticket)
    db_session.commit()

    headers_a = auth_headers(client, email="aboxA@example.com")

    # 1. Cross-sede ticket: admin A intenta PATCH → 404 (no debe leerlo)
    resp_cross = client.patch(
        f"/api/crm/counseling/{secret_ticket.id}",
        headers=headers_a,
        json={"status": "resolved", "notes": "mutado cross-sede (deberia fallar)"},
    )
    assert resp_cross.status_code == 404, (
        f"Leak update_counseling_ticket cross-sede: status {resp_cross.status_code}, body={resp_cross.text}"
    )
    # Sanity: el ticket NO fue mutado
    db_session.refresh(secret_ticket)
    assert secret_ticket.status == "open", "El ticket cross-sede NO debe mutarse"
    assert secret_ticket.notes == "encrypted-not-exported", "Las notas cross-sede NO deben modificarse"

    # 2. Sanity positiva: admin A puede mutar su propio ticket → 200
    resp_local = client.patch(
        f"/api/crm/counseling/{local_ticket.id}",
        headers=headers_a,
        json={"status": "in_progress", "notes": "mutado localmente"},
    )
    assert resp_local.status_code == 200, (
        f"Regresión: admin A no puede mutar su ticket (status {resp_local.status_code}): {resp_local.text}"
    )
    db_session.refresh(local_ticket)
    assert local_ticket.status == "in_progress"

    # 3. pastor_id cross-sede: admin A intenta asignar pastor de sede_b → 404
    resp_pastor_cross = client.patch(
        f"/api/crm/counseling/{local_ticket.id}",
        headers=headers_a,
        json={
            "pastor_id": str(persona_b_admin.id),  # UUID de persona en sede_b
            "status": "open",
        },
    )
    assert resp_pastor_cross.status_code == 404, (
        f"Leak pastor_id cross-sede en update: status {resp_pastor_cross.status_code}, body={resp_pastor_cross.text}"
    )
    # Sanity: el ticket NO debe haber mutado el pastor_id
    db_session.refresh(local_ticket)
    assert str(local_ticket.pastor_id) != str(persona_b_admin.id), (
        "El pastor_id NO debe haberse mutado a un cross-sede"
    )

    # 4. El UUID canónico cross-sede continúa fuera de scope.
    resp_pastor_user_cross = client.patch(
        f"/api/crm/counseling/{local_ticket.id}",
        headers=headers_a,
        json={
            "pastor_id": str(admin_b.id),  # user_id Integer de sede_b
            "status": "open",
        },
    )
    assert resp_pastor_user_cross.status_code == 404, (
        f"Leak pastor_id como user_id cross-sede en update: status {resp_pastor_user_cross.status_code}, body={resp_pastor_user_cross.text}"
    )

    # 5. El UUID canónico de la persona local es válido.
    resp_pastor_user_local = client.patch(
        f"/api/crm/counseling/{local_ticket.id}",
        headers=headers_a,
        json={
            "pastor_id": str(admin_a.id),  # user_id Integer de sede_a
            "status": "open",
        },
    )
    assert resp_pastor_user_local.status_code == 200, (
        f"pastor_id local canónico debe funcionar (status {resp_pastor_user_local.status_code}): {resp_pastor_user_local.text}"
    )


def test_get_prayer_request_detail_blocks_cross_sede(client, db_session):
    """PrayerRequest tiene sede_id propio; admin A no debe ver el de sede_b."""
    (admin_a, _, _), (_, _, sede_b) = _seed_two_sedes(db_session)
    secret_prayer = models.PrayerRequest(
        requester_name="Anónimo B",
        request_text="Oración secreta por conflicto familiar en sede B",
        category="Familia",
        sede_id=sede_b.id,
        status="private",
    )
    db_session.add(secret_prayer)
    db_session.commit()

    headers_a = auth_headers(client, email="aboxA@example.com")
    resp = client.get(
        f"/api/crm/prayer-requests/{secret_prayer.id}", headers=headers_a
    )
    assert resp.status_code == 404, (
        f"Leak prayer cross-sede: status {resp.status_code}, body={resp.text}"
    )
    assert "conflicto familiar" not in resp.text, (
        "FUGA CONFIRMADA: prayer text de sede_b en respuesta a sede_a"
    )


def test_get_grupo_detail_blocks_cross_sede(client, db_session):
    """GrupoEvangelismo: scope por sede_id; GET cross-sede → 404."""
    (admin_a, _, _), (_, _, sede_b) = _seed_two_sedes(db_session)
    grupo_b = models.GrupoEvangelismo(
        nombre="Grupo B Secreto",
        codigo=f"GB-{_uuid.uuid4().hex[:6]}",
        sede_id=sede_b.id,
        activo=True,
    )
    db_session.add(grupo_b)
    db_session.commit()

    headers_a = auth_headers(client, email="aboxA@example.com")
    resp = client.get(f"/api/crm/grupos/{grupo_b.id}", headers=headers_a)
    assert resp.status_code == 404, (
        f"Leak grupo detail cross-sede: status {resp.status_code}, body={resp.text}"
    )
    assert "Grupo B Secreto" not in resp.text, (
        "FUGA CONFIRMADA: nombre de grupo de sede_b en respuesta a sede_a"
    )


def test_update_grupo_blocks_cross_sede(client, db_session):
    """update_grupo (PUT): mutación cross-sede debe ser 404 antes de tocar el row."""
    (admin_a, _, _), (_, _, sede_b) = _seed_two_sedes(db_session)
    grupo_b = models.GrupoEvangelismo(
        nombre="Grupo B Original",
        codigo=f"GB-ORIG-{_uuid.uuid4().hex[:6]}",
        sede_id=sede_b.id,
        activo=True,
    )
    db_session.add(grupo_b)
    db_session.commit()

    headers_a = auth_headers(client, email="aboxA@example.com")
    resp = client.put(
        f"/api/crm/grupos/{grupo_b.id}",
        headers=headers_a,
        json={"name": "Grupo B Editado Por A (debería fallar)"},
    )
    assert resp.status_code == 404, (
        f"Leak update_grupo cross-sede: status {resp.status_code}, body={resp.text}"
    )

    # Sanity: el grupo NO debe haber sido mutado
    db_session.refresh(grupo_b)
    assert grupo_b.nombre == "Grupo B Original", (
        "El grupo NO debe mutarse cross-sede"
    )


def test_get_messaging_history_item_blocks_cross_sede(client, db_session):
    """get_messaging/history/{log_id}: log NO tiene sede_id propio; el scope
    se aplica vía JOIN Persona.sede_id. Cross-sede debe ser 404.
    """
    (admin_a, _, _), (_, _, sede_b) = _seed_two_sedes(db_session)
    persona_b = _persona_in(db_session, sede_b.id, "comm-target-b")
    secret_log = models.CommunicationLog(
        persona_id=persona_b.id,
        channel="email",
        content="Mensaje confidencial del pastor de sede B",
        outcome="delivered",
    )
    db_session.add(secret_log)
    db_session.commit()

    headers_a = auth_headers(client, email="aboxA@example.com")
    resp = client.get(f"/api/crm/messaging/history/{secret_log.id}", headers=headers_a)
    assert resp.status_code == 404, (
        f"Leak messaging history cross-sede: status {resp.status_code}, body={resp.text}"
    )
    assert "Mensaje confidencial" not in resp.text, (
        "FUGA CONFIRMADA: contenido de mensaje de sede_b en respuesta a sede_a"
    )


def test_export_newsletter_leads_csv_blocks_cross_sede(client, db_session):
    """Axioma 3: el export de leads NO debe exponer casos de otra sede.

    El endpoint filtra via JOIN con Persona (`Persona.sede_id == user_sede`).
    Sin ese filtro, admin A vería leads de sede_b. CasoCRM requiere
    `pipeline_id` y `etapa_actual_id` NOT NULL → hay que crear el pipeline
    y la etapa antes de instanciar el caso.

    El origen canónico es WEB_FORM y el detalle conserva ``newsletter-web``.
    """
    (admin_a, _, sede_a), (_, _, sede_b) = _seed_two_sedes(db_session)

    # Setup pipeline + etapa por sede (CasoCRM.pipeline_id/etapa_actual_id son NOT NULL)
    pipeline_a = models.PipelineCRM(
        sede_id=sede_a.id,
        nombre="Pipeline A",
        tipo=TipoPipelineEnum.NUEVOS_VISITANTES,
    )
    pipeline_b = models.PipelineCRM(
        sede_id=sede_b.id,
        nombre="Pipeline B",
        tipo=TipoPipelineEnum.NUEVOS_VISITANTES,
    )
    db_session.add_all([pipeline_a, pipeline_b])
    db_session.flush()
    etapa_a = models.EtapaPipeline(pipeline_id=pipeline_a.id, nombre="Etapa 1", orden=1)
    etapa_b = models.EtapaPipeline(pipeline_id=pipeline_b.id, nombre="Etapa 1", orden=1)
    db_session.add_all([etapa_a, etapa_b])
    db_session.flush()

    # Personas ancladas a su sede
    persona_a_local = _persona_in(db_session, sede_a.id, "newsletter-leads-local")
    persona_b = _persona_in(db_session, sede_b.id, "newsletter-leads-target-b")

    caso_a = models.CasoCRM(
        persona_id=persona_a_local.id,
        sede_id=sede_a.id,
        pipeline_id=pipeline_a.id,
        etapa_actual_id=etapa_a.id,
        titulo_caso="lead legitimo A",
        origen_canal=CanalOrigenEnum.WEB_FORM,
        origen_detalle_id="newsletter-web",
        estado=EstadoCasoEnum.ABIERTO,
        deleted_at=None,
    )
    caso_b = models.CasoCRM(
        persona_id=persona_b.id,
        sede_id=sede_b.id,
        pipeline_id=pipeline_b.id,
        etapa_actual_id=etapa_b.id,
        titulo_caso="LEAD SECRETO SEDE B",
        origen_canal=CanalOrigenEnum.WEB_FORM,
        origen_detalle_id="newsletter-web",
        estado=EstadoCasoEnum.ABIERTO,
        deleted_at=None,
    )
    db_session.add_all([caso_a, caso_b])
    db_session.commit()

    headers_a = auth_headers(client, email="aboxA@example.com")
    resp = client.get("/api/crm/leads/export-newsletter", headers=headers_a)
    assert resp.status_code == 200
    body_text = resp.text
    # Axioma 3 core: el cross-sede NO debe aparecer
    assert "LEAD SECRETO SEDE B" not in body_text, (
        f"FUGA: lead cross-sede en export admin A: {body_text[:300]}"
    )
    assert "lead legitimo A" in body_text


def test_get_newsletter_leads_blocks_cross_sede(client, db_session):
    """Axioma 3: get_newsletter_leads NO debe exponer leads de otra sede.

    El endpoint ya tenía un JOIN con Persona; sólo faltaba el filtro
    `Persona.sede_id == user_sede` (mismo bug que export_newsletter_leads_csv).
    Cross-sede no debe aparecer en la lista retornada.

    El origen canónico es WEB_FORM y el detalle conserva ``newsletter-web``.
    """
    (admin_a, _, sede_a), (_, _, sede_b) = _seed_two_sedes(db_session)

    # Setup pipeline + etapa por sede (CasoCRM.pipeline_id/etapa_actual_id son NOT NULL)
    pipeline_a = models.PipelineCRM(
        sede_id=sede_a.id,
        nombre="Pipeline A",
        tipo=TipoPipelineEnum.NUEVOS_VISITANTES,
    )
    pipeline_b = models.PipelineCRM(
        sede_id=sede_b.id,
        nombre="Pipeline B",
        tipo=TipoPipelineEnum.NUEVOS_VISITANTES,
    )
    db_session.add_all([pipeline_a, pipeline_b])
    db_session.flush()
    etapa_a = models.EtapaPipeline(pipeline_id=pipeline_a.id, nombre="Etapa 1", orden=1)
    etapa_b = models.EtapaPipeline(pipeline_id=pipeline_b.id, nombre="Etapa 1", orden=1)
    db_session.add_all([etapa_a, etapa_b])
    db_session.flush()

    persona_a_local = _persona_in(db_session, sede_a.id, "newsletter-list-local")
    persona_b = _persona_in(db_session, sede_b.id, "newsletter-list-target-b")

    caso_a = models.CasoCRM(
        persona_id=persona_a_local.id,
        sede_id=sede_a.id,
        pipeline_id=pipeline_a.id,
        etapa_actual_id=etapa_a.id,
        titulo_caso="lead legitimo lista A",
        origen_canal=CanalOrigenEnum.WEB_FORM,
        origen_detalle_id="newsletter-web",
        estado=EstadoCasoEnum.ABIERTO,
        deleted_at=None,
    )
    caso_b = models.CasoCRM(
        persona_id=persona_b.id,
        sede_id=sede_b.id,
        pipeline_id=pipeline_b.id,
        etapa_actual_id=etapa_b.id,
        titulo_caso="LEAD SECRETO LISTA SEDE B",
        origen_canal=CanalOrigenEnum.WEB_FORM,
        origen_detalle_id="newsletter-web",
        estado=EstadoCasoEnum.ABIERTO,
        deleted_at=None,
    )
    db_session.add_all([caso_a, caso_b])
    db_session.commit()

    headers_a = auth_headers(client, email="aboxA@example.com")
    resp = client.get("/api/crm/leads/newsletter", headers=headers_a)
    assert resp.status_code == 200
    body_text = resp.text
    # Axioma 3 core: el cross-sede NO debe aparecer
    assert "LEAD SECRETO LISTA SEDE B" not in body_text, (
        f"FUGA: lead cross-sede en lista de leads admin A: {body_text[:500]}"
    )
    assert "lead legitimo lista A" in body_text

    # Sanity inversa: el admin B tampoco debe ver el lead de sede_a
    headers_b = auth_headers(client, email="aboxB@example.com")
    resp_b = client.get("/api/crm/leads/newsletter", headers=headers_b)
    assert resp_b.status_code == 200
    body_b = resp_b.text
    assert "lead legitimo lista A" not in body_b, (
        f"FUGA: admin B ve lead de sede_a: {body_b[:500]}"
    )


# ── TareaCRM (CRM Tasks) endpoints cross-sede (Axioma 3 — Fase 3) ─────────


def _seed_task_in(
    db,
    *,
    title: str = "Secreto B",
    description: str = "Detalle confidencial",
    persona_id=None,
    asignado_a_id=None,
    caso_id=None,
    estado: str = "pending",
    prioridad: str = "medium",
):
    """Inserta una TareaCRM sin pasar por la API. Útil para sembrar el
    target cross-sede de tests de hardening."""
    import uuid as _u
    from backend.models_crm_pipeline import TareaCRM
    t = TareaCRM(
        id=_u.uuid4(),
        titulo=title,
        descripcion=description,
        categoria="Pastoral",
        persona_id=persona_id,
        asignado_a_id=asignado_a_id,
        caso_id=caso_id,
        estado=estado,
        prioridad=prioridad,
    )
    db.add(t)
    db.flush()
    return t


def test_create_crm_task_blocks_cross_sede_persona(client, db_session):
    """Axioma 3 — Multi-Tenant: crear una tarea con persona_id que pertenece
    a otra sede debe ser 404 (existence-leak safe). Esto evita que un editor
    de sede_a pueda etiquetar a miembros de sede_b con tareas pastorales
    propias."""
    (admin_a, _, sede_a), (_, _, sede_b) = _seed_two_sedes(db_session)
    persona_b = _persona_in(db_session, sede_b.id, "task-create-target-b")
    persona_a_local = _persona_in(db_session, sede_a.id, "task-create-local-a")

    headers_a = auth_headers(client, email="aboxA@example.com")

    # 1. Cross-sede: admin A intenta crear task con persona de sede_b → 404
    resp = client.post(
        "/api/crm/tasks/",
        headers=headers_a,
        json={
            "title": "Tarea cross-sede (debería fallar)",
            "description": "apuntando a persona de sede_b",
            "persona_id": str(persona_b.id),
        },
    )
    assert resp.status_code == 404, (
        f"Leak: admin A creó task con persona de sede_b; status {resp.status_code}, body={resp.text}"
    )
    # Sanity: NO se creó la task en la base de datos
    leaked = (
        db_session.query(models.TareaCRM)
        .filter(models.TareaCRM.descripcion == "apuntando a persona de sede_b")
        .first()
    )
    assert leaked is None, (
        "FUGA CONFIRMADA: task cross-sede persistida pese al 404"
    )

    # 2. Sanity positiva: admin A puede crear task con persona LOCAL → 201
    resp_ok = client.post(
        "/api/crm/tasks/",
        headers=headers_a,
        json={
            "title": "Tarea local legítima",
            "description": "tarea pastoral legítima en sede_a",
            "persona_id": str(persona_a_local.id),
        },
    )
    assert resp_ok.status_code == 200, (
        f"Regresión: admin A no puede crear task en su sede "
        f"(status {resp_ok.status_code}): {resp_ok.text}"
    )
    data = resp_ok.json()
    assert data["title"] == "Tarea local legítima"
    assert data["persona_id"] == str(persona_a_local.id)


def test_create_crm_task_blocks_cross_sede_assignee_uuid(client, db_session):
    """Axioma 3: cuando el editor pasa assignee_id como UUID de persona de
    otra sede, debe ser 404 antes de delegar al CRUD."""
    (admin_a, _, sede_a), (_, persona_b, sede_b) = _seed_two_sedes(db_session)
    persona_a_target = _persona_in(db_session, sede_a.id, "task-assignee-target-a")

    headers_a = auth_headers(client, email="aboxA@example.com")

    resp = client.post(
        "/api/crm/tasks/",
        headers=headers_a,
        json={
            "title": "Task con assignee cross-sede",
            "description": "tarea con destino a persona de sede_b",
            "persona_id": str(persona_a_target.id),
            "assignee_id": str(persona_b.id),  # persona de sede_b
        },
    )
    assert resp.status_code == 404, (
        f"Leak: assignee_id como UUID de persona de sede_b debería 404 "
        f"(status {resp.status_code}): {resp.text}"
    )
    leaked = (
        db_session.query(models.TareaCRM)
        .filter(models.TareaCRM.descripcion == "tarea con destino a persona de sede_b")
        .first()
    )
    assert leaked is None, "FUGA CONFIRMADA: task persistida con assignee cross-sede"


def test_create_crm_task_blocks_cross_sede_assignee_persona_id(client, db_session):
    """assignee_id valida el UUID canónico de Persona contra el scope."""
    (admin_a, _, sede_a), (admin_b, _, sede_b) = _seed_two_sedes(db_session)
    persona_a_target = _persona_in(db_session, sede_a.id, "task-assignee-userid-target-a")

    headers_a = auth_headers(client, email="aboxA@example.com")

    # admin_b.id es un Integer (User de la tabla auth_users). Si pasara el
    # filtro de scope, la asignación quedaría cross-sede sin raise.
    resp = client.post(
        "/api/crm/tasks/",
        headers=headers_a,
        json={
            "title": "Task con assignee user_id de sede_b",
            "description": "tarea con destino a user de sede_b via user_id",
            "persona_id": str(persona_a_target.id),
            "assignee_id": str(admin_b.id),
        },
    )
    assert resp.status_code == 404, (
        f"assignee_id cross-sede debe rechazarse con 404 "
        f"(status {resp.status_code}): {resp.text}"
    )
    leaked = (
        db_session.query(models.TareaCRM)
        .filter(
            models.TareaCRM.descripcion == "tarea con destino a user de sede_b via user_id"
        )
        .first()
    )
    assert leaked is None, "FUGA CONFIRMADA: task persistida con assignee cross-sede via user_id"


def test_create_crm_task_allows_local_assignee_persona_id(client, db_session):
    """El UUID canónico de la Persona local puede recibir la tarea."""
    (admin_a, persona_a, sede_a), _ = _seed_two_sedes(db_session)
    persona_a_target = _persona_in(db_session, sede_a.id, "task-assignee-local-userid")

    headers_a = auth_headers(client, email="aboxA@example.com")

    resp = client.post(
        "/api/crm/tasks/",
        headers=headers_a,
        json={
            "title": "Task con assignee local via user_id",
            "description": "tarea con destino a user de sede_a via user_id",
            "persona_id": str(persona_a_target.id),
            "assignee_id": str(admin_a.id),  # self-assignment
        },
    )
    assert resp.status_code == 200, (
        f"assignee_id local canónico debe funcionar "
        f"(status {resp.status_code}): {resp.text}"
    )


def test_create_crm_task_validates_status_whitelist(client, db_session):
    """Input whitelist: status fuera del set permitido → 422."""
    (admin_a, _, sede_a), _ = _seed_two_sedes(db_session)

    headers_a = auth_headers(client, email="aboxA@example.com")
    resp = client.post(
        "/api/crm/tasks/",
        headers=headers_a,
        json={
            "title": "Task con status inválido",
            "status": "BOGUS_STATUS",
        },
    )
    assert resp.status_code == 422, (
        f"status fuera de whitelist debería 422 (status {resp.status_code}): {resp.text}"
    )


def test_create_crm_task_validates_priority_whitelist(client, db_session):
    """Input whitelist: priority fuera del set permitido → 422."""
    (admin_a, _, sede_a), _ = _seed_two_sedes(db_session)

    headers_a = auth_headers(client, email="aboxA@example.com")
    resp = client.post(
        "/api/crm/tasks/",
        headers=headers_a,
        json={
            "title": "Task con priority inválida",
            "priority": "BOGUS_PRIORITY",
        },
    )
    assert resp.status_code == 422, (
        f"priority fuera de whitelist debería 422 (status {resp.status_code}): {resp.text}"
    )


def test_update_crm_task_blocks_cross_sede(client, db_session):
    """Axioma 3: PATCH /tasks/{id} rechaza leer/mutar tareas de otra sede.

    Un editor de sede_a puede tener la tentación de conocer un task_id de
    sede_b y mutarlo; sin hardening, incluso un 404 al GET no impide el
    PATCH si la query de update es libre. Validamos dos vectores completos
    de scope (persona_id sólo, caso_id cross-sede) sembrando tasks donde
    EXCLUSIVAMENTE un ancla es cross-sede.

    El vector asignado_a_id-only cross-sede está cubierto por
    `test_update_crm_task_blocks_cross_sede_assignee_change`, que valida
    específicamente el camino de mutación del FK (distinto de retrieval).
    """
    (admin_a, persona_a_admin, sede_a), (_, _, sede_b) = _seed_two_sedes(db_session)
    persona_b = _persona_in(db_session, sede_b.id, "task-update-target-b")
    persona_a_local = _persona_in(db_session, sede_a.id, "task-update-local-a")

    # 1. Vector persona_id cross-sede — sin asignado_a_id ni caso_id para
    #    que la única ancla de scope sea persona_id (cross-sede).
    task_via_persona = _seed_task_in(
        db_session,
        title="Task secret via persona_b",
        persona_id=persona_b.id,
    )

    # 2. Vector caso_id cross-sede — CasoCRM.sede_id == sede_b; persona
    #    y asignado locales (mismo seed_admin) hacen que el scope quede
    #    anclado únicamente por caso_id cross-sede.
    pipeline_b = models.PipelineCRM(
        sede_id=sede_b.id,
        nombre="Pipeline Tasks B",
        tipo=TipoPipelineEnum.CONSEJERIA,
    )
    db_session.add(pipeline_b)
    db_session.flush()
    etapa_b = models.EtapaPipeline(pipeline_id=pipeline_b.id, nombre="Etapa 1", orden=1)
    db_session.add(etapa_b)
    db_session.flush()
    caso_b = models.CasoCRM(
        persona_id=persona_b.id,
        sede_id=sede_b.id,
        pipeline_id=pipeline_b.id,
        etapa_actual_id=etapa_b.id,
        titulo_caso="caso task cross-sede",
        origen_canal=CanalOrigenEnum.WEB_FORM,
        estado=EstadoCasoEnum.ABIERTO,
        deleted_at=None,
    )
    db_session.add(caso_b)
    db_session.flush()
    # caso_id es la ÚNICA ancla de scope de este task (persona y asignado
    # son None) para que la lógica OR-based no autorice vía otros FKs.
    # CasoCRM.sede_id = sede_b ⇒ admin_a no debe poder recuperarlo.
    task_via_caso = _seed_task_in(
        db_session,
        title="Task secret via caso_b",
        persona_id=None,
        asignado_a_id=None,
        caso_id=caso_b.id,
    )

    # Task LOCAL (sanity regression)
    task_local = _seed_task_in(
        db_session,
        title="Task local en sede_a",
        persona_id=persona_a_local.id,
        asignado_a_id=persona_a_admin.id,
    )
    db_session.commit()
    for t in (task_via_persona, task_via_caso, task_local):
        db_session.refresh(t)

    headers_a = auth_headers(client, email="aboxA@example.com")

    # 1. Cross-sede via persona_id → 404
    resp = client.patch(
        f"/api/crm/tasks/{task_via_persona.id}",
        headers=headers_a,
        json={"status": "completed", "title": "Mutada cross-sede (deberia fallar)"},
    )
    assert resp.status_code == 404, (
        f"Leak PATCH task cross-sede via persona: status {resp.status_code}, body={resp.text}"
    )
    db_session.refresh(task_via_persona)
    assert task_via_persona.estado == "pending", "estado NO debe mutarse cross-sede"
    assert task_via_persona.titulo == "Task secret via persona_b", "título NO debe mutarse cross-sede"

    # 2. Cross-sede via caso_id → 404
    resp = client.patch(
        f"/api/crm/tasks/{task_via_caso.id}",
        headers=headers_a,
        json={"status": "completed"},
    )
    assert resp.status_code == 404, (
        f"Leak PATCH task cross-sede via caso: status {resp.status_code}, body={resp.text}"
    )
    db_session.refresh(task_via_caso)
    assert task_via_caso.estado == "pending", "estado NO debe mutarse cross-sede"

    # 3. Sanity positiva: admin A puede mutar task local → 200
    resp_ok = client.patch(
        f"/api/crm/tasks/{task_local.id}",
        headers=headers_a,
        json={"status": "in_progress", "priority": "high"},
    )
    assert resp_ok.status_code == 200, (
        f"Regresión: admin A no puede mutar task local (status {resp_ok.status_code}): {resp_ok.text}"
    )
    db_session.refresh(task_local)
    assert task_local.estado == "in_progress"
    assert task_local.prioridad == "high"


def test_update_crm_task_blocks_cross_sede_assignee_change(client, db_session):
    """Axioma 3: PATCH con assignee_id nuevo cross-sede (UUID o user_id)
    debe ser 404. Probamos los dos paths de resolución."""
    (admin_a, persona_a_admin, sede_a), (admin_b, persona_b_admin, sede_b) = _seed_two_sedes(db_session)
    persona_a_local = _persona_in(db_session, sede_a.id, "task-reassign-local-a")

    task_local = _seed_task_in(
        db_session,
        title="Task local reasignable",
        persona_id=persona_a_local.id,
        asignado_a_id=persona_a_admin.id,
    )
    db_session.commit()
    db_session.refresh(task_local)

    headers_a = auth_headers(client, email="aboxA@example.com")

    # 1. Reasignar con UUID de persona de sede_b → 404
    resp_uuid = client.patch(
        f"/api/crm/tasks/{task_local.id}",
        headers=headers_a,
        json={"assignee_id": str(persona_b_admin.id)},
    )
    assert resp_uuid.status_code == 404, (
        f"Leak reasignación UUID cross-sede: status {resp_uuid.status_code}, body={resp_uuid.text}"
    )
    db_session.refresh(task_local)
    assert task_local.asignado_a_id == persona_a_admin.id, (
        "El asignado NO debe haber mutado a cross-sede via UUID"
    )

    # 2. El UUID canónico cross-sede queda fuera de scope.
    resp_user = client.patch(
        f"/api/crm/tasks/{task_local.id}",
        headers=headers_a,
        json={"assignee_id": str(admin_b.id)},
    )
    assert resp_user.status_code == 404, (
        f"Reasignación cross-sede debe ser 404: status {resp_user.status_code}, body={resp_user.text}"
    )
    db_session.refresh(task_local)
    assert task_local.asignado_a_id == persona_a_admin.id, (
        "El asignado NO debe haber mutado a cross-sede via user_id"
    )

    # 3. El UUID canónico local puede recibir la tarea.
    resp_local = client.patch(
        f"/api/crm/tasks/{task_local.id}",
        headers=headers_a,
        json={"assignee_id": str(admin_a.id)},  # self user_id local
    )
    assert resp_local.status_code == 200, (
        f"persona_id local debe aceptarse "
        f"(status {resp_local.status_code}): {resp_local.text}"
    )
    db_session.refresh(task_local)
    assert task_local.asignado_a_id == persona_a_admin.id


def test_update_crm_task_blocks_cross_sede_persona_change(client, db_session):
    """Axioma 3: PATCH con persona_id nuevo cross-sede debe ser 404."""
    (admin_a, _, sede_a), (_, _, sede_b) = _seed_two_sedes(db_session)
    persona_a_local = _persona_in(db_session, sede_a.id, "task-retarget-local-a")
    persona_b = _persona_in(db_session, sede_b.id, "task-retarget-target-b")

    task_local = _seed_task_in(
        db_session,
        title="Task local retargetable",
        persona_id=persona_a_local.id,
    )
    db_session.commit()
    db_session.refresh(task_local)

    headers_a = auth_headers(client, email="aboxA@example.com")

    resp = client.patch(
        f"/api/crm/tasks/{task_local.id}",
        headers=headers_a,
        json={"persona_id": str(persona_b.id)},
    )
    assert resp.status_code == 404, (
        f"Leak reasignación de persona_id cross-sede: status {resp.status_code}, body={resp.text}"
    )
    db_session.refresh(task_local)
    assert task_local.persona_id == persona_a_local.id, (
        "persona_id NO debe haber mutado a cross-sede"
    )


def test_update_crm_task_auto_stamps_completed_at(client, db_session):
    """Side-effect: PATCH status='completed' debe auto-estampar fecha_completada."""
    (admin_a, persona_a_admin, sede_a), _ = _seed_two_sedes(db_session)

    task_local = _seed_task_in(
        db_session,
        title="Task completable",
        estado="pending",
        asignado_a_id=persona_a_admin.id,
    )
    db_session.commit()
    db_session.refresh(task_local)
    assert task_local.fecha_completada is None

    headers_a = auth_headers(client, email="aboxA@example.com")
    resp = client.patch(
        f"/api/crm/tasks/{task_local.id}",
        headers=headers_a,
        json={"status": "completed"},
    )
    assert resp.status_code == 200, resp.text
    db_session.refresh(task_local)
    assert task_local.estado == "completed"
    assert task_local.fecha_completada is not None, (
        "fecha_completada debe auto-estamparse al completar"
    )

    # Reabrir: limpiar fecha_completada
    resp_reopen = client.patch(
        f"/api/crm/tasks/{task_local.id}",
        headers=headers_a,
        json={"status": "in_progress"},
    )
    assert resp_reopen.status_code == 200, resp_reopen.text
    db_session.refresh(task_local)
    assert task_local.estado == "in_progress"
    assert task_local.fecha_completada is None, (
        "fecha_completada debe limpiarse al reabrir"
    )


def test_update_crm_task_rejects_out_of_whitelist(client, db_session):
    """Input whitelist en PATCH: status / priority fuera de whitelist → 422."""
    (admin_a, persona_a_admin, _), _ = _seed_two_sedes(db_session)

    task_local = _seed_task_in(
        db_session,
        title="Task whitelist test",
        asignado_a_id=persona_a_admin.id,
    )
    db_session.commit()
    db_session.refresh(task_local)

    headers_a = auth_headers(client, email="aboxA@example.com")

    resp_status = client.patch(
        f"/api/crm/tasks/{task_local.id}",
        headers=headers_a,
        json={"status": "BOGUS"},
    )
    assert resp_status.status_code == 422, resp_status.text

    resp_priority = client.patch(
        f"/api/crm/tasks/{task_local.id}",
        headers=headers_a,
        json={"priority": "TOP"},
    )
    assert resp_priority.status_code == 422, resp_priority.text


def test_create_crm_task_audit_log_recorded(client, db_session):
    """Axioma 1 — Auditoría: create_crm_task y update_crm_task dejan traza
    en la tabla log_auditoria para trazabilidad (Axioma 1: Mutaciones
    sensibles dejan huella)."""
    from backend.models_evangelism import LogAuditoria

    (admin_a, persona_a_admin, _sede_a), _ = _seed_two_sedes(db_session)

    headers_a = auth_headers(client, email="aboxA@example.com")
    resp = client.post(
        "/api/crm/tasks/",
        headers=headers_a,
        json={
            "title": "Task audit test",
            "description": "creada para validar audit log",
            "priority": "high",
            "persona_id": str(persona_a_admin.id),  # in-scope anchor
        },
    )
    assert resp.status_code == 200, resp.text
    task_id = resp.json()["id"]
    db_session.commit()

    audit_row = (
        db_session.query(LogAuditoria)
        .filter(
            LogAuditoria.tabla_afectada == "crm_tareas",
            LogAuditoria.registro_id == task_id,
            LogAuditoria.accion == "CREATE",
        )
        .first()
    )
    assert audit_row is not None, (
        f"No se registró audit log para CREATE de task {task_id}"
    )
    assert audit_row.detalles_cambio.get("title") == "Task audit test"
    assert audit_row.detalles_cambio.get("priority") == "high"

    # Update audit
    resp_u = client.patch(
        f"/api/crm/tasks/{task_id}",
        headers=headers_a,
        json={"status": "completed"},
    )
    assert resp_u.status_code == 200, resp_u.text
    db_session.commit()

    update_row = (
        db_session.query(LogAuditoria)
        .filter(
            LogAuditoria.tabla_afectada == "crm_tareas",
            LogAuditoria.registro_id == task_id,
            LogAuditoria.accion == "UPDATE",
        )
        .first()
    )
    assert update_row is not None, "No se registró audit log para UPDATE"

    # Sanity: PATCH sin cambios sensibles (e.g. description->mismo valor)
    # NO debe generar audit (optimización: audit sólo en cambios reales).


# ── CRUD-layer audit log defense-in-depth (Axioma 1) ─────────────────────
# Valida que el audit log vive en el CRUD layer y persiste
# independientemente de que el caller sea la API endurecida o un script
# directo. Sin esta garantía, una mutación vía cruds directos u otro
# endpoint no-API quedaría sin traza (regresión silenciosa a Axioma 1).


def test_crud_create_crm_task_logs_audit_directly(db_session):
    """Axioma 1 — defense in depth: `crud.create_crm_task` emite audit log
    sin necesidad de la API. Esto garantiza que mutaciones desde scripts
    de seeding, workers, o cualquier otro caller directo del CRUD queden
    trazadas."""
    from backend import crud, schemas
    from backend.models_evangelism import LogAuditoria

    _, persona_a, _ = seed_admin(db_session, email="seed-crud@example.com")

    create_payload = schemas.CrmTaskCreate(
        title="Direct CRUD create",
        description="creada vía crud directo, sin API",
        category="Pastoral",
        priority="low",
        status="pending",
        persona_id=persona_a.id,
    )

    task = crud.create_crm_task(
        db_session, create_payload, actor_user_id=str(persona_a.id)
    )
    db_session.commit()
    assert task.id is not None

    rows = (
        db_session.query(LogAuditoria)
        .filter(
            LogAuditoria.tabla_afectada == "crm_tareas",
            LogAuditoria.registro_id == str(task.id),
            LogAuditoria.accion == "CREATE",
        )
        .all()
    )
    assert len(rows) == 1, f"Audit CREATE esperado, encontrados {len(rows)}"
    assert rows[0].detalles_cambio["title"] == "Direct CRUD create"
    assert str(rows[0].usuario_id) == str(persona_a.id)

    # Con actor_user_id: actor debe propagarse a LogAuditoria.usuario_id.
    task2 = crud.create_crm_task(
        db_session,
        schemas.CrmTaskCreate(
            title="Direct CRUD create 2",
            persona_id=persona_a.id,  # in-scope anchor para pasar scope re-check
        ),
        actor_user_id=str(persona_a.id),
    )
    db_session.commit()
    row2 = (
        db_session.query(LogAuditoria)
        .filter(
            LogAuditoria.tabla_afectada == "crm_tareas",
            LogAuditoria.registro_id == str(task2.id),
            LogAuditoria.accion == "CREATE",
        )
        .first()
    )
    assert row2 is not None
    assert str(row2.usuario_id) == str(persona_a.id), (
        f"actor_user_id no se propagó: {row2.usuario_id}"
    )


def test_crud_update_crm_task_logs_audit_on_real_change(db_session):
    """Axioma 1 — defense in depth: `crud.update_crm_task` emite audit log
    cuando hay cambios REALES (no idempotent updates)."""
    import uuid as _u
    from backend import crud, schemas
    from backend.models_evangelism import LogAuditoria
    from backend.models_crm_pipeline import TareaCRM

    _, persona_a, _ = seed_admin(db_session, email="crud-update@example.com")

    # Seed una tarea con valores conocidos (SQL directo, sin audit previo).
    t = TareaCRM(
        id=_u.uuid4(),
        titulo="Task CRUD update",
        descripcion="initial",
        estado="pending",
        prioridad="low",
        categoria="Pastoral",
        asignado_a_id=persona_a.id,
    )
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)

    initial_audit_count = (
        db_session.query(LogAuditoria)
        .filter(
            LogAuditoria.tabla_afectada == "crm_tareas",
            LogAuditoria.registro_id == str(t.id),
        )
        .count()
    )
    # El seed directo no pasó por el CRUD, así que no debe haber audit aún.
    assert initial_audit_count == 0, (
        "El seed directo SQL no debe generar audit previo"
    )

    # Update con cambio real vía CRUD.
    updated = crud.update_crm_task(
        db_session,
        t.id,
        schemas.CrmTaskUpdate(status="completed"),
        actor_user_id=str(persona_a.id),
    )
    db_session.commit()
    assert updated is not None
    assert updated.estado == "completed"

    update_row = (
        db_session.query(LogAuditoria)
        .filter(
            LogAuditoria.tabla_afectada == "crm_tareas",
            LogAuditoria.registro_id == str(t.id),
            LogAuditoria.accion == "UPDATE",
        )
        .first()
    )
    assert update_row is not None, "No se registró audit UPDATE"
    assert "status" in update_row.detalles_cambio
    assert update_row.detalles_cambio["status"]["from"] == "pending"
    assert update_row.detalles_cambio["status"]["to"] == "completed"
    assert str(update_row.usuario_id) == str(persona_a.id)


def test_crud_update_crm_task_no_audit_when_idempotent(db_session):
    """Axioma 1 — minimización de ruido: si el update es idempotente
    (mismo valor), el CRUD NO debe registrar audit log. Esto evita
    inflar el log con filas inútiles y mantiene la traza enfocada en
    cambios reales."""
    import uuid as _u
    from backend import crud, schemas
    from backend.models_evangelism import LogAuditoria
    from backend.models_crm_pipeline import TareaCRM

    _, persona_a, _ = seed_admin(db_session, email="crud-noop@example.com")

    t = TareaCRM(
        id=_u.uuid4(),
        titulo="Task sin cambio",
        estado="pending",
        prioridad="low",
        categoria="Pastoral",
        asignado_a_id=persona_a.id,
    )
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)

    # Update idempotente: priority="low" igual al actual.
    crud.update_crm_task(
        db_session,
        t.id,
        schemas.CrmTaskUpdate(priority="low"),
        actor_user_id=str(persona_a.id),
    )
    db_session.commit()

    rows = (
        db_session.query(LogAuditoria)
        .filter(
            LogAuditoria.tabla_afectada == "crm_tareas",
            LogAuditoria.registro_id == str(t.id),
            LogAuditoria.accion == "UPDATE",
        )
        .all()
    )
    assert len(rows) == 0, (
        f"Update idempotente NO debe generar audit (encontrados {len(rows)})"
    )


def test_crud_update_crm_task_logs_audit_with_schema_payload(db_session):
    """El contrato Pydantic canónico conserva la auditoría de cambios."""
    import uuid as _u
    from backend import crud, schemas
    from backend.models_evangelism import LogAuditoria
    from backend.models_crm_pipeline import TareaCRM

    _, persona_a, _ = seed_admin(db_session, email="crud-dict@example.com")

    t = TareaCRM(
        id=_u.uuid4(),
        titulo="Task dict payload",
        estado="pending",
        prioridad="low",
        asignado_a_id=persona_a.id,  # in-scope anchor para pasar scope re-check
    )
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)

    crud.update_crm_task(
        db_session,
        t.id,
        schemas.CrmTaskUpdate(status="completed"),
        actor_user_id=str(persona_a.id),
    )
    db_session.commit()

    row = (
        db_session.query(LogAuditoria)
        .filter(
            LogAuditoria.tabla_afectada == "crm_tareas",
            LogAuditoria.registro_id == str(t.id),
            LogAuditoria.accion == "UPDATE",
        )
        .first()
    )
    assert row is not None
    assert row.detalles_cambio["status"]["from"] == "pending"
    assert row.detalles_cambio["status"]["to"] == "completed"


# ── CRUD-layer scope re-check (Axioma 3 — defense in depth) ───────────────
# Cierra el TOCTOU gap donde un caller que no es la API endurecida (script,
# worker, seed) podría mutar el row sin pasar por el helper API `_get_scoped_task`.
# La capa CRUD re-valida las anclas (caso_id/persona_id/asignado_a_id) cuando
# actor_user_id viene con sede asignada.


def test_crud_create_crm_task_blocks_cross_sede_when_actor_in_sede(db_session):
    """Axioma 3 — defense in depth: el CRUD debe bloquear CREATE cuando
    el actor está en sede_a e intenta referenciar una persona (vía
    persona_id) de sede_b, AUNQUE el caller no sea la API endurecida.

    Esto cierra el vector donde un script interno / worker async / seed
    llama a `crud.create_crm_task` directamente y bypasea el helper API.

    Política: OR-based. Si el actor NO tiene sede (superadmin/legacy) no
    se aplica check. Como aquí sí tiene sede, el check dispara.
    """
    from fastapi import HTTPException
    from backend import crud, schemas
    from backend.models_crm_pipeline import TareaCRM

    (admin_a, _persona_a, sede_a), (_, _, sede_b) = _seed_two_sedes(db_session)
    persona_b = _persona_in(db_session, sede_b.id, "crud-create-cross-b")

    cross_payload = schemas.CrmTaskCreate(
        title="CRUD direct cross-sede create (deberia fallar)",
        description="atacando por debajo de la API",
        persona_id=persona_b.id,  # cross-sede
    )
    count_before = db_session.query(TareaCRM).count()

    raised = False
    try:
        crud.create_crm_task(
            db_session,
            cross_payload,
            actor_user_id=str(admin_a.id),
        )
    except HTTPException as exc:
        raised = True
        assert exc.status_code == 404, (
            f"Cross-sede CREATE en CRUD debe ser 404, got {exc.status_code}"
        )

    assert raised, (
        "El CRUD NO emitió HTTPException al validar scope — defense-in-depth falló"
    )
    # Sanity: row NO fue persistido.
    db_session.rollback()
    count_after = db_session.query(TareaCRM).count()
    assert count_after == count_before, (
        "FUGA: CREATE cross-sede persistió la fila pese al 404"
    )


def test_crud_update_crm_task_blocks_toctou_when_actor_in_sede(db_session):
    """Axioma 3 — defense in depth (UPDATE TOCTOU): el CRUD debe detectar
    que el row fue movido cross-sede ENTRE el fetch inicial del API y el
    re-fetch del CRUD.

    Simulación: creamos una tarea válida con anclas locales. Luego
    forzamos la mutación del caso_id del row a un caso de sede_b
    (equivalente a que otro admin movió el row). Al ejecutar
    `crud.update_crm_task` con actor en sede_a, el helper
    `_crud_scope_re_check_task` debe abortar con 404.
    """
    from fastapi import HTTPException
    from backend import crud, schemas
    from backend.models_crm_pipeline import TareaCRM

    (admin_a, persona_a_admin, _sede_a), (_, _, sede_b) = _seed_two_sedes(db_session)
    persona_a_local = _persona_in(db_session, _sede_a.id, "crud-toctou-local-a")

    # Setup caso cross-sede para forzar el TOCTOU.
    pipeline_b = models.PipelineCRM(
        sede_id=sede_b.id,
        nombre="Pipeline TOCTOU B",
        tipo=TipoPipelineEnum.CONSEJERIA,
    )
    db_session.add(pipeline_b)
    db_session.flush()
    etapa_b = models.EtapaPipeline(pipeline_id=pipeline_b.id, nombre="Etapa 1", orden=1)
    db_session.add(etapa_b)
    db_session.flush()
    caso_b = models.CasoCRM(
        persona_id=persona_a_local.id,
        sede_id=sede_b.id,
        pipeline_id=pipeline_b.id,
        etapa_actual_id=etapa_b.id,
        titulo_caso="caso TOCTOU cross-sede",
        origen_canal=CanalOrigenEnum.WEB_FORM,
        estado=EstadoCasoEnum.ABIERTO,
        deleted_at=None,
    )
    db_session.add(caso_b)
    db_session.flush()

    # Sembramos la tarea con anclas de sede_a (aptas para el actor A).
    task = _seed_task_in(
        db_session,
        title="task TOCTOU simulada",
        persona_id=persona_a_local.id,
        asignado_a_id=persona_a_admin.id,
        caso_id=None,
    )
    db_session.commit()
    db_session.refresh(task)

    # FORZAMOS el TOCTOU: cambiamos caso_id a un caso de sede_b directamente
    # en BD (equivalente a otro admin moviendo el row cross-sede entre el
    # get-scoped inicial del API y el re-fetch del CRUD).
    db_session.expire(task)
    raw_task = db_session.query(TareaCRM).filter(TareaCRM.id == task.id).first()
    raw_task.caso_id = caso_b.id
    db_session.commit()
    db_session.refresh(raw_task)
    assert raw_task.caso_id == caso_b.id
    assert raw_task.persona_id == persona_a_local.id  # aún anclada a sede_a

    raised = False
    try:
        crud.update_crm_task(
            db_session,
            raw_task.id,
            schemas.CrmTaskUpdate(status="completed"),
            actor_user_id=str(admin_a.id),
        )
    except HTTPException as exc:
        raised = True
        assert exc.status_code == 404, (
            f"TOCTOU cross-sede UPDATE en CRUD debe ser 404, got {exc.status_code}"
        )

    assert raised, (
        "TOCTOU cerró el update sin raise — defense-in-depth falló"
    )
    db_session.rollback()
    db_session.refresh(raw_task)
    assert raw_task.estado == "pending", (
        "El estado NO debe mutarse cuando el CRUD detecta TOCTOU cross-sede"
    )


def test_crud_create_crm_task_requires_actor(db_session):
    from backend import crud, schemas

    payload = schemas.CrmTaskCreate(title="Actor required")
    with pytest.raises(TypeError):
        crud.create_crm_task(db_session, payload)


def test_crud_create_crm_task_rejects_unknown_actor(db_session):
    from backend import crud, schemas

    (_, _, _), (_, persona_b, _) = _seed_two_sedes(db_session)
    payload = schemas.CrmTaskCreate(
        title="Unknown actor rejected",
        persona_id=persona_b.id,
    )
    with pytest.raises(HTTPException) as exc_info:
        crud.create_crm_task(
            db_session,
            payload,
            actor_user_id=str(_uuid.uuid4()),
        )
    assert exc_info.value.status_code == 401


def test_crud_update_crm_task_blocks_assignee_change_cross_sede(db_session):
    """Axioma 3 — defense in depth (UPDATE new FK): el CRUD debe bloquear
    un PATCH que escribe assignee_id cross-sede, AUNQUE el row original
    esté en scope. Esto cubre el vector diferente al TOCTOU: la mutación
    de un FK hacia una sede distinta vía incoming_anchors.

    Tras extender `CrmTaskUpdate` con campos FK (persona_id, assignee_id,
    caso_id), este test usa el schema Pydantic directamente — alinea con
    el contrato del schema y evita el workaround dict-bypass previo.
    """
    from fastapi import HTTPException
    from backend import crud, schemas

    (admin_a, persona_a_admin, _sede_a), (_, persona_b_admin, sede_b) = _seed_two_sedes(db_session)
    persona_a_local = _persona_in(db_session, _sede_a.id, "crud-reassign-local-a")

    task = _seed_task_in(
        db_session,
        title="CRUD reassign target",
        persona_id=persona_a_local.id,
        asignado_a_id=persona_a_admin.id,
    )
    db_session.commit()
    db_session.refresh(task)

    # Pydantic schema ahora preserva el campo FK tras la extension de
    # CrmTaskUpdate. Defense-in-depth CRUD valida scope de FK incoming.
    raised = False
    try:
        crud.update_crm_task(
            db_session,
            task.id,
            schemas.CrmTaskUpdate(assignee_id=str(persona_b_admin.id)),  # cross-sede
            actor_user_id=str(admin_a.id),
        )
    except HTTPException as exc:
        raised = True
        assert exc.status_code == 404, (
            f"Reasignación cross-sede en CRUD debe ser 404, got {exc.status_code}"
        )

    assert raised, (
        "Reasignación cross-sede en CRUD bypasseó el scope re-check"
    )
    db_session.rollback()
    db_session.refresh(task)
    assert task.asignado_a_id == persona_a_admin.id, (
        "El asignado NO debe mutarse a cross-sede"
    )


def test_crud_update_crm_task_blocks_tropical_case_under_strict(db_session):
    """Axioma 3 — STRICT sobre estado final combinado: la defense-in-depth
    del CRUD es ESTRICTA (a diferencia del OR-based del API helper
    `_get_scoped_task`). Esto significa que un row con anclas mixtas
    (caso_b cross-sede + persona/asignado locales) ES rechazable en WRITE,
    aunque sea legible en READ.

    Esta asimetría es deliberada:
      - API READ (`_get_scoped_task` OR-based): una tarea con caso_de_sede_A
        asignada a pastor_de_sede_B es legible ("tropical case legítimo").
      - CRUD WRITE (defense-in-depth STRICT): no se permite INTRODUCIR o
        DEJAR anclas cross-sede. Esto blinda mutaciones y cierra el TOCTOU
        contra futuros movimientos cross-sede.

    Si el negocio requiere tareas tropicales editables, debe resolverse a
    nivel API (admin cross-sede con bypass explícito), NO en el CRUD."""
    from fastapi import HTTPException
    from backend import crud, schemas
    (admin_a, persona_a_admin, sede_a), (_, _, sede_b) = _seed_two_sedes(db_session)
    persona_a_local = _persona_in(db_session, sede_a.id, "crud-tropical-local-a")

    pipeline_b = models.PipelineCRM(
        sede_id=sede_b.id,
        nombre="Pipeline Tropical B",
        tipo=TipoPipelineEnum.CONSEJERIA,
    )
    db_session.add(pipeline_b)
    db_session.flush()
    etapa_b = models.EtapaPipeline(pipeline_id=pipeline_b.id, nombre="Etapa 1", orden=1)
    db_session.add(etapa_b)
    db_session.flush()
    caso_b = models.CasoCRM(
        persona_id=persona_a_local.id,
        sede_id=sede_b.id,  # ANCLA cross-sede
        pipeline_id=pipeline_b.id,
        etapa_actual_id=etapa_b.id,
        titulo_caso="caso tropical en sede B",
        origen_canal=CanalOrigenEnum.WEB_FORM,
        estado=EstadoCasoEnum.ABIERTO,
        deleted_at=None,
    )
    db_session.add(caso_b)
    db_session.flush()

    task = _seed_task_in(
        db_session,
        title="Task tropical",
        persona_id=persona_a_local.id,        # sede_a (ancla OK)
        asignado_a_id=persona_a_admin.id,    # sede_a (ancla OK)
        caso_id=caso_b.id,                   # sede_b → STRICT reject
    )
    db_session.commit()
    db_session.refresh(task)
    priority_before = task.prioridad

    raised = False
    try:
        crud.update_crm_task(
            db_session,
            task.id,
            schemas.CrmTaskUpdate(priority="high"),
            actor_user_id=str(admin_a.id),
        )
    except HTTPException as exc:
        raised = True
        assert exc.status_code == 404
        # Mensaje genérico: SIN nombre del anchor (no info leak).
        assert "anchor" not in (exc.detail or "").lower(), (
            f"detail message filtra vector de violation: {exc.detail!r}"
        )

    assert raised, (
        "STRICT policy: caso_b cross-sede debe rechazar UPDATE aunque "
        "persona/asignado sean locales"
    )
    db_session.rollback()
    db_session.refresh(task)
    assert task.prioridad == priority_before, (
        "La priority NO debe mutarse cuando el CRUD detecta STRICT violation"
    )


def test_crud_create_crm_task_orphan_rejected_for_editor(db_session):
    """Axioma 3 — comportamiento explícito: un CREATE sin ninguna FK
    (todas None) ejecutado por un editor en sede debe ser REJECTED con
    404. Esto es consistente con la política de la API (`_get_scoped_task`
    docstring dice "Tarea sin ninguna FK (huérfana): sólo visible a
    superadmin sin sede"). Por simetría, la creación de orphans también
    se restringe a superadmins/legacy.

    Si el caller NO provee actor_user_id (legacy path), la creación de
    orphans se permite para back-compat con scripts y bulk imports."""
    from fastapi import HTTPException
    from backend import crud, schemas

    (admin_a, _, _), _ = _seed_two_sedes(db_session)

    payload = schemas.CrmTaskCreate(
        title="CRUD orphan sin anclas",
        description="task sin persona, asignado ni caso",
    )
    raised = False
    try:
        crud.create_crm_task(
            db_session,
            payload,
            actor_user_id=str(admin_a.id),
        )
    except HTTPException as exc:
        raised = True
        assert exc.status_code == 404

    assert raised, (
        "STRICT policy + orphan guard: editor en sede NO debe poder crear "
        "tarea huérfana (consistencia con API que rechaza orphans en lectura)"
    )

def test_create_prayer_request_no_user_sede_returns_400(client, db_session, monkeypatch):
    """M3 — Axioma 3: create_prayer_request rechaza 400 cuando el editor
    no tiene sede asignada (superadmin legacy / token v2 residual) en vez
    de dejar el PrayerRequest con sede_id=NULL (invisible en listados).

    NOTA sobre estrategia:
        auth_users.sede_id es NOT NULL en DB, por lo que un user Auth v3
        válido siempre tendrá sede asignada. Esta línea defensiva (que
        existe para tokens legacy v2 o futuras migraciones semi-completas)
        sólo se puede disparar reproduciblemente monkeypatcheando
        `backend.api.crm.pastoral.get_user_sede_id` a retornar None.

    Cobertura del branch:
        if not user_sede:
            raise HTTPException(400, 'El usuario no tiene sede asignada')

    Sanity positivity al final: NO se crea ningún PrayerRequest con
    `requester_name` igual al enviado (defense-in-depth contra bypass).
    """
    seed_admin(db_session, email="no-sede-cfg@test.com")
    headers = auth_headers(client, email="no-sede-cfg@test.com")

    # Forzar el estado defensivo: el nombre `get_user_sede_id` está
    # importado en pastoral.py vía `from backend.crud.crm import (...,)
    # get_user_sede_id` (mismo objeto en memoria). Monkeypatch sobre el
    # nombre en el módulo caller desactiva el lookup en BD y retorna
    # None para cualquier user_id, disparando el branch 400.
    monkeypatch.setattr(
        "backend.api.crm.pastoral.get_user_sede_id",
        lambda db, current_user_id: None,
    )

    resp = client.post(
        "/api/crm/prayer-requests",
        headers=headers,
        json={
            "requester_name": "Superadmin Legacy",
            "request_text": "peticion de prueba (debe fallar)",
            "category": "General",
            "source": "crm",
        },
    )

    # Branch 400 debe disparar
    assert resp.status_code == 400, (
        f"create_prayer_request debería 400 cuando get_user_sede_id=None; "
        f"got {resp.status_code}: {resp.text}"
    )
    detail = resp.json().get("detail", "")
    assert detail == "El usuario no tiene sede asignada", (
        f"exact detail contract esperado: 'El usuario no tiene sede asignada', "
        f"got {detail!r}"
    )

    # Defense-in-depth: NO se creó ningún prayer con ese requester_name.
    db_session.commit()
    leaks = (
        db_session.query(models.PrayerRequest)
        .filter(models.PrayerRequest.requester_name == "Superadmin Legacy")
        .count()
    )
    assert leaks == 0, (
        f"FUGA: {leaks} prayer(s) creados pese al 400 "
        f"(el guard del API fue bypaseado)"
    )
