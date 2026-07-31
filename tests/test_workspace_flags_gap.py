"""
Direct unit tests for backend.api.workspace_shared._flags.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from backend.api.workspace_shared import _flags as flags


class TestSanitizeFeaturePayload:
    def test_empty_payload(self):
        result = flags._sanitize_feature_payload({}, {"feat_a", "feat_b"})
        assert result == {}

    def test_valid_features(self):
        result = flags._sanitize_feature_payload(
            {"feat_a": True, "feat_b": False},
            {"feat_a", "feat_b"},
        )
        assert result == {"feat_a": True, "feat_b": False}

    def test_unknown_feature_raises_400(self):
        with pytest.raises(HTTPException) as exc:
            flags._sanitize_feature_payload({"unknown": True}, {"known"})
        assert exc.value.status_code == 400

    def test_non_bool_value_raises_422(self):
        with pytest.raises(HTTPException) as exc:
            flags._sanitize_feature_payload({"known": "not-bool"}, {"known"})
        assert exc.value.status_code == 422

    def test_non_dict_payload_raises_422(self):
        with pytest.raises(HTTPException) as exc:
            flags._sanitize_feature_payload("not-dict", set())
        assert exc.value.status_code == 422


class TestNormalizeRoleList:
    def test_none_returns_empty(self):
        assert flags._normalize_role_list(None, "roles") == []

    def test_valid_roles(self, monkeypatch):
        monkeypatch.setattr("backend.api.workspace_shared._flags.VALID_ROLES", {"admin", "user"})
        monkeypatch.setattr("backend.api.workspace_shared._flags.MAX_LIST_ITEMS", 100)
        result = flags._normalize_role_list(["admin", "user"], "roles")
        assert result == ["admin", "user"]

    def test_invalid_role_raises_422(self, monkeypatch):
        monkeypatch.setattr("backend.api.workspace_shared._flags.VALID_ROLES", {"admin"})
        monkeypatch.setattr("backend.api.workspace_shared._flags.MAX_LIST_ITEMS", 100)
        with pytest.raises(HTTPException) as exc:
            flags._normalize_role_list(["invalid_role"], "roles")
        assert exc.value.status_code == 422

    def test_non_list_raises_422(self):
        with pytest.raises(HTTPException) as exc:
            flags._normalize_role_list("not-list", "roles")
        assert exc.value.status_code == 422

    def test_exceeds_max_raises_422(self, monkeypatch):
        monkeypatch.setattr("backend.api.workspace_shared._flags.MAX_LIST_ITEMS", 1)
        with pytest.raises(HTTPException) as exc:
            flags._normalize_role_list(["a", "b"], "roles")
        assert exc.value.status_code == 422

    def test_deduplicates(self, monkeypatch):
        monkeypatch.setattr("backend.api.workspace_shared._flags.VALID_ROLES", {"admin"})
        monkeypatch.setattr("backend.api.workspace_shared._flags.MAX_LIST_ITEMS", 100)
        result = flags._normalize_role_list(["admin", "admin"], "roles")
        assert result == ["admin"]

    def test_strips_and_lowers(self, monkeypatch):
        monkeypatch.setattr("backend.api.workspace_shared._flags.VALID_ROLES", {"admin"})
        monkeypatch.setattr("backend.api.workspace_shared._flags.MAX_LIST_ITEMS", 100)
        result = flags._normalize_role_list([" ADMIN "], "roles")
        assert result == ["admin"]


class TestNormalizeUserList:
    def test_none_returns_empty(self):
        assert flags._normalize_user_list(None, "users") == []

    def test_valid_users(self, monkeypatch):
        monkeypatch.setattr("backend.api.workspace_shared._flags.MAX_LIST_ITEMS", 100)
        result = flags._normalize_user_list(["user_1", "user_2"], "users")
        assert result == ["user_1", "user_2"]

    def test_non_list_raises_422(self):
        with pytest.raises(HTTPException) as exc:
            flags._normalize_user_list("not-list", "users")
        assert exc.value.status_code == 422

    def test_exceeds_max_raises_422(self, monkeypatch):
        monkeypatch.setattr("backend.api.workspace_shared._flags.MAX_LIST_ITEMS", 1)
        with pytest.raises(HTTPException) as exc:
            flags._normalize_user_list(["a", "b"], "users")
        assert exc.value.status_code == 422

    def test_non_string_element_raises_422(self):
        with pytest.raises(HTTPException) as exc:
            flags._normalize_user_list([123], "users")
        assert exc.value.status_code == 422

    def test_deduplicates(self, monkeypatch):
        monkeypatch.setattr("backend.api.workspace_shared._flags.MAX_LIST_ITEMS", 100)
        result = flags._normalize_user_list(["user1", "user1"], "users")
        assert result == ["user1"]

    def test_strips_whitespace(self, monkeypatch):
        monkeypatch.setattr("backend.api.workspace_shared._flags.MAX_LIST_ITEMS", 100)
        result = flags._normalize_user_list([" user1 "], "users")
        assert result == ["user1"]

    def test_skips_empty_strings(self, monkeypatch):
        monkeypatch.setattr("backend.api.workspace_shared._flags.MAX_LIST_ITEMS", 100)
        result = flags._normalize_user_list(["", "user1"], "users")
        assert result == ["user1"]
