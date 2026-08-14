"""Preflight seguro para el despliegue del clasificador contextual.

No modifica la base, no crea usuarios y no ejecuta migraciones. Detecta
configuraciones incompletas o ambiguas antes de operar staging/producción.

Para entornos protegidos, ``CCF_APPROVED_ENV_FILE`` debe apuntar a un archivo
fuera del repositorio, gestionado por operaciones/secret manager, con esta
forma (sin contraseñas):

{
  "target": "staging",
  "db_host": "staging-db.example",
  "db_name": "ccf_staging",
  "base_url": "https://staging.example"
}

Uso:
    ENV=local python scripts/preflight_contextual_staging.py --target local
    ENV=staging CCF_APPROVED_ENV_FILE=/etc/ccf/staging-identity.json \
      CCF_STAGING_BACKUP_VERIFIED=1 E2E_AUTH_ENABLED=1 \
      E2E_EMAIL=... E2E_PASSWORD=... E2E_API_URL=... \
      NEXT_PUBLIC_API_URL=... \
      python scripts/preflight_contextual_staging.py --target staging
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Check:
    """Resultado de una condición de preflight."""

    name: str
    ok: bool
    detail: str


LOCAL_ENVS = frozenset({"", "testing", "local", "test", "ci"})
PROTECTED_ENVS = frozenset({"production", "staging"})
POSTGRES_SCHEMES = frozenset({"postgresql", "postgresql+psycopg2", "postgres"})
IDENTITY_KEYS = frozenset({"target", "db_host", "db_name", "base_url"})


def _database_parts(value: str):
    """Retorna (scheme, host, database, has_credentials) de una URL de BD.

    Nunca retorna la contraseña. ``has_credentials`` es True si la URL lleva
    username o password embebidos (prohibido para staging/producción: se usa
    ``.pgpass`` o un secret manager).
    """
    if not value:
        return ("", "", "", False)
    parsed = urlsplit(value)
    return (
        parsed.scheme.lower(),
        (parsed.hostname or "").lower(),
        (parsed.path or "").lstrip("/").lower(),
        bool(parsed.username or parsed.password),
    )


def _configured_database():
    """Resuelve (DATABASE_URL o STAGING_DATABASE_URL, checks de ambigüedad).

    Fija una sola fuente de verdad: tener ambas variables es ambiguo y se
    bloquea (podrían apuntar a entornos distintos).
    """
    database_url = os.getenv("DATABASE_URL")
    staging_url = os.getenv("STAGING_DATABASE_URL")
    checks: list[Check] = []
    if database_url and staging_url:
        checks.append(
            Check(
                "database variable ambiguity",
                False,
                "set only DATABASE_URL or STAGING_DATABASE_URL, not both",
            )
        )
    selected = database_url or staging_url or ""
    return selected, checks


def _load_approved_identity():
    """Carga la identidad externa aprobada (``CCF_APPROVED_ENV_FILE``).

    Returns ``(identity, checks)``. El archivo vive FUERA del repositorio
    (secret manager / ops) y nunca contiene contraseñas; valida que tenga
    ``target``, ``db_host``, ``db_name`` y ``base_url``.
    """
    path_value = os.getenv("CCF_APPROVED_ENV_FILE")
    if not path_value:
        return {}, [
            Check(
                "approved environment identity",
                False,
                "CCF_APPROVED_ENV_FILE is required outside local",
            )
        ]
    path = Path(path_value)
    if not path.is_file():
        return {}, [
            Check(
                "approved environment identity",
                False,
                f"identity file does not exist: {path}",
            )
        ]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [
            Check(
                "approved environment identity",
                False,
                f"identity file unreadable: {type(exc).__name__}",
            )
        ]
    if not IDENTITY_KEYS.issubset(data):
        return {}, [
            Check(
                "approved environment identity",
                False,
                "identity file lacks target/db_host/db_name/base_url",
            )
        ]
    identity = {key: str(data[key]).strip() for key in IDENTITY_KEYS}
    return identity, [
        Check("approved environment identity", True, "external identity file loaded")
    ]


def _check_common(target: str) -> tuple[list[Check], str]:
    """Checks comunes: entorno, DB configurada, Postgres y sin credenciales.

    Returns ``(checks, database_url)`` para que los checks por entorno
    reutilicen la URL ya resuelta sin volver a invocar ``_configured_database``
    (evita duplicar el check de ambigüedad en la salida).
    """
    env = (os.getenv("ENV") or os.getenv("ENVIRONMENT") or "").strip().lower()
    database_url, checks = _configured_database()
    scheme, db_host, db_name, has_credentials = _database_parts(database_url)

    if target == "local":
        expected_env = set(LOCAL_ENVS)
    else:
        expected_env = target
    env_ok = env in expected_env if isinstance(expected_env, set) else env == expected_env

    checks.extend(
        [
            Check(
                "environment",
                env_ok,
                f"ENV/ENVIRONMENT={env or '<absent>'}; expected={target}",
            ),
            Check(
                "database configured",
                bool(database_url) or target == "local",
                f"driver={scheme or '<default>'} host={db_host or '<default>'} "
                f"database={db_name or '<default>'}",
            ),
        ]
    )

    if target in PROTECTED_ENVS:
        checks.extend(
            [
                Check(
                    "postgresql required",
                    scheme in POSTGRES_SCHEMES,
                    f"driver={scheme or '<absent>'}",
                ),
                Check(
                    "database URL has no embedded credentials",
                    not has_credentials,
                    "use .pgpass or a secret manager",
                ),
            ]
        )

    return checks, database_url


def _check_staging() -> list[Check]:
    """Checks de staging: identidad aprobada, backup verificado y E2E aislado."""
    checks, database_url = _check_common("staging")
    _, db_host, db_name, _ = _database_parts(database_url)

    identity, identity_checks = _load_approved_identity()
    checks.extend(identity_checks)

    if identity:
        checks.extend(
            [
                Check(
                    "approved staging target",
                    identity.get("target") == "staging",
                    "identity target must be staging",
                ),
                Check(
                    "approved staging DB host",
                    db_host == (identity.get("db_host", "") or "").lower(),
                    "database host matches external identity",
                ),
                Check(
                    "approved staging DB name",
                    db_name == (identity.get("db_name", "") or "").lower(),
                    "database name matches external identity",
                ),
                Check(
                    "approved staging base URL",
                    (identity.get("base_url", "") or "").startswith("https://"),
                    "approved base URL must use HTTPS",
                ),
            ]
        )

    checks.append(
        Check(
            "staging backup verified",
            os.getenv("CCF_STAGING_BACKUP_VERIFIED") == "1",
            "set only after verifying a restorable backup",
        )
    )

    e2e_base = (os.getenv("E2E_API_URL") or "").strip().rstrip("/")
    public_base = (os.getenv("NEXT_PUBLIC_API_URL") or "").strip().rstrip("/")
    e2e_host = urlsplit(e2e_base).hostname or ""
    public_host = urlsplit(public_base).hostname or ""
    approved_host_url = urlsplit((identity.get("base_url", "") or "")).hostname or ""

    checks.extend(
        [
            Check(
                "E2E_AUTH_ENABLED",
                os.getenv("E2E_AUTH_ENABLED") == "1",
                "must equal 1",
            ),
            Check(
                "E2E_EMAIL",
                bool(os.getenv("E2E_EMAIL")),
                "test-only staging user required",
            ),
            Check(
                "E2E_PASSWORD",
                bool(os.getenv("E2E_PASSWORD")),
                "test-only staging password required",
            ),
            Check(
                "E2E_API_URL",
                bool(e2e_host)
                and e2e_base.startswith("https://")
                and e2e_host == approved_host_url,
                "must be HTTPS and use approved staging host",
            ),
            Check(
                "NEXT_PUBLIC_API_URL",
                bool(public_host)
                and public_base.startswith("https://")
                and public_host == approved_host_url,
                "must be HTTPS and use approved staging host",
            ),
            Check(
                "E2E URL consistency",
                bool(e2e_host)
                and e2e_host == public_host
                and public_host == approved_host_url,
                "E2E/API URLs must target the same approved host",
            ),
        ]
    )

    return checks


def _check_production(ack: bool) -> list[Check]:
    """Checks de producción: identidad aprobada + ack/approval/backup explícitos."""
    checks, database_url = _check_common("production")
    _, db_host, db_name, _ = _database_parts(database_url)

    identity, identity_checks = _load_approved_identity()
    checks.extend(identity_checks)

    if identity:
        checks.extend(
            [
                Check(
                    "approved production target",
                    identity.get("target") == "production",
                    "identity target must be production",
                ),
                Check(
                    "approved production DB host",
                    db_host == (identity.get("db_host", "") or "").lower(),
                    "database host matches external identity",
                ),
                Check(
                    "approved production DB name",
                    db_name == (identity.get("db_name", "") or "").lower(),
                    "database name matches external identity",
                ),
            ]
        )

    checks.extend(
        [
            Check(
                "explicit production acknowledgement",
                ack,
                "pass --ack-production only after approved change window",
            ),
            Check(
                "production approval",
                os.getenv("CCF_PRODUCTION_CHANGE_APPROVED") == "1",
                "explicit operational approval required",
            ),
            Check(
                "production backup verified",
                os.getenv("CCF_PRODUCTION_BACKUP_VERIFIED") == "1",
                "set only after verifying a restorable backup",
            ),
        ]
    )

    return checks


def main() -> int:
    """Punto de entrada CLI. Nunca imprime contraseñas ni URLs de BD completas."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target", choices=("local", "staging", "production"), required=True
    )
    parser.add_argument("--ack-production", action="store_true")
    args = parser.parse_args()

    if args.target == "local":
        checks, _ = _check_common("local")
    elif args.target == "staging":
        checks = _check_staging()
    else:
        checks = _check_production(args.ack_production)

    for check in checks:
        status = "PASS" if check.ok else "BLOCK"
        print(f"{status} {check.name}: {check.detail}")

    failed = [check for check in checks if not check.ok]
    if failed:
        print(
            f"\nPreflight bloqueado: {len(failed)} condición(es) no cumplida(s).",
            file=sys.stderr,
        )
        return 1

    print("\nPreflight aprobado. Este comando no ejecutó migraciones ni modificó datos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
