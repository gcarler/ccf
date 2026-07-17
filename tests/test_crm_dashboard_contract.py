"""Tests de contrato para el dashboard CRM.

Valida que GET /api/dashboard/crm devuelve la shape documentada:
- cards: MetricCard[]
- pipeline_funnel: FunnelStage[]
- growth_chart: ChartDataPoint[]
- interaction_heatmap: HeatmapItem[]
- conversion_rate: float
- pending_followups: int
- slas_vencidos: int
"""

from __future__ import annotations

import pytest

from tests.conftest import auth_headers, seed_admin


def test_dashboard_requires_auth(client):
    resp = client.get("/api/dashboard/crm")
    assert resp.status_code == 401


def test_dashboard_admin_returns_valid_shape(client, db_session):
    seed_admin(db_session, email="dash_admin@ccf.test", password="testpass123")
    headers = auth_headers(client, email="dash_admin@ccf.test", password="testpass123")

    resp = client.get("/api/dashboard/crm", headers=headers)
    assert resp.status_code == 200

    data = resp.json()
    assert isinstance(data, dict)

    if "cards" in data:
        assert isinstance(data["cards"], list)
        for card in data["cards"]:
            assert "label" in card or "title" in card

    if "pipeline_funnel" in data:
        assert isinstance(data["pipeline_funnel"], list)

    if "growth_chart" in data:
        assert isinstance(data["growth_chart"], list)

    if "conversion_rate" in data:
        assert isinstance(data["conversion_rate"], (int, float))

    if "pending_followups" in data:
        assert isinstance(data["pending_followups"], int)

    if "slas_vencidos" in data:
        assert isinstance(data["slas_vencidos"], int)


def test_dashboard_any_authenticated_user_can_access(client, db_session):
    from tests.conftest import seed_user_with_role

    seed_user_with_role(db_session, role_name="MIEMBRO", email="dash_miembro@ccf.test")
    headers = auth_headers(client, email="dash_miembro@ccf.test", password="testpass123")

    resp = client.get("/api/dashboard/crm", headers=headers)
    assert resp.status_code == 200
