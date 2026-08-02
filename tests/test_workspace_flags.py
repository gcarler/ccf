"""Tests for _flags.py — pure dict/list logic."""
from __future__ import annotations

import pytest

from backend.api.workspace_shared import MAX_LIST_ITEMS
from backend.api.workspace_shared._flags import (
    _normalize_role_list,
    _normalize_rollout,
    _normalize_rule_payload,
    _normalize_user_list,
    _resolve_features,
    _sanitize_feature_payload,
    _stable_rollout_hit,
)

# ── _sanitize_feature_payload ──────────────────────────────────────────────────

class TestSanitizeFeaturePayload:
    def test_valid(self):
        r = _sanitize_feature_payload({"f1": True, "f2": False}, {"f1", "f2"})
        assert r == {"f1": True, "f2": False}

    def test_non_dict_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _sanitize_feature_payload("not-dict", set())
        assert exc.value.status_code == 422

    def test_unknown_keys_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _sanitize_feature_payload({"unknown": True}, {"known"})
        assert exc.value.status_code == 400

    def test_non_bool_value_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _sanitize_feature_payload({"f1": "yes"}, {"f1"})
        assert exc.value.status_code == 422


# ── _normalize_role_list ───────────────────────────────────────────────────────

class TestNormalizeRoleList:
    def test_none(self):
        assert _normalize_role_list(None, "roles") == []

    def test_valid(self):
        r = _normalize_role_list(["ADMIN", "pastor"], "roles")
        assert "admin" in r
        assert "pastor" in r

    def test_not_list_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _normalize_role_list("str", "x")
        assert exc.value.status_code == 422

    def test_too_many_items_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _normalize_role_list(["a"] * (MAX_LIST_ITEMS + 1), "x")
        assert exc.value.status_code == 422

    def test_non_string_item_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _normalize_role_list([123], "x")
        assert exc.value.status_code == 422

    def test_empty_string_skipped(self):
        r = _normalize_role_list(["admin", "", "pastor"], "roles")
        assert "admin" in r
        assert "pastor" in r
        assert "" not in r

    def test_invalid_role_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _normalize_role_list(["nonexistent_role"], "x")
        assert exc.value.status_code == 422

    def test_dedup(self):
        r = _normalize_role_list(["admin", "ADMIN", "admin"], "roles")
        assert r == ["admin"]


# ── _normalize_user_list ───────────────────────────────────────────────────────

class TestNormalizeUserList:
    def test_none(self):
        assert _normalize_user_list(None, "users") == []

    def test_valid(self):
        r = _normalize_user_list(["user_a", "user_b"], "users")
        assert "user_a" in r
        assert "user_b" in r

    def test_not_list_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _normalize_user_list("str", "x")
        assert exc.value.status_code == 422

    def test_too_many_items_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _normalize_user_list(["a"] * (MAX_LIST_ITEMS + 1), "x")
        assert exc.value.status_code == 422

    def test_non_string_item_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _normalize_user_list([123], "x")
        assert exc.value.status_code == 422

    def test_empty_string_skipped(self):
        r = _normalize_user_list(["a", "", "b"], "users")
        assert r == ["a", "b"]

    def test_overlong_raises(self):
        from fastapi import HTTPException

        from backend.api.workspace_shared import MAX_USER_REF_LENGTH
        with pytest.raises(HTTPException) as exc:
            _normalize_user_list(["x" * (MAX_USER_REF_LENGTH + 1)], "x")
        assert exc.value.status_code == 422

    def test_dedup(self):
        r = _normalize_user_list(["a", "A", "a"], "users")
        assert r == ["a", "A"]


# ── _normalize_rollout ─────────────────────────────────────────────────────────

class TestNormalizeRollout:
    def test_none_uses_fallback(self):
        assert _normalize_rollout(None, fallback=50) == 50

    def test_valid_int(self):
        assert _normalize_rollout(75) == 75

    def test_bool_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _normalize_rollout(True)
        assert exc.value.status_code == 422

    def test_invalid_type_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _normalize_rollout("not-a-number")
        assert exc.value.status_code == 422

    def test_clamped_below_zero(self):
        assert _normalize_rollout(-10) == 0

    def test_clamped_above_100(self):
        assert _normalize_rollout(200) == 100

    def test_none_no_fallback(self):
        assert _normalize_rollout(None) == 100


# ── _normalize_rule_payload ────────────────────────────────────────────────────

