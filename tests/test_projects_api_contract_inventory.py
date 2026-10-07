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
