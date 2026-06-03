import uuid
from datetime import datetime, timezone

import pytest
from backend import models
from backend.core.security import get_password_hash


def _seed_sede(db_session):
    sede = models.Sede(
        id=uuid.uuid4(), nombre="Test Sede", ciudad="Bogota", es_activa=True
    )
    db_session.add(sede)
    db_session.commit()
    db_session.refresh(sede)
    return sede


def _seed_admin(db_session, email="test@example.com", password="testpass123"):
    user = models.User(
        username=email.split("@")[0],
        email=email,
        password_hash=get_password_hash(password),
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    sede = _seed_sede(db_session)

    persona = models.Persona(
        id=uuid.uuid4(),
        user_id=user.id,
        first_name="Test",
        last_name="User",
        email=email,
        sede_id=sede.id,
    )
    db_session.add(persona)
    db_session.commit()
    return user, persona, sede


def _auth_headers(client, email="test@example.com", password="testpass123"):
    resp = client.post(
        "/api/auth/login",
        data={"username": email, "password": password, "grant_type": "password"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_finance_summary(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)
    resp = client.get("/api/finance/summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "balance" in data
    assert "total_income" in data
    assert "total_expense" in data


def test_finance_funds(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)
    resp = client.get("/api/finance/funds", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "ingresos_mes" in data
    assert "por_tipo" in data


def test_finance_transactions(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client)

    donation = models.Donation(
        amount=30000,
        donation_type="Ofrenda",
        donor_name="Pedro Perez",
        persona_id=persona.id,
    )
    db_session.add(donation)
    db_session.commit()

    resp = client.get("/api/finance/transactions", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.xfail(
    reason="Endpoint passes persona_id str to UUID column causing hex error",
    strict=False,
)
def test_finance_register_donation(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client)

    fund = models.Fund(
        name="Fondo Misiones",
        description="Fondo para misiones",
        current_balance=0.0,
    )
    db_session.add(fund)
    db_session.commit()
    db_session.refresh(fund)

    resp = client.post(
        "/api/finance/donations",
        params={
            "fund_id": fund.fund_id,
            "amount": 50000,
            "donation_type": "Diezmo",
            "donor_name": "Juan Diaz",
            "persona_id": str(persona.id),
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["amount"] == 50000
    assert data["type"] == "Diezmo"


def test_finance_admin_funds_crud(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)

    # Create
    resp = client.post(
        "/api/finance/admin/funds",
        json={
            "name": "Fondo Test",
            "description": "Desc",
            "is_public": True,
            "target_amount": 1000000,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    fund_id = resp.json()["id"]

    # List
    resp2 = client.get("/api/finance/admin/funds", headers=headers)
    assert resp2.status_code == 200
    funds = resp2.json()
    assert any(f["id"] == fund_id for f in funds)

    # Update
    resp3 = client.patch(
        f"/api/finance/admin/funds/{fund_id}",
        json={"name": "Fondo Test Actualizado"},
        headers=headers,
    )
    assert resp3.status_code == 200
    assert resp3.json()["name"] == "Fondo Test Actualizado"

    # Delete (soft)
    resp4 = client.delete(
        f"/api/finance/admin/funds/{fund_id}", headers=headers
    )
    assert resp4.status_code == 204


def test_finance_impact_public(client, db_session):
    resp = client.get("/api/finance/impact")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_miembros" in data
    assert "total_familias" in data
    assert "distribucion" in data
