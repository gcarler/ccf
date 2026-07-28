"""
Direct unit tests for backend.api.workspace_shared._incidents.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.api.workspace_shared import _incidents as incidents


class TestIncidentFingerprint:
    def test_fingerprint_is_consistent(self):
        kind = "test"
        key = "my-key"
        fp1 = incidents._incident_fingerprint(kind, key)
        fp2 = incidents._incident_fingerprint(kind, key)
        assert fp1 == fp2
        assert isinstance(fp1, str)
        assert len(fp1) == 32  # md5 hex

    def test_fingerprint_differs_for_different_keys(self):
        fp1 = incidents._incident_fingerprint("kind", "key1")
        fp2 = incidents._incident_fingerprint("kind", "key2")
        assert fp1 != fp2


class TestIsSilencedActive:
    def test_no_silenced_until_returns_false(self):
        incident = {}
        assert incidents._is_silenced_active(incident) is False

    def test_silenced_in_past_returns_false(self):
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        incident = {"silenced_until": past}
        assert incidents._is_silenced_active(incident) is False

    def test_silenced_in_future_returns_true(self):
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        incident = {"silenced_until": future}
        assert incidents._is_silenced_active(incident) is True

    def test_invalid_date_returns_false(self):
        incident = {"silenced_until": "not-a-date"}
        assert incidents._is_silenced_active(incident) is False


class TestSecondsBetween:
    def test_returns_positive_delta(self):
        start = datetime.now(timezone.utc).isoformat()
        end = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        delta = incidents._seconds_between(start, end)
        assert delta is not None
        assert delta > 0

    def test_returns_none_for_inverted_dates(self):
        start = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        end = datetime.now(timezone.utc).isoformat()
        assert incidents._seconds_between(start, end) is None

    def test_returns_none_for_invalid_dates(self):
        assert incidents._seconds_between("invalid", "invalid") is None

    def test_returns_none_for_none(self):
        assert incidents._seconds_between(None, None) is None


class TestComputeIncidentSeverity:
    def test_closed_status_returns_low(self):
        incident = {"status": "closed"}
        assert incidents._compute_incident_severity(incident) == "low"

    def test_high_ratio_returns_critical(self):
        incident = {"status": "open", "count": 10, "threshold": 2, "created_at": datetime.now(timezone.utc).isoformat()}
        assert incidents._compute_incident_severity(incident) == "critical"

    def test_default_severity_is_low(self):
        incident = {}
        severity = incidents._compute_incident_severity(incident)
        assert severity in ("low", "medium", "high", "critical")


class TestSummarizeIncidents:
    def test_empty_incidents(self):
        result = incidents._summarize_incidents([])
        assert result["total"] == 0
        assert result["counts"] == {}
        assert result["mtta_minutes"] is None

    def test_single_open_incident(self):
        inc = [{
            "status": "open",
            "severity": "high",
            "created_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        }]
        result = incidents._summarize_incidents(inc)
        assert result["total"] == 1
        assert result["counts"].get("open") == 1
        assert result["severity_counts"].get("high") == 1

    def test_with_ack_and_close(self):
        created = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
        ack_at = (datetime.now(timezone.utc) - timedelta(hours=2, minutes=30)).isoformat()
        closed_at = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        inc = [{
            "status": "closed",
            "severity": "critical",
            "created_at": created,
            "ack_at": ack_at,
            "closed_at": closed_at,
        }]
        result = incidents._summarize_incidents(inc)
        assert result["total"] == 1
        assert result["mtta_minutes"] is not None
        assert result["mttr_minutes"] is not None


class TestCleanupIncidents:
    def test_empty_list(self):
        result = incidents._cleanup_incidents([], retain_closed_days=30, retain_resolved_days=7)
        assert result["removed_closed"] == 0
        assert result["removed_resolved"] == 0

    def test_silence_expired_reopens(self):
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        inc = [{"status": "silenced", "silenced_until": past, "created_at": datetime.now(timezone.utc).isoformat()}]
        result = incidents._cleanup_incidents(inc, retain_closed_days=30, retain_resolved_days=7)
        assert result["reopened_silenced"] == 1
        assert inc[0]["status"] == "open"


class TestIncidentDailyTrends:
    def test_empty_incidents(self):
        result = incidents._incident_daily_trends([], days=7)
        assert len(result) == 7

    def test_with_incidents(self):
        inc = [{
            "status": "closed",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "closed_at": datetime.now(timezone.utc).isoformat(),
            "ack_at": datetime.now(timezone.utc).isoformat(),
        }]
        result = incidents._incident_daily_trends(inc, days=1)
        assert len(result) >= 1
