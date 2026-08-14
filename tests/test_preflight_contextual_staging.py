"""Preflight seguro de staging/producción — contratos de seguridad.

Reconstruido desde su bytecode (restauración de trabajo perdido): valida que
local permita la BD por defecto, que staging exija identidad externa + E2E,
que bloquee credenciales embebidas y variables ambiguas, y que producción
exija ack/approval/backup explícitos.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "preflight_contextual_staging.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("preflight_ctx_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # @dataclass requiere el módulo registrado
    spec.loader.exec_module(module)
    return module


def _clear(monkeypatch):
    for key in (
        "ENV",
        "ENVIRONMENT",
        "DATABASE_URL",
        "STAGING_DATABASE_URL",
        "CCF_APPROVED_ENV_FILE",
        "CCF_STAGING_BACKUP_VERIFIED",
        "CCF_PRODUCTION_CHANGE_APPROVED",
        "CCF_PRODUCTION_BACKUP_VERIFIED",
        "E2E_AUTH_ENABLED",
        "E2E_EMAIL",
        "E2E_PASSWORD",
        "E2E_API_URL",
        "NEXT_PUBLIC_API_URL",
    ):
        monkeypatch.delenv(key, raising=False)


def _identity(tmp_path, target: str = "staging") -> str:
    """Escribe la identidad aprobada y devuelve su path."""
    data = {
        "target": target,
        "db_host": "staging-db.example",
        "db_name": "ccf_staging",
        "base_url": "https://staging.example",
    }
    path = tmp_path / f"identity-{target}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def test_local_allows_default_database(monkeypatch):
    """Local no requiere DATABASE_URL ni identidad externa."""
    mod = _load_module()
    _clear(monkeypatch)
    monkeypatch.setenv("ENV", "local")
    checks, _ = mod._check_common("local")
    assert all(c.ok for c in checks)


def test_staging_requires_external_identity_and_e2e(monkeypatch, tmp_path):
    """Staging pasa solo con identidad aprobada + backup + E2E consistente."""
    mod = _load_module()
    _clear(monkeypatch)
    monkeypatch.setenv("ENV", "staging")
    monkeypatch.setenv("DATABASE_URL", "postgresql://staging-db.example:5432/ccf_staging")
    monkeypatch.setenv("CCF_APPROVED_ENV_FILE", _identity(tmp_path, "staging"))
    monkeypatch.setenv("CCF_STAGING_BACKUP_VERIFIED", "1")
    monkeypatch.setenv("E2E_AUTH_ENABLED", "1")
    monkeypatch.setenv("E2E_EMAIL", "e2e@example.invalid")
    monkeypatch.setenv("E2E_PASSWORD", "not-real")
    monkeypatch.setenv("E2E_API_URL", "https://staging.example/api")
    monkeypatch.setenv("NEXT_PUBLIC_API_URL", "https://staging.example/api")
    checks = mod._check_staging()
    assert all(c.ok for c in checks)


def test_staging_blocks_database_credentials_and_wrong_identity(monkeypatch, tmp_path):
    """Credenciales embebidas y host/DB fuera de la identidad → bloqueo."""
    mod = _load_module()
    _clear(monkeypatch)
    monkeypatch.setenv("ENV", "staging")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://user:secret@production.example:5432/ccf_production"
    )
    monkeypatch.setenv("CCF_APPROVED_ENV_FILE", _identity(tmp_path, "staging"))
    checks = mod._check_staging()
    by_name = {c.name: c for c in checks}
    assert not by_name["database URL has no embedded credentials"].ok
    assert not by_name["approved staging DB host"].ok
    assert not by_name["approved staging DB name"].ok


def test_staging_blocks_ambiguous_database_variables(monkeypatch, tmp_path):
    """DATABASE_URL + STAGING_DATABASE_URL a la vez → ambigüedad bloqueada."""
    mod = _load_module()
    _clear(monkeypatch)
    monkeypatch.setenv("ENV", "staging")
    monkeypatch.setenv("DATABASE_URL", "postgresql://staging-db.example:5432/ccf_staging")
    monkeypatch.setenv("STAGING_DATABASE_URL", "postgresql://other.example:5432/other")
    monkeypatch.setenv("CCF_APPROVED_ENV_FILE", _identity(tmp_path, "staging"))
    checks = mod._check_staging()
    by_name = {c.name: c for c in checks}
    assert not by_name["database variable ambiguity"].ok


def test_production_requires_external_identity_ack_approval_and_backup(monkeypatch, tmp_path):
    """Producción exige ack CLI + CCF_PRODUCTION_CHANGE_APPROVED + backup."""
    mod = _load_module()
    _clear(monkeypatch)
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://production-db.example:5432/ccf_production")
    monkeypatch.setenv("CCF_APPROVED_ENV_FILE", _identity(tmp_path, "production"))
    checks = mod._check_production(ack=False)
    by_name = {c.name: c for c in checks}
    assert not by_name["explicit production acknowledgement"].ok
    assert not by_name["production approval"].ok
    assert not by_name["production backup verified"].ok

    monkeypatch.setenv("CCF_PRODUCTION_CHANGE_APPROVED", "1")
    monkeypatch.setenv("CCF_PRODUCTION_BACKUP_VERIFIED", "1")
    checks = mod._check_production(ack=True)
    by_name = {c.name: c for c in checks}
    assert by_name["explicit production acknowledgement"].ok
    assert by_name["production approval"].ok
    assert by_name["production backup verified"].ok
