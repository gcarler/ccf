from __future__ import annotations

import pytest

from scripts.seeding.seed_projects_demo import (
    DEMO_PROJECTS,
    seed_projects_demo,
    validate_seed_target,
)
from tests.conftest import auth_headers, seed_admin


@pytest.mark.parametrize("database_name", ["ccf_test", "projects_e2e_20261004", "ccf_quality_run_42"])
def test_projects_demo_reset_requires_exact_confirmation_on_isolated_database(database_name):
    database_url = f"postgresql://tester:secret@127.0.0.1:5432/{database_name}"

    assert validate_seed_target(database_url, database_name, reset=True) == database_name


def test_projects_demo_seed_rejects_missing_or_mismatched_database_confirmation():
    database_url = "postgresql://tester:secret@127.0.0.1:5432/ccf_projects_e2e"

    with pytest.raises(RuntimeError, match="PROJECTS_DEMO_TARGET_DATABASE"):
        validate_seed_target(database_url, None, reset=True)
    with pytest.raises(RuntimeError, match="PROJECTS_DEMO_TARGET_DATABASE"):
        validate_seed_target(database_url, "another_database", reset=True)


def test_projects_demo_reset_rejects_confirmed_non_test_database():
    database_url = "postgresql://tester:secret@127.0.0.1:5432/ccf_recovery_20260823"

    with pytest.raises(RuntimeError, match="_e2e, _test o _quality"):
        validate_seed_target(database_url, "ccf_recovery_20260823", reset=True)


def test_projects_demo_non_reset_seed_allows_explicitly_confirmed_local_database():
    database_url = "postgresql://tester:secret@127.0.0.1:5432/ccf_dev"

    assert validate_seed_target(database_url, "ccf_dev", reset=False) == "ccf_dev"


def test_projects_demo_seed_roundtrip(client, db_session):
    user, persona, sede = seed_admin(db_session)
    created = seed_projects_demo(db_session, actor_email=user.email, reset=True)

    assert len(created) == 3

    headers = auth_headers(client)

    projects_resp = client.get("/api/projects", headers=headers)
    assert projects_resp.status_code == 200
    projects = projects_resp.json()
    assert len(projects) == 3

    projects_by_title = {row["title"]: row for row in projects}
    assert set(projects_by_title) == {item["title"] for item in DEMO_PROJECTS}

    tasks_resp = client.get("/api/projects/tasks", headers=headers)
    assert tasks_resp.status_code == 200
    assert len(tasks_resp.json()) == 15

    activities_resp = client.get("/api/projects/activities?limit=50", headers=headers)
    assert activities_resp.status_code == 200
    assert len(activities_resp.json()) == 15

    for project_def in DEMO_PROJECTS:
        project = projects_by_title[project_def["title"]]
        detail_resp = client.get(f"/api/projects/{project['id']}", headers=headers)
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["title"] == project_def["title"]
        assert len(detail["tasks"]) == 5

        project_activities_resp = client.get(
            f"/api/projects/activities?project_id={project['id']}&limit=10",
            headers=headers,
        )
        assert project_activities_resp.status_code == 200
        project_activities = project_activities_resp.json()
        assert len(project_activities) == 5
        assert {row["project_id"] for row in project_activities} == {project["id"]}

    summary_resp = client.get("/api/projects/summary", headers=headers)
    assert summary_resp.status_code == 200
    summary_rows = summary_resp.json()
    assert sum(row["total_projects"] for row in summary_rows) == 3
    assert sum(row["total_tasks"] for row in summary_rows) == 15


# ── audit_demo_seed_blueprint (pure helper) ──────────────────────────────────


def test_audit_demo_seed_blueprint_default_spec():
    """DEMO_PROJECTS por defecto: 3 proyectos, títulos únicos y diversidad de estados."""
    from scripts.seeding.seed_projects_demo import ACTIVITY_TYPES, audit_demo_seed_blueprint

    audit = audit_demo_seed_blueprint()

    assert audit == {
        "project_count": 3,
        "expected_tasks_per_project": 5,
        "expected_phases_per_project": 4,
        "expected_activities_per_project": len(ACTIVITY_TYPES),
        "total_expected_tasks": 15,
        "total_expected_phases": 12,
        "total_expected_activities": 3 * len(ACTIVITY_TYPES),
        "status_distribution": {"active": 1, "on_hold": 1, "planning": 1},
        "has_unique_titles": True,
        "has_lifecycle_diversity": True,
        "is_blueprint_valid": True,
    }
    assert list(audit["status_distribution"].items()) == [
        ("active", 1),
        ("on_hold", 1),
        ("planning", 1),
    ]


def test_audit_demo_seed_blueprint_detects_duplicate_titles():
    """Títulos duplicados (o vacíos tras limpiar) invalidan el blueprint."""
    from scripts.seeding.seed_projects_demo import audit_demo_seed_blueprint

    spec = [
        {"title": "Mismo Titulo", "status": "active"},
        {"title": "Mismo Titulo", "status": "planning"},
    ]
    audit = audit_demo_seed_blueprint(spec)
    assert audit["project_count"] == 2
    assert audit["has_unique_titles"] is False
    assert audit["has_lifecycle_diversity"] is True
    assert audit["is_blueprint_valid"] is False


