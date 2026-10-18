from __future__ import annotations

import pytest

from scripts.projects_quality_safety import (
    ProjectsQualityTargetError,
    build_projects_quality_audit_manifest,
    validate_projects_quality_target,
)


def _validate(database: str = "ccf_projects_quality_20261004", **overrides: str) -> str:
    values = {
        "database_url": f"postgresql://user:pass@localhost/{database}",
        "quality_database_url": f"postgresql://user:pass@localhost/{database}",
        "confirmed_database": database,
        "run_id": "projects-20261004-01",
    }
    values.update(overrides)
    return validate_projects_quality_target(**values)


def test_projects_quality_accepts_explicit_isolated_database():
    assert _validate() == "ccf_projects_quality_20261004"


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"quality_database_url": ""}, "QUALITY_DATABASE_URL es obligatorio"),
        ({"confirmed_database": ""}, "debe confirmar explícitamente"),
        ({"confirmed_database": "ccf_shared"}, "debe coincidir exactamente"),
        ({"database_url": "sqlite:///projects.db", "confirmed_database": "projects.db"}, "requiere PostgreSQL"),
        ({"database_url": "postgresql://user:pass@localhost/development", "confirmed_database": "development"}, "_e2e, _test o _quality"),
        ({"quality_database_url": "postgresql://user:pass@localhost/other_quality"}, "misma base PostgreSQL"),
        ({"quality_database_url": "postgresql://user:pass@other-host/ccf_projects_quality_20261004"}, "mismo host y puerto"),
        ({"quality_database_url": "postgresql://user:pass@localhost:5433/ccf_projects_quality_20261004"}, "mismo host y puerto"),
        ({"run_id": "   "}, "QUALITY_RUN_ID es obligatorio"),
    ],
)
def test_projects_quality_rejects_unisolated_or_ambiguous_target(kwargs, message):
    with pytest.raises(ProjectsQualityTargetError, match=message):
        _validate(**kwargs)


@pytest.mark.parametrize(
    ("database", "expected_tier", "port_suffix", "expected_port"),
    [
        ("ccf_projects_quality_20261018", "quality", "", 5432),
        ("ccf_projects_e2e_smoke", "e2e", ":5433", 5433),
        ("ccf_projects_test_ci", "test", "", 5432),
    ],
)
def test_build_projects_quality_audit_manifest_tiers_and_ports(
    database, expected_tier, port_suffix, expected_port
):
    url = f"postgresql://user:pass@localhost{port_suffix}/{database}"
    manifest = build_projects_quality_audit_manifest(
        database_url=url,
        quality_database_url=url,
        confirmed_database=database,
        run_id="  pmi-qa-run-01  ",
    )
    assert manifest == {
        "database_name": database,
        "run_id": "pmi-qa-run-01",
        "host": "localhost",
        "port": expected_port,
        "isolation_tier": expected_tier,
        "is_isolated_verified": True,
    }


def test_build_projects_quality_audit_manifest_propagates_target_error():
    with pytest.raises(ProjectsQualityTargetError, match="_e2e, _test o _quality"):
        build_projects_quality_audit_manifest(
            database_url="postgresql://user:pass@localhost/production",
            quality_database_url="postgresql://user:pass@localhost/production",
            confirmed_database="production",
            run_id="pmi-qa-run-02",
        )


# ── evaluate_quality_gate_sla (pure helper) ──────────────────────────────────


def test_quality_gate_sla_green_certified():
    """Suite completa en tiempo → 'green_certified' con pass_rate 100%."""
    from scripts.projects_quality_safety import evaluate_quality_gate_sla

    result = evaluate_quality_gate_sla(total_tests=33, passed_tests=33, duration_seconds=45.678)

    assert result == {
        "total_tests": 33,
        "passed_tests": 33,
        "failed_or_skipped": 0,
        "pass_rate_pct": 100.0,
        "duration_seconds": 45.68,
        "is_within_time_sla": True,
        "gate_verdict": "green_certified",
    }


def test_quality_gate_sla_failed_tests():
    """Failures/skips > 0 → 'failed_tests' aun estando dentro del SLA."""
    from scripts.projects_quality_safety import evaluate_quality_gate_sla

    result = evaluate_quality_gate_sla(total_tests=10, passed_tests=8, duration_seconds=30.0)

    assert result["failed_or_skipped"] == 2
    assert result["pass_rate_pct"] == 80.0
    assert result["is_within_time_sla"] is True
    assert result["gate_verdict"] == "failed_tests"


def test_quality_gate_sla_sla_breach():
    """Sin fallos pero duration > sla → 'sla_breach' (precedencia de fallas)."""
    from scripts.projects_quality_safety import evaluate_quality_gate_sla

    result = evaluate_quality_gate_sla(total_tests=5, passed_tests=5, duration_seconds=121.0)

    assert result["is_within_time_sla"] is False
    assert result["gate_verdict"] == "sla_breach"

    # SLA nulo (falsy) cae al default 120.0 (per spec: sla_seconds or 120.0)
    zero_sla = evaluate_quality_gate_sla(total_tests=5, passed_tests=5, duration_seconds=0.5, max_duration_sla_seconds=0.0)
    assert zero_sla["is_within_time_sla"] is True
    assert zero_sla["gate_verdict"] == "green_certified"

    # SLA positivo minúsculo se acota al piso 0.1
    tiny_sla = evaluate_quality_gate_sla(total_tests=5, passed_tests=5, duration_seconds=0.5, max_duration_sla_seconds=0.05)
    assert tiny_sla["is_within_time_sla"] is False
    assert tiny_sla["gate_verdict"] == "sla_breach"

    # Fallas tienen precedencia sobre breach de SLA
    mixed = evaluate_quality_gate_sla(total_tests=5, passed_tests=3, duration_seconds=999.0)
    assert mixed["gate_verdict"] == "failed_tests"


