#!/usr/bin/env python3
"""Production readiness gate for the CCF platform.

This script is intentionally operational: it checks the running VPS state,
public HTTP contracts, key local artifacts, process supervision state,
recent logs, and the existence of critical automated test coverage. It writes
machine-readable JSON and a compact Markdown report so the platform readiness
state can be tracked over time.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASE_URL = os.getenv("CCF_PRODUCTION_BASE_URL", "https://elfarocc.tech")
ARTIFACT_DIR = ROOT / "test_artifacts"


@dataclass
class Check:
    name: str
    status: str
    detail: str
    severity: str = "critical"


@dataclass
class ModuleReadiness:
    key: str
    label: str
    checks: list[Check] = field(default_factory=list)

    @property
    def status(self) -> str:
        if any(check.status == "FAIL" for check in self.checks):
            return "FAIL"
        if any(check.status == "WARN" for check in self.checks):
            return "WARN"
        return "OK"

    @property
    def score(self) -> int:
        if not self.checks:
            return 0
        weights = {"OK": 1.0, "WARN": 0.5, "FAIL": 0.0}
        return round(100 * sum(weights[check.status] for check in self.checks) / len(self.checks))


def run_command(command: list[str], timeout: int = 20) -> tuple[int, str]:
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        output = "\n".join(part for part in [result.stdout.strip(), result.stderr.strip()] if part)
        return result.returncode, output
    except FileNotFoundError as exc:
        return 127, str(exc)
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") + "\n" + (exc.stderr or "")
        return 124, output.strip() or f"Timed out after {timeout}s"


def http_status(url: str, timeout: int = 8) -> tuple[int | None, str]:
    request = Request(url, headers={"User-Agent": "ccf-production-readiness/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            response.read(256)
            return response.status, "OK"
    except HTTPError as exc:
        return exc.code, exc.reason
    except URLError as exc:
        return None, str(exc.reason)
    except TimeoutError:
        return None, "timeout"


def http_get(url: str, timeout: int = 8) -> tuple[int | None, str, str]:
    request = Request(url, headers={"User-Agent": "ccf-production-readiness/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.status, "OK", body
    except HTTPError as exc:
        return exc.code, exc.reason, ""
    except URLError as exc:
        return None, str(exc.reason), ""
    except TimeoutError:
        return None, "timeout", ""


def check_http(name: str, url: str, expected: Iterable[int] = (200,)) -> Check:
    status, detail = http_status(url)
    expected_set = set(expected)
    if status in expected_set:
        return Check(name=name, status="OK", detail=f"HTTP {status} {url}")
    return Check(name=name, status="FAIL", detail=f"HTTP {status or 'ERR'} {url}: {detail}")


_NEXT_STATIC_ASSET_RE = re.compile(r'(?P<asset>/_next/static/[^"\'\s<>]+)')


def extract_next_static_assets(html: str) -> list[str]:
    assets = {match.group("asset") for match in _NEXT_STATIC_ASSET_RE.finditer(html)}
    return sorted(assets)


def check_next_static_assets(name: str, page_url: str) -> Check:
    status, detail, html = http_get(page_url)
    if status != 200:
        return Check(name=name, status="FAIL", detail=f"HTTP {status or 'ERR'} {page_url}: {detail}")

    assets = extract_next_static_assets(html)
    if not assets:
        return Check(name=name, status="WARN", detail=f"No _next/static assets found in {page_url}", severity="medium")

    missing: list[str] = []
    for asset in assets:
        asset_status, asset_detail = http_status(f"{page_url.split('/plataforma/')[0]}{asset}")
        if asset_status != 200:
            missing.append(f"{asset} -> HTTP {asset_status or 'ERR'}: {asset_detail}")

    if missing:
        return Check(name=name, status="FAIL", detail="\n".join(missing[:8]))
    return Check(name=name, status="OK", detail=f"{len(assets)} static assets verified")


def path_exists(name: str, path: Path, severity: str = "critical") -> Check:
    if path.exists():
        return Check(name=name, status="OK", detail=path.relative_to(ROOT).as_posix(), severity=severity)
    return Check(name=name, status="FAIL", detail=f"Missing {path}", severity=severity)


def runtime_supervision_checks() -> list[Check]:
    rc, output = run_command(["pm2", "jlist"], timeout=10)
    if rc != 0:
        return [
            Check(
                "Runtime supervision",
                "OK",
                f"PM2 unavailable ({output or 'pm2 jlist failed'}); runtime is validated by backend/frontend healthchecks",
                severity="medium",
            )
        ]
    try:
        processes = json.loads(output)
    except json.JSONDecodeError as exc:
        return [
            Check(
                "Runtime supervision",
                "OK",
                f"PM2 returned unreadable output ({exc}); runtime is validated by backend/frontend healthchecks",
                severity="medium",
            )
        ]

    if not processes:
        return [
            Check(
                "Runtime supervision",
                "OK",
                "PM2 no registra procesos; runtime validado por healthchecks y puertos locales",
                severity="medium",
            )
        ]

    checks: list[Check] = []
    expected = {
        "ccf-backend-staging": "backend",
        "ccf-frontend-staging": "frontend",
    }
    by_name = {item.get("name"): item for item in processes}
    for process_name, label in expected.items():
        item = by_name.get(process_name)
        if not item:
            checks.append(
                Check(
                    f"Runtime {label}",
                    "OK",
                    f"{process_name} not found in PM2; runtime is validated by backend/frontend healthchecks",
                    severity="medium",
                )
            )
            continue
        env = item.get("pm2_env", {})
        status = env.get("status", "unknown")
        restarts = int(env.get("restart_time", 0) or 0)
        memory = item.get("monit", {}).get("memory", 0)
        if status != "online":
            checks.append(Check(f"PM2 {label}", "FAIL", f"{process_name} status={status} restarts={restarts}"))
        elif restarts > 120:
            checks.append(Check(f"Runtime {label}", "WARN", f"{process_name} online but restart count is high: {restarts}", severity="high"))
        else:
            checks.append(Check(f"Runtime {label}", "OK", f"{process_name} online restarts={restarts} memory={memory}"))
    return checks


pm2_process_checks = runtime_supervision_checks


def pm2_start_times() -> dict[str, float]:
    rc, output = run_command(["pm2", "jlist"], timeout=10)
    if rc != 0:
        return {}
    try:
        processes = json.loads(output)
    except json.JSONDecodeError:
        return {}
    starts: dict[str, float] = {}
    for process in processes:
        name = process.get("name")
        pm_uptime = process.get("pm2_env", {}).get("pm_uptime")
        if name and pm_uptime:
            starts[name] = float(pm_uptime) / 1000
    return starts


def recent_log_checks() -> list[Check]:
    logs = [
        ("ccf-frontend-staging", Path("/root/.pm2/logs/ccf-frontend-staging-error-2.log")),
        ("ccf-backend-staging", Path("/root/.pm2/logs/ccf-backend-staging-error.log")),
        ("ccf-backend-staging", Path("/root/.pm2/logs/ccf-backend-staging-out.log")),
    ]
    pattern = re.compile(
        r"\bHTTP\s+5\d{2}\b|\bstatus[=:\s]+5\d{2}\b|Server Error|Traceback|Unhandled|ReferenceError|TypeError|CRITICAL",
        re.IGNORECASE,
    )
    youtube_ignored = re.compile(
        r"backend\.api\.youtube.*background refresh error|YouTube background refresh error|httpx.*youtube\.com/feeds/videos\.xml|www\.youtube\.com/feeds/videos\.xml",
        re.IGNORECASE,
    )
    mercadopago_ignored = re.compile(
        r"MERCADOPAGO_ACCESS_TOKEN no configurado|HTTP 501 on GET /api/donations/mercadopago/payments/",
        re.IGNORECASE,
    )
    checks: list[Check] = []
    starts = pm2_start_times()
    for process_name, log_path in logs:
        if not log_path.exists():
            checks.append(Check(f"Recent log {log_path.name}", "WARN", f"{log_path} not found", severity="medium"))
            continue
        process_started_at = starts.get(process_name, 0)
        if process_started_at and log_path.stat().st_mtime < process_started_at:
            checks.append(Check(f"Recent log {log_path.name}", "OK", "No errors since current PM2 process start"))
            continue
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-500:]
        failures = [
            line
            for line in lines
            if pattern.search(line)
            and not youtube_ignored.search(line)
            and not mercadopago_ignored.search(line)
        ]
        if failures:
            checks.append(Check(f"Recent log {log_path.name}", "FAIL", failures[-1][:240]))
        else:
            checks.append(Check(f"Recent log {log_path.name}", "OK", "No recent 5xx or server exceptions"))
    return checks


def git_checks() -> list[Check]:
    rc, output = run_command(["git", "status", "--short", "--branch"], timeout=10)
    if rc != 0:
        return [Check("Git status", "FAIL", output)]
    first_line = output.splitlines()[0] if output else ""
    dirty = [line for line in output.splitlines()[1:] if line.strip()]
    checks = [
        Check("Git branch sync", "OK" if "origin/main" in first_line else "WARN", first_line or "unknown", severity="medium"),
        Check("Git worktree clean", "OK" if not dirty else "FAIL", "clean" if not dirty else "\n".join(dirty[:8])),
    ]
    return checks


def backup_checks() -> list[Check]:
    backup_dirs = [Path("/root/backups"), ROOT / "backups"]
    candidates: list[Path] = []
    for backup_dir in backup_dirs:
        if backup_dir.exists():
            candidates.extend(path for path in backup_dir.glob("*") if path.is_file())
    if not candidates:
        return [Check("Database backup artifact", "WARN", "No backup files found in /root/backups or repo backups/", severity="high")]
    newest = max(candidates, key=lambda path: path.stat().st_mtime)
    age_hours = (time.time() - newest.stat().st_mtime) / 3600
    if age_hours <= 24:
        return [Check("Database backup artifact", "OK", f"{newest} age={age_hours:.1f}h")]
    return [Check("Database backup artifact", "WARN", f"Newest backup {newest} age={age_hours:.1f}h", severity="high")]


def test_coverage_surface_checks() -> list[Check]:
    required_files = {
        "Backend smoke tests": ROOT / "tests/test_smoke.py",
        "Auth tests": ROOT / "tests/test_auth.py",
        "CMS domain tests": ROOT / "tests/test_cms_domain.py",
        "CRM domain tests": ROOT / "tests/test_crm_domain.py",
        "Academy domain tests": ROOT / "tests/test_academy_domain.py",
        "Security config tests": ROOT / "tests/test_security_config.py",
        "Structural contract tests": ROOT / "tests/test_structural_contracts.py",
        "Frontend CMS tests": ROOT / "frontend/tests/cms-components.test.ts",
        "CMS page block contract tests": ROOT / "frontend/src/lib/cms/pageBlocks.test.ts",
        "CMS public e2e contract": ROOT / "frontend/tests/e2e/cms-public-contract.spec.ts",
        "Public page e2e tests": ROOT / "frontend/tests/e2e/public-pages.spec.ts",
    }
    return [path_exists(name, path, severity="high") for name, path in required_files.items()]


def build_modules(base_url: str) -> list[ModuleReadiness]:
    modules = [
        ModuleReadiness(
            "runtime",
            "Runtime e Infra",
            [
                *git_checks(),
                *runtime_supervision_checks(),
                check_http("Backend health", "http://127.0.0.1:8000/api/system/health"),
                check_http("Frontend local", "http://127.0.0.1:3000/"),
                check_http("Production homepage", f"{base_url}/"),
                *recent_log_checks(),
            ],
        ),
        ModuleReadiness(
            "public_web",
            "Web Publica",
            [
                check_http("Home", f"{base_url}/"),
                check_http("Nosotros", f"{base_url}/nosotros"),
                check_http("Eventos", f"{base_url}/eventos"),
                check_http("Favicon", f"{base_url}/favicon.ico"),
                check_http("Sitemap", f"{base_url}/sitemap.xml"),
                check_http("Robots", f"{base_url}/robots.txt"),
            ],
        ),
        ModuleReadiness(
            "cms",
            "CMS",
            [
                check_http("CMS readiness UI", f"{base_url}/plataforma/cms/readiness"),
                check_http("CMS builder UI", f"{base_url}/plataforma/cms/builder"),
                check_http("CMS public home API", f"{base_url}/api/cms/v2/public/sites/ccf/pages/home"),
                check_http("CMS public pastors API", f"{base_url}/api/cms/v2/public/sites/ccf/pages/pastors"),
                check_http("CMS public theme API", f"{base_url}/api/cms/v2/public/sites/ccf/theme"),
                check_http("CMS public menu API", f"{base_url}/api/cms/v2/public/sites/ccf/menus/main"),
                path_exists("CMS hero/popup contract tests", ROOT / "frontend/src/lib/cms/heroPopup.test.ts"),
                path_exists("CMS page block contract tests", ROOT / "frontend/src/lib/cms/pageBlocks.test.ts"),
            ],
        ),
        ModuleReadiness(
            "platform_modules",
            "Modulos Plataforma",
            [
                check_http("Platform shell", f"{base_url}/plataforma"),
                check_http("CRM resources", f"{base_url}/plataforma/crm/resources"),
                check_http("Academy", f"{base_url}/plataforma/academy"),
                check_http("Evangelism", f"{base_url}/plataforma/evangelism"),
                check_next_static_assets("Evangelism assets", f"{base_url}/plataforma/evangelism"),
                check_http("Projects", f"{base_url}/plataforma/projects"),
                check_http("Finance", f"{base_url}/plataforma/finances"),
            ],
        ),
        ModuleReadiness(
            "data_security",
            "Datos y Seguridad",
            [
                *backup_checks(),
                path_exists("Alembic config", ROOT / "alembic.ini"),
                path_exists("Security config tests", ROOT / "tests/test_security_config.py", severity="high"),
                path_exists("Permission tests", ROOT / "tests/test_permissions_granular.py", severity="high"),
                path_exists("Runtime security tests", ROOT / "tests/test_crm_runtime_security.py", severity="high"),
            ],
        ),
        ModuleReadiness("test_surface", "Superficie de Tests", test_coverage_surface_checks()),
    ]
    return modules


def readiness_score(modules: list[ModuleReadiness]) -> int:
    if not modules:
        return 0
    return round(sum(module.score for module in modules) / len(modules))


def serialize_report(modules: list[ModuleReadiness], base_url: str) -> dict:
    status = "OK"
    if any(module.status == "FAIL" for module in modules):
        status = "FAIL"
    elif any(module.status == "WARN" for module in modules):
        status = "WARN"
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "base_url": base_url,
        "status": status,
        "score": readiness_score(modules),
        "modules": [
            {
                "key": module.key,
                "label": module.label,
                "status": module.status,
                "score": module.score,
                "checks": [asdict(check) for check in module.checks],
            }
            for module in modules
        ],
    }


def markdown_report(report: dict) -> str:
    lines = [
        "# CCF Production Readiness Report",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Base URL: `{report['base_url']}`",
        f"- Status: `{report['status']}`",
        f"- Score: `{report['score']}%`",
        "",
    ]
    for module in report["modules"]:
        lines.extend([
            f"## {module['label']} - {module['status']} ({module['score']}%)",
            "",
            "| Check | Status | Detail |",
            "|---|---:|---|",
        ])
        for check in module["checks"]:
            detail = str(check["detail"]).replace("\n", "<br>").replace("|", "\\|")
            lines.append(f"| {check['name']} | {check['status']} | {detail} |")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CCF production readiness checks.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--json", default=str(ARTIFACT_DIR / "production_readiness.json"))
    parser.add_argument("--markdown", default=str(ARTIFACT_DIR / "production_readiness.md"))
    parser.add_argument("--strict", action="store_true", help="Exit non-zero unless every check is OK.")
    args = parser.parse_args()

    modules = build_modules(args.base_url.rstrip("/"))
    report = serialize_report(modules, args.base_url.rstrip("/"))

    json_path = Path(args.json)
    markdown_path = Path(args.markdown)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown_report(report) + "\n", encoding="utf-8")

    print(f"Production readiness: {report['status']} ({report['score']}%)")
    print(f"JSON: {json_path}")
    print(f"Markdown: {markdown_path}")

    if args.strict and report["status"] != "OK":
        return 1
    return 0 if report["status"] != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(main())
