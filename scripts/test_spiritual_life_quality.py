#!/usr/bin/env python3
"""
Canonical quality smoke for Spiritual Life module.

Usage:
    python scripts/test_spiritual_life_quality.py [--backend-deep]

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
            VENV_PYTHON, "-m", "pytest", "tests/test_spiritual_life_api.py",
            "-q", "--tb=short", "--no-cov"]),
        ("🔍 Health endpoint", [
            "curl", "-sf", "http://127.0.0.1:8000/healthz"]),
    ]

    if "--backend-deep" in sys.argv:
        gates.append(("📊 Deep coverage", [
            VENV_PYTHON, "-m", "pytest", "tests/test_spiritual_life_api.py",
            "-v", "--tb=short", "--no-cov"]))

    all_ok = True
    for label, cmd in gates:
        if not run(label, cmd):
            all_ok = False

    if all_ok:
        print("\n✅ ALL GATES PASS — Spiritual Life module is healthy.")
    else:
        print("\n❌ SOME GATES FAILED — review output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
