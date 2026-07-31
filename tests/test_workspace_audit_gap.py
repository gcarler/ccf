"""
Direct unit tests for backend.api.workspace_shared._audit.
"""

from __future__ import annotations

from backend.api.workspace_shared import _audit as audit


class TestParseTimestamp:
    def test_iso_format_with_z(self):
        result = audit._parse_timestamp("2026-07-01T12:00:00Z")
        assert result is not None
        assert result.tzinfo is not None

    def test_iso_format_with_offset(self):
        result = audit._parse_timestamp("2026-07-01T12:00:00+00:00")
        assert result is not None

    def test_naive_iso_is_parsed_as_utc(self):
        result = audit._parse_timestamp("2026-07-01T12:00:00")
        assert result is not None
        assert result.tzinfo is not None
        assert result.hour == 12

    def test_empty_string_returns_none(self):
        assert audit._parse_timestamp("") is None

    def test_none_returns_none(self):
        assert audit._parse_timestamp(None) is None

    def test_invalid_format_returns_none(self):
        assert audit._parse_timestamp("not-a-date") is None

    def test_whitespace_returns_none(self):
        assert audit._parse_timestamp("   ") is None

    def test_other_types_return_none(self):
        assert audit._parse_timestamp(12345) is None


class TestFilterAuditRows:
    def test_no_filters_returns_all(self):
        rows = [{"action": "create"}, {"action": "update"}]
        result = audit._filter_audit_rows(rows)
        assert len(result) == 2

    def test_filter_by_action(self):
        rows = [{"action": "create"}, {"action": "update"}, {"action": "create"}]
        result = audit._filter_audit_rows(rows, action="create")
        assert len(result) == 2

    def test_filter_by_action_case_insensitive(self):
        rows = [{"action": "CREATE"}, {"action": "create"}]
        result = audit._filter_audit_rows(rows, action="create")
        assert len(result) == 2

    def test_filter_by_feature_id(self):
        rows = [{"feature_id": "abc"}, {"feature_id": "def"}]
        result = audit._filter_audit_rows(rows, feature_id="abc")
        assert len(result) == 1

    def test_filter_by_actor(self):
        rows = [{"updated_by": "user1"}, {"updated_by": "user2"}]
        result = audit._filter_audit_rows(rows, actor="user1")
        assert len(result) == 1

    def test_limit_respected(self):
        rows = [{"action": "x"} for _ in range(20)]
        result = audit._filter_audit_rows(rows, limit=5)
        assert len(result) == 5

    def test_empty_rows(self):
        result = audit._filter_audit_rows([])
        assert result == []


class TestBuildEventDiff:
    def test_no_before_after(self):
        row = {}
        result = audit._build_event_diff(row)
        assert result["count"] == 0

    def test_identical_dicts(self):
        row = {"before": {"a": 1}, "after": {"a": 1}}
        result = audit._build_event_diff(row)
        assert result["count"] == 0

    def test_different_dicts(self):
        row = {"before": {"a": 1}, "after": {"a": 2}}
        result = audit._build_event_diff(row)
        assert result["count"] == 1
        assert result["changes"][0]["key"] == "a"
        assert result["changes"][0]["before"] == 1
        assert result["changes"][0]["after"] == 2

    def test_added_key(self):
        row = {"before": {}, "after": {"new_key": "value"}}
        result = audit._build_event_diff(row)
        assert result["count"] == 1

    def test_removed_key(self):
        row = {"before": {"old": "gone"}, "after": {}}
        result = audit._build_event_diff(row)
        assert result["count"] == 1

    def test_non_dict_before_after(self):
        row = {"before": "string", "after": "string"}
        result = audit._build_event_diff(row)
        assert result["count"] == 0


class TestEnrichAuditRows:
    def test_adds_diff_to_each_row(self):
        rows = [{"before": {"a": 1}, "after": {"a": 2}}]
        result = audit._enrich_audit_rows(rows)
        assert len(result) == 1
        assert "diff" in result[0]

    def test_empty_rows(self):
        result = audit._enrich_audit_rows([])
        assert result == []


class TestSummarizeAudit:
    def test_returns_dict_with_counts(self):
        rows = [{"action": "create"}, {"action": "update"}, {"action": "delete"}]
        result = audit._summarize_audit(rows)
        assert isinstance(result, dict)
        assert result["total_events"] == 3
        assert result["by_action"]["create"] == 1
        assert result["by_action"]["update"] == 1
        assert result["by_action"]["delete"] == 1

    def test_empty_rows(self):
        result = audit._summarize_audit([])
        assert result["total_events"] == 0

    def test_groups_by_action(self):
        rows = [{"action": "create"}, {"action": "create"}, {"action": "create"}]
        result = audit._summarize_audit(rows)
        assert result["by_action"]["create"] == 3
