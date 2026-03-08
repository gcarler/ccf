from pathlib import Path

import pytest

from backend.analytics import event_sink, queries


@pytest.fixture(autouse=True)
def temp_analytics_db(tmp_path, monkeypatch):
    db_path = tmp_path / "warehouse.duckdb"
    monkeypatch.setattr(event_sink, "WAREHOUSE_PATH", db_path)
    monkeypatch.setattr(queries, "WAREHOUSE_PATH", db_path)
    yield
    if db_path.exists():
        db_path.unlink()


def test_event_persistence_and_summary():
    event_sink.persist_event("EnrollmentCreated", {"course_id": 1, "user_id": 10})
    event_sink.persist_event("AssessmentSubmitted", {"course_id": 1, "passed": True})
    event_sink.persist_event("CertificateIssued", {"course_id": 1})

    summary = queries.get_event_summary(days=30)
    assert summary["total_events"] == 3
    assert any(item["event_name"] == "EnrollmentCreated" for item in summary["by_event"])

    course_stats = queries.get_course_performance()
    assert course_stats[0]["course_id"] == 1
    assert course_stats[0]["enrollments"] >= 1

    raw = queries.list_raw_events(limit=2)
    assert len(raw) == 2
