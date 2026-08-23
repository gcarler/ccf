"""Contrato común de entorno para suites de calidad de integración.

Las pruebas unitarias pueden seguir usando SQLite mediante ``TEST_DATABASE_URL``.
Las suites que llaman una API HTTP deben declarar explícitamente la misma base
y API con ``QUALITY_DATABASE_URL`` y ``QUALITY_API_URL``. Esto evita que una
suite escriba en una base y consulte otra.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit


class QualityEnvironmentError(RuntimeError):
    """El entorno de integración no cumple el contrato mínimo."""


def _without_credentials(url: str) -> str:
    parsed = urlsplit(url)
    if not parsed.username and not parsed.password:
        return url
    host = parsed.hostname or ""
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme, host, parsed.path, parsed.query, parsed.fragment))


@dataclass(frozen=True)
class QualityEnvironment:
    database_url: str
    api_url: str
    run_id: str

    @classmethod
    def from_process(cls, *, require_api: bool = True) -> "QualityEnvironment":
        database_url = (os.environ.get("QUALITY_DATABASE_URL") or "").strip()
        api_url = (os.environ.get("QUALITY_API_URL") or "").strip().rstrip("/")
        run_id = (os.environ.get("QUALITY_RUN_ID") or "").strip()

        missing = []
        if not database_url:
            missing.append("QUALITY_DATABASE_URL")
        if require_api and not api_url:
            missing.append("QUALITY_API_URL")
        if missing:
            raise QualityEnvironmentError(
                "Faltan variables del entorno de integración: "
                + ", ".join(missing)
                + ". Usa scripts/run_quality_integration.py para provisionarlas."
            )

        if not run_id:
            raise QualityEnvironmentError(
                "Falta QUALITY_RUN_ID; cada ejecución debe tener un identificador aislado."
            )

        if not database_url.startswith(("postgresql://", "postgresql+psycopg2://")):
            raise QualityEnvironmentError(
                "QUALITY_DATABASE_URL debe apuntar a PostgreSQL para pruebas de integración; "
                "SQLite queda reservado para pruebas unitarias."
            )

        return cls(database_url=database_url, api_url=api_url, run_id=run_id)

    def describe(self) -> str:
        return (
            f"run_id={self.run_id} "
            f"database={_without_credentials(self.database_url)} "
            f"api={self.api_url or '<no requerida>'}"
        )

    def child_environment(self) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "DATABASE_URL": self.database_url,
                "database_url": self.database_url,
                "QUALITY_DATABASE_URL": self.database_url,
                "QUALITY_API_URL": self.api_url,
                "QUALITY_RUN_ID": self.run_id,
            }
        )
        return env
