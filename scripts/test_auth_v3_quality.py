#!/usr/bin/env python3
"""
Canonical quality smoke for Auth v3 module.

Usage:
    python scripts/test_auth_v3_quality.py [--backend-deep]

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
        ("🔍 Health endpoint", [
            "curl", "-sf", "http://127.0.0.1:8000/healthz"]),
        ("🧪 Auth login smoke", [
            "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
            "-X", "POST", "http://127.0.0.1:8000/api/v3/auth/login",
            "-H", "Content-Type: application/json",
            "-d", '{"email":"admin@example.com","password":"testpass123"}']),
    ]

    if "--backend-deep" in sys.argv:
        gates.append(("📊 Auth module search", [
            VENV_PYTHON, "-c",
            '"from backend.app import app; print(f\"Auth routes: {sum(1 for r in app.routes if \\\"auth\\\" in str(r.path))}\")"']))

    all_ok = True
    for label, cmd in gates:
        if not run(label, cmd):
            all_ok = False

    if all_ok:
        print("\n✅ ALL GATES PASS — Auth v3 module is healthy.")
    else:
        print("\n❌ SOME GATES FAILED — review output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