class TestNormalizeRulePayload:
    def test_full_payload(self):
        r = _normalize_rule_payload({
            "roles_allow": ["admin"], "roles_deny": ["aspirante"],
            "users_allow": ["u1"], "users_deny": ["u2"],
            "rollout_percent": 50,
        })
        assert "admin" in r["roles_allow"]
        assert "aspirante" in r["roles_deny"]
        assert r["users_allow"] == ["u1"]
        assert r["users_deny"] == ["u2"]
        assert r["rollout_percent"] == 50
        assert r["roles_deny"] == ["aspirante"]
        assert r["users_allow"] == ["u1"]
        assert r["users_deny"] == ["u2"]
        assert r["rollout_percent"] == 50

    def test_inherits_fallback(self):
        fallback = {"roles_allow": ["admin"], "rollout_percent": 30}
        r = _normalize_rule_payload({}, fallback)
        assert r["roles_allow"] == ["admin"]
        assert r["rollout_percent"] == 30

    def test_not_dict_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _normalize_rule_payload("str")
        assert exc.value.status_code == 422

    def test_unknown_keys_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _normalize_rule_payload({"unknown_field": True})
        assert exc.value.status_code == 400

    def test_empty_payload(self):
        r = _normalize_rule_payload({})
        assert r["rollout_percent"] == 100
        assert r["roles_allow"] == []


# ── _stable_rollout_hit ────────────────────────────────────────────────────────

class TestStableRolloutHit:
    def test_100_percent_hits(self):
        assert _stable_rollout_hit("user1", "feat1", 100) is True

    def test_0_percent_misses(self):
        assert _stable_rollout_hit("user1", "feat1", 0) is False

    def test_consistent(self):
        r1 = _stable_rollout_hit("user_a", "feature_x", 50)
        r2 = _stable_rollout_hit("user_a", "feature_x", 50)
        assert r1 == r2

    def test_clamped_negative(self):
        assert _stable_rollout_hit("u1", "f1", -10) is False

    def test_clamped_over_100(self):
        assert _stable_rollout_hit("u1", "f1", 150) is True


# ── _resolve_features ──────────────────────────────────────────────────────────

class TestResolveFeatures:
    def test_all_disabled_if_base_off(self):
        config = {"features_enabled": {"f1": False}}
        user = type("U", (), {"role": "admin", "id": "user1"})()
        r = _resolve_features(config, user)
        assert r == {"f1": False}

    def test_roles_deny(self):
        config = {"features_enabled": {"f1": True},
                  "feature_rules": {"f1": {"roles_deny": ["admin"]}}}
        user = type("U", (), {"role": "admin", "id": "user1"})()
        r = _resolve_features(config, user)
        assert r["f1"] is False

    def test_users_deny(self):
        config = {"features_enabled": {"f1": True},
                  "feature_rules": {"f1": {"users_deny": ["user1"]}}}
        user = type("U", (), {"role": "admin", "id": "user1"})()
        r = _resolve_features(config, user)
        assert r["f1"] is False

    def test_users_allow_missing(self):
        config = {"features_enabled": {"f1": True},
                  "feature_rules": {"f1": {"users_allow": ["user2"]}}}
        user = type("U", (), {"role": "admin", "id": "user1"})()
        r = _resolve_features(config, user)
        assert r["f1"] is False

    def test_roles_allow_missing(self):
        config = {"features_enabled": {"f1": True},
                  "feature_rules": {"f1": {"roles_allow": ["editor"]}}}
        user = type("U", (), {"role": "admin", "id": "user1"})()
        r = _resolve_features(config, user)
        assert r["f1"] is False

    def test_rollout_miss(self):
        config = {"features_enabled": {"f1": True},
                  "feature_rules": {"f1": {"rollout_percent": 0}}}
        user = type("U", (), {"role": "admin", "id": "user1"})()
        r = _resolve_features(config, user)
        assert r["f1"] is False

    def test_allows(self):
        config = {"features_enabled": {"f1": True}}
        user = type("U", (), {"role": "admin", "id": "user1"})()
        r = _resolve_features(config, user)
        assert r["f1"] is True

    def test_empty_config(self):
        user = type("U", (), {"role": "admin", "id": "user1"})()
        r = _resolve_features({}, user)
        assert r == {}

    def test_rule_without_base_enabled(self):
        """Feature in rules but not in features_enabled -> False."""
        config = {"feature_rules": {"f1": {}}}
        user = type("U", (), {"role": "admin", "id": "user1"})()
        r = _resolve_features(config, user)
        assert r["f1"] is False

    def test_rules_with_empty_strings_filtered(self):
        """Roles with empty strings in config are filtered."""
        config = {"features_enabled": {"f1": True},
                  "feature_rules": {"f1": {"roles_deny": [""]}}}
        user = type("U", (), {"role": "admin", "id": "user1"})()
        r = _resolve_features(config, user)
        assert r["f1"] is True  # empty string filtered, no deny matches
