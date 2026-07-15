from scripts.auditing.production_readiness import (
    Check,
    ModuleReadiness,
    check_next_static_assets,
    extract_next_static_assets,
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


def test_extract_next_static_assets_deduplicates_and_sorts():
    html = """
        <link rel="stylesheet" href="/_next/static/css/b.css">
        <script src="/_next/static/chunks/a.js"></script>
        <link rel="preload" href="/_next/static/css/b.css">
    """

    assert extract_next_static_assets(html) == [
        "/_next/static/chunks/a.js",
        "/_next/static/css/b.css",
    ]


def test_next_static_asset_check_reports_missing_assets(monkeypatch):
    monkeypatch.setattr(
        "scripts.auditing.production_readiness.http_get",
        lambda url, timeout=8: (
            200,
            "OK",
            '<link rel="stylesheet" href="/_next/static/css/a.css">'
            '<script src="/_next/static/chunks/app.js"></script>',
        ),
    )

    def fake_http_status(url, timeout=8):
        return (200, "OK") if url.endswith("a.css") else (404, "Not Found")

    monkeypatch.setattr("scripts.auditing.production_readiness.http_status", fake_http_status)

    check = check_next_static_assets("Evangelism assets", "https://example.test/plataforma/evangelism")

    assert check.status == "FAIL"
    assert "/_next/static/chunks/app.js" in check.detail
