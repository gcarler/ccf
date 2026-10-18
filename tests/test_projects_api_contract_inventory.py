"""Regression tests for the Projects OpenAPI security inventory."""

from __future__ import annotations

import pytest

from scripts import audit_projects_api_contracts


def test_inventory_refuses_operations_without_authenticated_actor_dependency(monkeypatch):
    monkeypatch.setattr(
        audit_projects_api_contracts,
        "declared_guards",
        lambda: {("GET", "/api/projects/private"): "NO current_user dependency"},
    )

    with pytest.raises(ValueError, match="authenticated current_user dependency"):
        audit_projects_api_contracts.render_inventory(
            {"paths": {"/api/projects/private": {"get": {"operationId": "private"}}}}
        )


def test_inventory_accepts_an_explicit_permission_guard(monkeypatch):
    monkeypatch.setattr(
        audit_projects_api_contracts,
        "declared_guards",
        lambda: {("GET", "/api/projects/private"): "projects:read"},
    )

    inventory = audit_projects_api_contracts.render_inventory(
        {"paths": {"/api/projects/private": {"get": {"operationId": "private"}}}}
    )

    assert "`projects:read`" in inventory


# ── summarize_projects_guard_coverage (pure helper) ───────────────────────────


def test_guard_summary_reports_full_coverage(monkeypatch):
    """Todas las operaciones con guard válido → 0 sin autenticar y 100% cubierto."""
    monkeypatch.setattr(
        audit_projects_api_contracts,
        "declared_guards",
        lambda: {
            ("GET", "/api/projects/items"): "projects:read",
            ("POST", "/api/projects/items"): "projects:create",
        },
    )

    summary = audit_projects_api_contracts.summarize_projects_guard_coverage(
        {
            "paths": {
                "/api/projects/items": {
                    "get": {"operationId": "list"},
                    "post": {"operationId": "create"},
                }
            }
        }
    )

    assert summary["total_operations"] == 2
    assert summary["authenticated_operations"] == 2
    assert summary["unauthenticated_operations"] == 0
    assert summary["missing_guard_mappings"] == 0
    assert summary["coverage_pct"] == 100.0
    assert summary["guard_distribution"] == {"projects:create": 1, "projects:read": 1}
    assert summary["is_fully_guarded"] is True


def test_guard_summary_counts_unauthenticated_operations(monkeypatch):
    """Operación con guard 'NO current_user dependency' → no cubierta."""
    monkeypatch.setattr(
        audit_projects_api_contracts,
        "declared_guards",
        lambda: {("GET", "/api/projects/open"): "NO current_user dependency"},
    )

    summary = audit_projects_api_contracts.summarize_projects_guard_coverage(
        {"paths": {"/api/projects/open": {"get": {"operationId": "open"}}}}
    )

    assert summary["total_operations"] == 1
    assert summary["authenticated_operations"] == 0
    assert summary["unauthenticated_operations"] == 1
    assert summary["missing_guard_mappings"] == 0
    assert summary["coverage_pct"] == 0.0
    assert summary["guard_distribution"] == {"NO current_user dependency": 1}
    assert summary["is_fully_guarded"] is False


def test_guard_summary_counts_missing_guard_mappings(monkeypatch):
    """Operación OpenAPI sin entrada en declared_guards() → missing mapping."""
    monkeypatch.setattr(
        audit_projects_api_contracts,
        "declared_guards",
        lambda: {("GET", "/api/projects/items"): "projects:read"},
    )

    summary = audit_projects_api_contracts.summarize_projects_guard_coverage(
        {
            "paths": {
                "/api/projects/items": {"get": {"operationId": "list"}},
                "/api/projects/orphan": {"delete": {"operationId": "orphan"}},
            }
        }
    )

    assert summary["total_operations"] == 2
    assert summary["authenticated_operations"] == 1
    assert summary["missing_guard_mappings"] == 1
    # La operación sin mapeo no entra en la distribución ni en coverage
    assert summary["coverage_pct"] == 50.0
    assert summary["guard_distribution"] == {"projects:read": 1}
    assert summary["is_fully_guarded"] is False


def test_guard_summary_empty_openapi(monkeypatch):
    """OpenAPI vacío (0 operaciones) → coverage 100.0 y is_fully_guarded False."""
    monkeypatch.setattr(
        audit_projects_api_contracts,
        "declared_guards",
        lambda: {},
    )

    summary = audit_projects_api_contracts.summarize_projects_guard_coverage({"paths": {}})

    assert summary == {
        "total_operations": 0,
        "authenticated_operations": 0,
        "unauthenticated_operations": 0,
        "missing_guard_mappings": 0,
        "coverage_pct": 100.0,
        "guard_distribution": {},
        "is_fully_guarded": False,
    }


def test_guard_summary_orders_guard_distribution_alphabetically(monkeypatch):
    """La distribución agrupa por guard y sale ordenada alfabéticamente."""
    monkeypatch.setattr(
        audit_projects_api_contracts,
        "declared_guards",
        lambda: {
            ("GET", "/api/projects/a"): "projects:read",
            ("GET", "/api/projects/b"): "projects:admin",
            ("GET", "/api/projects/c"): "projects:read",
            ("GET", "/api/projects/d"): "projects:edit",
        },
    )

    summary = audit_projects_api_contracts.summarize_projects_guard_coverage(
        {
            "paths": {
                f"/api/projects/{key}": {"get": {"operationId": f"op{key}"}} for key in "abcd"
            }
        }
    )

    assert summary["total_operations"] == 4
    assert summary["authenticated_operations"] == 4
    assert list(summary["guard_distribution"].items()) == [
        ("projects:admin", 1),
        ("projects:edit", 1),
        ("projects:read", 2),
    ]
    assert summary["coverage_pct"] == 100.0
    assert summary["is_fully_guarded"] is True
