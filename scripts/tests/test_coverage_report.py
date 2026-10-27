import json
from pathlib import Path

import pytest

from scripts.check_coverage_report import line_coverage


def test_measures_real_summary(tmp_path: Path):
    report = tmp_path / "summary.json"
    report.write_text(json.dumps({"total": {"lines": {"pct": 61.48}}}))
    assert line_coverage(report) == 61.48


@pytest.mark.parametrize("data", [
    {"numTotalTests": 3061, "numPassedTests": 3061},
    {"total": {"lines": {"pct": "61.48"}}},
    {"total": {"lines": {"pct": True}}},
    {"total": {"lines": {"pct": float("nan")}}},
    {"total": {"lines": {"pct": 101}}},
])
def test_rejects_test_reports_and_invalid_measurements(tmp_path: Path, data):
    report = tmp_path / "summary.json"
    report.write_text(json.dumps(data))
    with pytest.raises((KeyError, ValueError)):
        line_coverage(report)
