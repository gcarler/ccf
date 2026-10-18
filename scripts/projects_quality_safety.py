"""Safety checks for the destructive Projects integration smoke."""

from __future__ import annotations

import re
from typing import Any

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


def build_projects_quality_audit_manifest(
    *,
    database_url: str,
    quality_database_url: str,
    confirmed_database: str,
    run_id: str,
) -> dict:
    """Construye el manifiesto de auditoría de aseguramiento de calidad PMI (§8.2)."""
    database_name = validate_projects_quality_target(
        database_url=database_url,
        quality_database_url=quality_database_url,
        confirmed_database=confirmed_database,
        run_id=run_id,
    )
    target = make_url(database_url)
    lower_name = database_name.lower()
    if "e2e" in lower_name:
        isolation_tier = "e2e"
    elif "quality" in lower_name:
        isolation_tier = "quality"
    else:
        isolation_tier = "test"

    return {
        "database_name": database_name,
        "run_id": run_id.strip(),
        "host": target.host or "localhost",
        "port": int(target.port or 5432),
        "isolation_tier": isolation_tier,
        "is_isolated_verified": True,
    }


def evaluate_quality_gate_sla(
    total_tests: int,
    passed_tests: int,
    duration_seconds: float,
    max_duration_sla_seconds: float = 120.0,
) -> dict[str, Any]:
    """Evalúa el cumplimiento del Quality Gate PMI (función pura).

    Retorna:
    - `total_tests`: total saneado (>= 0).
    - `passed_tests`: aprobados saneados, acotados a [0, total].
    - `failed_or_skipped`: fallidos + omitidos (total - passed).
    - `pass_rate_pct`: % aprobados (2 decimales; 0.0 si total == 0).
    - `duration_seconds`: duración redondeada (>= 0).
    - `is_within_time_sla`: True si duration <= sla (sla >= 0.1).
    - `gate_verdict`: 'empty_suite' (0 tests), 'failed_tests' (failures >
      0), 'sla_breach' (excede SLA) o 'green_certified'.
    """
    total = max(0, int(total_tests or 0))
    passed = min(total, max(0, int(passed_tests or 0)))
    failed_or_skipped = total - passed
    pass_rate_pct = round((passed / total) * 100.0, 2) if total > 0 else 0.0
    duration = round(max(0.0, float(duration_seconds or 0.0)), 2)
    sla = max(0.1, float(max_duration_sla_seconds or 120.0))
    is_within_time_sla = bool(duration <= sla)

    if total == 0:
        gate_verdict = "empty_suite"
    elif failed_or_skipped > 0:
        gate_verdict = "failed_tests"
    elif not is_within_time_sla:
        gate_verdict = "sla_breach"
    else:
        gate_verdict = "green_certified"

    return {
        "total_tests": total,
        "passed_tests": passed,
        "failed_or_skipped": failed_or_skipped,
        "pass_rate_pct": pass_rate_pct,
        "duration_seconds": duration,
        "is_within_time_sla": is_within_time_sla,
        "gate_verdict": gate_verdict,
    }


def evaluate_test_suite_assertion_density(
    total_tests: int,
    total_assertions: int,
    skipped_tests: int = 0,
) -> dict:
    """Audita la densidad de aserciones y disciplina de ejecución (PMBOK §8.3 Control Quality).

    Sanitiza las entradas (tests >= 0, aserciones >= 0, skips acotados a
    [0, tests]) y calcula el rigor de verificación de la suite:
    - `assertions_per_executed_test`: aserciones / tests ejecutados
      (round 2; 0.0 sin ejecuciones).
    - `skip_rate_pct`: % de tests omitidos (round 2; 0.0 sin tests).
    - `rigor_status` (precedencia):
      'no_tests_executed' (executed == 0), 'excessive_skips'
      (skip_rate > 10%), 'shallow_assertions' (< 1.5 aserciones/test),
      'high_verification_rigor' (>= 3.0 aserciones/test y skip_rate 0)
      o 'standard_coverage'.
    """
    tests_count = max(0, int(total_tests or 0))
    assertions_count = max(0, int(total_assertions or 0))
    skipped_count = min(tests_count, max(0, int(skipped_tests or 0)))
    executed_tests = max(0, tests_count - skipped_count)

    assertions_per_executed_test = (
        round(assertions_count / executed_tests, 2) if executed_tests > 0 else 0.0
    )
    skip_rate_pct = (
        round((skipped_count / tests_count) * 100.0, 2) if tests_count > 0 else 0.0
    )

    if executed_tests == 0:
        rigor_status = "no_tests_executed"
    elif skip_rate_pct > 10.0:
        rigor_status = "excessive_skips"
    elif assertions_per_executed_test < 1.5:
        rigor_status = "shallow_assertions"
    elif assertions_per_executed_test >= 3.0 and skip_rate_pct == 0.0:
        rigor_status = "high_verification_rigor"
    else:
        rigor_status = "standard_coverage"

    return {
        "total_tests": tests_count,
        "executed_tests": executed_tests,
        "skipped_tests": skipped_count,
        "total_assertions": assertions_count,
        "assertions_per_executed_test": assertions_per_executed_test,
        "skip_rate_pct": skip_rate_pct,
        "rigor_status": rigor_status,
    }
