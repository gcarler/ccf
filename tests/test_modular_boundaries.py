"""Executable contract for the strict modular-monolith boundary baseline."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_modular_boundary_guard_is_clean():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/check_modular_boundaries.py", "--strict"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
