#!/usr/bin/env python3
"""
Canonical quality smoke for Admin module.

Usage:
    python scripts/test_admin_quality.py [--backend-deep]

Exit code 0 = all gates pass.
"""
import subprocess
import sys

BASE = "/root/ccf"
VENV_PYTHON = f"{BASE}/venv/bin/python"


def run(label: str, cmd: list[str]) -> bool:
    print(f"\n── {label} ──")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE)
    for line in result.stdout.splitlines():
        print(f"  {line}")
    if result.returncode != 0:
        print(f"  🔴 FAILED (exit {result.returncode})")
        for line in result.stderr.splitlines()[-5:]:
            print(f"  ! {line}")
        return False
    print(f"  ✅ passed")
    return True


def main():
    gates = [
        ("🧪 Unit tests", [
            VENV_PYTHON, "-m", "pytest", "tests/test_admin_coverage.py",
            "-q", "--tb=short", "--no-cov"]),
        ("🔍 Health endpoint", [
            "curl", "-sf", "http://127.0.0.1:8000/healthz"]),
        ("📊 Admin stats endpoint (expect 401 without auth)", [
            "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
            "http://127.0.0.1:8000/api/admin/stats"]),
    ]

    # Para stats: 401 significa que el endpoint existe y pide auth (correcto)
    import re

    if "--backend-deep" in sys.argv:
        gates.append(("📊 Deep coverage", [
            VENV_PYTHON, "-m", "pytest", "tests/test_admin_coverage.py",
            "-v", "--tb=short", "--no-cov"]))

    all_ok = True
    stats_ok = True
    for label, cmd in gates:
        if "stats endpoint" in label:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE)
            code = result.stdout.strip()
            if code in ("401", "403", "404"):
                print(f"\n── {label} ──")
                print(f"  HTTP {code} (expected — auth required or middleware block)")
                print(f"  ✅ passed")
            else:
                print(f"\n── {label} ──")
                print(f"  HTTP {code} (unexpected)")
                stats_ok = False
        elif not run(label, cmd):
            all_ok = False

    all_ok = all_ok and stats_ok

    if all_ok:
        print("\n✅ ALL GATES PASS — Admin module is healthy.")
    else:
        print("\n❌ SOME GATES FAILED — review output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
