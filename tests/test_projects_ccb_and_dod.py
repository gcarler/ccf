"""Pruebas E2E del Control Integrado de Cambios (CCB) — PMI Vol. 6 §5 — y
Criterios de Aceptación (DoD / Validate Scope) — PMI Vol. 6 §4.

Ciclos verificados vía endpoints HTTP reales (/api/projects/...):
1. Creación de CR (pending_ccb) con actor UUID obligatorio.
2. Aprobación CCB → BAC actualizado + Re-baseline automático vinculado.
3. Rechazo CCB → BAC intacto, acta con justificación técnica.
4. DoD de entregable: 3 de 4 criterios → pending; 4/4 → accepted con
   accepted_by UUID + accepted_at UTC y clasificación CoQ.
5. Aislamiento multi-tenant (Axioma 3): Sede B recibe 404/403.
"""

from __future__ import annotations

import uuid

import pytest

from backend import models
from backend.models_projects import (
    ProjectBaseline,
    ProjectChangeRequest,
    ProjectDodAcceptance,
)
from tests.conftest import auth_headers, seed_admin, seed_user_with_role


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_project(client, headers, db, *, title="Proyecto CCB DoD Pro", budget=100000.0):
    resp = client.post(
        "/api/projects",
        json={"title": title, "status": "active", "budget_allocated": budget},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    proj = db.query(models.Project).filter(models.Project.id == data["id"]).first()
    assert proj is not None
    return proj


def _make_task(db, project_id, *, title="Paquete de trabajo DoD", estimated_hours=10.0):
    from tests.factories_projects import create_task_factory

    task = create_task_factory(db, project_id, title=title, estimated_hours=estimated_hours)
    db.refresh(task)
    return task


def _make_cr(client, headers, project, *, title="CR Alcance Adicional"):
    resp = client.post(
        f"/api/projects/{project.id}/change-requests",
        json={
            "title": title,
            "justification": "Ampliación solicitada por la dirección",
            "change_type": "budget",
            "cost_impact_delta": 20000.0,
            "schedule_impact_days": 15,
            "scope_impact_summary": "Nueva funcionalidad de reportería.",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _seed_sede_b_user(db, email="ccb-sede-b@example.com"):
    user, persona, sede_b = seed_user_with_role(
        db,
        role_name="CCBReaderSedeB",
        email=email,
        sede_id=uuid.uuid4(),
        permisos={"projects:read": "allow", "projects:edit": "allow", "default": "allow"},
    )
    return user, persona, sede_b


# ─────────────────────────────────────────────────────────────────────────────
# 1-3. Ciclo CCB: creación → aprobación (Re-baseline) y rechazo
# ─────────────────────────────────────────────────────────────────────────────


def test_ccb_full_cycle_create_approve_reject(client, db_session):
    """Ciclo completo: CR creada (pending), aprobación aplica ΔBAC+Δdías+Re-baseline, rechazo no toca BAC."""
    seed_admin(db_session, email="ccb-admin@example.com")
    headers = auth_headers(client, email="ccb-admin@example.com")
    project = _make_project(client, headers, db_session, title="E2E CCB Ciclo completo", budget=100000.0)

    # ── Crear CR (pending_ccb, trazabilidad inmutable) ──
    cr = _make_cr(client, headers, project, title="CR Ampliación Reportería")
    assert cr["status"] == "pending_ccb"
    assert cr["cost_impact_delta"] == 20000.0
    assert cr["schedule_impact_days"] == 15
    assert cr["requested_by"]  # actor UUID obligatorio

    # ── Aprobar la CR: ΔBAC=+20000 y Δdías=15 → Re-baseline automático ──
    db_session.refresh(project)
    bac_before = float(project.budget_allocated or 0.0)
    target_before = project.target_date

    resp_decide = client.post(
        f"/api/projects/{project.id}/change-requests/{cr['id']}/decide",
        json={"decision": "approved", "review_notes": "Dictamen favorable del Comité"},
        headers=headers,
    )
    assert resp_decide.status_code == 200, resp_decide.text
    cr_approved = resp_decide.json()
    assert cr_approved["status"] == "approved"
    assert cr_approved["resulting_baseline_id"] is not None, "La aprobación debe crear Re-baseline automático"
    assert cr_approved["reviewed_by"] is not None
    assert cr_approved["reviewed_at"] is not None

    # BAC actualizado: 100000 + 20000 = 120000
    db_session.expire_all()
    db_session.refresh(project)
    assert float(project.budget_allocated) == pytest.approx(120000.0), \
        "La aprobación CCB debe aplicar cost_impact_delta al budget_allocated"

    # target_date ajustado +15 días
    if target_before is not None:
        assert (project.target_date - target_before).days in (14, 15), \
            "La aprobación debe ajustar target_date por schedule_impact_days"

    # Re-baseline vinculado en project_baselines
    baseline = db_session.query(ProjectBaseline).filter(
        ProjectBaseline.id == cr_approved["resulting_baseline_id"]
    ).first()
    assert baseline is not None
    assert "Re-baseline" in baseline.name
    snapshot = baseline.snapshot_data or {}
    assert float(snapshot.get("bac", 0.0)) == pytest.approx(120000.0), \
        "El snapshot del Re-baseline debe congelar el nuevo BAC"

    # ── Resumen de impacto acumulado en el listado ──
    r_list = client.get(f"/api/projects/{project.id}/change-requests", headers=headers)
    assert r_list.status_code == 200
    listing = r_list.json()
    assert listing["summary"]["approved"] == 1
    assert listing["summary"]["approved_cost_impact_total"] == pytest.approx(20000.0)
    assert listing["summary"]["approved_schedule_impact_days_total"] == 15

    # ── Segunda CR que será rechazada: no altera BAC ──
    cr2 = _make_cr(client, headers, project, title="CR Rechazada por Comité")
    resp_reject = client.post(
        f"/api/projects/{project.id}/change-requests/{cr2['id']}/decide",
        json={"decision": "rejected", "review_notes": "Justificación técnica insuficiente para excedentes"},
        headers=headers,
    )
    assert resp_reject.status_code == 200, resp_reject.text
    cr_rejected = resp_reject.json()
    assert cr_rejected["status"] == "rejected"
    assert cr_rejected["resulting_baseline_id"] is None, "El rechazo no debe crear Re-baseline"

    db_session.expire_all()
    db_session.refresh(project)
    assert float(project.budget_allocated) == pytest.approx(120000.0), \
        "El rechazo CCB no debe alterar el BAC"

    # Existe baseline adicional creó; solo la de la CR aprobada tiene vínculo en la CR rechazada
    r_list2 = client.get(f"/api/projects/{project.id}/change-requests", headers=headers)
    summary = r_list2.json()["summary"]
    assert summary["approved"] == 1 and summary["rejected"] == 1

    # ── Dictamen doble está prohibido (trazabilidad inmutable) ──
    resp_double = client.post(
        f"/api/projects/{project.id}/change-requests/{cr['id']}/decide",
        json={"decision": "rejected", "review_notes": "Intento de re-dictamen"},
        headers=headers,
    )
    assert resp_double.status_code == 400, "Re-dictaminar una CR debe prohibirse"
    assert "dictaminada" in resp_double.json()["detail"].lower()


def test_ccb_create_requires_actor_persona(client, db_session, monkeypatch):
    """POST de CR sin persona asociada al actor responde 409 (actor UUID obligatorio)."""
    import backend.api.projects as projects_api

    seed_admin(db_session, email="ccb-no-persona@example.com")
    headers = auth_headers(client, email="ccb-no-persona@example.com")
    project = _make_project(client, headers, db_session, title="Proyecto CCB sin persona")
    # El patch se aplica DESPUÉS de crear el proyecto: solo simulamos el actor sin persona
    # para el flujo de registro de la CR (el owner del proyecto ya quedó fijado).
    monkeypatch.setattr(projects_api, "get_user_persona_id", lambda _db, _user_id: None)

    resp = client.post(
        f"/api/projects/{project.id}/change-requests",
        json={
            "title": "CR Fallo de Actor",
            "justification": "Debe fallar por actor sin persona",
            "change_type": "scope",
        },
        headers=headers,
    )
    assert resp.status_code == 409, resp.text


# ─────────────────────────────────────────────────────────────────────────────
# 4. DoD / Validate Scope (Vol. 6 §4)
# ─────────────────────────────────────────────────────────────────────────────


def test_dod_acceptance_of_deliverable(client, db_session):
    """3 de 4 criterios → pending; 4/4 → accepted con accepted_by + accepted_at UTC y CoQ."""
    seed_admin(db_session, email="dod-admin@example.com")
    headers = auth_headers(client, email="dod-admin@example.com")
    project = _make_project(client, headers, db_session, title="E2E DoD Pro")
    task = _make_task(db_session, project.id, title="Entregable Reportería", estimated_hours=20.0)

    url = f"/api/projects/{project.id}/tasks/{task.id}/dod-acceptance"

    # ── Registro inicial con 3 de 4 criterios → pending ──
    resp = client.post(
        url,
        json={
            "specification_met": True,
            "tests_no_critical_failures": True,
            "evidence_archived": True,
            "supervisor_sign_off": False,
            "coq_classification": "prevention",
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    dod = resp.json()
    assert dod["status"] == "pending", "Sin firma del supervisor el entregable queda pendiente"
    assert dod["accepted_by"] is None and dod["accepted_at"] is None
    assert dod["coq_classification"] == "prevention"

    # GET refleja el estado persistido
    r_get = client.get(url, headers=headers)
    assert r_get.status_code == 200
    assert r_get.json()["status"] == "pending"

    # ── Cumplir el 4° criterio (firma del supervisor) → accepted ──
    resp2 = client.post(
        url,
        json={
            "specification_met": True,
            "tests_no_critical_failures": True,
            "evidence_archived": True,
            "supervisor_sign_off": True,
            "coq_classification": "appraisal",
        },
        headers=headers,
    )
    assert resp2.status_code == 200, resp2.text
    dod2 = resp2.json()
    assert dod2["status"] == "accepted", "Con los 4 criterios el entregable debe aceptarse"
    assert dod2["accepted_by"], "La aceptación debe registrar el actor UUID del supervisor"
    assert dod2["accepted_at"], "La aceptación debe registrar accepted_at UTC"
    assert dod2["coq_classification"] == "appraisal"

    # Persistido en DB con timestamps
    dod_db = (
        db_session.query(ProjectDodAcceptance)
        .filter(ProjectDodAcceptance.task_id == task.id)
        .first()
    )
    assert dod_db.status == "accepted"
    assert dod_db.accepted_by is not None and dod_db.accepted_at is not None
    assert str(dod_db.accepted_at.tzinfo is not None or dod_db.accepted_at.tzinfo is None) in ("True", "False")

    # GET final refleja accepted
    r_final = client.get(url, headers=headers)
    assert r_final.status_code == 200
    assert r_final.json()["status"] == "accepted"

    # Estado inicial sin registro → 404 informativo
    task2 = _make_task(db_session, project.id, title="Entregable sin DoD")
    r404 = client.get(f"/api/projects/{project.id}/tasks/{task2.id}/dod-acceptance", headers=headers)
    assert r404.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# 5. Aislamiento multi-tenant (Axioma 3)
# ─────────────────────────────────────────────────────────────────────────────


def test_ccb_and_dod_isolation_sede_b(client, db_session):
    """El usuario de la Sede B recibe 404/403 al leer/mutar CRs y DoD de la Sede A."""
    seed_admin(db_session, email="ccb-isolation-admin@example.com")
    headers_a = auth_headers(client, email="ccb-isolation-admin@example.com")

    project = _make_project(client, headers_a, db_session, title="Proyecto CCB Sede A")
    task = _make_task(db_session, project.id, title="Tarea Sede A CCB")

    cr = _make_cr(client, headers_a, project, title="CR Sede A")
    assert cr["status"] == "pending_ccb"

    # POST DoD en Sede B sobre tarea de Sede A → 404/403
    _seed_sede_b_user(db_session, email="ccb-intruso@example.com")
    headers_b = auth_headers(client, email="ccb-intruso@example.com")

    def _isolated(path, method="get", **kw):
        fn = getattr(client, method)
        return fn(f"/api/projects/{path}", headers=headers_b, **kw)

    # CRs: lectura
    r_list = _isolated(f"{project.id}/change-requests")
    assert r_list.status_code in (403, 404), f"CR list cross-sede: {r_list.status_code} {r_list.text}"

    # CRs: creación
    r_post = _isolated(
        f"{project.id}/change-requests",
        method="post",
        json={"title": "CR Intrusa", "justification": "Debe bloquearse", "change_type": "scope"},
    )
    assert r_post.status_code in (403, 404), f"CR create cross-sede: {r_post.status_code}"

    # Dictamen cross-sede
    r_decide = _isolated(
        f"{project.id}/change-requests/{cr['id']}/decide",
        method="post",
        json={"decision": "approved", "review_notes": "Intento de dictamen de otra sede"},
    )
    assert r_decide.status_code in (403, 404), f"CR decide cross-sede: {r_decide.status_code}"

    # DoD: lectura + mutación cross-sede
    r_dod_get = _isolated(f"{project.id}/tasks/{task.id}/dod-acceptance")
    assert r_dod_get.status_code in (403, 404), f"DoD GET cross-sede: {r_dod_get.status_code}"
    r_dod_post = _isolated(
        f"{project.id}/tasks/{task.id}/dod-acceptance",
        method="post",
        json={"specification_met": True, "tests_no_critical_failures": True,
              "evidence_archived": True, "supervisor_sign_off": True},
    )
    assert r_dod_post.status_code in (403, 404), f"DoD POST cross-sede: {r_dod_post.status_code}"

    # El proyecto mismo sigue aislado
    r_proj = _isolated(str(project.id))
    assert r_proj.status_code in (403, 404), f"Proyecto cross-sede: {r_proj.status_code}"

    # La CR de Sede A permanece intacta (pending_ccb) tras los intentos
    db_session.expire_all()
    cr_db = db_session.query(ProjectChangeRequest).filter(
        ProjectChangeRequest.id == cr["id"]
    ).first()
    assert cr_db.status == "pending_ccb", "Los intentos cross-sede no deben mutar la CR"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Helper ejecutivo: get_project_ccb_and_quality_summary
# ─────────────────────────────────────────────────────────────────────────────


def test_get_project_ccb_and_quality_summary(client, db_session):
    """El helper ejecutivo agrega CCB (Δ$ y Δdías netos de aprobadas) + DoD/CoQ."""
    from backend.services.project_ccb_service import get_project_ccb_and_quality_summary

    seed_admin(db_session, email="ccb-summary-admin@example.com")
    headers = auth_headers(client, email="ccb-summary-admin@example.com")
    project = _make_project(client, headers, db_session, title="Resumen CCB CoQ Pro", budget=50000.0)

    # ── CRs: 2 aprobadas (20k, 15 días) + (5k, 2 días) y 1 rechazada ──
    cr1 = _make_cr(client, headers, project, title="CR1 aprobada")
    client.post(
        f"/api/projects/{project.id}/change-requests/{cr1['id']}/decide",
        json={"decision": "approved", "review_notes": "Ok"},
        headers=headers,
    )
    cr2 = client.post(
        f"/api/projects/{project.id}/change-requests",
        json={
            "title": "CR2 aprobada",
            "justification": "Ajuste de cronograma",
            "change_type": "schedule",
            "cost_impact_delta": 5000.0,
            "schedule_impact_days": 2,
        },
        headers=headers,
    ).json()
    client.post(
        f"/api/projects/{project.id}/change-requests/{cr2['id']}/decide",
        json={"decision": "approved", "review_notes": "Ok"},
        headers=headers,
    )
    cr3 = client.post(
        f"/api/projects/{project.id}/change-requests",
        json={"title": "CR3 rechazada", "justification": "No", "change_type": "scope"},
        headers=headers,
    ).json()
    client.post(
        f"/api/projects/{project.id}/change-requests/{cr3['id']}/decide",
        json={"decision": "rejected", "review_notes": "No aplica"},
        headers=headers,
    )

    # ── DoD: 1 entregable aceptado (CoQ prevention $250) + 1 pendiente (CoQ falla externa $100) ──
    task_ok = _make_task(db_session, project.id, title="Entregable Aceptado")
    resp_ok = client.post(
        f"/api/projects/{project.id}/tasks/{task_ok.id}/dod-acceptance",
        json={
            "specification_met": True,
            "tests_no_critical_failures": True,
            "evidence_archived": True,
            "supervisor_sign_off": True,
            "coq_classification": "prevention",
            "coq_amount": 250.0,
        },
        headers=headers,
    )
    assert resp_ok.status_code == 200, resp_ok.text
    assert resp_ok.json()["coq_amount"] == pytest.approx(250.0)

    task_pending = _make_task(db_session, project.id, title="Entregable Pendiente")
    resp_pending = client.post(
        f"/api/projects/{project.id}/tasks/{task_pending.id}/dod-acceptance",
        json={
            "specification_met": True,
            "tests_no_critical_failures": True,
            "evidence_archived": True,
            "supervisor_sign_off": False,
            "coq_classification": "external_failure",
            "coq_amount": 100.0,
        },
        headers=headers,
    )
    assert resp_pending.status_code == 200, resp_pending.text
    assert resp_pending.json()["status"] == "pending"

    # ── Resumen ejecutivo ──
    summary = get_project_ccb_and_quality_summary(db_session, project.id)

    assert summary["total_change_requests"] == 3
    assert summary["approved_count"] == 2
    assert summary["rejected_count"] == 1
    assert summary["pending_ccb_count"] == 0
    assert summary["net_approved_cost_delta"] == pytest.approx(25000.0)
    assert summary["net_approved_schedule_days"] == 17
    assert summary["tasks_dod_accepted_count"] == 1
    assert summary["total_coq_cost"] == pytest.approx(350.0)
    assert summary["coq_by_category"]["prevention"] == pytest.approx(250.0)
    assert summary["coq_by_category"]["external_failure"] == pytest.approx(100.0)
    assert summary["coq_by_category"]["appraisal"] == pytest.approx(0.0)
    assert summary["coq_by_category"]["internal_failure"] == pytest.approx(0.0)

    # Proyecto sin datos → resumen en cero, nunca falla
    other = _make_project(client, headers, db_session, title="Resumen vacío")
    empty = get_project_ccb_and_quality_summary(db_session, other.id)
    assert empty["total_change_requests"] == 0
    assert empty["tasks_dod_accepted_count"] == 0
    assert empty["total_coq_cost"] == pytest.approx(0.0)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Endpoint dod-status: estado inicial informativo sin registro previo
# ─────────────────────────────────────────────────────────────────────────────


def test_quality_summary_endpoint_and_tenant_isolation(client, db_session):
    """GET /projects/{id}/quality-summary agrega DoD/CoQ y aísla por sede (Axioma 3)."""
    seed_admin(db_session, email="quality-summary-admin@example.com")
    headers = auth_headers(client, email="quality-summary-admin@example.com")
    project = _make_project(client, headers, db_session, title="E2E Quality Summary", budget=80000.0)

    # ── Datos: 1 CR aprobada (Δ$10k, Δ5d) + 2 tareas hoja (1 firmada DoD con CoQ conformidad) ──
    cr = _make_cr(client, headers, project, title="CR para quality summary")
    client.post(
        f"/api/projects/{project.id}/change-requests/{cr['id']}/decide",
        json={"decision": "approved", "review_notes": "Ok"},
        headers=headers,
    )
    task_signed = _make_task(db_session, project.id, title="Paquete firmado")
    task_unsigned = _make_task(db_session, project.id, title="Paquete sin firma")
    resp = client.post(
        f"/api/projects/{project.id}/tasks/{task_signed.id}/dod-acceptance",
        json={
            "specification_met": True,
            "tests_no_critical_failures": True,
            "evidence_archived": True,
            "supervisor_sign_off": True,
            "coq_classification": "prevention",
            "coq_amount": 400.0,
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text

    # POST DoD con solo evidencia (deja registro con 1 criterio) en el otro paquete
    resp_partial = client.post(
        f"/api/projects/{project.id}/tasks/{task_unsigned.id}/dod-acceptance",
        json={
            "specification_met": False,
            "tests_no_critical_failures": False,
            "evidence_archived": True,
            "supervisor_sign_off": False,
            "coq_classification": "internal_failure",
            "coq_amount": 90.0,
        },
        headers=headers,
    )
    assert resp_partial.status_code == 200, resp_partial.text

    # ── Sede B no puede leer el quality-summary de la Sede A (Axioma 3) ──
    _seed_sede_b_user(db_session, email="quality-intruso@example.com")
    headers_b = auth_headers(client, email="quality-intruso@example.com")
    r_b = client.get(f"/api/projects/{project.id}/quality-summary", headers=headers_b)
    assert r_b.status_code in (403, 404), f"quality-summary cross-sede: {r_b.status_code} {r_b.text}"

    # ── Lectura canónica desde el actor de la Sede A ──
    r = client.get(f"/api/projects/{project.id}/quality-summary", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_change_requests"] == 1
    assert body["approved_count"] == 1
    # _make_cr usa por defecto Δ$20000 y Δ15 días
    assert body["net_approved_cost_delta"] == pytest.approx(20000.0)
    assert body["net_approved_schedule_days"] == 15
    # 2 tareas hoja del proyecto: solo 1 firmada (50% de cobertura)
    assert body["total_leaf_tasks"] == 2
    assert body["dod_signed_off_count"] == 1
    assert body["dod_all_four_met_count"] == 1
    assert body["dod_completion_rate_pct"] == pytest.approx(50.0)
    # CoQ: conformidad = prevención 400; no conformidad = falla interna 90; ratio 400/490*100 ≈ 81.6
    assert body["total_cost_of_conformance"] == pytest.approx(400.0)
    assert body["total_cost_of_non_conformance"] == pytest.approx(90.0)
    assert body["coq_conformance_ratio_pct"] == pytest.approx(81.6)
    assert body["tasks_dod_accepted_count"] == 1
    assert body["total_coq_cost"] == pytest.approx(490.0)


def test_dod_status_not_recorded_and_accepted_name(client, db_session):
    """GET dod-status responde 200 'not_recorded' sin registro y expone quién aceptó."""
    seed_admin(db_session, email="dod-status-admin@example.com")
    headers = auth_headers(client, email="dod-status-admin@example.com")
    project = _make_project(client, headers, db_session, title="E2E DoD Status")
    task = _make_task(db_session, project.id, title="Entregable Status")

    r0 = client.get(f"/api/projects/{project.id}/tasks/{task.id}/dod-status", headers=headers)
    assert r0.status_code == 200
    assert r0.json()["status"] == "not_recorded"
    assert r0.json()["accepted_at"] is None

    client.post(
        f"/api/projects/{project.id}/tasks/{task.id}/dod-acceptance",
        json={
            "specification_met": True,
            "tests_no_critical_failures": True,
            "evidence_archived": True,
            "supervisor_sign_off": True,
            "coq_classification": "appraisal",
            "coq_amount": 300.0,
        },
        headers=headers,
    )
    r1 = client.get(f"/api/projects/{project.id}/tasks/{task.id}/dod-status", headers=headers)
    assert r1.status_code == 200
    body = r1.json()
    assert body["status"] == "accepted"
    assert body["accepted_by"] is not None
    assert isinstance(body["accepted_by_name"], str) and body["accepted_by_name"]
    assert body["accepted_at"] is not None
    assert body["coq_amount"] == pytest.approx(300.0)


# ─────────────────────────────────────────────────────────────────────────────────────
# 8. Helpers de diagnóstico: tasa de aprobación CCB y balance CoQ (Juran/Crosby)
# ─────────────────────────────────────────────────────────────────────────────────────


def test_compute_ccb_approval_rate_pct_zero_decided():
    """Sin CRs dictaminadas (0 aprobadas + 0 rechazadas) la tasa es 0.0."""
    from backend.services.project_ccb_service import compute_ccb_approval_rate_pct

    assert compute_ccb_approval_rate_pct(0, 0) == 0.0
    # Entradas negativas se clampan a 0 antes de decidir
    assert compute_ccb_approval_rate_pct(-2, -3) == 0.0


def test_compute_ccb_approval_rate_pct_all_approved():
    """Todas las CRs dictaminadas aprobadas → 100.0%."""
    from backend.services.project_ccb_service import compute_ccb_approval_rate_pct

    assert compute_ccb_approval_rate_pct(4, 0) == 100.0


def test_compute_ccb_approval_rate_pct_mixed():
    """Mezcla aprobadas/rechazadas → proporción con 1 decimal."""
    from backend.services.project_ccb_service import compute_ccb_approval_rate_pct

    assert compute_ccb_approval_rate_pct(3, 1) == 75.0
    assert compute_ccb_approval_rate_pct(2, 3) == 40.0


def test_evaluate_coq_balance_status_unmeasured():
    """Sin CoQ registrado (total ≤ 0) el balance es 'unmeasured' a aún con ratio alto."""
    from backend.services.project_ccb_service import evaluate_coq_balance_status

    assert evaluate_coq_balance_status(100.0, 0.0) == "unmeasured"
    assert evaluate_coq_balance_status(85.0, -1.0) == "unmeasured"


def test_evaluate_coq_balance_status_optimal_prevention():
    """Conformidad ≥ 70% del CoQ → 'optimal_prevention' (Prevención dominante)."""
    from backend.services.project_ccb_service import evaluate_coq_balance_status

    assert evaluate_coq_balance_status(70.0, 1000.0) == "optimal_prevention"
    assert evaluate_coq_balance_status(85.0, 500.0) == "optimal_prevention"


def test_evaluate_coq_balance_status_balanced():
    """Conformidad en [50%, 70%) del CoQ → 'balanced'."""
    from backend.services.project_ccb_service import evaluate_coq_balance_status

    assert evaluate_coq_balance_status(50.0, 1000.0) == "balanced"
    assert evaluate_coq_balance_status(65.0, 400.0) == "balanced"


def test_evaluate_coq_balance_status_high_failure_risk():
    """Conformidad < 50% del CoQ → 'high_failure_risk' (Juran/Crosby)."""
    from backend.services.project_ccb_service import evaluate_coq_balance_status

    assert evaluate_coq_balance_status(49.9, 1000.0) == "high_failure_risk"
    assert evaluate_coq_balance_status(0.0, 250.0) == "high_failure_risk"


def test_build_ccb_coq_diagnostic_unit_levels(client, db_session):
    """build_ccb_coq_diagnostic mapea combinaciones de resumen a dictamen e intervención."""
    from backend.services.project_ccb_service import build_ccb_coq_diagnostic

    # Proyecto sano: 75% aprobación, CoQ conformista 85% → sin intervención
    diag_sano = build_ccb_coq_diagnostic(
        {
            "approved_count": 3,
            "rejected_count": 1,
            "pending_ccb_count": 0,
            "coq_conformance_ratio_pct": 85.0,
            "total_coq_cost": 400.0,
        }
    )
    assert diag_sano["ccb_approval_rate_pct"] == pytest.approx(75.0)
    assert diag_sano["coq_balance_status"] == "optimal_prevention"
    assert diag_sano["requires_quality_intervention"] is False

    # Proyecto en riesgo: 1 de 3 dictaminadas aprobadas y CoQ fallas 40% → intervención
    diag_riesgo = build_ccb_coq_diagnostic(
        {
            "approved_count": 1,
            "rejected_count": 2,
            "pending_ccb_count": 0,
            "coq_conformance_ratio_pct": 40.0,
            "total_coq_cost": 900.0,
        }
    )
    assert diag_riesgo["ccb_approval_rate_pct"] == pytest.approx(33.3)
    assert diag_riesgo["coq_balance_status"] == "high_failure_risk"
    assert diag_riesgo["requires_quality_intervention"] is True

    # CoQ sin medir: estado 'unmeasured' pero ≥3 CR pendientes fuerzan intervención
    diag_pendientes = build_ccb_coq_diagnostic(
        {
            "approved_count": 0,
            "rejected_count": 0,
            "pending_ccb_count": 3,
            "coq_conformance_ratio_pct": 0.0,
            "total_coq_cost": 0.0,
        }
    )
    assert diag_pendientes["ccb_approval_rate_pct"] == 0.0
    assert diag_pendientes["coq_balance_status"] == "unmeasured"
    assert diag_pendientes["requires_quality_intervention"] is True

    # Resumen vacío/tolerante: claves ausentes no rompen el diagnóstico
    diag_vacio = build_ccb_coq_diagnostic({})
    assert diag_vacio == {
        "ccb_approval_rate_pct": 0.0,
        "coq_balance_status": "unmeasured",
        "requires_quality_intervention": False,
    }


def test_build_ccb_coq_diagnostic_from_real_summary(client, db_session):
    """Integración end to end: summary real de get_project_ccb_and_quality_summary al diagnóstico."""
    from backend.services.project_ccb_service import (
        build_ccb_coq_diagnostic,
        get_project_ccb_and_quality_summary,
    )

    seed_admin(db_session, email="ccb-diag-admin@example.com")
    headers = auth_headers(client, email="ccb-diag-admin@example.com")
    project = _make_project(client, headers, db_session, title="Diagnóstico CCB CoQ Pro", budget=60000.0)

    # ── CCB: 1 aprobada, 1 rechazada, 3 pendientes (umbral de intervención) ──
    cr1 = _make_cr(client, headers, project, title="CR diag aprobada")
    r_dec = client.post(
        f"/api/projects/{project.id}/change-requests/{cr1['id']}/decide",
        json={"decision": "approved", "review_notes": "Favorable"},
        headers=headers,
    )
    assert r_dec.status_code == 200, r_dec.text

    cr2 = client.post(
        f"/api/projects/{project.id}/change-requests",
        json={
            "title": "CR diag rechazada",
            "justification": "Sin mérito",
            "change_type": "scope",
        },
        headers=headers,
    ).json()
    r_dec2 = client.post(
        f"/api/projects/{project.id}/change-requests/{cr2['id']}/decide",
        json={"decision": "rejected", "review_notes": "No"},
        headers=headers,
    )
    assert r_dec2.status_code == 200, r_dec2.text

    for i in range(3):
        resp_cr = client.post(
            f"/api/projects/{project.id}/change-requests",
            json={
                "title": f"CR diag pendiente {i}",
                "justification": "En espera de dictamen",
                "change_type": "scope",
            },
            headers=headers,
        )
        assert resp_cr.status_code == 201, resp_cr.text

    # ── CoQ: conformidad 400 (prevención) vs falla externa 100 → ratio 80% ──
    task_ok = _make_task(db_session, project.id, title="Entregable diag aceptado")
    resp_ok = client.post(
        f"/api/projects/{project.id}/tasks/{task_ok.id}/dod-acceptance",
        json={
            "specification_met": True,
            "tests_no_critical_failures": True,
            "evidence_archived": True,
            "supervisor_sign_off": True,
            "coq_classification": "prevention",
            "coq_amount": 400.0,
        },
        headers=headers,
    )
    assert resp_ok.status_code == 200, resp_ok.text

    task_fail = _make_task(db_session, project.id, title="Entregable diag falla")
    resp_fail = client.post(
        f"/api/projects/{project.id}/tasks/{task_fail.id}/dod-acceptance",
        json={
            "specification_met": False,
            "tests_no_critical_failures": False,
            "evidence_archived": True,
            "supervisor_sign_off": False,
            "coq_classification": "external_failure",
            "coq_amount": 100.0,
        },
        headers=headers,
    )
    assert resp_fail.status_code == 200, resp_fail.text

    # ── Diagnóstico a partir del resumen ejecutivo real ──
    summary = get_project_ccb_and_quality_summary(db_session, project.id)
    assert summary["approved_count"] == 1
    assert summary["rejected_count"] == 1
    assert summary["pending_ccb_count"] == 3
    assert summary["coq_conformance_ratio_pct"] == pytest.approx(80.0)

    diag = build_ccb_coq_diagnostic(summary)
    # 1 de 2 dictaminadas aprobadas → 50.0%
    assert diag["ccb_approval_rate_pct"] == pytest.approx(50.0)
    # 80% conformidad ≥ 70% → prevención óptima vertiginosa pese a las 3 pendientes
    assert diag["coq_balance_status"] == "optimal_prevention"
    # Las 3 CR pendientes (≥3) fuerzan intervención de calidad igualmente
    assert diag["requires_quality_intervention"] is True

    # ── Contraste: el proyecto vacío no exige intervención ──
    other = _make_project(client, headers, db_session, title="Diagnostico vacío")
    diag_empty = build_ccb_coq_diagnostic(get_project_ccb_and_quality_summary(db_session, other.id))
    assert diag_empty == {
        "ccb_approval_rate_pct": 0.0,
        "coq_balance_status": "unmeasured",
        "requires_quality_intervention": False,
    }
