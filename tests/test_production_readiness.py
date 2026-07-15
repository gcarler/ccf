from scripts.auditing.production_readiness import (
    Check,
    ModuleReadiness,
    markdown_report,
    runtime_supervision_checks,
    serialize_report,
)


def test_module_readiness_status_and_score_are_deterministic():
    module = ModuleReadiness(
        "cms",
        "CMS",
        [
            Check("a", "OK", "ok"),
            Check("b", "WARN", "warn"),
            Check("c", "FAIL", "fail"),
        ],
    )

    assert module.status == "FAIL"
    assert module.score == 50


def test_report_serialization_marks_warnings_without_failing_everything():
    modules = [
        ModuleReadiness("runtime", "Runtime", [Check("health", "OK", "200")]),
        ModuleReadiness("backups", "Backups", [Check("backup", "WARN", "old")]),
    ]

    report = serialize_report(modules, "https://example.test")

    assert report["status"] == "WARN"
    assert report["score"] == 75
    assert report["modules"][0]["checks"][0]["name"] == "health"


def test_markdown_report_contains_module_check_table():
    report = serialize_report(
        [ModuleReadiness("public", "Public", [Check("home", "OK", "HTTP 200")])],
        "https://example.test",
    )

    markdown = markdown_report(report)

    assert "# CCF Production Readiness Report" in markdown
    assert "## Public - OK (100%)" in markdown
    assert "| home | OK | HTTP 200 |" in markdown


def test_runtime_supervision_is_non_blocking_when_pm2_is_empty(monkeypatch):
    monkeypatch.setattr(
        "scripts.auditing.production_readiness.run_command",
        lambda command, timeout=20: (0, "[]"),
    )

    checks = runtime_supervision_checks()

    assert len(checks) == 1
    assert checks[0].status == "OK"
    assert "PM2 no registra procesos" in checks[0].detail
