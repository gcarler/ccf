#!/usr/bin/env python3
"""Script de calidad canónico para Messaging / Community.

Uso:
    cd /root/ccf && ./venv/bin/python scripts/test_messaging_quality.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
PROJECT_ROOT = next((p for p in HERE.parents if (p / "backend" / "__init__.py").is_file()), None)
if PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {HERE}")

os.chdir(PROJECT_ROOT)

GREEN = "\033[0;32m"
RED = "\033[0;31m"
BLUE = "\033[0;34m"
NC = "\033[0m"

PASS = 0
FAIL = 0


def section(title: str) -> None:
    print(f"\n{'=' * 64}")
    print(f"  {title}")
    print(f"{'=' * 64}")


def ok(message: str) -> None:
    global PASS
    PASS += 1
    print(f"  {GREEN}✓{NC} {message}")


def fail(message: str) -> None:
    global FAIL
    FAIL += 1
    print(f"  {RED}✗{NC} {message}")


def info(message: str) -> None:
    print(f"  {BLUE}ℹ{NC} {message}")


def run_pytest(label: str, *tests: str) -> bool:
    section(label)
    cmd = [sys.executable, "-m", "pytest", "-q", "-o", "addopts="]
    cmd.extend(tests)
    info("Ejecutando: " + " ".join(tests))
    result = subprocess.run(cmd, cwd=PROJECT_ROOT, text=True, capture_output=True)
    if result.stdout.strip():
        for line in result.stdout.strip().splitlines():
            print(f"    {line}")
    if result.returncode == 0:
        ok(f"{label} OK")
        return True
    fail(f"{label} falló")
    if result.stderr.strip():
        for line in result.stderr.strip().splitlines()[:20]:
            print(f"    {line}")
    return False


def main() -> int:
    section("MESSAGING / COMMUNITY QUALITY")
    info(f"Proyecto: {PROJECT_ROOT}")
    info(f"Python: {sys.executable}")

    core_ok = run_pytest(
        "1. Inbox y notificaciones",
        "tests/test_messaging.py",
        "tests/test_messaging_api.py",
    )

    hardening_ok = run_pytest(
        "2. Isolation y ownership",
        "tests/test_messaging_sede_isolation.py",
        "tests/test_messaging_fase4_owner_and_crud_layer.py",
    )

    chat_ok = run_pytest(
        "3. Chat directo",
        "tests/test_chat_sede_isolation.py",
    )

    section("RESUMEN")
    total = PASS + FAIL
    if core_ok and hardening_ok and chat_ok:
        print(f"  {GREEN}RESUMEN: {PASS} passed, {FAIL} failed, {total} total suites{NC}")
        return 0

    print(f"  {RED}RESUMEN: {PASS} passed, {FAIL} failed, {total} total suites{NC}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
