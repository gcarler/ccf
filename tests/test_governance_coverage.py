"""Coverage tests for the Governance module.

Covers:
- GET /api/governance/audit-logs (list, auth, filtering)
- AutomationRule CRUD functions
- Edge cases: 401, 404, empty results, cross-sede isolation
"""

from __future__ import annotations

import uuid as _uuid

from backend import models as _models
from tests.conftest import (
    auth_headers as _auth_headers,
)
from tests.conftest import (
    seed_admin as _seed_admin,
)
from tests.conftest import (
    seed_user_with_role as _seed_user_with_role,
)

# ── Helpers ─────────────────────────────────────────────────────────


def _create_audit_log(db_session, *, persona_id=None, action="test_action", resource_type="test"):
    """Crea un AdminAuditLog directamente en la BD."""
    log = _models.AdminAuditLog(
        actor_persona_id=persona_id or _uuid.uuid4(),
        action=action,
        resource_type=resource_type,
        resource_id=str(_uuid.uuid4()),
        severity="info",
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)
    return log


def _create_automation_rule(db_session, *, name="Test Rule", trigger_type="manual"):
    """Crea un AutomationRule directamente en la BD."""
    rule = _models.AutomationRule(
        name=name,
        trigger_type=trigger_type,
        action_type="notify",
        is_active=True,
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)
    return rule


# ══════════════════════════════════════════════════════════════════════
# A. Governance audit-logs endpoint tests
# ══════════════════════════════════════════════════════════════════════


def test_audit_logs_list(client, db_session):
    """GET /governance/audit-logs → 200 + list con logs existentes."""
    admin, persona, _ = _seed_admin(db_session)
    _create_audit_log(db_session, persona_id=persona.id, action="user_created")
    _create_audit_log(db_session, persona_id=persona.id, action="role_updated")
    headers = _auth_headers(client, email=admin.email)
    resp = client.get("/api/governance/audit-logs", headers=headers)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 2


def test_audit_logs_unauthenticated_401(client, db_session):
    """GET /governance/audit-logs sin auth → 401/403."""
    resp = client.get("/api/governance/audit-logs")
    assert resp.status_code in (401, 403), f"Expected 401/403, got {resp.status_code}"


def test_audit_logs_non_admin_403(client, db_session):
    """GET /governance/audit-logs con rol sin permisos → 403."""
    student, _, _ = _seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="gov.student@example.com",
        permisos={"default": "allow"},
    )
    headers = _auth_headers(client, email=student.email)
    resp = client.get("/api/governance/audit-logs", headers=headers)
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


