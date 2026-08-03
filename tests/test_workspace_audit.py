"""Tests for _audit.py — pure dict/list logic."""
from __future__ import annotations

from backend.api.workspace_shared._audit import (
    _build_event_diff,
    _enrich_audit_rows,
    _filter_audit_rows,
    _parse_timestamp,
    _summarize_audit,
)

# ── _parse_timestamp ───────────────────────────────────────────────────────────

class TestParseTimestamp:
    def test_valid_iso(self):
        r = _parse_timestamp("2026-07-29T12:00:00Z")
        assert r is not None
        assert r.hour == 12

    def test_valid_offset(self):
        r = _parse_timestamp("2026-07-29T12:00:00+02:00")
        assert r is not None
        assert r.hour == 10  # converted to UTC

    def test_naive_becomes_utc(self):
        r = _parse_timestamp("2026-07-29T12:00:00")
        assert r is not None
        assert r.tzinfo is not None
        assert r.hour == 12  # kept as UTC

    def test_invalid(self):
        assert _parse_timestamp("not-a-date") is None

    def test_empty(self):
        assert _parse_timestamp("") is None

    def test_none(self):
        assert _parse_timestamp(None) is None

    def test_non_string(self):
        assert _parse_timestamp(12345) is None

    def test_whitespace(self):
        assert _parse_timestamp("  ") is None


# ── _filter_audit_rows ─────────────────────────────────────────────────────────

class TestFilterAuditRows:
    ROWS = [
        {"action": "update", "feature_id": "f1", "updated_by": "user_a"},
        {"action": "create", "feature_id": "f2", "updated_by": "user_b"},
        {"action": "update", "feature_id": "f1", "updated_by": "user_b"},
    ]

    def test_no_filter(self):
        r = _filter_audit_rows(self.ROWS)
        assert len(r) == 3

    def test_by_action(self):
        r = _filter_audit_rows(self.ROWS, action="update")
        assert len(r) == 2

    def test_by_feature(self):
        r = _filter_audit_rows(self.ROWS, feature_id="f1")
        assert len(r) == 2

    def test_by_actor(self):
        r = _filter_audit_rows(self.ROWS, actor="user_a")
        assert len(r) == 1

    def test_combined(self):
        r = _filter_audit_rows(self.ROWS, action="update", actor="user_b")
        assert len(r) == 1

    def test_limit(self):
        rows = [{"action": "x", "feature_id": "f", "updated_by": "u"} for _ in range(200)]
        r = _filter_audit_rows(rows, limit=10)
        assert len(r) == 10

    def test_limit_clamped(self):
        rows = [{"action": "x"} for _ in range(200)]
        r = _filter_audit_rows(rows, limit=9999)
        assert len(r) == 200  # 200 rows, clamped limit 1000 doesn't reduce

    def test_case_insensitive_action(self):
        r = _filter_audit_rows(self.ROWS, action="UPDATE")
        assert len(r) == 2


# ── _build_event_diff ──────────────────────────────────────────────────────────

class TestBuildEventDiff:
    def test_no_diff(self):
        r = _build_event_diff({"before": {"a": 1}, "after": {"a": 1}})
        assert r["count"] == 0

    def test_with_diff(self):
        r = _build_event_diff({"before": {"a": 1, "b": 2}, "after": {"a": 1, "b": 3}})
        assert r["count"] == 1
        assert r["changes"][0]["key"] == "b"

    def test_new_key(self):
        r = _build_event_diff({"before": {}, "after": {"a": 1}})
        assert r["count"] == 1

    def test_removed_key(self):
        r = _build_event_diff({"before": {"a": 1}, "after": {}})
        assert r["count"] == 1

    def test_missing_before_after(self):
        r = _build_event_diff({})
        assert r["count"] == 0

    def test_non_dict_before(self):
        r = _build_event_diff({"before": "string", "after": {"a": 1}})
        assert r["count"] == 0


# ── _enrich_audit_rows ─────────────────────────────────────────────────────────

class TestEnrichAuditRows:
    def test_adds_diff(self):
        rows = [{"before": {"a": 1}, "after": {"a": 2}}]
        r = _enrich_audit_rows(rows)
        assert len(r) == 1
        assert "diff" in r[0]
        assert r[0]["diff"]["count"] == 1

    def test_preserves_original(self):
        rows = [{"id": "1", "action": "update"}]
        r = _enrich_audit_rows(rows)
        assert r[0]["id"] == "1"
        assert r[0]["action"] == "update"


# ── _summarize_audit ───────────────────────────────────────────────────────────

class TestSummarizeAudit:
    def test_empty(self):
        r = _summarize_audit([])
        assert r["total_events"] == 0

    def test_with_rows(self):
        rows = [
            {"action": "update", "updated_by": "alice", "feature_id": "f1"},
            {"action": "update", "updated_by": "alice", "feature_id": "f1"},
            {"action": "create", "updated_by": "bob", "feature_id": "f2"},
        ]
        r = _summarize_audit(rows)
        assert r["total_events"] == 3
        assert r["by_action"]["update"] == 2
        assert r["by_action"]["create"] == 1
        assert len(r["top_actors"]) == 2
        assert r["top_actors"][0]["actor"] == "alice"

    def test_default_values(self):
        rows = [{"no_action": True}]
        r = _summarize_audit(rows)
        assert r["by_action"].get("unknown") == 1
