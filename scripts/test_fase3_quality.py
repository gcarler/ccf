#!/usr/bin/env python3
"""
Canonical quality smoke for Fase 3 modules (lightweight).

Usage:
    python scripts/test_fase3_quality.py

Exit code 0 = all gates pass.
"""
import subprocess
import sys

BASE = "/root/ccf"
VENV_PYTHON = f"{BASE}/venv/bin/python"

MODULES = {
    "Support": "tests/test_support_tables_api.py",
    "Donations": "tests/test_donations_api.py",
    "Agents": "tests/test_agents.py",
    "Graph": "tests/test_graph_api.py",
    "Enterprise CMS": "tests/test_enterprise_cms.py",
}


def run(label: str, cmd: list[str]) -> bool:
    print(f"\n── {label} ──")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE)
    for line in result.stdout.splitlines():
        print(f"  {line}")
    if result.returncode != 0:
        print(f"  🔴 FAILED (exit {result.returncode})")
        for line in result.stderr.splitlines()[-3:]:
            print(f"  ! {line}")
        return False
    print(f"  ✅ passed")
    return True


def main():
    gates = [("🔍 Health endpoint", ["curl", "-sf", "http://127.0.0.1:8000/healthz"])]

    for name, testfile in MODULES.items():
        gates.append((f"🧪 {name}", [
            VENV_PYTHON, "-m", "pytest", testfile, "-q", "--tb=short", "--no-cov"]))

    all_ok = True
    for label, cmd in gates:
        if not run(label, cmd):
            all_ok = False

    if all_ok:
        print("\n✅ ALL GATES PASS — Fase 3 modules healthy.")
    else:
        print("\n❌ SOME GATES FAILED — review output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
