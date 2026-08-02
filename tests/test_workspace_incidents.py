"""Tests for _incidents.py — pure dict/list logic."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from backend.api.workspace_shared._incidents import (
    _cleanup_incidents,
    _compute_incident_severity,
    _detect_anomalies,
    _in_range,
    _incident_daily_trends,
    _incident_fingerprint,
    _is_silenced_active,
    _pct_delta,
    _period_bounds,
    _period_incident_stats,
    _scan_incidents_from_anomalies,
    _seconds_between,
    _set_incident_severity,
    _summarize_incidents,
)

# ── _incident_fingerprint ──────────────────────────────────────────────────────

class TestIncidentFingerprint:
    def test_consistent(self):
        assert _incident_fingerprint("a", "b") == _incident_fingerprint("a", "b")

    def test_differs(self):
        assert _incident_fingerprint("a", "b") != _incident_fingerprint("b", "a")


# ── _is_silenced_active ────────────────────────────────────────────────────────

class TestIsSilencedActive:
    def test_no_silenced_until(self):
        assert _is_silenced_active({"silenced_until": None}) is False
        assert _is_silenced_active({}) is False

    def test_expired(self):
        past = (datetime.now(tz=timezone.utc) - timedelta(hours=1)).isoformat()
        assert _is_silenced_active({"silenced_until": past}) is False

    def test_active(self):
        future = (datetime.now(tz=timezone.utc) + timedelta(hours=1)).isoformat()
        assert _is_silenced_active({"silenced_until": future}) is True

    def test_invalid_timestamp(self):
        assert _is_silenced_active({"silenced_until": "not-a-date"}) is False


# ── _seconds_between ───────────────────────────────────────────────────────────

class TestSecondsBetween:
    def test_valid(self):
        start = "2026-07-01T10:00:00Z"
        end = "2026-07-01T11:30:00Z"
        result = _seconds_between(start, end)
        assert result == pytest.approx(5400, abs=1)

    def test_invalid_start(self):
        assert _seconds_between(None, "2026-07-01T12:00:00Z") is None

    def test_invalid_end(self):
        assert _seconds_between("2026-07-01T12:00:00Z", None) is None

    def test_reversed_order(self):
        start = "2026-07-01T12:00:00Z"
        end = "2026-07-01T10:00:00Z"
        assert _seconds_between(start, end) is None


# ── _compute_incident_severity ─────────────────────────────────────────────────

class TestComputeIncidentSeverity:
    def test_closed_returns_low(self):
        assert _compute_incident_severity({"status": "closed"}) == "low"

    def test_critical_ratio(self):
        """ratio >= 3.0 -> critical."""
        inc = {"status": "open", "count": 9, "threshold": 3, "created_at": datetime.now(tz=timezone.utc).isoformat()}
        assert _compute_incident_severity(inc) == "critical"

    def test_critical_age(self):
        """age >= 24h -> critical."""
        old = (datetime.now(tz=timezone.utc) - timedelta(hours=25)).isoformat()
        inc = {"status": "open", "count": 0, "threshold": 1, "created_at": old}
        assert _compute_incident_severity(inc) == "critical"

    def test_high_ratio(self):
        """ratio >= 2.0 -> high."""
        inc = {"status": "open", "count": 4, "threshold": 2, "created_at": datetime.now(tz=timezone.utc).isoformat()}
        assert _compute_incident_severity(inc) == "high"

    def test_high_age(self):
        """age >= 6h -> high."""
        old = (datetime.now(tz=timezone.utc) - timedelta(hours=7)).isoformat()
        inc = {"status": "open", "count": 0, "threshold": 1, "created_at": old}
        assert _compute_incident_severity(inc) == "high"

    def test_medium_ratio(self):
        """ratio >= 1.2 -> medium."""
        inc = {"status": "open", "count": 3, "threshold": 2, "created_at": datetime.now(tz=timezone.utc).isoformat()}
        assert _compute_incident_severity(inc) == "medium"

    def test_medium_age(self):
        """age >= 2h -> medium."""
        old = (datetime.now(tz=timezone.utc) - timedelta(hours=3)).isoformat()
        inc = {"status": "open", "count": 0, "threshold": 1, "created_at": old}
        assert _compute_incident_severity(inc) == "medium"

    def test_low(self):
        inc = {"status": "open", "count": 0, "threshold": 1, "created_at": datetime.now(tz=timezone.utc).isoformat()}
        assert _compute_incident_severity(inc) == "low"

    def test_defaults(self):
        assert _compute_incident_severity({}) == "low"


# ── _set_incident_severity ─────────────────────────────────────────────────────

class TestSetIncidentSeverity:
    def test_same_severity_no_change(self):
        inc = {"severity": "low", "status": "open", "count": 0, "threshold": 1,
               "created_at": datetime.now(tz=timezone.utc).isoformat()}
        with patch("backend.api.workspace_shared._incidents._append_incident_history") as mock_hist:
            with patch("backend.api.workspace_shared._incidents._append_notification") as mock_notif:
                changed = _set_incident_severity(inc, actor_id="test", reason="check")
        assert changed is False
        mock_hist.assert_not_called()
        mock_notif.assert_not_called()

    def test_escalation_triggers_notification(self):
        inc = {"severity": "low", "status": "open", "count": 6, "threshold": 2,
               "created_at": datetime.now(tz=timezone.utc).isoformat()}
        with patch("backend.api.workspace_shared._incidents._append_incident_history") as mock_hist:
            with patch("backend.api.workspace_shared._incidents._append_notification") as mock_notif:
                changed = _set_incident_severity(inc, actor_id="test", reason="spike")
        assert changed is True  # low -> high
        mock_hist.assert_called_once()
        mock_notif.assert_called_once()

    def test_deescalation_no_notification(self):
        inc = {"severity": "high", "status": "closed",
               "created_at": datetime.now(tz=timezone.utc).isoformat()}
        with patch("backend.api.workspace_shared._incidents._append_incident_history") as mock_hist:
            with patch("backend.api.workspace_shared._incidents._append_notification") as mock_notif:
                changed = _set_incident_severity(inc, actor_id="test", reason="resolved")
        assert changed is True  # high -> low
        mock_hist.assert_called_once()
        mock_notif.assert_not_called()


# ── _summarize_incidents ───────────────────────────────────────────────────────

class TestSummarizeIncidents:
    def test_empty(self):
        r = _summarize_incidents([])
        assert r["total"] == 0
        assert r["mtta_minutes"] is None

    def test_with_incidents(self):
        incidents = [
            {"status": "open", "severity": "high", "created_at": datetime.now(tz=timezone.utc).isoformat()},
            {"status": "closed", "severity": "low", "created_at": "2026-07-01T10:00:00Z",
             "ack_at": "2026-07-01T10:05:00Z", "closed_at": "2026-07-01T11:00:00Z"},
        ]
        r = _summarize_incidents(incidents)
        assert r["total"] == 2
        assert "counts" in r
        assert "severity_counts" in r

    def test_target_breaches(self):
        incidents = [
            {"status": "closed", "severity": "low", "created_at": "2026-07-01T10:00:00Z",
             "ack_at": "2026-07-01T12:00:00Z", "closed_at": "2026-07-01T14:00:00Z"},
        ]
        r = _summarize_incidents(incidents, mtta_target_minutes=30, mttr_target_minutes=30)
        assert r["breaches"]["mtta"] is True
        assert r["breaches"]["mttr"] is True

    def test_open_age_tracked(self):
        incidents = [
            {"status": "open", "severity": "medium",
             "created_at": (datetime.now(tz=timezone.utc) - timedelta(hours=2)).isoformat()},
        ]
        r = _summarize_incidents(incidents)
        assert r["open_age_p95_minutes"] is not None


# ── _cleanup_incidents ─────────────────────────────────────────────────────────

class TestCleanupIncidents:
    def test_removes_closed_old(self):
        closed_old = {"status": "closed",
                      "closed_at": (datetime.now(tz=timezone.utc) - timedelta(days=100)).isoformat()}
        recent = {"status": "open", "created_at": datetime.now(tz=timezone.utc).isoformat()}
        incidents = [closed_old, recent]
        with patch("backend.api.workspace_shared._incidents._append_incident_history"):
            r = _cleanup_incidents(incidents, retain_closed_days=30, retain_resolved_days=30)
        assert r["removed_closed"] == 1
        assert len(incidents) == 1

    def test_removes_resolved_old(self):
        resolved_old = {"status": "acknowledged",
                        "updated_at": (datetime.now(tz=timezone.utc) - timedelta(days=100)).isoformat()}
        incidents = [resolved_old]
        with patch("backend.api.workspace_shared._incidents._append_incident_history"):
            r = _cleanup_incidents(incidents, retain_closed_days=30, retain_resolved_days=30)
        assert r["removed_resolved"] == 1

    def test_expired_silence_reopens(self):
        expired = {"status": "silenced", "silenced_until": (datetime.now(tz=timezone.utc) - timedelta(hours=1)).isoformat(),
                   "created_at": datetime.now(tz=timezone.utc).isoformat()}
        incidents = [expired]
        with patch("backend.api.workspace_shared._incidents._append_incident_history") as mock:
            r = _cleanup_incidents(incidents, retain_closed_days=30, retain_resolved_days=30)
        assert r["reopened_silenced"] == 1
        assert incidents[0]["status"] == "open"
        mock.assert_called_once()

    def test_keeps_recent(self):
        recent = {"status": "open", "created_at": datetime.now(tz=timezone.utc).isoformat()}
        incidents = [recent]
        with patch("backend.api.workspace_shared._incidents._append_incident_history"):
            r = _cleanup_incidents(incidents, retain_closed_days=30, retain_resolved_days=30)
        assert r["removed_closed"] == 0
        assert r["removed_resolved"] == 0
        assert len(incidents) == 1


# ── _incident_daily_trends ─────────────────────────────────────────────────────

class TestIncidentDailyTrends:
    def test_empty(self):
        r = _incident_daily_trends([], days=7)
        assert len(r) == 7

    def test_with_incidents(self):
        now = datetime.now(tz=timezone.utc)
        incidents = [
            {"created_at": now.isoformat(), "closed_at": now.isoformat(), "ack_at": now.isoformat()},
        ]
        r = _incident_daily_trends(incidents, days=7)
        today = next((d for d in r if d["created"] > 0), None)
        assert today is not None
        assert today["created"] >= 1
        assert today["closed"] >= 1
        assert today["acknowledged"] >= 1

    def test_with_mtta_mttr(self):
        now = datetime.now(tz=timezone.utc)
        incidents = [
            {"created_at": (now - timedelta(minutes=60)).isoformat(),
             "closed_at": now.isoformat(),
             "ack_at": (now - timedelta(minutes=30)).isoformat()},
        ]
        r = _incident_daily_trends(incidents, days=7)
        today = next((d for d in r if d["created"] > 0), None)
        assert today["mtta_avg_minutes"] is not None
        assert today["mttr_avg_minutes"] is not None

    def test_unknown_dates_skipped(self):
        incidents = [{"created_at": "not-a-date"}]
        r = _incident_daily_trends(incidents, days=3)
        assert all(d["created"] == 0 for d in r)


# ── _period_bounds ─────────────────────────────────────────────────────────────

class TestPeriodBounds:
    def test_weekly(self):
        s, e, ps, pe, days = _period_bounds("weekly")
        assert days == 7
        assert s <= e
        assert ps < pe

    def test_monthly(self):
        s, e, ps, pe, days = _period_bounds("monthly")
        assert days == 30

    def test_invalid(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _period_bounds("invalid")
        assert exc.value.status_code == 400

    def test_default_weekly(self):
        s, e, ps, pe, days = _period_bounds(None)
        assert days == 7


# ── _in_range ──────────────────────────────────────────────────────────────────

class TestInRange:
    def test_in_range(self):
        start = datetime(2026, 7, 1, tzinfo=timezone.utc)
        end = datetime(2026, 7, 8, tzinfo=timezone.utc)
        assert _in_range(datetime(2026, 7, 3, tzinfo=timezone.utc), start, end) is True

    def test_outside_range(self):
        start = datetime(2026, 7, 1, tzinfo=timezone.utc)
        end = datetime(2026, 7, 8, tzinfo=timezone.utc)
        assert _in_range(datetime(2026, 6, 30, tzinfo=timezone.utc), start, end) is False

    def test_none_returns_false(self):
        assert _in_range(None, datetime.now(tz=timezone.utc), datetime.now(tz=timezone.utc)) is False


# ── _period_incident_stats ─────────────────────────────────────────────────────

class TestPeriodIncidentStats:
    def test_empty(self):
        now = datetime.now(tz=timezone.utc)
        r = _period_incident_stats([], now - timedelta(days=7), now)
        assert r["created"] == 0

    def test_with_data(self):
        now = datetime.now(tz=timezone.utc)
        incidents = [
            {"status": "open", "severity": "high",
             "created_at": (now - timedelta(days=1)).isoformat()},
            {"status": "closed", "severity": "low",
             "created_at": (now - timedelta(days=2)).isoformat(),
             "ack_at": (now - timedelta(days=2, hours=-1)).isoformat(),
             "closed_at": (now - timedelta(days=1)).isoformat()},
        ]
        start = now - timedelta(days=7)
        r = _period_incident_stats(incidents, start, now)
        assert r["created"] >= 1
        assert r["mtta_minutes"] is not None or r["mttr_minutes"] is not None

    def test_active_at_end(self):
        now = datetime.now(tz=timezone.utc)
        incidents = [
            {"created_at": (now - timedelta(days=2)).isoformat()},
        ]
        start = now - timedelta(days=7)
        r = _period_incident_stats(incidents, start, now)
        assert r["active_end"] >= 1


# ── _pct_delta ─────────────────────────────────────────────────────────────────

class TestPctDelta:
    def test_valid(self):
        assert _pct_delta(120, 100) == 20.0

    def test_none_current(self):
        assert _pct_delta(None, 100) is None

    def test_none_previous(self):
        assert _pct_delta(100, None) is None

    def test_zero_previous(self):
        assert _pct_delta(100, 0) is None

    def test_decrease(self):
        assert _pct_delta(50, 100) == -50.0


# ── _detect_anomalies ──────────────────────────────────────────────────────────

class TestDetectAnomalies:
    def test_no_recent_events(self):
        r = _detect_anomalies([])
        assert r["has_anomaly"] is False
        assert r["recent_events"] == 0

    def test_thresholds_clamped(self):
        old = (datetime.now(tz=timezone.utc) - timedelta(hours=48)).isoformat()
        rows = [{"timestamp": old, "updated_by": "u1", "action": "login"}]
        r = _detect_anomalies(rows, lookback_hours=24, actor_threshold=10, action_threshold=20)
        assert r["recent_events"] == 0  # old event excluded

    def test_detects_spikes(self):
        rows = []
        for i in range(15):
            rows.append({"timestamp": datetime.now(tz=timezone.utc).isoformat(),
                         "updated_by": "spammer", "action": "bulk_delete"})
        r = _detect_anomalies(rows, lookback_hours=24, actor_threshold=10, action_threshold=20)
        assert r["has_anomaly"] is True
        assert len(r["actor_spikes"]) >= 1

    def test_action_spike_detected(self):
        rows = [{"timestamp": datetime.now(tz=timezone.utc).isoformat(),
                 "updated_by": "u1", "action": "mass_edit"} for _ in range(25)]
        r = _detect_anomalies(rows, lookback_hours=24, actor_threshold=100, action_threshold=20)
        assert len(r["action_spikes"]) >= 1

    def test_safe_hours_clamped(self):
        rows = [{"timestamp": datetime.now(tz=timezone.utc).isoformat(),
                 "updated_by": "u1", "action": "login"}]
        r = _detect_anomalies(rows, lookback_hours=9999)
        assert r["lookback_hours"] == 720


# ── _scan_incidents_from_anomalies ─────────────────────────────────────────────

class TestScanIncidentsFromAnomalies:
    def test_empty_anomalies(self):
        r = _scan_incidents_from_anomalies({"actor_spikes": [], "action_spikes": []},
                                            incidents=[], actor_threshold=10, action_threshold=20)
        assert r["created"] == 0

    def test_creates_new_incidents(self):
        r = _scan_incidents_from_anomalies(
            {"actor_spikes": [{"actor": "bob", "count": 15}],
             "action_spikes": [{"action": "delete", "count": 25}]},
            incidents=[], actor_threshold=10, action_threshold=20,
        )
        assert r["created"] == 2

    def test_updates_existing(self):
        existing_inc = {"fingerprint": _incident_fingerprint("actor_spike", "bob"),
                        "status": "open", "count": 5, "threshold": 10,
                        "history": [], "note": "", "ack_by": None, "ack_at": None,
                        "closed_by": None, "closed_at": None, "silenced_until": None,
                        "severity": "low"}
        incidents = [existing_inc]
        with patch("backend.api.workspace_shared._incidents._append_incident_history"):
            r = _scan_incidents_from_anomalies(
                {"actor_spikes": [{"actor": "bob", "count": 20}], "action_spikes": []},
                incidents=incidents, actor_threshold=10, action_threshold=20,
            )
        assert r["updated"] == 1
        assert r["created"] == 0

    def test_reopens_silenced_expired(self):
        expired = {"fingerprint": _incident_fingerprint("actor_spike", "bob"),
                   "status": "silenced",
                   "silenced_until": (datetime.now(tz=timezone.utc) - timedelta(hours=1)).isoformat(),
                   "count": 5, "threshold": 10, "history": [],
                   "note": "", "ack_by": None, "ack_at": None,
                   "closed_by": None, "closed_at": None, "severity": "low"}
        incidents = [expired]
        with patch("backend.api.workspace_shared._incidents._append_incident_history"):
            r = _scan_incidents_from_anomalies(
                {"actor_spikes": [{"actor": "bob", "count": 20}], "action_spikes": []},
                incidents=incidents, actor_threshold=10, action_threshold=20,
            )
        assert r["updated"] == 1
        assert expired["status"] == "open"
