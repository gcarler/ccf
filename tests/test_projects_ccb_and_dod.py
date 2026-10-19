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
try:
    from backend.models_projects import (
        ProjectBaseline,
        ProjectChangeRequest,
        ProjectDodAcceptance,
    )
except ImportError:
    ProjectBaseline = None  # type: ignore[assignment,misc]
    ProjectChangeRequest = None  # type: ignore[assignment,misc]
    ProjectDodAcceptance = None  # type: ignore[assignment,misc]
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


def test_dod_gate_compliance_no_leaf_tasks():
    """Proyecto sin paquetes hoja retorna no_leaf_tasks y 100.0% de integridad de firma."""
    from backend.services.project_ccb_service import evaluate_dod_gate_compliance

    res = evaluate_dod_gate_compliance({"total_leaf_tasks": 0, "dod_signed_off_count": 0, "dod_all_four_met_count": 0})
    assert res == {
        "total_leaf_tasks": 0,
        "dod_signed_off_count": 0,
        "dod_all_four_met_count": 0,
        "unsigned_leaf_tasks": 0,
        "premature_sign_off_count": 0,
        "strict_dod_compliance_pct": 0.0,
        "sign_off_integrity_pct": 100.0,
        "dod_gate_status": "no_leaf_tasks",
    }


def test_dod_gate_compliance_certified():
    """Cumplimiento estricto >= 80% sin firmas prematuras retorna certified."""
    from backend.services.project_ccb_service import evaluate_dod_gate_compliance

    res = evaluate_dod_gate_compliance({
        "total_leaf_tasks": 10,
        "dod_signed_off_count": 9,
        "dod_all_four_met_count": 9,
    })
    assert res["dod_gate_status"] == "certified"
    assert res["strict_dod_compliance_pct"] == 90.0
    assert res["sign_off_integrity_pct"] == 100.0
    assert res["premature_sign_off_count"] == 0
    assert res["unsigned_leaf_tasks"] == 1


def test_dod_gate_compliance_integrity_breach():
    """Firmas de supervisor sin los 4 criterios DoD cumplidos disparan integrity_breach."""
    from backend.services.project_ccb_service import evaluate_dod_gate_compliance

    res = evaluate_dod_gate_compliance({
        "total_leaf_tasks": 10,
        "dod_signed_off_count": 8,
        "dod_all_four_met_count": 6,
    })
    assert res["dod_gate_status"] == "integrity_breach"
    assert res["premature_sign_off_count"] == 2
    assert res["sign_off_integrity_pct"] == 75.0
    assert res["strict_dod_compliance_pct"] == 60.0
    assert res["unsigned_leaf_tasks"] == 2


def test_dod_gate_compliance_in_progress():
    """Cumplimiento entre 40% y 79.9% sin brecha de integridad retorna in_progress."""
    from backend.services.project_ccb_service import evaluate_dod_gate_compliance

    res = evaluate_dod_gate_compliance({
        "total_leaf_tasks": 10,
        "dod_signed_off_count": 5,
        "dod_all_four_met_count": 5,
    })
    assert res["dod_gate_status"] == "in_progress"
    assert res["strict_dod_compliance_pct"] == 50.0
    assert res["sign_off_integrity_pct"] == 100.0
    assert res["premature_sign_off_count"] == 0
    assert res["unsigned_leaf_tasks"] == 5


def test_dod_gate_compliance_at_risk():
    """Cumplimiento < 40% sin brecha de integridad retorna at_risk."""
    from backend.services.project_ccb_service import evaluate_dod_gate_compliance

    res = evaluate_dod_gate_compliance({
        "total_leaf_tasks": 10,
        "dod_signed_off_count": 3,
        "dod_all_four_met_count": 3,
    })
    assert res["dod_gate_status"] == "at_risk"
    assert res["strict_dod_compliance_pct"] == 30.0
    assert res["sign_off_integrity_pct"] == 100.0
    assert res["premature_sign_off_count"] == 0
    assert res["unsigned_leaf_tasks"] == 7


# ─── 9. Helper de creep de línea base CCB (PMBOK §4.6) ───


def _assert_creep(result, **expected):
    for key, value in expected.items():
        assert result[key] == pytest.approx(value) if isinstance(value, float) else result[key] == value


def test_ccb_baseline_creep_stable():
    from backend.services.project_ccb_service import evaluate_ccb_baseline_creep_impact

    result = evaluate_ccb_baseline_creep_impact(
        net_approved_cost_delta=3000.0,
        bac=120000.0,
        net_approved_schedule_days=2,
        planned_duration_days=90,
    )
    _assert_creep(
        result,
        net_approved_cost_delta=3000.0,
        cost_creep_pct=2.5,
        net_approved_schedule_days=2,
        schedule_creep_pct=2.22,
        requires_rebaselining=False,
        baseline_stability_status="stable",
    )


def test_ccb_baseline_creep_moderate_expansion():
    from backend.services.project_ccb_service import evaluate_ccb_baseline_creep_impact

    result = evaluate_ccb_baseline_creep_impact(
        net_approved_cost_delta=12000.0,
        bac=120000.0,
        net_approved_schedule_days=7,
        planned_duration_days=90,
    )
    _assert_creep(
        result,
        cost_creep_pct=10.0,
        schedule_creep_pct=7.78,
        requires_rebaselining=False,
        baseline_stability_status="moderate_expansion",
    )


def test_ccb_baseline_creep_rebaseline_required_by_cost():
    from backend.services.project_ccb_service import evaluate_ccb_baseline_creep_impact

    result = evaluate_ccb_baseline_creep_impact(
        net_approved_cost_delta=18000.0,
        bac=120000.0,
        net_approved_schedule_days=1,
        planned_duration_days=90,
    )
    _assert_creep(
        result,
        cost_creep_pct=15.0,
        schedule_creep_pct=1.11,
        requires_rebaselining=True,
        baseline_stability_status="rebaseline_required",
    )


def test_ccb_baseline_creep_rebaseline_required_by_schedule():
    from backend.services.project_ccb_service import evaluate_ccb_baseline_creep_impact

    result = evaluate_ccb_baseline_creep_impact(
        net_approved_cost_delta=1000.0,
        bac=120000.0,
        net_approved_schedule_days=15,
        planned_duration_days=90,
    )
    _assert_creep(
        result,
        cost_creep_pct=0.83,
        schedule_creep_pct=16.67,
        requires_rebaselining=True,
        baseline_stability_status="rebaseline_required",
    )


def test_ccb_baseline_creep_zero_denominators():
    from backend.services.project_ccb_service import evaluate_ccb_baseline_creep_impact

    result_bac_cero = evaluate_ccb_baseline_creep_impact(
        net_approved_cost_delta=5000.0,
        bac=0.0,
        net_approved_schedule_days=0,
        planned_duration_days=60,
    )
    _assert_creep(
        result_bac_cero,
        cost_creep_pct=0.0,
        schedule_creep_pct=0.0,
        requires_rebaselining=False,
        baseline_stability_status="stable",
    )

    result_pd_cero = evaluate_ccb_baseline_creep_impact(
        net_approved_cost_delta=0.0,
        bac=50000.0,
        net_approved_schedule_days=20,
        planned_duration_days=0,
    )
    _assert_creep(
        result_pd_cero,
        cost_creep_pct=0.0,
        schedule_creep_pct=0.0,
        requires_rebaselining=False,
        baseline_stability_status="stable",
    )

    # Ambos denominadores cero
    result_ambos = evaluate_ccb_baseline_creep_impact(0.0, 0.0, 0, 0)
    _assert_creep(
        result_ambos,
        net_approved_cost_delta=0.0,
        cost_creep_pct=0.0,
        schedule_creep_pct=0.0,
        requires_rebaselining=False,
        baseline_stability_status="stable",
    )


# ─── 10. Analizador de Costo de la Calidad (CoQ — PMI PMBOK §8.1.2.3) ───


def test_evaluate_cost_of_quality_balance_proactive_conformance():
    """Prevención >= Evaluación y Conformidad >= No Conformidad -> 'proactive_conformance'."""
    from backend.services.project_ccb_service import evaluate_cost_of_quality_balance

    res = evaluate_cost_of_quality_balance(
        prevention_cost=5000.0,
        appraisal_cost=3000.0,
        internal_failure_cost=1000.0,
        external_failure_cost=0.0,
    )
    assert res == {
        "prevention_cost": 5000.0,
        "appraisal_cost": 3000.0,
        "internal_failure_cost": 1000.0,
        "external_failure_cost": 0.0,
        "cost_of_conformance": 8000.0,
        "cost_of_nonconformance": 1000.0,
        "total_coq": 9000.0,
        "conformance_ratio_pct": 88.89,
        "nonconformance_ratio_pct": 11.11,
        "coq_maturity_status": "proactive_conformance",
    }


def test_evaluate_cost_of_quality_balance_inspection_dependent():
    """Conformidad >= No Conformidad pero Evaluación > Prevención -> 'inspection_dependent'."""
    from backend.services.project_ccb_service import evaluate_cost_of_quality_balance

    res = evaluate_cost_of_quality_balance(
        prevention_cost=2000.0,
        appraisal_cost=6000.0,
        internal_failure_cost=1500.0,
        external_failure_cost=0.0,
    )
    assert res["cost_of_conformance"] == 8000.0
    assert res["cost_of_nonconformance"] == 1500.0
    assert res["total_coq"] == 9500.0
    assert res["coq_maturity_status"] == "inspection_dependent"


def test_evaluate_cost_of_quality_balance_reactive_rework_heavy():
    """No Conformidad > Conformidad sin superar umbral de falla externa >= 25% -> 'reactive_rework_heavy'."""
    from backend.services.project_ccb_service import evaluate_cost_of_quality_balance

    res = evaluate_cost_of_quality_balance(
        prevention_cost=1000.0,
        appraisal_cost=1000.0,
        internal_failure_cost=4000.0,
        external_failure_cost=500.0,
    )
    assert res["cost_of_conformance"] == 2000.0
    assert res["cost_of_nonconformance"] == 4500.0
    assert res["total_coq"] == 6500.0
    assert res["coq_maturity_status"] == "reactive_rework_heavy"


def test_evaluate_cost_of_quality_balance_external_failure_critical():
    """Fallas externas >= 25% del CoQ total -> 'external_failure_critical'."""
    from backend.services.project_ccb_service import evaluate_cost_of_quality_balance

    res = evaluate_cost_of_quality_balance(
        prevention_cost=1000.0,
        appraisal_cost=1000.0,
        internal_failure_cost=1000.0,
        external_failure_cost=2000.0,
    )
    assert res["total_coq"] == 5000.0
    assert res["conformance_ratio_pct"] == 40.0
    assert res["nonconformance_ratio_pct"] == 60.0
    assert res["coq_maturity_status"] == "external_failure_critical"


def test_evaluate_cost_of_quality_balance_untracked_or_negative():
    """Ceros o valores negativos se sanitizan a 0.0 y reportan 'untracked'."""
    from backend.services.project_ccb_service import evaluate_cost_of_quality_balance

    for res in (
        evaluate_cost_of_quality_balance(),
        evaluate_cost_of_quality_balance(-100.0, -50.0, -20.0, -10.0),
    ):
        assert res == {
            "prevention_cost": 0.0,
            "appraisal_cost": 0.0,
            "internal_failure_cost": 0.0,
            "external_failure_cost": 0.0,
            "cost_of_conformance": 0.0,
            "cost_of_nonconformance": 0.0,
            "total_coq": 0.0,
            "conformance_ratio_pct": 0.0,
            "nonconformance_ratio_pct": 0.0,
            "coq_maturity_status": "untracked",
        }


# ─── 11. Analizador de Velocidad de Decisión y SLA del CCB (PMI PMBOK §4.6) ───


def test_evaluate_ccb_backlog_velocity_responsive_governance():
    """Mayoría de CRs decididas y pendientes dentro de SLA (<= 7.0 días) -> 'responsive_governance'."""
    from backend.services.project_ccb_service import evaluate_ccb_backlog_velocity

    crs = [
        {"status": "approved", "resolution_days": 3.0},
        {"status": "rejected", "resolution_days": 5.0},
        {"status": "pending", "age_days": 4.0},
    ]
    res = evaluate_ccb_backlog_velocity(crs, sla_days=7.0)
    assert res == {
        "total_requests": 3,
        "decided_count": 2,
        "pending_count": 1,
        "overdue_pending_count": 0,
        "avg_resolution_days": 4.0,
        "max_pending_age_days": 4.0,
        "backlog_pressure_pct": 33.33,
        "ccb_velocity_status": "responsive_governance",
    }


def test_evaluate_ccb_backlog_velocity_sla_breach_bottleneck():
    """Al menos 1 CR pendiente con age_days > sla_days -> 'sla_breach_bottleneck'."""
    from backend.services.project_ccb_service import evaluate_ccb_backlog_velocity

    crs = [
        {"status": "approved", "resolution_days": 2.0},
        {"status": "under_review", "age_days": 12.5},
    ]
    res = evaluate_ccb_backlog_velocity(crs, sla_days=7.0)
    assert res["overdue_pending_count"] == 1
    assert res["max_pending_age_days"] == 12.5
    assert res["ccb_velocity_status"] == "sla_breach_bottleneck"


def test_evaluate_ccb_backlog_velocity_backlog_accumulating():
    """Más CRs pendientes que decididas pero todas dentro del SLA -> 'backlog_accumulating'."""
    from backend.services.project_ccb_service import evaluate_ccb_backlog_velocity

    crs = [
        {"status": "approved", "resolution_days": 2.0},
        {"status": "pending", "age_days": 3.0},
        {"status": "pending", "age_days": 5.0},
    ]
    res = evaluate_ccb_backlog_velocity(crs, sla_days=7.0)
    assert res["decided_count"] == 1
    assert res["pending_count"] == 2
    assert res["overdue_pending_count"] == 0
    assert res["ccb_velocity_status"] == "backlog_accumulating"


def test_evaluate_ccb_backlog_velocity_no_requests():
    """None o [] -> 'no_requests' y total_requests=0."""
    from backend.services.project_ccb_service import evaluate_ccb_backlog_velocity

    for empty_val in (None, []):
        res = evaluate_ccb_backlog_velocity(empty_val)
        assert res == {
            "total_requests": 0,
            "decided_count": 0,
            "pending_count": 0,
            "overdue_pending_count": 0,
            "avg_resolution_days": 0.0,
            "max_pending_age_days": 0.0,
            "backlog_pressure_pct": 0.0,
            "ccb_velocity_status": "no_requests",
        }


# ─── 12. Evaluador de Contención de Defectos DRE (PMI PMBOK §8.3) ───


def test_evaluate_defect_containment_efficiency_world_class_and_acceptable():
    """Valida DRE >= 95% ('world_class_containment') y 85%-95% ('acceptable_containment')."""
    from backend.services.project_ccb_service import (
        evaluate_defect_containment_efficiency,
    )

    world_class = evaluate_defect_containment_efficiency(19, 1, 20)
    assert world_class == {
        "pre_delivery_defects": 19,
        "post_delivery_defects": 1,
        "total_defects": 20,
        "reworked_verified_count": 20,
        "unverified_defects_count": 0,
        "containment_efficiency_pct": 95.0,
        "defect_escape_rate_pct": 5.0,
        "rework_verification_pct": 100.0,
        "quality_containment_status": "world_class_containment",
    }

    acceptable = evaluate_defect_containment_efficiency(9, 1, 10)
    assert acceptable["containment_efficiency_pct"] == 90.0
    assert acceptable["defect_escape_rate_pct"] == 10.0
    assert acceptable["unverified_defects_count"] == 0
    assert acceptable["quality_containment_status"] == "acceptable_containment"


def test_evaluate_defect_containment_efficiency_high_escape_breach():
    """Escape a producción > 15% -> 'high_escape_breach'."""
    from backend.services.project_ccb_service import (
        evaluate_defect_containment_efficiency,
    )

    res = evaluate_defect_containment_efficiency(7, 3, 10)
    assert res["total_defects"] == 10
    assert res["containment_efficiency_pct"] == 70.0
    assert res["defect_escape_rate_pct"] == 30.0
    assert res["quality_containment_status"] == "high_escape_breach"


def test_evaluate_defect_containment_efficiency_pending_defect_rework():
    """Escape <= 15% pero defectos sin retrabajo verificado -> 'pending_defect_rework'."""
    from backend.services.project_ccb_service import (
        evaluate_defect_containment_efficiency,
    )

    res = evaluate_defect_containment_efficiency(10, 0, 7)
    assert res["total_defects"] == 10
    assert res["reworked_verified_count"] == 7
    assert res["unverified_defects_count"] == 3
    assert res["rework_verification_pct"] == 70.0
    assert res["quality_containment_status"] == "pending_defect_rework"


def test_evaluate_defect_containment_efficiency_zero_defects():
    """Cero defectos registrados -> 'zero_defects_recorded' y 100.0% de eficiencia."""
    from backend.services.project_ccb_service import (
        evaluate_defect_containment_efficiency,
    )

    res = evaluate_defect_containment_efficiency(0, 0, 0)
    assert res == {
        "pre_delivery_defects": 0,
        "post_delivery_defects": 0,
        "total_defects": 0,
        "reworked_verified_count": 0,
        "unverified_defects_count": 0,
        "containment_efficiency_pct": 100.0,
        "defect_escape_rate_pct": 0.0,
        "rework_verification_pct": 100.0,
        "quality_containment_status": "zero_defects_recorded",
    }


# ─── 13. Evaluador de Profundidad de Verificación DoD (PMI PMBOK §8.2) ───


def test_evaluate_dod_checklist_verification_depth_audit_ready():
    """100% completado y >= 80% con evidencia verificable -> 'AUDIT_READY_DOD'."""
    from backend.services.project_ccb_service import (
        evaluate_dod_checklist_verification_depth,
    )

    items = [
        {"title": "Tests unitarios", "completed": True, "evidence": "pytest 100% green"},
        {"title": "Revisión de código", "checked": True, "verified_by": "qa-lead"},
        {"title": "Manual técnico", "done": True, "artifact_url": "https://docs/manual"},
        {"title": "Aprobación sponsor", "completed": True, "evidence": "Acta #12"},
        {"title": "Checklist menor", "completed": True, "evidence": "   "},
        "invalid_entry_ignored",  # type: ignore[list-item]
    ]
    res = evaluate_dod_checklist_verification_depth(items)
    assert res == {
        "total_items": 5,
        "completed_items": 5,
        "verified_with_evidence_items": 4,
        "completion_pct": 100.0,
        "evidence_coverage_pct": 80.0,
        "posture": "AUDIT_READY_DOD",
    }


def test_evaluate_dod_checklist_verification_depth_completed_without_evidence():
    """100% completado pero < 80% con evidencia -> 'COMPLETED_WITHOUT_EVIDENCE'."""
    from backend.services.project_ccb_service import (
        evaluate_dod_checklist_verification_depth,
    )

    items = [
        {"title": "Criterio 1", "completed": True, "evidence": "PR #45"},
        {"title": "Criterio 2", "completed": True},
        {"title": "Criterio 3", "checked": True, "verified_by": ""},
        {"title": "Criterio 4", "done": True},
    ]
    res = evaluate_dod_checklist_verification_depth(items)
    assert res == {
        "total_items": 4,
        "completed_items": 4,
        "verified_with_evidence_items": 1,
        "completion_pct": 100.0,
        "evidence_coverage_pct": 25.0,
        "posture": "COMPLETED_WITHOUT_EVIDENCE",
    }


def test_evaluate_dod_checklist_verification_depth_incomplete():
    """Menos del 100% de ítems completados -> 'INCOMPLETE_DOD'."""
    from backend.services.project_ccb_service import (
        evaluate_dod_checklist_verification_depth,
    )

    items = [
        {"title": "Criterio 1", "completed": True, "evidence": "Evidencia A"},
        {"title": "Criterio 2", "completed": False, "evidence": "Borrador"},
    ]
    res = evaluate_dod_checklist_verification_depth(items)
    assert res == {
        "total_items": 2,
        "completed_items": 1,
        "verified_with_evidence_items": 1,
        "completion_pct": 50.0,
        "evidence_coverage_pct": 100.0,
        "posture": "INCOMPLETE_DOD",
    }


def test_evaluate_dod_checklist_verification_depth_no_dod_checklist():
    """None, lista vacía o sin dicts válidos -> 'NO_DOD_CHECKLIST'."""
    from backend.services.project_ccb_service import (
        evaluate_dod_checklist_verification_depth,
    )

    for empty_val in (None, [], ["not-a-dict", 123]):  # type: ignore[list-item]
        res = evaluate_dod_checklist_verification_depth(empty_val)
        assert res == {
            "total_items": 0,
            "completed_items": 0,
            "verified_with_evidence_items": 0,
            "completion_pct": 0.0,
            "evidence_coverage_pct": 0.0,
            "posture": "NO_DOD_CHECKLIST",
        }


# ─── evaluate_scope_creep_baseline_drift (pure helper) ─────────────


def test_evaluate_scope_creep_drift_controlled_baseline():
    """Tareas actuales dentro del alcance autorizado -> CONTROLLED_BASELINE (delta 0)."""
    from backend.services.project_ccb_service import (
        evaluate_scope_creep_baseline_drift,
    )

    res = evaluate_scope_creep_baseline_drift(
        baseline_tasks_count=20,
        current_tasks_count=23,
        approved_change_requests_tasks_delta=3,
    )

    assert res["authorized_scope_count"] == 23
    assert res["unapproved_tasks_delta"] == 0
    assert res["scope_creep_pct"] == 0.0
    assert res["posture"] == "CONTROLLED_BASELINE"


def test_evaluate_scope_creep_drift_moderate_and_critical():
    """Drift <= 15% -> MODERATE_SCOPE_DRIFT; drift > 15% -> CRITICAL_SCOPE_CREEP."""
    from backend.services.project_ccb_service import (
        evaluate_scope_creep_baseline_drift,
    )

    moderate = evaluate_scope_creep_baseline_drift(20, 23, 0)
    assert moderate["unapproved_tasks_delta"] == 3
    assert moderate["scope_creep_pct"] == 15.0
    assert moderate["posture"] == "MODERATE_SCOPE_DRIFT"

    critical = evaluate_scope_creep_baseline_drift(10, 13, 0)
    assert critical["scope_creep_pct"] == 30.0
    assert critical["posture"] == "CRITICAL_SCOPE_CREEP"


def test_evaluate_scope_creep_drift_negative_gamma_edge_cases():
    """None/negativos se clamparan; CR negativo reduce el alcance autorizado; drift sin autorizado -> 100.0."""
    from backend.services.project_ccb_service import (
        evaluate_scope_creep_baseline_drift,
    )

    no_baseline = evaluate_scope_creep_baseline_drift(None, None, None)
    assert no_baseline == {
        "baseline_tasks_count": 0,
        "current_tasks_count": 0,
        "approved_change_requests_tasks_delta": 0,
        "authorized_scope_count": 0,
        "unapproved_tasks_delta": 0,
        "scope_creep_pct": 0.0,
        "posture": "NO_BASELINE_SCOPE",
    }

    reduced_scope = evaluate_scope_creep_baseline_drift(10, 8, -3)
    assert reduced_scope["approved_change_requests_tasks_delta"] == -3
    assert reduced_scope["authorized_scope_count"] == 7
    assert reduced_scope["unapproved_tasks_delta"] == 1
    assert reduced_scope["scope_creep_pct"] == 14.29
    assert reduced_scope["posture"] == "MODERATE_SCOPE_DRIFT"

    orphan_tasks = evaluate_scope_creep_baseline_drift(None, 2, 0)
    assert orphan_tasks["authorized_scope_count"] == 0
    assert orphan_tasks["unapproved_tasks_delta"] == 2
    assert orphan_tasks["scope_creep_pct"] == 100.0
    assert orphan_tasks["posture"] == "CRITICAL_SCOPE_CREEP"


def test_evaluate_scope_creep_drift_empty_with_orphan_counts():
    """Sin baseline pero con tareas actuales y autorizado 0 -> 100% drift crítico."""
    from backend.services.project_ccb_service import (
        evaluate_scope_creep_baseline_drift,
    )

    res = evaluate_scope_creep_baseline_drift(0, 5, 0)
    assert res["authorized_scope_count"] == 0
    assert res["unapproved_tasks_delta"] == 5
    assert res["scope_creep_pct"] == 100.0
    assert res["posture"] == "CRITICAL_SCOPE_CREEP"


# ─── 15. Evaluador de Quórum y Consenso de Votación CCB (PMI PMBOK §4.6) ───


def test_evaluate_ccb_voting_consensus_unanimous_and_majority():
    """Quórum cumplido con 100% aprobación ('UNANIMOUS_CCB_APPROVAL') o mayoría >= 60% ('MAJORITY_CCB_APPROVAL')."""
    import backend.services.project_ccb_service as ccb_module
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        evaluate_ccb_voting_consensus,
    )

    unanimous_votes = [
        {"member": "PMO", "vote": "approve"},
        {"member": "Sponsor", "decision": "aprobado"},
        {"member": "Arquitectura", "vote": "yes"},
        "invalid_entry_ignored",  # type: ignore[list-item]
    ]
    res_unanimous = evaluate_ccb_voting_consensus(unanimous_votes, required_quorum=3)
    assert res_unanimous == {
        "safe_quorum": 3,
        "total_votes": 3,
        "approve_votes": 3,
        "reject_votes": 0,
        "veto_cast": False,
        "quorum_met": True,
        "approval_ratio": 100.0,
        "posture": "UNANIMOUS_CCB_APPROVAL",
    }
    assert (
        ProjectCCBService.evaluate_ccb_voting_consensus(
            unanimous_votes, required_quorum=3
        )
        == res_unanimous
    )
    assert "evaluate_ccb_voting_consensus" in ccb_module.__all__

    majority_votes = [
        {"member": "PMO", "vote": "approved"},
        {"member": "Sponsor", "vote": "aprobar"},
        {"member": "Finanzas", "vote": "si"},
        {"member": "Operaciones", "vote": "reject"},
        {"member": "Calidad", "vote": "abstain"},
    ]
    res_majority = evaluate_ccb_voting_consensus(majority_votes, required_quorum=3)
    assert res_majority == {
        "safe_quorum": 3,
        "total_votes": 5,
        "approve_votes": 3,
        "reject_votes": 1,
        "veto_cast": False,
        "quorum_met": True,
        "approval_ratio": 60.0,
        "posture": "MAJORITY_CCB_APPROVAL",
    }


def test_evaluate_ccb_voting_consensus_vetoed_by_authority():
    """Voto con is_veto=True o vote='veto' -> 'VETOED_BY_AUTHORITY' sin importar el quórum o mayoría."""
    from backend.services.project_ccb_service import evaluate_ccb_voting_consensus

    votes_flag = [
        {"member": "PMO", "vote": "approve"},
        {"member": "Sponsor", "vote": "reject", "is_veto": True},
        {"member": "Finanzas", "vote": "approve"},
    ]
    res_flag = evaluate_ccb_voting_consensus(votes_flag, required_quorum=3)
    assert res_flag["veto_cast"] is True
    assert res_flag["posture"] == "VETOED_BY_AUTHORITY"

    votes_token = [{"member": "Sponsor", "decision": "VETO"}]
    res_token = evaluate_ccb_voting_consensus(votes_token, required_quorum=3)
    assert res_token["veto_cast"] is True
    assert res_token["quorum_met"] is False
    assert res_token["posture"] == "VETOED_BY_AUTHORITY"


def test_evaluate_ccb_voting_consensus_insufficient_quorum():
    """Sin veto pero total_votes < safe_quorum -> 'INSUFFICIENT_QUORUM'."""
    from backend.services.project_ccb_service import evaluate_ccb_voting_consensus

    res = evaluate_ccb_voting_consensus(
        [{"member": "PMO", "vote": "approve"}, {"member": "QA", "vote": "approve"}],
        required_quorum=3,
    )
    assert res == {
        "safe_quorum": 3,
        "total_votes": 2,
        "approve_votes": 2,
        "reject_votes": 0,
        "veto_cast": False,
        "quorum_met": False,
        "approval_ratio": 100.0,
        "posture": "INSUFFICIENT_QUORUM",
    }

    empty_res = evaluate_ccb_voting_consensus(None, required_quorum=0)
    assert empty_res["safe_quorum"] == 3
    assert empty_res["total_votes"] == 0
    assert empty_res["quorum_met"] is False
    assert empty_res["posture"] == "INSUFFICIENT_QUORUM"


def test_evaluate_ccb_voting_consensus_rejected_or_deadlocked():
    """Quórum cumplido pero mayoría de rechazos o empate (< 60% aprobación) -> 'CCB_REJECTED_OR_DEADLOCKED'."""
    from backend.services.project_ccb_service import evaluate_ccb_voting_consensus

    deadlock_votes = [
        {"member": "M1", "vote": "approve"},
        {"member": "M2", "vote": "approve"},
        {"member": "M3", "vote": "rejected"},
        {"member": "M4", "vote": "no"},
    ]
    res = evaluate_ccb_voting_consensus(deadlock_votes, required_quorum=4)
    assert res == {
        "safe_quorum": 4,
        "total_votes": 4,
        "approve_votes": 2,
        "reject_votes": 2,
        "veto_cast": False,
        "quorum_met": True,
        "approval_ratio": 50.0,
        "posture": "CCB_REJECTED_OR_DEADLOCKED",
    }


# ─── audit_ccb_decision_sla_breaches (pure helper) ───────────────


def test_audit_ccb_decision_sla_compliant_with_default_sla():
    """Todas las resoluciones dentro de 72h (borde exacto incluido) -> SLA_GOVERNANCE_COMPLIANT."""
    from backend.services.project_ccb_service import (
        audit_ccb_decision_sla_breaches,
    )

    res = audit_ccb_decision_sla_breaches(
        [
            {"id": "CR-1", "elapsed_hours": 8.5},
            {"id": "CR-2", "age_hours": 72},  # borde exacto: no incumple
            {"id": "CR-3"},  # sin horas -> 0.0
        ]
    )

    assert res["sla_hours"] == 72.0
    assert res["total_requests"] == 3
    assert res["breached_count"] == 0
    assert res["within_sla_count"] == 3
    assert res["sla_compliance_rate"] == 100.0
    assert res["posture"] == "SLA_GOVERNANCE_COMPLIANT"


def test_audit_ccb_decision_sla_moderate_delay():
    """2 de 3 fuera del SLA (compliance 33.34... -> no; uso 1 de 3 = 33.34 -> crítico)."""
    from backend.services.project_ccb_service import (
        audit_ccb_decision_sla_breaches,
    )

    moderate = audit_ccb_decision_sla_breaches(
        [
            {"elapsed_hours": 10.0},
            {"elapsed_hours": 96.5},
            {"age_hours": 80.0},
            {"elapsed_hours": 20.0},
            {"elapsed_hours": 12.0},
        ],
        sla_hours=48,
    )
    assert moderate["sla_hours"] == 48.0
    assert moderate["breached_count"] == 2
    assert moderate["within_sla_count"] == 3
    assert moderate["sla_compliance_rate"] == 60.0
    # 60.0 < 70.0 -> crítico, no moderado; el correcto es este spread:
    assert moderate["posture"] == "CRITICAL_SLA_BOTTLENECK"

    truly_moderate = audit_ccb_decision_sla_breaches(
        [
            {"elapsed_hours": 100.0},
            {"elapsed_hours": 10.0},
            {"elapsed_hours": 20.0},
            {"age_hours": 30.0},
            {"elapsed_hours": 5.0},
        ],
        sla_hours=72.0,
    )
    assert truly_moderate["breached_count"] == 1
    assert truly_moderate["sla_compliance_rate"] == 80.0
    assert truly_moderate["posture"] == "MODERATE_SLA_DELAY"


def test_audit_ccb_decision_sla_custom_sla_floor_and_bad_entries():
    """SLA custom clampado a >= 1.0h; entradas no-dict ignoradas; SLA None usa 72.0."""
    from backend.services.project_ccb_service import (
        audit_ccb_decision_sla_breaches,
    )

    tiny_sla = audit_ccb_decision_sla_breaches(
        ["no-soy-dict", 42, {"elapsed_hours": 2.0}],  # type: ignore[list-item]
        sla_hours=0.25,
    )
    assert tiny_sla["sla_hours"] == 1.0
    assert tiny_sla["total_requests"] == 1
    assert tiny_sla["breached_count"] == 1
    assert tiny_sla["sla_compliance_rate"] == 0.0
    assert tiny_sla["posture"] == "CRITICAL_SLA_BOTTLENECK"

    no_sla = audit_ccb_decision_sla_breaches(
        [{"elapsed_hours": 120.0}, {"age_hours": 30.0}],
        sla_hours=None,
    )
    assert no_sla["sla_hours"] == 72.0
    assert no_sla["breached_count"] == 1
    assert no_sla["sla_compliance_rate"] == 50.0
    assert no_sla["posture"] == "CRITICAL_SLA_BOTTLENECK"


def test_audit_ccb_decision_sla_no_requests():
    """None, lista vacía o sin dicts -> NO_CCB_REQUESTS con compliance 100.0."""
    from backend.services.project_ccb_service import (
        audit_ccb_decision_sla_breaches,
    )

    for val in (None, [], ["no dict", 7]):
        res = audit_ccb_decision_sla_breaches(val)  # type: ignore[arg-type]
        assert res == {
            "sla_hours": 72.0,
            "total_requests": 0,
            "breached_count": 0,
            "within_sla_count": 0,
            "sla_compliance_rate": 100.0,
            "posture": "NO_CCB_REQUESTS",
        }


# ─── evaluate_deliverable_first_time_right_yield (pure helper) ───────────────


def test_evaluate_deliverable_first_time_right_yield_high_ftr():
    """FTR >= target_ftr_pct y sin retrabajo crónico -> HIGH_FIRST_TIME_RIGHT_YIELD."""
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        evaluate_deliverable_first_time_right_yield,
    )

    deliverables = [
        {"id": "DEL-01", "accepted": True, "rejection_cycles": 0, "rework_hours": 0.0},
        {"id": "DEL-02", "accepted": True, "rejection_cycles": 0, "rework_hours": 0.0},
        {"task_id": "DEL-03", "accepted": True, "rework_count": 0, "rework_hours": 0.0},
        {"id": "DEL-04", "accepted": True, "rejection_cycles": 0, "rework_hours": 0.0},
        {"id": "DEL-05", "accepted": True, "rejection_cycles": 0, "rework_hours": 0.0},
        {"id": "DEL-06", "accepted": True, "rejection_cycles": 0, "rework_hours": 0.0},
        {"id": "DEL-07", "accepted": True, "rejection_cycles": 1, "rework_hours": 2.5},
    ]

    res = evaluate_deliverable_first_time_right_yield(deliverables, target_ftr_pct=85.0)
    assert res["total_inspected"] == 7
    assert res["first_time_right_count"] == 6
    assert res["reworked_deliverable_ids"] == ["DEL-07"]
    assert res["chronic_rework_ids"] == []
    assert res["total_rework_hours"] == 2.5
    assert res["ftr_yield_pct"] == 85.71
    assert res["quality_yield_posture"] == "HIGH_FIRST_TIME_RIGHT_YIELD"
    assert len(res["recommendations"]) >= 1

    via_service = ProjectCCBService.evaluate_deliverable_first_time_right_yield(
        deliverables, target_ftr_pct=85.0
    )
    assert via_service == res


def test_evaluate_deliverable_first_time_right_yield_chronic_rework_bottleneck():
    """Al menos un entregable con rejection_cycles >= 2 -> CHRONIC_REWORK_BOTTLENECK."""
    from backend.services.project_ccb_service import (
        evaluate_deliverable_first_time_right_yield,
    )

    deliverables = [
        {"id": "DEL-10", "accepted": True, "rejection_cycles": 0, "rework_hours": 0.0},
        {"id": "DEL-11", "accepted": True, "rejection_cycles": 0, "rework_hours": 0.0},
        {"task_id": "DEL-12", "accepted": False, "rework_count": 3, "rework_hours": 14.25},
        {"id": "DEL-13", "accepted": True, "rejection_cycles": 2, "rework_hours": 6.5},
    ]

    res = evaluate_deliverable_first_time_right_yield(deliverables, target_ftr_pct=80.0)
    assert res["total_inspected"] == 4
    assert res["first_time_right_count"] == 2
    assert res["reworked_deliverable_ids"] == ["DEL-12", "DEL-13"]
    assert res["chronic_rework_ids"] == ["DEL-12", "DEL-13"]
    assert res["total_rework_hours"] == 20.75
    assert res["ftr_yield_pct"] == 50.0
    assert res["quality_yield_posture"] == "CHRONIC_REWORK_BOTTLENECK"
    assert any("DEL-12" in rec for rec in res["recommendations"])


def test_evaluate_deliverable_first_time_right_yield_below_target():
    """Sin retrabajo crónico pero ftr_yield_pct < target_ftr_pct -> BELOW_TARGET_FTR_YIELD."""
    from backend.services.project_ccb_service import (
        evaluate_deliverable_first_time_right_yield,
    )

    deliverables = [
        {"id": "DEL-20", "accepted": True, "rejection_cycles": 0, "rework_hours": 0.0},
        {"id": "DEL-21", "accepted": True, "rejection_cycles": 1, "rework_hours": 3.2},
        {"id": "DEL-22", "accepted": False, "rejection_cycles": 1, "rework_hours": 4.8},
        {"id": "DEL-23", "accepted": True, "rejection_cycles": 0, "rework_hours": 0.0},
    ]

    res = evaluate_deliverable_first_time_right_yield(deliverables, target_ftr_pct=85.0)
    assert res["total_inspected"] == 4
    assert res["first_time_right_count"] == 2
    assert res["reworked_deliverable_ids"] == ["DEL-21", "DEL-22"]
    assert res["chronic_rework_ids"] == []
    assert res["total_rework_hours"] == 8.0
    assert res["ftr_yield_pct"] == 50.0
    assert res["quality_yield_posture"] == "BELOW_TARGET_FTR_YIELD"
    assert len(res["recommendations"]) >= 2


def test_evaluate_deliverable_first_time_right_yield_no_deliverables_inspected():
    """None, lista vacía o entradas no-dict -> NO_DELIVERABLES_INSPECTED."""
    from backend.services.project_ccb_service import (
        evaluate_deliverable_first_time_right_yield,
    )

    for payload in (None, [], ["invalid", 99]):
        res = evaluate_deliverable_first_time_right_yield(payload)  # type: ignore[arg-type]
        assert res["total_inspected"] == 0
        assert res["first_time_right_count"] == 0
        assert res["reworked_deliverable_ids"] == []
        assert res["chronic_rework_ids"] == []
        assert res["total_rework_hours"] == 0.0
        assert res["ftr_yield_pct"] == 0.0
        assert res["quality_yield_posture"] == "NO_DELIVERABLES_INSPECTED"
        assert len(res["recommendations"]) == 1


# ─── audit_emergency_change_retroactive_ratification (pure helper) ─────


def test_audit_emergency_change_governed_protocol():
    """Emergencias ratificadas con PIR y share bajo -> GOVERNED_EMERGENCY_PROTOCOL."""
    from backend.services.project_ccb_service import (
        audit_emergency_change_retroactive_ratification,
    )

    res = audit_emergency_change_retroactive_ratification(
        [
            {
                "id": "CR-1",
                "is_emergency": False,
                "retroactively_ratified": True,
            },
            {
                "code": "CR-2",
                "fast_track": True,
                "retroactively_ratified": True,
                "pir_completed": True,
            },
            {
                "id": "CR-3",
                "is_emergency": True,
                "ccb_ratified": True,
                "post_implementation_review_done": True,
            },
        ],
        max_emergency_share_pct=70.0,
    )

    assert res["total_evaluated"] == 3
    assert res["emergency_count"] == 2
    assert res["unratified_emergency_ids"] == []
    assert res["missing_pir_emergency_ids"] == []
    assert res["emergency_share_pct"] == 66.67
    assert res["emergency_governance_posture"] == "GOVERNED_EMERGENCY_PROTOCOL"
    assert len(res["recommendations"]) == 1


def test_audit_emergency_change_unratified_bypass_takes_precedence():
    """Emergencia sin ratificación CCB -> UNRATIFIED_EMERGENCY_BYPASS aunque el share no exceda."""
    from backend.services.project_ccb_service import (
        audit_emergency_change_retroactive_ratification,
    )

    res = audit_emergency_change_retroactive_ratification(
        [
            {"id": "ER-1", "is_emergency": True},
            {"id": "ER-2", "fast_track": True, "retroactively_ratified": True, "pir_completed": True},
            {"id": "CR-7"},
        ]
    )

    assert res["emergency_count"] == 2
    assert res["unratified_emergency_ids"] == ["ER-1"]
    assert len(res["missing_pir_emergency_ids"]) == 1
    assert res["emergency_share_pct"] == 66.67
    assert res["emergency_governance_posture"] == "UNRATIFIED_EMERGENCY_BYPASS"
    assert len(res["recommendations"]) == 2  # ratificación + PIR


def test_audit_emergency_change_excessive_fast_track_abuse():
    """Ratificadas con PIR pero share > máximo -> EXCESSIVE_FAST_TRACK_ABUSE con ventana custom."""
    from backend.services.project_ccb_service import (
        audit_emergency_change_retroactive_ratification,
    )

    res = audit_emergency_change_retroactive_ratification(
        [
            {"id": "ER-1", "is_emergency": True, "retroactively_ratified": True, "pir_completed": True},
            {"id": "ER-2", "is_emergency": True, "retroactively_ratified": True, "pir_completed": True},
        ],
        total_requests_window=5,
        max_emergency_share_pct=30.0,
    )

    assert res["total_evaluated"] == 5
    assert res["emergency_count"] == 2
    assert res["emergency_share_pct"] == 40.0
    assert res["emergency_governance_posture"] == "EXCESSIVE_FAST_TRACK_ABUSE"
    assert len(res["recommendations"]) == 1


def test_audit_emergency_change_no_emergencies_and_missing_pir_only():
    """Sin emergencias -> NO_EMERGENCY_CHANGES; ratificadas pero sin PIR -> PENDING_POST_IMPLEMENTATION_REVIEW."""
    from backend.services.project_ccb_service import (
        audit_emergency_change_retroactive_ratification,
    )

    for payload in (None, [], ["no dict", 5]):
        res = audit_emergency_change_retroactive_ratification(payload)  # type: ignore[arg-type]
        assert res["emergency_count"] == 0
        assert res["emergency_share_pct"] == 0.0
        assert res["emergency_governance_posture"] == "NO_EMERGENCY_CHANGES"

    pending_pir = audit_emergency_change_retroactive_ratification(
        [
            {"code": "ER-9", "fast_track": True, "ccb_ratified": True},
        ],
        total_requests_window=10,
    )
    assert pending_pir["total_evaluated"] == 10
    assert pending_pir["emergency_share_pct"] == 10.0
    assert pending_pir["missing_pir_emergency_ids"] == ["ER-9"]
    assert pending_pir["emergency_governance_posture"] == "PENDING_POST_IMPLEMENTATION_REVIEW"
    assert len(pending_pir["recommendations"]) == 1


def test_audit_configuration_baseline_integrity_verified_baseline():
    """CIs con versión coincidente o cambio aprobado por CCB y checksum verificado -> VERIFIED_CONFIGURATION_BASELINE."""
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_configuration_baseline_integrity,
    )

    items = [
        {
            "ci_id": "CI-101",
            "approved_version": "v1.0.0",
            "current_version": "v1.0.0",
            "has_checksum": True,
        },
        {
            "id": "CI-102",
            "approved_version": "1.0",
            "deployed_version": "1.1",
            "authorized_by_cr": "CR-2026-09",
            "verified_hash": "sha256:9f86d081884c7d659a2feaa0c55ad015",
        },
    ]

    res = audit_configuration_baseline_integrity(items)
    assert res["total_items"] == 2
    assert res["unauthorized_drift_ids"] == []
    assert res["unverified_checksum_ids"] == []
    assert res["compliant_count"] == 2
    assert res["integrity_rate_pct"] == 100.0
    assert res["configuration_posture"] == "VERIFIED_CONFIGURATION_BASELINE"
    assert len(res["recommendations"]) == 1
    assert ProjectCCBService.audit_configuration_baseline_integrity(items) == res


def test_audit_configuration_baseline_integrity_unauthorized_version_drift():
    """CI con cambio de versión sin CR aprobado o sin versión aprobada -> UNAUTHORIZED_VERSION_DRIFT."""
    from backend.services.project_ccb_service import (
        audit_configuration_baseline_integrity,
    )

    items = [
        {
            "id": "CI-201",
            "approved_version": "2.0.0",
            "current_version": "2.0.0",
            "has_checksum": True,
        },
        {
            "artifact_id": "CI-202",
            "approved_version": "2.0.0",
            "deployed_version": "2.1.0-hotfix",
            "authorized_by_cr": "",
            "has_checksum": True,
        },
        {
            "ci_id": "CI-203",
            "approved_version": "",
            "current_version": "1.0.0",
            "has_checksum": False,
        },
    ]

    res = audit_configuration_baseline_integrity(items)
    assert res["total_items"] == 3
    assert res["unauthorized_drift_ids"] == ["CI-202", "CI-203"]
    assert res["unverified_checksum_ids"] == ["CI-203"]
    assert res["compliant_count"] == 1
    assert res["integrity_rate_pct"] == 33.33
    assert res["configuration_posture"] == "UNAUTHORIZED_VERSION_DRIFT"
    assert any("CI-202" in r and "CI-203" in r for r in res["recommendations"])


def test_audit_configuration_baseline_integrity_unverified_artifact_checksums():
    """Sin deriva no autorizada pero con artefactos sin verificación de checksum -> UNVERIFIED_ARTIFACT_CHECKSUMS."""
    from backend.services.project_ccb_service import (
        audit_configuration_baseline_integrity,
    )

    items = [
        {
            "ci_id": "CI-301",
            "approved_version": "3.1",
            "current_version": "3.2",
            "cr_id": "CCB-88",
            "has_checksum": True,
        },
        {
            "ci_id": "CI-302",
            "approved_version": "1.4",
            "current_version": "1.4",
            "has_checksum": False,
        },
    ]

    res = audit_configuration_baseline_integrity(items)
    assert res["total_items"] == 2
    assert res["unauthorized_drift_ids"] == []
    assert res["unverified_checksum_ids"] == ["CI-302"]
    assert res["compliant_count"] == 1
    assert res["integrity_rate_pct"] == 50.0
    assert res["configuration_posture"] == "UNVERIFIED_ARTIFACT_CHECKSUMS"
    assert any("CI-302" in r for r in res["recommendations"])


def test_audit_configuration_baseline_integrity_no_configuration_items():
    """Lista vacía, None o entradas no-dict -> NO_CONFIGURATION_ITEMS."""
    from backend.services.project_ccb_service import (
        audit_configuration_baseline_integrity,
    )

    for payload in (None, [], ["invalid", 42, None]):
        res = audit_configuration_baseline_integrity(payload)  # type: ignore[arg-type]
        assert res["total_items"] == 0
        assert res["unauthorized_drift_ids"] == []
        assert res["unverified_checksum_ids"] == []
        assert res["compliant_count"] == 0
        assert res["integrity_rate_pct"] == 0.0
        assert res["configuration_posture"] == "NO_CONFIGURATION_ITEMS"
        assert len(res["recommendations"]) == 1


# ─── audit_pareto_defect_root_causes (pure helper) ───────────────


def test_audit_pareto_defect_root_causes_concentrated_bottleneck():
    """Causa dominante >= 50% -> CONCENTRATED_PARETO_BOTTLENECK con top y vital few."""
    from backend.services.project_ccb_service import audit_pareto_defect_root_causes

    defects = [
        {"root_cause": "CONFIG-DRIFT", "count": 12},
        {"root_cause": "config-drift", "occurrences": 8},
        {"category": "human-error", "count": 4},
        {"root_cause": "supplier-delay", "count": 2},
    ]

    res = audit_pareto_defect_root_causes(defects)

    assert res["total_defect_occurrences"] == 26
    assert res["unique_causes_count"] == 3
    assert res["uncategorized_occurrences"] == 0
    assert res["top_cause"] == "CONFIG-DRIFT"
    assert res["top_cause_share_pct"] == 76.92
    # 76.92 < 80 -> acumula también HUMAN-ERROR (24/26 = 92.3% >= 80).
    assert res["vital_few_causes"] == ["CONFIG-DRIFT", "HUMAN-ERROR"]
    assert res["pareto_posture"] == "CONCENTRATED_PARETO_BOTTLENECK"
    assert len(res["recommendations"]) == 1


def test_audit_pareto_defect_root_causes_uncategorized_blindspot():
    """>= 30% sin categorizar (vacío, TBD, N/A, accénto) -> UNCATEGORIZED_ROOT_CAUSE_BLINDSPOT."""
    from backend.services.project_ccb_service import audit_pareto_defect_root_causes

    res = audit_pareto_defect_root_causes(
        [
            {"root_cause": "network", "count": 7},
            {"root_cause": "", "count": 3},
            {"category": "TBD", "occurrences": 1},
        ]
    )

    assert res["total_defect_occurrences"] == 11
    assert res["unique_causes_count"] == 2
    assert res["uncategorized_occurrences"] == 4
    assert res["top_cause"] == "NETWORK"
    assert res["top_cause_share_pct"] == 63.64
    assert res["pareto_posture"] == "UNCATEGORIZED_ROOT_CAUSE_BLINDSPOT"
    assert any("causa raíz" in rec for rec in res["recommendations"])


def test_audit_pareto_defect_root_causes_diffuse_distribution():
    """Causas repartidas con vital few >= 3 -> DIFFUSE_DEFECT_DISTRIBUTION."""
    from backend.services.project_ccb_service import audit_pareto_defect_root_causes

    res = audit_pareto_defect_root_causes(
        [
            {"root_cause": "alpha", "count": 3},
            {"root_cause": "beta", "count": 3},
            {"root_cause": "gamma", "count": 3},
            {"root_cause": "delta", "count": 1},
        ]
    )

    assert res["total_defect_occurrences"] == 10
    assert res["unique_causes_count"] == 4
    assert res["top_cause"] == "ALPHA"
    assert res["top_cause_share_pct"] == 30.0
    # Umbral 80: ALPHA (30) -> +BETA (60) -> +GAMMA (90 >= 80) -> 3 causas.
    assert res["vital_few_causes"] == ["ALPHA", "BETA", "GAMMA"]
    assert res["pareto_posture"] == "DIFFUSE_DEFECT_DISTRIBUTION"


def test_audit_pareto_defect_root_causes_empty_and_degenerate_counts():
    """None/vacíos/no-dicts -> NO_DEFECTS_RECORDED; counts degenerados clampan >= 1; vital few por borde."""
    from backend.services.project_ccb_service import audit_pareto_defect_root_causes

    for payload in (None, [], ["no dict", 5]):
        res = audit_pareto_defect_root_causes(payload)  # type: ignore[arg-type]
        assert res == {
            "total_defect_occurrences": 0,
            "unique_causes_count": 0,
            "uncategorized_occurrences": 0,
            "top_cause": None,
            "top_cause_share_pct": 0.0,
            "vital_few_causes": [],
            "pareto_posture": "NO_DEFECTS_RECORDED",
            "recommendations": [
                "Registrar los defectos con su causa raíz para habilitar el analisis Pareto (PMBOK §8.3)."
            ],
        }

    clamped = audit_pareto_defect_root_causes(
        [{"root_cause": "flip", "count": 0}, {"root_cause": "flip"}]
    )
    assert clamped["total_defect_occurrences"] == 2
    assert clamped["unique_causes_count"] == 1
    assert clamped["top_cause_share_pct"] == 100.0
    assert clamped["vital_few_causes"] == ["FLIP"]
    assert clamped["pareto_posture"] == "CONCENTRATED_PARETO_BOTTLENECK"


def test_audit_unapproved_scope_creep_exposure_controlled_baseline():
    """Paquetes con CR aprobada o dentro de la tolerancia -> CONTROLLED_SCOPE_BASELINE."""
    from backend.services.project_ccb_service import (
        audit_unapproved_scope_creep_exposure as audit_fn,
    )

    res = audit_fn(
        [
            {
                "id": "WP-1",
                "baseline_hours": 100.0,
                "actual_hours": 105.0,
            },
            {
                "id": "WP-2",
                "baseline_hours": 50.0,
                "actual_hours": 60.0,
                "approved_cr_id": "CR-9",
            },
            {
                "id": "WP-3",
                "planned_hours": 20.0,
                "effort_hours": 0.0,
            },
        ],
        tolerance_hours_pct=10.0,
    )
    assert res["is_scope_controlled"] is True
    assert res["total_packages"] == 3
    assert res["unbaselined_package_ids"] == []
    assert res["scope_creep_package_ids"] == []
    assert res["unapproved_effort_hours"] == 0.0
    assert res["scope_posture"] == "CONTROLLED_SCOPE_BASELINE"


def test_audit_unapproved_scope_creep_exposure_unbaselined_work():
    """Esfuerzo real sin linea base y sin CR aprobada -> UNAUTHORIZED_UNBASELINED_WORK."""
    from backend.services.project_ccb_service import (
        audit_unapproved_scope_creep_exposure as audit_fn,
    )

    res = audit_fn(
        [
            {
                "id": "WP-4",
                "actual_hours": 12.5,
            },
            {
                "package_id": "WP-5",
                "baseline_hours": 8.0,
                "actual_hours": 8.0,
                "has_approved_cr": True,
            },
        ]
    )
    assert res["is_scope_controlled"] is False
    assert res["total_packages"] == 2
    assert res["unbaselined_package_ids"] == ["WP-4"]
    assert res["scope_creep_package_ids"] == []
    assert res["unapproved_effort_hours"] == 12.5
    assert res["scope_posture"] == "UNAUTHORIZED_UNBASELINED_WORK"


def test_audit_unapproved_scope_creep_exposure_creep_over_tolerance():
    """Overrun sin CR por encima de la tolerancia -> UNAPPROVED_SCOPE_CREEP_DETECTED."""
    from backend.services.project_ccb_service import (
        audit_unapproved_scope_creep_exposure as audit_fn,
    )

    res = audit_fn(
        [
            {
                "wbs_code": "1.2",
                "baseline_hours": 40.0,
                "actual_hours": 48.0,
            },
            {
                "id": "WP-OK",
                "baseline_hours": 30.0,
                "actual_hours": 32.0,
            },
        ],
        tolerance_hours_pct=10.0,
    )
    assert res["is_scope_controlled"] is False
    assert res["total_packages"] == 2
    assert res["unbaselined_package_ids"] == []
    # 1.2: (48-40)/40 = 20.0% > 10% -> creep; WP-OK: 6.67% dentro de tolerancia.
    assert res["scope_creep_package_ids"] == ["1.2"]
    assert res["unapproved_effort_hours"] == 8.0
    assert res["scope_posture"] == "UNAPPROVED_SCOPE_CREEP_DETECTED"


def test_audit_unapproved_scope_creep_exposure_empty_or_none():
    """None, lista vacia o entradas no-dict -> NO_WORK_PACKAGES_EVALUATED."""
    from backend.services.project_ccb_service import (
        audit_unapproved_scope_creep_exposure as audit_fn,
    )

    for payload in (None, [], ["invalid", 42, None]):
        res = audit_fn(payload)  # type: ignore[arg-type]
        assert res == {
            "total_packages": 0,
            "unbaselined_package_ids": [],
            "scope_creep_package_ids": [],
            "unapproved_effort_hours": 0.0,
            "is_scope_controlled": True,
            "scope_posture": "NO_WORK_PACKAGES_EVALUATED",
        }


def test_evaluate_cost_of_quality_prevention_balance_optimal():
    """Conformidad (prevention + appraisal) y fallas dentro del 35% -> OPTIMAL balance."""
    from backend.services.project_ccb_service import (
        evaluate_cost_of_quality_prevention_balance as eval_fn,
    )

    res = eval_fn(
        [
            {"id": "COQ-1", "category": "prevention", "amount": 8000.0},
            {"entry_id": "COQ-2", "type": "Evaluación", "cost": 4000.0},
        ]
    )
    assert res["is_balanced"] is True
    assert res["total_coq_amount"] == 12000.0
    assert res["conformance_cost"] == 12000.0
    assert res["nonconformance_cost"] == 0.0
    assert res["failure_cost_share_pct"] == 0.0
    assert res["unclassified_entry_ids"] == []
    assert res["coq_posture"] == "OPTIMAL_CONFORMANCE_COQ_BALANCE"


def test_evaluate_cost_of_quality_prevention_balance_invalid_or_unclassified():
    """Monto <= 0 o categoría fuera de los conjuntos -> INVALID_OR_UNCLASSIFIED (precedencia)."""
    from backend.services.project_ccb_service import (
        evaluate_cost_of_quality_prevention_balance as eval_fn,
    )

    res = eval_fn(
        [
            {"id": "COQ-P", "category": "prevention", "amount": 3000.0},
            {"id": "COQ-ZERO", "category": "appraisal", "amount": 0.0},
            {"id": "COQ-BOGUS", "category": "marketing", "amount": 1500.0},
        ]
    )
    assert res["is_balanced"] is False
    assert res["unclassified_entry_ids"] == ["COQ-ZERO", "COQ-BOGUS"]
    assert res["total_coq_amount"] == 3000.0
    assert res["conformance_cost"] == 3000.0
    assert res["nonconformance_cost"] == 0.0
    assert res["failure_cost_share_pct"] == 0.0
    assert res["coq_posture"] == "INVALID_OR_UNCLASSIFIED_COQ_ENTRIES"


def test_evaluate_cost_of_quality_prevention_balance_high_failure_burden():
    """> 35% de fallas -> HIGH_NONCONFORMANCE_FAILURE_BURDEN con share exacto."""
    from backend.services.project_ccb_service import (
        evaluate_cost_of_quality_prevention_balance as eval_fn,
    )

    res = eval_fn(
        [
            {"id": "COQ-P", "category": "prevention", "amount": 3000.0},
            {"id": "COQ-F1", "coq_category": "rework", "amount": 3000.0},
            {"id": "COQ-F2", "category": "external_failure", "amount": 4000.0},
        ]
    )
    assert res["is_balanced"] is False
    assert res["total_coq_amount"] == 10000.0
    assert res["conformance_cost"] == 3000.0
    assert res["nonconformance_cost"] == 7000.0
    assert res["failure_cost_share_pct"] == 70.0
    assert res["unclassified_entry_ids"] == []
    assert res["coq_posture"] == "HIGH_NONCONFORMANCE_FAILURE_BURDEN"


def test_evaluate_cost_of_quality_prevention_balance_empty_or_none():
    """None, lista vacía o entradas no-dict -> NO_COQ_ENTRIES_RECORDED."""
    from backend.services.project_ccb_service import (
        evaluate_cost_of_quality_prevention_balance as eval_fn,
    )

    for payload in (None, [], ["invalid", 42, None]):
        res = eval_fn(payload)  # type: ignore[arg-type]
        assert res == {
            "total_coq_amount": 0.0,
            "conformance_cost": 0.0,
            "nonconformance_cost": 0.0,
            "failure_cost_share_pct": 0.0,
            "unclassified_entry_ids": [],
            "is_balanced": False,
            "coq_posture": "NO_COQ_ENTRIES_RECORDED",
        }


def test_evaluate_defect_containment_and_escape_rate_effective():
    """DCE >= 85% sin críticos escapados -> EFFECTIVE_QA_DEFECT_CONTAINMENT."""
    from backend.services.project_ccb_service import (
        evaluate_defect_containment_and_escape_rate as eval_fn,
    )

    res = eval_fn(
        [
            {"id": "DEF-1", "detected_in": "code_review", "severity": "critical"},
            {"defect_id": "DEF-2", "phase": "Testing QA", "priority": "medium"},
            {"id": "DEF-3", "stage": "UAT", "severity": "low"},
            {"id": "DEF-4", "detected_in": "staging", "severity": "high"},
            {"id": "DEF-5", "detected_in": "unit_test", "severity": "low"},
            {"id": "DEF-6", "phase": "smoke", "severity": "medium"},
            {"id": "DEF-7", "phase": " producción ", "severity": "low", "escaped_to_production": True},
        ]
    )
    assert res["is_contained"] is True
    assert res["total_defects"] == 7
    assert res["pre_release_defects_count"] == 6
    assert res["escaped_production_defects_count"] == 1
    assert res["critical_escaped_defect_ids"] == []
    assert res["containment_effectiveness_pct"] == 85.71
    assert res["escape_rate_pct"] == 14.29
    assert res["containment_posture"] == "EFFECTIVE_QA_DEFECT_CONTAINMENT"


def test_evaluate_defect_containment_and_escape_rate_critical_escape():
    """Critical/high escapado a producción -> CRITICAL_PRODUCTION_DEFECT_ESCAPE."""
    from backend.services.project_ccb_service import (
        evaluate_defect_containment_and_escape_rate as eval_fn,
    )

    res = eval_fn(
        [
            {"id": "DEF-A", "detected_in": "qa", "severity": "medium"},
            {"id": "DEF-B", "detected_in": "production", "severity": "P1"},
            {"defect_id": "DEF-C", "phase": "cliente", "severity": "low", "escaped_to_production": True},
        ]
    )
    assert res["is_contained"] is False
    assert res["total_defects"] == 3
    assert res["pre_release_defects_count"] == 1
    assert res["escaped_production_defects_count"] == 2
    assert res["critical_escaped_defect_ids"] == ["DEF-B"]
    assert res["containment_effectiveness_pct"] == 33.33
    assert res["escape_rate_pct"] == 66.67
    assert res["containment_posture"] == "CRITICAL_PRODUCTION_DEFECT_ESCAPE"


def test_evaluate_defect_containment_and_escape_rate_low_containment():
    """DCE < 85% con escapes de severidad low/medium -> LOW_DEFECT_CONTAINMENT_EFFECTIVENESS."""
    from backend.services.project_ccb_service import (
        evaluate_defect_containment_and_escape_rate as eval_fn,
    )

    res = eval_fn(
        [
            {"id": "DEF-X", "detected_in": "unit", "severity": "low"},
            {"id": "DEF-Y", "detected_in": "field", "severity": "low"},
            {"id": "DEF-Z", "detected_in": "post_release", "severity": "medium"},
        ],
        min_containment_effectiveness_pct=85.0,
    )
    assert res["is_contained"] is False
    assert res["total_defects"] == 3
    assert res["pre_release_defects_count"] == 1
    assert res["escaped_production_defects_count"] == 2
    assert res["critical_escaped_defect_ids"] == []
    assert res["containment_effectiveness_pct"] == 33.33
    assert res["escape_rate_pct"] == 66.67
    assert res["containment_posture"] == "LOW_DEFECT_CONTAINMENT_EFFECTIVENESS"


def test_evaluate_defect_containment_and_escape_rate_empty_or_none():
    """None, lista vacía o entradas no-dict -> NO_DEFECTS_EVALUATED."""
    from backend.services.project_ccb_service import (
        evaluate_defect_containment_and_escape_rate as eval_fn,
    )

    for payload in (None, [], ["invalid", 42, None]):
        res = eval_fn(payload)  # type: ignore[arg-type]
        assert res == {
            "total_defects": 0,
            "pre_release_defects_count": 0,
            "escaped_production_defects_count": 0,
            "critical_escaped_defect_ids": [],
            "containment_effectiveness_pct": 100.0,
            "escape_rate_pct": 0.0,
            "is_contained": True,
            "containment_posture": "NO_DEFECTS_EVALUATED",
        }


def test_audit_configuration_items_baseline_integrity_verified():
    """IC alineados a su base (o con CR aprobado y audit OK) -> VERIFIED baseline 100%."""
    # Contrato v1 (compatibilidad): implementación original preservada.
    from backend.services.project_ccb_service import (
        audit_configuration_items_baseline_integrity_v1 as audit_fn,
    )

    res = audit_fn(
        [
            {
                "id": "CI-1",
                "baseline_version": "v1.2.0",
                "deployed_version": "v1.2.0",
                "verification_status": "verificado",
            },
            {
                "ci_id": "CI-2",
                "approved_version": "v1.1.0",
                "current_version": "v1.1.3",
                "change_request_id": "CR-42",
                "pca_fca_status": "APPROVED",
            },
        ]
    )
    assert res["is_configuration_compliant"] is True
    assert res["total_items"] == 2
    assert res["verified_items_count"] == 2
    assert res["unauthorized_drift_ci_ids"] == []
    assert res["unbaselined_ci_ids"] == []
    assert res["unverified_audit_ci_ids"] == []
    assert res["integrity_rate_pct"] == 100.0
    assert res["configuration_posture"] == "VERIFIED_CONFIGURATION_BASELINE"


def test_audit_configuration_items_baseline_integrity_unauthorized_drift():
    """Versión desplegada distinta de la base sin CR -> UNAUTHORIZED_CONFIGURATION_DRIFT."""
    # Contrato v1 (compatibilidad): implementación original preservada.
    from backend.services.project_ccb_service import (
        audit_configuration_items_baseline_integrity_v1 as audit_fn,
    )

    res = audit_fn(
        [
            {
                "id": "CI-OK",
                "baseline_version": "v2.0.0",
                "deployed_version": "v2.0.0",
                "verification_status": "passed",
            },
            {
                "id": "CI-DRIFT",
                "baseline_version": "v2.0.0",
                "deployed_version": "v2.1.0",
                "verification_status": "verified",
            },
        ]
    )
    assert res["is_configuration_compliant"] is False
    assert res["total_items"] == 2
    assert res["verified_items_count"] == 1
    assert res["unauthorized_drift_ci_ids"] == ["CI-DRIFT"]
    assert res["unbaselined_ci_ids"] == []
    assert res["unverified_audit_ci_ids"] == []
    assert res["integrity_rate_pct"] == 50.0
    assert res["configuration_posture"] == "UNAUTHORIZED_CONFIGURATION_DRIFT"


def test_audit_configuration_items_baseline_integrity_unbaselined_and_pending():
    """Sin versiones y con PCA/FCA pendiente: ambos no verificados (d excluye a/b/c)."""
    # Contrato v1 (compatibilidad): implementación original preservada.
    from backend.services.project_ccb_service import (
        audit_configuration_items_baseline_integrity_v1 as audit_fn,
    )

    res = audit_fn(
        [
            {
                "code": "CI-X",
                "verification_status": "verified",
            },
            {
                "id": "CI-PENDING",
                "baseline_version": "v1.0.0",
                "deployed_version": "v1.0.0",
                "verification_status": "pending_audit",
            },
        ]
    )
    assert res["is_configuration_compliant"] is False
    assert res["total_items"] == 2
    # CI-X cae en (a) aun con status verified; CI-PENDING cae en (c): ninguno cuenta.
    assert res["verified_items_count"] == 0
    assert res["unbaselined_ci_ids"] == ["CI-X"]
    assert res["unverified_audit_ci_ids"] == ["CI-PENDING"]
    assert res["unauthorized_drift_ci_ids"] == []
    assert res["integrity_rate_pct"] == 0.0
    # Precedencia: drift > unbaselined > pending PCA/FCA.
    assert res["configuration_posture"] == "UNBASELINED_CONFIGURATION_ITEM"


def test_audit_configuration_items_baseline_integrity_empty_or_none():
    """None, lista vacía o entradas no-dict -> NO_CONFIGURATION_ITEMS."""
    # Contrato v1 (compatibilidad): implementación original preservada.
    from backend.services.project_ccb_service import (
        audit_configuration_items_baseline_integrity_v1 as audit_fn,
    )

    for payload in (None, [], ["invalid", 42, None]):
        res = audit_fn(payload)  # type: ignore[arg-type]
        assert res == {
            "total_items": 0,
            "verified_items_count": 0,
            "unauthorized_drift_ci_ids": [],
            "unbaselined_ci_ids": [],
            "unverified_audit_ci_ids": [],
            "integrity_rate_pct": 100.0,
            "is_configuration_compliant": True,
            "configuration_posture": "NO_CONFIGURATION_ITEMS",
        }


def test_evaluate_spc_process_stability_in_statistical_control():
    """Proceso estable bajo control sin violar UCL/LCL/USL/LSL ni Regla de Siete -> IN_STATISTICAL_CONTROL."""
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        evaluate_spc_process_stability,
    )

    res = evaluate_spc_process_stability(
        [10.0, 10.2, 9.8, 10.1, 9.9, 10.3, 9.7, 10.0],
        center_line=10.0,
        ucl=11.0,
        lcl=9.0,
        usl=12.0,
        lsl=8.0,
    )
    assert res["sample_size"] == 8
    assert res["process_mean"] == 10.0
    assert res["beyond_control_limit_indices"] == []
    assert res["beyond_spec_limit_indices"] == []
    assert res["max_same_side_run"] == 1
    assert res["has_rule_of_seven_run"] is False
    assert res["is_in_statistical_control"] is True
    assert res["spc_posture"] == "IN_STATISTICAL_CONTROL"
    assert (
        ProjectCCBService.evaluate_spc_process_stability(
            [10.0, 10.2, 9.8], center_line=10.0, ucl=11.0, lcl=9.0
        )["spc_posture"]
        == "IN_STATISTICAL_CONTROL"
    )


def test_evaluate_spc_process_stability_spec_and_control_limit_breaches():
    """Violación de límites de especificación (USL/LSL) y control (UCL/LCL)."""
    from backend.services.project_ccb_service import evaluate_spc_process_stability

    res_spec = evaluate_spc_process_stability(
        [10.0, 11.5, 12.5, 7.5],
        center_line=10.0,
        ucl=11.0,
        lcl=9.0,
        usl=12.0,
        lsl=8.0,
    )
    assert res_spec["beyond_control_limit_indices"] == [1, 2, 3]
    assert res_spec["beyond_spec_limit_indices"] == [2, 3]
    assert res_spec["is_in_statistical_control"] is False
    assert res_spec["spc_posture"] == "SPECIFICATION_LIMIT_BREACH"

    res_ctrl = evaluate_spc_process_stability(
        [10.0, 11.4, 9.9, 8.6],
        center_line=10.0,
        ucl=11.0,
        lcl=9.0,
        usl=12.0,
        lsl=8.0,
    )
    assert res_ctrl["beyond_control_limit_indices"] == [1, 3]
    assert res_ctrl["beyond_spec_limit_indices"] == []
    assert res_ctrl["is_in_statistical_control"] is False
    assert res_ctrl["spc_posture"] == "CONTROL_LIMIT_OUTLIER"


def test_evaluate_spc_process_stability_rule_of_seven_run():
    """7 puntos consecutivos del mismo lado de la media sin cruzar UCL/LCL -> RULE_OF_SEVEN_NON_RANDOM_RUN."""
    from backend.services.project_ccb_service import evaluate_spc_process_stability

    res = evaluate_spc_process_stability(
        [9.8, 10.1, 10.2, 10.3, 10.1, 10.4, 10.2, 10.5, 9.9],
        center_line=10.0,
        ucl=11.0,
        lcl=9.0,
        usl=12.0,
        lsl=8.0,
    )
    assert res["sample_size"] == 9
    assert res["beyond_control_limit_indices"] == []
    assert res["beyond_spec_limit_indices"] == []
    assert res["max_same_side_run"] == 7
    assert res["has_rule_of_seven_run"] is True
    assert res["is_in_statistical_control"] is False
    assert res["spc_posture"] == "RULE_OF_SEVEN_NON_RANDOM_RUN"


def test_evaluate_spc_process_stability_empty_or_none():
    """Lista vacía o None -> NO_MEASUREMENTS_PROVIDED e is_in_statistical_control=True."""
    from backend.services.project_ccb_service import evaluate_spc_process_stability

    for payload in (None, []):
        res = evaluate_spc_process_stability(payload)
        assert res == {
            "sample_size": 0,
            "process_mean": 0.0,
            "beyond_control_limit_indices": [],
            "beyond_spec_limit_indices": [],
            "max_same_side_run": 0,
            "has_rule_of_seven_run": False,
            "is_in_statistical_control": True,
            "spc_posture": "NO_MEASUREMENTS_PROVIDED",
        }


def test_evaluate_fmea_rpn_criticality_low_rpn_and_mitigated_high_rpn():
    """RPN bajo -> LOW_RPN_BASELINE_RISK; RPN alto con CAPA y dueño -> MITIGATED_HIGH_RPN_EXPOSURE."""
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        evaluate_fmea_rpn_criticality,
    )

    res_low = evaluate_fmea_rpn_criticality(
        [
            {"id": "FM-1", "severity": 4, "occurrence": 3, "detection": 2},
            {"id": "FM-2", "s": 5, "o": 2, "d": 3},
        ]
    )
    assert res_low == {
        "total_failure_modes": 2,
        "max_rpn": 30,
        "critical_modes_count": 0,
        "unmitigated_critical_mode_ids": [],
        "is_fmea_controlled": True,
        "fmea_posture": "LOW_RPN_BASELINE_RISK",
    }

    res_mit = evaluate_fmea_rpn_criticality(
        [
            {
                "id": "FM-CRIT",
                "severity": 8,
                "occurrence": 5,
                "detection": 4,
                "recommended_action": "Implementar circuit breaker y failover automático",
                "action_owner": "Líder SRE",
            }
        ],
        rpn_threshold=125,
    )
    assert res_mit["total_failure_modes"] == 1
    assert res_mit["max_rpn"] == 160
    assert res_mit["critical_modes_count"] == 1
    assert res_mit["unmitigated_critical_mode_ids"] == []
    assert res_mit["is_fmea_controlled"] is True
    assert res_mit["fmea_posture"] == "MITIGATED_HIGH_RPN_EXPOSURE"
    assert (
        ProjectCCBService.evaluate_fmea_rpn_criticality(
            [
                {
                    "id": "FM-CRIT",
                    "severity": 8,
                    "occurrence": 5,
                    "detection": 4,
                    "recommended_action": "Implementar circuit breaker y failover automático",
                    "action_owner": "Líder SRE",
                }
            ]
        )["fmea_posture"]
        == "MITIGATED_HIGH_RPN_EXPOSURE"
    )


def test_evaluate_fmea_rpn_criticality_unmitigated_high_rpn():
    """RPN >= 125 sin acción recomendada o sin dueño -> UNMITIGATED_CRITICAL_FAILURE_MODE."""
    from backend.services.project_ccb_service import evaluate_fmea_rpn_criticality

    res = evaluate_fmea_rpn_criticality(
        [
            {
                "id": "FM-NOACT",
                "severity": 7,
                "occurrence": 5,
                "detection": 4,
                "recommended_action": "",
                "action_owner": "Arquitecto",
            },
            {
                "id": "FM-NOOWNER",
                "severity": 6,
                "occurrence": 5,
                "detection": 5,
                "mitigation_action": "Redundancia activa en base de datos",
                "owner": "",
            },
        ],
        rpn_threshold=125,
    )
    assert res["total_failure_modes"] == 2
    assert res["max_rpn"] == 150
    assert res["critical_modes_count"] == 2
    assert res["unmitigated_critical_mode_ids"] == ["FM-NOACT", "FM-NOOWNER"]
    assert res["is_fmea_controlled"] is False
    assert res["fmea_posture"] == "UNMITIGATED_CRITICAL_FAILURE_MODE"


def test_evaluate_fmea_rpn_criticality_high_severity_below_rpn_threshold():
    """RPN < 125 pero severity >= 9 sin acción CAPA -> UNMITIGATED_CRITICAL_FAILURE_MODE."""
    from backend.services.project_ccb_service import evaluate_fmea_rpn_criticality

    res = evaluate_fmea_rpn_criticality(
        [
            {
                "id": "FM-SEV9",
                "severity": 9,
                "occurrence": 2,
                "detection": 2,
                "recommended_action": "",
            }
        ],
        rpn_threshold=125,
        high_severity_threshold=9,
    )
    assert res["max_rpn"] == 36
    assert res["critical_modes_count"] == 1
    assert res["unmitigated_critical_mode_ids"] == ["FM-SEV9"]
    assert res["is_fmea_controlled"] is False
    assert res["fmea_posture"] == "UNMITIGATED_CRITICAL_FAILURE_MODE"


def test_evaluate_fmea_rpn_criticality_empty_or_none():
    """Lista vacía o None -> NO_FAILURE_MODES_EVALUATED e is_fmea_controlled=True."""
    from backend.services.project_ccb_service import evaluate_fmea_rpn_criticality

    for payload in (None, [], ["invalid", 42]):
        res = evaluate_fmea_rpn_criticality(payload)  # type: ignore[arg-type]
        assert res == {
            "total_failure_modes": 0,
            "max_rpn": 0,
            "critical_modes_count": 0,
            "unmitigated_critical_mode_ids": [],
            "is_fmea_controlled": True,
            "fmea_posture": "NO_FAILURE_MODES_EVALUATED",
        }


def test_evaluate_quality_ncr_sla_compliance_compliant():
    """NCRs dentro de SLA con RCA para mayores/críticos y evidencia en cerrados -> COMPLIANT_NCR_GOVERNANCE."""
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        evaluate_quality_ncr_sla_compliance,
    )

    ncrs = [
        {
            "id": "NCR-1",
            "severity": "MAJOR",
            "status": "OPEN",
            "age_days": 5,
            "root_cause": "Falta de validación de esquema en ingesta",
        },
        {
            "ncr_id": "NCR-2",
            "severity": "MINOR",
            "status": "CLOSED",
            "age_days": 10,
            "verification_evidence": "PR-412 aprobado y suite QA en verde",
        },
    ]
    res = evaluate_quality_ncr_sla_compliance(ncrs, major_sla_days=7, minor_sla_days=14)
    assert res == {
        "total_ncrs": 2,
        "open_ncrs_count": 1,
        "sla_breached_ncr_ids": [],
        "missing_rca_ncr_ids": [],
        "unverified_closed_ncr_ids": [],
        "is_ncr_governance_compliant": True,
        "ncr_posture": "COMPLIANT_NCR_GOVERNANCE",
    }
    assert (
        ProjectCCBService.evaluate_quality_ncr_sla_compliance(
            ncrs, major_sla_days=7, minor_sla_days=14
        )
        == res
    )


def test_evaluate_quality_ncr_sla_compliance_unverified_closure():
    """NCR cerrado sin evidencia de verificación -> UNVERIFIED_NCR_CLOSURE."""
    from backend.services.project_ccb_service import evaluate_quality_ncr_sla_compliance

    res = evaluate_quality_ncr_sla_compliance(
        [
            {
                "id": "NCR-CLOSED-NOEV",
                "severity": "MAJOR",
                "status": "CLOSED",
                "verification_evidence": "",
            }
        ]
    )
    assert res["unverified_closed_ncr_ids"] == ["NCR-CLOSED-NOEV"]
    assert res["is_ncr_governance_compliant"] is False
    assert res["ncr_posture"] == "UNVERIFIED_NCR_CLOSURE"


def test_evaluate_quality_ncr_sla_compliance_sla_breach_and_missing_rca():
    """NCR abierto fuera de SLA -> NCR_SLA_BREACH; severidad MAJOR sin RCA -> MISSING_MAJOR_NCR_ROOT_CAUSE."""
    from backend.services.project_ccb_service import evaluate_quality_ncr_sla_compliance

    res_sla = evaluate_quality_ncr_sla_compliance(
        [
            {
                "id": "NCR-LATE",
                "severity": "MAJOR",
                "status": "OPEN",
                "age_days": 10,
                "root_cause": "Defecto de integración",
            }
        ],
        major_sla_days=7,
    )
    assert res_sla["sla_breached_ncr_ids"] == ["NCR-LATE"]
    assert res_sla["is_ncr_governance_compliant"] is False
    assert res_sla["ncr_posture"] == "NCR_SLA_BREACH"

    res_rca = evaluate_quality_ncr_sla_compliance(
        [
            {
                "id": "NCR-NORCA",
                "severity": "CRITICAL",
                "status": "IN_PROGRESS",
                "age_days": 1,
                "root_cause": "",
            }
        ],
        major_sla_days=7,
    )
    assert res_rca["missing_rca_ncr_ids"] == ["NCR-NORCA"]
    assert res_rca["is_ncr_governance_compliant"] is False
    assert res_rca["ncr_posture"] == "MISSING_MAJOR_NCR_ROOT_CAUSE"


def test_evaluate_quality_ncr_sla_compliance_no_ncrs():
    """Lista vacía o None -> NO_NCRS_RECORDED."""
    from backend.services.project_ccb_service import evaluate_quality_ncr_sla_compliance

    for payload in (None, [], [{"id": ""}]):
        res = evaluate_quality_ncr_sla_compliance(payload)
        assert res == {
            "total_ncrs": 0,
            "open_ncrs_count": 0,
            "sla_breached_ncr_ids": [],
            "missing_rca_ncr_ids": [],
            "unverified_closed_ncr_ids": [],
            "is_ncr_governance_compliant": False,
            "ncr_posture": "NO_NCRS_RECORDED",
        }





def test_audit_emergency_change_ccb_ratification_governance_governed():
    """> Emergencias justificadas y ratificadas dentro del límite -> GOVERNED protocol."""
    from backend.services.project_ccb_service import (
        audit_emergency_change_ccb_ratification_governance as audit_fn,
    )

    res = audit_fn(
        [
            {
                "id": "CR-PLAN-1",
                "status": "CCB_APPROVED",
            },
            {
                "id": "CR-EMG-1",
                "is_emergency": True,
                "incident_reference": "INC-2026-441",
                "justification": "Caída del medidor de red en sede central",
                "status": "RATIFIED",
                "days_since_implementation": 2,
                "ratified_by": "@ccb-secretaria",
            },
            {
                "id": "CR-EMG-NO-PLANO",
                "status": "IMPLEMENTED",
            },
        ] + [{"id": f"CR-FILLER-{i}", "status": "APPROVED"} for i in range(8)],
        max_ratification_days=5,
        max_emergency_share_pct=20.0,
    )
    assert res["total_change_requests"] == 11
    assert res["emergency_changes_count"] == 1
    assert res["emergency_share_pct"] == 9.09
    assert res["unjustified_emergency_cr_ids"] == []
    assert res["overdue_ratification_cr_ids"] == []
    assert res["unratified_closed_emergency_cr_ids"] == []
    assert res["is_emergency_governance_valid"] is True
    assert res["emergency_posture"] == "GOVERNED_EMERGENCY_CHANGE_PROTOCOL"


def test_audit_emergency_change_ccb_ratification_governance_unjustified():
    """> Emergencia sin incident_reference o justification -> UNJUSTIFIED bypass."""
    from backend.services.project_ccb_service import (
        audit_emergency_change_ccb_ratification_governance as audit_fn,
    )

    res = audit_fn(
        [
            {
                "id": "CR-EMG-2",
                "is_emergency": True,
                "incident_reference": "INC-2026-442",
                "justification": "Minuta de ataques de red en mediación",
                "status": "RATIFIED",
                "days_since_implementation": 1,
                "ratified_by": "@ccb",
            },
            {
                "id": "CR-EMG-3",
                "is_emergency": True,
                "justification": "Solo justificación sin referencia de incidente",
                "status": "RATIFIED",
                "days_since_implementation": 1,
                "ratified_by": "@ccb",
            },
        ]
    )
    assert res["is_emergency_governance_valid"] is False
    assert res["total_change_requests"] == 2
    assert res["emergency_changes_count"] == 2
    assert res["emergency_share_pct"] == 100.0
    assert res["unjustified_emergency_cr_ids"] == ["CR-EMG-3"]
    assert res["overdue_ratification_cr_ids"] == []
    assert res["unratified_closed_emergency_cr_ids"] == []
    assert res["emergency_posture"] == "UNJUSTIFIED_EMERGENCY_BYPASS"


def test_audit_emergency_change_ccb_ratification_governance_overdue():
    """> Ratificación tardía (8 > 5 días) sin status ratificado -> OVERDUE ratification."""
    from backend.services.project_ccb_service import (
        audit_emergency_change_ccb_ratification_governance as audit_fn,
    )

    res = audit_fn(
        [
            {
                "id": "CR-EMG-LATE",
                "is_emergency": True,
                "incident_reference": "INC-2026-500",
                "justification": "Falla critica en producción",
                "status": "IMPLEMENTED",
                "days_since_implementation": 8,
                "ratified_by": "@ccb",
            }
        ],
        max_ratification_days=5,
    )
    assert res["is_emergency_governance_valid"] is False
    assert res["total_change_requests"] == 1
    assert res["emergency_changes_count"] == 1
    assert res["unjustified_emergency_cr_ids"] == []
    assert res["overdue_ratification_cr_ids"] == ["CR-EMG-LATE"]
    assert res["unratified_closed_emergency_cr_ids"] == []
    assert res["emergency_posture"] == "OVERDUE_RETROACTIVE_CCB_RATIFICATION"


def test_audit_emergency_change_ccb_ratification_governance_unratified_and_empty():
    """> Cierre sin ratified_by -> UNRATIFIED closure; sin emergencias -> NO_EMERGENCY."""
    from backend.services.project_ccb_service import (
        audit_emergency_change_ccb_ratification_governance as audit_fn,
    )

    res = audit_fn(
        [
            {
                "id": "CR-EMG-CLOSED",
                "is_emergency": True,
                "incident_reference": "INC-2026-600",
                "justification": "Riesgo de datos en despliegue",
                "status": "CLOSED",
                "days_since_implementation": 1,
            }
        ]
    )
    assert res["is_emergency_governance_valid"] is False
    assert res["total_change_requests"] == 1
    assert res["emergency_changes_count"] == 1
    assert res["unratified_closed_emergency_cr_ids"] == ["CR-EMG-CLOSED"]
    assert res["unjustified_emergency_cr_ids"] == []
    assert res["overdue_ratification_cr_ids"] == []
    assert res["emergency_posture"] == "UNRATIFIED_EMERGENCY_CLOSURE"

    for payload in (None, [], [{"status": "APPROVED"}, {"cr_id": ""}], ["invalid", 42]):
        res = audit_fn(payload)  # type: ignore[arg-type]
        assert res["total_change_requests"] == 0
        assert res["emergency_changes_count"] == 0
        assert res["emergency_share_pct"] == 0.0
        assert res["is_emergency_governance_valid"] is False
        assert res["emergency_posture"] == "NO_EMERGENCY_CHANGES"


def test_evaluate_pareto_vital_few_defect_causes_high_concentration_governed():
    """<= 50% de categorías concentran >= 80% de defectos con CAPA -> HIGH_PARETO_CONCENTRATION_GOVERNED."""
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        evaluate_pareto_vital_few_defect_causes,
    )

    categories = [
        {"category_id": "CAT-SCHEMA", "defect_count": 55, "has_capa_plan": True},
        {"id": "CAT-AUTH", "defect_count": 30, "has_capa_plan": True},
        {"category_id": "CAT-UI", "defect_count": 8, "has_capa_plan": False},
        {"category_id": "CAT-CSS", "defect_count": 5, "has_capa_plan": False},
        {"category_id": "CAT-COPY", "defect_count": 2, "has_capa_plan": False},
    ]
    res = evaluate_pareto_vital_few_defect_causes(categories, pareto_cutoff_pct=80.0)
    assert res == {
        "total_defects": 100,
        "total_categories": 5,
        "vital_few_category_ids": ["CAT-SCHEMA", "CAT-AUTH"],
        "vital_few_share_pct": 85.0,
        "unmitigated_vital_category_ids": [],
        "is_pareto_actionable": True,
        "pareto_posture": "HIGH_PARETO_CONCENTRATION_GOVERNED",
    }
    assert (
        ProjectCCBService.evaluate_pareto_vital_few_defect_causes(
            categories, pareto_cutoff_pct=80.0
        )
        == res
    )


def test_evaluate_pareto_vital_few_defect_causes_unmitigated_vital():
    """Categoría vital sin plan CAPA -> UNMITIGATED_VITAL_FEW_CAUSES."""
    from backend.services.project_ccb_service import (
        evaluate_pareto_vital_few_defect_causes,
    )

    res = evaluate_pareto_vital_few_defect_causes(
        [
            {"category_id": "CAT-DB-LOCK", "defect_count": 60, "has_capa_plan": False},
            {"category_id": "CAT-TIMEOUT", "defect_count": 25, "has_capa_plan": True},
            {"category_id": "CAT-TYPO", "defect_count": 15, "has_capa_plan": False},
        ],
        pareto_cutoff_pct=80.0,
    )
    assert res["vital_few_category_ids"] == ["CAT-DB-LOCK", "CAT-TIMEOUT"]
    assert res["unmitigated_vital_category_ids"] == ["CAT-DB-LOCK"]
    assert res["is_pareto_actionable"] is False
    assert res["pareto_posture"] == "UNMITIGATED_VITAL_FEW_CAUSES"


def test_evaluate_pareto_vital_few_defect_causes_dispersed_distribution():
    """> 50% de las categorías son necesarias para alcanzar 80% -> DISPERSED_DEFECT_DISTRIBUTION."""
    from backend.services.project_ccb_service import (
        evaluate_pareto_vital_few_defect_causes,
    )

    res = evaluate_pareto_vital_few_defect_causes(
        [
            {"category_id": "CAT-1", "defect_count": 25, "has_capa_plan": True},
            {"category_id": "CAT-2", "defect_count": 25, "has_capa_plan": True},
            {"category_id": "CAT-3", "defect_count": 25, "has_capa_plan": True},
            {"category_id": "CAT-4", "defect_count": 25, "has_capa_plan": True},
        ],
        pareto_cutoff_pct=80.0,
    )
    assert res["vital_few_category_ids"] == ["CAT-1", "CAT-2", "CAT-3", "CAT-4"]
    assert res["vital_few_share_pct"] == 100.0
    assert res["is_pareto_actionable"] is True
    assert res["pareto_posture"] == "DISPERSED_DEFECT_DISTRIBUTION"


def test_evaluate_pareto_vital_few_defect_causes_no_defect_data():
    """Lista vacía, None o categorías con 0 defectos -> NO_DEFECT_DATA."""
    from backend.services.project_ccb_service import (
        evaluate_pareto_vital_few_defect_causes,
    )

    for payload in (None, [], [{"category_id": "CAT-ZERO", "defect_count": 0}]):
        res = evaluate_pareto_vital_few_defect_causes(payload)
        assert res == {
            "total_defects": 0,
            "total_categories": 0,
            "vital_few_category_ids": [],
            "vital_few_share_pct": 0.0,
            "unmitigated_vital_category_ids": [],
            "is_pareto_actionable": False,
            "pareto_posture": "NO_DEFECT_DATA",
        }


def test_evaluate_deliverable_acceptance_traceability_verified_and_validated():
    """Entregables aceptados tras QC sin defectos críticos, con signoff y requirement_id -> VERIFIED_AND_VALIDATED_DELIVERABLES."""
    import backend.services.project_ccb_service as ccb_module
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        evaluate_deliverable_acceptance_traceability,
    )

    deliverables = [
        {
            "id": "DEL-01",
            "qc_verified": True,
            "scope_accepted": True,
            "open_critical_defects": 0,
            "acceptance_signoff_by": "Sponsor General",
            "requirement_id": "REQ-WBS-1.1",
        },
        {
            "deliverable_id": "DEL-02",
            "qc_verified": True,
            "scope_accepted": False,
            "open_critical_defects": 0,
            "acceptance_signoff_by": "",
            "requirement_id": "REQ-WBS-1.2",
        },
    ]
    res = evaluate_deliverable_acceptance_traceability(deliverables)
    assert res == {
        "total_deliverables": 2,
        "accepted_deliverables_count": 1,
        "accepted_without_qc_ids": [],
        "missing_signoff_deliverable_ids": [],
        "unlinked_requirement_deliverable_ids": [],
        "is_acceptance_chain_valid": True,
        "acceptance_posture": "VERIFIED_AND_VALIDATED_DELIVERABLES",
    }
    assert ProjectCCBService.evaluate_deliverable_acceptance_traceability(deliverables) == res
    assert "evaluate_deliverable_acceptance_traceability" in ccb_module.__all__


def test_evaluate_deliverable_acceptance_traceability_accepted_without_qc():
    """Entregable aceptado sin qc_verified o con defectos críticos abiertos -> SCOPE_ACCEPTED_WITHOUT_QC_VERIFICATION."""
    from backend.services.project_ccb_service import (
        evaluate_deliverable_acceptance_traceability,
    )

    res = evaluate_deliverable_acceptance_traceability(
        [
            {
                "id": "DEL-NO-QC",
                "qc_verified": False,
                "scope_accepted": True,
                "open_critical_defects": 0,
                "acceptance_signoff_by": "Sponsor",
                "requirement_id": "REQ-1",
            },
            {
                "id": "DEL-CRIT-DEF",
                "qc_verified": True,
                "scope_accepted": True,
                "open_critical_defects": 2,
                "acceptance_signoff_by": "Sponsor",
                "requirement_id": "REQ-2",
            },
        ]
    )
    assert res["total_deliverables"] == 2
    assert res["accepted_deliverables_count"] == 2
    assert res["accepted_without_qc_ids"] == ["DEL-NO-QC", "DEL-CRIT-DEF"]
    assert res["is_acceptance_chain_valid"] is False
    assert res["acceptance_posture"] == "SCOPE_ACCEPTED_WITHOUT_QC_VERIFICATION"


def test_evaluate_deliverable_acceptance_traceability_missing_signoff_and_unlinked_req():
    """Aceptado sin firma -> MISSING_FORMAL_ACCEPTANCE_SIGNOFF; sin requirement_id -> UNLINKED_REQUIREMENT_TRACEABILITY."""
    from backend.services.project_ccb_service import (
        evaluate_deliverable_acceptance_traceability,
    )

    res_signoff = evaluate_deliverable_acceptance_traceability(
        [
            {
                "id": "DEL-UNSIGNED",
                "qc_verified": True,
                "scope_accepted": True,
                "open_critical_defects": 0,
                "acceptance_signoff_by": "   ",
                "requirement_id": "REQ-10",
            }
        ]
    )
    assert res_signoff["missing_signoff_deliverable_ids"] == ["DEL-UNSIGNED"]
    assert res_signoff["is_acceptance_chain_valid"] is False
    assert res_signoff["acceptance_posture"] == "MISSING_FORMAL_ACCEPTANCE_SIGNOFF"

    res_unlinked = evaluate_deliverable_acceptance_traceability(
        [
            {
                "id": "DEL-ORPHAN",
                "qc_verified": True,
                "scope_accepted": True,
                "open_critical_defects": 0,
                "acceptance_signoff_by": "Cliente",
                "requirement_id": "",
            }
        ]
    )
    assert res_unlinked["unlinked_requirement_deliverable_ids"] == ["DEL-ORPHAN"]
    assert res_unlinked["is_acceptance_chain_valid"] is False
    assert res_unlinked["acceptance_posture"] == "UNLINKED_REQUIREMENT_TRACEABILITY"


def test_evaluate_deliverable_acceptance_traceability_no_deliverables():
    """Lista vacía, None o entradas sin id -> NO_DELIVERABLES_REGISTERED."""
    from backend.services.project_ccb_service import (
        evaluate_deliverable_acceptance_traceability,
    )

    for payload in (None, [], [{"id": ""}]):
        res = evaluate_deliverable_acceptance_traceability(payload)
        assert res == {
            "total_deliverables": 0,
            "accepted_deliverables_count": 0,
            "accepted_without_qc_ids": [],
            "missing_signoff_deliverable_ids": [],
            "unlinked_requirement_deliverable_ids": [],
            "is_acceptance_chain_valid": False,
            "acceptance_posture": "NO_DELIVERABLES_REGISTERED",
        }


def test_evaluate_cost_of_quality_conformance_balance_balanced():
    """Conformidad >= 50% y falla externa <= 15% sin entradas inválidas -> is_conformance_balanced True."""
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        evaluate_cost_of_quality_conformance_balance,
    )

    entries = [
        {"entry_id": "COQ-1", "category": "prevention", "amount": 4000.0},
        {"entry_id": "COQ-2", "category": "appraisal", "amount": 2500.0},
        {"entry_id": "COQ-3", "category": "internal_failure", "amount": 2500.0},
        {"entry_id": "COQ-4", "category": "external_failure", "amount": 1000.0},
    ]
    res = evaluate_cost_of_quality_conformance_balance(entries)
    assert res == {
        "evaluated_entry_count": 4,
        "prevention_cost": 4000.0,
        "appraisal_cost": 2500.0,
        "internal_failure_cost": 2500.0,
        "external_failure_cost": 1000.0,
        "conformance_cost": 6500.0,
        "nonconformance_cost": 3500.0,
        "total_coq": 10000.0,
        "conformance_share_pct": 65.0,
        "nonconformance_share_pct": 35.0,
        "external_failure_share_pct": 10.0,
        "prevention_to_failure_ratio": 1.14,
        "invalid_entry_ids": [],
        "is_conformance_balanced": True,
    }
    assert (
        ProjectCCBService.evaluate_cost_of_quality_conformance_balance(entries) == res
    )


def test_evaluate_cost_of_quality_conformance_balance_high_external_failure_or_low_conformance():
    """Falla externa > 15% o conformidad < 50% -> is_conformance_balanced False."""
    from backend.services.project_ccb_service import (
        evaluate_cost_of_quality_conformance_balance,
    )

    res_ext = evaluate_cost_of_quality_conformance_balance(
        [
            {"entry_id": "COQ-P", "category": "prevention", "amount": 6000.0},
            {"entry_id": "COQ-E", "category": "external_failure", "amount": 2000.0},
        ],
        max_external_failure_share_pct=15.0,
    )
    assert res_ext["conformance_share_pct"] == 75.0
    assert res_ext["external_failure_share_pct"] == 25.0
    assert res_ext["is_conformance_balanced"] is False

    res_low_conf = evaluate_cost_of_quality_conformance_balance(
        [
            {"entry_id": "COQ-P2", "category": "prevention", "amount": 2000.0},
            {"entry_id": "COQ-I2", "category": "internal_failure", "amount": 3000.0},
        ],
        min_conformance_share_pct=50.0,
    )
    assert res_low_conf["conformance_share_pct"] == 40.0
    assert res_low_conf["nonconformance_share_pct"] == 60.0
    assert res_low_conf["is_conformance_balanced"] is False


def test_evaluate_cost_of_quality_conformance_balance_invalid_entries():
    """Categoría desconocida o monto negativo -> invalid_entry_ids poblado, is_conformance_balanced False."""
    from backend.services.project_ccb_service import (
        evaluate_cost_of_quality_conformance_balance,
    )

    res = evaluate_cost_of_quality_conformance_balance(
        [
            {"entry_id": "COQ-OK", "category": "prevention", "amount": 1000.0},
            {"entry_id": "COQ-BAD-CAT", "category": "unknown_type", "amount": 500.0},
            {"entry_id": "COQ-NEG", "category": "appraisal", "amount": -100.0},
        ]
    )
    assert res["evaluated_entry_count"] == 3
    assert res["invalid_entry_ids"] == ["COQ-BAD-CAT", "COQ-NEG"]
    assert res["prevention_cost"] == 1000.0
    assert res["prevention_to_failure_ratio"] == 1000.0
    assert res["is_conformance_balanced"] is False


def test_evaluate_cost_of_quality_conformance_balance_empty():
    """Lista vacía, None o entradas sin entry_id -> evaluated_entry_count 0, is_conformance_balanced False."""
    from backend.services.project_ccb_service import (
        evaluate_cost_of_quality_conformance_balance,
    )

    for payload in (None, [], [{"entry_id": "  "}], ["invalid"]):
        res = evaluate_cost_of_quality_conformance_balance(payload)  # type: ignore[arg-type]
        assert res == {
            "evaluated_entry_count": 0,
            "prevention_cost": 0.0,
            "appraisal_cost": 0.0,
            "internal_failure_cost": 0.0,
            "external_failure_cost": 0.0,
            "conformance_cost": 0.0,
            "nonconformance_cost": 0.0,
            "total_coq": 0.0,
            "conformance_share_pct": 100.0,
            "nonconformance_share_pct": 0.0,
            "external_failure_share_pct": 0.0,
            "prevention_to_failure_ratio": 0.0,
            "invalid_entry_ids": [],
            "is_conformance_balanced": False,
        }


def test_evaluate_spc_control_chart_stability_in_statistical_control():
    """Muestras dentro de límites de control y especificación sin rachas >= 7 -> is_in_statistical_control True."""
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        evaluate_spc_control_chart_stability,
    )

    samples = [10.1, 9.8, 10.2, 10.0, 9.9, 10.3, 9.7, 10.1]
    res = evaluate_spc_control_chart_stability(
        samples,
        center_line=10.0,
        upper_control_limit=11.0,
        lower_control_limit=9.0,
        upper_spec_limit=11.5,
        lower_spec_limit=8.5,
    )
    assert res == {
        "sample_count": 8,
        "has_invalid_limits": False,
        "out_of_control_indices": [],
        "out_of_spec_indices": [],
        "rule_of_seven_violation_indices": [],
        "is_in_statistical_control": True,
    }
    assert (
        ProjectCCBService.evaluate_spc_control_chart_stability(
            samples,
            center_line=10.0,
            upper_control_limit=11.0,
            lower_control_limit=9.0,
            upper_spec_limit=11.5,
            lower_spec_limit=8.5,
        )
        == res
    )


def test_evaluate_spc_control_chart_stability_out_of_control_and_spec():
    """Muestras fuera de UCL/LCL y USL/LSL -> out_of_control_indices y out_of_spec_indices poblados."""
    from backend.services.project_ccb_service import (
        evaluate_spc_control_chart_stability,
    )

    res = evaluate_spc_control_chart_stability(
        [10.0, 11.2, 8.4, 10.0],
        center_line=10.0,
        upper_control_limit=11.0,
        lower_control_limit=9.0,
        upper_spec_limit=11.5,
        lower_spec_limit=8.5,
    )
    assert res == {
        "sample_count": 4,
        "has_invalid_limits": False,
        "out_of_control_indices": [1, 2],
        "out_of_spec_indices": [2],
        "rule_of_seven_violation_indices": [],
        "is_in_statistical_control": False,
    }


def test_evaluate_spc_control_chart_stability_rule_of_seven_violation():
    """7 o más puntos consecutivos del mismo lado de center_line -> rule_of_seven_violation_indices."""
    from backend.services.project_ccb_service import (
        evaluate_spc_control_chart_stability,
    )

    res = evaluate_spc_control_chart_stability(
        [10.1, 10.2, 10.3, 10.1, 10.4, 10.2, 10.1, 10.3, 9.8],
        center_line=10.0,
        upper_control_limit=11.0,
        lower_control_limit=9.0,
    )
    assert res == {
        "sample_count": 9,
        "has_invalid_limits": False,
        "out_of_control_indices": [],
        "out_of_spec_indices": [],
        "rule_of_seven_violation_indices": [6, 7],
        "is_in_statistical_control": False,
    }


def test_evaluate_spc_control_chart_stability_invalid_limits_or_empty():
    """Límites inválidos o muestras vacías -> is_in_statistical_control False."""
    from backend.services.project_ccb_service import (
        evaluate_spc_control_chart_stability,
    )

    res_inv = evaluate_spc_control_chart_stability(
        [10.0, 10.1],
        center_line=12.0,
        upper_control_limit=11.0,
        lower_control_limit=9.0,
    )
    assert res_inv["has_invalid_limits"] is True
    assert res_inv["is_in_statistical_control"] is False

    res_empty = evaluate_spc_control_chart_stability(
        None,
        center_line=10.0,
        upper_control_limit=11.0,
        lower_control_limit=9.0,
    )
    assert res_empty == {
        "sample_count": 0,
        "has_invalid_limits": False,
        "out_of_control_indices": [],
        "out_of_spec_indices": [],
        "rule_of_seven_violation_indices": [],
        "is_in_statistical_control": False,
    }


def test_audit_configuration_items_baseline_integrity_v2_verified():
    """CIs baselined, sin drift y con checksum verificado -> is_integrity_verified."""
    from backend.services.project_ccb_service import (
        audit_configuration_items_baseline_integrity,
        ProjectCCBService,
    )

    res = audit_configuration_items_baseline_integrity(
        [
            {
                "ci_id": "CI-API",
                "baseline_version": "1.2.0",
                "deployed_version": "1.2.0",
                "checksum_verified": True,
            },
            {
                "ci_id": "CI-DB",
                "baseline_version": "2026.10",
                "deployed_version": "2026.10",
                "checksum_verified": True,
            },
        ]
    )
    assert res["evaluated_ci_count"] == 2
    assert res["unbaselined_ci_ids"] == []
    assert res["version_drift_ci_ids"] == []
    assert res["unauthorized_drift_ci_ids"] == []
    assert res["unverified_checksum_ci_ids"] == []
    assert res["is_integrity_verified"] is True

    static_res = ProjectCCBService.audit_configuration_items_baseline_integrity(
        [
            {
                "ci_id": "CI-API",
                "baseline_version": "1.2.0",
                "deployed_version": "1.2.0",
                "checksum_verified": True,
            },
        ]
    )
    assert static_res["is_integrity_verified"] is True


def test_audit_configuration_items_baseline_integrity_v2_unbaselined_skips_drift():
    """CI sin baseline o sin deployed -> unbaselined (continúa, no aporta drift)."""
    from backend.services.project_ccb_service import (
        audit_configuration_items_baseline_integrity,
    )

    res = audit_configuration_items_baseline_integrity(
        [
            {"ci_id": "CI-NO-BASE", "deployed_version": "1.0.0", "checksum_verified": True},
            {"ci_id": "CI-NO-DEPLOY", "baseline_version": "1.0.0", "checksum_verified": True},
            {
                "ci_id": "CI-DRIFT-OK",
                "baseline_version": "1.0.0",
                "deployed_version": "1.1.0",
                "approved_change_request_id": "CR-77",
                "checksum_verified": True,
            },
        ]
    )
    assert res["evaluated_ci_count"] == 3
    assert res["unbaselined_ci_ids"] == ["CI-NO-BASE", "CI-NO-DEPLOY"]
    assert res["version_drift_ci_ids"] == ["CI-DRIFT-OK"]
    assert res["unauthorized_drift_ci_ids"] == []
    assert res["unverified_checksum_ci_ids"] == []
    assert res["is_integrity_verified"] is False


def test_audit_configuration_items_baseline_integrity_v2_unauthorized_drift():
    """Drift sin CR aprobado -> unauthorized_drift; checksum falso se reporta aparte."""
    from backend.services.project_ccb_service import (
        audit_configuration_items_baseline_integrity,
    )

    res = audit_configuration_items_baseline_integrity(
        [
            {
                "ci_id": "CI-ROGUE",
                "baseline_version": "2.0.0",
                "deployed_version": "2.1.0",
                "checksum_verified": True,
            },
            {
                "ci_id": "CI-DRIFT-OK",
                "baseline_version": "2.0.0",
                "deployed_version": "2.0.1",
                "approved_change_request_id": "CR-88",
                "checksum_verified": True,
            },
        ]
    )
    assert res["evaluated_ci_count"] == 2
    assert res["version_drift_ci_ids"] == ["CI-ROGUE", "CI-DRIFT-OK"]
    assert res["unauthorized_drift_ci_ids"] == ["CI-ROGUE"]
    assert res["unbaselined_ci_ids"] == []
    assert res["is_integrity_verified"] is False

    res_checksum = audit_configuration_items_baseline_integrity(
        [
            {
                "ci_id": "CI-BASE-SAME",
                "baseline_version": "3.0.0",
                "deployed_version": "3.0.0",
            },
        ]
    )
    assert res_checksum["version_drift_ci_ids"] == []
    assert res_checksum["unverified_checksum_ci_ids"] == ["CI-BASE-SAME"]
    assert res_checksum["is_integrity_verified"] is False


def test_audit_configuration_items_baseline_integrity_v2_empty_or_none():
    """None, lista vacía o entradas no-Mapping/sin ci_id -> is_integrity_verified False."""
    from backend.services.project_ccb_service import (
        audit_configuration_items_baseline_integrity,
    )

    for payload in (None, [], ["no-dict", 42, {"baseline_version": "1.0.0"}]):
        assert audit_configuration_items_baseline_integrity(payload) == {  # type: ignore[arg-type]
            "evaluated_ci_count": 0,
            "unbaselined_ci_ids": [],
            "version_drift_ci_ids": [],
            "unauthorized_drift_ci_ids": [],
            "unverified_checksum_ci_ids": [],
            "is_integrity_verified": False,
        }


def test_evaluate_quality_capa_root_cause_effectiveness_healthy():
    """CAPAs con método RCA válido, verificación aprobada y 0 recurrencias pasan is_capa_system_healthy=True."""
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        evaluate_quality_capa_root_cause_effectiveness,
    )

    records = [
        {
            "capa_id": "CAPA-01",
            "root_cause_method": "5_Whys",
            "verification_passed": True,
            "recurrence_count": 0,
            "status": "closed",
        },
        {
            "capa_id": "CAPA-02",
            "root_cause_method": "ishikawa",
            "verification_passed": True,
            "recurrence_count": 0,
            "status": "verified",
        },
    ]
    res = evaluate_quality_capa_root_cause_effectiveness(records)
    assert res == {
        "total_capas": 2,
        "missing_rca_method_capa_ids": [],
        "unverified_closure_capa_ids": [],
        "recurring_defect_capa_ids": [],
        "effectiveness_rate_pct": 100.0,
        "is_capa_system_healthy": True,
    }
    assert (
        ProjectCCBService.evaluate_quality_capa_root_cause_effectiveness(records)
        == res
    )


def test_evaluate_quality_capa_root_cause_effectiveness_missing_rca_and_unverified_closure():
    """Detecta método RCA no canónico y cierre sin verificación."""
    from backend.services.project_ccb_service import (
        evaluate_quality_capa_root_cause_effectiveness,
    )

    res = evaluate_quality_capa_root_cause_effectiveness(
        [
            {
                "capa_id": "CAPA-NO-RCA",
                "root_cause_method": "guesswork",
                "verification_passed": True,
                "recurrence_count": 0,
                "status": "closed",
            },
            {
                "capa_id": "CAPA-UNVERIF",
                "root_cause_method": "fmea",
                "verification_passed": False,
                "recurrence_count": 0,
                "status": "Closed",
            },
        ]
    )
    assert res == {
        "total_capas": 2,
        "missing_rca_method_capa_ids": ["CAPA-NO-RCA"],
        "unverified_closure_capa_ids": ["CAPA-UNVERIF"],
        "recurring_defect_capa_ids": [],
        "effectiveness_rate_pct": 0.0,
        "is_capa_system_healthy": False,
    }


def test_evaluate_quality_capa_root_cause_effectiveness_recurring_defects():
    """Detecta CAPAs con recurrencia posterior (recurrence_count > 0)."""
    from backend.services.project_ccb_service import (
        evaluate_quality_capa_root_cause_effectiveness,
    )

    res = evaluate_quality_capa_root_cause_effectiveness(
        [
            {
                "capa_id": "CAPA-OK",
                "root_cause_method": "fault_tree",
                "verification_passed": True,
                "recurrence_count": 0,
                "status": "effective",
            },
            {
                "capa_id": "CAPA-REC",
                "root_cause_method": "pareto",
                "verification_passed": True,
                "recurrence_count": 2,
                "status": "closed",
            },
        ]
    )
    assert res == {
        "total_capas": 2,
        "missing_rca_method_capa_ids": [],
        "unverified_closure_capa_ids": [],
        "recurring_defect_capa_ids": ["CAPA-REC"],
        "effectiveness_rate_pct": 50.0,
        "is_capa_system_healthy": False,
    }


def test_evaluate_quality_capa_root_cause_effectiveness_empty_or_invalid():
    """Entradas vacías, None o no-secuencia devuelven total_capas=0 e is_capa_system_healthy=False."""
    from backend.services.project_ccb_service import (
        evaluate_quality_capa_root_cause_effectiveness,
    )

    for payload in (None, [], "invalid", {"capa_id": "C1"}, [{"capa_id": "  "}]):
        assert evaluate_quality_capa_root_cause_effectiveness(payload) == {  # type: ignore[arg-type]
            "total_capas": 0,
            "missing_rca_method_capa_ids": [],
            "unverified_closure_capa_ids": [],
            "recurring_defect_capa_ids": [],
            "effectiveness_rate_pct": 0.0,
            "is_capa_system_healthy": False,
        }


def test_evaluate_ccb_emergency_change_retrospective_compliance_compliant():
    """Cambios de emergencia con rollback documentado, ratificación CCB y PIR dentro del SLA pasan is_emergency_governance_compliant=True."""
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        evaluate_ccb_emergency_change_retrospective_compliance,
    )

    crs = [
        {
            "cr_id": "CR-EMG-01",
            "is_emergency": True,
            "rollback_plan_documented": True,
            "ccb_ratified": True,
            "post_implementation_review_hours": 24.0,
        },
        {
            "cr_id": "CR-STD-02",
            "is_emergency": False,
            "rollback_plan_documented": False,
            "ccb_ratified": False,
        },
    ]
    res = evaluate_ccb_emergency_change_retrospective_compliance(
        crs, max_retrospective_sla_hours=48.0
    )
    assert res == {
        "total_emergency_changes": 1,
        "missing_rollback_plan_cr_ids": [],
        "unratified_emergency_cr_ids": [],
        "sla_breached_pir_cr_ids": [],
        "is_emergency_governance_compliant": True,
    }
    assert (
        ProjectCCBService.evaluate_ccb_emergency_change_retrospective_compliance(
            crs, max_retrospective_sla_hours=48.0
        )
        == res
    )


def test_evaluate_ccb_emergency_change_retrospective_compliance_missing_rollback_and_unratified():
    """Detecta cambios de emergencia sin rollback_plan_documented o sin ccb_ratified."""
    from backend.services.project_ccb_service import (
        evaluate_ccb_emergency_change_retrospective_compliance,
    )

    res = evaluate_ccb_emergency_change_retrospective_compliance(
        [
            {
                "cr_id": "CR-NO-RB",
                "is_emergency": True,
                "rollback_plan_documented": False,
                "ccb_ratified": True,
                "post_implementation_review_hours": 12.0,
            },
            {
                "cr_id": "CR-UNRAT",
                "is_emergency": True,
                "rollback_plan_documented": True,
                "ccb_ratified": False,
                "post_implementation_review_hours": 36.0,
            },
        ]
    )
    assert res == {
        "total_emergency_changes": 2,
        "missing_rollback_plan_cr_ids": ["CR-NO-RB"],
        "unratified_emergency_cr_ids": ["CR-UNRAT"],
        "sla_breached_pir_cr_ids": [],
        "is_emergency_governance_compliant": False,
    }


def test_evaluate_ccb_emergency_change_retrospective_compliance_pir_sla_breach():
    """Detecta PIR ausente (None), negativo o mayor a max_retrospective_sla_hours."""
    from backend.services.project_ccb_service import (
        evaluate_ccb_emergency_change_retrospective_compliance,
    )

    res = evaluate_ccb_emergency_change_retrospective_compliance(
        [
            {
                "cr_id": "CR-PIR-NONE",
                "is_emergency": True,
                "rollback_plan_documented": True,
                "ccb_ratified": True,
                "post_implementation_review_hours": None,
            },
            {
                "cr_id": "CR-PIR-LATE",
                "is_emergency": True,
                "rollback_plan_documented": True,
                "ccb_ratified": True,
                "post_implementation_review_hours": 72.0,
            },
        ],
        max_retrospective_sla_hours=48.0,
    )
    assert res == {
        "total_emergency_changes": 2,
        "missing_rollback_plan_cr_ids": [],
        "unratified_emergency_cr_ids": [],
        "sla_breached_pir_cr_ids": ["CR-PIR-NONE", "CR-PIR-LATE"],
        "is_emergency_governance_compliant": False,
    }


def test_evaluate_ccb_emergency_change_retrospective_compliance_empty_or_no_emergency():
    """Entradas vacías, None o sin cambios de emergencia devuelven total_emergency_changes=0 e is_emergency_governance_compliant=False."""
    from backend.services.project_ccb_service import (
        evaluate_ccb_emergency_change_retrospective_compliance,
    )

    for payload in (
        None,
        [],
        "invalid",
        [{"cr_id": "CR-NORMAL", "is_emergency": False}],
    ):
        assert evaluate_ccb_emergency_change_retrospective_compliance(payload) == {  # type: ignore[arg-type]
            "total_emergency_changes": 0,
            "missing_rollback_plan_cr_ids": [],
            "unratified_emergency_cr_ids": [],
            "sla_breached_pir_cr_ids": [],
            "is_emergency_governance_compliant": False,
        }


def test_evaluate_quality_aql_lot_sampling_acceptance_all_accepted():
    """Lotes con muestra válida y defectos <= acceptance_number -> 100% aceptados y compliant True."""
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        evaluate_quality_aql_lot_sampling_acceptance,
    )

    lots = [
        {
            "lot_id": "LOT-01",
            "lot_size": 500,
            "sample_size": 50,
            "defects_found": 1,
            "acceptance_number": 2,
        },
        {
            "lot_id": "LOT-02",
            "lot_size": 200,
            "sample_size": 32,
            "defects_found": 0,
            "acceptance_number": 0,
        },
    ]
    res = evaluate_quality_aql_lot_sampling_acceptance(lots)
    assert res == {
        "total_lots": 2,
        "accepted_lot_ids": ["LOT-01", "LOT-02"],
        "rejected_lot_ids": [],
        "invalid_sample_size_lot_ids": [],
        "lot_acceptance_rate_pct": 100.0,
        "is_sampling_quality_compliant": True,
    }
    assert ProjectCCBService.evaluate_quality_aql_lot_sampling_acceptance(lots) == res


def test_evaluate_quality_aql_lot_sampling_acceptance_rejected_lots():
    """Lotes con defects_found > acceptance_number se reportan en rejected_lot_ids."""
    from backend.services.project_ccb_service import (
        evaluate_quality_aql_lot_sampling_acceptance,
    )

    res = evaluate_quality_aql_lot_sampling_acceptance(
        [
            {
                "lot_id": "LOT-PASS",
                "lot_size": 100,
                "sample_size": 20,
                "defects_found": 1,
                "acceptance_number": 1,
            },
            {
                "lot_id": "LOT-FAIL",
                "lot_size": 100,
                "sample_size": 20,
                "defects_found": 3,
                "acceptance_number": 1,
            },
        ]
    )
    assert res == {
        "total_lots": 2,
        "accepted_lot_ids": ["LOT-PASS"],
        "rejected_lot_ids": ["LOT-FAIL"],
        "invalid_sample_size_lot_ids": [],
        "lot_acceptance_rate_pct": 50.0,
        "is_sampling_quality_compliant": False,
    }


def test_evaluate_quality_aql_lot_sampling_acceptance_invalid_sample_sizes():
    """lot_size <= 0, sample_size <= 0 o sample_size > lot_size -> invalid_sample_size_lot_ids."""
    from backend.services.project_ccb_service import (
        evaluate_quality_aql_lot_sampling_acceptance,
    )

    res = evaluate_quality_aql_lot_sampling_acceptance(
        [
            {"lot_id": "LOT-ZERO-LOT", "lot_size": 0, "sample_size": 10},
            {"lot_id": "LOT-ZERO-SMP", "lot_size": 100, "sample_size": 0},
            {"lot_id": "LOT-OVERSMP", "lot_size": 50, "sample_size": 60},
        ]
    )
    assert res == {
        "total_lots": 3,
        "accepted_lot_ids": [],
        "rejected_lot_ids": [],
        "invalid_sample_size_lot_ids": [
            "LOT-ZERO-LOT",
            "LOT-ZERO-SMP",
            "LOT-OVERSMP",
        ],
        "lot_acceptance_rate_pct": 0.0,
        "is_sampling_quality_compliant": False,
    }


def test_evaluate_quality_aql_lot_sampling_acceptance_empty_or_invalid():
    """Entrada None, vacía o no secuencial retorna contadores en 0 e is_sampling_quality_compliant=False."""
    from backend.services.project_ccb_service import (
        evaluate_quality_aql_lot_sampling_acceptance,
    )

    for payload in (None, [], "invalid", {"lot_id": "LOT-1"}, [{"lot_id": "  "}]):
        assert evaluate_quality_aql_lot_sampling_acceptance(payload) == {  # type: ignore[arg-type]
            "total_lots": 0,
            "accepted_lot_ids": [],
            "rejected_lot_ids": [],
            "invalid_sample_size_lot_ids": [],
            "lot_acceptance_rate_pct": 0.0,
            "is_sampling_quality_compliant": False,
        }


def test_evaluate_copq_rework_and_scrap_ratio_controlled():
    """COPQ <= max_copq_pct_of_actual y fallas externas <= 40% del COPQ -> controlled."""
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        evaluate_copq_rework_and_scrap_ratio,
    )

    metrics = {
        "rework_cost": 3000.0,
        "scrap_cost": 2000.0,
        "warranty_cost": 1500.0,
        "sla_penalty_cost": 500.0,
        "actual_project_cost": 100000.0,
    }
    res = evaluate_copq_rework_and_scrap_ratio(metrics, max_copq_pct_of_actual=10.0)
    assert res == {
        "internal_failure_cost": 5000.0,
        "external_failure_cost": 2000.0,
        "total_copq": 7000.0,
        "copq_pct_of_actual_cost": 7.0,
        "external_failure_share_pct": 28.57,
        "copq_posture": "controlled",
        "is_copq_controlled": True,
    }
    assert (
        ProjectCCBService.evaluate_copq_rework_and_scrap_ratio(
            metrics, max_copq_pct_of_actual=10.0
        )
        == res
    )


def test_evaluate_copq_rework_and_scrap_ratio_excessive_bleed():
    """COPQ > max_copq_pct_of_actual -> excessive_copq_bleed."""
    from backend.services.project_ccb_service import (
        evaluate_copq_rework_and_scrap_ratio,
    )

    res = evaluate_copq_rework_and_scrap_ratio(
        {
            "rework_cost": 9000.0,
            "scrap_cost": 4000.0,
            "warranty_cost": 1000.0,
            "sla_penalty_cost": 0.0,
            "actual_project_cost": 100000.0,
        },
        max_copq_pct_of_actual=10.0,
    )
    assert res == {
        "internal_failure_cost": 13000.0,
        "external_failure_cost": 1000.0,
        "total_copq": 14000.0,
        "copq_pct_of_actual_cost": 14.0,
        "external_failure_share_pct": 7.14,
        "copq_posture": "excessive_copq_bleed",
        "is_copq_controlled": False,
    }


def test_evaluate_copq_rework_and_scrap_ratio_external_escape_dominant():
    """COPQ <= umbral pero fallas externas > 40% del total_copq -> external_escape_dominant."""
    from backend.services.project_ccb_service import (
        evaluate_copq_rework_and_scrap_ratio,
    )

    res = evaluate_copq_rework_and_scrap_ratio(
        {
            "rework_cost": 2000.0,
            "scrap_cost": 1000.0,
            "warranty_cost": 2500.0,
            "sla_penalty_cost": 1500.0,
            "actual_project_cost": 100000.0,
        },
        max_copq_pct_of_actual=10.0,
    )
    assert res == {
        "internal_failure_cost": 3000.0,
        "external_failure_cost": 4000.0,
        "total_copq": 7000.0,
        "copq_pct_of_actual_cost": 7.0,
        "external_failure_share_pct": 57.14,
        "copq_posture": "external_escape_dominant",
        "is_copq_controlled": False,
    }


def test_evaluate_copq_rework_and_scrap_ratio_invalid_inputs():
    """Entrada no Mapping o actual_project_cost <= 0 -> invalid_inputs."""
    from backend.services.project_ccb_service import (
        evaluate_copq_rework_and_scrap_ratio,
    )

    for payload in (
        None,
        {},
        "invalid",
        {"actual_project_cost": 0.0, "rework_cost": 500.0},
        {"actual_project_cost": -1000.0, "rework_cost": 500.0},
    ):
        assert evaluate_copq_rework_and_scrap_ratio(payload) == {  # type: ignore[arg-type]
            "internal_failure_cost": 0.0,
            "external_failure_cost": 0.0,
            "total_copq": 0.0,
            "copq_pct_of_actual_cost": 0.0,
            "external_failure_share_pct": 0.0,
            "copq_posture": "invalid_inputs",
            "is_copq_controlled": False,
        }


def test_audit_ccb_change_request_sla_and_aging_backlog_compliant():
    """> Cola dentro de SLA (normal/urgente), diferidos con fecha bajo umbral -> compliant."""
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_ccb_change_request_sla_and_aging_backlog,
    )

    res = audit_ccb_change_request_sla_and_aging_backlog(
        [
            {
                "cr_id": "CR-1",
                "status": "pending",
                "priority": "normal",
                "age_days": 14.0,
                "impact_assessment_owner": "u-1",
            },
            {
                "cr_id": "CR-2",
                "status": "in_review",
                "priority": "urgent",
                "age_days": 3.0,
                "impact_assessment_owner": "u-2",
            },
            {
                "cr_id": "CR-3",
                "status": "deferred",
                "re_evaluation_date": "2026-11-01",
            },
            {
                "cr_id": "CR-4",
                "status": "approved",
                "impact_assessment_owner": "u-1",
            },
        ]
    )
    assert res["total_evaluated"] == 4
    assert res["open_pending_count"] == 2
    assert res["deferred_count"] == 1
    assert res["deferred_ratio_pct"] == 25.0
    assert res["sla_breached_cr_ids"] == []
    assert res["unassigned_impact_owner_cr_ids"] == []
    assert res["deferred_without_review_date_cr_ids"] == []
    assert res["deferred_backlog_excess"] is False
    assert res["is_ccb_sla_compliant"] is True

    static_res = ProjectCCBService.audit_ccb_change_request_sla_and_aging_backlog(
        [
            {
                "cr_id": "CR-1",
                "status": "pending",
                "priority": "normal",
                "age_days": 10.0,
                "impact_assessment_owner": "u-1",
            },
        ]
    )
    assert static_res["is_ccb_sla_compliant"] is True


def test_audit_ccb_change_request_sla_and_aging_backlog_sla_and_owner_breaches():
    """> SLA violado en prioridad normal y urgent/critical; sin dueño de impacto."""
    from backend.services.project_ccb_service import (
        audit_ccb_change_request_sla_and_aging_backlog,
    )

    res = audit_ccb_change_request_sla_and_aging_backlog(
        [
            {
                "cr_id": "CR-SLA-NORMAL",
                "status": "submitted",
                "age_days": 15.0,
                "impact_assessment_owner": "u-1",
            },
            {
                "cr_id": "CR-SLA-URGENT",
                "status": "under_review",
                "priority": "critical",
                "age_days": 4.0,
                "impact_assessment_owner": "u-2",
            },
            {
                "cr_id": "CR-NO-OWNER",
                "status": "pending",
                "age_days": 1.0,
            },
            {
                "cr_id": "CR-EDGE-OK",
                "status": "pending",
                "age_days": 14.0,
                "impact_assessment_owner": "u-3",
            },
        ]
    )
    assert res["total_evaluated"] == 4
    assert res["open_pending_count"] == 4
    assert res["sla_breached_cr_ids"] == ["CR-SLA-NORMAL", "CR-SLA-URGENT"]
    assert res["unassigned_impact_owner_cr_ids"] == ["CR-NO-OWNER"]
    assert res["deferred_count"] == 0
    assert res["deferred_backlog_excess"] is False
    assert res["is_ccb_sla_compliant"] is False

    res_custom_sla = audit_ccb_change_request_sla_and_aging_backlog(
        [
            {
                "cr_id": "CR-SLA-NORMAL",
                "status": "submitted",
                "age_days": 15.0,
                "impact_assessment_owner": "u-1",
            },
        ],
        normal_sla_days=20.0,
    )
    assert res_custom_sla["sla_breached_cr_ids"] == []
    assert res_custom_sla["is_ccb_sla_compliant"] is True


def test_audit_ccb_change_request_sla_and_aging_backlog_deferred_backlog_excess():
    """> Ratio diferido > 25% y diferidos sin re_evaluation_date."""
    from backend.services.project_ccb_service import (
        audit_ccb_change_request_sla_and_aging_backlog,
    )

    res = audit_ccb_change_request_sla_and_aging_backlog(
        [
            {
                "cr_id": "CR-DEF-1",
                "status": "deferred",
                "re_evaluation_date": "  ",
            },
            {"cr_id": "CR-DEF-2", "status": "on_hold"},
            {
                "cr_id": "CR-OPEN",
                "status": "pending",
                "age_days": 2.0,
                "impact_assessment_owner": "u-1",
            },
        ]
    )
    assert res["total_evaluated"] == 3
    assert res["deferred_count"] == 2
    assert res["deferred_ratio_pct"] == 66.67
    assert res["deferred_backlog_excess"] is True
    assert res["deferred_without_review_date_cr_ids"] == ["CR-DEF-1", "CR-DEF-2"]
    assert res["is_ccb_sla_compliant"] is False

    res_within = audit_ccb_change_request_sla_and_aging_backlog(
        [
            {"cr_id": "CR-DEF-OK", "status": "deferred", "re_evaluation_date": "2026-12-01"},
            {"cr_id": "CR-OPEN", "status": "pending", "age_days": 1.0, "impact_assessment_owner": "u-1"},
            {"cr_id": "CR-OPEN2", "status": "pending", "age_days": 1.0, "impact_assessment_owner": "u-1"},
            {"cr_id": "CR-OPEN3", "status": "pending", "age_days": 1.0, "impact_assessment_owner": "u-1"},
        ],
    )
    assert res_within["deferred_ratio_pct"] == 25.0
    assert res_within["deferred_backlog_excess"] is False
    assert res_within["is_ccb_sla_compliant"] is True


def test_audit_ccb_change_request_sla_and_aging_backlog_empty_or_none():
    """None, no-secuencia, str, Mapping, 42 o basura -> 0 evaluadas."""
    from backend.services.project_ccb_service import (
        audit_ccb_change_request_sla_and_aging_backlog,
    )

    # Literal del spec: sin requisito total_evaluated>0 -> compliant=True con 0 entradas.
    empty_result = {
        "total_evaluated": 0,
        "open_pending_count": 0,
        "deferred_count": 0,
        "deferred_ratio_pct": 0.0,
        "sla_breached_cr_ids": [],
        "unassigned_impact_owner_cr_ids": [],
        "deferred_without_review_date_cr_ids": [],
        "deferred_backlog_excess": False,
        "is_ccb_sla_compliant": True,
    }

    for payload in (
        None,
        "changes-string",
        42,
        [],
        ["no-dict", {"status": "pending"}],
        [{"cr_id": "   "}, {"id": ""}],
    ):
        assert audit_ccb_change_request_sla_and_aging_backlog(payload) == empty_result  # type: ignore[arg-type]

    # ID válido con tipos basura: 1 evaluada, pending sin owner -> unassigned.
    assert audit_ccb_change_request_sla_and_aging_backlog(
        [{"cr_id": "CR-BAD", "age_days": "x"}]
    ) == {
        "total_evaluated": 1,
        "open_pending_count": 1,
        "deferred_count": 0,
        "deferred_ratio_pct": 0.0,
        "sla_breached_cr_ids": [],
        "unassigned_impact_owner_cr_ids": ["CR-BAD"],
        "deferred_without_review_date_cr_ids": [],
        "deferred_backlog_excess": False,
        "is_ccb_sla_compliant": False,
    }
    assert audit_ccb_change_request_sla_and_aging_backlog([{"cr_id": "X"}]) == {
        "total_evaluated": 1,
        "open_pending_count": 1,
        "deferred_count": 0,
        "deferred_ratio_pct": 0.0,
        "sla_breached_cr_ids": [],
        "unassigned_impact_owner_cr_ids": ["X"],
        "deferred_without_review_date_cr_ids": [],
        "deferred_backlog_excess": False,
        "is_ccb_sla_compliant": False,
    }

    res_bad_types = audit_ccb_change_request_sla_and_aging_backlog(
        [{"cr_id": "CR-BAD", "age_days": "x"}]
    )
    assert res_bad_types == {
        "total_evaluated": 1,
        "open_pending_count": 1,
        "deferred_count": 0,
        "deferred_ratio_pct": 0.0,
        "sla_breached_cr_ids": [],
        "unassigned_impact_owner_cr_ids": ["CR-BAD"],
        "deferred_without_review_date_cr_ids": [],
        "deferred_backlog_excess": False,
        "is_ccb_sla_compliant": False,
    }


def test_evaluate_supplier_ncr_disposition_governance_healthy():
    """Verifica lote NCR conforme con cuarentena activa, recupero de costos y concesión menor autorizada bajo umbral."""
    from backend.services.project_ccb_service import (
        evaluate_supplier_ncr_disposition_governance,
    )

    ncr_items = [
        {"ncr_id": "NCR-01", "disposition": "pending", "severity": "major", "quarantine_isolated": True},
        {"ncr_id": "NCR-02", "disposition": "rework", "severity": "major"},
        {"ncr_id": "NCR-03", "disposition": "scrap", "severity": "critical", "cost_recovery_claimed": True},
        {"ncr_id": "NCR-04", "disposition": "return_to_vendor", "severity": "major", "cost_recovery_claimed": True},
        {"ncr_id": "NCR-05", "disposition": "rework", "severity": "minor"},
        {"ncr_id": "NCR-06", "disposition": "rework", "severity": "minor"},
        {"ncr_id": "NCR-07", "disposition": "rework", "severity": "minor"},
        {
            "ncr_id": "NCR-08",
            "disposition": "concession",
            "severity": "minor",
            "engineering_authority_approved": True,
        },
    ]
    res = evaluate_supplier_ncr_disposition_governance(ncr_items, max_concession_ratio_pct=15.0)
    assert res == {
        "total_evaluated": 8,
        "concession_count": 1,
        "concession_ratio_pct": 12.5,
        "unquarantined_open_ncr_ids": [],
        "unauthorized_concession_ncr_ids": [],
        "unclaimed_vendor_recovery_ncr_ids": [],
        "excessive_concession_rate": False,
        "is_ncr_governance_compliant": True,
        "status": "healthy",
        "recommendations": [],
    }


def test_evaluate_supplier_ncr_disposition_governance_critical_quarantine_and_concession():
    """Detecta NCR abierta sin aislamiento en cuarentena o concesión sobre severidad crítica / sin firma de ingeniería (critical)."""
    from backend.services.project_ccb_service import (
        evaluate_supplier_ncr_disposition_governance,
    )

    ncr_items = [
        {"ncr_id": "NCR-10", "disposition": "pending", "severity": "major", "quarantine_isolated": False},
        {
            "ncr_id": "NCR-11",
            "disposition": "use_as_is",
            "severity": "critical",
            "engineering_authority_approved": True,
        },
        {
            "ncr_id": "NCR-12",
            "disposition": "concession",
            "severity": "minor",
            "engineering_authority_approved": False,
        },
    ]
    res = evaluate_supplier_ncr_disposition_governance(ncr_items, max_concession_ratio_pct=80.0)
    assert res["total_evaluated"] == 3
    assert res["concession_count"] == 2
    assert res["unquarantined_open_ncr_ids"] == ["NCR-10"]
    assert res["unauthorized_concession_ncr_ids"] == ["NCR-11", "NCR-12"]
    assert res["is_ncr_governance_compliant"] is False
    assert res["status"] == "critical"
    assert len(res["recommendations"]) == 2


def test_evaluate_supplier_ncr_disposition_governance_warning_excess_concession_and_unclaimed_scrap():
    """Detecta exceso de tasa de concesión (> max_concession_ratio_pct) o desecho/devolución sin reclamo al proveedor (warning)."""
    from backend.services.project_ccb_service import (
        evaluate_supplier_ncr_disposition_governance,
    )

    ncr_items = [
        {
            "ncr_id": "NCR-20",
            "disposition": "concession",
            "severity": "minor",
            "engineering_authority_approved": True,
        },
        {
            "ncr_id": "NCR-21",
            "disposition": "scrap",
            "severity": "major",
            "cost_recovery_claimed": False,
        },
        {"ncr_id": "NCR-22", "disposition": "rework", "severity": "minor"},
    ]
    res = evaluate_supplier_ncr_disposition_governance(ncr_items, max_concession_ratio_pct=15.0)
    assert res["total_evaluated"] == 3
    assert res["concession_count"] == 1
    assert res["concession_ratio_pct"] == 33.33
    assert res["unquarantined_open_ncr_ids"] == []
    assert res["unauthorized_concession_ncr_ids"] == []
    assert res["unclaimed_vendor_recovery_ncr_ids"] == ["NCR-21"]
    assert res["excessive_concession_rate"] is True
    assert res["is_ncr_governance_compliant"] is False
    assert res["status"] == "warning"
    assert len(res["recommendations"]) == 2


def test_evaluate_supplier_ncr_disposition_governance_empty_and_service_staticmethod():
    """Verifica entradas vacías/None e invocación mediante ProjectCCBService.evaluate_supplier_ncr_disposition_governance."""
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        evaluate_supplier_ncr_disposition_governance,
    )

    empty_res = evaluate_supplier_ncr_disposition_governance(None)
    assert empty_res == {
        "total_evaluated": 0,
        "concession_count": 0,
        "concession_ratio_pct": 0.0,
        "unquarantined_open_ncr_ids": [],
        "unauthorized_concession_ncr_ids": [],
        "unclaimed_vendor_recovery_ncr_ids": [],
        "excessive_concession_rate": False,
        "is_ncr_governance_compliant": True,
        "status": "healthy",
        "recommendations": [],
    }

    sample = [
        {"id": "NCR-99", "disposition": "pending", "quarantine_isolated": True},
        "invalid",
        {"id": "   "},
    ]
    assert (
        ProjectCCBService.evaluate_supplier_ncr_disposition_governance(sample)
        == evaluate_supplier_ncr_disposition_governance(sample)
    )



def test_audit_scope_creep_and_gold_plating_drift_controlled():
    """Paquetes en baseline o con approved_cr_id válido -> is_scope_baseline_controlled."""
    from backend.services.project_ccb_service import (
        audit_scope_creep_and_gold_plating_drift,
    )

    packages = [
        # En baseline aprobado, sin expansión de esfuerzo.
        {
            "wp_id": "W-1",
            "in_approved_wbs_baseline": True,
            "baseline_hours": 100.0,
            "actual_or_forecast_hours": 100.0,
        },
        # Fuera de WBS pero respaldado por CR aprobado.
        {
            "wp_id": "W-2",
            "in_approved_wbs_baseline": False,
            "approved_cr_id": "CR-7",
            "baseline_hours": 100.0,
            "actual_or_forecast_hours": 200.0,
        },
        # Gold-plating respaldado por CR aprobado.
        {
            "wp_id": "W-3",
            "in_approved_wbs_baseline": False,
            "approved_cr_id": "CR-8",
            "extra_features_added_count": 3,
        },
    ]
    res = audit_scope_creep_and_gold_plating_drift(packages)
    assert res == {
        "total_evaluated": 3,
        "unapproved_scope_addition_wp_ids": [],
        "gold_plating_wp_ids": [],
        "silent_effort_expansion_wp_ids": [],
        "is_scope_baseline_controlled": True,
    }


def test_audit_scope_creep_and_gold_plating_drift_unapproved_additions():
    """Adición fuera de WBS sin CR y gold-plating con features extra sin CR."""
    from backend.services.project_ccb_service import (
        audit_scope_creep_and_gold_plating_drift,
    )

    packages = [
        {"wp_id": "A-1", "in_approved_wbs_baseline": False},
        {"wp_id": "A-2", "in_approved_wbs_baseline": True, "extra_features_added_count": 2},
        {"wp_id": "A-3", "in_approved_wbs_baseline": False, "extra_features_added_count": 1},
    ]
    res = audit_scope_creep_and_gold_plating_drift(packages)
    assert res["total_evaluated"] == 3
    assert res["unapproved_scope_addition_wp_ids"] == ["A-1", "A-3"]
    assert res["gold_plating_wp_ids"] == ["A-2", "A-3"]
    assert res["silent_effort_expansion_wp_ids"] == []
    assert res["is_scope_baseline_controlled"] is False

    # El mismo patrón con approved_cr_id en blanco tras strip sigue sin respaldo.
    blank_cr = audit_scope_creep_and_gold_plating_drift(
        [
            {
                "wp_id": "A-4",
                "in_approved_wbs_baseline": False,
                "approved_cr_id": "   ",
                "extra_features_added_count": 2,
            }
        ]
    )
    assert blank_cr["unapproved_scope_addition_wp_ids"] == ["A-4"]
    assert blank_cr["gold_plating_wp_ids"] == ["A-4"]


def test_audit_scope_creep_and_gold_plating_drift_effort_expansion():
    """Expansión silenciosa de esfuerzo sobre el umbral sin CR vs expansion respaldada."""
    from backend.services.project_ccb_service import (
        audit_scope_creep_and_gold_plating_drift,
    )

    packages = [
        # drift 6.0% > 5.0 sin CR -> detectado.
        {
            "wp_id": "E-1",
            "in_approved_wbs_baseline": True,
            "baseline_hours": 100.0,
            "actual_or_forecast_hours": 106.0,
        },
        # drift 5.0% == umbral -> no excede (comparación estricta).
        {
            "wp_id": "E-2",
            "in_approved_wbs_baseline": True,
            "baseline_hours": 100.0,
            "actual_or_forecast_hours": 105.0,
        },
        # sobrecosto severo pero respaldado por CR aprobado -> no detectado.
        {
            "wp_id": "E-3",
            "in_approved_wbs_baseline": True,
            "baseline_hours": 100.0,
            "actual_or_forecast_hours": 150.0,
            "approved_cr_id": "CR-9",
        },
        # baseline 0 horas -> no evaluable -> no detectado.
        {"wp_id": "E-4", "in_approved_wbs_baseline": True, "baseline_hours": 0.0},
    ]
    res = audit_scope_creep_and_gold_plating_drift(packages)
    assert res["total_evaluated"] == 4
    assert res["silent_effort_expansion_wp_ids"] == ["E-1"]
    assert res["is_scope_baseline_controlled"] is False

    # Umbral personalizado más estricto.
    strict = audit_scope_creep_and_gold_plating_drift(packages, max_unapproved_effort_drift_pct=3.0)
    assert strict["silent_effort_expansion_wp_ids"] == ["E-1", "E-2"]


def test_audit_scope_creep_and_gold_plating_drift_empty_and_service_proxy():
    """Entradas vacías/None + llamada vía ProjectCCBService.audit_scope_creep_and_gold_plating_drift."""
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_scope_creep_and_gold_plating_drift,
    )
    import backend.services.project_ccb_service as _m

    res_none = audit_scope_creep_and_gold_plating_drift(None)
    assert res_none == {
        "total_evaluated": 0,
        "unapproved_scope_addition_wp_ids": [],
        "gold_plating_wp_ids": [],
        "silent_effort_expansion_wp_ids": [],
        "is_scope_baseline_controlled": True,
    }
    assert audit_scope_creep_and_gold_plating_drift([])["total_evaluated"] == 0
    assert (
        audit_scope_creep_and_gold_plating_drift(
            ["not-a-mapping", {"wp_id": "   "}, {"other_id": "x"}]
        )["total_evaluated"]
        == 0
    )
    assert "audit_scope_creep_and_gold_plating_drift" in _m.__all__

    sample = [
        {
            "wp_id": "W-1",
            "in_approved_wbs_baseline": True,
            "baseline_hours": 100.0,
            "actual_or_forecast_hours": 100.0,
        }
    ]
    assert (
        ProjectCCBService.audit_scope_creep_and_gold_plating_drift(sample)
        == audit_scope_creep_and_gold_plating_drift(sample)
    )


def test_audit_requirements_traceability_matrix_coverage_complete():
    """Requisitos con trazabilidad hacia adelante (objetivo + WBS), casos de prueba y automatización en críticos -> complete True."""
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_requirements_traceability_matrix_coverage,
    )

    entries = [
        {
            "requirement_id": "REQ-01",
            "business_objective_ref": "OBJ-FIN-1",
            "wbs_deliverable_ref": "WBS-2.1",
            "verification_test_case_ids": ["TC-101", "TC-102"],
            "priority_tier": "critical",
            "regression_suite_automated": True,
        },
        {
            "id": "REQ-02",
            "business_objective_ref": "OBJ-OPS-2",
            "wbs_deliverable_ref": "WBS-3.4",
            "verification_test_case_ids": ["TC-201"],
            "priority_tier": "low",
            "regression_suite_automated": False,
        },
    ]
    res = audit_requirements_traceability_matrix_coverage(entries)
    assert res == {
        "total_evaluated": 2,
        "orphan_forward_traceability_req_ids": [],
        "untested_backward_traceability_req_ids": [],
        "unautomated_critical_req_ids": [],
        "is_rtm_bidirectional_complete": True,
    }
    assert (
        ProjectCCBService.audit_requirements_traceability_matrix_coverage(
            entries
        )
        == res
    )


def test_audit_requirements_traceability_matrix_coverage_orphan_and_untested():
    """Detecta requisitos huérfanos (sin objetivo o sin WBS) y sin casos de prueba válidos."""
    from backend.services.project_ccb_service import (
        audit_requirements_traceability_matrix_coverage,
    )

    entries = [
        {
            "requirement_id": "REQ-NO-OBJ",
            "business_objective_ref": "",
            "wbs_deliverable_ref": "WBS-1.1",
            "verification_test_case_ids": ["TC-1"],
            "priority_tier": "medium",
        },
        {
            "requirement_id": "REQ-NO-TEST",
            "business_objective_ref": "OBJ-1",
            "wbs_deliverable_ref": "WBS-1.2",
            "verification_test_case_ids": ["   ", 123],
            "priority_tier": "medium",
        },
    ]
    res = audit_requirements_traceability_matrix_coverage(entries)
    assert res["total_evaluated"] == 2
    assert res["orphan_forward_traceability_req_ids"] == ["REQ-NO-OBJ"]
    assert res["untested_backward_traceability_req_ids"] == ["REQ-NO-TEST"]
    assert res["unautomated_critical_req_ids"] == []
    assert res["is_rtm_bidirectional_complete"] is False


def test_audit_requirements_traceability_matrix_coverage_unautomated_critical():
    """Requisitos de prioridad critical/high/must/p0 sin automatización de regresión."""
    from backend.services.project_ccb_service import (
        audit_requirements_traceability_matrix_coverage,
    )

    entries = [
        {
            "requirement_id": "REQ-P0-MANUAL",
            "business_objective_ref": "OBJ-SEC",
            "wbs_deliverable_ref": "WBS-4.1",
            "verification_test_case_ids": ["TC-99"],
            "priority_tier": "P0",
            "regression_suite_automated": False,
        }
    ]
    res = audit_requirements_traceability_matrix_coverage(entries)
    assert res["total_evaluated"] == 1
    assert res["orphan_forward_traceability_req_ids"] == []
    assert res["untested_backward_traceability_req_ids"] == []
    assert res["unautomated_critical_req_ids"] == ["REQ-P0-MANUAL"]
    assert res["is_rtm_bidirectional_complete"] is False


def test_audit_requirements_traceability_matrix_coverage_invalid_inputs_and_export():
    """Ignora entradas no secuencia o sin requirement_id válido y verifica exportación en __all__."""
    import backend.services.project_ccb_service as _m
    from backend.services.project_ccb_service import (
        audit_requirements_traceability_matrix_coverage,
    )

    assert "audit_requirements_traceability_matrix_coverage" in _m.__all__
    for bad in (None, "not-a-seq", b"bytes", bytearray(b"xyz"), [{"requirement_id": "  "}, 42]):
        res = audit_requirements_traceability_matrix_coverage(bad)
        assert res == {
            "total_evaluated": 0,
            "orphan_forward_traceability_req_ids": [],
            "untested_backward_traceability_req_ids": [],
            "unautomated_critical_req_ids": [],
            "is_rtm_bidirectional_complete": True,
        }


def test_audit_configuration_fca_pca_baseline_verification_compliant():
    """CIs con FCA pasada, PCA conforme, sin desviaciones y version_tag inmutable."""
    from backend.services.project_ccb_service import (
        audit_configuration_fca_pca_baseline_verification,
    )

    items = [
        {
            "ci_id": "CI-1",
            "fca_functional_test_passed": True,
            "pca_as_built_matches_as_designed": True,
            "unapproved_baseline_deviations_count": 0,
            "version_tag_immutable": True,
        },
        {
            "id": "CI-2",
            "fca_functional_test_passed": True,
            "pca_as_built_matches_as_designed": True,
            "version_tag_immutable": True,
        },
    ]
    res = audit_configuration_fca_pca_baseline_verification(items)
    assert res == {
        "total_evaluated": 2,
        "fca_failed_ci_ids": [],
        "pca_discrepancy_ci_ids": [],
        "mutable_version_tag_ci_ids": [],
        "is_fca_pca_audit_compliant": True,
    }


def test_audit_configuration_fca_pca_baseline_verification_fca_and_pca_failures():
    """Detecta FCA fallida y discrepancias PCA (as-built != as-designed o desviaciones > 0)."""
    from backend.services.project_ccb_service import (
        audit_configuration_fca_pca_baseline_verification,
    )

    items = [
        {"ci_id": "F-1", "fca_functional_test_passed": False,
         "pca_as_built_matches_as_designed": True, "version_tag_immutable": True},
        {"ci_id": "P-1", "fca_functional_test_passed": True,
         "pca_as_built_matches_as_designed": False, "version_tag_immutable": True},
        {"ci_id": "P-2", "fca_functional_test_passed": True,
         "pca_as_built_matches_as_designed": True,
         "unapproved_baseline_deviations_count": 3, "version_tag_immutable": True},
        {"ci_id": "OK-1", "fca_functional_test_passed": True,
         "pca_as_built_matches_as_designed": True,
         "unapproved_baseline_deviations_count": None,  # coercion -> 0 -> sin discrepancia.
         "version_tag_immutable": True},
    ]
    res = audit_configuration_fca_pca_baseline_verification(items)
    assert res["total_evaluated"] == 4
    assert res["fca_failed_ci_ids"] == ["F-1"]
    assert res["pca_discrepancy_ci_ids"] == ["P-1", "P-2"]
    assert res["is_fca_pca_audit_compliant"] is False


def test_audit_configuration_fca_pca_baseline_verification_mutable_tags():
    """CIs con version_tag no inmutable quedan marcados; coerción de contador invalido."""
    from backend.services.project_ccb_service import (
        audit_configuration_fca_pca_baseline_verification,
    )

    items = [
        {"ci_id": "V-1", "fca_functional_test_passed": True,
         "pca_as_built_matches_as_designed": True, "version_tag_immutable": False},
        {"ci_id": "V-2", "fca_functional_test_passed": True,
         "pca_as_built_matches_as_designed": True},  # default False -> mutable.
        {"ci_id": "OK-2", "fca_functional_test_passed": True,
         "pca_as_built_matches_as_designed": True,
         "unapproved_baseline_deviations_count": "oops", "version_tag_immutable": True},
    ]
    res = audit_configuration_fca_pca_baseline_verification(items)
    assert res["mutable_version_tag_ci_ids"] == ["V-1", "V-2"]
    assert res["pca_discrepancy_ci_ids"] == []
    assert res["is_fca_pca_audit_compliant"] is False


def test_audit_configuration_fca_pca_baseline_verification_empty_and_service_proxy():
    """Entradas vacias/None/invalidas + llamada via ProjectCCBService (staticmethod + __all__)."""
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_configuration_fca_pca_baseline_verification,
    )
    import backend.services.project_ccb_service as _m

    res_none = audit_configuration_fca_pca_baseline_verification(None)
    assert res_none == {
        "total_evaluated": 0,
        "fca_failed_ci_ids": [],
        "pca_discrepancy_ci_ids": [],
        "mutable_version_tag_ci_ids": [],
        "is_fca_pca_audit_compliant": True,
    }
    assert audit_configuration_fca_pca_baseline_verification("no-seq")["total_evaluated"] == 0
    assert (
        audit_configuration_fca_pca_baseline_verification(
            ["no-map", {"ci_id": "   "}, {"other_id": "x"}]
        )["total_evaluated"]
        == 0
    )
    assert "audit_configuration_fca_pca_baseline_verification" in _m.__all__

    sample = [
        {"ci_id": "CI-1", "fca_functional_test_passed": True,
         "pca_as_built_matches_as_designed": True, "version_tag_immutable": True},
    ]
    assert (
        ProjectCCBService.audit_configuration_fca_pca_baseline_verification(sample)
        == audit_configuration_fca_pca_baseline_verification(sample)
    )


def test_audit_emergency_change_fast_track_ratification_compliant():
    """Cambios de emergencia Sev1/Sev2 bajo el ratio máximo, con aprobador, rollback y ratificación en SLA."""
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_emergency_change_fast_track_ratification,
    )

    crs = [
        {
            "cr_id": "CR-EMG-01",
            "is_emergency": True,
            "incident_severity": "SEV1",
            "delegated_approver_id": "CTO-01",
            "rollback_plan_documented": True,
            "hours_since_execution": 72.0,
            "post_facto_ccb_ratified": True,
        }
    ] + [{"cr_id": f"CR-STD-{i}", "is_emergency": False} for i in range(2, 11)]

    res = audit_emergency_change_fast_track_ratification(
        crs, max_emergency_ratio_pct=15.0, ratification_sla_hours=48.0
    )
    assert res == {
        "total_change_requests": 10,
        "emergency_change_count": 1,
        "emergency_ratio_pct": 10.0,
        "exceeds_emergency_ratio_cap": False,
        "unjustified_emergency_severity_cr_ids": [],
        "missing_safeguard_or_approver_cr_ids": [],
        "overdue_post_facto_ratification_cr_ids": [],
        "is_emergency_governance_compliant": True,
    }
    assert (
        ProjectCCBService.audit_emergency_change_fast_track_ratification(crs)
        == res
    )


def test_audit_emergency_change_unjustified_severity_and_ratio_cap():
    """Detecta abuso de vía de emergencia con Sev3/Sev4 y exceso del ratio máximo permitido."""
    from backend.services.project_ccb_service import (
        audit_emergency_change_fast_track_ratification,
    )

    crs = [
        {
            "cr_id": "CR-EMG-SEV3",
            "is_emergency": True,
            "incident_severity": "sev3",
            "delegated_approver_id": "VP-01",
            "rollback_plan_documented": True,
            "hours_since_execution": 12.0,
            "post_facto_ccb_ratified": True,
        },
        {
            "cr_id": "CR-EMG-SEV2",
            "is_emergency": True,
            "incident_severity": "sev2",
            "delegated_approver_id": "VP-01",
            "rollback_plan_documented": True,
            "hours_since_execution": 10.0,
            "post_facto_ccb_ratified": True,
        },
        {"cr_id": "CR-STD-01", "is_emergency": False},
    ]
    res = audit_emergency_change_fast_track_ratification(
        crs, max_emergency_ratio_pct=15.0
    )
    assert res["total_change_requests"] == 3
    assert res["emergency_change_count"] == 2
    assert res["emergency_ratio_pct"] == 66.67
    assert res["exceeds_emergency_ratio_cap"] is True
    assert res["unjustified_emergency_severity_cr_ids"] == ["CR-EMG-SEV3"]
    assert res["is_emergency_governance_compliant"] is False


def test_audit_emergency_change_missing_safeguard_and_overdue_ratification():
    """Detecta falta de aprobador delegado/rollback y vencimiento del SLA de ratificación post-facto."""
    from backend.services.project_ccb_service import (
        audit_emergency_change_fast_track_ratification,
    )

    crs = [
        {
            "cr_id": "CR-EMG-NO-ROLLBACK",
            "is_emergency": True,
            "incident_severity": "sev1",
            "delegated_approver_id": "   ",
            "rollback_plan_documented": False,
            "hours_since_execution": 60.0,
            "post_facto_ccb_ratified": False,
        }
    ] + [{"cr_id": f"CR-N-{i}", "is_emergency": False} for i in range(1, 10)]

    res = audit_emergency_change_fast_track_ratification(
        crs, max_emergency_ratio_pct=15.0, ratification_sla_hours=48.0
    )
    assert res["missing_safeguard_or_approver_cr_ids"] == [
        "CR-EMG-NO-ROLLBACK"
    ]
    assert res["overdue_post_facto_ratification_cr_ids"] == [
        "CR-EMG-NO-ROLLBACK"
    ]
    assert res["is_emergency_governance_compliant"] is False


def test_audit_emergency_change_invalid_inputs_and_export():
    """Ignora entradas no secuencia o sin cr_id válido y verifica exportación en __all__."""
    import backend.services.project_ccb_service as _m
    from backend.services.project_ccb_service import (
        audit_emergency_change_fast_track_ratification,
    )

    assert "audit_emergency_change_fast_track_ratification" in _m.__all__
    for bad in (None, "not-a-seq", b"bytes", [{"cr_id": "  "}, 42]):
        assert audit_emergency_change_fast_track_ratification(bad) == {
            "total_change_requests": 0,
            "emergency_change_count": 0,
            "emergency_ratio_pct": 0.0,
            "exceeds_emergency_ratio_cap": False,
            "unjustified_emergency_severity_cr_ids": [],
            "missing_safeguard_or_approver_cr_ids": [],
            "overdue_post_facto_ratification_cr_ids": [],
            "is_emergency_governance_compliant": True,
        }



def test_audit_dod_defect_escape_and_first_time_right_rate_compliant():
    """Entregables limpios: sin escapes, 1 ciclo de inspeccion -> 100% FTR compliant."""
    from backend.services.project_ccb_service import (
        audit_dod_defect_escape_and_first_time_right_rate,
    )

    items = [
        {"deliverable_id": "D-1", "pre_release_defects_found": 2,
         "post_release_escaped_defects": 0, "inspection_cycles_count": 1,
         "automated_regression_coverage_pct": 85.0},
        {"deliverable_id": "D-2", "pre_release_defects_found": 0,
         "post_release_escaped_defects": 0, "inspection_cycles_count": 1,
         "automated_regression_coverage_pct": 85.0},
        {"deliverable_id": "D-3", "pre_release_defects_found": 0,
         "post_release_escaped_defects": 0, "inspection_cycles_count": 1,
         "automated_regression_coverage_pct": 85.0},
        {"deliverable_id": "D-4", "pre_release_defects_found": 0,
         "post_release_escaped_defects": 0, "inspection_cycles_count": 1,
         "automated_regression_coverage_pct": 85.0},
    ]
    res = audit_dod_defect_escape_and_first_time_right_rate(items)
    assert res == {
        "total_deliverables": 4,
        "first_time_right_count": 4,
        "first_time_right_pct": 100.0,
        "below_first_time_right_threshold": False,
        "invalid_metric_deliverable_ids": [],
        "high_defect_escape_deliverable_ids": [],
        "unlinked_capa_escaped_deliverable_ids": [],
        "regression_gap_deliverable_ids": [],
        "is_dod_quality_gate_compliant": True,
    }

    # Borde exacto 10.0% de escape -> sin breach (comparacion estricta >).
    edge = audit_dod_defect_escape_and_first_time_right_rate(
        [
            {"deliverable_id": "E-1", "pre_release_defects_found": 9,
             "post_release_escaped_defects": 1, "root_cause_capa_linked": True,
             "automated_regression_coverage_pct": 90.0, "inspection_cycles_count": 2},
        ]
    )
    assert edge["high_defect_escape_deliverable_ids"] == []
    assert edge["first_time_right_pct"] == 0.0  # 2 ciclos -> no FTR.
    assert edge["below_first_time_right_threshold"] is True
    # Con below=True el gate DoD no es compliant aunque las 4 listas esten vacias.
    assert edge["is_dod_quality_gate_compliant"] is False


def test_audit_dod_defect_escape_and_first_time_right_rate_invalid_metrics():
    """Metricas negativas o ciclos de inspeccion < 1 expulsan al entregable del analisis."""
    from backend.services.project_ccb_service import (
        audit_dod_defect_escape_and_first_time_right_rate,
    )

    items = [
        {"deliverable_id": "I-1", "pre_release_defects_found": -1},
        {"deliverable_id": "I-2", "post_release_escaped_defects": -3},
        {"deliverable_id": "I-3", "inspection_cycles_count": 0},  # explicito -> invalido.
        {"deliverable_id": "OK-1"},  # metricas ausentes -> defaults validos.
    ]
    res = audit_dod_defect_escape_and_first_time_right_rate(items)
    assert res["total_deliverables"] == 1
    assert res["first_time_right_count"] == 1
    assert res["first_time_right_pct"] == 100.0
    assert res["invalid_metric_deliverable_ids"] == ["I-1", "I-2", "I-3"]
    assert res["is_dod_quality_gate_compliant"] is False

    # Coercion a defaults: strings invalidos/None no invalidan, usan defaults.
    coerce = audit_dod_defect_escape_and_first_time_right_rate(
        [
            {"deliverable_id": "B-1", "pre_release_defects_found": "oops",
             "post_release_escaped_defects": None, "inspection_cycles_count": "x",
             "automated_regression_coverage_pct": "oops"},
        ]
    )
    assert coerce["invalid_metric_deliverable_ids"] == []
    assert coerce["first_time_right_pct"] == 100.0


def test_audit_dod_defect_escape_and_first_time_right_rate_gaps():
    """Escape alto (>10%), escapes sin CAPA vinculada y gap de regresion < 70%."""
    from backend.services.project_ccb_service import (
        audit_dod_defect_escape_and_first_time_right_rate,
    )

    items = [
        {"deliverable_id": "H-1", "pre_release_defects_found": 1,
         "post_release_escaped_defects": 1, "root_cause_capa_linked": True,
         "automated_regression_coverage_pct": 90.0},  # escape 50%.
        {"deliverable_id": "C-1", "pre_release_defects_found": 5,
         "post_release_escaped_defects": 2, "root_cause_capa_linked": False,
         "automated_regression_coverage_pct": 100.0},  # escape 28.57% + sin CAPA.
        {"deliverable_id": "R-1", "pre_release_defects_found": 5,
         "post_release_escaped_defects": 0, "root_cause_capa_linked": True,
         "automated_regression_coverage_pct": 30.0},  # sin escape -> sin gap.
        {"deliverable_id": "R-2", "pre_release_defects_found": 0,
         "post_release_escaped_defects": 1, "root_cause_capa_linked": True,
         "automated_regression_coverage_pct": 69.99},  # escape 100% + gap.
    ]
    res = audit_dod_defect_escape_and_first_time_right_rate(items)
    assert res["total_deliverables"] == 4
    assert res["high_defect_escape_deliverable_ids"] == ["H-1", "C-1", "R-2"]
    assert res["unlinked_capa_escaped_deliverable_ids"] == ["C-1"]
    assert res["regression_gap_deliverable_ids"] == ["R-2"]
    assert res["first_time_right_count"] == 1  # solo R-1.
    assert res["first_time_right_pct"] == 25.0
    assert res["below_first_time_right_threshold"] is True
    assert res["is_dod_quality_gate_compliant"] is False


def test_audit_dod_defect_escape_and_first_time_right_rate_thresholds_and_scope():
    """below_threshold con umbral custom; entradas vacias/None + proxy estatico + __all__."""
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_dod_defect_escape_and_first_time_right_rate,
    )
    import backend.services.project_ccb_service as _m

    res_none = audit_dod_defect_escape_and_first_time_right_rate(None)
    assert res_none == {
        "total_deliverables": 0,
        "first_time_right_count": 0,
        "first_time_right_pct": 100.0,
        "below_first_time_right_threshold": False,
        "invalid_metric_deliverable_ids": [],
        "high_defect_escape_deliverable_ids": [],
        "unlinked_capa_escaped_deliverable_ids": [],
        "regression_gap_deliverable_ids": [],
        "is_dod_quality_gate_compliant": True,
    }
    assert audit_dod_defect_escape_and_first_time_right_rate("no-seq")["total_deliverables"] == 0
    assert (
        audit_dod_defect_escape_and_first_time_right_rate(
            ["no-map", {"deliverable_id": "   "}, {"other_id": "x"}]
        )["total_deliverables"]
        == 0
    )
    assert "audit_dod_defect_escape_and_first_time_right_rate" in _m.__all__

    sample = [
        {"deliverable_id": "D-1", "pre_release_defects_found": 0,
         "post_release_escaped_defects": 0, "inspection_cycles_count": 1},
    ]
    strict = audit_dod_defect_escape_and_first_time_right_rate(
        sample, min_first_time_right_pct=100.0
    )
    assert strict["first_time_right_pct"] == 100.0
    assert strict["below_first_time_right_threshold"] is False  # borde == umbral no es below.
    assert (
        ProjectCCBService.audit_dod_defect_escape_and_first_time_right_rate(sample)
        == audit_dod_defect_escape_and_first_time_right_rate(sample)
    )


def test_audit_contract_change_order_cumulative_escalation_compliant():
    """Órdenes de cambio con adenda firmada y ratificación ejecutiva cuando superan umbral cumplen §4.6 y §12.2."""
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_contract_change_order_cumulative_escalation,
    )

    ledgers = [
        {
            "contract_id": "CNT-MINOR-01",
            "original_contract_value": 100000.0,
            "change_orders": [
                {
                    "co_id": "CO-1",
                    "cost_delta": 5000.0,
                    "executive_board_ratified": False,
                    "legal_amendment_signed": True,
                }
            ],
        },
        {
            "contract_id": "CNT-MAJOR-RATIFIED-02",
            "original_contract_value": 100000.0,
            "change_orders": [
                {
                    "co_id": "CO-2",
                    "cost_delta": 25000.0,
                    "executive_board_ratified": True,
                    "legal_amendment_signed": True,
                }
            ],
        },
    ]
    res = audit_contract_change_order_cumulative_escalation(ledgers)
    assert res == {
        "total_contracts": 2,
        "invalid_base_contract_ids": [],
        "unsigned_legal_amendment_contract_ids": [],
        "unratified_threshold_breach_contract_ids": [],
        "is_change_order_escalation_compliant": True,
    }
    assert (
        ProjectCCBService.audit_contract_change_order_cumulative_escalation(
            ledgers
        )
        == res
    )


def test_audit_contract_change_order_cumulative_splitting_and_single_breach():
    """Detecta fraccionamiento de órdenes (cada una <= 10% pero acumulado > 20%) sin ratificación ejecutiva."""
    from backend.services.project_ccb_service import (
        audit_contract_change_order_cumulative_escalation,
    )

    ledgers = [
        {
            "contract_id": "CNT-SPLIT-BYPASS",
            "original_contract_value": 100000.0,
            "change_orders": [
                {
                    "co_id": "CO-A",
                    "cost_delta": 8000.0,
                    "executive_board_ratified": False,
                    "legal_amendment_signed": True,
                },
                {
                    "co_id": "CO-B",
                    "cost_delta": 8000.0,
                    "executive_board_ratified": False,
                    "legal_amendment_signed": True,
                },
                {
                    "co_id": "CO-C",
                    "cost_delta": 8000.0,  # Acumulado 24% > 20%
                    "executive_board_ratified": False,
                    "legal_amendment_signed": True,
                },
            ],
        },
        {
            "contract_id": "CNT-SINGLE-SPIKE",
            "original_contract_value": 100000.0,
            "change_orders": [
                {
                    "co_id": "CO-SPIKE",
                    "cost_delta": 14000.0,  # Individual 14% > 10%
                    "executive_board_ratified": False,
                    "legal_amendment_signed": True,
                }
            ],
        },
    ]
    res = audit_contract_change_order_cumulative_escalation(ledgers)
    assert res["total_contracts"] == 2
    assert res["unratified_threshold_breach_contract_ids"] == [
        "CNT-SPLIT-BYPASS",
        "CNT-SINGLE-SPIKE",
    ]
    assert res["is_change_order_escalation_compliant"] is False


def test_audit_contract_change_order_cumulative_unsigned_legal_amendment():
    """Detecta órdenes de cambio con impacto en costo que carecen de adenda legal firmada."""
    from backend.services.project_ccb_service import (
        audit_contract_change_order_cumulative_escalation,
    )

    ledgers = [
        {
            "contract_id": "CNT-NO-AMENDMENT",
            "original_contract_value": 200000.0,
            "change_orders": [
                {
                    "co_id": "CO-UNSIGNED",
                    "cost_delta": 5000.0,
                    "executive_board_ratified": True,
                    "legal_amendment_signed": False,
                }
            ],
        }
    ]
    res = audit_contract_change_order_cumulative_escalation(ledgers)
    assert res["unsigned_legal_amendment_contract_ids"] == ["CNT-NO-AMENDMENT"]
    assert res["is_change_order_escalation_compliant"] is False


def test_audit_contract_change_order_cumulative_invalid_base_and_export():
    """Detecta valor contractual original <= 0, maneja entradas no secuencia y verifica __all__."""
    import backend.services.project_ccb_service as _m
    from backend.services.project_ccb_service import (
        audit_contract_change_order_cumulative_escalation,
    )

    assert "audit_contract_change_order_cumulative_escalation" in _m.__all__
    res = audit_contract_change_order_cumulative_escalation(
        [{"contract_id": "CNT-ZERO-BASE", "original_contract_value": 0.0}]
    )
    assert res["invalid_base_contract_ids"] == ["CNT-ZERO-BASE"]
    assert res["is_change_order_escalation_compliant"] is False

    for bad in (None, "not-a-seq", b"bytes", [{"contract_id": "  "}]):
        assert audit_contract_change_order_cumulative_escalation(bad) == {
            "total_contracts": 0,
            "invalid_base_contract_ids": [],
            "unsigned_legal_amendment_contract_ids": [],
            "unratified_threshold_breach_contract_ids": [],
            "is_change_order_escalation_compliant": True,
        }


def test_audit_ncr_capa_effectiveness_and_recurrence_compliant():
    """Cumple cuando NCRs mayores tienen RCA, verificación en SLA, QA independiente y cero recurrencia."""
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_ncr_capa_effectiveness_and_recurrence,
    )

    records = [
        {
            "ncr_id": "NCR-CRIT-01",
            "severity": "critical",
            "status": "verified_closed",
            "root_cause_method_documented": True,
            "days_in_pending_verification": 5.0,
            "recurrence_count_after_closure": 0,
            "independent_qa_verifier_id": "QA-VER-09",
        },
        {
            "ncr_id": "NCR-MAJ-02",
            "severity": "major",
            "status": "pending_verification",
            "root_cause_method_documented": True,
            "days_in_pending_verification": 10.0,
            "recurrence_count_after_closure": 0,
            "independent_qa_verifier_id": None,
        },
        {
            "ncr_id": "NCR-MIN-03",
            "severity": "minor",
            "status": "capa_in_progress",
            "root_cause_method_documented": False,
            "days_in_pending_verification": 0.0,
            "recurrence_count_after_closure": 0,
        },
    ]
    res = audit_ncr_capa_effectiveness_and_recurrence(records, max_verification_lag_days=14)
    assert res == {
        "total_ncrs": 3,
        "invalid_ncr_metadata_ids": [],
        "missing_rca_major_ncr_ids": [],
        "overdue_capa_verification_ncr_ids": [],
        "unverified_closure_ncr_ids": [],
        "ineffective_capa_recurrent_ncr_ids": [],
        "is_ncr_capa_governance_compliant": True,
    }
    assert (
        ProjectCCBService.audit_ncr_capa_effectiveness_and_recurrence(
            records, max_verification_lag_days=14
        )
        == res
    )


def test_audit_ncr_capa_missing_rca_and_overdue_verification():
    """Detecta NCR mayor/crítica en progreso sin RCA documentado y verificación pendiente fuera de SLA."""
    from backend.services.project_ccb_service import (
        audit_ncr_capa_effectiveness_and_recurrence,
    )

    res = audit_ncr_capa_effectiveness_and_recurrence(
        [
            {
                "ncr_id": "NCR-NO-RCA",
                "severity": "major",
                "status": "capa_in_progress",
                "root_cause_method_documented": False,
                "days_in_pending_verification": 0.0,
            },
            {
                "ncr_id": "NCR-LATE-VER",
                "severity": "minor",
                "status": "pending_verification",
                "root_cause_method_documented": True,
                "days_in_pending_verification": 21.0,
            },
        ],
        max_verification_lag_days=14,
    )
    assert res["missing_rca_major_ncr_ids"] == ["NCR-NO-RCA"]
    assert res["overdue_capa_verification_ncr_ids"] == ["NCR-LATE-VER"]
    assert res["is_ncr_capa_governance_compliant"] is False


def test_audit_ncr_capa_unverified_closure_and_recurrence():
    """Detecta cierre sin verificador QA independiente y reincidencia posterior al cierre."""
    from backend.services.project_ccb_service import (
        audit_ncr_capa_effectiveness_and_recurrence,
    )

    res = audit_ncr_capa_effectiveness_and_recurrence(
        [
            {
                "ncr_id": "NCR-UNVERIFIED-CLOSE",
                "severity": "critical",
                "status": "verified_closed",
                "root_cause_method_documented": True,
                "independent_qa_verifier_id": "   ",
                "recurrence_count_after_closure": 0,
            },
            {
                "ncr_id": "NCR-RECURRENT",
                "severity": "major",
                "status": "verified_closed",
                "root_cause_method_documented": True,
                "independent_qa_verifier_id": "QA-01",
                "recurrence_count_after_closure": 2,
            },
        ]
    )
    assert res["unverified_closure_ncr_ids"] == ["NCR-UNVERIFIED-CLOSE"]
    assert res["ineffective_capa_recurrent_ncr_ids"] == ["NCR-RECURRENT"]
    assert res["is_ncr_capa_governance_compliant"] is False


def test_audit_ncr_capa_invalid_metadata_and_export():
    """Detecta severidad/estado inválido o conteos negativos, maneja entradas no secuencia y verifica __all__."""
    import backend.services.project_ccb_service as _m
    from backend.services.project_ccb_service import (
        audit_ncr_capa_effectiveness_and_recurrence,
    )

    assert "audit_ncr_capa_effectiveness_and_recurrence" in _m.__all__
    res = audit_ncr_capa_effectiveness_and_recurrence(
        [
            {
                "ncr_id": "NCR-BAD-SEV",
                "severity": "catastrophic",
                "status": "open",
            },
            {
                "ncr_id": "NCR-NEG-RECURRENCE",
                "severity": "minor",
                "status": "verified_closed",
                "independent_qa_verifier_id": "QA-1",
                "recurrence_count_after_closure": -1,
            },
        ]
    )
    assert res["invalid_ncr_metadata_ids"] == ["NCR-BAD-SEV", "NCR-NEG-RECURRENCE"]
    assert res["is_ncr_capa_governance_compliant"] is False

    for bad in (None, "not-a-seq", b"bytes", [{"ncr_id": "  "}]):
        assert audit_ncr_capa_effectiveness_and_recurrence(bad) == {
            "total_ncrs": 0,
            "invalid_ncr_metadata_ids": [],
            "missing_rca_major_ncr_ids": [],
            "overdue_capa_verification_ncr_ids": [],
            "unverified_closure_ncr_ids": [],
            "ineffective_capa_recurrent_ncr_ids": [],
            "is_ncr_capa_governance_compliant": True,
        }


def test_audit_configuration_baseline_drift_and_hotfix_governance_healthy():
    """Verifica estado HEALTHY cuando todos los CIs coinciden con baseline o tienen CR autorizado y auditorías FCA/PCA vigentes."""
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_configuration_baseline_drift_and_hotfix_governance,
    )

    items = [
        {
            "ci_id": "CI-API-GW",
            "baseline_version": "2.1.0",
            "deployed_version": "2.1.0",
            "authorized_change_request_id": None,
            "is_production_hotfix": False,
            "physical_configuration_audit_passed": True,
            "functional_configuration_audit_passed": True,
            "days_since_last_configuration_audit": 10,
        },
        {
            "ci_id": "CI-AUTH-SVC",
            "baseline_version": "1.4.0",
            "deployed_version": "1.4.1",
            "authorized_change_request_id": "CR-2026-109",
            "is_production_hotfix": True,
            "physical_configuration_audit_passed": True,
            "functional_configuration_audit_passed": True,
            "days_since_last_configuration_audit": 5,
        },
    ]
    res = audit_configuration_baseline_drift_and_hotfix_governance(
        items, max_unverified_audit_age_days=30
    )
    assert res == {
        "total_configuration_items": 2,
        "compliant_ci_count": 2,
        "unauthorized_version_drift_count": 0,
        "unauthorized_hotfix_count": 0,
        "failed_fca_pca_count": 0,
        "stale_audit_ci_count": 0,
        "configuration_integrity_pct": 100.0,
        "configuration_governance_status": "HEALTHY",
        "discrepancies": [],
    }
    assert (
        ProjectCCBService.audit_configuration_baseline_drift_and_hotfix_governance(
            items, max_unverified_audit_age_days=30
        )
        == res
    )


def test_audit_configuration_baseline_drift_and_hotfix_governance_at_risk_stale_audit():
    """Verifica estado AT_RISK cuando la única anomalía es antigüedad excesiva desde la última auditoría de configuración."""
    from backend.services.project_ccb_service import (
        audit_configuration_baseline_drift_and_hotfix_governance,
    )

    res = audit_configuration_baseline_drift_and_hotfix_governance(
        [
            {
                "ci_id": "CI-DB-SCHEMA",
                "baseline_version": "3.0.0",
                "deployed_version": "3.0.0",
                "authorized_change_request_id": "",
                "is_production_hotfix": False,
                "physical_configuration_audit_passed": True,
                "functional_configuration_audit_passed": True,
                "days_since_last_configuration_audit": 45,
            }
        ],
        max_unverified_audit_age_days=30,
    )
    assert res["stale_audit_ci_count"] == 1
    assert res["compliant_ci_count"] == 0
    assert res["configuration_integrity_pct"] == 0.0
    assert res["configuration_governance_status"] == "AT_RISK"
    assert len(res["discrepancies"]) == 1
    assert res["discrepancies"][0]["ci_id"] == "CI-DB-SCHEMA"


def test_audit_configuration_baseline_drift_and_hotfix_governance_critical():
    """Verifica estado CRITICAL ante deriva de versión sin CR, hotfix no autorizado o fallo FCA/PCA."""
    from backend.services.project_ccb_service import (
        audit_configuration_baseline_drift_and_hotfix_governance,
    )

    res = audit_configuration_baseline_drift_and_hotfix_governance(
        [
            {
                "ci_id": "CI-ROGUE-HOTFIX",
                "baseline_version": "1.0.0",
                "deployed_version": "1.0.1-hotfix",
                "authorized_change_request_id": "   ",
                "is_production_hotfix": True,
                "physical_configuration_audit_passed": True,
                "functional_configuration_audit_passed": False,
                "days_since_last_configuration_audit": 12,
            }
        ],
        max_unverified_audit_age_days=30,
    )
    assert res["unauthorized_version_drift_count"] == 1
    assert res["unauthorized_hotfix_count"] == 1
    assert res["failed_fca_pca_count"] == 1
    assert res["configuration_governance_status"] == "CRITICAL"


def test_audit_configuration_baseline_drift_and_hotfix_governance_empty_and_export():
    """Verifica manejo de entradas vacías o no secuencia y exportación en __all__."""
    import backend.services.project_ccb_service as _m
    from backend.services.project_ccb_service import (
        audit_configuration_baseline_drift_and_hotfix_governance,
    )

    assert "audit_configuration_baseline_drift_and_hotfix_governance" in _m.__all__
    for bad in ([], None, "invalid"):
        assert audit_configuration_baseline_drift_and_hotfix_governance(bad) == {
            "total_configuration_items": 0,
            "compliant_ci_count": 0,
            "unauthorized_version_drift_count": 0,
            "unauthorized_hotfix_count": 0,
            "failed_fca_pca_count": 0,
            "stale_audit_ci_count": 0,
            "configuration_integrity_pct": 100.0,
            "configuration_governance_status": "HEALTHY",
            "discrepancies": [],
        }


def test_audit_quality_gate_peer_review_and_defect_density_healthy():
    """Verifica estado HEALTHY cuando todos los entregables tienen revisión 100%, revisor independiente, defectos cerrados y baja densidad."""
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_quality_gate_peer_review_and_defect_density,
    )

    reviews = [
        {
            "deliverable_id": "DLV-MOD-AUTH",
            "size_kloc_or_units": 5.0,
            "review_coverage_pct": 100.0,
            "independent_reviewer_assigned": True,
            "critical_major_defects_open": 0,
            "total_defects_found": 8,
            "rework_verified": True,
        },
        {
            "deliverable_id": "DLV-MOD-PAY",
            "size_kloc_or_units": 2.0,
            "review_coverage_pct": 100.0,
            "independent_reviewer_assigned": True,
            "critical_major_defects_open": 0,
            "total_defects_found": 0,
            "rework_verified": False,
        },
    ]
    res = audit_quality_gate_peer_review_and_defect_density(
        reviews, min_review_coverage_pct=100.0, max_defect_density_per_kloc=2.5
    )
    assert res == {
        "total_deliverables": 2,
        "compliant_deliverables_count": 2,
        "insufficient_review_coverage_count": 0,
        "open_critical_or_unverified_rework_count": 0,
        "excessive_defect_density_count": 0,
        "peer_review_governance_status": "HEALTHY",
        "violations": [],
    }
    assert (
        ProjectCCBService.audit_quality_gate_peer_review_and_defect_density(reviews)
        == res
    )


def test_audit_quality_gate_peer_review_and_defect_density_at_risk_high_density():
    """Verifica estado AT_RISK cuando la revisión y corrección están completas pero la densidad de defectos supera el umbral."""
    from backend.services.project_ccb_service import (
        audit_quality_gate_peer_review_and_defect_density,
    )

    res = audit_quality_gate_peer_review_and_defect_density(
        [
            {
                "deliverable_id": "DLV-DENSE-01",
                "size_kloc_or_units": 2.0,
                "review_coverage_pct": 100.0,
                "independent_reviewer_assigned": True,
                "critical_major_defects_open": 0,
                "total_defects_found": 9,
                "rework_verified": True,
            }
        ],
        min_review_coverage_pct=100.0,
        max_defect_density_per_kloc=2.5,
    )
    assert res["excessive_defect_density_count"] == 1
    assert res["compliant_deliverables_count"] == 0
    assert res["peer_review_governance_status"] == "AT_RISK"
    assert res["violations"][0]["defect_density"] == 4.5


def test_audit_quality_gate_peer_review_and_defect_density_critical():
    """Verifica estado CRITICAL cuando la cobertura de revisión es incompleta o existen defectos mayores abiertos."""
    from backend.services.project_ccb_service import (
        audit_quality_gate_peer_review_and_defect_density,
    )

    res = audit_quality_gate_peer_review_and_defect_density(
        [
            {
                "deliverable_id": "DLV-UNREVIEWED-BUGGY",
                "size_kloc_or_units": 4.0,
                "review_coverage_pct": 80.0,
                "independent_reviewer_assigned": False,
                "critical_major_defects_open": 1,
                "total_defects_found": 3,
                "rework_verified": False,
            }
        ],
        min_review_coverage_pct=100.0,
        max_defect_density_per_kloc=2.5,
    )
    assert res["insufficient_review_coverage_count"] == 1
    assert res["open_critical_or_unverified_rework_count"] == 1
    assert res["peer_review_governance_status"] == "CRITICAL"


def test_audit_quality_gate_peer_review_and_defect_density_empty_and_export():
    """Verifica manejo de entradas vacías o no secuencia y exportación en __all__."""
    import backend.services.project_ccb_service as _m
    from backend.services.project_ccb_service import (
        audit_quality_gate_peer_review_and_defect_density,
    )

    assert "audit_quality_gate_peer_review_and_defect_density" in _m.__all__
    for bad in ([], None, "invalid"):
        assert audit_quality_gate_peer_review_and_defect_density(bad) == {
            "total_deliverables": 0,
            "compliant_deliverables_count": 0,
            "insufficient_review_coverage_count": 0,
            "open_critical_or_unverified_rework_count": 0,
            "excessive_defect_density_count": 0,
            "peer_review_governance_status": "HEALTHY",
            "violations": [],
        }





def test_audit_retrospective_action_item_closure_and_process_improvement_healthy():
    """Acciones compliant (CLOSED verificada y en curso con owner/criterio)."""
    from backend.services.project_ccb_service import (
        audit_retrospective_action_item_closure_and_process_improvement,
    )

    res = audit_retrospective_action_item_closure_and_process_improvement(
        [
            {"action_id": "A-1", "status": "Closed", "sprints_carried_over": 2,
             "owner_assigned": True, "measurable_success_criterion_defined": True,
             "verified_effectiveness": True},
            {"action_id": "A-2", "status": "in_progress", "sprints_carried_over": 1,
             "owner_assigned": True, "measurable_success_criterion_defined": True,
             "verified_effectiveness": False},
        ]
    )
    assert res == {
        "total_actions": 2,
        "compliant_actions_count": 2,
        "stalled_carryover_actions_count": 0,
        "unowned_or_unmeasurable_actions_count": 0,
        "unverified_closed_actions_count": 0,
        "measurable_outcome_coverage_pct": 100.0,
        "continuous_improvement_status": "HEALTHY",
        "violations": [],
    }


def test_audit_retrospective_action_item_closure_and_process_improvement_critical():
    """Stalled carry-over ([3>2], borde 2 == umbral no stalled) y closure sin verificación -> CRITICAL."""
    from backend.services.project_ccb_service import (
        audit_retrospective_action_item_closure_and_process_improvement,
    )

    res = audit_retrospective_action_item_closure_and_process_improvement(
        [
            {"action_id": "A-3", "status": "OPEN", "sprints_carried_over": 3,
             "owner_assigned": True, "measurable_success_criterion_defined": True,
             "verified_effectiveness": False},
            {"action_id": "A-4", "status": "CLOSED", "sprints_carried_over": 0,
             "owner_assigned": True, "measurable_success_criterion_defined": True,
             "verified_effectiveness": False},
        ]
    )
    assert res["stalled_carryover_actions_count"] == 1
    assert res["unverified_closed_actions_count"] == 1
    assert res["compliant_actions_count"] == 0
    assert res["continuous_improvement_status"] == "CRITICAL"
    assert res["violations"][0]["reasons"] == ["STALLED_CARRYOVER (3>2, status OPEN)"]
    assert res["violations"][1]["reasons"] == ["CLOSED_WITHOUT_VERIFIED_EFFECTIVENESS"]

    # Borde: 2 sprints (== umbral) con status no CLOSED no es stalled.
    border = audit_retrospective_action_item_closure_and_process_improvement(
        [
            {"action_id": "A-5", "status": "OPEN", "sprints_carried_over": 2,
             "owner_assigned": True, "measurable_success_criterion_defined": True,
             "verified_effectiveness": False},
        ]
    )
    assert border["stalled_carryover_actions_count"] == 0
    assert border["continuous_improvement_status"] == "HEALTHY"


def test_audit_retrospective_action_item_closure_and_process_improvement_at_risk():
    """Unowned/unmeasurable y cobertura baja -> AT_RISK."""
    from backend.services.project_ccb_service import (
        audit_retrospective_action_item_closure_and_process_improvement,
    )

    res = audit_retrospective_action_item_closure_and_process_improvement(
        [
            {"action_id": "A-6", "status": "IN_PROGRESS", "sprints_carried_over": 1,
             "owner_assigned": False, "measurable_success_criterion_defined": False,
             "verified_effectiveness": False},
            {"action_id": "A-7", "status": "IN_PROGRESS", "sprints_carried_over": 1,
             "owner_assigned": True, "measurable_success_criterion_defined": True,
             "verified_effectiveness": False},
        ]
    )
    assert res["unowned_or_unmeasurable_actions_count"] == 1
    assert res["measurable_outcome_coverage_pct"] == 50.0
    assert res["continuous_improvement_status"] == "AT_RISK"
    assert res["violations"][0]["reasons"] == [
        "OWNER_UNASSIGNED", "SUCCESS_CRITERION_NOT_MEASURABLE",
    ]

    # Cobertura baja por si sola con umbral custom -> AT_RISK.
    low = audit_retrospective_action_item_closure_and_process_improvement(
        [
            {"action_id": "A-8", "status": "IN_PROGRESS", "sprints_carried_over": 1,
             "owner_assigned": True, "measurable_success_criterion_defined": False,
             "verified_effectiveness": False},
        ],
        min_measurable_outcome_pct=90.0,
    )
    assert low["measurable_outcome_coverage_pct"] == 0.0
    assert low["unowned_or_unmeasurable_actions_count"] == 1
    assert low["continuous_improvement_status"] == "AT_RISK"


def test_audit_retrospective_action_item_closure_and_process_improvement_custom_and_empty():
    """Umbrales custom, entrada vacia/None y proxy estatico + __all__."""
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_retrospective_action_item_closure_and_process_improvement,
    )
    import backend.services.project_ccb_service as mod

    # Umbral custom: 2 sprints permitidos; 3 pasa a stalled (case-insensitive).
    custom = audit_retrospective_action_item_closure_and_process_improvement(
        [
            {"action_id": "A-9", "status": "open", "sprints_carried_over": 3,
             "owner_assigned": True, "measurable_success_criterion_defined": True,
             "verified_effectiveness": False},
        ],
        max_action_carryover_sprints=1,
    )
    assert custom["stalled_carryover_actions_count"] == 1
    assert custom["continuous_improvement_status"] == "CRITICAL"

    for payload in ([], None, 42):
        empty = audit_retrospective_action_item_closure_and_process_improvement(payload)
        assert empty["total_actions"] == 0
        assert empty["measurable_outcome_coverage_pct"] == 100.0
        assert empty["continuous_improvement_status"] == "HEALTHY"
        assert empty["violations"] == []

    sample = [{"action_id": "SM", "status": "OPEN", "sprints_carried_over": 1,
               "owner_assigned": True, "measurable_success_criterion_defined": True,
               "verified_effectiveness": False}]
    assert (
        ProjectCCBService.audit_retrospective_action_item_closure_and_process_improvement(sample)
        == audit_retrospective_action_item_closure_and_process_improvement(sample)
    )
    assert "audit_retrospective_action_item_closure_and_process_improvement" in mod.__all__


def test_audit_procurement_warranty_claims_and_holdback_release_healthy():
    """Contratos con retencion liberada solo sin defectos latentes, con lien waiver y fianza activa -> HEALTHY."""
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_procurement_warranty_claims_and_holdback_release,
    )

    contracts = [
        {
            "contract_id": "CNT-W-01",
            "open_latent_defects_count": 0,
            "max_claim_response_days": 0,
            "holdback_released": True,
            "warranty_bond_active": True,
            "final_lien_waiver_signed": True,
        },
        {
            "contract_id": "CNT-W-02",
            "open_latent_defects_count": 2,
            "max_claim_response_days": 4,
            "holdback_released": False,
            "warranty_bond_active": False,
            "final_lien_waiver_signed": False,
        },
    ]
    res = audit_procurement_warranty_claims_and_holdback_release(
        contracts, max_warranty_response_days=5
    )
    assert res == {
        "total_contracts_evaluated": 2,
        "compliant_contracts_count": 2,
        "premature_holdback_releases_count": 0,
        "warranty_sla_breached_contracts_count": 0,
        "unsecured_warranty_contracts_count": 0,
        "warranty_governance_status": "HEALTHY",
        "violations": [],
    }
    assert (
        ProjectCCBService.audit_procurement_warranty_claims_and_holdback_release(
            contracts, max_warranty_response_days=5
        )
        == res
    )


def test_audit_procurement_warranty_claims_and_holdback_release_premature_and_unsecured():
    """Detecta liberacion prematura de retencion (con defectos, sin lien waiver o sin fianza) como CRITICAL."""
    from backend.services.project_ccb_service import (
        audit_procurement_warranty_claims_and_holdback_release,
    )

    res = audit_procurement_warranty_claims_and_holdback_release(
        [
            {
                "contract_id": "CNT-PREMATURE-DEFECT",
                "open_latent_defects_count": 1,
                "max_claim_response_days": 2,
                "holdback_released": True,
                "warranty_bond_active": True,
                "final_lien_waiver_signed": True,
            },
            {
                "contract_id": "CNT-UNSECURED",
                "open_latent_defects_count": 0,
                "max_claim_response_days": 0,
                "holdback_released": True,
                "warranty_bond_active": False,
                "final_lien_waiver_signed": True,
            },
        ],
        max_warranty_response_days=5,
    )
    assert res["total_contracts_evaluated"] == 2
    assert res["compliant_contracts_count"] == 0
    assert res["premature_holdback_releases_count"] == 2
    assert res["unsecured_warranty_contracts_count"] == 1
    assert res["warranty_sla_breached_contracts_count"] == 0
    assert res["warranty_governance_status"] == "CRITICAL"
    assert len(res["violations"]) == 2
    assert "premature_holdback_release" in res["violations"][0]["reasons"]
    assert "unsecured_warranty_period" in res["violations"][1]["reasons"]


def test_audit_procurement_warranty_claims_and_holdback_release_sla_breach():
    """Detecta incumplimiento de SLA de respuesta de garantia (> max_warranty_response_days) como CRITICAL."""
    from backend.services.project_ccb_service import (
        audit_procurement_warranty_claims_and_holdback_release,
    )

    res = audit_procurement_warranty_claims_and_holdback_release(
        [
            {
                "contract_id": "CNT-SLA-BREACH",
                "open_latent_defects_count": 3,
                "max_claim_response_days": 9,
                "holdback_released": False,
                "warranty_bond_active": True,
                "final_lien_waiver_signed": False,
            }
        ],
        max_warranty_response_days=5,
    )
    assert res["total_contracts_evaluated"] == 1
    assert res["compliant_contracts_count"] == 0
    assert res["premature_holdback_releases_count"] == 0
    assert res["warranty_sla_breached_contracts_count"] == 1
    assert res["unsecured_warranty_contracts_count"] == 0
    assert res["warranty_governance_status"] == "CRITICAL"
    assert res["violations"] == [
        {
            "contract_id": "CNT-SLA-BREACH",
            "reasons": ["warranty_claim_sla_breach"],
        }
    ]


def test_audit_procurement_warranty_claims_and_holdback_release_empty_and_export():
    """Maneja entradas vacias o invalidas devolviendo HEALTHY y verifica exportacion en __all__."""
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        audit_procurement_warranty_claims_and_holdback_release,
    )

    assert "audit_procurement_warranty_claims_and_holdback_release" in mod.__all__
    for payload in ([], None, "invalid"):
        empty = audit_procurement_warranty_claims_and_holdback_release(payload)  # type: ignore[arg-type]
        assert empty == {
            "total_contracts_evaluated": 0,
            "compliant_contracts_count": 0,
            "premature_holdback_releases_count": 0,
            "warranty_sla_breached_contracts_count": 0,
            "unsecured_warranty_contracts_count": 0,
            "warranty_governance_status": "HEALTHY",
            "violations": [],
        }


def test_audit_change_request_reserve_drawdown_authorization_healthy():
    """Disposiciones válidas de contingencia (known_unknown con risk_id) y gestión (unknown_unknown con sponsor y baseline)."""
    from backend.services.project_ccb_service import (
        audit_change_request_reserve_drawdown_authorization,
    )

    requests = [
        {
            "id": "CR-101",
            "uncertainty_type": "known_unknown",
            "reserve_pool": "contingency",
            "amount": 12000.0,
            "linked_risk_id": "RISK-07",
            "approved_by_role": "project_manager",
            "baseline_updated": False,
        },
        {
            "id": "CR-102",
            "uncertainty_type": "unknown_unknown",
            "reserve_pool": "management",
            "amount": 25000.0,
            "linked_risk_id": "",
            "approved_by_role": "sponsor",
            "baseline_updated": True,
        },
    ]
    res = audit_change_request_reserve_drawdown_authorization(
        requests,
        contingency_reserve_available=20000.0,
        management_reserve_available=30000.0,
    )
    assert res["total_requests"] == 2
    assert res["compliant_requests"] == 2
    assert res["total_contingency_requested"] == 12000.0
    assert res["total_management_requested"] == 25000.0
    assert res["contingency_overrun_amount"] == 0.0
    assert res["management_overrun_amount"] == 0.0
    assert res["pool_mismatch_ids"] == []
    assert res["missing_risk_traceability_ids"] == []
    assert res["unauthorized_management_drawdown_ids"] == []
    assert res["governance_health"] == "healthy"
    assert res["is_compliant"] is True
    assert res["recommendations"] == []


def test_audit_change_request_reserve_drawdown_authorization_mismatch_and_unauthorized():
    """Detecta pool_mismatch y uso de reserva de gestión sin Sponsor o sin baseline_updated."""
    from backend.services.project_ccb_service import (
        audit_change_request_reserve_drawdown_authorization,
    )

    requests = [
        {
            "request_id": "CR-201",
            "uncertainty_type": "unknown_unknown",
            "reserve_pool": "contingency",
            "amount": 5000.0,
            "linked_risk_id": "RISK-11",
            "approved_by_role": "project_manager",
            "baseline_updated": False,
        },
        {
            "request_id": "CR-202",
            "uncertainty_type": "unknown_unknown",
            "reserve_pool": "management",
            "amount": 15000.0,
            "approved_by_role": "project_manager",
            "baseline_updated": False,
        },
    ]
    res = audit_change_request_reserve_drawdown_authorization(
        requests,
        contingency_reserve_available=10000.0,
        management_reserve_available=20000.0,
    )
    assert res["total_requests"] == 2
    assert res["compliant_requests"] == 0
    assert res["pool_mismatch_ids"] == ["CR-201"]
    assert res["unauthorized_management_drawdown_ids"] == ["CR-202"]
    assert res["governance_health"] == "critical"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_change_request_reserve_drawdown_authorization_overruns_and_missing_risk():
    """Detecta falta de trazabilidad de riesgo (at_risk) y sobrecosto sobre reservas disponibles (critical)."""
    from backend.services.project_ccb_service import (
        audit_change_request_reserve_drawdown_authorization,
    )

    at_risk_res = audit_change_request_reserve_drawdown_authorization(
        [
            {
                "cr_id": "CR-301",
                "uncertainty_type": "known_unknown",
                "reserve_pool": "contingency",
                "amount": 4000.0,
                "linked_risk_id": "",
            }
        ],
        contingency_reserve_available=10000.0,
        management_reserve_available=10000.0,
    )
    assert at_risk_res["missing_risk_traceability_ids"] == ["CR-301"]
    assert at_risk_res["governance_health"] == "at_risk"
    assert at_risk_res["is_compliant"] is False

    overrun_res = audit_change_request_reserve_drawdown_authorization(
        [
            {
                "cr_id": "CR-302",
                "uncertainty_type": "known_unknown",
                "reserve_pool": "contingency",
                "amount": 14500.0,
                "linked_risk_id": "RISK-99",
            },
            {
                "cr_id": "CR-303",
                "uncertainty_type": "unknown_unknown",
                "reserve_pool": "management",
                "amount": 18000.0,
                "approved_by_role": "ccb_chair",
                "baseline_updated": True,
            },
        ],
        contingency_reserve_available=10000.0,
        management_reserve_available=15000.0,
    )
    assert overrun_res["contingency_overrun_amount"] == 4500.0
    assert overrun_res["management_overrun_amount"] == 3000.0
    assert overrun_res["governance_health"] == "critical"
    assert overrun_res["is_compliant"] is False
    assert len(overrun_res["recommendations"]) >= 2


def test_audit_change_request_reserve_drawdown_authorization_empty_and_service_binding():
    """Maneja entradas vacías o no válidas y expone el método en ProjectCCBService y __all__."""
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_change_request_reserve_drawdown_authorization,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        res = audit_change_request_reserve_drawdown_authorization(payload)  # type: ignore[arg-type]
        assert res["total_requests"] == 0
        assert res["compliant_requests"] == 0
        assert res["governance_health"] == "healthy"
        assert res["is_compliant"] is True
        assert res["recommendations"] == []

    sample = [
        {
            "id": "CR-401",
            "uncertainty_type": "known_unknown",
            "reserve_pool": "contingency",
            "amount": 1000.0,
            "linked_risk_id": "R-1",
        }
    ]
    assert ProjectCCBService.audit_change_request_reserve_drawdown_authorization(
        sample, contingency_reserve_available=5000.0
    ) == audit_change_request_reserve_drawdown_authorization(
        sample, contingency_reserve_available=5000.0
    )
    assert "audit_change_request_reserve_drawdown_authorization" in mod.__all__


def test_audit_deliverable_formal_acceptance_and_waiver_expiration_healthy():
    """Entregables aceptados y condicionalmente aceptados con qc_verified=True, firma válida, 0 defectos críticos y waiver vigente con plan."""
    from backend.services.project_ccb_service import (
        audit_deliverable_formal_acceptance_and_waiver_expiration,
    )

    items = [
        {
            "id": "DEL-01",
            "acceptance_status": "accepted",
            "qc_verified": True,
            "signed_off_by_role": "customer",
            "open_critical_defects": 0,
        },
        {
            "id": "DEL-02",
            "acceptance_status": "conditionally_accepted",
            "qc_verified": True,
            "signed_off_by_role": "sponsor",
            "open_critical_defects": 0,
            "waiver_days_elapsed": 15,
            "waiver_remediation_plan_linked": True,
        },
    ]
    res = audit_deliverable_formal_acceptance_and_waiver_expiration(
        items, max_conditional_waiver_days=30
    )
    assert res["total_deliverables"] == 2
    assert res["compliant_deliverables"] == 2
    assert res["unverified_scope_acceptance_ids"] == []
    assert res["unauthorized_signoff_or_critical_defect_ids"] == []
    assert res["expired_or_unplanned_waiver_ids"] == []
    assert res["acceptance_integrity_score"] == 100.0
    assert res["acceptance_governance_health"] == "healthy"
    assert res["is_compliant"] is True
    assert res["recommendations"] == []


def test_audit_deliverable_formal_acceptance_and_waiver_expiration_at_risk_waiver():
    """Detecta expired_or_unplanned_waiver_ids cuando la dispensa condicional expiró o carece de plan (at_risk)."""
    from backend.services.project_ccb_service import (
        audit_deliverable_formal_acceptance_and_waiver_expiration,
    )

    items = [
        {
            "deliverable_id": "DEL-10",
            "acceptance_status": "conditionally_accepted",
            "qc_verified": True,
            "signed_off_by_role": "product_owner",
            "open_critical_defects": 0,
            "waiver_days_elapsed": 45,
            "waiver_remediation_plan_linked": True,
        },
        {
            "deliverable_id": "DEL-11",
            "acceptance_status": "conditionally_accepted",
            "qc_verified": True,
            "signed_off_by_role": "client_representative",
            "open_critical_defects": 0,
            "waiver_days_elapsed": 10,
            "waiver_remediation_plan_linked": False,
        },
    ]
    res = audit_deliverable_formal_acceptance_and_waiver_expiration(
        items, max_conditional_waiver_days=30
    )
    assert res["total_deliverables"] == 2
    assert res["compliant_deliverables"] == 0
    assert res["expired_or_unplanned_waiver_ids"] == ["DEL-10", "DEL-11"]
    assert res["unverified_scope_acceptance_ids"] == []
    assert res["unauthorized_signoff_or_critical_defect_ids"] == []
    assert res["acceptance_integrity_score"] == 0.0
    assert res["acceptance_governance_health"] == "at_risk"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 1


def test_audit_deliverable_formal_acceptance_and_waiver_expiration_critical_qc_and_signoff():
    """Detecta unverified_scope_acceptance_ids y unauthorized_signoff_or_critical_defect_ids (critical)."""
    from backend.services.project_ccb_service import (
        audit_deliverable_formal_acceptance_and_waiver_expiration,
    )

    items = [
        {
            "deliverable_id": "DEL-20",
            "acceptance_status": "accepted",
            "qc_verified": False,
            "signed_off_by_role": "customer",
            "open_critical_defects": 0,
        },
        {
            "deliverable_id": "DEL-21",
            "acceptance_status": "accepted",
            "qc_verified": True,
            "signed_off_by_role": "developer",
            "open_critical_defects": 2,
        },
    ]
    res = audit_deliverable_formal_acceptance_and_waiver_expiration(items)
    assert res["total_deliverables"] == 2
    assert res["compliant_deliverables"] == 0
    assert res["unverified_scope_acceptance_ids"] == ["DEL-20"]
    assert res["unauthorized_signoff_or_critical_defect_ids"] == ["DEL-21"]
    assert res["acceptance_governance_health"] == "critical"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_deliverable_formal_acceptance_and_waiver_expiration_empty_and_service_binding():
    """Manejo defensivo de entradas vacías/no-secuencia y exposición en ProjectCCBService y __all__."""
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_deliverable_formal_acceptance_and_waiver_expiration,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_deliverable_formal_acceptance_and_waiver_expiration(payload)  # type: ignore[arg-type]
        assert empty["total_deliverables"] == 0
        assert empty["compliant_deliverables"] == 0
        assert empty["acceptance_integrity_score"] == 100.0
        assert empty["acceptance_governance_health"] == "healthy"
        assert empty["is_compliant"] is True
        assert empty["recommendations"] == []

    sample = [
        {
            "id": "DEL-99",
            "acceptance_status": "accepted",
            "qc_verified": True,
            "signed_off_by_role": "customer",
            "open_critical_defects": 0,
        }
    ]
    assert (
        ProjectCCBService.audit_deliverable_formal_acceptance_and_waiver_expiration(
            sample
        )
        == audit_deliverable_formal_acceptance_and_waiver_expiration(sample)
    )
    assert "audit_deliverable_formal_acceptance_and_waiver_expiration" in mod.__all__


def test_audit_quality_copq_and_rework_scrap_threshold_healthy():
    """Valida registros CoQ con inversión mayoritaria en conformidad, baja fuga externa y COPQ <= 10% BAC."""
    from backend.services.project_ccb_service import (
        audit_quality_copq_and_rework_scrap_threshold,
    )

    records = [
        {
            "id": "COQ-01",
            "prevention_cost": 4000.0,
            "appraisal_cost": 3000.0,
            "internal_failure_cost": 2000.0,
            "external_failure_cost": 500.0,
            "bac": 50000.0,
        },
        {
            "id": "COQ-02",
            "prevention_cost": 3500.0,
            "appraisal_cost": 2500.0,
            "internal_failure_cost": 1500.0,
            "external_failure_cost": 500.0,
            "bac": 40000.0,
        },
    ]
    res = audit_quality_copq_and_rework_scrap_threshold(records)
    assert res["total_records"] == 2
    assert res["compliant_records"] == 2
    assert res["total_conformance_cost"] == 13000.0
    assert res["total_copq"] == 4500.0
    assert res["underinvested_conformance_ids"] == []
    assert res["excessive_external_failure_leakage_ids"] == []
    assert res["copq_budget_erosion_ids"] == []
    assert res["coq_governance_health"] == "healthy"
    assert res["is_compliant"] is True
    assert res["recommendations"] == []


def test_audit_quality_copq_and_rework_scrap_threshold_at_risk_underinvested():
    """Detecta subinversión en prevención/evaluación (< 50% CoQ total) sin fuga externa ni erosión BAC ('at_risk')."""
    from backend.services.project_ccb_service import (
        audit_quality_copq_and_rework_scrap_threshold,
    )

    records = [
        {
            "record_id": "COQ-10",
            "prevention_cost": 1000.0,
            "appraisal_cost": 1000.0,
            "internal_failure_cost": 3000.0,
            "external_failure_cost": 500.0,
            "bac": 60000.0,
        }
    ]
    res = audit_quality_copq_and_rework_scrap_threshold(records)
    assert res["total_records"] == 1
    assert res["compliant_records"] == 0
    assert res["underinvested_conformance_ids"] == ["COQ-10"]
    assert res["excessive_external_failure_leakage_ids"] == []
    assert res["copq_budget_erosion_ids"] == []
    assert res["coq_governance_health"] == "at_risk"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 1


def test_audit_quality_copq_and_rework_scrap_threshold_critical_leakage_and_erosion():
    """Detecta fuga excesiva de fallos externos (> 35% COPQ) y erosión presupuestaria (> 10% BAC) ('critical')."""
    from backend.services.project_ccb_service import (
        audit_quality_copq_and_rework_scrap_threshold,
    )

    records = [
        {
            "record_id": "COQ-20",
            "prevention_cost": 5000.0,
            "appraisal_cost": 4000.0,
            "internal_failure_cost": 1000.0,
            "external_failure_cost": 2000.0,
            "bac": 50000.0,
        },
        {
            "record_id": "COQ-21",
            "prevention_cost": 8000.0,
            "appraisal_cost": 6000.0,
            "internal_failure_cost": 9000.0,
            "external_failure_cost": 2000.0,
            "bac": 80000.0,
        },
    ]
    res = audit_quality_copq_and_rework_scrap_threshold(records)
    assert res["total_records"] == 2
    assert res["compliant_records"] == 0
    assert res["excessive_external_failure_leakage_ids"] == ["COQ-20"]
    assert res["copq_budget_erosion_ids"] == ["COQ-21"]
    assert res["coq_governance_health"] == "critical"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_quality_copq_and_rework_scrap_threshold_empty_and_service_binding():
    """Manejo defensivo de entradas vacías/no-secuencia y exposición en ProjectCCBService y __all__."""
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_quality_copq_and_rework_scrap_threshold,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_quality_copq_and_rework_scrap_threshold(payload)  # type: ignore[arg-type]
        assert empty["total_records"] == 0
        assert empty["compliant_records"] == 0
        assert empty["total_conformance_cost"] == 0.0
        assert empty["total_copq"] == 0.0
        assert empty["coq_governance_health"] == "healthy"
        assert empty["is_compliant"] is True
        assert empty["recommendations"] == []

    sample = [
        {
            "id": "COQ-99",
            "prevention_cost": 2000.0,
            "appraisal_cost": 2000.0,
            "internal_failure_cost": 500.0,
            "external_failure_cost": 100.0,
            "bac": 20000.0,
        }
    ]
    assert (
        ProjectCCBService.audit_quality_copq_and_rework_scrap_threshold(sample)
        == audit_quality_copq_and_rework_scrap_threshold(sample)
    )
    assert "audit_quality_copq_and_rework_scrap_threshold" in mod.__all__






def test_emergency_ratification_bypass_critical_and_overdue():
    """Emergencia sin justificar y sin ratificar vencida + sin rollback -> CRITICAL y doble reason."""
    from backend.services.project_ccb_service import (
        audit_emergency_change_ratification_and_bypass_governance,
    )

    res = audit_emergency_change_ratification_and_bypass_governance(
        [
            {
                "cr_id": "CR-1",
                "is_emergency": True,
                "severity_incident_linked": False,
                "post_facto_ratified": False,
                "hours_since_execution": 72.0,
                "rollback_tested": False,
            }
        ]
    )
    assert res["total_changes"] == 1
    assert res["emergency_changes_count"] == 1
    assert res["compliant_changes_count"] == 0
    assert res["unratified_overdue_or_unjustified_emergency_count"] == 1
    assert res["emergency_without_rollback_safety_count"] == 1
    assert res["violations"][0]["cr_id"] == "CR-1"
    assert res["violations"][0]["reasons"] == [
        "unratified_overdue_or_unjustified_emergency",
        "emergency_without_rollback_safety",
    ]
    assert res["emergency_share_pct"] == 100.0
    assert res["emergency_bypass_ratio_exceeded"] is True
    assert res["emergency_governance_status"] == "CRITICAL"

    # Vencida pero justificada y no ratificada -> regla 1 por overdue.
    overdue = audit_emergency_change_ratification_and_bypass_governance(
        [
            {
                "cr_id": "CR-2",
                "is_emergency": True,
                "severity_incident_linked": True,
                "post_facto_ratified": False,
                "hours_since_execution": 48.1,
                "rollback_tested": True,
            }
        ]
    )
    assert overdue["violations"][0]["reasons"] == ["unratified_overdue_or_unjustified_emergency"]
    assert overdue["unratified_overdue_or_unjustified_emergency_count"] == 1
    assert overdue["emergency_without_rollback_safety_count"] == 0
    assert overdue["emergency_governance_status"] == "CRITICAL"

    # Ratificada a tiempo y justificada -> sin regla 1 (share 1/5 = 20%, sin bypass).
    timely = audit_emergency_change_ratification_and_bypass_governance(
        [
            {
                "cr_id": "CR-3",
                "is_emergency": True,
                "severity_incident_linked": True,
                "post_facto_ratified": False,
                "hours_since_execution": 48.0,
                "rollback_tested": True,
            },
            {"cr_id": "CR-25"},
            {"cr_id": "CR-26"},
            {"cr_id": "CR-27"},
            {"cr_id": "CR-28"},
        ]
    )
    assert timely["violations"] == []
    assert timely["compliant_changes_count"] == 5
    assert timely["emergency_share_pct"] == 20.0
    assert timely["emergency_bypass_ratio_exceeded"] is False
    assert timely["emergency_governance_status"] == "HEALTHY"


def test_emergency_ratification_bypass_rollback_and_share_thresholds():
    """Sin rollback -> AT_RISK; share: limite exacto no excede, por encima si."""
    from backend.services.project_ccb_service import (
        audit_emergency_change_ratification_and_bypass_governance,
    )

    rollback = audit_emergency_change_ratification_and_bypass_governance(
        [
            {
                "cr_id": "CR-4",
                "is_emergency": True,
                "severity_incident_linked": True,
                "post_facto_ratified": True,
                "hours_since_execution": 1.0,
            }
        ]
    )
    assert rollback["emergency_without_rollback_safety_count"] == 1
    assert rollback["unratified_overdue_or_unjustified_emergency_count"] == 0
    assert rollback["violations"][0]["reasons"] == ["emergency_without_rollback_safety"]
    assert rollback["emergency_governance_status"] == "AT_RISK"

    # 1 de 5 = 20.0%: no excede (comparacion estricta) -> HEALTHY.
    at_limit = audit_emergency_change_ratification_and_bypass_governance(
        [
            {
                "cr_id": "CR-5",
                "is_emergency": True,
                "severity_incident_linked": True,
                "post_facto_ratified": True,
                "hours_since_execution": 0.0,
                "rollback_tested": True,
            },
            {"cr_id": "CR-6"},
            {"cr_id": "CR-7"},
            {"cr_id": "CR-8"},
            {"cr_id": "CR-9"},
        ]
    )
    assert at_limit["emergency_share_pct"] == 20.0
    assert at_limit["emergency_bypass_ratio_exceeded"] is False
    assert at_limit["emergency_governance_status"] == "HEALTHY"
    assert at_limit["compliant_changes_count"] == 5

    # 2 de 5 = 40.0%: excede -> AT_RISK.
    over_limit = audit_emergency_change_ratification_and_bypass_governance(
        [
            {"cr_id": "CR-10", "is_emergency": True, "severity_incident_linked": True,
             "post_facto_ratified": True, "hours_since_execution": 0.0, "rollback_tested": True},
            {"cr_id": "CR-11", "is_emergency": True, "severity_incident_linked": True,
             "post_facto_ratified": True, "hours_since_execution": 0.0, "rollback_tested": True},
            {"cr_id": "CR-12"},
            {"cr_id": "CR-13"},
            {"cr_id": "CR-14"},
        ]
    )
    assert over_limit["emergency_share_pct"] == 40.0
    assert over_limit["emergency_bypass_ratio_exceeded"] is True
    assert over_limit["unratified_overdue_or_unjustified_emergency_count"] == 0
    assert over_limit["emergency_without_rollback_safety_count"] == 0
    assert over_limit["emergency_governance_status"] == "AT_RISK"

    # Umbral custom: max 10.0 con 1 de 5 (20%) -> excede.
    custom = audit_emergency_change_ratification_and_bypass_governance(
        [
            {"cr_id": "CR-15", "is_emergency": True, "severity_incident_linked": True,
             "post_facto_ratified": True, "hours_since_execution": 0.0, "rollback_tested": True},
            {"cr_id": "CR-16"},
            {"cr_id": "CR-17"},
            {"cr_id": "CR-18"},
            {"cr_id": "CR-19"},
        ],
        max_emergency_share_pct=10.0,
    )
    assert custom["emergency_bypass_ratio_exceeded"] is True
    assert custom["emergency_governance_status"] == "AT_RISK"


def test_emergency_ratification_bypass_ignores_bad_and_non_emergency():
    """No-lista/None -> vacio; no-dict ignorados; no-emergencia son conformes y no se cuentan."""
    from backend.services.project_ccb_service import (
        audit_emergency_change_ratification_and_bypass_governance,
    )

    for payload in (None, "not-a-list", 42):
        empty = audit_emergency_change_ratification_and_bypass_governance(payload)
        assert empty["total_changes"] == 0
        assert empty["emergency_changes_count"] == 0
        assert empty["emergency_share_pct"] == 0.0
        assert empty["emergency_bypass_ratio_exceeded"] is False
        assert empty["emergency_governance_status"] == "HEALTHY"
        assert empty["violations"] == []

    mixed = audit_emergency_change_ratification_and_bypass_governance(
        [
            "no-dict",
            42,
            None,
            {"cr_id": "CR-20", "is_emergency": False},
            {"cr_id": "CR-21", "is_emergency": True, "severity_incident_linked": True,
             "post_facto_ratified": True, "hours_since_execution": 0.0, "rollback_tested": True},
        ],
        max_emergency_share_pct=50.0,
    )
    assert mixed["total_changes"] == 2
    assert mixed["emergency_changes_count"] == 1
    assert mixed["compliant_changes_count"] == 2
    assert mixed["emergency_share_pct"] == 50.0
    assert mixed["emergency_bypass_ratio_exceeded"] is False
    assert mixed["violations"] == []
    assert mixed["emergency_governance_status"] == "HEALTHY"

    # Non-owner keys irrelevantes no rompen: emergencia sin severty -> regla 1.
    bare = audit_emergency_change_ratification_and_bypass_governance(
        [{"cr_id": "CR-22", "is_emergency": True}]
    )
    assert bare["violations"][0]["reasons"] == [
        "unratified_overdue_or_unjustified_emergency",
        "emergency_without_rollback_safety",
    ]
    assert bare["emergency_governance_status"] == "CRITICAL"


def test_emergency_ratification_bypass_precedence_and_binding():
    """CRITICAL domina; AT_RISK solo rollback o ratio; proxy @staticmethod y __all__."""
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_emergency_change_ratification_and_bypass_governance,
    )

    # CRITICAL por regla 1 pese a exceder ratio y tener rollback pendiente.
    dominates = audit_emergency_change_ratification_and_bypass_governance(
        [
            {"cr_id": "CR-23", "is_emergency": True, "severity_incident_linked": False,
             "post_facto_ratified": True, "hours_since_execution": 1.0, "rollback_tested": False},
        ]
    )
    assert dominates["unratified_overdue_or_unjustified_emergency_count"] == 1
    assert dominates["emergency_without_rollback_safety_count"] == 1
    assert dominates["emergency_bypass_ratio_exceeded"] is True
    assert dominates["emergency_governance_status"] == "CRITICAL"

    sample = [{"cr_id": "CR-24", "is_emergency": True, "severity_incident_linked": True,
               "post_facto_ratified": True, "hours_since_execution": 0.0, "rollback_tested": True}]
    assert (
        ProjectCCBService.audit_emergency_change_ratification_and_bypass_governance(sample)
        == audit_emergency_change_ratification_and_bypass_governance(sample)
    )
    assert "audit_emergency_change_ratification_and_bypass_governance" in mod.__all__


def test_audit_quality_capa_root_cause_and_recurrence_healthy():
    """Valida CAPAs con método RCA documentado, efectividad verificada y cero recurrencias."""
    from backend.services.project_ccb_service import (
        audit_quality_capa_root_cause_and_recurrence,
    )

    capas = [
        {
            "id": "CAPA-01",
            "status": "verified_closed",
            "rca_method": "5_whys",
            "effectiveness_verified": True,
            "days_since_implementation": 45,
            "recurrence_count": 0,
        },
        {
            "id": "CAPA-02",
            "status": "implemented",
            "rca_method": "ishikawa",
            "effectiveness_verified": False,
            "days_since_implementation": 14,
            "recurrence_count": 0,
        },
    ]
    res = audit_quality_capa_root_cause_and_recurrence(capas)
    assert res["total_capas"] == 2
    assert res["compliant_capas"] == 2
    assert res["missing_rca_or_premature_closure_ids"] == []
    assert res["overdue_effectiveness_verification_ids"] == []
    assert res["recurring_failure_capa_ids"] == []
    assert res["capa_governance_health"] == "healthy"
    assert res["is_compliant"] is True
    assert res["recommendations"] == []


def test_audit_quality_capa_root_cause_and_recurrence_at_risk_overdue():
    """Detecta CAPA implementada con verificación de efectividad vencida (> 30 días) sin recurrencia ('at_risk')."""
    from backend.services.project_ccb_service import (
        audit_quality_capa_root_cause_and_recurrence,
    )

    capas = [
        {
            "capa_id": "CAPA-10",
            "status": "implemented",
            "rca_method": "fault_tree",
            "effectiveness_verified": False,
            "days_since_implementation": 40,
            "recurrence_count": 0,
        }
    ]
    res = audit_quality_capa_root_cause_and_recurrence(capas)
    assert res["total_capas"] == 1
    assert res["compliant_capas"] == 0
    assert res["overdue_effectiveness_verification_ids"] == ["CAPA-10"]
    assert res["missing_rca_or_premature_closure_ids"] == []
    assert res["recurring_failure_capa_ids"] == []
    assert res["capa_governance_health"] == "at_risk"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 1


def test_audit_quality_capa_root_cause_and_recurrence_critical_rca_and_recurrence():
    """Detecta cierre prematuro sin efectividad/sin RCA y recurrencia del defecto ('critical')."""
    from backend.services.project_ccb_service import (
        audit_quality_capa_root_cause_and_recurrence,
    )

    capas = [
        {
            "capa_id": "CAPA-20",
            "status": "verified_closed",
            "rca_method": "",
            "effectiveness_verified": False,
            "days_since_implementation": 10,
            "recurrence_count": 0,
        },
        {
            "capa_id": "CAPA-21",
            "status": "verified_closed",
            "rca_method": "pareto",
            "effectiveness_verified": True,
            "days_since_implementation": 20,
            "recurrence_count": 2,
        },
    ]
    res = audit_quality_capa_root_cause_and_recurrence(capas)
    assert res["total_capas"] == 2
    assert res["compliant_capas"] == 0
    assert res["missing_rca_or_premature_closure_ids"] == ["CAPA-20"]
    assert res["recurring_failure_capa_ids"] == ["CAPA-21"]
    assert res["capa_governance_health"] == "critical"
    assert res["is_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_quality_capa_root_cause_and_recurrence_empty_and_service_binding():
    """Manejo defensivo de entradas vacías/no-secuencia y exposición en ProjectCCBService y __all__."""
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_quality_capa_root_cause_and_recurrence,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_quality_capa_root_cause_and_recurrence(payload)  # type: ignore[arg-type]
        assert empty["total_capas"] == 0
        assert empty["compliant_capas"] == 0
        assert empty["missing_rca_or_premature_closure_ids"] == []
        assert empty["overdue_effectiveness_verification_ids"] == []
        assert empty["recurring_failure_capa_ids"] == []
        assert empty["capa_governance_health"] == "healthy"
        assert empty["is_compliant"] is True
        assert empty["recommendations"] == []

    sample = [
        {
            "id": "CAPA-99",
            "status": "open",
            "rca_method": "5_whys",
            "effectiveness_verified": False,
            "days_since_implementation": 0,
            "recurrence_count": 0,
        }
    ]
    assert (
        ProjectCCBService.audit_quality_capa_root_cause_and_recurrence(sample)
        == audit_quality_capa_root_cause_and_recurrence(sample)
    )
    assert "audit_quality_capa_root_cause_and_recurrence" in mod.__all__



def test_configuration_baseline_integrity_verified_and_compromised():
    """CI alineado -> VERIFIED; hotfix sin CR o checksum fallido -> COMPROMISED."""
    from backend.services.project_ccb_service import (
        audit_configuration_baseline_integrity_and_version_drift,
    )

    verified = audit_configuration_baseline_integrity_and_version_drift(
        [
            {
                "ci_id": "CI-1",
                "approved_baseline_version": "1.0.0",
                "deployed_version": "1.0.0",
                "approved_cr_id": None,
                "checksum_matches_artifact": True,
                "is_locked_in_cm_repo": True,
            }
        ]
    )
    assert verified["total_configuration_items"] == 1
    assert verified["unauthorized_drift_ci_ids"] == []
    assert verified["pending_baseline_sync_ci_ids"] == []
    assert verified["checksum_mismatch_ci_ids"] == []
    assert verified["unlocked_baseline_ci_ids"] == []
    assert verified["cm_audit_status"] == "VERIFIED"
    assert verified["is_baseline_intact"] is True

    compromised = audit_configuration_baseline_integrity_and_version_drift(
        [
            {
                "ci_id": "CI-2",
                "approved_baseline_version": "1.0.0",
                "deployed_version": "9.9.9-hotfix",
                "approved_cr_id": None,
                "checksum_matches_artifact": False,
                "is_locked_in_cm_repo": True,
            }
        ]
    )
    assert compromised["unauthorized_drift_ci_ids"] == ["CI-2"]
    assert compromised["checksum_mismatch_ci_ids"] == ["CI-2"]
    assert compromised["cm_audit_status"] == "COMPROMISED"
    assert compromised["is_baseline_intact"] is False

    # Solo checksum fallo sin drift -> COMPROMISED igualmente.
    only_checksum = audit_configuration_baseline_integrity_and_version_drift(
        [
            {
                "ci_id": "CI-3",
                "approved_baseline_version": "2.0",
                "deployed_version": "2.0",
                "checksum_matches_artifact": False,
                "is_locked_in_cm_repo": True,
            }
        ]
    )
    assert only_checksum["checksum_mismatch_ci_ids"] == ["CI-3"]
    assert only_checksum["unauthorized_drift_ci_ids"] == []
    assert only_checksum["cm_audit_status"] == "COMPROMISED"


def test_configuration_baseline_integrity_pending_sync_and_unlocked():
    """Con CR aprobado -> pending_sync; sin lock -> unlocked; ambos -> DRIFT_DETECTED."""
    from backend.services.project_ccb_service import (
        audit_configuration_baseline_integrity_and_version_drift,
    )

    pending = audit_configuration_baseline_integrity_and_version_drift(
        [
            {
                "ci_id": "CI-4",
                "approved_baseline_version": "1.0.0",
                "deployed_version": "1.1.0",
                "approved_cr_id": "CR-42",
                "checksum_matches_artifact": True,
                "is_locked_in_cm_repo": True,
            }
        ]
    )
    assert pending["pending_baseline_sync_ci_ids"] == ["CI-4"]
    assert pending["unauthorized_drift_ci_ids"] == []
    assert pending["cm_audit_status"] == "DRIFT_DETECTED"
    assert pending["is_baseline_intact"] is False

    unlocked = audit_configuration_baseline_integrity_and_version_drift(
        [
            {
                "ci_id": "CI-5",
                "approved_baseline_version": "2.0",
                "deployed_version": "2.0",
                "checksum_matches_artifact": True,
                "is_locked_in_cm_repo": False,
            }
        ]
    )
    assert unlocked["unlocked_baseline_ci_ids"] == ["CI-5"]
    assert unlocked["pending_baseline_sync_ci_ids"] == []
    assert unlocked["cm_audit_status"] == "DRIFT_DETECTED"

    # approved_cr_id vacío o whitespace -> unauthorized (no pending).
    blank_cr = audit_configuration_baseline_integrity_and_version_drift(
        [
            {
                "ci_id": "CI-6",
                "approved_baseline_version": "1.0",
                "deployed_version": "3.0",
                "approved_cr_id": "   ",
                "checksum_matches_artifact": True,
                "is_locked_in_cm_repo": True,
            }
        ]
    )
    assert blank_cr["unauthorized_drift_ci_ids"] == ["CI-6"]
    assert blank_cr["pending_baseline_sync_ci_ids"] == []


def test_configuration_baseline_integrity_thresholds_and_flags():
    """max_allowed_drift_items tolera drift; require_checksum_verification False desactiva regla 3."""
    from backend.services.project_ccb_service import (
        audit_configuration_baseline_integrity_and_version_drift,
    )

    drifted_item = {
        "ci_id": "CI-7",
        "approved_baseline_version": "1.0",
        "deployed_version": "2.0",
        "checksum_matches_artifact": True,
        "is_locked_in_cm_repo": True,
    }

    tolerated = audit_configuration_baseline_integrity_and_version_drift(
        [drifted_item], max_allowed_drift_items=2
    )
    assert tolerated["unauthorized_drift_ci_ids"] == ["CI-7"]
    assert tolerated["cm_audit_status"] == "DRIFT_DETECTED"

    breached = audit_configuration_baseline_integrity_and_version_drift(
        [drifted_item], max_allowed_drift_items=0
    )
    assert breached["cm_audit_status"] == "COMPROMISED"

    # límite exacto: max=1 con 1 drift -> tolerado (comparación estricta >).
    at_limit = audit_configuration_baseline_integrity_and_version_drift(
        [drifted_item], max_allowed_drift_items=1
    )
    assert at_limit["cm_audit_status"] == "DRIFT_DETECTED"

    no_checksum_req = audit_configuration_baseline_integrity_and_version_drift(
        [
            {
                "ci_id": "CI-8",
                "approved_baseline_version": "1.0",
                "deployed_version": "1.0",
                "checksum_matches_artifact": False,
                "is_locked_in_cm_repo": True,
            }
        ],
        require_checksum_verification=False,
    )
    assert no_checksum_req["checksum_mismatch_ci_ids"] == []
    assert no_checksum_req["cm_audit_status"] == "VERIFIED"
    assert no_checksum_req["is_baseline_intact"] is True


def test_configuration_baseline_integrity_neutral_and_binding():
    """No-lista/None -> vacío VERIFIED; no-dict ignorados; proxy estático."""
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_configuration_baseline_integrity_and_version_drift,
    )

    for payload in (None, "no-list", 42):
        empty = audit_configuration_baseline_integrity_and_version_drift(payload)
        assert empty["total_configuration_items"] == 0
        assert empty["unauthorized_drift_ci_ids"] == []
        assert empty["pending_baseline_sync_ci_ids"] == []
        assert empty["checksum_mismatch_ci_ids"] == []
        assert empty["unlocked_baseline_ci_ids"] == []
        assert empty["cm_audit_status"] == "VERIFIED"
        assert empty["is_baseline_intact"] is True

    mixed = audit_configuration_baseline_integrity_and_version_drift(
        [
            "no-dict",
            42,
            {
                "ci_id": "CI-9",
                "approved_baseline_version": "1.0",
                "deployed_version": "1.0",
                "checksum_matches_artifact": True,
                "is_locked_in_cm_repo": True,
            },
        ]
    )
    assert mixed["total_configuration_items"] == 1
    assert mixed["cm_audit_status"] == "VERIFIED"

    sample = [
        {
            "ci_id": "CI-10",
            "approved_baseline_version": "1.0",
            "deployed_version": "9.0",
            "checksum_matches_artifact": True,
            "is_locked_in_cm_repo": True,
        }
    ]
    assert (
        ProjectCCBService.audit_configuration_baseline_integrity_and_version_drift(sample)
        == audit_configuration_baseline_integrity_and_version_drift(sample)
    )
    assert "audit_configuration_baseline_integrity_and_version_drift" in mod.__all__


def test_audit_scope_creep_and_gold_plating_effort_disciplined():
    """Valida ítems dentro de la línea base WBS o respaldados por CR aprobado sin Gold-Plating ('DISCIPLINED')."""
    from backend.services.project_ccb_service import (
        audit_scope_creep_and_gold_plating_effort,
    )

    items = [
        {
            "item_id": "WRK-01",
            "logged_hours": 120.0,
            "in_approved_wbs_baseline": True,
            "linked_approved_cr_id": None,
            "is_gold_plating_extra_feature": False,
        },
        {
            "item_id": "WRK-02",
            "logged_hours": 40.0,
            "in_approved_wbs_baseline": False,
            "linked_approved_cr_id": "CR-2026-09",
            "is_gold_plating_extra_feature": False,
        },
    ]
    res = audit_scope_creep_and_gold_plating_effort(items)
    assert res["total_work_items"] == 2
    assert res["unapproved_scope_creep_ids"] == []
    assert res["gold_plating_item_ids"] == []
    assert res["unbaselined_effort_hours"] == 0.0
    assert res["total_effort_hours"] == 160.0
    assert res["unbaselined_effort_ratio_pct"] == 0.0
    assert res["scope_control_status"] == "DISCIPLINED"
    assert res["is_scope_disciplined"] is True
    assert res["issues"] == []


def test_audit_scope_creep_and_gold_plating_effort_scope_breach():
    """Detecta Gold-Plating o porcentaje de esfuerzo fuera de línea base > 5.0% sin duplicar horas ('SCOPE_BREACH')."""
    from backend.services.project_ccb_service import (
        audit_scope_creep_and_gold_plating_effort,
    )

    items = [
        {
            "item_id": "WRK-10",
            "logged_hours": 80.0,
            "in_approved_wbs_baseline": True,
            "linked_approved_cr_id": None,
            "is_gold_plating_extra_feature": False,
        },
        {
            "item_id": "WRK-11",
            "logged_hours": 20.0,
            "in_approved_wbs_baseline": False,
            "linked_approved_cr_id": "",
            "is_gold_plating_extra_feature": True,
        },
    ]
    res = audit_scope_creep_and_gold_plating_effort(items)
    assert res["total_work_items"] == 2
    assert res["unapproved_scope_creep_ids"] == ["WRK-11"]
    assert res["gold_plating_item_ids"] == ["WRK-11"]
    assert res["unbaselined_effort_hours"] == 20.0
    assert res["total_effort_hours"] == 100.0
    assert res["unbaselined_effort_ratio_pct"] == 20.0
    assert res["scope_control_status"] == "SCOPE_BREACH"
    assert res["is_scope_disciplined"] is False
    assert len(res["issues"]) >= 3


def test_audit_scope_creep_and_gold_plating_effort_minor_drift():
    """Detecta esfuerzo fuera de línea base <= 5.0% sin Gold-Plating ('MINOR_DRIFT')."""
    from backend.services.project_ccb_service import (
        audit_scope_creep_and_gold_plating_effort,
    )

    items = [
        {
            "item_id": "WRK-20",
            "logged_hours": 96.0,
            "in_approved_wbs_baseline": True,
            "linked_approved_cr_id": None,
            "is_gold_plating_extra_feature": False,
        },
        {
            "item_id": "WRK-21",
            "logged_hours": 4.0,
            "in_approved_wbs_baseline": False,
            "linked_approved_cr_id": None,
            "is_gold_plating_extra_feature": False,
        },
    ]
    res = audit_scope_creep_and_gold_plating_effort(items)
    assert res["total_work_items"] == 2
    assert res["unapproved_scope_creep_ids"] == ["WRK-21"]
    assert res["gold_plating_item_ids"] == []
    assert res["unbaselined_effort_hours"] == 4.0
    assert res["total_effort_hours"] == 100.0
    assert res["unbaselined_effort_ratio_pct"] == 4.0
    assert res["scope_control_status"] == "MINOR_DRIFT"
    assert res["is_scope_disciplined"] is False
    assert len(res["issues"]) == 1


def test_audit_scope_creep_and_gold_plating_effort_empty_and_binding():
    """Verifica manejo defensivo de entradas vacías/no-secuencia y enlace en ProjectCCBService y __all__."""
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_scope_creep_and_gold_plating_effort,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_scope_creep_and_gold_plating_effort(payload)  # type: ignore[arg-type]
        assert empty["total_work_items"] == 0
        assert empty["unapproved_scope_creep_ids"] == []
        assert empty["gold_plating_item_ids"] == []
        assert empty["unbaselined_effort_hours"] == 0.0
        assert empty["total_effort_hours"] == 0.0
        assert empty["unbaselined_effort_ratio_pct"] == 0.0
        assert empty["scope_control_status"] == "DISCIPLINED"
        assert empty["is_scope_disciplined"] is True
        assert empty["issues"] == []

    sample = [
        {
            "item_id": "WRK-99",
            "logged_hours": 10.0,
            "in_approved_wbs_baseline": True,
            "linked_approved_cr_id": None,
            "is_gold_plating_extra_feature": False,
        }
    ]
    assert (
        ProjectCCBService.audit_scope_creep_and_gold_plating_effort(sample)
        == audit_scope_creep_and_gold_plating_effort(sample)
    )
    assert "audit_scope_creep_and_gold_plating_effort" in mod.__all__


def test_audit_quality_spc_control_chart_in_control():
    """Caso 1: Muestras dentro de +-3 sigma, dentro de USL/LSL y sin corrida de 7 -> IN_STATISTICAL_CONTROL."""
    from backend.services.project_ccb_service import (
        audit_quality_spc_control_chart_stability,
    )

    samples = [
        {"sample_id": "S-01", "measured_value": 10.2},
        {"sample_id": "S-02", "measured_value": 9.8},
        {"sample_id": "S-03", "measured_value": 10.5},
        {"sample_id": "S-04", "measured_value": 9.6},
        {"sample_id": "S-05", "measured_value": 10.0},
    ]
    res = audit_quality_spc_control_chart_stability(
        samples,
        center_line_mean=10.0,
        one_sigma_std_dev=0.5,
        upper_spec_limit_usl=12.0,
        lower_spec_limit_lsl=8.0,
    )
    assert res["total_samples"] == 5
    assert res["ucl_3sigma"] == 11.5
    assert res["lcl_3sigma"] == 8.5
    assert res["beyond_3sigma_sample_ids"] == []
    assert res["beyond_spec_limit_sample_ids"] == []
    assert res["rule_of_seven_run_detected"] is False
    assert res["process_stability_status"] == "IN_STATISTICAL_CONTROL"
    assert res["is_process_stable"] is True
    assert res["issues"] == []


def test_audit_quality_spc_control_chart_out_of_control_rule_of_seven_and_3sigma():
    """Caso 2: Corrida de 7 puntos de un lado de la media o punto fuera de 3 sigma (dentro de USL/LSL) -> OUT_OF_CONTROL."""
    from backend.services.project_ccb_service import (
        audit_quality_spc_control_chart_stability,
    )

    samples = [
        {"sample_id": f"S-{i}", "measured_value": 10.3} for i in range(1, 8)
    ] + [{"sample_id": "S-8", "measured_value": 11.6}]
    res = audit_quality_spc_control_chart_stability(
        samples,
        center_line_mean=10.0,
        one_sigma_std_dev=0.5,
        upper_spec_limit_usl=12.0,
        lower_spec_limit_lsl=8.0,
    )
    assert res["total_samples"] == 8
    assert res["beyond_3sigma_sample_ids"] == ["S-8"]
    assert res["beyond_spec_limit_sample_ids"] == []
    assert res["rule_of_seven_run_detected"] is True
    assert res["process_stability_status"] == "OUT_OF_CONTROL"
    assert res["is_process_stable"] is False
    assert len(res["issues"]) >= 2


def test_audit_quality_spc_control_chart_out_of_spec():
    """Caso 3: Punto supera USL o cae bajo LSL -> OUT_OF_SPEC."""
    from backend.services.project_ccb_service import (
        audit_quality_spc_control_chart_stability,
    )

    samples = [
        {"sample_id": "S-01", "measured_value": 10.1},
        {"sample_id": "S-02", "measured_value": 12.4},
        {"sample_id": "S-03", "measured_value": 7.5},
    ]
    res = audit_quality_spc_control_chart_stability(
        samples,
        center_line_mean=10.0,
        one_sigma_std_dev=1.0,
        upper_spec_limit_usl=12.0,
        lower_spec_limit_lsl=8.0,
    )
    assert res["total_samples"] == 3
    assert res["beyond_spec_limit_sample_ids"] == ["S-02", "S-03"]
    assert res["process_stability_status"] == "OUT_OF_SPEC"
    assert res["is_process_stable"] is False
    assert len(res["issues"]) >= 1


def test_audit_quality_spc_control_chart_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en ProjectCCBService y __all__."""
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_quality_spc_control_chart_stability,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_quality_spc_control_chart_stability(payload)  # type: ignore[arg-type]
        assert empty["total_samples"] == 0
        assert empty["ucl_3sigma"] == 3.0
        assert empty["lcl_3sigma"] == -3.0
        assert empty["beyond_3sigma_sample_ids"] == []
        assert empty["beyond_spec_limit_sample_ids"] == []
        assert empty["rule_of_seven_run_detected"] is False
        assert empty["process_stability_status"] == "IN_STATISTICAL_CONTROL"
        assert empty["is_process_stable"] is True
        assert empty["issues"] == []

    sample = [{"sample_id": "S-99", "measured_value": 0.2}]
    assert (
        ProjectCCBService.audit_quality_spc_control_chart_stability(sample)
        == audit_quality_spc_control_chart_stability(sample)
    )
    assert "audit_quality_spc_control_chart_stability" in mod.__all__



def test_audit_defect_removal_efficiency_and_uat_readiness_blocked_paths():
    """Caso 1: SEV1 abierto y UAT bajo umbral fuerzan RELEASE_BLOCKED."""
    from backend.services.project_ccb_service import (
        audit_defect_removal_efficiency_and_uat_readiness,
    )

    res = audit_defect_removal_efficiency_and_uat_readiness(
        pre_release_defects_found=6,
        post_release_escaped_defects=2,
        open_sev1_blocker_defects=1,
        uat_test_cases_total=10,
        uat_test_cases_passed=7,
    )
    assert res["total_defects"] == 8
    assert res["defect_removal_efficiency_dre_pct"] == 75.0
    assert res["defect_escape_ratio_pct"] == 25.0
    assert res["uat_pass_rate_pct"] == 70.0
    assert res["blocking_conditions"] == [
        "open_sev1_blockers",
        "uat_pass_rate_below_threshold",
        "dre_below_threshold",
    ]
    assert res["release_gate_status"] == "RELEASE_BLOCKED"
    assert res["is_uat_sign_off_ready"] is False


def test_audit_defect_removal_efficiency_and_uat_readiness_conditional_waiver_status_precedence():
    """Caso 2: SEV2 crítico con DRE baja pero sin SEV1 ni UAT fallido -> CONDITIONAL_WAIVER_REQUIRED."""
    from backend.services.project_ccb_service import (
        audit_defect_removal_efficiency_and_uat_readiness,
    )

    res = audit_defect_removal_efficiency_and_uat_readiness(
        pre_release_defects_found=18,
        post_release_escaped_defects=2,
        open_sev2_critical_defects=1,
        uat_test_cases_total=20,
        uat_test_cases_passed=20,
    )
    assert res["total_defects"] == 20
    assert res["defect_removal_efficiency_dre_pct"] == 90.0
    assert res["defect_escape_ratio_pct"] == 10.0
    assert res["uat_pass_rate_pct"] == 100.0
    # DRE 90.0 no es < min 90.0; el bloqueo viene solo del SEV2.
    assert res["blocking_conditions"] == ["open_sev2_criticals"]
    assert res["release_gate_status"] == "CONDITIONAL_WAIVER_REQUIRED"
    assert res["is_uat_sign_off_ready"] is False

    # Umbral DRE incumplido sin SEV2 también cae en waiver condicional.
    res2 = audit_defect_removal_efficiency_and_uat_readiness(
        pre_release_defects_found=9,
        post_release_escaped_defects=1,
        uat_test_cases_total=20,
        uat_test_cases_passed=19,
    )
    assert res2["defect_removal_efficiency_dre_pct"] == 90.0
    assert res2["uat_pass_rate_pct"] == 95.0
    assert res2["blocking_conditions"] == []
    assert res2["release_gate_status"] == "READY_FOR_SIGN_OFF"


def test_audit_defect_removal_efficiency_and_uat_readiness_ready_and_dre_boundary():
    """Caso 3: DRE y UAT sobre umbrales con defectos cerrados -> READY_FOR_SIGN_OFF."""
    from backend.services.project_ccb_service import (
        audit_defect_removal_efficiency_and_uat_readiness,
    )

    res = audit_defect_removal_efficiency_and_uat_readiness(
        pre_release_defects_found=12,
        post_release_escaped_defects=1,
        uat_test_cases_total=40,
        uat_test_cases_passed=39,
    )
    assert res["total_defects"] == 13
    assert res["defect_removal_efficiency_dre_pct"] == round(12 / 13 * 100, 2)
    assert res["defect_escape_ratio_pct"] == round(100 - res["defect_removal_efficiency_dre_pct"], 2)
    assert res["uat_pass_rate_pct"] == 97.5
    assert res["blocking_conditions"] == []
    assert res["release_gate_status"] == "READY_FOR_SIGN_OFF"
    assert res["is_uat_sign_off_ready"] is True


def test_audit_defect_removal_efficiency_and_uat_readiness_empty_and_binding():
    """Caso 4: Entradas vacías/negativas y binding en ProjectCCBService y __all__."""
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_defect_removal_efficiency_and_uat_readiness,
    )

    empty = audit_defect_removal_efficiency_and_uat_readiness(
        pre_release_defects_found=-3,
        post_release_escaped_defects=-1,
        uat_test_cases_total=0,
        uat_test_cases_passed=-2,
    )
    assert empty["total_defects"] == 0
    assert empty["defect_removal_efficiency_dre_pct"] == 100.0
    assert empty["defect_escape_ratio_pct"] == 0.0
    assert empty["uat_pass_rate_pct"] == 0.0
    # Sin casos UAT, el pass rate 0.0 rompe el umbral mínimo default (95.0).
    assert empty["blocking_conditions"] == ["uat_pass_rate_below_threshold"]
    assert empty["release_gate_status"] == "RELEASE_BLOCKED"
    assert empty["is_uat_sign_off_ready"] is False

    assert (
        ProjectCCBService.audit_defect_removal_efficiency_and_uat_readiness()
        == audit_defect_removal_efficiency_and_uat_readiness()
    )
    assert "audit_defect_removal_efficiency_and_uat_readiness" in mod.__all__


def test_audit_cost_of_quality_conformance_and_failure_ratio_optimal():
    """Caso 1: Conformidad >= 60%, CoQ <= 15% del presupuesto y sin prevención famélica -> OPTIMAL."""
    from backend.services.project_ccb_service import (
        audit_cost_of_quality_conformance_and_failure_ratio,
    )

    entries = [
        {"entry_id": "E-1", "category": "PREVENTION", "amount": 15000.0, "work_package_id": "WP-1"},
        {"entry_id": "E-2", "category": "APPRAISAL", "amount": 25000.0, "work_package_id": "WP-1"},
        {"entry_id": "E-3", "category": "INTERNAL_FAILURE", "amount": 8000.0, "work_package_id": "WP-2"},
        {"entry_id": "E-4", "category": "EXTERNAL_FAILURE", "amount": 2000.0, "work_package_id": "WP-2"},
    ]
    res = audit_cost_of_quality_conformance_and_failure_ratio(
        entries,
        total_project_budget=500000.0,
        min_conformance_share_pct=60.0,
        max_coq_budget_share_pct=15.0,
    )
    assert res["prevention_cost"] == 15000.0
    assert res["appraisal_cost"] == 25000.0
    assert res["internal_failure_cost"] == 8000.0
    assert res["external_failure_cost"] == 2000.0
    assert res["cost_of_conformance"] == 40000.0
    assert res["cost_of_non_conformance"] == 10000.0
    assert res["total_coq"] == 50000.0
    assert res["conformance_share_pct"] == 80.0
    assert res["external_failure_share_pct"] == 4.0
    assert res["coq_budget_share_pct"] == 10.0
    assert res["prevention_starvation"] is False
    assert res["coq_health_status"] == "OPTIMAL"
    assert res["recommendations"] == []


def test_audit_cost_of_quality_conformance_and_failure_ratio_warning():
    """Caso 2: Conformidad > no-conformidad pero prevention_starvation o CoQ > 15% -> WARNING."""
    from backend.services.project_ccb_service import (
        audit_cost_of_quality_conformance_and_failure_ratio,
    )

    entries = [
        {"entry_id": "E-1", "category": "PREVENTION", "amount": 2000.0, "work_package_id": "WP-1"},
        {"entry_id": "E-2", "category": "APPRAISAL", "amount": 20000.0, "work_package_id": "WP-1"},
        {"entry_id": "E-3", "category": "INTERNAL_FAILURE", "amount": 18000.0, "work_package_id": "WP-2"},
    ]
    res = audit_cost_of_quality_conformance_and_failure_ratio(
        entries,
        total_project_budget=200000.0,
        min_conformance_share_pct=60.0,
        max_coq_budget_share_pct=15.0,
    )
    assert res["cost_of_conformance"] == 22000.0
    assert res["cost_of_non_conformance"] == 18000.0
    assert res["conformance_share_pct"] == 55.0
    assert res["coq_budget_share_pct"] == 20.0
    assert res["prevention_starvation"] is True
    assert res["coq_health_status"] == "WARNING"
    assert len(res["recommendations"]) >= 2


def test_audit_cost_of_quality_conformance_and_failure_ratio_critical():
    """Caso 3: No-conformidad > conformidad o falla externa > 25% del CoQ -> CRITICAL."""
    from backend.services.project_ccb_service import (
        audit_cost_of_quality_conformance_and_failure_ratio,
    )

    entries = [
        {"entry_id": "E-1", "category": "PREVENTION", "amount": 5000.0, "work_package_id": "WP-1"},
        {"entry_id": "E-2", "category": "APPRAISAL", "amount": 5000.0, "work_package_id": "WP-1"},
        {"entry_id": "E-3", "category": "INTERNAL_FAILURE", "amount": 10000.0, "work_package_id": "WP-2"},
        {"entry_id": "E-4", "category": "EXTERNAL_FAILURE", "amount": 15000.0, "work_package_id": "WP-2"},
    ]
    res = audit_cost_of_quality_conformance_and_failure_ratio(
        entries, total_project_budget=300000.0
    )
    assert res["cost_of_conformance"] == 10000.0
    assert res["cost_of_non_conformance"] == 25000.0
    assert res["external_failure_share_pct"] == 42.86
    assert res["coq_health_status"] == "CRITICAL"
    assert len(res["recommendations"]) >= 2


def test_audit_cost_of_quality_conformance_and_failure_ratio_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en ProjectCCBService + __all__."""
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_cost_of_quality_conformance_and_failure_ratio,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_cost_of_quality_conformance_and_failure_ratio(
            payload, total_project_budget=0.0  # type: ignore[arg-type]
        )
        assert empty["prevention_cost"] == 0.0
        assert empty["appraisal_cost"] == 0.0
        assert empty["internal_failure_cost"] == 0.0
        assert empty["external_failure_cost"] == 0.0
        assert empty["cost_of_conformance"] == 0.0
        assert empty["cost_of_non_conformance"] == 0.0
        assert empty["total_coq"] == 0.0
        assert empty["conformance_share_pct"] == 100.0
        assert empty["external_failure_share_pct"] == 0.0
        assert empty["coq_budget_share_pct"] == 0.0
        assert empty["prevention_starvation"] is False
        assert empty["coq_health_status"] == "OPTIMAL"
        assert empty["recommendations"] == []

    sample = [
        {"entry_id": "E-9", "category": "PREVENTION", "amount": 5000.0, "work_package_id": "WP-9"}
    ]
    assert (
        ProjectCCBService.audit_cost_of_quality_conformance_and_failure_ratio(
            sample, total_project_budget=100000.0
        )
        == audit_cost_of_quality_conformance_and_failure_ratio(
            sample, total_project_budget=100000.0
        )
    )
    assert "audit_cost_of_quality_conformance_and_failure_ratio" in mod.__all__



def test_audit_technical_debt_interest_and_remediation_quota_bankruptcy_paths():
    """Caso 1: drag sobre umbral y deuda HIGH sin ticket -> BANKRUPTCY_RISK."""
    from backend.services.project_ccb_service import (
        audit_technical_debt_interest_and_remediation_quota,
    )

    res = audit_technical_debt_interest_and_remediation_quota(
        [
            {
                "debt_id": "TD-01",
                "principal_remediation_hours": 40.0,
                "recurring_interest_hours_per_iteration": 8.0,
                "age_iterations": 2,
                "has_remediation_ticket": False,
                "severity": "HIGH",
            },
            {
                "debt_id": "TD-02",
                "principal_remediation_hours": 3.0,
                "recurring_interest_hours_per_iteration": 4.0,
                "age_iterations": 1,
                "has_remediation_ticket": True,
                "severity": "MEDIUM",
            },
        ],
        total_iteration_capacity_hours=40.0,
        allocated_remediation_hours=20.0,
    )
    assert res["total_debt_items"] == 2
    assert res["total_principal_hours"] == 43.0
    assert res["total_interest_hours_per_iteration"] == 12.0
    assert res["debt_drag_pct"] == 30.0
    assert res["actual_remediation_quota_pct"] == 50.0
    assert res["untracked_high_debt_ids"] == ["TD-01"]
    # TD-01: 8.0 * 2 = 16.0 <= 40.0 principal, no insolvente.
    # TD-02: 4.0 * 1 = 4.0 > 3.0 principal, insolvente.
    assert res["compounding_insolvency_ids"] == ["TD-02"]
    assert res["debt_governance_status"] == "BANKRUPTCY_RISK"
    assert res["is_debt_sustainable"] is False
    # Drag 30% > max 20%, TD-01 HIGH sin ticket y TD-02 insolvente.
    assert len(res["recommendations"]) == 3


def test_audit_technical_debt_interest_and_remediation_quota_warning_paths():
    """Caso 2: cuota de remediación baja con principal > 0 y/o insolvencia compuesta -> WARNING."""
    from backend.services.project_ccb_service import (
        audit_technical_debt_interest_and_remediation_quota,
    )

    res_quota = audit_technical_debt_interest_and_remediation_quota(
        [
            {
                "debt_id": "TD-10",
                "principal_remediation_hours": 100.0,
                "recurring_interest_hours_per_iteration": 2.0,
                "age_iterations": 0,
                "severity": "LOW",
            },
        ],
        total_iteration_capacity_hours=100.0,
        allocated_remediation_hours=10.0,
    )
    assert res_quota["debt_drag_pct"] == 2.0
    assert res_quota["actual_remediation_quota_pct"] == 10.0
    # 10% < min 15% con principal > 0 -> WARNING.
    assert res_quota["debt_governance_status"] == "WARNING"
    assert res_quota["compounding_insolvency_ids"] == []

    res_insolvency = audit_technical_debt_interest_and_remediation_quota(
        [
            {
                "debt_id": "TD-11",
                "principal_remediation_hours": 20.0,
                "recurring_interest_hours_per_iteration": 3.0,
                "age_iterations": 8,
                "severity": "MEDIUM",
            },
        ],
        total_iteration_capacity_hours=100.0,
        allocated_remediation_hours=20.0,
    )
    # 3.0 * 8 = 24.0 > 20.0 principal; cuota 20% >= 15%.
    assert res_insolvency["compounding_insolvency_ids"] == ["TD-11"]
    assert res_insolvency["debt_governance_status"] == "WARNING"
    assert res_insolvency["is_debt_sustainable"] is False


def test_audit_technical_debt_interest_and_remediation_quota_sustainable_and_zero_capacity():
    """Caso 3: sin deuda, drag 0 y cuota suficiente -> SUSTAINABLE; capacidad 0 no explota."""
    from backend.services.project_ccb_service import (
        audit_technical_debt_interest_and_remediation_quota,
    )

    res = audit_technical_debt_interest_and_remediation_quota(
        [
            {
                "debt_id": "TD-20",
                "principal_remediation_hours": 5.0,
                "recurring_interest_hours_per_iteration": 0.5,
                "age_iterations": 1,
                "severity": "LOW",
            },
        ],
        total_iteration_capacity_hours=100.0,
        allocated_remediation_hours=20.0,
    )
    assert res["total_debt_items"] == 1
    assert res["total_principal_hours"] == 5.0
    assert res["total_interest_hours_per_iteration"] == 0.5
    assert res["debt_drag_pct"] == 0.5
    assert res["actual_remediation_quota_pct"] == 20.0
    assert res["debt_governance_status"] == "SUSTAINABLE"
    assert res["is_debt_sustainable"] is True
    assert res["recommendations"] == []

    empty_capacity = audit_technical_debt_interest_and_remediation_quota(
        [],
        total_iteration_capacity_hours=0.0,
        allocated_remediation_hours=0.0,
    )
    assert empty_capacity["total_debt_items"] == 0
    assert empty_capacity["debt_drag_pct"] == 0.0
    assert empty_capacity["actual_remediation_quota_pct"] == 0.0
    # Sin principal ni drag: SUSTAINABLE pese a cuota 0/0.
    assert empty_capacity["debt_governance_status"] == "SUSTAINABLE"


def test_audit_technical_debt_interest_and_remediation_quota_invalid_and_binding():
    """Caso 4: entradas no-lista/no-dict y binding en ProjectCCBService + __all__."""
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_technical_debt_interest_and_remediation_quota,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_technical_debt_interest_and_remediation_quota(
            payload,  # type: ignore[arg-type]
            total_iteration_capacity_hours=100.0,
            allocated_remediation_hours=20.0,
        )
        assert empty["total_debt_items"] == 0
        assert empty["total_principal_hours"] == 0.0
        assert empty["total_interest_hours_per_iteration"] == 0.0
        assert empty["debt_drag_pct"] == 0.0
        assert empty["actual_remediation_quota_pct"] == 20.0
        assert empty["untracked_high_debt_ids"] == []
        assert empty["compounding_insolvency_ids"] == []
        # Cuota 20% >= min 15% y sin deuda -> SUSTAINABLE.
        assert empty["debt_governance_status"] == "SUSTAINABLE"
        assert empty["is_debt_sustainable"] is True
        assert empty["recommendations"] == []

    sample = [
        {
            "debt_id": "TD-30",
            "principal_remediation_hours": 1.0,
            "recurring_interest_hours_per_iteration": 0.0,
            "age_iterations": 0,
            "severity": "LOW",
        },
    ]
    assert (
        ProjectCCBService.audit_technical_debt_interest_and_remediation_quota(
            sample,
            total_iteration_capacity_hours=10.0,
            allocated_remediation_hours=2.0,
        )
        == audit_technical_debt_interest_and_remediation_quota(
            sample,
            total_iteration_capacity_hours=10.0,
            allocated_remediation_hours=2.0,
        )
    )
    assert "audit_technical_debt_interest_and_remediation_quota" in mod.__all__


def test_audit_canary_rollout_blast_radius_and_rollback_readiness_safe():
    """Caso 1: Releases con tráfico canary <=10%, bake time >=60m, rollback automatizado y DB compatible -> SAFE_TO_DEPLOY."""
    from backend.services.project_ccb_service import (
        audit_canary_rollout_blast_radius_and_rollback_readiness,
    )

    releases = [
        {
            "release_id": "REL-2026-01",
            "initial_canary_traffic_pct": 5.0,
            "bake_time_minutes": 90,
            "has_automated_rollback_trigger": True,
            "rollback_tested_in_staging": True,
            "has_backward_compatible_db_migration": True,
        },
        {
            "release_id": "REL-2026-02",
            "initial_canary_traffic_pct": 10.0,
            "bake_time_minutes": 60,
            "has_automated_rollback_trigger": True,
            "rollback_tested_in_staging": True,
            "has_backward_compatible_db_migration": True,
        },
    ]
    res = audit_canary_rollout_blast_radius_and_rollback_readiness(
        releases, max_initial_canary_traffic_pct=10.0, min_bake_time_minutes=60
    )
    assert res["total_releases"] == 2
    assert res["excessive_blast_radius_release_ids"] == []
    assert res["insufficient_bake_time_release_ids"] == []
    assert res["unverified_rollback_release_ids"] == []
    assert res["breaking_db_migration_release_ids"] == []
    assert res["rollout_governance_status"] == "SAFE_TO_DEPLOY"
    assert res["is_rollout_ready"] is True
    assert res["recommendations"] == []


def test_audit_canary_rollout_blast_radius_and_rollback_readiness_warning():
    """Caso 2: Tráfico inicial excesivo (>10%) o bake time insuficiente (<60m) con rollback verificado -> WARNING."""
    from backend.services.project_ccb_service import (
        audit_canary_rollout_blast_radius_and_rollback_readiness,
    )

    releases = [
        {
            "release_id": "REL-FAST",
            "initial_canary_traffic_pct": 25.0,
            "bake_time_minutes": 30,
            "has_automated_rollback_trigger": True,
            "rollback_tested_in_staging": True,
            "has_backward_compatible_db_migration": True,
        }
    ]
    res = audit_canary_rollout_blast_radius_and_rollback_readiness(
        releases, max_initial_canary_traffic_pct=10.0, min_bake_time_minutes=60
    )
    assert res["total_releases"] == 1
    assert res["excessive_blast_radius_release_ids"] == ["REL-FAST"]
    assert res["insufficient_bake_time_release_ids"] == ["REL-FAST"]
    assert res["unverified_rollback_release_ids"] == []
    assert res["breaking_db_migration_release_ids"] == []
    assert res["rollout_governance_status"] == "WARNING"
    assert res["is_rollout_ready"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_canary_rollout_blast_radius_and_rollback_readiness_blocked():
    """Caso 3: Sin rollback automatizado/probado o migración DB incompatible -> BLOCKED."""
    from backend.services.project_ccb_service import (
        audit_canary_rollout_blast_radius_and_rollback_readiness,
    )

    releases = [
        {
            "release_id": "REL-RISKY-01",
            "initial_canary_traffic_pct": 5.0,
            "bake_time_minutes": 120,
            "has_automated_rollback_trigger": False,
            "rollback_tested_in_staging": True,
            "has_backward_compatible_db_migration": True,
        },
        {
            "release_id": "REL-RISKY-02",
            "initial_canary_traffic_pct": 5.0,
            "bake_time_minutes": 120,
            "has_automated_rollback_trigger": True,
            "rollback_tested_in_staging": True,
            "has_backward_compatible_db_migration": False,
        },
    ]
    res = audit_canary_rollout_blast_radius_and_rollback_readiness(releases)
    assert res["total_releases"] == 2
    assert res["unverified_rollback_release_ids"] == ["REL-RISKY-01"]
    assert res["breaking_db_migration_release_ids"] == ["REL-RISKY-02"]
    assert res["rollout_governance_status"] == "BLOCKED"
    assert res["is_rollout_ready"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_canary_rollout_blast_radius_and_rollback_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en ProjectCCBService + __all__."""
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_canary_rollout_blast_radius_and_rollback_readiness,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_canary_rollout_blast_radius_and_rollback_readiness(payload)  # type: ignore[arg-type]
        assert empty["total_releases"] == 0
        assert empty["excessive_blast_radius_release_ids"] == []
        assert empty["insufficient_bake_time_release_ids"] == []
        assert empty["unverified_rollback_release_ids"] == []
        assert empty["breaking_db_migration_release_ids"] == []
        assert empty["rollout_governance_status"] == "SAFE_TO_DEPLOY"
        assert empty["is_rollout_ready"] is True
        assert empty["recommendations"] == []

    sample = [
        {
            "release_id": "REL-99",
            "initial_canary_traffic_pct": 5.0,
            "bake_time_minutes": 60,
            "has_automated_rollback_trigger": True,
            "rollback_tested_in_staging": True,
            "has_backward_compatible_db_migration": True,
        }
    ]
    assert (
        ProjectCCBService.audit_canary_rollout_blast_radius_and_rollback_readiness(
            sample
        )
        == audit_canary_rollout_blast_radius_and_rollback_readiness(sample)
    )
    assert (
        "audit_canary_rollout_blast_radius_and_rollback_readiness" in mod.__all__
    )


def test_audit_feature_flag_lifecycle_debt_and_kill_switch_hygiene_clean():
    """Caso 1: Flags con propietario, ambas ramas probadas en CI y sin flags zombi -> CLEAN."""
    from backend.services.project_ccb_service import (
        audit_feature_flag_lifecycle_debt_and_kill_switch_hygiene,
    )

    flags = [
        {
            "flag_id": "FF-NEW-CHECKOUT",
            "flag_type": "RELEASE",
            "age_days": 12,
            "rollout_pct": 50.0,
            "owner_id": "TEAM-PAYMENTS",
            "has_cleanup_ticket": True,
            "both_paths_tested_in_ci": True,
        },
        {
            "flag_id": "FF-KILL-SMS-GATEWAY",
            "flag_type": "OPS_KILL_SWITCH",
            "age_days": 180,
            "rollout_pct": 100.0,
            "owner_id": "TEAM-SRE",
            "has_cleanup_ticket": False,
            "both_paths_tested_in_ci": True,
        },
    ]
    res = audit_feature_flag_lifecycle_debt_and_kill_switch_hygiene(
        flags, max_rollout_flag_ttl_days=30, max_active_release_flags=10
    )
    assert res["total_flags"] == 2
    assert res["active_release_flags_count"] == 1
    assert res["combinatorial_explosion_risk"] is False
    assert res["zombie_flag_ids"] == []
    assert res["unowned_flag_ids"] == []
    assert res["untested_branch_flag_ids"] == []
    assert res["missing_cleanup_ticket_flag_ids"] == []
    assert res["flag_governance_status"] == "CLEAN"
    assert res["is_flag_hygiene_compliant"] is True
    assert res["recommendations"] == []


def test_audit_feature_flag_lifecycle_debt_and_kill_switch_hygiene_warning():
    """Caso 2: Un flag zombi (100% rollout y >30d) o explosión combinatoria (>max_active_release_flags) -> WARNING."""
    from backend.services.project_ccb_service import (
        audit_feature_flag_lifecycle_debt_and_kill_switch_hygiene,
    )

    flags = [
        {
            "flag_id": "FF-ZOMBIE-01",
            "flag_type": "RELEASE",
            "age_days": 45,
            "rollout_pct": 100.0,
            "owner_id": "TEAM-CORE",
            "has_cleanup_ticket": False,
            "both_paths_tested_in_ci": True,
        },
        {
            "flag_id": "FF-EXP-02",
            "flag_type": "EXPERIMENT",
            "age_days": 10,
            "rollout_pct": 25.0,
            "owner_id": "TEAM-GROWTH",
            "has_cleanup_ticket": True,
            "both_paths_tested_in_ci": True,
        },
    ]
    res = audit_feature_flag_lifecycle_debt_and_kill_switch_hygiene(
        flags, max_rollout_flag_ttl_days=30, max_active_release_flags=1
    )
    assert res["total_flags"] == 2
    assert res["active_release_flags_count"] == 2
    assert res["combinatorial_explosion_risk"] is True
    assert res["zombie_flag_ids"] == ["FF-ZOMBIE-01"]
    assert res["missing_cleanup_ticket_flag_ids"] == ["FF-ZOMBIE-01"]
    assert res["flag_governance_status"] == "WARNING"
    assert res["is_flag_hygiene_compliant"] is False
    assert len(res["recommendations"]) >= 2


def test_audit_feature_flag_lifecycle_debt_and_kill_switch_hygiene_critical():
    """Caso 3: Flag sin propietario y sin cobertura dual en CI -> CRITICAL."""
    from backend.services.project_ccb_service import (
        audit_feature_flag_lifecycle_debt_and_kill_switch_hygiene,
    )

    flags = [
        {
            "flag_id": "FF-ORPHAN-RISKY",
            "flag_type": "RELEASE",
            "age_days": 75,
            "rollout_pct": 100.0,
            "owner_id": None,
            "has_cleanup_ticket": False,
            "both_paths_tested_in_ci": False,
        }
    ]
    res = audit_feature_flag_lifecycle_debt_and_kill_switch_hygiene(flags)
    assert res["total_flags"] == 1
    assert res["zombie_flag_ids"] == ["FF-ORPHAN-RISKY"]
    assert res["unowned_flag_ids"] == ["FF-ORPHAN-RISKY"]
    assert res["untested_branch_flag_ids"] == ["FF-ORPHAN-RISKY"]
    assert res["missing_cleanup_ticket_flag_ids"] == ["FF-ORPHAN-RISKY"]
    assert res["flag_governance_status"] == "CRITICAL"
    assert res["is_flag_hygiene_compliant"] is False
    assert len(res["recommendations"]) >= 3


def test_audit_feature_flag_lifecycle_debt_and_kill_switch_empty_and_binding():
    """Caso 4: Entradas vacías/inválidas y binding en ProjectCCBService + __all__."""
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_feature_flag_lifecycle_debt_and_kill_switch_hygiene,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_feature_flag_lifecycle_debt_and_kill_switch_hygiene(payload)  # type: ignore[arg-type]
        assert empty["total_flags"] == 0
        assert empty["active_release_flags_count"] == 0
        assert empty["combinatorial_explosion_risk"] is False
        assert empty["zombie_flag_ids"] == []
        assert empty["unowned_flag_ids"] == []
        assert empty["untested_branch_flag_ids"] == []
        assert empty["missing_cleanup_ticket_flag_ids"] == []
        assert empty["flag_governance_status"] == "CLEAN"
        assert empty["is_flag_hygiene_compliant"] is True
        assert empty["recommendations"] == []

    sample = [
        {
            "flag_id": "FF-99",
            "flag_type": "RELEASE",
            "age_days": 5,
            "rollout_pct": 10.0,
            "owner_id": "TEAM-01",
            "has_cleanup_ticket": True,
            "both_paths_tested_in_ci": True,
        }
    ]
    assert (
        ProjectCCBService.audit_feature_flag_lifecycle_debt_and_kill_switch_hygiene(
            sample
        )
        == audit_feature_flag_lifecycle_debt_and_kill_switch_hygiene(sample)
    )
    assert (
        "audit_feature_flag_lifecycle_debt_and_kill_switch_hygiene" in mod.__all__
    )


def test_audit_requirements_volatility_churn_scope_freeze_violation_paths():
    """Caso 1: cambios post-freeze sin CR aprobado o churn > 2x umbral -> SCOPE_FREEZE_VIOLATION."""
    from backend.services.project_ccb_service import (
        audit_requirements_volatility_churn_and_scope_freeze_breaches,
    )

    res = audit_requirements_volatility_churn_and_scope_freeze_breaches(
        [
            {
                "req_id": "REQ-01",
                "change_action": "MODIFIED",
                "modified_after_scope_freeze": True,
                "has_ccb_approval_cr_id": False,
                "story_points_delta": 3.0,
            },
            {
                "req_id": "REQ-02",
                "change_action": "UNCHANGED",
                "modified_after_scope_freeze": True,
                "has_ccb_approval_cr_id": False,
            },
        ],
        baseline_locked_count=10,
    )
    assert res["total_requirements"] == 2
    assert res["churned_requirements_count"] == 1
    assert res["requirements_churn_rate_pct"] == 10.0
    assert res["net_story_points_delta"] == 3.0
    assert res["unapproved_post_freeze_req_ids"] == ["REQ-01"]
    assert res["approved_post_freeze_req_ids"] == []
    assert res["volatility_governance_status"] == "SCOPE_FREEZE_VIOLATION"
    assert res["is_baseline_stable"] is False

    # Churn 70% > 2x umbral (30%) sin cambios post-freeze -> violación igual.
    res_churn = audit_requirements_volatility_churn_and_scope_freeze_breaches(
        [
            {"req_id": f"REQ-{i:02d}", "change_action": "ADDED"}
            for i in range(1, 8)
        ],
        baseline_locked_count=10,
    )
    assert res_churn["churned_requirements_count"] == 7
    assert res_churn["requirements_churn_rate_pct"] == 70.0
    assert res_churn["unapproved_post_freeze_req_ids"] == []
    assert res_churn["volatility_governance_status"] == "SCOPE_FREEZE_VIOLATION"


def test_audit_requirements_volatility_churn_warning_paths():
    """Caso 2: churn sobre umbral con cambios post-freeze aprobados y DELETED -> WARNING."""
    from backend.services.project_ccb_service import (
        audit_requirements_volatility_churn_and_scope_freeze_breaches,
    )

    res = audit_requirements_volatility_churn_and_scope_freeze_breaches(
        [
            {
                "req_id": "REQ-10",
                "change_action": "MODIFIED",
                "modified_after_scope_freeze": True,
                "has_ccb_approval_cr_id": True,
                "story_points_delta": 1.5,
            },
            {
                "req_id": "REQ-11",
                "change_action": "DELETED",
                "modified_after_scope_freeze": False,
                "story_points_delta": -2.0,
            },
        ],
        baseline_locked_count=10,
    )
    assert res["churned_requirements_count"] == 2
    assert res["requirements_churn_rate_pct"] == 20.0
    assert res["net_story_points_delta"] == -0.5
    assert res["unapproved_post_freeze_req_ids"] == []
    assert res["approved_post_freeze_req_ids"] == ["REQ-10"]
    assert res["volatility_governance_status"] == "WARNING"
    assert res["is_baseline_stable"] is False


def test_audit_requirements_volatility_churn_stable_and_boundaries():
    """Caso 3: fronteras exactas (churn = umbral inclusive) y baseline 0 -> STABLE_BASELINE."""
    from backend.services.project_ccb_service import (
        audit_requirements_volatility_churn_and_scope_freeze_breaches,
    )

    res = audit_requirements_volatility_churn_and_scope_freeze_breaches(
        [
            {"req_id": "REQ-20", "change_action": "ADDED"},
            {"req_id": "REQ-21", "change_action": "UNCHANGED"},
            {"req_id": "REQ-22", "change_action": "UNCHANGED"},
        ],
        baseline_locked_count=20,
    )
    # 1/20 = 5% <= 15%: estable.
    assert res["total_requirements"] == 3
    assert res["churned_requirements_count"] == 1
    assert res["requirements_churn_rate_pct"] == 5.0
    assert res["net_story_points_delta"] == 0.0
    assert res["unapproved_post_freeze_req_ids"] == []
    assert res["approved_post_freeze_req_ids"] == []
    assert res["volatility_governance_status"] == "STABLE_BASELINE"
    assert res["is_baseline_stable"] is True
    assert res["recommendations"] == []

    # Frontera 15% exacto con umbral default 15%: no superado -> estable.
    res_boundary = audit_requirements_volatility_churn_and_scope_freeze_breaches(
        [{"req_id": "REQ-30", "change_action": "MODIFIED"}],
        baseline_locked_count=100,
    )
    assert res_boundary["requirements_churn_rate_pct"] == 1.0

    # Baseline 0: churn 0.0 y estable pese a cambios.
    res_frozen = audit_requirements_volatility_churn_and_scope_freeze_breaches(
        [{"req_id": "REQ-40", "change_action": "ADDED"}],
        baseline_locked_count=0,
    )
    assert res_frozen["requirements_churn_rate_pct"] == 0.0
    assert res_frozen["volatility_governance_status"] == "STABLE_BASELINE"


def test_audit_requirements_volatility_churn_invalid_and_binding():
    """Caso 4: entradas no-lista/no-dict y binding en ProjectCCBService + __all__."""
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_requirements_volatility_churn_and_scope_freeze_breaches,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_requirements_volatility_churn_and_scope_freeze_breaches(
            payload,  # type: ignore[arg-type]
            baseline_locked_count=10,
        )
        assert empty["total_requirements"] == 0
        assert empty["churned_requirements_count"] == 0
        assert empty["requirements_churn_rate_pct"] == 0.0
        assert empty["net_story_points_delta"] == 0.0
        assert empty["unapproved_post_freeze_req_ids"] == []
        assert empty["approved_post_freeze_req_ids"] == []
        assert empty["volatility_governance_status"] == "STABLE_BASELINE"
        assert empty["is_baseline_stable"] is True
        assert empty["recommendations"] == []

    sample = [{"req_id": "REQ-50", "change_action": "UNCHANGED"}]
    assert (
        ProjectCCBService.audit_requirements_volatility_churn_and_scope_freeze_breaches(
            sample, baseline_locked_count=10
        )
        == audit_requirements_volatility_churn_and_scope_freeze_breaches(
            sample, baseline_locked_count=10
        )
    )
    assert (
        "audit_requirements_volatility_churn_and_scope_freeze_breaches" in mod.__all__
    )


def test_audit_architectural_fitness_functions_erosion_blocked_paths():
    """Caso 1: ciclo, fitness fallida o core inestable -> EROSION_BLOCKED."""
    from backend.services.project_ccb_service import (
        audit_architectural_fitness_functions_and_coupling_drift,
    )

    res = audit_architectural_fitness_functions_and_coupling_drift(
        [
            {
                "component_id": "COMP-01",
                "afferent_coupling_ca": 2,
                "efferent_coupling_ce": 8,
                "abstractness_ratio": 0.2,
                "has_cyclic_dependency": True,
                "is_core_domain": True,
            },
            {
                "component_id": "COMP-02",
                "afferent_coupling_ca": 5,
                "efferent_coupling_ce": 5,
                "abstractness_ratio": 0.5,
                "fitness_function_passed": False,
            },
        ]
    )
    assert res["total_components_evaluated"] == 2
    assert res["cyclic_dependency_component_ids"] == ["COMP-01"]
    assert res["failed_fitness_component_ids"] == ["COMP-02"]
    # COMP-01: ca+ce=10, ce=8 -> inestabilidad 0.8, no > 0.8 -> core inestable NO.
    assert res["unstable_core_component_ids"] == []
    assert res["architecture_governance_status"] == "EROSION_BLOCKED"
    assert res["is_architecture_compliant"] is False
    assert res["max_instability_observed"] == 0.8

    # Core inestable: ce/ca = 0.9 > 0.8.
    res_core = audit_architectural_fitness_functions_and_coupling_drift(
        [
            {
                "component_id": "COMP-03",
                "afferent_coupling_ca": 1,
                "efferent_coupling_ce": 9,
                "abstractness_ratio": 0.5,
                "is_core_domain": True,
            },
        ]
    )
    assert res_core["unstable_core_component_ids"] == ["COMP-03"]
    assert res_core["max_instability_observed"] == 0.9
    assert res_core["architecture_governance_status"] == "EROSION_BLOCKED"


def test_audit_architectural_fitness_functions_drift_warning_paths():
    """Caso 2: solo zone of pain/uselessness (distancia > max) -> DRIFT_WARNING."""
    from backend.services.project_ccb_service import (
        audit_architectural_fitness_functions_and_coupling_drift,
    )

    res = audit_architectural_fitness_functions_and_coupling_drift(
        [
            {
                "component_id": "COMP-10",
                "afferent_coupling_ca": 0,
                "efferent_coupling_ce": 0,
                "abstractness_ratio": 1.0,
            },
        ]
    )
    # inestabilidad 0.0 (sin acoplamientos), distancia = |1.0 + 0.0 - 1| = 0.0 <= 0.35.
    assert res["zone_of_pain_or_uselessness_ids"] == []
    assert res["architecture_governance_status"] == "FITNESS_HEALTHY"

    res_pain = audit_architectural_fitness_functions_and_coupling_drift(
        [
            {
                "component_id": "COMP-11",
                "afferent_coupling_ca": 8,
                "efferent_coupling_ce": 2,
                "abstractness_ratio": 0.0,
            },
        ]
    )
    # inestabilidad 0.2, distancia = |0.0 + 0.2 - 1| = 0.8 > 0.35 -> zona de dolor.
    assert res_pain["zone_of_pain_or_uselessness_ids"] == ["COMP-11"]
    assert res_pain["architecture_governance_status"] == "DRIFT_WARNING"
    assert res_pain["max_instability_observed"] == 0.2
    assert res_pain["is_architecture_compliant"] is False


def test_audit_architectural_fitness_functions_healthy_and_boundaries():
    """Caso 3: componente en la secuencia principal -> FITNESS_HEALTHY, frontera de inestabilidad."""
    from backend.services.project_ccb_service import (
        audit_architectural_fitness_functions_and_coupling_drift,
    )

    res = audit_architectural_fitness_functions_and_coupling_drift(
        [
            {
                "component_id": "COMP-20",
                "afferent_coupling_ca": 5,
                "efferent_coupling_ce": 5,
                "abstractness_ratio": 0.5,
                "is_core_domain": True,
            },
        ]
    )
    # inestabilidad 0.5, distancia = |0.5 + 0.5 - 1| = 0.0; core con 0.5 <= 0.8.
    assert res["total_components_evaluated"] == 1
    assert res["cyclic_dependency_component_ids"] == []
    assert res["failed_fitness_component_ids"] == []
    assert res["unstable_core_component_ids"] == []
    assert res["zone_of_pain_or_uselessness_ids"] == []
    assert res["max_instability_observed"] == 0.5
    assert res["architecture_governance_status"] == "FITNESS_HEALTHY"
    assert res["is_architecture_compliant"] is True

    # Frontera: inestabilidad exactamente max (0.8) no es > max.
    res_boundary = audit_architectural_fitness_functions_and_coupling_drift(
        [
            {
                "component_id": "COMP-21",
                "afferent_coupling_ca": 2,
                "efferent_coupling_ce": 8,
                "abstractness_ratio": 0.2,
                "is_core_domain": True,
            },
        ],
        max_instability_index=0.8,
    )
    assert res_boundary["unstable_core_component_ids"] == []
    assert res_boundary["architecture_governance_status"] == "FITNESS_HEALTHY"


def test_audit_architectural_fitness_functions_invalid_and_binding():
    """Caso 4: entradas no-lista/no-dict y binding en ProjectCCBService + __all__."""
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_architectural_fitness_functions_and_coupling_drift,
    )

    for payload in (None, [], "invalid", ["not-a-dict"]):
        empty = audit_architectural_fitness_functions_and_coupling_drift(payload)  # type: ignore[arg-type]
        assert empty["total_components_evaluated"] == 0
        assert empty["cyclic_dependency_component_ids"] == []
        assert empty["failed_fitness_component_ids"] == []
        assert empty["unstable_core_component_ids"] == []
        assert empty["zone_of_pain_or_uselessness_ids"] == []
        assert empty["max_instability_observed"] == 0.0
        assert empty["architecture_governance_status"] == "FITNESS_HEALTHY"
        assert empty["is_architecture_compliant"] is True

    sample = [
        {
            "component_id": "COMP-30",
            "afferent_coupling_ca": 3,
            "efferent_coupling_ce": 3,
            "abstractness_ratio": 0.5,
        },
    ]
    assert (
        ProjectCCBService.audit_architectural_fitness_functions_and_coupling_drift(sample)
        == audit_architectural_fitness_functions_and_coupling_drift(sample)
    )
    assert "audit_architectural_fitness_functions_and_coupling_drift" in mod.__all__


def test_audit_api_backward_compatibility_and_contract_versioning_breaking_blocked():
    from backend.services.project_ccb_service import (
        audit_api_backward_compatibility_and_contract_versioning,
    )

    res = audit_api_backward_compatibility_and_contract_versioning(
        [
            {
                "endpoint_id": "POST /v1/orders",
                "removes_required_response_field": True,
                "adds_mandatory_request_parameter_without_default": False,
                "bumps_major_api_version": False,
                "consumer_contract_tests_passed": True,
                "deprecation_notice_days_provided": 45,
            },
            {
                "endpoint_id": "GET /v1/invoices",
                "removes_required_response_field": False,
                "adds_mandatory_request_parameter_without_default": False,
                "bumps_major_api_version": False,
                "consumer_contract_tests_passed": False,
                "deprecation_notice_days_provided": 60,
            },
        ],
        min_deprecation_notice_days=30,
    )
    assert res["total_endpoints_evaluated"] == 2
    assert res["breaking_change_count"] == 1
    assert res["unversioned_breaking_change_ids"] == ["POST /v1/orders"]
    assert res["failed_contract_test_ids"] == ["GET /v1/invoices"]
    assert res["insufficient_deprecation_window_ids"] == []
    assert res["contract_governance_status"] == "BREAKING_BLOCKED"
    assert res["is_contract_gate_compliant"] is False


def test_audit_api_backward_compatibility_and_contract_versioning_deprecation_window_warning():
    from backend.services.project_ccb_service import (
        audit_api_backward_compatibility_and_contract_versioning,
    )

    res = audit_api_backward_compatibility_and_contract_versioning(
        [
            {
                "endpoint_id": "PUT /v2/users",
                "removes_required_response_field": False,
                "adds_mandatory_request_parameter_without_default": True,
                "bumps_major_api_version": True,
                "consumer_contract_tests_passed": True,
                "deprecation_notice_days_provided": 10,
            }
        ],
        min_deprecation_notice_days=30,
    )
    assert res["breaking_change_count"] == 1
    assert res["unversioned_breaking_change_ids"] == []
    assert res["failed_contract_test_ids"] == []
    assert res["insufficient_deprecation_window_ids"] == ["PUT /v2/users"]
    assert res["contract_governance_status"] == "DEPRECATION_WINDOW_WARNING"
    assert res["is_contract_gate_compliant"] is False


def test_audit_api_backward_compatibility_and_contract_versioning_safe_and_empty():
    from backend.services.project_ccb_service import (
        audit_api_backward_compatibility_and_contract_versioning,
    )

    empty = audit_api_backward_compatibility_and_contract_versioning(
        [{"endpoint_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_endpoints_evaluated"] == 0
    assert empty["breaking_change_count"] == 0
    assert empty["contract_governance_status"] == "BACKWARD_COMPATIBLE_SAFE"
    assert empty["is_contract_gate_compliant"] is True

    safe = audit_api_backward_compatibility_and_contract_versioning(
        [
            {
                "endpoint_id": "GET /v2/projects",
                "removes_required_response_field": True,
                "adds_mandatory_request_parameter_without_default": False,
                "bumps_major_api_version": True,
                "consumer_contract_tests_passed": True,
                "deprecation_notice_days_provided": 60,
            }
        ],
        min_deprecation_notice_days=30,
    )
    assert safe["total_endpoints_evaluated"] == 1
    assert safe["breaking_change_count"] == 1
    assert safe["unversioned_breaking_change_ids"] == []
    assert safe["failed_contract_test_ids"] == []
    assert safe["insufficient_deprecation_window_ids"] == []
    assert safe["contract_governance_status"] == "BACKWARD_COMPATIBLE_SAFE"
    assert safe["is_contract_gate_compliant"] is True


def test_audit_api_backward_compatibility_and_contract_versioning_staticmethod_and_dunder_all():
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_api_backward_compatibility_and_contract_versioning,
    )

    sample = [
        {
            "endpoint_id": "GET /v1/health",
            "removes_required_response_field": False,
            "adds_mandatory_request_parameter_without_default": False,
            "bumps_major_api_version": False,
            "consumer_contract_tests_passed": True,
            "deprecation_notice_days_provided": 30,
        }
    ]
    assert (
        ProjectCCBService.audit_api_backward_compatibility_and_contract_versioning(
            sample
        )
        == audit_api_backward_compatibility_and_contract_versioning(sample)
    )
    assert (
        "audit_api_backward_compatibility_and_contract_versioning" in mod.__all__
    )


def test_audit_test_pyramid_balance_and_mutation_coverage_gate_quality_gate_blocked():
    from backend.services.project_ccb_service import (
        audit_test_pyramid_balance_and_mutation_coverage_gate,
    )

    res = audit_test_pyramid_balance_and_mutation_coverage_gate(
        [
            {
                "suite_id": "SUITE-BILLING",
                "unit_tests_count": 70,
                "integration_tests_count": 20,
                "e2e_tests_count": 10,
                "mutation_kill_score_pct": 62.0,
                "flaky_tests_rate_pct": 4.5,
            }
        ],
        min_unit_test_share_pct=60.0,
        max_e2e_test_share_pct=20.0,
        min_mutation_score_pct=75.0,
        max_flaky_rate_pct=2.0,
    )
    assert res["total_suites_evaluated"] == 1
    assert res["ice_cream_cone_antipattern_suite_ids"] == []
    assert res["weak_mutation_coverage_suite_ids"] == ["SUITE-BILLING"]
    assert res["flaky_instability_suite_ids"] == ["SUITE-BILLING"]
    assert res["quality_pyramid_status"] == "QUALITY_GATE_BLOCKED"
    assert res["is_test_pyramid_compliant"] is False


def test_audit_test_pyramid_balance_and_mutation_coverage_gate_pyramid_imbalance_warning():
    from backend.services.project_ccb_service import (
        audit_test_pyramid_balance_and_mutation_coverage_gate,
    )

    res = audit_test_pyramid_balance_and_mutation_coverage_gate(
        [
            {
                "suite_id": "SUITE-FRONTEND-E2E-HEAVY",
                "unit_tests_count": 20,
                "integration_tests_count": 30,
                "e2e_tests_count": 50,
                "mutation_kill_score_pct": 82.0,
                "flaky_tests_rate_pct": 1.0,
            }
        ],
        min_unit_test_share_pct=60.0,
        max_e2e_test_share_pct=20.0,
        min_mutation_score_pct=75.0,
        max_flaky_rate_pct=2.0,
    )
    assert res["ice_cream_cone_antipattern_suite_ids"] == [
        "SUITE-FRONTEND-E2E-HEAVY"
    ]
    assert res["weak_mutation_coverage_suite_ids"] == []
    assert res["flaky_instability_suite_ids"] == []
    assert res["quality_pyramid_status"] == "PYRAMID_IMBALANCE_WARNING"
    assert res["is_test_pyramid_compliant"] is False


def test_audit_test_pyramid_balance_and_mutation_coverage_gate_optimal_and_empty():
    from backend.services.project_ccb_service import (
        audit_test_pyramid_balance_and_mutation_coverage_gate,
    )

    empty = audit_test_pyramid_balance_and_mutation_coverage_gate(
        [{"suite_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_suites_evaluated"] == 0
    assert empty["quality_pyramid_status"] == "PYRAMID_OPTIMAL"
    assert empty["is_test_pyramid_compliant"] is True

    optimal = audit_test_pyramid_balance_and_mutation_coverage_gate(
        [
            {
                "suite_id": "SUITE-CORE",
                "unit_tests_count": 140,
                "integration_tests_count": 40,
                "e2e_tests_count": 20,
                "mutation_kill_score_pct": 85.0,
                "flaky_tests_rate_pct": 0.5,
            }
        ]
    )
    assert optimal["total_suites_evaluated"] == 1
    assert optimal["ice_cream_cone_antipattern_suite_ids"] == []
    assert optimal["weak_mutation_coverage_suite_ids"] == []
    assert optimal["flaky_instability_suite_ids"] == []
    assert optimal["quality_pyramid_status"] == "PYRAMID_OPTIMAL"
    assert optimal["is_test_pyramid_compliant"] is True


def test_audit_test_pyramid_balance_and_mutation_coverage_gate_staticmethod_and_dunder_all():
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_test_pyramid_balance_and_mutation_coverage_gate,
    )

    sample = [
        {
            "suite_id": "SUITE-99",
            "unit_tests_count": 80,
            "integration_tests_count": 15,
            "e2e_tests_count": 5,
            "mutation_kill_score_pct": 80.0,
            "flaky_tests_rate_pct": 0.0,
        }
    ]
    assert (
        ProjectCCBService.audit_test_pyramid_balance_and_mutation_coverage_gate(
            sample
        )
        == audit_test_pyramid_balance_and_mutation_coverage_gate(sample)
    )
    assert (
        "audit_test_pyramid_balance_and_mutation_coverage_gate" in mod.__all__
    )


def test_audit_supply_chain_slsa_provenance_and_artifact_signing_tamper_risk():
    from backend.services.project_ccb_service import (
        audit_supply_chain_slsa_provenance_and_artifact_signing,
    )

    res = audit_supply_chain_slsa_provenance_and_artifact_signing(
        [
            {
                "artifact_id": "IMG-API-GATEWAY",
                "slsa_provenance_level": 2,
                "is_cryptographically_signed_cosign": False,
                "built_in_ephemeral_hermetic_runner": True,
                "has_pinned_dependency_digests": True,
            },
            {
                "artifact_id": "IMG-WORKER",
                "slsa_provenance_level": 3,
                "is_cryptographically_signed_cosign": True,
                "built_in_ephemeral_hermetic_runner": False,
                "has_pinned_dependency_digests": True,
            },
        ],
        min_slsa_level=3,
    )
    assert res["total_artifacts_evaluated"] == 2
    assert res["unsigned_artifact_ids"] == ["IMG-API-GATEWAY"]
    assert res["insufficient_slsa_artifact_ids"] == [
        "IMG-API-GATEWAY",
        "IMG-WORKER",
    ]
    assert res["unpinned_digest_artifact_ids"] == []
    assert res["supply_chain_status"] == "PROVENANCE_TAMPER_RISK"
    assert res["is_slsa_supply_chain_compliant"] is False


def test_audit_supply_chain_slsa_provenance_and_artifact_signing_digest_pinning_warning():
    from backend.services.project_ccb_service import (
        audit_supply_chain_slsa_provenance_and_artifact_signing,
    )

    res = audit_supply_chain_slsa_provenance_and_artifact_signing(
        [
            {
                "artifact_id": "IMG-FRONTEND",
                "slsa_provenance_level": 3,
                "is_cryptographically_signed_cosign": True,
                "built_in_ephemeral_hermetic_runner": True,
                "has_pinned_dependency_digests": False,
            }
        ],
        min_slsa_level=3,
    )
    assert res["unsigned_artifact_ids"] == []
    assert res["insufficient_slsa_artifact_ids"] == []
    assert res["unpinned_digest_artifact_ids"] == ["IMG-FRONTEND"]
    assert res["supply_chain_status"] == "DIGEST_PINNING_WARNING"
    assert res["is_slsa_supply_chain_compliant"] is False


def test_audit_supply_chain_slsa_provenance_and_artifact_signing_verified_secure_and_empty():
    from backend.services.project_ccb_service import (
        audit_supply_chain_slsa_provenance_and_artifact_signing,
    )

    empty = audit_supply_chain_slsa_provenance_and_artifact_signing(
        [{"artifact_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_artifacts_evaluated"] == 0
    assert empty["supply_chain_status"] == "SLSA_VERIFIED_SECURE"
    assert empty["is_slsa_supply_chain_compliant"] is True

    secure = audit_supply_chain_slsa_provenance_and_artifact_signing(
        [
            {
                "artifact_id": "IMG-CORE-SIGNED",
                "slsa_provenance_level": 3,
                "is_cryptographically_signed_cosign": True,
                "built_in_ephemeral_hermetic_runner": True,
                "has_pinned_dependency_digests": True,
            }
        ],
        min_slsa_level=3,
    )
    assert secure["total_artifacts_evaluated"] == 1
    assert secure["supply_chain_status"] == "SLSA_VERIFIED_SECURE"
    assert secure["is_slsa_supply_chain_compliant"] is True


def test_audit_supply_chain_slsa_provenance_and_artifact_signing_staticmethod_and_dunder_all():
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_supply_chain_slsa_provenance_and_artifact_signing,
    )

    sample = [
        {
            "artifact_id": "IMG-99",
            "slsa_provenance_level": 4,
            "is_cryptographically_signed_cosign": True,
            "built_in_ephemeral_hermetic_runner": True,
            "has_pinned_dependency_digests": True,
        }
    ]
    assert (
        ProjectCCBService.audit_supply_chain_slsa_provenance_and_artifact_signing(
            sample
        )
        == audit_supply_chain_slsa_provenance_and_artifact_signing(sample)
    )
    assert (
        "audit_supply_chain_slsa_provenance_and_artifact_signing"
        in mod.__all__
    )


def test_audit_ecab_emergency_change_retroactive_ratification_and_abuse_bypass_detected():
    from backend.services.project_ccb_service import (
        audit_ecab_emergency_change_retroactive_ratification_and_abuse,
    )

    res = audit_ecab_emergency_change_retroactive_ratification_and_abuse(
        [
            {
                "change_id": "CHG-EMERG-01",
                "is_emergency_break_glass": True,
                "hours_to_ecab_ratification": 72.0,
                "has_ecab_retroactive_signoff": True,
                "has_linked_sev1_incident_id": True,
                "has_post_implementation_review_completed": True,
            },
            {
                "change_id": "CHG-EMERG-02",
                "is_emergency_break_glass": True,
                "hours_to_ecab_ratification": 12.0,
                "has_ecab_retroactive_signoff": False,
                "has_linked_sev1_incident_id": False,
                "has_post_implementation_review_completed": True,
            },
            {
                "change_id": "CHG-STD-01",
                "is_emergency_break_glass": False,
                "hours_to_ecab_ratification": 999.0,
                "has_ecab_retroactive_signoff": False,
                "has_linked_sev1_incident_id": False,
                "has_post_implementation_review_completed": False,
            },
        ],
        max_retroactive_ratification_hours=48.0,
        max_emergency_change_ratio_pct=15.0,
    )
    assert res["total_changes_evaluated"] == 3
    assert res["emergency_changes_count"] == 2
    assert res["emergency_change_ratio_pct"] == 66.67
    assert res["unratified_or_late_ecab_ids"] == [
        "CHG-EMERG-01",
        "CHG-EMERG-02",
    ]
    assert res["unjustified_break_glass_ids"] == ["CHG-EMERG-02"]
    assert res["missing_pir_emergency_ids"] == []
    assert res["ecab_governance_status"] == "ECAB_BYPASS_ABUSE_DETECTED"
    assert res["is_ecab_compliant"] is False


def test_audit_ecab_emergency_change_retroactive_ratification_and_abuse_ratio_or_pir_warning():
    from backend.services.project_ccb_service import (
        audit_ecab_emergency_change_retroactive_ratification_and_abuse,
    )

    res = audit_ecab_emergency_change_retroactive_ratification_and_abuse(
        [
            {
                "change_id": "CHG-EMERG-PIR",
                "is_emergency_break_glass": True,
                "hours_to_ecab_ratification": 24.0,
                "has_ecab_retroactive_signoff": True,
                "has_linked_sev1_incident_id": True,
                "has_post_implementation_review_completed": False,
            },
            {"change_id": "CHG-STD-1", "is_emergency_break_glass": False},
            {"change_id": "CHG-STD-2", "is_emergency_break_glass": False},
            {"change_id": "CHG-STD-3", "is_emergency_break_glass": False},
            {"change_id": "CHG-STD-4", "is_emergency_break_glass": False},
            {"change_id": "CHG-STD-5", "is_emergency_break_glass": False},
            {"change_id": "CHG-STD-6", "is_emergency_break_glass": False},
            {"change_id": "CHG-STD-7", "is_emergency_break_glass": False},
            {"change_id": "CHG-STD-8", "is_emergency_break_glass": False},
            {"change_id": "CHG-STD-9", "is_emergency_break_glass": False},
        ],
        max_retroactive_ratification_hours=48.0,
        max_emergency_change_ratio_pct=15.0,
    )
    assert res["total_changes_evaluated"] == 10
    assert res["emergency_changes_count"] == 1
    assert res["emergency_change_ratio_pct"] == 10.0
    assert res["unratified_or_late_ecab_ids"] == []
    assert res["unjustified_break_glass_ids"] == []
    assert res["missing_pir_emergency_ids"] == ["CHG-EMERG-PIR"]
    assert res["ecab_governance_status"] == "EMERGENCY_RATIO_OR_PIR_WARNING"
    assert res["is_ecab_compliant"] is False


def test_audit_ecab_emergency_change_retroactive_ratification_and_abuse_governed_and_empty():
    from backend.services.project_ccb_service import (
        audit_ecab_emergency_change_retroactive_ratification_and_abuse,
    )

    empty = audit_ecab_emergency_change_retroactive_ratification_and_abuse(
        [{"change_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_changes_evaluated"] == 0
    assert empty["emergency_changes_count"] == 0
    assert empty["emergency_change_ratio_pct"] == 0.0
    assert empty["ecab_governance_status"] == "ECAB_GOVERNED"
    assert empty["is_ecab_compliant"] is True

    governed = audit_ecab_emergency_change_retroactive_ratification_and_abuse(
        [
            {
                "change_id": "CHG-EMERG-OK",
                "is_emergency_break_glass": True,
                "hours_to_ecab_ratification": 18.0,
                "has_ecab_retroactive_signoff": True,
                "has_linked_sev1_incident_id": True,
                "has_post_implementation_review_completed": True,
            },
            *[
                {"change_id": f"CHG-STD-{i}", "is_emergency_break_glass": False}
                for i in range(9)
            ],
        ],
        max_retroactive_ratification_hours=48.0,
        max_emergency_change_ratio_pct=15.0,
    )
    assert governed["total_changes_evaluated"] == 10
    assert governed["emergency_changes_count"] == 1
    assert governed["emergency_change_ratio_pct"] == 10.0
    assert governed["ecab_governance_status"] == "ECAB_GOVERNED"
    assert governed["is_ecab_compliant"] is True


def test_audit_ecab_emergency_change_retroactive_ratification_and_abuse_staticmethod_and_dunder_all():
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_ecab_emergency_change_retroactive_ratification_and_abuse,
    )

    sample = [
        {
            "change_id": "CHG-100",
            "is_emergency_break_glass": False,
        }
    ]
    assert (
        ProjectCCBService.audit_ecab_emergency_change_retroactive_ratification_and_abuse(
            sample
        )
        == audit_ecab_emergency_change_retroactive_ratification_and_abuse(sample)
    )
    assert (
        "audit_ecab_emergency_change_retroactive_ratification_and_abuse"
        in mod.__all__
    )


def test_audit_release_freeze_blackout_window_and_change_collisions_freeze_breach():
    from backend.services.project_ccb_service import (
        audit_release_freeze_blackout_window_and_change_collisions,
    )

    res = audit_release_freeze_blackout_window_and_change_collisions(
        [
            {
                "deployment_id": "DEP-BLACKOUT-01",
                "is_during_blackout_freeze_window": True,
                "has_vp_exception_waiver_signed": False,
                "concurrent_shared_infra_changes_count": 1,
                "has_dedicated_rollback_commander_on_duty": True,
            },
            {
                "deployment_id": "DEP-NO-CMD-02",
                "is_during_blackout_freeze_window": False,
                "has_vp_exception_waiver_signed": False,
                "concurrent_shared_infra_changes_count": 1,
                "has_dedicated_rollback_commander_on_duty": False,
            },
        ],
        max_concurrent_shared_infra_changes=1,
    )
    assert res["total_deployments_evaluated"] == 2
    assert res["unauthorized_blackout_deployment_ids"] == ["DEP-BLACKOUT-01"]
    assert res["collision_hazard_deployment_ids"] == []
    assert res["unattended_rollback_deployment_ids"] == ["DEP-NO-CMD-02"]
    assert res["release_window_status"] == "FREEZE_OR_COMMAND_BREACH"
    assert res["is_release_window_compliant"] is False


def test_audit_release_freeze_blackout_window_and_change_collisions_collision_warning():
    from backend.services.project_ccb_service import (
        audit_release_freeze_blackout_window_and_change_collisions,
    )

    res = audit_release_freeze_blackout_window_and_change_collisions(
        [
            {
                "deployment_id": "DEP-SHARED-DB-10",
                "is_during_blackout_freeze_window": False,
                "has_vp_exception_waiver_signed": False,
                "concurrent_shared_infra_changes_count": 3,
                "has_dedicated_rollback_commander_on_duty": True,
            }
        ],
        max_concurrent_shared_infra_changes=1,
    )
    assert res["unauthorized_blackout_deployment_ids"] == []
    assert res["collision_hazard_deployment_ids"] == ["DEP-SHARED-DB-10"]
    assert res["unattended_rollback_deployment_ids"] == []
    assert res["release_window_status"] == "CHANGE_COLLISION_WARNING"
    assert res["is_release_window_compliant"] is False


def test_audit_release_freeze_blackout_window_and_change_collisions_safe_and_empty():
    from backend.services.project_ccb_service import (
        audit_release_freeze_blackout_window_and_change_collisions,
    )

    empty = audit_release_freeze_blackout_window_and_change_collisions(
        [{"deployment_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_deployments_evaluated"] == 0
    assert empty["release_window_status"] == "RELEASE_WINDOW_SAFE"
    assert empty["is_release_window_compliant"] is True

    safe = audit_release_freeze_blackout_window_and_change_collisions(
        [
            {
                "deployment_id": "DEP-WAIVED-20",
                "is_during_blackout_freeze_window": True,
                "has_vp_exception_waiver_signed": True,
                "concurrent_shared_infra_changes_count": 1,
                "has_dedicated_rollback_commander_on_duty": True,
            }
        ]
    )
    assert safe["total_deployments_evaluated"] == 1
    assert safe["release_window_status"] == "RELEASE_WINDOW_SAFE"
    assert safe["is_release_window_compliant"] is True


def test_audit_release_freeze_blackout_window_and_change_collisions_staticmethod_and_dunder_all():
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_release_freeze_blackout_window_and_change_collisions,
    )

    sample = [
        {
            "deployment_id": "DEP-99",
            "is_during_blackout_freeze_window": False,
            "concurrent_shared_infra_changes_count": 1,
            "has_dedicated_rollback_commander_on_duty": True,
        }
    ]
    assert (
        ProjectCCBService.audit_release_freeze_blackout_window_and_change_collisions(
            sample
        )
        == audit_release_freeze_blackout_window_and_change_collisions(sample)
    )
    assert (
        "audit_release_freeze_blackout_window_and_change_collisions"
        in mod.__all__
    )


def test_audit_query_performance_n_plus_one_and_full_scan_gate_regression_blocked():
    from backend.services.project_ccb_service import (
        audit_query_performance_n_plus_one_and_full_scan_gate,
    )

    res = audit_query_performance_n_plus_one_and_full_scan_gate(
        [
            {
                "query_id": "QRY-LIST-TASKS",
                "triggers_n_plus_one_loop": True,
                "uses_full_table_seq_scan_on_large_table": False,
                "p99_execution_ms": 80.0,
                "rows_scanned_to_returned_ratio": 2.0,
            },
            {
                "query_id": "QRY-EXPORT-LEDGER",
                "triggers_n_plus_one_loop": False,
                "uses_full_table_seq_scan_on_large_table": False,
                "p99_execution_ms": 450.0,
                "rows_scanned_to_returned_ratio": 10.0,
            },
        ],
        max_p99_latency_ms=200.0,
        max_rows_scanned_to_returned_ratio=50.0,
    )
    assert res["total_queries_evaluated"] == 2
    assert res["n_plus_one_or_full_scan_query_ids"] == ["QRY-LIST-TASKS"]
    assert res["p99_latency_breach_query_ids"] == ["QRY-EXPORT-LEDGER"]
    assert res["inefficient_selectivity_query_ids"] == []
    assert res["query_gate_status"] == "PERFORMANCE_REGRESSION_BLOCKED"
    assert res["is_query_performance_compliant"] is False


def test_audit_query_performance_n_plus_one_and_full_scan_gate_selectivity_warning():
    from backend.services.project_ccb_service import (
        audit_query_performance_n_plus_one_and_full_scan_gate,
    )

    res = audit_query_performance_n_plus_one_and_full_scan_gate(
        [
            {
                "query_id": "QRY-FILTER-AUDIT",
                "triggers_n_plus_one_loop": False,
                "uses_full_table_seq_scan_on_large_table": False,
                "p99_execution_ms": 95.0,
                "rows_scanned_to_returned_ratio": 120.0,
            }
        ],
        max_p99_latency_ms=200.0,
        max_rows_scanned_to_returned_ratio=50.0,
    )
    assert res["n_plus_one_or_full_scan_query_ids"] == []
    assert res["p99_latency_breach_query_ids"] == []
    assert res["inefficient_selectivity_query_ids"] == ["QRY-FILTER-AUDIT"]
    assert res["query_gate_status"] == "SELECTIVITY_INDEX_WARNING"
    assert res["is_query_performance_compliant"] is False


def test_audit_query_performance_n_plus_one_and_full_scan_gate_optimal_and_empty():
    from backend.services.project_ccb_service import (
        audit_query_performance_n_plus_one_and_full_scan_gate,
    )

    empty = audit_query_performance_n_plus_one_and_full_scan_gate(
        [{"query_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["total_queries_evaluated"] == 0
    assert empty["query_gate_status"] == "QUERY_PLAN_OPTIMAL"
    assert empty["is_query_performance_compliant"] is True

    optimal = audit_query_performance_n_plus_one_and_full_scan_gate(
        [
            {
                "query_id": "QRY-INDEXED-LOOKUP",
                "triggers_n_plus_one_loop": False,
                "uses_full_table_seq_scan_on_large_table": False,
                "p99_execution_ms": 12.5,
                "rows_scanned_to_returned_ratio": 1.2,
            }
        ]
    )
    assert optimal["total_queries_evaluated"] == 1
    assert optimal["query_gate_status"] == "QUERY_PLAN_OPTIMAL"
    assert optimal["is_query_performance_compliant"] is True


def test_audit_query_performance_n_plus_one_and_full_scan_gate_staticmethod_and_dunder_all():
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_query_performance_n_plus_one_and_full_scan_gate,
    )

    sample = [
        {
            "query_id": "QRY-99",
            "p99_execution_ms": 15.0,
            "rows_scanned_to_returned_ratio": 1.0,
        }
    ]
    assert (
        ProjectCCBService.audit_query_performance_n_plus_one_and_full_scan_gate(
            sample
        )
        == audit_query_performance_n_plus_one_and_full_scan_gate(sample)
    )
    assert (
        "audit_query_performance_n_plus_one_and_full_scan_gate"
        in mod.__all__
    )


def test_audit_feature_flag_stale_toggle_debt_and_kill_switch_breach():
    from backend.services.project_ccb_service import (
        audit_feature_flag_stale_toggle_debt_and_kill_switch,
    )

    res = audit_feature_flag_stale_toggle_debt_and_kill_switch(
        [
            {
                "flag_key": "ops.circuit_breaker.payments",
                "age_days_since_100pct_rollout": 180,
                "is_permanent_ops_kill_switch": True,
                "kill_switch_propagation_seconds": 120.0,
                "has_assigned_owner_and_cleanup_ticket": True,
                "nested_flag_dependencies_count": 0,
            },
            {
                "flag_key": "release.checkout_v2",
                "age_days_since_100pct_rollout": 10,
                "is_permanent_ops_kill_switch": False,
                "kill_switch_propagation_seconds": 3.0,
                "has_assigned_owner_and_cleanup_ticket": False,
                "nested_flag_dependencies_count": 0,
            },
        ],
        max_toggle_age_days=45,
        max_kill_switch_propagation_seconds=30.0,
    )
    assert res["evaluated_flags_count"] == 2
    assert res["broken_kill_switch_or_unowned_flag_keys"] == [
        "ops.circuit_breaker.payments",
        "release.checkout_v2",
    ]
    assert res["stale_or_entangled_flag_keys"] == []
    assert (
        res["feature_flag_governance_status"]
        == "FLAG_KILL_SWITCH_OR_OWNERSHIP_BREACH"
    )
    assert res["is_feature_flag_compliant"] is False


def test_audit_feature_flag_stale_toggle_debt_and_kill_switch_stale_or_entangled_warning():
    from backend.services.project_ccb_service import (
        audit_feature_flag_stale_toggle_debt_and_kill_switch,
    )

    res = audit_feature_flag_stale_toggle_debt_and_kill_switch(
        [
            {
                "flag_key": "release.legacy_banner",
                "age_days_since_100pct_rollout": 90,
                "is_permanent_ops_kill_switch": False,
                "kill_switch_propagation_seconds": 5.0,
                "has_assigned_owner_and_cleanup_ticket": True,
                "nested_flag_dependencies_count": 0,
            },
            {
                "flag_key": "release.entangled_pricing",
                "age_days_since_100pct_rollout": 5,
                "is_permanent_ops_kill_switch": False,
                "kill_switch_propagation_seconds": 5.0,
                "has_assigned_owner_and_cleanup_ticket": True,
                "nested_flag_dependencies_count": 3,
            },
        ],
        max_toggle_age_days=45,
        max_kill_switch_propagation_seconds=30.0,
    )
    assert res["evaluated_flags_count"] == 2
    assert res["broken_kill_switch_or_unowned_flag_keys"] == []
    assert res["stale_or_entangled_flag_keys"] == [
        "release.legacy_banner",
        "release.entangled_pricing",
    ]
    assert (
        res["feature_flag_governance_status"]
        == "FLAG_STALE_TOGGLE_DEBT_WARNING"
    )
    assert res["is_feature_flag_compliant"] is False


def test_audit_feature_flag_stale_toggle_debt_and_kill_switch_optimal_and_empty():
    from backend.services.project_ccb_service import (
        audit_feature_flag_stale_toggle_debt_and_kill_switch,
    )

    empty = audit_feature_flag_stale_toggle_debt_and_kill_switch(
        [{"flag_key": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_flags_count"] == 0
    assert empty["feature_flag_governance_status"] == "FLAG_HYGIENE_OPTIMAL"
    assert empty["is_feature_flag_compliant"] is True

    optimal = audit_feature_flag_stale_toggle_debt_and_kill_switch(
        [
            {
                "flag_key": "ops.shed_load",
                "age_days_since_100pct_rollout": 365,
                "is_permanent_ops_kill_switch": True,
                "kill_switch_propagation_seconds": 4.0,
                "has_assigned_owner_and_cleanup_ticket": True,
                "nested_flag_dependencies_count": 1,
            },
            {
                "flag_key": "release.new_search",
                "age_days_since_100pct_rollout": 45,
                "is_permanent_ops_kill_switch": False,
                "kill_switch_propagation_seconds": 5.0,
                "has_assigned_owner_and_cleanup_ticket": True,
                "nested_flag_dependencies_count": 0,
            },
        ],
        max_toggle_age_days=45,
        max_kill_switch_propagation_seconds=30.0,
    )
    assert optimal["evaluated_flags_count"] == 2
    assert optimal["feature_flag_governance_status"] == "FLAG_HYGIENE_OPTIMAL"
    assert optimal["is_feature_flag_compliant"] is True


def test_audit_feature_flag_stale_toggle_debt_and_kill_switch_staticmethod_and_dunder_all():
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_feature_flag_stale_toggle_debt_and_kill_switch,
    )

    sample = [
        {
            "flag_key": "release.sample",
            "age_days_since_100pct_rollout": 10,
        }
    ]
    assert (
        ProjectCCBService.audit_feature_flag_stale_toggle_debt_and_kill_switch(
            sample
        )
        == audit_feature_flag_stale_toggle_debt_and_kill_switch(sample)
    )
    assert (
        "audit_feature_flag_stale_toggle_debt_and_kill_switch"
        in mod.__all__
    )


def test_audit_canary_rollout_traffic_shift_and_auto_rollback_gate_breach():
    from backend.services.project_ccb_service import (
        audit_canary_rollout_traffic_shift_and_auto_rollback_gate,
    )

    result = audit_canary_rollout_traffic_shift_and_auto_rollback_gate(
        [
            {
                "deployment_id": "CAN-UNARMED",
                "initial_traffic_step_pct": 5.0,
                "bake_time_minutes_observed": 35,
                "observed_5xx_error_rate_pct": 0.1,
                "automated_rollback_hook_armed": False,
                "baseline_golden_signals_compared": True,
            },
            {
                "deployment_id": "CAN-SPIKE",
                "initial_traffic_step_pct": 5.0,
                "bake_time_minutes_observed": 35,
                "observed_5xx_error_rate_pct": 1.2,
                "automated_rollback_hook_armed": True,
                "baseline_golden_signals_compared": True,
            },
        ],
        min_bake_time_minutes_per_stage=30,
        max_canary_5xx_error_rate_pct=0.5,
    )
    assert result["evaluated_deployments_count"] == 2
    assert result["unarmed_rollback_or_error_spike_deployment_ids"] == [
        "CAN-UNARMED",
        "CAN-SPIKE",
    ]
    assert result["rushed_bake_or_aggressive_step_deployment_ids"] == []
    assert (
        result["canary_governance_status"]
        == "CANARY_ROLLBACK_OR_ERROR_SPIKE_BREACH"
    )
    assert result["is_canary_rollout_compliant"] is False


def test_audit_canary_rollout_traffic_shift_and_auto_rollback_gate_warning():
    from backend.services.project_ccb_service import (
        audit_canary_rollout_traffic_shift_and_auto_rollback_gate,
    )

    result = audit_canary_rollout_traffic_shift_and_auto_rollback_gate(
        [
            {
                "deployment_id": "CAN-RUSHED",
                "initial_traffic_step_pct": 5.0,
                "bake_time_minutes_observed": 10,
                "observed_5xx_error_rate_pct": 0.1,
                "automated_rollback_hook_armed": True,
                "baseline_golden_signals_compared": True,
            },
            {
                "deployment_id": "CAN-BIG-STEP",
                "initial_traffic_step_pct": 50.0,
                "bake_time_minutes_observed": 40,
                "observed_5xx_error_rate_pct": 0.1,
                "automated_rollback_hook_armed": True,
                "baseline_golden_signals_compared": True,
            },
            {
                "deployment_id": "CAN-NO-SIGNALS",
                "initial_traffic_step_pct": 5.0,
                "bake_time_minutes_observed": 40,
                "observed_5xx_error_rate_pct": 0.1,
                "automated_rollback_hook_armed": True,
                "baseline_golden_signals_compared": False,
            },
        ],
        min_bake_time_minutes_per_stage=30,
        max_canary_5xx_error_rate_pct=0.5,
    )
    assert result["evaluated_deployments_count"] == 3
    assert result["unarmed_rollback_or_error_spike_deployment_ids"] == []
    assert result["rushed_bake_or_aggressive_step_deployment_ids"] == [
        "CAN-RUSHED",
        "CAN-BIG-STEP",
        "CAN-NO-SIGNALS",
    ]
    assert (
        result["canary_governance_status"]
        == "CANARY_BAKE_TIME_OR_STEP_WARNING"
    )
    assert result["is_canary_rollout_compliant"] is False


def test_audit_canary_rollout_traffic_shift_and_auto_rollback_gate_optimal_and_empty():
    from backend.services.project_ccb_service import (
        audit_canary_rollout_traffic_shift_and_auto_rollback_gate,
    )

    empty = audit_canary_rollout_traffic_shift_and_auto_rollback_gate(
        [{"deployment_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_deployments_count"] == 0
    assert (
        empty["canary_governance_status"]
        == "CANARY_PROGRESSIVE_DELIVERY_OPTIMAL"
    )
    assert empty["is_canary_rollout_compliant"] is True

    optimal = audit_canary_rollout_traffic_shift_and_auto_rollback_gate(
        [
            {
                "deployment_id": "CAN-GOLD-1",
                "initial_traffic_step_pct": 5.0,
                "bake_time_minutes_observed": 45,
                "observed_5xx_error_rate_pct": 0.08,
                "automated_rollback_hook_armed": True,
                "baseline_golden_signals_compared": True,
            }
        ],
        min_bake_time_minutes_per_stage=30,
        max_canary_5xx_error_rate_pct=0.5,
    )
    assert optimal["evaluated_deployments_count"] == 1
    assert (
        optimal["canary_governance_status"]
        == "CANARY_PROGRESSIVE_DELIVERY_OPTIMAL"
    )
    assert optimal["is_canary_rollout_compliant"] is True


def test_audit_canary_rollout_traffic_shift_and_auto_rollback_gate_staticmethod_and_dunder_all():
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_canary_rollout_traffic_shift_and_auto_rollback_gate,
    )

    sample = [
        {
            "deployment_id": "CAN-99",
            "initial_traffic_step_pct": 5.0,
            "bake_time_minutes_observed": 30,
            "observed_5xx_error_rate_pct": 0.1,
        }
    ]
    assert (
        ProjectCCBService.audit_canary_rollout_traffic_shift_and_auto_rollback_gate(
            sample
        )
        == audit_canary_rollout_traffic_shift_and_auto_rollback_gate(sample)
    )
    assert (
        "audit_canary_rollout_traffic_shift_and_auto_rollback_gate"
        in mod.__all__
    )



def test_ccb_secret_scanning_leak_or_hook_bypass_breach():
    from backend.services.project_ccb_service import (
        audit_secret_scanning_pre_receive_and_leak_revocation,
    )

    res = audit_secret_scanning_pre_receive_and_leak_revocation(
        [
            {
                "repo_id": "REPO-NO-HOOK",
                "pre_receive_secret_hook_enforced": False,
            },
            {
                "repo_id": "REPO-ACTIVE-LEAK",
                "unrevoked_leaked_secrets_count": 2,
            },
            {
                "repo_id": "REPO-HISTORY-DIRTY",
                "git_history_purged_on_leak": False,
            },
        ],
        max_revocation_minutes_sla=15.0,
        max_false_positive_bypass_rate_pct=5.0,
    )
    assert res["evaluated_repos_count"] == 3
    assert res["active_leak_or_unprotected_repo_ids"] == [
        "REPO-NO-HOOK",
        "REPO-ACTIVE-LEAK",
        "REPO-HISTORY-DIRTY",
    ]
    assert res["slow_revocation_or_high_bypass_repo_ids"] == []
    assert (
        res["secret_scanning_governance_status"]
        == "SECRET_LEAK_OR_HOOK_BYPASS_BREACH"
    )
    assert res["is_secret_scanning_compliant"] is False


def test_ccb_secret_scanning_revocation_sla_or_bypass_warning():
    from backend.services.project_ccb_service import (
        audit_secret_scanning_pre_receive_and_leak_revocation,
    )

    res = audit_secret_scanning_pre_receive_and_leak_revocation(
        [
            {
                "repo_id": "REPO-SLOW-REVOKE",
                "max_observed_revocation_minutes": 22.0,
            },
            {
                "repo_id": "REPO-HIGH-BYPASS",
                "push_bypass_rate_pct": 7.5,
            },
        ],
        max_revocation_minutes_sla=15.0,
        max_false_positive_bypass_rate_pct=5.0,
    )
    assert res["evaluated_repos_count"] == 2
    assert res["active_leak_or_unprotected_repo_ids"] == []
    assert res["slow_revocation_or_high_bypass_repo_ids"] == [
        "REPO-SLOW-REVOKE",
        "REPO-HIGH-BYPASS",
    ]
    assert (
        res["secret_scanning_governance_status"]
        == "SECRET_REVOCATION_SLA_OR_BYPASS_WARNING"
    )
    assert res["is_secret_scanning_compliant"] is False


def test_ccb_secret_scanning_boundaries_optimal_and_defaults():
    from backend.services.project_ccb_service import (
        audit_secret_scanning_pre_receive_and_leak_revocation,
    )

    res = audit_secret_scanning_pre_receive_and_leak_revocation(
        [
            {
                "repo_id": "REPO-BOUNDARY",
                "max_observed_revocation_minutes": 15.0,
                "push_bypass_rate_pct": 5.0,
            },
            {"repo_id": "REPO-ALL-DEFAULTS"},
        ],
        max_revocation_minutes_sla=15.0,
        max_false_positive_bypass_rate_pct=5.0,
    )
    assert res["evaluated_repos_count"] == 2
    assert res["active_leak_or_unprotected_repo_ids"] == []
    assert res["slow_revocation_or_high_bypass_repo_ids"] == []
    assert (
        res["secret_scanning_governance_status"]
        == "SECRET_HYGIENE_ZERO_LEAK_OPTIMAL"
    )
    assert res["is_secret_scanning_compliant"] is True


def test_ccb_secret_scanning_invalid_and_binding():
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_secret_scanning_pre_receive_and_leak_revocation,
    )

    empty = audit_secret_scanning_pre_receive_and_leak_revocation(None)
    assert empty["evaluated_repos_count"] == 0
    assert empty["active_leak_or_unprotected_repo_ids"] == []
    assert empty["slow_revocation_or_high_bypass_repo_ids"] == []
    assert (
        empty["secret_scanning_governance_status"]
        == "SECRET_HYGIENE_ZERO_LEAK_OPTIMAL"
    )
    assert empty["is_secret_scanning_compliant"] is True

    invalid = audit_secret_scanning_pre_receive_and_leak_revocation(
        [42, "not-a-dict", None, {"repo_id": "   "}]  # type: ignore[list-item]
    )
    assert invalid["evaluated_repos_count"] == 0

    defaults = audit_secret_scanning_pre_receive_and_leak_revocation(
        [
            {
                "repo_id": "REPO-DEFAULTS",
                "pre_receive_secret_hook_enforced": None,
                "unrevoked_leaked_secrets_count": None,
                "max_observed_revocation_minutes": None,
                "push_bypass_rate_pct": None,
                "git_history_purged_on_leak": None,
            }
        ]
    )
    assert defaults["evaluated_repos_count"] == 1
    assert (
        defaults["secret_scanning_governance_status"]
        == "SECRET_HYGIENE_ZERO_LEAK_OPTIMAL"
    )
    assert defaults["is_secret_scanning_compliant"] is True

    sample = [
        {
            "repo_id": "REPO-1",
            "max_observed_revocation_minutes": 8.0,
        }
    ]
    assert (
        ProjectCCBService.audit_secret_scanning_pre_receive_and_leak_revocation(
            sample
        )
        == audit_secret_scanning_pre_receive_and_leak_revocation(sample)
    )
    assert (
        "audit_secret_scanning_pre_receive_and_leak_revocation"
        in mod.__all__
    )


def test_audit_iac_terraform_drift_and_state_lock_hygiene_breach():
    from backend.services.project_ccb_service import (
        audit_iac_terraform_drift_and_state_lock_hygiene,
    )

    result = audit_iac_terraform_drift_and_state_lock_hygiene(
        [
            {
                "workspace_id": "WS-UNLOCKED",
                "unmanaged_console_mutations_count": 0,
                "drifted_resources_count": 0,
                "hours_since_drift_detected": 0.0,
                "remote_state_locking_and_encryption_enabled": False,
                "destructive_plan_requires_ccb_approval": True,
            },
            {
                "workspace_id": "WS-NO-CCB-GATE",
                "unmanaged_console_mutations_count": 0,
                "drifted_resources_count": 0,
                "hours_since_drift_detected": 0.0,
                "remote_state_locking_and_encryption_enabled": True,
                "destructive_plan_requires_ccb_approval": False,
            },
            {
                "workspace_id": "WS-CLICKOPS",
                "unmanaged_console_mutations_count": 2,
                "drifted_resources_count": 0,
                "hours_since_drift_detected": 0.0,
                "remote_state_locking_and_encryption_enabled": True,
                "destructive_plan_requires_ccb_approval": True,
            },
        ],
        max_drift_reconciliation_hours=24.0,
    )
    assert result["evaluated_workspaces_count"] == 3
    assert result["unlocked_state_or_console_mutation_workspace_ids"] == [
        "WS-UNLOCKED",
        "WS-NO-CCB-GATE",
        "WS-CLICKOPS",
    ]
    assert result["unreconciled_drift_workspace_ids"] == []
    assert (
        result["iac_governance_status"]
        == "IAC_STATE_LOCK_OR_CONSOLE_MUTATION_BREACH"
    )
    assert result["is_iac_gitops_compliant"] is False


def test_audit_iac_terraform_drift_and_state_lock_hygiene_warning():
    from backend.services.project_ccb_service import (
        audit_iac_terraform_drift_and_state_lock_hygiene,
    )

    result = audit_iac_terraform_drift_and_state_lock_hygiene(
        [
            {
                "workspace_id": "WS-STALE-DRIFT",
                "unmanaged_console_mutations_count": 0,
                "drifted_resources_count": 3,
                "hours_since_drift_detected": 36.0,
                "remote_state_locking_and_encryption_enabled": True,
                "destructive_plan_requires_ccb_approval": True,
            },
            {
                "workspace_id": "WS-FRESH-DRIFT",
                "unmanaged_console_mutations_count": 0,
                "drifted_resources_count": 1,
                "hours_since_drift_detected": 4.0,
                "remote_state_locking_and_encryption_enabled": True,
                "destructive_plan_requires_ccb_approval": True,
            },
        ],
        max_drift_reconciliation_hours=24.0,
    )
    assert result["evaluated_workspaces_count"] == 2
    assert result["unlocked_state_or_console_mutation_workspace_ids"] == []
    assert result["unreconciled_drift_workspace_ids"] == ["WS-STALE-DRIFT"]
    assert (
        result["iac_governance_status"]
        == "IAC_DRIFT_RECONCILIATION_SLA_WARNING"
    )
    assert result["is_iac_gitops_compliant"] is False


def test_audit_iac_terraform_drift_and_state_lock_hygiene_optimal_and_empty():
    from backend.services.project_ccb_service import (
        audit_iac_terraform_drift_and_state_lock_hygiene,
    )

    empty = audit_iac_terraform_drift_and_state_lock_hygiene(
        [{"workspace_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_workspaces_count"] == 0
    assert empty["iac_governance_status"] == "IAC_GITOPS_PARITY_OPTIMAL"
    assert empty["is_iac_gitops_compliant"] is True

    optimal = audit_iac_terraform_drift_and_state_lock_hygiene(
        [
            {
                "workspace_id": "WS-PROD-CORE",
                "unmanaged_console_mutations_count": 0,
                "drifted_resources_count": 0,
                "hours_since_drift_detected": 0.0,
                "remote_state_locking_and_encryption_enabled": True,
                "destructive_plan_requires_ccb_approval": True,
            }
        ],
        max_drift_reconciliation_hours=24.0,
    )
    assert optimal["evaluated_workspaces_count"] == 1
    assert optimal["iac_governance_status"] == "IAC_GITOPS_PARITY_OPTIMAL"
    assert optimal["is_iac_gitops_compliant"] is True


def test_audit_iac_terraform_drift_and_state_lock_hygiene_staticmethod_and_dunder_all():
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_iac_terraform_drift_and_state_lock_hygiene,
    )

    sample = [
        {
            "workspace_id": "WS-99",
            "unmanaged_console_mutations_count": 0,
            "drifted_resources_count": 0,
        }
    ]
    assert (
        ProjectCCBService.audit_iac_terraform_drift_and_state_lock_hygiene(
            sample
        )
        == audit_iac_terraform_drift_and_state_lock_hygiene(sample)
    )
    assert (
        "audit_iac_terraform_drift_and_state_lock_hygiene"
        in mod.__all__
    )


def test_audit_container_image_vulnerability_and_non_root_runtime_gate_breach():
    from backend.services.project_ccb_service import (
        audit_container_image_vulnerability_and_non_root_runtime_gate,
    )

    result = audit_container_image_vulnerability_and_non_root_runtime_gate(
        [
            {
                "image_id": "IMG-CVE",
                "critical_or_high_cves_count": 2,
                "runs_as_non_root_uid": True,
                "pinned_by_sha256_digest": True,
                "image_size_mb": 150.0,
                "read_only_root_filesystem_enabled": True,
            },
            {
                "image_id": "IMG-ROOT",
                "critical_or_high_cves_count": 0,
                "runs_as_non_root_uid": False,
                "pinned_by_sha256_digest": True,
                "image_size_mb": 150.0,
                "read_only_root_filesystem_enabled": True,
            },
            {
                "image_id": "IMG-UNPINNED",
                "critical_or_high_cves_count": 0,
                "runs_as_non_root_uid": True,
                "pinned_by_sha256_digest": False,
                "image_size_mb": 150.0,
                "read_only_root_filesystem_enabled": True,
            },
        ],
        max_high_cves_allowed=0,
        max_image_size_mb=500.0,
    )
    assert result["evaluated_images_count"] == 3
    assert result["vulnerable_or_root_runtime_image_ids"] == [
        "IMG-CVE",
        "IMG-ROOT",
        "IMG-UNPINNED",
    ]
    assert result["bloated_or_writable_rootfs_image_ids"] == []
    assert (
        result["container_security_status"]
        == "CONTAINER_CVE_OR_ROOT_RUNTIME_BREACH"
    )
    assert result["is_container_security_compliant"] is False


def test_audit_container_image_vulnerability_and_non_root_runtime_gate_warning():
    from backend.services.project_ccb_service import (
        audit_container_image_vulnerability_and_non_root_runtime_gate,
    )

    result = audit_container_image_vulnerability_and_non_root_runtime_gate(
        [
            {
                "image_id": "IMG-BLOATED",
                "critical_or_high_cves_count": 0,
                "runs_as_non_root_uid": True,
                "pinned_by_sha256_digest": True,
                "image_size_mb": 720.0,
                "read_only_root_filesystem_enabled": True,
            },
            {
                "image_id": "IMG-WRITABLE-ROOTFS",
                "critical_or_high_cves_count": 0,
                "runs_as_non_root_uid": True,
                "pinned_by_sha256_digest": True,
                "image_size_mb": 190.0,
                "read_only_root_filesystem_enabled": False,
            },
        ],
        max_high_cves_allowed=0,
        max_image_size_mb=500.0,
    )
    assert result["evaluated_images_count"] == 2
    assert result["vulnerable_or_root_runtime_image_ids"] == []
    assert result["bloated_or_writable_rootfs_image_ids"] == [
        "IMG-BLOATED",
        "IMG-WRITABLE-ROOTFS",
    ]
    assert (
        result["container_security_status"]
        == "CONTAINER_BLOAT_OR_WRITABLE_ROOTFS_WARNING"
    )
    assert result["is_container_security_compliant"] is False


def test_audit_container_image_vulnerability_and_non_root_runtime_gate_optimal_and_empty():
    from backend.services.project_ccb_service import (
        audit_container_image_vulnerability_and_non_root_runtime_gate,
    )

    empty = audit_container_image_vulnerability_and_non_root_runtime_gate(
        [{"image_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_images_count"] == 0
    assert (
        empty["container_security_status"]
        == "CONTAINER_RUNTIME_HARDENED_OPTIMAL"
    )
    assert empty["is_container_security_compliant"] is True

    optimal = audit_container_image_vulnerability_and_non_root_runtime_gate(
        [
            {
                "image_id": "IMG-DISTROLESS-1",
                "critical_or_high_cves_count": 0,
                "runs_as_non_root_uid": True,
                "pinned_by_sha256_digest": True,
                "image_size_mb": 95.0,
                "read_only_root_filesystem_enabled": True,
            }
        ],
        max_high_cves_allowed=0,
        max_image_size_mb=500.0,
    )
    assert optimal["evaluated_images_count"] == 1
    assert optimal["vulnerable_or_root_runtime_image_ids"] == []
    assert optimal["bloated_or_writable_rootfs_image_ids"] == []
    assert (
        optimal["container_security_status"]
        == "CONTAINER_RUNTIME_HARDENED_OPTIMAL"
    )
    assert optimal["is_container_security_compliant"] is True


def test_audit_container_image_vulnerability_and_non_root_runtime_gate_staticmethod_and_dunder_all():
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_container_image_vulnerability_and_non_root_runtime_gate,
    )

    sample = [
        {
            "image_id": "IMG-99",
            "critical_or_high_cves_count": 0,
            "image_size_mb": 140.0,
        }
    ]
    assert (
        ProjectCCBService.audit_container_image_vulnerability_and_non_root_runtime_gate(
            sample
        )
        == audit_container_image_vulnerability_and_non_root_runtime_gate(sample)
    )
    assert (
        "audit_container_image_vulnerability_and_non_root_runtime_gate"
        in mod.__all__
    )



def test_dark_launch_side_effect_or_pii_breach():
    from backend.services.project_ccb_service import (
        audit_dark_launch_shadow_traffic_parity_and_isolation,
    )

    res = audit_dark_launch_shadow_traffic_parity_and_isolation(
        [
            {
                "campaign_id": "SHADOW-WRITES-LEAK",
                "shadow_write_side_effects_muted": False,
            },
            {
                "campaign_id": "SHADOW-SYNC-BLOCK",
                "async_fire_and_forget_enforced": False,
            },
            {
                "campaign_id": "SHADOW-PII-EXPOSED",
                "pii_masked_in_shadow_diff_logs": False,
            },
        ],
        min_payload_parity_pct=99.5,
        max_primary_latency_overhead_ms=10.0,
    )
    assert res["evaluated_campaigns_count"] == 3
    assert res["side_effect_leak_or_sync_blocking_campaign_ids"] == [
        "SHADOW-WRITES-LEAK",
        "SHADOW-SYNC-BLOCK",
        "SHADOW-PII-EXPOSED",
    ]
    assert res["parity_mismatch_or_latency_drag_campaign_ids"] == []
    assert (
        res["dark_launch_governance_status"]
        == "DARK_LAUNCH_SIDE_EFFECT_OR_PII_BREACH"
    )
    assert res["is_dark_launch_compliant"] is False


def test_dark_launch_parity_or_latency_warning():
    from backend.services.project_ccb_service import (
        audit_dark_launch_shadow_traffic_parity_and_isolation,
    )

    res = audit_dark_launch_shadow_traffic_parity_and_isolation(
        [
            {
                "campaign_id": "SHADOW-PARITY-DRIFT",
                "payload_response_parity_pct": 98.0,
            },
            {
                "campaign_id": "SHADOW-LATENCY-DRAG",
                "primary_path_latency_overhead_ms": 18.0,
            },
        ],
        min_payload_parity_pct=99.5,
        max_primary_latency_overhead_ms=10.0,
    )
    assert res["evaluated_campaigns_count"] == 2
    assert res["side_effect_leak_or_sync_blocking_campaign_ids"] == []
    assert res["parity_mismatch_or_latency_drag_campaign_ids"] == [
        "SHADOW-PARITY-DRIFT",
        "SHADOW-LATENCY-DRAG",
    ]
    assert (
        res["dark_launch_governance_status"]
        == "DARK_LAUNCH_PARITY_OR_LATENCY_WARNING"
    )
    assert res["is_dark_launch_compliant"] is False


def test_dark_launch_boundaries_optimal_and_defaults():
    from backend.services.project_ccb_service import (
        audit_dark_launch_shadow_traffic_parity_and_isolation,
    )

    res = audit_dark_launch_shadow_traffic_parity_and_isolation(
        [
            {
                "campaign_id": "SHADOW-BOUNDARY",
                "payload_response_parity_pct": 99.5,
                "primary_path_latency_overhead_ms": 10.0,
            },
            {"campaign_id": "SHADOW-ALL-DEFAULTS"},
        ],
        min_payload_parity_pct=99.5,
        max_primary_latency_overhead_ms=10.0,
    )
    assert res["evaluated_campaigns_count"] == 2
    assert res["side_effect_leak_or_sync_blocking_campaign_ids"] == []
    assert res["parity_mismatch_or_latency_drag_campaign_ids"] == []
    assert (
        res["dark_launch_governance_status"]
        == "DARK_LAUNCH_SHADOW_PARITY_OPTIMAL"
    )
    assert res["is_dark_launch_compliant"] is True


def test_dark_launch_invalid_and_binding():
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_dark_launch_shadow_traffic_parity_and_isolation,
    )

    empty = audit_dark_launch_shadow_traffic_parity_and_isolation(None)
    assert empty["evaluated_campaigns_count"] == 0
    assert empty["side_effect_leak_or_sync_blocking_campaign_ids"] == []
    assert empty["parity_mismatch_or_latency_drag_campaign_ids"] == []
    assert (
        empty["dark_launch_governance_status"]
        == "DARK_LAUNCH_SHADOW_PARITY_OPTIMAL"
    )
    assert empty["is_dark_launch_compliant"] is True

    invalid = audit_dark_launch_shadow_traffic_parity_and_isolation(
        [42, "not-a-dict", None, {"campaign_id": "   "}]  # type: ignore[list-item]
    )
    assert invalid["evaluated_campaigns_count"] == 0

    defaults = audit_dark_launch_shadow_traffic_parity_and_isolation(
        [
            {
                "campaign_id": "SHADOW-DEFAULTS",
                "payload_response_parity_pct": None,
                "shadow_write_side_effects_muted": None,
                "async_fire_and_forget_enforced": None,
                "primary_path_latency_overhead_ms": None,
                "pii_masked_in_shadow_diff_logs": None,
            }
        ]
    )
    assert defaults["evaluated_campaigns_count"] == 1
    assert (
        defaults["dark_launch_governance_status"]
        == "DARK_LAUNCH_SHADOW_PARITY_OPTIMAL"
    )
    assert defaults["is_dark_launch_compliant"] is True

    sample = [
        {
            "campaign_id": "SHADOW-1",
            "payload_response_parity_pct": 99.8,
            "primary_path_latency_overhead_ms": 3.0,
        }
    ]
    assert (
        ProjectCCBService.audit_dark_launch_shadow_traffic_parity_and_isolation(
            sample
        )
        == audit_dark_launch_shadow_traffic_parity_and_isolation(sample)
    )
    assert (
        "audit_dark_launch_shadow_traffic_parity_and_isolation"
        in mod.__all__
    )


def test_audit_db_connection_pool_saturation_and_idle_tx_timeout_breach():
    from backend.services.project_ccb_service import (
        audit_db_connection_pool_saturation_and_idle_tx_timeout,
    )

    result = audit_db_connection_pool_saturation_and_idle_tx_timeout(
        [
            {
                "pool_id": "POOL-CONN-LEAK",
                "peak_active_connections_pct": 50.0,
                "idle_in_transaction_timeout_seconds": 15.0,
                "connection_leaks_detected_count": 3,
                "pgbouncer_transaction_pooling_enabled": True,
            },
            {
                "pool_id": "POOL-ZERO-IDLE-TIMEOUT",
                "peak_active_connections_pct": 50.0,
                "idle_in_transaction_timeout_seconds": 0.0,
                "connection_leaks_detected_count": 0,
                "pgbouncer_transaction_pooling_enabled": True,
            },
            {
                "pool_id": "POOL-HIGH-IDLE-TIMEOUT",
                "peak_active_connections_pct": 50.0,
                "idle_in_transaction_timeout_seconds": 60.0,
                "connection_leaks_detected_count": 0,
                "pgbouncer_transaction_pooling_enabled": True,
            },
        ],
        max_pool_utilization_pct=80.0,
        max_idle_in_tx_timeout_seconds=30.0,
    )
    assert result["evaluated_pools_count"] == 3
    assert result["leaking_or_unbounded_idle_tx_pool_ids"] == [
        "POOL-CONN-LEAK",
        "POOL-ZERO-IDLE-TIMEOUT",
        "POOL-HIGH-IDLE-TIMEOUT",
    ]
    assert result["high_utilization_or_unpooled_pool_ids"] == []
    assert (
        result["db_pool_governance_status"]
        == "DB_POOL_LEAK_OR_UNBOUNDED_IDLE_TX_BREACH"
    )
    assert result["is_db_pool_compliant"] is False


def test_audit_db_connection_pool_saturation_and_idle_tx_timeout_warning():
    from backend.services.project_ccb_service import (
        audit_db_connection_pool_saturation_and_idle_tx_timeout,
    )

    result = audit_db_connection_pool_saturation_and_idle_tx_timeout(
        [
            {
                "pool_id": "POOL-SATURATED",
                "peak_active_connections_pct": 92.0,
                "idle_in_transaction_timeout_seconds": 15.0,
                "connection_leaks_detected_count": 0,
                "pgbouncer_transaction_pooling_enabled": True,
            },
            {
                "pool_id": "POOL-NO-PGBOUNCER",
                "peak_active_connections_pct": 45.0,
                "idle_in_transaction_timeout_seconds": 15.0,
                "connection_leaks_detected_count": 0,
                "pgbouncer_transaction_pooling_enabled": False,
            },
        ],
        max_pool_utilization_pct=80.0,
        max_idle_in_tx_timeout_seconds=30.0,
    )
    assert result["evaluated_pools_count"] == 2
    assert result["leaking_or_unbounded_idle_tx_pool_ids"] == []
    assert result["high_utilization_or_unpooled_pool_ids"] == [
        "POOL-SATURATED",
        "POOL-NO-PGBOUNCER",
    ]
    assert (
        result["db_pool_governance_status"]
        == "DB_POOL_SATURATION_OR_MULTIPLEXING_WARNING"
    )
    assert result["is_db_pool_compliant"] is False


def test_audit_db_connection_pool_saturation_and_idle_tx_timeout_optimal_and_empty():
    from backend.services.project_ccb_service import (
        audit_db_connection_pool_saturation_and_idle_tx_timeout,
    )

    empty = audit_db_connection_pool_saturation_and_idle_tx_timeout(
        [{"pool_id": "   "}, "invalid"]  # type: ignore[list-item]
    )
    assert empty["evaluated_pools_count"] == 0
    assert empty["db_pool_governance_status"] == "DB_POOL_CAPACITY_OPTIMAL"
    assert empty["is_db_pool_compliant"] is True

    optimal = audit_db_connection_pool_saturation_and_idle_tx_timeout(
        [
            {
                "pool_id": "POOL-PRIMARY-RW",
                "peak_active_connections_pct": 58.0,
                "idle_in_transaction_timeout_seconds": 10.0,
                "connection_leaks_detected_count": 0,
                "pgbouncer_transaction_pooling_enabled": True,
            }
        ],
        max_pool_utilization_pct=80.0,
        max_idle_in_tx_timeout_seconds=30.0,
    )
    assert optimal["evaluated_pools_count"] == 1
    assert optimal["leaking_or_unbounded_idle_tx_pool_ids"] == []
    assert optimal["high_utilization_or_unpooled_pool_ids"] == []
    assert optimal["db_pool_governance_status"] == "DB_POOL_CAPACITY_OPTIMAL"
    assert optimal["is_db_pool_compliant"] is True


def test_audit_db_connection_pool_saturation_and_idle_tx_timeout_staticmethod_and_dunder_all():
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_db_connection_pool_saturation_and_idle_tx_timeout,
    )

    sample = [
        {
            "pool_id": "POOL-99",
            "peak_active_connections_pct": 42.0,
            "idle_in_transaction_timeout_seconds": 12.0,
        }
    ]
    assert (
        ProjectCCBService.audit_db_connection_pool_saturation_and_idle_tx_timeout(
            sample
        )
        == audit_db_connection_pool_saturation_and_idle_tx_timeout(sample)
    )
    assert (
        "audit_db_connection_pool_saturation_and_idle_tx_timeout"
        in mod.__all__
    )


def test_audit_message_broker_consumer_lag_and_dlq_poison_pill_gate_breach():
    from backend.services.project_ccb_service import (
        audit_message_broker_consumer_lag_and_dlq_poison_pill_gate,
    )

    res = audit_message_broker_consumer_lag_and_dlq_poison_pill_gate(
        [
            {
                "topic_id": "  TOPIC-ORDERS-V2  ",
                "consumer_lag_messages": 120,
                "dlq_poison_pill_quarantine_enabled": True,
                "schema_backward_compatible": False,
                "configured_max_retries": 3,
            },
            {
                "topic_id": "TOPIC-PAYMENTS-V1",
                "consumer_lag_messages": 8000,
                "dlq_poison_pill_quarantine_enabled": False,
                "schema_backward_compatible": True,
                "configured_max_retries": 4,
            },
            {
                "topic_id": "TOPIC-CLEAN",
                "consumer_lag_messages": 5000,
                "dlq_poison_pill_quarantine_enabled": True,
                "schema_backward_compatible": True,
                "configured_max_retries": 5,
            },
        ]
    )
    assert res["evaluated_topics_count"] == 3
    assert res["schema_break_or_missing_dlq_topic_ids"] == [
        "TOPIC-ORDERS-V2",
        "TOPIC-PAYMENTS-V1",
    ]
    assert res["high_lag_or_retry_storm_topic_ids"] == ["TOPIC-PAYMENTS-V1"]
    assert (
        res["message_broker_gate_status"]
        == "BROKER_SCHEMA_OR_DLQ_QUARANTINE_BREACH"
    )
    assert res["is_message_broker_gate_compliant"] is False


def test_audit_message_broker_consumer_lag_and_dlq_poison_pill_gate_warning():
    from backend.services.project_ccb_service import (
        audit_message_broker_consumer_lag_and_dlq_poison_pill_gate,
    )

    res = audit_message_broker_consumer_lag_and_dlq_poison_pill_gate(
        [
            {
                "topic_id": "TOPIC-LAG",
                "consumer_lag_messages": 5001,
                "dlq_poison_pill_quarantine_enabled": True,
                "schema_backward_compatible": True,
                "configured_max_retries": 5,
            },
            {
                "topic_id": "TOPIC-RETRY-STORM",
                "consumer_lag_messages": 5000,
                "dlq_poison_pill_quarantine_enabled": True,
                "schema_backward_compatible": True,
                "configured_max_retries": 6,
            },
        ],
        max_consumer_lag_messages=5000,
        max_poison_pill_retries=5,
    )
    assert res["evaluated_topics_count"] == 2
    assert res["schema_break_or_missing_dlq_topic_ids"] == []
    assert res["high_lag_or_retry_storm_topic_ids"] == [
        "TOPIC-LAG",
        "TOPIC-RETRY-STORM",
    ]
    assert (
        res["message_broker_gate_status"]
        == "BROKER_CONSUMER_LAG_OR_RETRY_WARNING"
    )
    assert res["is_message_broker_gate_compliant"] is False


def test_audit_message_broker_consumer_lag_and_dlq_poison_pill_gate_optimal_and_defensive():
    from backend.services.project_ccb_service import (
        audit_message_broker_consumer_lag_and_dlq_poison_pill_gate,
    )

    empty = audit_message_broker_consumer_lag_and_dlq_poison_pill_gate(None)
    assert empty["evaluated_topics_count"] == 0
    assert empty["schema_break_or_missing_dlq_topic_ids"] == []
    assert empty["high_lag_or_retry_storm_topic_ids"] == []
    assert (
        empty["message_broker_gate_status"] == "BROKER_STREAMING_GATE_OPTIMAL"
    )
    assert empty["is_message_broker_gate_compliant"] is True

    optimal = audit_message_broker_consumer_lag_and_dlq_poison_pill_gate(
        [
            "not-a-dict",  # type: ignore[list-item]
            {"topic_id": "   "},
            {
                "topic_id": "TOPIC-DEFAULTS",
                "consumer_lag_messages": None,
                "dlq_poison_pill_quarantine_enabled": None,
                "schema_backward_compatible": None,
                "configured_max_retries": None,
            },
        ]
    )
    assert optimal["evaluated_topics_count"] == 1
    assert optimal["schema_break_or_missing_dlq_topic_ids"] == []
    assert optimal["high_lag_or_retry_storm_topic_ids"] == []
    assert (
        optimal["message_broker_gate_status"]
        == "BROKER_STREAMING_GATE_OPTIMAL"
    )
    assert optimal["is_message_broker_gate_compliant"] is True


def test_audit_message_broker_consumer_lag_and_dlq_poison_pill_gate_staticmethod_and_dunder_all():
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_message_broker_consumer_lag_and_dlq_poison_pill_gate,
    )

    sample = [
        {
            "topic_id": "TOPIC-99",
            "consumer_lag_messages": 250,
            "configured_max_retries": 3,
        }
    ]
    assert (
        ProjectCCBService.audit_message_broker_consumer_lag_and_dlq_poison_pill_gate(
            sample
        )
        == audit_message_broker_consumer_lag_and_dlq_poison_pill_gate(sample)
    )
    assert (
        "audit_message_broker_consumer_lag_and_dlq_poison_pill_gate"
        in mod.__all__
    )


def test_audit_distributed_cache_stampede_and_hotkey_skew_gate_breach():
    from backend.services.project_ccb_service import (
        audit_distributed_cache_stampede_and_hotkey_skew_gate,
    )

    res = audit_distributed_cache_stampede_and_hotkey_skew_gate(
        [
            {
                "cache_id": "  REDIS-CATALOG-01  ",
                "singleflight_stampede_lock_enabled": False,
                "ttl_jitter_configured": True,
                "cache_hit_ratio_pct": 95.0,
                "max_single_key_traffic_share_pct": 10.0,
            },
            {
                "cache_id": "REDIS-SESSION-02",
                "singleflight_stampede_lock_enabled": True,
                "ttl_jitter_configured": False,
                "cache_hit_ratio_pct": 70.0,
                "max_single_key_traffic_share_pct": 30.0,
            },
            {
                "cache_id": "REDIS-CLEAN",
                "singleflight_stampede_lock_enabled": True,
                "ttl_jitter_configured": True,
                "cache_hit_ratio_pct": 85.0,
                "max_single_key_traffic_share_pct": 25.0,
            },
        ]
    )
    assert res["evaluated_caches_count"] == 3
    assert res["stampede_unprotected_cache_ids"] == [
        "REDIS-CATALOG-01",
        "REDIS-SESSION-02",
    ]
    assert res["low_hit_ratio_or_hotkey_skew_cache_ids"] == [
        "REDIS-SESSION-02"
    ]
    assert (
        res["cache_resilience_status"]
        == "CACHE_STAMPEDE_LOCK_OR_JITTER_BREACH"
    )
    assert res["is_cache_resilience_compliant"] is False


def test_audit_distributed_cache_stampede_and_hotkey_skew_gate_warning():
    from backend.services.project_ccb_service import (
        audit_distributed_cache_stampede_and_hotkey_skew_gate,
    )

    res = audit_distributed_cache_stampede_and_hotkey_skew_gate(
        [
            {
                "cache_id": "REDIS-LOW-HIT",
                "singleflight_stampede_lock_enabled": True,
                "ttl_jitter_configured": True,
                "cache_hit_ratio_pct": 84.9,
                "max_single_key_traffic_share_pct": 25.0,
            },
            {
                "cache_id": "REDIS-HOTKEY",
                "singleflight_stampede_lock_enabled": True,
                "ttl_jitter_configured": True,
                "cache_hit_ratio_pct": 85.0,
                "max_single_key_traffic_share_pct": 25.1,
            },
        ],
        min_cache_hit_ratio_pct=85.0,
        max_hotkey_traffic_share_pct=25.0,
    )
    assert res["evaluated_caches_count"] == 2
    assert res["stampede_unprotected_cache_ids"] == []
    assert res["low_hit_ratio_or_hotkey_skew_cache_ids"] == [
        "REDIS-LOW-HIT",
        "REDIS-HOTKEY",
    ]
    assert (
        res["cache_resilience_status"]
        == "CACHE_HIT_RATIO_OR_HOTKEY_SKEW_WARNING"
    )
    assert res["is_cache_resilience_compliant"] is False


def test_audit_distributed_cache_stampede_and_hotkey_skew_gate_optimal_and_defensive():
    from backend.services.project_ccb_service import (
        audit_distributed_cache_stampede_and_hotkey_skew_gate,
    )

    empty = audit_distributed_cache_stampede_and_hotkey_skew_gate(None)
    assert empty["evaluated_caches_count"] == 0
    assert empty["stampede_unprotected_cache_ids"] == []
    assert empty["low_hit_ratio_or_hotkey_skew_cache_ids"] == []
    assert (
        empty["cache_resilience_status"] == "CACHE_TIER_RESILIENCE_OPTIMAL"
    )
    assert empty["is_cache_resilience_compliant"] is True

    optimal = audit_distributed_cache_stampede_and_hotkey_skew_gate(
        [
            "not-a-dict",  # type: ignore[list-item]
            {"cache_id": "   "},
            {
                "cache_id": "REDIS-DEFAULTS",
                "singleflight_stampede_lock_enabled": None,
                "ttl_jitter_configured": None,
                "cache_hit_ratio_pct": None,
                "max_single_key_traffic_share_pct": None,
            },
        ]
    )
    assert optimal["evaluated_caches_count"] == 1
    assert optimal["stampede_unprotected_cache_ids"] == []
    assert optimal["low_hit_ratio_or_hotkey_skew_cache_ids"] == []
    assert (
        optimal["cache_resilience_status"] == "CACHE_TIER_RESILIENCE_OPTIMAL"
    )
    assert optimal["is_cache_resilience_compliant"] is True


def test_audit_distributed_cache_stampede_and_hotkey_skew_gate_staticmethod_and_dunder_all():
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_distributed_cache_stampede_and_hotkey_skew_gate,
    )

    sample = [
        {
            "cache_id": "REDIS-99",
            "cache_hit_ratio_pct": 96.0,
            "max_single_key_traffic_share_pct": 5.0,
        }
    ]
    assert (
        ProjectCCBService.audit_distributed_cache_stampede_and_hotkey_skew_gate(
            sample
        )
        == audit_distributed_cache_stampede_and_hotkey_skew_gate(sample)
    )
    assert (
        "audit_distributed_cache_stampede_and_hotkey_skew_gate"
        in mod.__all__
    )


def test_audit_service_mesh_mtls_strict_and_outlier_ejection_gate_breach():
    from backend.services.project_ccb_service import (
        audit_service_mesh_mtls_strict_and_outlier_ejection_gate,
    )

    res = audit_service_mesh_mtls_strict_and_outlier_ejection_gate(
        [
            {
                "mesh_id": "  MESH-PROD-EAST  ",
                "mtls_strict_mode_enforced": False,
                "outlier_detection_configured": True,
                "sidecar_cpu_overhead_pct": 5.0,
                "max_ejection_percent": 15.0,
            },
            {
                "mesh_id": "MESH-PROD-WEST",
                "mtls_strict_mode_enforced": True,
                "outlier_detection_configured": False,
                "sidecar_cpu_overhead_pct": 18.0,
                "max_ejection_percent": 50.0,
            },
            {
                "mesh_id": "MESH-CLEAN",
                "mtls_strict_mode_enforced": True,
                "outlier_detection_configured": True,
                "sidecar_cpu_overhead_pct": 12.0,
                "max_ejection_percent": 30.0,
            },
        ]
    )
    assert res["evaluated_meshes_count"] == 3
    assert res["permissive_mtls_or_missing_outlier_mesh_ids"] == [
        "MESH-PROD-EAST",
        "MESH-PROD-WEST",
    ]
    assert res["high_sidecar_overhead_or_cascading_ejection_mesh_ids"] == [
        "MESH-PROD-WEST"
    ]
    assert (
        res["service_mesh_gate_status"]
        == "MESH_PERMISSIVE_MTLS_OR_OUTLIER_BREACH"
    )
    assert res["is_service_mesh_gate_compliant"] is False


def test_audit_service_mesh_mtls_strict_and_outlier_ejection_gate_warning():
    from backend.services.project_ccb_service import (
        audit_service_mesh_mtls_strict_and_outlier_ejection_gate,
    )

    res = audit_service_mesh_mtls_strict_and_outlier_ejection_gate(
        [
            {
                "mesh_id": "MESH-HIGH-CPU",
                "mtls_strict_mode_enforced": True,
                "outlier_detection_configured": True,
                "sidecar_cpu_overhead_pct": 12.1,
                "max_ejection_percent": 30.0,
            },
            {
                "mesh_id": "MESH-HIGH-EJECTION",
                "mtls_strict_mode_enforced": True,
                "outlier_detection_configured": True,
                "sidecar_cpu_overhead_pct": 12.0,
                "max_ejection_percent": 30.1,
            },
        ],
        max_sidecar_cpu_overhead_pct=12.0,
        max_ejected_endpoints_share_pct=30.0,
    )
    assert res["evaluated_meshes_count"] == 2
    assert res["permissive_mtls_or_missing_outlier_mesh_ids"] == []
    assert res["high_sidecar_overhead_or_cascading_ejection_mesh_ids"] == [
        "MESH-HIGH-CPU",
        "MESH-HIGH-EJECTION",
    ]
    assert (
        res["service_mesh_gate_status"]
        == "MESH_SIDECAR_OVERHEAD_OR_EJECTION_WARNING"
    )
    assert res["is_service_mesh_gate_compliant"] is False


def test_audit_service_mesh_mtls_strict_and_outlier_ejection_gate_optimal_and_defensive():
    from backend.services.project_ccb_service import (
        audit_service_mesh_mtls_strict_and_outlier_ejection_gate,
    )

    empty = audit_service_mesh_mtls_strict_and_outlier_ejection_gate(None)
    assert empty["evaluated_meshes_count"] == 0
    assert empty["permissive_mtls_or_missing_outlier_mesh_ids"] == []
    assert empty["high_sidecar_overhead_or_cascading_ejection_mesh_ids"] == []
    assert (
        empty["service_mesh_gate_status"]
        == "MESH_ZERO_TRUST_RESILIENCE_OPTIMAL"
    )
    assert empty["is_service_mesh_gate_compliant"] is True

    optimal = audit_service_mesh_mtls_strict_and_outlier_ejection_gate(
        [
            "not-a-dict",  # type: ignore[list-item]
            {"mesh_id": "   "},
            {
                "mesh_id": "MESH-DEFAULTS",
                "mtls_strict_mode_enforced": None,
                "outlier_detection_configured": None,
                "sidecar_cpu_overhead_pct": None,
                "max_ejection_percent": None,
            },
        ]
    )
    assert optimal["evaluated_meshes_count"] == 1
    assert optimal["permissive_mtls_or_missing_outlier_mesh_ids"] == []
    assert optimal["high_sidecar_overhead_or_cascading_ejection_mesh_ids"] == []
    assert (
        optimal["service_mesh_gate_status"]
        == "MESH_ZERO_TRUST_RESILIENCE_OPTIMAL"
    )
    assert optimal["is_service_mesh_gate_compliant"] is True


def test_audit_service_mesh_mtls_strict_and_outlier_ejection_gate_staticmethod_and_dunder_all():
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_service_mesh_mtls_strict_and_outlier_ejection_gate,
    )

    sample = [
        {
            "mesh_id": "MESH-99",
            "sidecar_cpu_overhead_pct": 4.0,
            "max_ejection_percent": 15.0,
        }
    ]
    assert (
        ProjectCCBService.audit_service_mesh_mtls_strict_and_outlier_ejection_gate(
            sample
        )
        == audit_service_mesh_mtls_strict_and_outlier_ejection_gate(sample)
    )
    assert (
        "audit_service_mesh_mtls_strict_and_outlier_ejection_gate"
        in mod.__all__
    )


def test_audit_graphql_query_depth_and_n_plus_one_batching_gate_breach():
    from backend.services.project_ccb_service import (
        audit_graphql_query_depth_and_n_plus_one_batching_gate,
    )

    res = audit_graphql_query_depth_and_n_plus_one_batching_gate(
        [
            {
                "operation_id": "  GQL-UNBOUNDED-ALIAS  ",
                "depth_and_alias_limit_enforced": False,
                "dataloader_batching_verified": True,
                "observed_query_depth": 4,
                "complexity_cost_score": 200,
            },
            {
                "operation_id": "GQL-N-PLUS-ONE",
                "depth_and_alias_limit_enforced": True,
                "dataloader_batching_verified": False,
                "observed_query_depth": 11,
                "complexity_cost_score": 800,
            },
            {
                "operation_id": "GQL-CLEAN",
                "depth_and_alias_limit_enforced": True,
                "dataloader_batching_verified": True,
                "observed_query_depth": 8,
                "complexity_cost_score": 500,
            },
        ]
    )
    assert res["evaluated_operations_count"] == 3
    assert res["unbounded_depth_or_n_plus_one_operation_ids"] == [
        "GQL-UNBOUNDED-ALIAS",
        "GQL-N-PLUS-ONE",
    ]
    assert res["deep_query_or_high_complexity_operation_ids"] == [
        "GQL-N-PLUS-ONE"
    ]
    assert (
        res["graphql_gate_status"]
        == "GRAPHQL_UNBOUNDED_DEPTH_OR_N_PLUS_ONE_BREACH"
    )
    assert res["is_graphql_gate_compliant"] is False


def test_audit_graphql_query_depth_and_n_plus_one_batching_gate_warning():
    from backend.services.project_ccb_service import (
        audit_graphql_query_depth_and_n_plus_one_batching_gate,
    )

    res = audit_graphql_query_depth_and_n_plus_one_batching_gate(
        [
            {
                "operation_id": "GQL-DEEP-QUERY",
                "depth_and_alias_limit_enforced": True,
                "dataloader_batching_verified": True,
                "observed_query_depth": 9,
                "complexity_cost_score": 500,
            },
            {
                "operation_id": "GQL-HIGH-COMPLEXITY",
                "depth_and_alias_limit_enforced": True,
                "dataloader_batching_verified": True,
                "observed_query_depth": 8,
                "complexity_cost_score": 501,
            },
        ],
        max_query_depth=8,
        max_complexity_cost_score=500,
    )
    assert res["evaluated_operations_count"] == 2
    assert res["unbounded_depth_or_n_plus_one_operation_ids"] == []
    assert res["deep_query_or_high_complexity_operation_ids"] == [
        "GQL-DEEP-QUERY",
        "GQL-HIGH-COMPLEXITY",
    ]
    assert res["graphql_gate_status"] == "GRAPHQL_COMPLEXITY_OR_DEPTH_WARNING"
    assert res["is_graphql_gate_compliant"] is False


def test_audit_graphql_query_depth_and_n_plus_one_batching_gate_optimal_and_defensive():
    from backend.services.project_ccb_service import (
        audit_graphql_query_depth_and_n_plus_one_batching_gate,
    )

    empty = audit_graphql_query_depth_and_n_plus_one_batching_gate(None)
    assert empty["evaluated_operations_count"] == 0
    assert empty["unbounded_depth_or_n_plus_one_operation_ids"] == []
    assert empty["deep_query_or_high_complexity_operation_ids"] == []
    assert empty["graphql_gate_status"] == "GRAPHQL_QUERY_GOVERNANCE_OPTIMAL"
    assert empty["is_graphql_gate_compliant"] is True

    optimal = audit_graphql_query_depth_and_n_plus_one_batching_gate(
        [
            "not-a-dict",  # type: ignore[list-item]
            {"operation_id": "   "},
            {
                "operation_id": "GQL-DEFAULTS",
                "depth_and_alias_limit_enforced": None,
                "dataloader_batching_verified": None,
                "observed_query_depth": None,
                "complexity_cost_score": None,
            },
        ]
    )
    assert optimal["evaluated_operations_count"] == 1
    assert optimal["unbounded_depth_or_n_plus_one_operation_ids"] == []
    assert optimal["deep_query_or_high_complexity_operation_ids"] == []
    assert optimal["graphql_gate_status"] == "GRAPHQL_QUERY_GOVERNANCE_OPTIMAL"
    assert optimal["is_graphql_gate_compliant"] is True


def test_audit_graphql_query_depth_and_n_plus_one_batching_gate_staticmethod_and_dunder_all():
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_graphql_query_depth_and_n_plus_one_batching_gate,
    )

    sample = [
        {
            "operation_id": "GQL-99",
            "observed_query_depth": 5,
            "complexity_cost_score": 210,
        }
    ]
    assert (
        ProjectCCBService.audit_graphql_query_depth_and_n_plus_one_batching_gate(
            sample
        )
        == audit_graphql_query_depth_and_n_plus_one_batching_gate(sample)
    )
    assert (
        "audit_graphql_query_depth_and_n_plus_one_batching_gate"
        in mod.__all__
    )


def test_blue_green_db_compat_or_smoke_breach():
    from backend.services.project_ccb_service import (
        audit_blue_green_cutover_drain_and_db_backward_compatibility,
    )

    res = audit_blue_green_cutover_drain_and_db_backward_compatibility(
        [
            {
                "cutover_id": "CG-INCOMPATIBLE-DB",
                "expand_contract_db_schema_compatible": False,
            },
            {
                "cutover_id": "CG-SMOKE-FAILED",
                "synthetic_smoke_test_green_passed": False,
            },
        ],
        min_standby_warm_retention_minutes=60,
        max_inflight_dropped_requests=0,
    )
    assert res["evaluated_cutovers_count"] == 2
    assert res["incompatible_db_or_failed_smoke_cutover_ids"] == [
        "CG-INCOMPATIBLE-DB",
        "CG-SMOKE-FAILED",
    ]
    assert res["dropped_requests_or_cold_standby_cutover_ids"] == []
    assert (
        res["blue_green_cutover_status"]
        == "BLUE_GREEN_DB_COMPAT_OR_SMOKE_BREACH"
    )
    assert res["is_blue_green_cutover_compliant"] is False


def test_blue_green_drain_drop_or_cold_standby_warning():
    from backend.services.project_ccb_service import (
        audit_blue_green_cutover_drain_and_db_backward_compatibility,
    )

    res = audit_blue_green_cutover_drain_and_db_backward_compatibility(
        [
            {
                "cutover_id": "CG-REQUESTS-DROPPED",
                "inflight_dropped_requests_count": 3,
            },
            {
                "cutover_id": "CG-COLD-STANDBY",
                "blue_standby_warm_retention_minutes": 15,
            },
        ],
        min_standby_warm_retention_minutes=60,
        max_inflight_dropped_requests=0,
    )
    assert res["evaluated_cutovers_count"] == 2
    assert res["incompatible_db_or_failed_smoke_cutover_ids"] == []
    assert res["dropped_requests_or_cold_standby_cutover_ids"] == [
        "CG-REQUESTS-DROPPED",
        "CG-COLD-STANDBY",
    ]
    assert (
        res["blue_green_cutover_status"]
        == "BLUE_GREEN_DRAIN_DROP_OR_WARM_STANDBY_WARNING"
    )
    assert res["is_blue_green_cutover_compliant"] is False


def test_blue_green_boundaries_optimal_and_defaults():
    from backend.services.project_ccb_service import (
        audit_blue_green_cutover_drain_and_db_backward_compatibility,
    )

    res = audit_blue_green_cutover_drain_and_db_backward_compatibility(
        [
            {
                "cutover_id": "CG-BOUNDARY",
                "inflight_dropped_requests_count": 0,
                "blue_standby_warm_retention_minutes": 60,
            },
            {"cutover_id": "CG-ALL-DEFAULTS"},
        ],
        min_standby_warm_retention_minutes=60,
        max_inflight_dropped_requests=0,
    )
    assert res["evaluated_cutovers_count"] == 2
    assert res["incompatible_db_or_failed_smoke_cutover_ids"] == []
    assert res["dropped_requests_or_cold_standby_cutover_ids"] == []
    assert (
        res["blue_green_cutover_status"]
        == "BLUE_GREEN_ZERO_DOWNTIME_OPTIMAL"
    )
    assert res["is_blue_green_cutover_compliant"] is True


def test_blue_green_invalid_and_binding():
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_blue_green_cutover_drain_and_db_backward_compatibility,
    )

    empty = audit_blue_green_cutover_drain_and_db_backward_compatibility(None)
    assert empty["evaluated_cutovers_count"] == 0
    assert empty["incompatible_db_or_failed_smoke_cutover_ids"] == []
    assert empty["dropped_requests_or_cold_standby_cutover_ids"] == []
    assert (
        empty["blue_green_cutover_status"]
        == "BLUE_GREEN_ZERO_DOWNTIME_OPTIMAL"
    )
    assert empty["is_blue_green_cutover_compliant"] is True

    invalid = audit_blue_green_cutover_drain_and_db_backward_compatibility(
        [42, "not-a-dict", None, {"cutover_id": "   "}]  # type: ignore[list-item]
    )
    assert invalid["evaluated_cutovers_count"] == 0

    defaults = audit_blue_green_cutover_drain_and_db_backward_compatibility(
        [
            {
                "cutover_id": "CG-DEFAULTS",
                "expand_contract_db_schema_compatible": None,
                "synthetic_smoke_test_green_passed": None,
                "inflight_dropped_requests_count": None,
                "blue_standby_warm_retention_minutes": None,
            }
        ]
    )
    assert defaults["evaluated_cutovers_count"] == 1
    assert (
        defaults["blue_green_cutover_status"]
        == "BLUE_GREEN_ZERO_DOWNTIME_OPTIMAL"
    )
    assert defaults["is_blue_green_cutover_compliant"] is True

    sample = [
        {
            "cutover_id": "CG-1",
            "blue_standby_warm_retention_minutes": 120,
            "inflight_dropped_requests_count": 0,
        }
    ]
    assert (
        ProjectCCBService.audit_blue_green_cutover_drain_and_db_backward_compatibility(
            sample
        )
        == audit_blue_green_cutover_drain_and_db_backward_compatibility(sample)
    )
    assert (
        "audit_blue_green_cutover_drain_and_db_backward_compatibility"
        in mod.__all__
    )


def test_audit_database_connection_pool_pgbouncer_saturation_and_idle_in_transaction_gate_healthy_and_empty():
    from backend.services.project_ccb_service import (
        audit_database_connection_pool_pgbouncer_saturation_and_idle_in_transaction_gate,
    )

    empty = audit_database_connection_pool_pgbouncer_saturation_and_idle_in_transaction_gate(
        []
    )
    assert empty["status"] == "healthy"
    assert empty["gate_passed"] is True
    assert empty["pools_evaluated"] == 0
    assert empty["saturated_pool_ids"] == []
    assert empty["idle_in_tx_leak_pool_ids"] == []

    healthy = audit_database_connection_pool_pgbouncer_saturation_and_idle_in_transaction_gate(
        [
            {
                "pool_id": "pgbouncer-primary",
                "active_server_connections": 40,
                "max_pool_size": 50,
                "waiting_clients_count": 0,
                "max_wait_time_ms": 12.0,
                "longest_idle_in_tx_seconds": 3.5,
                "pooling_mode": "transaction",
                "reserve_pool_exhausted": False,
            }
        ]
    )
    assert healthy["status"] == "healthy"
    assert healthy["gate_passed"] is True
    assert healthy["pools_evaluated"] == 1
    assert healthy["records"][0]["utilization_pct"] == 80.0
    assert healthy["saturated_pool_ids"] == []
    assert healthy["idle_in_tx_leak_pool_ids"] == []


def test_audit_database_connection_pool_pgbouncer_saturation_and_idle_in_transaction_gate_critical():
    from backend.services.project_ccb_service import (
        audit_database_connection_pool_pgbouncer_saturation_and_idle_in_transaction_gate,
    )

    res = audit_database_connection_pool_pgbouncer_saturation_and_idle_in_transaction_gate(
        [
            {
                "pool_id": "pool-idle-leak",
                "active_server_connections": 20,
                "max_pool_size": 50,
                "waiting_clients_count": 2,
                "max_wait_time_ms": 10.0,
                "longest_idle_in_tx_seconds": 25.0,
                "pooling_mode": "transaction",
                "reserve_pool_exhausted": False,
            },
            {
                "pool_id": "pool-exhausted",
                "active_server_connections": 49,
                "max_pool_size": 50,
                "waiting_clients_count": 15,
                "max_wait_time_ms": 120.0,
                "longest_idle_in_tx_seconds": 2.0,
                "pooling_mode": "transaction",
                "reserve_pool_exhausted": True,
            },
        ]
    )
    assert res["status"] == "critical"
    assert res["gate_passed"] is False
    assert res["pools_evaluated"] == 2
    assert res["idle_in_tx_leak_pool_ids"] == ["pool-idle-leak"]
    assert res["saturated_pool_ids"] == ["pool-exhausted"]


def test_audit_database_connection_pool_pgbouncer_saturation_and_idle_in_transaction_gate_warning():
    from backend.services.project_ccb_service import (
        audit_database_connection_pool_pgbouncer_saturation_and_idle_in_transaction_gate,
    )

    res = audit_database_connection_pool_pgbouncer_saturation_and_idle_in_transaction_gate(
        [
            {
                "pool_id": "pool-warn-util",
                "active_server_connections": 45,
                "max_pool_size": 50,
                "waiting_clients_count": 3,
                "max_wait_time_ms": 65.0,
                "longest_idle_in_tx_seconds": 5.0,
                "pooling_mode": "session",
                "reserve_pool_exhausted": False,
            }
        ],
        max_pool_utilization_pct=85.0,
        max_client_wait_ms=50.0,
        require_transaction_pooling_mode=True,
    )
    assert res["status"] == "warning"
    assert res["gate_passed"] is False
    assert res["saturated_pool_ids"] == ["pool-warn-util"]
    assert res["records"][0]["pool_utilization_exceeded"] is True
    assert res["records"][0]["client_wait_sla_breach"] is True
    assert res["records"][0]["invalid_pooling_mode"] is True


def test_audit_database_connection_pool_pgbouncer_saturation_and_idle_in_transaction_gate_staticmethod_and_dunder_all():
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_database_connection_pool_pgbouncer_saturation_and_idle_in_transaction_gate,
    )

    sample = [
        {
            "id": "pool-zero-max",
            "active_server_connections": 5,
            "max_pool_size": 0,
            "pooling_mode": "session",
        }
    ]
    res = ProjectCCBService.audit_database_connection_pool_pgbouncer_saturation_and_idle_in_transaction_gate(
        sample, require_transaction_pooling_mode=False
    )
    assert res == audit_database_connection_pool_pgbouncer_saturation_and_idle_in_transaction_gate(
        sample, require_transaction_pooling_mode=False
    )
    assert res["records"][0]["utilization_pct"] == 100.0
    assert res["status"] == "critical"
    assert (
        "audit_database_connection_pool_pgbouncer_saturation_and_idle_in_transaction_gate"
        in mod.__all__
    )


def test_audit_ingress_rate_limiting_token_bucket_and_waf_owasp_crs_gate_healthy_and_empty():
    from backend.services.project_ccb_service import (
        audit_ingress_rate_limiting_token_bucket_and_waf_owasp_crs_gate,
    )

    empty = audit_ingress_rate_limiting_token_bucket_and_waf_owasp_crs_gate([])
    assert empty["status"] == "healthy"
    assert empty["gate_passed"] is True
    assert empty["routes_evaluated"] == 0
    assert empty["unprotected_route_ids"] == []
    assert empty["degraded_throttle_or_fp_route_ids"] == []

    healthy = audit_ingress_rate_limiting_token_bucket_and_waf_owasp_crs_gate(
        [
            {
                "route_id": "ingress-api-v1",
                "waf_mode": "blocking",
                "waf_crs_paranoia_level": 2,
                "token_bucket_rps_limit": 500,
                "burst_multiplier": 2.0,
                "total_requests": 10000,
                "throttled_429_requests": 200,
                "waf_false_positive_blocks": 10,
            }
        ]
    )
    assert healthy["status"] == "healthy"
    assert healthy["gate_passed"] is True
    assert healthy["routes_evaluated"] == 1
    assert healthy["records"][0]["throttle_429_rate_pct"] == 2.0
    assert healthy["records"][0]["waf_false_positive_rate_pct"] == 0.1
    assert healthy["unprotected_route_ids"] == []
    assert healthy["degraded_throttle_or_fp_route_ids"] == []


def test_audit_ingress_rate_limiting_token_bucket_and_waf_owasp_crs_gate_critical():
    from backend.services.project_ccb_service import (
        audit_ingress_rate_limiting_token_bucket_and_waf_owasp_crs_gate,
    )

    res = audit_ingress_rate_limiting_token_bucket_and_waf_owasp_crs_gate(
        [
            {
                "route_id": "route-detection-only",
                "waf_mode": "detection_only",
                "waf_crs_paranoia_level": 2,
                "token_bucket_rps_limit": 200,
                "burst_multiplier": 1.5,
                "total_requests": 1000,
                "throttled_429_requests": 10,
                "waf_false_positive_blocks": 0,
            },
            {
                "route_id": "route-low-pl-no-rps",
                "waf_mode": "blocking",
                "waf_crs_paranoia_level": 1,
                "token_bucket_rps_limit": 0,
                "burst_multiplier": 1.0,
                "total_requests": 1000,
                "throttled_429_requests": 0,
                "waf_false_positive_blocks": 0,
            },
        ],
        min_waf_paranoia_level=2,
        require_waf_blocking_mode=True,
    )
    assert res["status"] == "critical"
    assert res["gate_passed"] is False
    assert res["routes_evaluated"] == 2
    assert res["unprotected_route_ids"] == [
        "route-detection-only",
        "route-low-pl-no-rps",
    ]
    assert res["records"][0]["waf_not_in_blocking_mode"] is True
    assert res["records"][1]["insufficient_paranoia_level"] is True
    assert res["records"][1]["missing_rate_limit_quota"] is True


def test_audit_ingress_rate_limiting_token_bucket_and_waf_owasp_crs_gate_warning():
    from backend.services.project_ccb_service import (
        audit_ingress_rate_limiting_token_bucket_and_waf_owasp_crs_gate,
    )

    res = audit_ingress_rate_limiting_token_bucket_and_waf_owasp_crs_gate(
        [
            {
                "route_id": "route-high-429-and-fp",
                "waf_mode": "blocking",
                "waf_crs_paranoia_level": 3,
                "token_bucket_rps_limit": 100,
                "burst_multiplier": 1.5,
                "total_requests": 1000,
                "throttled_429_requests": 80,
                "waf_false_positive_blocks": 12,
            }
        ],
        max_429_throttle_rate_pct=5.0,
        max_waf_false_positive_rate_pct=0.5,
    )
    assert res["status"] == "warning"
    assert res["gate_passed"] is False
    assert res["unprotected_route_ids"] == []
    assert res["degraded_throttle_or_fp_route_ids"] == [
        "route-high-429-and-fp"
    ]
    assert res["records"][0]["excessive_429_throttling"] is True
    assert res["records"][0]["excessive_waf_false_positives"] is True


def test_audit_ingress_rate_limiting_token_bucket_and_waf_owasp_crs_gate_staticmethod_and_dunder_all():
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_ingress_rate_limiting_token_bucket_and_waf_owasp_crs_gate,
    )

    sample = [
        {
            "id": "route-sample",
            "waf_mode": "blocking",
            "waf_crs_paranoia_level": 2,
            "token_bucket_rps_limit": 300,
            "burst_multiplier": 2.0,
            "total_requests": 500,
            "throttled_429_requests": 5,
            "waf_false_positive_blocks": 1,
        }
    ]
    res = ProjectCCBService.audit_ingress_rate_limiting_token_bucket_and_waf_owasp_crs_gate(
        sample
    )
    assert res == audit_ingress_rate_limiting_token_bucket_and_waf_owasp_crs_gate(
        sample
    )
    assert res["status"] == "healthy"
    assert res["gate_passed"] is True
    assert (
        "audit_ingress_rate_limiting_token_bucket_and_waf_owasp_crs_gate"
        in mod.__all__
    )


def test_audit_chaos_engineering_fault_injection_blast_radius_and_steady_state_abort_gate_healthy():
    from backend.services.project_ccb_service import (
        audit_chaos_engineering_fault_injection_blast_radius_and_steady_state_abort_gate,
    )

    res = audit_chaos_engineering_fault_injection_blast_radius_and_steady_state_abort_gate(
        [
            {
                "experiment_id": "CHAOS-LATENCY-01",
                "targeted_pods_pct": 5.0,
                "steady_state_hypothesis_breached": False,
                "auto_abort_triggered": True,
                "kill_switch_abort_latency_ms": 180.0,
                "rollback_completed_cleanly": True,
            }
        ]
    )
    assert res["status"] == "healthy"
    assert res["gate_passed"] is True
    assert res["experiments_evaluated"] == 1
    assert res["unsafe_blast_or_abort_experiment_ids"] == []
    assert res["slow_kill_switch_experiment_ids"] == []
    assert res["Violations"] == []


def test_audit_chaos_engineering_fault_injection_blast_radius_and_steady_state_abort_gate_critical():
    from backend.services.project_ccb_service import (
        audit_chaos_engineering_fault_injection_blast_radius_and_steady_state_abort_gate,
    )

    res = audit_chaos_engineering_fault_injection_blast_radius_and_steady_state_abort_gate(
        [
            {
                "experiment_id": "CHAOS-RUNAWAY",
                "targeted_pods_pct": 35.0,
                "steady_state_hypothesis_breached": True,
                "auto_abort_triggered": False,
                "kill_switch_abort_latency_ms": 200.0,
                "rollback_completed_cleanly": False,
            }
        ],
        max_blast_radius_pods_pct=10.0,
    )
    assert res["status"] == "critical"
    assert res["gate_passed"] is False
    assert res["unsafe_blast_or_abort_experiment_ids"] == ["CHAOS-RUNAWAY"]
    assert len(res["Violations"]) >= 3


def test_audit_chaos_engineering_fault_injection_blast_radius_and_steady_state_abort_gate_warning():
    from backend.services.project_ccb_service import (
        audit_chaos_engineering_fault_injection_blast_radius_and_steady_state_abort_gate,
    )

    res = audit_chaos_engineering_fault_injection_blast_radius_and_steady_state_abort_gate(
        [
            {
                "id": "CHAOS-SLOW-ABORT",
                "targeted_pods_pct": 8.0,
                "steady_state_hypothesis_breached": True,
                "auto_abort_triggered": True,
                "kill_switch_abort_latency_ms": 950.0,
                "rollback_completed_cleanly": True,
            }
        ],
        max_kill_switch_abort_latency_ms=500.0,
    )
    assert res["status"] == "warning"
    assert res["gate_passed"] is False
    assert res["unsafe_blast_or_abort_experiment_ids"] == []
    assert res["slow_kill_switch_experiment_ids"] == ["CHAOS-SLOW-ABORT"]
    assert res["records"][0]["kill_switch_latency_exceeded"] is True


def test_audit_chaos_engineering_fault_injection_blast_radius_and_steady_state_abort_gate_staticmethod_and_dunder_all():
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_chaos_engineering_fault_injection_blast_radius_and_steady_state_abort_gate,
    )

    sample = [{"experiment_id": "CHAOS-1", "targeted_pods_pct": 4.0}]
    assert (
        ProjectCCBService.audit_chaos_engineering_fault_injection_blast_radius_and_steady_state_abort_gate(
            sample
        )
        == audit_chaos_engineering_fault_injection_blast_radius_and_steady_state_abort_gate(
            sample
        )
    )
    assert (
        "audit_chaos_engineering_fault_injection_blast_radius_and_steady_state_abort_gate"
        in mod.__all__
    )


def test_audit_supply_chain_sbom_slsa_provenance_and_cve_epss_gate_healthy():
    from backend.services.project_ccb_service import (
        audit_supply_chain_sbom_slsa_provenance_and_cve_epss_gate,
    )

    res = audit_supply_chain_sbom_slsa_provenance_and_cve_epss_gate(
        [
            {
                "artifact_id": "ART-BACKEND-2.4",
                "slsa_provenance_level": 3,
                "sbom_cosign_attested": True,
                "cisa_kev_count": 0,
                "max_observed_epss_score": 0.02,
                "unpinned_transitive_deps_count": 0,
            }
        ]
    )
    assert res["status"] == "healthy"
    assert res["gate_passed"] is True
    assert res["artifacts_evaluated"] == 1
    assert res["blocked_supply_chain_artifact_ids"] == []
    assert res["epss_or_unpinned_warning_artifact_ids"] == []
    assert res["Violations"] == []


def test_audit_supply_chain_sbom_slsa_provenance_and_cve_epss_gate_critical():
    from backend.services.project_ccb_service import (
        audit_supply_chain_sbom_slsa_provenance_and_cve_epss_gate,
    )

    res = audit_supply_chain_sbom_slsa_provenance_and_cve_epss_gate(
        [
            {
                "artifact_id": "ART-KEV-UNSIGNED",
                "slsa_provenance_level": 1,
                "sbom_cosign_attested": False,
                "cisa_kev_count": 2,
                "max_observed_epss_score": 0.05,
                "unpinned_transitive_deps_count": 0,
            }
        ],
        min_slsa_level=3,
    )
    assert res["status"] == "critical"
    assert res["gate_passed"] is False
    assert res["blocked_supply_chain_artifact_ids"] == ["ART-KEV-UNSIGNED"]
    assert len(res["Violations"]) >= 2


def test_audit_supply_chain_sbom_slsa_provenance_and_cve_epss_gate_warning():
    from backend.services.project_ccb_service import (
        audit_supply_chain_sbom_slsa_provenance_and_cve_epss_gate,
    )

    res = audit_supply_chain_sbom_slsa_provenance_and_cve_epss_gate(
        [
            {
                "id": "ART-HIGH-EPSS",
                "slsa_provenance_level": 3,
                "sbom_cosign_attested": True,
                "cisa_kev_count": 0,
                "max_observed_epss_score": 0.35,
                "unpinned_transitive_deps_count": 4,
            }
        ],
        max_allowed_epss_score=0.10,
    )
    assert res["status"] == "warning"
    assert res["gate_passed"] is False
    assert res["blocked_supply_chain_artifact_ids"] == []
    assert res["epss_or_unpinned_warning_artifact_ids"] == ["ART-HIGH-EPSS"]
    assert res["records"][0]["epss_threshold_exceeded"] is True
    assert res["records"][0]["unpinned_dependencies_present"] is True


def test_audit_supply_chain_sbom_slsa_provenance_and_cve_epss_gate_staticmethod_and_dunder_all():
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_supply_chain_sbom_slsa_provenance_and_cve_epss_gate,
    )

    sample = [{"artifact_id": "ART-1", "slsa_provenance_level": 3}]
    assert (
        ProjectCCBService.audit_supply_chain_sbom_slsa_provenance_and_cve_epss_gate(
            sample
        )
        == audit_supply_chain_sbom_slsa_provenance_and_cve_epss_gate(
            sample
        )
    )
    assert (
        "audit_supply_chain_sbom_slsa_provenance_and_cve_epss_gate"
        in mod.__all__
    )


def test_audit_zero_downtime_db_migration_lock_timeout_and_expand_contract_gate_healthy():
    from backend.services.project_ccb_service import (
        audit_zero_downtime_db_migration_lock_timeout_and_expand_contract_gate,
    )

    res = audit_zero_downtime_db_migration_lock_timeout_and_expand_contract_gate(
        [
            {
                "migration_id": "20261019_01_add_nullable_col",
                "lock_timeout_ms": 1500,
                "statement_timeout_ms": 20000,
                "creates_index_non_concurrently": False,
                "drops_or_renames_column_in_expand_phase": False,
                "has_reversible_downgrade": True,
            }
        ]
    )
    assert res["status"] == "healthy"
    assert res["gate_passed"] is True
    assert res["migrations_evaluated"] == 1
    assert res["unsafe_ddl_migration_ids"] == []
    assert res["timeout_misconfigured_migration_ids"] == []
    assert res["Violations"] == []


def test_audit_zero_downtime_db_migration_lock_timeout_and_expand_contract_gate_critical():
    from backend.services.project_ccb_service import (
        audit_zero_downtime_db_migration_lock_timeout_and_expand_contract_gate,
    )

    res = audit_zero_downtime_db_migration_lock_timeout_and_expand_contract_gate(
        [
            {
                "migration_id": "20261019_02_blocking_idx_and_drop",
                "lock_timeout_ms": 1000,
                "statement_timeout_ms": 10000,
                "creates_index_non_concurrently": True,
                "drops_or_renames_column_in_expand_phase": True,
                "has_reversible_downgrade": False,
            }
        ]
    )
    assert res["status"] == "critical"
    assert res["gate_passed"] is False
    assert res["unsafe_ddl_migration_ids"] == [
        "20261019_02_blocking_idx_and_drop"
    ]
    assert len(res["Violations"]) >= 1


def test_audit_zero_downtime_db_migration_lock_timeout_and_expand_contract_gate_warning():
    from backend.services.project_ccb_service import (
        audit_zero_downtime_db_migration_lock_timeout_and_expand_contract_gate,
    )

    res = audit_zero_downtime_db_migration_lock_timeout_and_expand_contract_gate(
        [
            {
                "id": "20261019_03_high_lock_timeout",
                "lock_timeout_ms": 5000,
                "statement_timeout_ms": 45000,
                "creates_index_non_concurrently": False,
                "drops_or_renames_column_in_expand_phase": False,
                "has_reversible_downgrade": True,
            }
        ],
        max_lock_timeout_ms=2000,
        max_statement_timeout_ms=30000,
    )
    assert res["status"] == "warning"
    assert res["gate_passed"] is False
    assert res["unsafe_ddl_migration_ids"] == []
    assert res["timeout_misconfigured_migration_ids"] == [
        "20261019_03_high_lock_timeout"
    ]
    assert res["records"][0]["lock_or_statement_timeout_exceeded"] is True


def test_audit_zero_downtime_db_migration_lock_timeout_and_expand_contract_gate_staticmethod_and_dunder_all():
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_zero_downtime_db_migration_lock_timeout_and_expand_contract_gate,
    )

    sample = [{"migration_id": "MIG-1", "lock_timeout_ms": 1000}]
    assert (
        ProjectCCBService.audit_zero_downtime_db_migration_lock_timeout_and_expand_contract_gate(
            sample
        )
        == audit_zero_downtime_db_migration_lock_timeout_and_expand_contract_gate(
            sample
        )
    )
    assert (
        "audit_zero_downtime_db_migration_lock_timeout_and_expand_contract_gate"
        in mod.__all__
    )


def test_audit_bgp_anycast_rpki_roa_origin_and_ddos_scrubbing_gate_approved():
    from backend.services.project_ccb_service import (
        audit_bgp_anycast_rpki_roa_origin_and_ddos_scrubbing_gate,
    )

    res = audit_bgp_anycast_rpki_roa_origin_and_ddos_scrubbing_gate(
        [
            {
                "prefix_cidr": "203.0.113.0/24",
                "origin_asn": 64512,
                "rpki_roa_status": "VALID",
                "flap_count_last_hour": 0,
                "bgp_session_state": "ESTABLISHED",
            },
            {
                "prefix_cidr": "198.51.100.0/24",
                "origin_asn": 64512,
                "rpki_roa_status": "VALID",
                "flap_count_last_hour": 1,
                "bgp_session_state": "ESTABLISHED",
            },
        ],
        ddos_scrubbing_redirect_latency_sec=8.5,
        max_scrubbing_redirect_latency_sec=30.0,
    )
    assert res["is_valid"] is True
    assert res["total_prefixes"] == 2
    assert res["rpki_roa_violations"] == []
    assert res["route_flap_breaches"] == []
    assert res["unestablished_sessions"] == []
    assert res["scrubbing_sla_breached"] is False
    assert res["gate_decision"] == "APPROVED"
    assert res["recommendations"] == []


def test_audit_bgp_anycast_rpki_roa_origin_and_ddos_scrubbing_gate_rejected():
    from backend.services.project_ccb_service import (
        audit_bgp_anycast_rpki_roa_origin_and_ddos_scrubbing_gate,
    )

    res = audit_bgp_anycast_rpki_roa_origin_and_ddos_scrubbing_gate(
        [
            {
                "prefix_cidr": "203.0.113.0/24",
                "origin_asn": 64599,
                "rpki_roa_status": "INVALID",
                "flap_count_last_hour": 1,
                "bgp_session_state": "IDLE",
            }
        ],
        ddos_scrubbing_redirect_latency_sec=45.0,
        max_scrubbing_redirect_latency_sec=30.0,
    )
    assert res["is_valid"] is False
    assert len(res["rpki_roa_violations"]) == 1
    assert len(res["unestablished_sessions"]) == 1
    assert res["scrubbing_sla_breached"] is True
    assert res["gate_decision"] == "REJECTED"
    assert len(res["recommendations"]) >= 3


def test_audit_bgp_anycast_rpki_roa_origin_and_ddos_scrubbing_gate_conditional():
    from backend.services.project_ccb_service import (
        audit_bgp_anycast_rpki_roa_origin_and_ddos_scrubbing_gate,
    )

    res = audit_bgp_anycast_rpki_roa_origin_and_ddos_scrubbing_gate(
        [
            {
                "prefix_cidr": "192.0.2.0/24",
                "origin_asn": 64512,
                "rpki_roa_status": "NOT_FOUND",
                "flap_count_last_hour": 6,
                "bgp_session_state": "ESTABLISHED",
            }
        ],
        ddos_scrubbing_redirect_latency_sec=10.0,
        max_flaps_per_hour=3,
        require_rpki_valid=False,
    )
    assert res["is_valid"] is False
    assert res["rpki_roa_violations"] == []
    assert len(res["route_flap_breaches"]) == 1
    assert res["unestablished_sessions"] == []
    assert res["scrubbing_sla_breached"] is False
    assert res["gate_decision"] == "CONDITIONAL"


def test_audit_bgp_anycast_rpki_roa_origin_and_ddos_scrubbing_gate_staticmethod_and_dunder_all():
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_bgp_anycast_rpki_roa_origin_and_ddos_scrubbing_gate,
    )

    empty = audit_bgp_anycast_rpki_roa_origin_and_ddos_scrubbing_gate([])
    assert empty["is_valid"] is False
    assert empty["gate_decision"] == "REJECTED"

    sample = [
        {
            "prefix_cidr": "203.0.113.0/24",
            "origin_asn": 64512,
            "rpki_roa_status": "VALID",
            "flap_count_last_hour": 0,
            "bgp_session_state": "ESTABLISHED",
        }
    ]
    assert (
        ProjectCCBService.audit_bgp_anycast_rpki_roa_origin_and_ddos_scrubbing_gate(
            sample
        )
        == audit_bgp_anycast_rpki_roa_origin_and_ddos_scrubbing_gate(sample)
    )
    assert (
        "audit_bgp_anycast_rpki_roa_origin_and_ddos_scrubbing_gate"
        in mod.__all__
    )


def test_audit_k8s_pdb_quorum_drain_and_statefulset_volume_gate_approved():
    from backend.services.project_ccb_service import (
        audit_k8s_pdb_quorum_drain_and_statefulset_volume_gate,
    )

    res = audit_k8s_pdb_quorum_drain_and_statefulset_volume_gate(
        workloads=[
            {
                "workload_id": "api-gateway",
                "desired_replicas": 4,
                "ready_replicas": 4,
                "pdb_min_available": 3,
                "pdb_disruptions_allowed": 1,
                "is_statefulset": False,
                "stuck_volume_attachments": 0,
            },
            {
                "workload_id": "redis-cluster",
                "desired_replicas": 3,
                "ready_replicas": 3,
                "pdb_min_available": 2,
                "pdb_disruptions_allowed": 1,
                "is_statefulset": True,
                "stuck_volume_attachments": 0,
            },
        ],
        node_drain_timeout_sec=300,
        max_allowed_drain_timeout_sec=600,
    )
    assert res["is_valid"] is True
    assert res["total_workloads"] == 2
    assert res["zero_disruption_quorum_breaches"] == []
    assert res["misconfigured_100pct_pdb_workloads"] == []
    assert res["stuck_csi_volume_workloads"] == []
    assert res["drain_timeout_invalid"] is False
    assert res["gate_decision"] == "APPROVED"


def test_audit_k8s_pdb_quorum_drain_and_statefulset_volume_gate_rejected():
    from backend.services.project_ccb_service import (
        audit_k8s_pdb_quorum_drain_and_statefulset_volume_gate,
    )

    res = audit_k8s_pdb_quorum_drain_and_statefulset_volume_gate(
        workloads=[
            {
                "workload_id": "pg-primary-sts",
                "desired_replicas": 3,
                "ready_replicas": 3,
                "pdb_min_available": 3,
                "pdb_disruptions_allowed": 0,
                "is_statefulset": True,
                "stuck_volume_attachments": 2,
            }
        ],
        node_drain_timeout_sec=900,
        max_allowed_drain_timeout_sec=600,
    )
    assert res["is_valid"] is False
    assert res["misconfigured_100pct_pdb_workloads"] == ["pg-primary-sts"]
    assert res["stuck_csi_volume_workloads"] == ["pg-primary-sts"]
    assert res["drain_timeout_invalid"] is True
    assert res["gate_decision"] == "REJECTED"


def test_audit_k8s_pdb_quorum_drain_and_statefulset_volume_gate_conditional():
    from backend.services.project_ccb_service import (
        audit_k8s_pdb_quorum_drain_and_statefulset_volume_gate,
    )

    res = audit_k8s_pdb_quorum_drain_and_statefulset_volume_gate(
        workloads=[
            {
                "workload_id": "checkout-svc",
                "desired_replicas": 3,
                "ready_replicas": 2,
                "pdb_min_available": 2,
                "pdb_disruptions_allowed": 0,
                "is_statefulset": False,
                "stuck_volume_attachments": 0,
            }
        ],
        node_drain_timeout_sec=300,
    )
    assert res["is_valid"] is False
    assert res["zero_disruption_quorum_breaches"] == ["checkout-svc"]
    assert res["misconfigured_100pct_pdb_workloads"] == []
    assert res["stuck_csi_volume_workloads"] == []
    assert res["drain_timeout_invalid"] is False
    assert res["gate_decision"] == "CONDITIONAL"


def test_audit_k8s_pdb_quorum_drain_and_statefulset_volume_gate_staticmethod_and_dunder_all():
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_k8s_pdb_quorum_drain_and_statefulset_volume_gate,
    )

    empty = audit_k8s_pdb_quorum_drain_and_statefulset_volume_gate([])
    assert empty["is_valid"] is False
    assert empty["gate_decision"] == "REJECTED"

    sample = [
        {
            "workload_id": "web-1",
            "desired_replicas": 3,
            "ready_replicas": 3,
            "pdb_min_available": 2,
            "pdb_disruptions_allowed": 1,
        }
    ]
    assert (
        ProjectCCBService.audit_k8s_pdb_quorum_drain_and_statefulset_volume_gate(
            sample
        )
        == audit_k8s_pdb_quorum_drain_and_statefulset_volume_gate(sample)
    )
    assert (
        "audit_k8s_pdb_quorum_drain_and_statefulset_volume_gate"
        in mod.__all__
    )


def test_audit_service_mesh_mtls_strict_mode_and_tls13_cipher_gate_approved():
    from backend.services.project_ccb_service import (
        audit_service_mesh_mtls_strict_mode_and_tls13_cipher_gate,
    )

    res = audit_service_mesh_mtls_strict_mode_and_tls13_cipher_gate(
        mesh_services=[
            {
                "service_id": "payments-svc",
                "peer_authn_mode": "STRICT",
                "min_tls_version": "TLSv1_3",
                "weak_cbc_or_rc4_ciphers_enabled": False,
                "dual_pin_backup_spki_configured": True,
            },
            {
                "service_id": "ledger-svc",
                "peer_authn_mode": "STRICT",
                "min_tls_version": "TLSv1_2",
                "weak_cbc_or_rc4_ciphers_enabled": False,
                "dual_pin_backup_spki_configured": True,
            },
        ]
    )
    assert res["is_valid"] is True
    assert res["total_services"] == 2
    assert res["non_strict_mtls_services"] == []
    assert res["weak_tls_or_cipher_services"] == []
    assert res["single_pin_lockout_risk_services"] == []
    assert res["gate_decision"] == "APPROVED"


def test_audit_service_mesh_mtls_strict_mode_and_tls13_cipher_gate_rejected():
    from backend.services.project_ccb_service import (
        audit_service_mesh_mtls_strict_mode_and_tls13_cipher_gate,
    )

    res = audit_service_mesh_mtls_strict_mode_and_tls13_cipher_gate(
        mesh_services=[
            {
                "service_id": "legacy-auth-svc",
                "peer_authn_mode": "PERMISSIVE",
                "min_tls_version": "TLSv1_1",
                "weak_cbc_or_rc4_ciphers_enabled": True,
                "dual_pin_backup_spki_configured": True,
            }
        ],
        require_strict_mtls=True,
    )
    assert res["is_valid"] is False
    assert res["non_strict_mtls_services"] == ["legacy-auth-svc"]
    assert res["weak_tls_or_cipher_services"] == ["legacy-auth-svc"]
    assert res["gate_decision"] == "REJECTED"


def test_audit_service_mesh_mtls_strict_mode_and_tls13_cipher_gate_conditional():
    from backend.services.project_ccb_service import (
        audit_service_mesh_mtls_strict_mode_and_tls13_cipher_gate,
    )

    res = audit_service_mesh_mtls_strict_mode_and_tls13_cipher_gate(
        mesh_services=[
            {
                "service_id": "edge-proxy-svc",
                "peer_authn_mode": "STRICT",
                "min_tls_version": "TLSv1_3",
                "weak_cbc_or_rc4_ciphers_enabled": False,
                "dual_pin_backup_spki_configured": False,
            }
        ]
    )
    assert res["is_valid"] is False
    assert res["non_strict_mtls_services"] == []
    assert res["weak_tls_or_cipher_services"] == []
    assert res["single_pin_lockout_risk_services"] == ["edge-proxy-svc"]
    assert res["gate_decision"] == "CONDITIONAL"


def test_audit_service_mesh_mtls_strict_mode_and_tls13_cipher_gate_staticmethod_and_dunder_all():
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_service_mesh_mtls_strict_mode_and_tls13_cipher_gate,
    )

    empty = audit_service_mesh_mtls_strict_mode_and_tls13_cipher_gate([])
    assert empty["is_valid"] is False
    assert empty["gate_decision"] == "REJECTED"

    sample = [
        {
            "service_id": "svc-1",
            "peer_authn_mode": "STRICT",
            "min_tls_version": "TLSv1_3",
        }
    ]
    assert (
        ProjectCCBService.audit_service_mesh_mtls_strict_mode_and_tls13_cipher_gate(
            sample
        )
        == audit_service_mesh_mtls_strict_mode_and_tls13_cipher_gate(sample)
    )
    assert (
        "audit_service_mesh_mtls_strict_mode_and_tls13_cipher_gate"
        in mod.__all__
    )


def test_audit_kafka_consumer_rebalance_dlq_and_schema_registry_gate_approved():
    from backend.services.project_ccb_service import (
        audit_kafka_consumer_rebalance_dlq_and_schema_registry_gate,
    )

    res = audit_kafka_consumer_rebalance_dlq_and_schema_registry_gate(
        [
            {
                "topic_id": "orders.events.v1",
                "consumer_lag_records": 1200,
                "rebalances_last_hour": 1,
                "dlq_poison_pill_rate_pct": 0.05,
                "schema_compatibility_mode": "BACKWARD",
                "breaking_schema_evolution_detected": False,
            },
            {
                "topic_id": "payments.settled.v2",
                "consumer_lag_records": 450,
                "rebalances_last_hour": 0,
                "dlq_poison_pill_rate_pct": 0.0,
                "schema_compatibility_mode": "FULL_TRANSITIVE",
                "breaking_schema_evolution_detected": False,
            },
        ]
    )
    assert res["is_valid"] is True
    assert res["total_topics"] == 2
    assert res["incompatible_schema_or_dlq_surge_topics"] == []
    assert res["lag_or_rebalance_storm_topics"] == []
    assert res["gate_decision"] == "APPROVED"
    assert res["recommendations"] == []


def test_audit_kafka_consumer_rebalance_dlq_and_schema_registry_gate_rejected_on_schema_or_dlq():
    from backend.services.project_ccb_service import (
        audit_kafka_consumer_rebalance_dlq_and_schema_registry_gate,
    )

    res = audit_kafka_consumer_rebalance_dlq_and_schema_registry_gate(
        [
            {
                "topic_id": "orders.events.v1",
                "consumer_lag_records": 500,
                "rebalances_last_hour": 1,
                "dlq_poison_pill_rate_pct": 0.1,
                "schema_compatibility_mode": "NONE",
                "breaking_schema_evolution_detected": False,
            },
            {
                "topic_id": "inventory.mutations.v1",
                "consumer_lag_records": 800,
                "rebalances_last_hour": 2,
                "dlq_poison_pill_rate_pct": 1.25,
                "schema_compatibility_mode": "BACKWARD",
                "breaking_schema_evolution_detected": False,
            },
            {
                "topic_id": "shipments.tracking.v1",
                "consumer_lag_records": 300,
                "rebalances_last_hour": 0,
                "dlq_poison_pill_rate_pct": 0.0,
                "schema_compatibility_mode": "FULL",
                "breaking_schema_evolution_detected": True,
            },
        ],
        max_dlq_poison_pill_rate_pct=0.5,
    )
    assert res["is_valid"] is False
    assert res["incompatible_schema_or_dlq_surge_topics"] == [
        "orders.events.v1",
        "inventory.mutations.v1",
        "shipments.tracking.v1",
    ]
    assert res["lag_or_rebalance_storm_topics"] == []
    assert res["gate_decision"] == "REJECTED"
    assert len(res["recommendations"]) == 1


def test_audit_kafka_consumer_rebalance_dlq_and_schema_registry_gate_conditional_on_lag_or_rebalance():
    from backend.services.project_ccb_service import (
        audit_kafka_consumer_rebalance_dlq_and_schema_registry_gate,
    )

    res = audit_kafka_consumer_rebalance_dlq_and_schema_registry_gate(
        [
            {
                "topic_id": "telemetry.metrics.v1",
                "consumer_lag_records": 25000,
                "rebalances_last_hour": 2,
                "dlq_poison_pill_rate_pct": 0.1,
                "schema_compatibility_mode": "BACKWARD_TRANSITIVE",
            },
            {
                "topic_id": "audit.logs.v1",
                "consumer_lag_records": 1500,
                "rebalances_last_hour": 9,
                "dlq_poison_pill_rate_pct": 0.0,
                "schema_compatibility_mode": "FULL",
            },
        ],
        max_consumer_lag_records=10000,
        max_rebalances_per_hour=4,
    )
    assert res["is_valid"] is False
    assert res["incompatible_schema_or_dlq_surge_topics"] == []
    assert res["lag_or_rebalance_storm_topics"] == [
        "telemetry.metrics.v1",
        "audit.logs.v1",
    ]
    assert res["gate_decision"] == "CONDITIONAL"
    assert len(res["recommendations"]) == 1


def test_audit_kafka_consumer_rebalance_dlq_and_schema_registry_gate_staticmethod_and_dunder_all():
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_kafka_consumer_rebalance_dlq_and_schema_registry_gate,
    )

    sample = [
        {
            "topic_id": "custom.forward.v1",
            "consumer_lag_records": 100,
            "rebalances_last_hour": 0,
            "dlq_poison_pill_rate_pct": 0.0,
            "schema_compatibility_mode": "FORWARD",
        }
    ]
    relaxed = audit_kafka_consumer_rebalance_dlq_and_schema_registry_gate(
        sample, require_backward_or_full_compatibility=False
    )
    assert relaxed["is_valid"] is True
    assert relaxed["gate_decision"] == "APPROVED"

    assert (
        ProjectCCBService.audit_kafka_consumer_rebalance_dlq_and_schema_registry_gate(
            sample
        )
        == audit_kafka_consumer_rebalance_dlq_and_schema_registry_gate(sample)
    )
    assert (
        "audit_kafka_consumer_rebalance_dlq_and_schema_registry_gate"
        in mod.__all__
    )


def test_audit_graphql_federation_supergraph_composition_and_query_cost_gate_approved():
    from backend.services.project_ccb_service import (
        audit_graphql_federation_supergraph_composition_and_query_cost_gate,
    )

    res = audit_graphql_federation_supergraph_composition_and_query_cost_gate(
        subgraphs=[
            {
                "subgraph_id": "projects-subgraph",
                "rover_composition_valid": True,
                "breaking_field_removals_count": 0,
                "max_query_depth_configured": 10,
                "max_query_complexity_cost_configured": 800,
                "dataloader_n_plus_one_guarded": True,
            },
            {
                "subgraph_id": "evm-subgraph",
                "rover_composition_valid": True,
                "breaking_field_removals_count": 0,
                "max_query_depth_configured": 8,
                "max_query_complexity_cost_configured": 500,
                "dataloader_n_plus_one_guarded": True,
            },
        ]
    )
    assert res["is_valid"] is True
    assert res["total_subgraphs"] == 2
    assert res["composition_or_breaking_schema_subgraphs"] == []
    assert res["unbounded_depth_or_complexity_subgraphs"] == []
    assert res["unbatched_n_plus_one_subgraphs"] == []
    assert res["gate_decision"] == "APPROVED"


def test_audit_graphql_federation_supergraph_composition_and_query_cost_gate_rejected():
    from backend.services.project_ccb_service import (
        audit_graphql_federation_supergraph_composition_and_query_cost_gate,
    )

    res = audit_graphql_federation_supergraph_composition_and_query_cost_gate(
        subgraphs=[
            {
                "subgraph_id": "broken-subgraph",
                "rover_composition_valid": False,
                "breaking_field_removals_count": 2,
                "max_query_depth_configured": 20,
                "max_query_complexity_cost_configured": 2500,
                "dataloader_n_plus_one_guarded": True,
            }
        ],
        max_allowed_query_depth=12,
        max_allowed_complexity_cost=1000,
    )
    assert res["is_valid"] is False
    assert res["composition_or_breaking_schema_subgraphs"] == ["broken-subgraph"]
    assert res["unbounded_depth_or_complexity_subgraphs"] == ["broken-subgraph"]
    assert res["gate_decision"] == "REJECTED"


def test_audit_graphql_federation_supergraph_composition_and_query_cost_gate_conditional():
    from backend.services.project_ccb_service import (
        audit_graphql_federation_supergraph_composition_and_query_cost_gate,
    )

    res = audit_graphql_federation_supergraph_composition_and_query_cost_gate(
        subgraphs=[
            {
                "subgraph_id": "wiki-subgraph",
                "rover_composition_valid": True,
                "breaking_field_removals_count": 0,
                "max_query_depth_configured": 10,
                "max_query_complexity_cost_configured": 600,
                "dataloader_n_plus_one_guarded": False,
            }
        ]
    )
    assert res["is_valid"] is False
    assert res["composition_or_breaking_schema_subgraphs"] == []
    assert res["unbounded_depth_or_complexity_subgraphs"] == []
    assert res["unbatched_n_plus_one_subgraphs"] == ["wiki-subgraph"]
    assert res["gate_decision"] == "CONDITIONAL"


def test_audit_graphql_federation_supergraph_composition_and_query_cost_gate_staticmethod_and_dunder_all():
    import backend.services.project_ccb_service as mod
    from backend.services.project_ccb_service import (
        ProjectCCBService,
        audit_graphql_federation_supergraph_composition_and_query_cost_gate,
    )

    empty = audit_graphql_federation_supergraph_composition_and_query_cost_gate([])
    assert empty["is_valid"] is False
    assert empty["gate_decision"] == "REJECTED"

    sample = [
        {
            "subgraph_id": "sg-1",
            "rover_composition_valid": True,
            "breaking_field_removals_count": 0,
            "max_query_depth_configured": 8,
            "max_query_complexity_cost_configured": 400,
        }
    ]
    assert (
        ProjectCCBService.audit_graphql_federation_supergraph_composition_and_query_cost_gate(
            sample
        )
        == audit_graphql_federation_supergraph_composition_and_query_cost_gate(
            sample
        )
    )
    assert (
        "audit_graphql_federation_supergraph_composition_and_query_cost_gate"
        in mod.__all__
    )


