"""CLI del preflight contextual — bloqueo de staging y no-fuga de contraseñas.

Reconstruido desde su bytecode (restauración de trabajo perdido): la CLI
bloquea staging sin configuración aprobada, pasa en local sin DATABASE_URL
y nunca imprime contraseñas de BD.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "preflight_contextual_staging.py"


def _run(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    full_env = {**os.environ, **env}
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        env=full_env,
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=60,
    )


def test_cli_blocks_staging_without_approved_configuration():
    result = _run(["--target", "staging"], {"ENV": "staging"})
    assert result.returncode != 0
    assert "Preflight bloqueado" in result.stderr


def test_cli_passes_local_without_database_url():
    result = _run(["--target", "local"], {"ENV": "local"})
    assert result.returncode == 0
    assert "Preflight aprobado" in result.stdout


def test_cli_never_prints_database_password():
    password = "super-secret-password-xyz"
    result = _run(
        ["--target", "local"],
        {
            "ENV": "local",
            "DATABASE_URL": f"postgresql://user:{password}@localhost:5432/ccf_db",
        },
    )
    assert result.returncode == 0
    combined = result.stdout + result.stderr
    assert password not in combined
