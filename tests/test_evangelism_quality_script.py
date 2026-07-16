from __future__ import annotations

import argparse

from scripts import test_evangelism_quality as quality


def _args(**overrides: bool) -> argparse.Namespace:
    base = {
        "backend_deep": False,
        "frontend_smoke": False,
        "frontend_deep": False,
        "expanded": False,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def test_build_checks_base_mode():
    checks = quality.build_checks(_args())
    assert [check.label for check in checks] == [
        "1. Smoke mínimo Evangelismo",
        "2. Regresiones críticas Evangelismo",
    ]


def test_build_checks_backend_deep_mode():
    checks = quality.build_checks(_args(backend_deep=True))
    assert [check.label for check in checks] == [
        "1. Smoke mínimo Evangelismo",
        "2. Regresiones críticas Evangelismo",
        "3. Cobertura amplia backend Evangelismo",
    ]


def test_build_checks_expanded_mode_includes_required_frontend_gate():
    checks = quality.build_checks(_args(expanded=True))
    assert [check.label for check in checks] == [
        "1. Smoke mínimo Evangelismo",
        "2. Regresiones críticas Evangelismo",
        "3. Cobertura amplia backend Evangelismo",
        "4. Smoke frontend Evangelismo",
    ]
    assert checks[-1].optional is False


def test_build_checks_frontend_smoke_only_mode():
    checks = quality.build_checks(_args(frontend_smoke=True))
    assert [check.label for check in checks] == [
        "1. Smoke mínimo Evangelismo",
        "2. Regresiones críticas Evangelismo",
        "4. Smoke frontend Evangelismo",
    ]
    assert checks[-1].optional is False


def test_build_checks_frontend_deep_only_mode():
    checks = quality.build_checks(_args(frontend_deep=True))
    assert [check.label for check in checks] == [
        "1. Smoke mínimo Evangelismo",
        "2. Regresiones críticas Evangelismo",
        "5. Cobertura profunda frontend Evangelismo",
    ]
    assert checks[-1].cmd == ("npm", "run", "test:e2e:evangelism:deep")
