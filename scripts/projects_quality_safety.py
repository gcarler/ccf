"""Safety checks for the destructive Projects integration smoke."""

from __future__ import annotations

import re

from sqlalchemy.engine import make_url

_DISPOSABLE_DATABASE_NAME = re.compile(r"(?:^|_)(?:e2e|test|quality)(?:_|$)", re.IGNORECASE)


class ProjectsQualityTargetError(RuntimeError):
    """Raised when the Projects smoke target is not explicitly isolated."""


def validate_projects_quality_target(
    *,
    database_url: str,
    quality_database_url: str,
    confirmed_database: str,
    run_id: str,
) -> str:
    """Require an exact, isolated PostgreSQL target before cleanup or writes."""
    if not database_url.strip():
        raise ProjectsQualityTargetError("DATABASE_URL es obligatorio para el smoke Projects.")
    if not quality_database_url.strip():
        raise ProjectsQualityTargetError("QUALITY_DATABASE_URL es obligatorio para el smoke Projects.")
    if not confirmed_database.strip():
        raise ProjectsQualityTargetError(
            "PROJECTS_QUALITY_TARGET_DATABASE debe confirmar explícitamente la base destino."
        )
    if not run_id.strip():
        raise ProjectsQualityTargetError("QUALITY_RUN_ID es obligatorio para identificar la ejecución.")
    try:
        target = make_url(database_url)
        quality_target = make_url(quality_database_url)
    except Exception as exc:
        raise ProjectsQualityTargetError("No se pudo parsear la URL de la base de calidad.") from exc

    database_name = target.database
    if target.get_backend_name() != "postgresql":
        raise ProjectsQualityTargetError("El smoke Projects requiere PostgreSQL aislado.")
    if not database_name:
        raise ProjectsQualityTargetError("La URL no identifica la base de datos destino.")
    if confirmed_database != database_name:
        raise ProjectsQualityTargetError(
            "Smoke Projects bloqueado: PROJECTS_QUALITY_TARGET_DATABASE debe coincidir "
            f"exactamente con la base destino ({database_name})."
        )
    if not _DISPOSABLE_DATABASE_NAME.search(database_name):
        raise ProjectsQualityTargetError(
            "Smoke Projects bloqueado: la base debe identificarse como _e2e, _test o _quality."
        )
    if quality_target.get_backend_name() != "postgresql" or quality_target.database != database_name:
        raise ProjectsQualityTargetError(
            "QUALITY_DATABASE_URL debe apuntar a la misma base PostgreSQL que DATABASE_URL."
        )
    if target.host != quality_target.host or target.port != quality_target.port:
        raise ProjectsQualityTargetError(
            "QUALITY_DATABASE_URL debe apuntar al mismo host y puerto PostgreSQL que DATABASE_URL."
        )
    return database_name