def test_audit_demo_seed_blueprint_detects_single_status_lack_of_diversity():
    """Un único estado repetido → sin diversidad de ciclo de vida."""
    from scripts.seeding.seed_projects_demo import audit_demo_seed_blueprint

    spec = [
        {"title": "Proyecto A", "status": "active"},
        {"title": "Proyecto B", "status": "active"},
        {"title": "Proyecto C", "status": "  active  "},  # espacios se limpian
    ]
    audit = audit_demo_seed_blueprint(spec)
    assert audit["status_distribution"] == {"active": 3}
    assert audit["has_unique_titles"] is True
    assert audit["has_lifecycle_diversity"] is False
    assert audit["is_blueprint_valid"] is False


def test_audit_demo_seed_blueprint_rejects_empty_spec():
    """Especificación vacía → 0 proyectos y False en validaciones."""
    from scripts.seeding.seed_projects_demo import ACTIVITY_TYPES, audit_demo_seed_blueprint

    audit = audit_demo_seed_blueprint([])

    assert audit == {
        "project_count": 0,
        "expected_tasks_per_project": 5,
        "expected_phases_per_project": 4,
        "expected_activities_per_project": len(ACTIVITY_TYPES),
        "total_expected_tasks": 0,
        "total_expected_phases": 0,
        "total_expected_activities": 0,
        "status_distribution": {},
        "has_unique_titles": False,
        "has_lifecycle_diversity": False,
        "is_blueprint_valid": False,
    }


# ── summarize_demo_seed_budget_allocation (PMBOK §7.3, pure helper) ───────


def test_budget_allocation_default_spec_diversified():
    """DEMO_PROJECTS con budgets (150k/90k/60k) → 'diversified_funded'."""
    from scripts.seeding.seed_projects_demo import summarize_demo_seed_budget_allocation

    result = summarize_demo_seed_budget_allocation()

    assert result == {
        "total_projects": 3,
        "funded_projects_count": 3,
        "unfunded_projects_count": 0,
        "total_portfolio_budget": 300000.0,
        "avg_project_budget": 100000.0,
        "max_project_budget": 150000.0,
        "max_budget_share_pct": 50.0,
        "allocation_status": "diversified_funded",
    }


def test_budget_allocation_over_concentrated():
    """>= 2 proyectos con >= 75% del presupuesto en uno → 'over_concentrated'."""
    from scripts.seeding.seed_projects_demo import summarize_demo_seed_budget_allocation

    projects = [
        {"budget": 90000.0},
        {"bac": 6000.0},   # cae en la variante 'bac'
        {},                # sin presupuesto
    ]
    result = summarize_demo_seed_budget_allocation(projects)

    assert result["total_projects"] == 3
    assert result["funded_projects_count"] == 2
    assert result["unfunded_projects_count"] == 1
    assert result["total_portfolio_budget"] == 96000.0
    assert result["max_project_budget"] == 90000.0
    assert result["max_budget_share_pct"] == round(90000 / 96000 * 100.0, 2)
    assert result["allocation_status"] == "over_concentrated"

    # borde: exactamente 75% también concentra
    edge = summarize_demo_seed_budget_allocation([{"budget": 3}, {"budget": 1}])
    assert edge["max_budget_share_pct"] == 75.0
    assert edge["allocation_status"] == "over_concentrated"


def test_budget_allocation_partially_funded():
    """Alguno con budget 0 sin llegar a 75% de concentración → 'partially_funded'."""
    from scripts.seeding.seed_projects_demo import summarize_demo_seed_budget_allocation

    projects = [
        {"budget": 50000.0},
        {"budget": 30000.0},
        {"budget": 0.0},
    ]
    result = summarize_demo_seed_budget_allocation(projects)

    assert result["total_projects"] == 3
    assert result["funded_projects_count"] == 2
    assert result["unfunded_projects_count"] == 1
    assert result["total_portfolio_budget"] == 80000.0
    assert result["avg_project_budget"] == round(80000 / 3, 2)
    assert result["max_budget_share_pct"] == 62.5
    assert result["allocation_status"] == "partially_funded"


def test_budget_allocation_empty_and_unfunded():
    """Lista vacía → 'empty_seed'; presupuestos en 0 → 'unfunded_portfolio'."""
    from scripts.seeding.seed_projects_demo import summarize_demo_seed_budget_allocation

    empty = summarize_demo_seed_budget_allocation([])
    assert empty == {
        "total_projects": 0,
        "funded_projects_count": 0,
        "unfunded_projects_count": 0,
        "total_portfolio_budget": 0.0,
        "avg_project_budget": 0.0,
        "max_project_budget": 0.0,
        "max_budget_share_pct": 0.0,
        "allocation_status": "empty_seed",
    }

    # presupuesto en cero y valores negativos clampean a 0
    unfunded = summarize_demo_seed_budget_allocation(
        [{"budget": -5}, {"bac": 0.0}, "no-dict"]
    )
    assert unfunded["total_projects"] == 2  # el str no-dict se filtra
    assert unfunded["total_portfolio_budget"] == 0.0
    assert unfunded["allocation_status"] == "unfunded_portfolio"
