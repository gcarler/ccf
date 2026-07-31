"""
Unit tests for evangelism_shared.py — working pure functions.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from backend.api import evangelism_shared as shared


class TestAttendanceStatus:
    def test_attended(self):
        assert shared.is_attended_status("ASISTIO") is True
        assert shared.is_attended_status("AUSENTE") is False

    def test_absent(self):
        assert shared.is_absent_status("AUSENTE") is True
        assert shared.is_absent_status("ASISTIO") is False


class TestUtcNow:
    def test_returns_datetime(self):
        assert shared.utc_now().tzinfo is not None


class TestParseSessionDate:
    def test_from_datetime(self):
        assert shared.parse_session_date(datetime(2026, 6, 15, tzinfo=timezone.utc)) == date(2026, 6, 15)

    def test_from_date(self):
        assert shared.parse_session_date(date(2026, 6, 15)) == date(2026, 6, 15)

    def test_from_string(self):
        assert shared.parse_session_date("2026-06-15") == date(2026, 6, 15)

    def test_from_none(self):
        with pytest.raises(Exception):
            shared.parse_session_date(None)
