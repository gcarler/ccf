"""Independent C06 oracles: forecasts must not divide by display-rounded indices."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from backend import models
from backend.services.project_evm_service import (
    calculate_eac_forecasts,
    calculate_project_evm_advanced,
)

CUTOFF = datetime(2026, 10, 28, tzinfo=timezone.utc)


def _project(db, *, progress, actual_cost):
    project = models.Project(
        title="Forecast precision regression",
        budget_allocated=1000,
        budget_spent=actual_cost,
        progress_mode="manual",
        manual_progress=progress,
        start_date=CUTOFF - timedelta(days=10),
        target_date=CUTOFF + timedelta(days=10),
    )
    db.add(project)
    db.commit()
    return project


@pytest.mark.parametrize("actual_cost", [300000, 3000, 1234.56])
def test_completed_forecasts_equal_incurred_cost(db_session, actual_cost):
    project = _project(db_session, progress=100, actual_cost=actual_cost)
    result = calculate_project_evm_advanced(db_session, project, now=CUTOFF)
    standard = result["standard_evm"]

    assert standard["eac"] == actual_cost
    assert standard["vac"] == round(1000 - actual_cost, 2)
    assert standard["cpi"] == round(1000 / actual_cost, 2)
    for model in result["forecast_models"].values():
        assert model["eac"] == actual_cost
        assert model["etc"] == 0
        assert model["vac"] == round(1000 - actual_cost, 2)


def test_partial_forecasts_use_unrounded_cost_and_schedule_indices(db_session):
    project = _project(db_session, progress=10, actual_cost=300000)
    result = calculate_project_evm_advanced(db_session, project, now=CUTOFF)
    standard = result["standard_evm"]
    # Decimal arithmetic supplies an oracle independent of the service formulas.
    bac, ev, ac, pv = map(Decimal, (1000, 100, 300000, 500))
    raw_cpi, raw_spi = ev / ac, ev / pv
    typical_eac = float((ac + (bac - ev) / raw_cpi).quantize(Decimal("0.01")))
    composite_eac = float((ac + (bac - ev) / (raw_cpi * raw_spi)).quantize(Decimal("0.01")))

    assert standard["cpi"] == 0  # Display DTO stays at two decimals.
    assert standard["spi"] == 0.2
    assert standard["eac"] == typical_eac == 3000000
    assert standard["vac"] == float(bac) - typical_eac
    for name, expected_eac in (("typical", typical_eac), ("composite", composite_eac)):
        model = result["forecast_models"][name]
        assert model["eac"] == expected_eac
        assert model["etc"] == expected_eac - float(ac)
        assert model["vac"] == float(bac) - expected_eac
    assert result["forecast_models"]["composite"]["eac"] == 13800000



def test_advanced_composite_uses_schedule_ratio_before_display_rounding(db_session):
    project = _project(db_session, progress=33.3, actual_cost=333)
    result = calculate_project_evm_advanced(db_session, project, now=CUTOFF)
    # CPI is exactly1 here, isolating SPI precision from the cost-index fix.
    expected = float((Decimal(333) + Decimal(667) / (Decimal(333) / Decimal(500))).quantize(Decimal("0.01")))

    assert result["standard_evm"]["cpi"] == 1
    assert result["standard_evm"]["spi"] == 0.67
    assert result["forecast_models"]["composite"]["eac"] == expected == 1334.5
    assert result["forecast_models"]["composite"]["etc"] == 1001.5
    assert result["forecast_models"]["composite"]["vac"] == -334.5


def test_composite_forecast_preserves_a_small_nonzero_performance_product():
    bac, ev, ac, pv = map(Decimal, (1000, 100, 300000, 999))
    raw_cpi, raw_spi = ev / ac, ev / pv
    expected = float((ac + (bac - ev) / (raw_cpi * raw_spi)).quantize(Decimal("0.01")))
    result = calculate_eac_forecasts(
        bac=float(bac), ev=float(ev), ac=float(ac), cpi=float(raw_cpi), spi=float(raw_spi)
    )["composite"]

    assert result["eac"] == expected == 27273000
    assert result["etc"] == expected - float(ac)
    assert result["vac"] == float(bac) - expected


def test_unmeasured_cost_policy_remains_outside_precision_fix(db_session):
    project = _project(db_session, progress=50, actual_cost=0)
    result = calculate_project_evm_advanced(db_session, project, now=CUTOFF)
    # H07 owns availability. This unit does not certify its existing fallback.
    assert result["standard_evm"]["cpi"] == 2
    assert result["standard_evm"]["eac"] == 500
    assert result["forecast_models"]["typical"]["eac"] == 250
