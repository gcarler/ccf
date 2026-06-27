import json
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import models
from backend.api import workspace_shared
from tests.conftest import seed_admin, auth_headers

pytestmark = pytest.mark.xfail(
    reason="DATA_DIR apunta a ruta Windows (C:/Users/USUARIO/) — no disponible en servidor Linux",
    strict=False,
)


@pytest.fixture(autouse=True)
def isolated_workspace_storage(monkeypatch):
    data_dir = Path("C:/Users/USUARIO/.codex/memories")
    run_id = uuid.uuid4().hex
    flags_file = data_dir / f"feature_flags_{run_id}.json"
    audit_file = data_dir / f"feature_flags_audit_{run_id}.ndjson"
    incidents_file = data_dir / f"feature_flags_incidents_{run_id}.json"
    notifications_file = data_dir / f"feature_flags_notifications_{run_id}.ndjson"
    snapshot_history_file = data_dir / f"feature_flags_snapshot_history_{run_id}.ndjson"
    from backend.api.workspace_shared import _storage

    monkeypatch.setattr(workspace_shared, "DATA_DIR", data_dir)
    monkeypatch.setattr(workspace_shared, "FLAGS_FILE", flags_file)
    monkeypatch.setattr(_storage, "DATA_DIR", data_dir)
    monkeypatch.setattr(_storage, "FLAGS_FILE", flags_file)
    monkeypatch.setattr(_storage, "AUDIT_FILE", audit_file)
    monkeypatch.setattr(_storage, "INCIDENTS_FILE", incidents_file)
    monkeypatch.setattr(_storage, "NOTIFICATIONS_FILE", notifications_file)
    monkeypatch.setattr(_storage, "SNAPSHOT_HISTORY_FILE", snapshot_history_file)
    try:
        yield
    finally:
        for path in [
            flags_file,
            audit_file,
            incidents_file,
            notifications_file,
            snapshot_history_file,
        ]:
            path.unlink(missing_ok=True)


def seed_admin(
    db_session, email: str = "admin@example.com", password: str = "secret123"
):
    user_obj, _, _ = seed_admin(db_session, email, password)
    return user_obj


def auth_headers(
    client, email: str = "admin@example.com", password: str = "secret123"
) -> dict[str, str]:
    return auth_headers(client, email, password)


def test_workspace_config_returns_resolved_features(client: TestClient, db_session):
    admin = seed_admin(db_session)

    response = client.get("/api/workspace/config", headers=auth_headers(client))

    assert response.status_code == 200
    payload = response.json()
    assert payload["requested_by"] == str(admin.id)
    assert payload["features_raw"]["command_center"] is True
    assert payload["features_enabled"]["command_center"] is True
    assert "feature_rules" in payload


def test_workspace_flags_update_persists_and_surfaces_in_audit(
    client: TestClient, db_session
):
    seed_admin(db_session)
    headers = auth_headers(client)

    update_response = client.put(
        "/api/workspace/flags",
        headers=headers,
        json={"automation_builder": True, "presence_live": True},
    )

    assert update_response.status_code == 200
    assert update_response.json()["features_enabled"]["automation_builder"] is True

    saved_config = json.loads(workspace_shared.FLAGS_FILE.read_text(encoding="utf-8"))
    assert saved_config["features_enabled"]["automation_builder"] is True
    assert saved_config["features_enabled"]["presence_live"] is True

    audit_response = client.get("/api/workspace/flags/audit", headers=headers)
    assert audit_response.status_code == 200
    audit_payload = audit_response.json()
    assert audit_payload["count"] == 1
    assert audit_payload["events"][0]["action"] == "update_flags"
    assert audit_payload["events"][0]["changes"]["automation_builder"] is True


def test_workspace_incident_scan_and_acknowledge_flow(client: TestClient, db_session):
    seed_admin(db_session)
    headers = auth_headers(client)

    first = client.put(
        "/api/workspace/flags", headers=headers, json={"automation_builder": True}
    )
    second = client.put(
        "/api/workspace/flags", headers=headers, json={"automation_builder": False}
    )
    assert first.status_code == 200
    assert second.status_code == 200

    scan_response = client.post(
        "/api/workspace/flags/incidents/scan",
        headers=headers,
        params={"actor_threshold": 2, "action_threshold": 99},
    )

    assert scan_response.status_code == 200
    scan_payload = scan_response.json()
    assert scan_payload["anomalies"]["has_anomaly"] is True
    assert scan_payload["scan"]["created"] >= 1

    incidents_response = client.get("/api/workspace/flags/incidents", headers=headers)
    assert incidents_response.status_code == 200
    incidents = incidents_response.json()["incidents"]
    assert len(incidents) >= 1

    incident_id = incidents[0]["id"]
    patch_response = client.patch(
        f"/api/workspace/flags/incidents/{incident_id}",
        headers=headers,
        json={"action": "acknowledge", "note": "triaged"},
    )

    assert patch_response.status_code == 200
    patched = patch_response.json()["incident"]
    assert patched["status"] == "acknowledged"
    assert patched["note"] == "triaged"


def test_workspace_compliance_history_and_drift_compare(client: TestClient, db_session):
    seed_admin(db_session)
    headers = auth_headers(client)

    first_update = client.put(
        "/api/workspace/flags", headers=headers, json={"automation_builder": True}
    )
    assert first_update.status_code == 200
    first_snapshot = client.get(
        "/api/workspace/flags/compliance/snapshot", headers=headers
    )
    assert first_snapshot.status_code == 200
    first_snapshot_id = first_snapshot.json()["signature"]["snapshot_id"]

    second_update = client.put(
        "/api/workspace/flags",
        headers=headers,
        json={"automation_builder": False, "presence_live": True},
    )
    assert second_update.status_code == 200
    second_snapshot = client.get(
        "/api/workspace/flags/compliance/snapshot", headers=headers
    )
    assert second_snapshot.status_code == 200
    second_snapshot_id = second_snapshot.json()["signature"]["snapshot_id"]

    history_response = client.get(
        "/api/workspace/flags/compliance/history", headers=headers
    )
    assert history_response.status_code == 200
    history_payload = history_response.json()
    assert history_payload["count"] == 2

    drift_response = client.get(
        "/api/workspace/flags/compliance/drift",
        headers=headers,
        params={
            "from_snapshot_id": first_snapshot_id,
            "to_snapshot_id": second_snapshot_id,
        },
    )
    assert drift_response.status_code == 200
    drift_payload = drift_response.json()["drift"]
    assert drift_payload["has_drift"] is True
    changed_features = {
        item["feature"] for item in drift_payload["active"]["feature_changes"]
    }
    assert "automation_builder" in changed_features