def test_quality_gate_sla_empty_suite():
    """0 tests → 'empty_suite' (pass_rate 0.0 incluso con duración cero)."""
    from scripts.projects_quality_safety import evaluate_quality_gate_sla

    result = evaluate_quality_gate_sla(total_tests=0, passed_tests=0, duration_seconds=0.0)

    assert result == {
        "total_tests": 0,
        "passed_tests": 0,
        "failed_or_skipped": 0,
        "pass_rate_pct": 0.0,
        "duration_seconds": 0.0,
        "is_within_time_sla": True,
        "gate_verdict": "empty_suite",
    }

    # Sanitización: pasadas > total se acotan; negativos a 0
    weird = evaluate_quality_gate_sla(total_tests=-3, passed_tests=7, duration_seconds=-5.0)
    assert weird["total_tests"] == 0
    assert weird["passed_tests"] == 0
    assert weird["duration_seconds"] == 0.0
    assert weird["gate_verdict"] == "empty_suite"


# ── evaluate_test_suite_assertion_density (PMBOK §8.3, pure helper) ───────


def test_assertion_density_high_verification_rigor():
    """>= 3.0 aserciones/test y 0 skips → 'high_verification_rigor'."""
    from scripts.projects_quality_safety import evaluate_test_suite_assertion_density

    result = evaluate_test_suite_assertion_density(
        total_tests=33, total_assertions=100, skipped_tests=0
    )

    assert result == {
        "total_tests": 33,
        "executed_tests": 33,
        "skipped_tests": 0,
        "total_assertions": 100,
        "assertions_per_executed_test": 3.03,
        "skip_rate_pct": 0.0,
        "rigor_status": "high_verification_rigor",
    }


def test_assertion_density_standard_coverage():
    """Aserciones en [1.5, 3.0) o skips <= 10% → 'standard_coverage'."""
    from scripts.projects_quality_safety import evaluate_test_suite_assertion_density

    standard = evaluate_test_suite_assertion_density(total_tests=10, total_assertions=20)
    assert standard["assertions_per_executed_test"] == 2.0
    assert standard["skip_rate_pct"] == 0.0
    assert standard["rigor_status"] == "standard_coverage"

    # borde inferior: exactamente 1.5 aserciones/test → standard (no shallow)
    borderline = evaluate_test_suite_assertion_density(total_tests=4, total_assertions=6)
    assert borderline["assertions_per_executed_test"] == 1.5
    assert borderline["rigor_status"] == "standard_coverage"

    # skips <= 10% no degradan a excessive_skips
    light_skips = evaluate_test_suite_assertion_density(
        total_tests=100, total_assertions=150, skipped_tests=10
    )
    assert light_skips["skip_rate_pct"] == 10.0
    assert light_skips["assertions_per_executed_test"] == round(150 / 90, 2)
    assert light_skips["rigor_status"] == "standard_coverage"


def test_assertion_density_excessive_skips():
    """skip_rate > 10% → 'excessive_skips' (precedencia sobre densidad baja)."""
    from scripts.projects_quality_safety import evaluate_test_suite_assertion_density

    result = evaluate_test_suite_assertion_density(
        total_tests=50, total_assertions=200, skipped_tests=6
    )
    assert result["skipped_tests"] == 6
    assert result["executed_tests"] == 44
    assert result["skip_rate_pct"] == 12.0
    # Aun con 4.55 aserciones/test, el exceso de skips manda
    assert result["assertions_per_executed_test"] == 4.55
    assert result["rigor_status"] == "excessive_skips"


def test_assertion_density_shallow_and_no_tests_executed():
    """< 1.5 aserciones/test → 'shallow_assertions'; 0 ejecutados → 'no_tests_executed'."""
    from scripts.projects_quality_safety import evaluate_test_suite_assertion_density

    result = evaluate_test_suite_assertion_density(
        total_tests=10, total_assertions=12, skipped_tests=1
    )
    assert result["assertions_per_executed_test"] == round(12 / 9, 2)
    assert result["skip_rate_pct"] == 10.0  # 10% exacto NO es excessive (<=)
    assert result["rigor_status"] == "shallow_assertions"

    # Cero aserciones con tests ejecutados → shallow
    zero = evaluate_test_suite_assertion_density(total_tests=5, total_assertions=0)
    assert zero["assertions_per_executed_test"] == 0.0
    assert zero["rigor_status"] == "shallow_assertions"

    # 0 tests totales → no_tests_executed con métricas en 0
    zeros = evaluate_test_suite_assertion_density(
        total_tests=0, total_assertions=0, skipped_tests=0
    )
    assert zeros == {
        "total_tests": 0,
        "executed_tests": 0,
        "skipped_tests": 0,
        "total_assertions": 0,
        "assertions_per_executed_test": 0.0,
        "skip_rate_pct": 0.0,
        "rigor_status": "no_tests_executed",
    }

    # Todos skipped (8/8) o exceso de skips sanitizado (99 → 3) → sin ejecuciones
    all_skipped = evaluate_test_suite_assertion_density(
        total_tests=8, total_assertions=40, skipped_tests=8
    )
    assert all_skipped["executed_tests"] == 0
    assert all_skipped["rigor_status"] == "no_tests_executed"

    over = evaluate_test_suite_assertion_density(
        total_tests=3, total_assertions=9, skipped_tests=99
    )
    assert over["skipped_tests"] == 3
    assert over["executed_tests"] == 0
    assert over["rigor_status"] == "no_tests_executed"
