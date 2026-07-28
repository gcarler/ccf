"""
Direct unit tests for backend.api.workspace_shared._storage.
"""
from __future__ import annotations

from backend.api.workspace_shared import _storage as storage
from backend.api.workspace_shared import DATA_DIR


class TestNowIso:
    def test_now_iso_returns_string(self):
        result = storage._now_iso()
        assert isinstance(result, str)
        assert "T" in result


class TestJsonCanonical:
    def test_json_canonical_sorts_keys(self):
        result = storage._json_canonical({"z": 1, "a": 2})
        assert result == '{"a":2,"z":1}'


class TestLoadWorkspaceConfig:
    def test_returns_dict(self):
        result = storage._load_workspace_config()
        assert isinstance(result, dict)

    def test_has_feature_rules(self):
        result = storage._load_workspace_config()
        assert "feature_rules" in result


class TestAppendIncidentHistory:
    def test_appends_to_incident(self):
        incident = {"history": []}
        storage._append_incident_history(
            incident, event="test", actor_id="actor_1",
            metadata={"key": "value"},
        )
        assert len(incident["history"]) == 1
        entry = incident["history"][0]
        assert entry["event"] == "test"

    def test_creates_history_key(self):
        incident = {}
        storage._append_incident_history(incident, event="created", actor_id="system")
        assert "history" in incident
        assert len(incident["history"]) == 1


class TestAppendNotification:
    def test_appends_notification(self):
        event = {"type": "test"}
        storage._append_notification(event)


class TestDataDir:
    def test_data_dir_is_path(self):
        assert DATA_DIR is not None


class TestDefaultConfigs:
    def test_has_default_workspace_config(self):
        from backend.api.workspace_shared import DEFAULT_WORKSPACE_CONFIG
        assert isinstance(DEFAULT_WORKSPACE_CONFIG, dict)
        assert "feature_rules" in DEFAULT_WORKSPACE_CONFIG

    def test_has_default_compliance_policy(self):
        from backend.api.workspace_shared import DEFAULT_COMPLIANCE_POLICY
        assert isinstance(DEFAULT_COMPLIANCE_POLICY, dict)
