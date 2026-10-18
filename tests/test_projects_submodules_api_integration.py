"""Suite E2E de Integración HTTP API y Aislamiento Multi-Tenant (Axioma 3)
para los 6 submódulos conectados de Proyectos.

Verifica vía TestClient contra los endpoints HTTP reales (/api/projects/...):
a) Suministros (Supplies → Expenses → EVM AC) con soft-delete.
b) Control de Tiempo (TimeLogs → actual_hours → roll-up EDT).
c) Línea Base (Baselines → EVM & Curva S).
d) Carga de Trabajo (Workload ponderado sobre tareas hoja).
e) Ruta Crítica (CPM Dependencies con lag_days).
f) Automatizaciones en Tiempo Real (regla activa + disparo al mutar tarea).
g) Aislamiento Multi-Tenant (Axioma 3): 404/403 cross-sede en los 6 submódulos.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest

from backend import models as models
from backend.models_projects import ProjectExpense
from tests.conftest import auth_headers, seed_admin, seed_user_with_role
from tests.factories_projects import (
    create_subtask_factory,
    create_task_factory,
)

pytestmark = pytest.mark.django_db if False else pytest.mark.usefixtures("db_session")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_project(client, headers, db_session, *, title="Proyecto E2E Submódulos Pro", budget=100000.0):
    """Crea un proyecto real vía HTTP POST /api/projects (201)."""
    resp = client.post(
        "/api/projects",
        json={"title": title, "status": "active", "budget_allocated": budget},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    proj = db_session.query(models.Project).filter(models.Project.id == data["id"]).first()
    assert proj is not None
    return proj


def _make_task(db_session, project_id, *, title="Tarea hoja", estimated_hours=10.0, **overrides):
    defaults = dict(
        title=title,
        estimated_hours=estimated_hours,
        status="todo",
        physical_progress_pct=0.0,
    )
    defaults.update(overrides)
    task = create_task_factory(db_session, project_id, **defaults)
    db_session.refresh(task)
    return task


def _seed_sede_b_user(db_session, email="user-sede-b@example.com"):
    """Usuario autenticado de la Sede B (no admin) para Axioma 3."""
    user, persona, sede_b = seed_user_with_role(
        db_session,
        role_name="ProjectsReaderSedeB",
        email=email,
        sede_id=uuid.uuid4(),  # Sede B explícita: Axioma 3 exige sedes distintas
        permisos={"projects:read": "allow", "projects:edit": "allow", "default": "allow"},
    )
    return user, persona, sede_b


# ─────────────────────────────────────────────────────────────────────────────
# a) Suministros (Supplies → Expenses → EVM AC) + soft-delete
# ─────────────────────────────────────────────────────────────────────────────


def test_supplies_crud_auto_expense_and_evm_ac(client, db_session):
    """POST/PATCH/DELETE de suministros crea gasto automático (is_auto_generated),
    actualiza task.actual_cost y se refleja en AC del GET /evm; DELETE hace soft-delete."""
    seed_admin(db_session, email="supplies-admin@example.com")
    headers = auth_headers(client, email="supplies-admin@example.com")
    project = _make_project(client, headers, db_session, title="E2E Suministros Pro")
    task = _make_task(db_session, project.id, title="Tarea con suministro", estimated_hours=20.0)  # EV = 100k

    # ── POST: crea el suministro con unit_cost y qty → gasto auto ──
    resp = client.post(
        f"/api/projects/{project.id}/tasks/{task.id}/supplies",
        json={"item_name": "Servidor Dell", "quantity": 2, "unit_cost": 1250.0, "status": "paid"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    supply = resp.json()
    supply_id = supply["id"]

    # El gasto automático se linkeó (expense_id) y es is_auto_generated=True
    assert supply.get("expense_id"), "El suministro debe crear un ProjectExpense automático"
    expense = db_session.query(ProjectExpense).filter(ProjectExpense.id == supply["expense_id"]).first()
    assert expense is not None
    assert str(expense.is_auto_generated).lower() in ("true", "1") or expense.is_auto_generated, \
        "El gasto automático debe marcarse is_auto_generated=True"
    expense_id = expense.id
    assert float(expense.amount) == pytest.approx(2500.0), "total_cost = unit_cost × quantity"

    # task.actual_cost refleja el suministro total (activo)
    db_session.refresh(task)
    assert float(getattr(task, "actual_cost", 0.0) or 0.0) == pytest.approx(2500.0), \
        "task.actual_cost debe reflejar el gasto activo del suministro"

    # El AC del EVM del proyecto se refleja vía roll-up de budget_spent
    r_evm = client.get(f"/api/projects/{project.id}/evm", headers=headers)
    assert r_evm.status_code == 200, r_evm.text
    evm = r_evm.json()
    assert float(evm["ac"]) == pytest.approx(2500.0), "AC del EVM debe reflejar el gasto autosumado"

    # ── PATCH: actualizar unit_cost del suministro propaga al gasto ──
    resp_patch = client.patch(
        f"/api/projects/{project.id}/tasks/{task.id}/supplies/{supply_id}",
        json={"unit_cost": 2000.0},
        headers=headers,
    )
    assert resp_patch.status_code == 200, resp_patch.text
    db_session.rollback()
    db_session.expire_all()
    db_session.refresh(task)
    assert float(getattr(task, "actual_cost", 0.0) or 0.0) == pytest.approx(4000.0), \
        "PATCH de unit_cost debe recalcular task.actual_cost (2000×2)"

    # ── DELETE: soft-delete del suministro (expense marcada deleted_at, actual_cost = 0) ──
    resp_del = client.delete(
        f"/api/projects/{project.id}/tasks/{task.id}/supplies/{supply_id}",
        headers=headers,
    )
    assert resp_del.status_code in (200, 204), resp_del.text

    db_session.expire_all()
    task_db = db_session.query(type(task)).filter(type(task).id == task.id).first()
    assert float(getattr(task_db, "actual_cost", 0.0) or 0.0) == pytest.approx(0.0), \
        "Tras el DELETE del suministro, task.actual_cost vuelve a 0"

    # GET de la lista ya no incluye el suministro (soft-delete, sin hard-delete)
    resp_list = client.get(f"/api/projects/{project.id}/tasks/{task.id}/supplies", headers=headers)
    assert resp_list.status_code == 200
    assert all(s["id"] != supply_id for s in resp_list.json()), "El suministro eliminado no debe listarse"


# ─────────────────────────────────────────────────────────────────────────────
# b) Control de Tiempo (TimeLogs → actual_hours → roll-up EDT)
# ─────────────────────────────────────────────────────────────────────────────


def test_time_logs_update_actual_hours_and_rollup(client, db_session):
    """POST de time-logs actualiza task.actual_hours y hace roll-up hacia el componente EDT/proyecto."""
    seed_admin(db_session, email="time-admin@example.com")
    headers = auth_headers(client, email="time-admin@example.com")
    project = _make_project(client, headers, db_session, title="E2E TimeLogs Pro")

    parent = _make_task(db_session, project.id, title="EDT Padre Timing", estimated_hours=10.0)
    child = create_subtask_factory(
        db_session, parent.id, project.id, title="Subtarea Timing", estimated_hours=8.0
    )
    db_session.refresh(child)

    # POST de un time-log de 3h sobre la subtarea
    resp = client.post(
        f"/api/projects/{project.id}/time-logs",
        json={"task_id": str(child.id), "hours": 3.0, "description": "Ejecución			                campo"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    log = resp.json()
    assert float(log["hours"]) == 3.0

    # task.actual_hours de la subtarea = 3.0
    db_session.expire_all()
    child_db = db_session.query(type(child)).filter(type(child).id == child.id).first()
    assert float(getattr(child_db, "actual_hours", 0.0) or 0.0) == pytest.approx(3.0)

    # Roll-up continuo: la tarea padre EDT suma 3.0h desde sus hijos
    parent_db = db_session.query(type(parent)).filter(type(parent).id == parent.id).first()
    assert float(getattr(parent_db, "actual_hours", 0.0) or 0.0) == pytest.approx(3.0), \
        "El roll-up EDT debe tributar actual_hours de subtareas hacia la tarea padre"

    # El endpoint GET /time-logs lista el registro creado
    r_list = client.get(f"/api/projects/{project.id}/time-logs", headers=headers)
    assert r_list.status_code == 200
    assert any(str(l["id"]) == str(log["id"]) for l in r_list.json())

    # Segundo registro y roll-up a 5.0
    resp2 = client.post(
        f"/api/projects/{project.id}/time-logs",
        json={"task_id": str(child.id), "hours": 2.0},
        headers=headers,
    )
    assert resp2.status_code == 201, resp2.text
    db_session.expire_all()
    parent_db2 = db_session.query(type(parent)).filter(type(parent).id == parent.id).first()
    assert float(getattr(parent_db2, "actual_hours", 0.0) or 0.0) == pytest.approx(5.0)


# ─────────────────────────────────────────────────────────────────────────────
# c) Línea Base (Baselines → EVM & Curva S)
# ─────────────────────────────────────────────────────────────────────────────


def test_baseline_snapshot_reflects_in_evm_and_curve_s(client, db_session):
    """POST de snapshot de línea base expone baseline_* en /evm y serie baseline_pv en /evm/curve-s."""
    seed_admin(db_session, email="baseline-admin@example.com")
    headers = auth_headers(client, email="baseline-admin@example.com")
    project = _make_project(client, headers, db_session, title="E2E Baseline Pro", budget=50000.0)
    _make_task(db_session, project.id, title="Tarea Baseline", estimated_hours=10.0)

    # ── POST de la línea base (POST /{id}/baseline y /{id}/baselines comparten handler) ──
    resp = client.post(
        f"/api/projects/{project.id}/baselines",
        json={"name": "Línea Base 2026-Q4"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    baseline = resp.json()
    assert baseline["name"] == "Línea Base 2026-Q4"
    assert baseline["project_id"] == str(project.id)

    # Reflexión en GET /evm: baseline_id / baseline_name / baseline_bac / varianzas
    r_evm = client.get(f"/api/projects/{project.id}/evm", headers=headers)
    assert r_evm.status_code == 200
    evm = r_evm.json()
    assert evm.get("baseline_id") == str(baseline["id"]), "El EVM debe reportar el baseline activo"
    assert evm.get("baseline_name") == "Línea Base 2026-Q4"
    assert float(evm.get("baseline_bac", 0.0)) == pytest.approx(50000.0), \
        "baseline_bac debe congelar el BAC al momento del snapshot"
    assert "baseline_variance_cost" in evm
    assert "baseline_variance_schedule" in evm

    # Serie baseline_pv en GET /evm/curve-s
    r_curve = client.get(f"/api/projects/{project.id}/evm/curve-s?points=8", headers=headers)
    assert r_curve.status_code == 200
    curve = r_curve.json()
    points = curve["points"]
    assert len(points) == 8
    baseline_series = [p.get("baseline_pv") for p in points]
    assert all(v is not None for v in baseline_series), "Cada punto de la curva debe traer baseline_pv"
    assert baseline_series[0] == pytest.approx(0.0), "El primer punto del PV planificado es 0"
    assert baseline_series[-1] == pytest.approx(50000.0), "El último punto del PV planificado alcanza el BAC"

    # Hitorial de líneas base: GET /{id}/baselines lista la snapshot
    r_baselines = client.get(f"/api/projects/{project.id}/baselines", headers=headers)
    assert r_baselines.status_code == 200
    assert any(b["id"] == baseline["id"] for b in r_baselines.json())


# ─────────────────────────────────────────────────────────────────────────────
# d) Carga de Trabajo (Workload ponderado sobre tareas hoja)
# ─────────────────────────────────────────────────────────────────────────────


def test_workload_ponderacion_tareas_hoja(client, db_session):
    """GET /workload suma estimated/actual hours ponderadas solo sobre tareas hoja (sin doble conteo EDT)."""
    seed_admin(db_session, email="workload-admin@example.com")
    headers = auth_headers(client, email="workload-admin@example.com")
    project = _make_project(client, headers, db_session, title="E2E Workload Pro")

    parent = _make_task(
        db_session, project.id, title="EDT Padre WL", estimated_hours=1000.0, assignee_id=project.owner_id
    )
    child1 = create_subtask_factory(
        db_session, parent.id, project.id, title="Hijo WL 1", estimated_hours=10.0, assignee_id=project.owner_id
    )
    child2 = create_subtask_factory(
        db_session, parent.id, project.id, title="Hijo WL 2", estimated_hours=10.0, assignee_id=project.owner_id
    )
    db_session.refresh(child1)
    db_session.refresh(child2)

    # Registrar 2h en child1 vía HTTP
    resp = client.post(
        f"/api/projects/{project.id}/time-logs",
        json={"task_id": str(child1.id), "hours": 2.0},
        headers=headers,
    )
    assert resp.status_code == 201

    r_workload = client.get(f"/api/projects/{project.id}/workload", headers=headers)
    assert r_workload.status_code == 200, r_workload.text
    workload = r_workload.json()

    # Ponderación: el padre EDT (1000h) queda excluido por tener hijos; solo hojas 10+10
    total_est = float(workload["total_estimated_hours"])
    total_act = float(workload["total_actual_hours"])
    assert total_est == pytest.approx(20.0), (
        f"total_estimated_hours debe ponderar solo tareas hoja (body={r_workload.text[:600]})"
    )
    assert total_act == pytest.approx(2.0), "total_actual_hours debe reflejar los time-logs reales"
    if "hours_utilization_pct" in workload and total_est > 0:
        assert float(workload["hours_utilization_pct"]) == pytest.approx((2.0 / 20.0) * 100.0, abs=0.1)


# ─────────────────────────────────────────────────────────────────────────────
# e) Ruta Crítica (CPM Dependencies)
# ─────────────────────────────────────────────────────────────────────────────


def test_critical_path_propagation_with_dependencies(client, db_session):
    """POST de dependencias con lag_days propaga la ruta crítica (critical-path endpoint)."""
    seed_admin(db_session, email="cpm-admin@example.com")
    headers = auth_headers(client, email="cpm-admin@example.com")
    project = _make_project(client, headers, db_session, title="E2E CPM Pro")

    t1 = _make_task(db_session, project.id, title="Tarea CPM A", estimated_hours=5.0)
    t2 = _make_task(db_session, project.id, title="Tarea CPM B", estimated_hours=5.0)

    # POST de la dependencia FS con lag de 2 días
    resp = client.post(
        f"/api/projects/{project.id}/dependencies",
        json={"predecessor_id": str(t1.id), "successor_id": str(t2.id), "dependency_type": "FS", "lag_days": 2},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    dep = resp.json()
    assert dep["dependency_type"] == "FS"
    assert int(dep["lag_days"]) == 2
    assert dep["predecessor_id"] == str(t1.id)
    assert dep["successor_id"] == str(t2.id)

    # La lista de dependencias la incluye
    r_deps = client.get(f"/api/projects/{project.id}/dependencies", headers=headers)
    assert r_deps.status_code == 200
    assert any(d["id"] == dep["id"] for d in r_deps.json())

    # Ruta crítica calculada: t2 hereda el early start de t1 + duración de t1 + lag 2
    r_cpm = client.get(f"/api/projects/{project.id}/critical-path", headers=headers)
    assert r_cpm.status_code == 200, r_cpm.text
    cpm = r_cpm.json()
    items = cpm["tasks"] if isinstance(cpm, dict) and "tasks" in cpm else cpm
    by_id = {str(i["task_id"]): i for i in items}
    assert str(t1.id) in by_id and str(t2.id) in by_id
    t2_item = by_id[str(t2.id)]
    early_start_t2 = t2_item["early_start"]
    t1_item = by_id[str(t1.id)]
    assert early_start_t2 == pytest.approx(t1_item["early_finish"] + 2), (
        "Con FS + lag_days=2, el inicio temprano del sucesor = fin temprano del predecesor + lag"
    )


# ─────────────────────────────────────────────────────────────────────────────
# f) Automatizaciones en Tiempo Real
# ─────────────────────────────────────────────────────────────────────────────


def test_project_automations_realtime_trigger(client, db_session):
    """POST de regla activa (task_completed/notify_assignee) y disparo automático al completar la tarea."""
    seed_admin(db_session, email="auto-admin@example.com")
    headers = auth_headers(client, email="auto-admin@example.com")
    project = _make_project(client, headers, db_session, title="E2E Automations Pro")
    task = _make_task(db_session, project.id, title="Tarea Auto", estimated_hours=4.0)

    # POST de la regla activa
    resp = client.post(
        f"/api/projects/{project.id}/automations",
        json={
            "name": "Notificar al completar tarea",
            "trigger_event": "task_completed",
            "action_type": "notify_assignee",
            "condition_data": {},
            "action_data": {"message": "Tarea lista"},
            "is_active": True,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    rule = resp.json()
    assert rule["is_active"] is True
    assert int(rule["execution_count"]) == 0

    # Mutación de la tarea vía HTTP → status completed → dispara la regla
    r_task = client.patch(
        f"/api/projects/{project.id}/tasks/{task.id}",
        json={"status": "completed"},
        headers=headers,
    )
    assert r_task.status_code == 200, r_task.text

    # La regla incrementa execution_count y last_triggered_at
    r_rule = client.get(f"/api/projects/{project.id}/automations/{rule['id']}", headers=headers)
    assert r_rule.status_code == 200
    rule_after = r_rule.json()
    assert int(rule_after["execution_count"]) >= 1, "La regla debe incrementar execution_count al disparar"
    assert rule_after.get("last_triggered_at") is not None


# ─────────────────────────────────────────────────────────────────────────────
# g) Aislamiento Multi-Tenant (Axioma 3): cross-sede → 404/403
# ─────────────────────────────────────────────────────────────────────────────


def test_multitentant_isolation_all_submodules(client, db_session):
    """El usuario de la Sede B recibe 404/403 al leer/mutar recursos de un proyecto de la Sede A."""
    seed_admin(db_session, email="isolation-admin@example.com")
    headers_a = auth_headers(client, email="isolation-admin@example.com")

    # Proyecto + data de la Sede A (admin de ahí)
    project = _make_project(client, headers_a, db_session, title="Proyecto Sede A Aislado")
    task = _make_task(db_session, project.id, title="Tarea Sede A", estimated_hours=8.0)

    sup_resp = client.post(
        f"/api/projects/{project.id}/tasks/{task.id}/supplies",
        json={"item_name": "Suministro Sede A", "quantity": 1, "unit_cost": 100.0},
        headers=headers_a,
    )
    assert sup_resp.status_code == 201, sup_resp.text
    supply_id = sup_resp.json()["id"]

    bl_resp = client.post(
        f"/api/projects/{project.id}/baselines",
        json={"name": "LB Sede A"},
        headers=headers_a,
    )
    assert bl_resp.status_code == 201, bl_resp.text

    # Usuario real de la Sede B (sede distinta explícita)
    user_b, _, _ = _seed_sede_b_user(db_session, email="intruso-sede-b@example.com")
    headers_b = auth_headers(client, email="intruso-sede-b@example.com")
    assert str(user_b.sede_id) != str(project.sede_id), "El setup debe ser cross-sede real"

    def _isolated(path, method="get", **kw):
        fn = getattr(client, method)
        return fn(f"/api/projects/{path}", headers=headers_b, **kw)

    # ── EVM (lectura) ──
    r_evm = _isolated(f"{project.id}/evm")
    assert r_evm.status_code in (403, 404), f"EVM cross-sede: {r_evm.status_code} {r_evm.text}"

    # ── Supplies (lectura + mutación) ──
    r_sup = _isolated(f"{project.id}/tasks/{task.id}/supplies")
    assert r_sup.status_code in (403, 404), f"Supplies GET cross-sede: {r_sup.status_code}"
    r_sup_patch = _isolated(
        f"{project.id}/tasks/{task.id}/supplies/{supply_id}", method="patch", json={"unit_cost": 999.0}
    )
    assert r_sup_patch.status_code in (403, 404), f"Supplies PATCH cross-sede: {r_sup_patch.status_code}"

    # ── Time-logs (lectura + mutación) ──
    r_tl = _isolated(f"{project.id}/time-logs")
    assert r_tl.status_code in (403, 404), f"Time-logs GET cross-sede: {r_tl.status_code}"
    r_tl_post = _isolated(
        f"{project.id}/time-logs", method="post", json={"task_id": str(task.id), "hours": 1.0}
    )
    assert r_tl_post.status_code in (403, 404), f"Time-logs POST cross-sede: {r_tl_post.status_code}"

    # ── Baselines (lectura + mutación) ──
    r_bl = _isolated(f"{project.id}/baselines")
    assert r_bl.status_code in (403, 404), f"Baselines GET cross-sede: {r_bl.status_code}"
    r_bl_post = _isolated(f"{project.id}/baselines", method="post", json={"name": "LB Intrusa"})
    assert r_bl_post.status_code in (403, 404), f"Baselines POST cross-sede: {r_bl_post.status_code}"

    # ── Workload (lectura) ──
    r_wl = _isolated(f"{project.id}/workload")
    assert r_wl.status_code in (403, 404), f"Workload cross-sede: {r_wl.status_code}"

    # ── Automatizaciones (lectura + mutación) ──
    r_auto = _isolated(f"{project.id}/automations")
    assert r_auto.status_code in (403, 404), f"Automations GET cross-sede: {r_auto.status_code}"
    r_auto_post = _isolated(
        f"{project.id}/automations",
        method="post",
        json={
            "name": "Regla Intrusa",
            "trigger_event": "task_completed",
            "action_type": "notify_assignee",
            "is_active": True,
        },
    )
    assert r_auto_post.status_code in (403, 404), f"Automations POST cross-sede: {r_auto_post.status_code}"

    # El guard inicial del proyecto también aísla la lectura del propio proyecto
    r_proj = _isolated(str(project.id))
    assert r_proj.status_code in (403, 404), f"Proyecto cross-sede: {r_proj.status_code}"