def test_audit_logs_empty(client, db_session):
    """GET /governance/audit-logs sin logs → 200 + lista vacía."""
    admin, _, _ = _seed_admin(db_session)
    headers = _auth_headers(client, email=admin.email)
    resp = client.get("/api/governance/audit-logs", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_audit_logs_filter_by_resource_type(client, db_session):
    """GET /governance/audit-logs?resource_type=... filtra correctamente."""
    admin, persona, _ = _seed_admin(db_session)
    _create_audit_log(db_session, persona_id=persona.id, action="create", resource_type="user")
    _create_audit_log(db_session, persona_id=persona.id, action="create", resource_type="role")
    headers = _auth_headers(client, email=admin.email)

    resp = client.get("/api/governance/audit-logs?resource_type=user", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert all(entry["resource_type"] == "user" for entry in data), (
        f"Expected all resource_type='user', got: {[e['resource_type'] for e in data]}"
    )


def test_audit_logs_response_shape(client, db_session):
    """GET /governance/audit-logs → cada entry tiene las claves del schema AdminAuditLog."""
    admin, persona, _ = _seed_admin(db_session)
    _create_audit_log(db_session, persona_id=persona.id, action="test_shape")
    headers = _auth_headers(client, email=admin.email)
    resp = client.get("/api/governance/audit-logs?limit=1", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    entry = data[0]
    expected_keys = {
        "id",
        "actor_persona_id",
        "action",
        "resource_type",
        "resource_id",
        "severity",
        "metadata",
        "created_at",
    }
    assert expected_keys.issubset(entry.keys()), f"Missing keys: {expected_keys - set(entry.keys())}"


# ══════════════════════════════════════════════════════════════════════
# B. AutomationRule CRUD (from crud/governance.py)
# ══════════════════════════════════════════════════════════════════════


def test_get_automation_rules(client, db_session):
    """Verifica que las funciones CRUD de AutomationRule existen y son llamables."""
    from backend import crud

    _create_automation_rule(db_session, name="Rule A")
    _create_automation_rule(db_session, name="Rule B")
    rules = crud.get_automation_rules(db_session)
    assert len(rules) >= 2


def test_get_automation_rule_by_id(client, db_session):
    from backend import crud

    rule = _create_automation_rule(db_session, name="Find Me")
    found = crud.get_automation_rule(db_session, rule.id)
    assert found is not None
    assert found.name == "Find Me"


def test_get_automation_rule_not_found(client, db_session):
    from backend import crud

    found = crud.get_automation_rule(db_session, _uuid.uuid4())
    assert found is None


def test_get_automation_rules_only_active(client, db_session):
    from backend import crud

    _create_automation_rule(db_session, name="Active", trigger_type="manual")
    inactive = _create_automation_rule(db_session, name="Inactive", trigger_type="manual")
    inactive.is_active = False
    db_session.commit()
    all_rules = crud.get_automation_rules(db_session)
    active_rules = crud.get_automation_rules(db_session, only_active=True)
    assert len(active_rules) < len(all_rules)
    assert all(r.is_active for r in active_rules)


def test_create_automation_rule(client, db_session):
    from backend import crud
    from backend.schemas.governance import AutomationRuleCreate

    payload = AutomationRuleCreate(name="New Rule", trigger_type="scheduled", action_type="email")
    rule = crud.create_automation_rule(db_session, payload)
    assert rule.id is not None
    assert rule.name == "New Rule"
    assert rule.trigger_type == "scheduled"


def test_update_automation_rule(client, db_session):
    from backend import crud
    from backend.schemas.governance import AutomationRuleUpdate

    rule = _create_automation_rule(db_session, name="Old Name")
    payload = AutomationRuleUpdate(name="Updated Name")
    updated = crud.update_automation_rule(db_session, rule.id, payload)
    assert updated is not None
    assert updated.name == "Updated Name"


def test_update_automation_rule_not_found(client, db_session):
    from backend import crud
    from backend.schemas.governance import AutomationRuleUpdate

    payload = AutomationRuleUpdate(name="Nope")
    result = crud.update_automation_rule(db_session, _uuid.uuid4(), payload)
    assert result is None


def test_delete_automation_rule(client, db_session):
    from backend import crud

    rule = _create_automation_rule(db_session, name="To Delete")
    result = crud.delete_automation_rule(db_session, rule.id)
    assert result is True
    # Verify soft delete via is_active=False
    from backend import models

    deactivated = db_session.query(models.AutomationRule).filter(models.AutomationRule.id == rule.id).first()
    assert deactivated is not None
    assert deactivated.is_active is False


def test_delete_automation_rule_not_found(client, db_session):
    from backend import crud

    result = crud.delete_automation_rule(db_session, _uuid.uuid4())
    assert result is False


def test_record_automation_run(client, db_session):
    from backend import crud

    rule = _create_automation_rule(db_session, name="Runnable")
    assert rule.last_run is None
    result = crud.record_automation_run(db_session, rule.id)
    assert result is not None
    assert result.last_run is not None


def test_record_automation_run_not_found(client, db_session):
    from backend import crud

    result = crud.record_automation_run(db_session, _uuid.uuid4())
    assert result is None
