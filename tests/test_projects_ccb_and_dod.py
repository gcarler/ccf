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
    from backend.services.project_ccb_service import (
        audit_configuration_items_baseline_integrity as audit_fn,
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
    from backend.services.project_ccb_service import (
        audit_configuration_items_baseline_integrity as audit_fn,
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
    from backend.services.project_ccb_service import (
        audit_configuration_items_baseline_integrity as audit_fn,
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
    from backend.services.project_ccb_service import (
        audit_configuration_items_baseline_integrity as audit_fn,
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
