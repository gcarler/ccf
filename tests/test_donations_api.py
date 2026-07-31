import uuid
from unittest.mock import patch as _patch

from backend import models
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin

# ── Helpers ────────────────────────────────────────────────────────────


def _seed_sede(db_session):
    sede = models.Sede(id=uuid.uuid4(), nombre="Test Sede", ciudad="Bogota", es_activa=True)
    db_session.add(sede)
    db_session.commit()
    db_session.refresh(sede)
    return sede


# ── CRUD endpoints ─────────────────────────────────────────────────────


def test_create_donation(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)
    payload = {
        "amount": 100000,
        "donation_type": "Diezmo",
        "donor_name": "Carlos Ruiz",
    }
    resp = client.post("/api/donations", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["amount"] == 100000
    assert data["donation_type"] == "Diezmo"


def test_list_donations(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client)

    donation = models.Donation(
        amount=50000,
        donation_type="Ofrenda",
        donor_name="Ana Lopez",
        persona_id=persona.id,
        sede_id=sede.id,
    )
    db_session.add(donation)
    db_session.commit()

    resp = client.get("/api/donations", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_donations_total(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client)

    donation = models.Donation(
        amount=75000,
        donation_type="Diezmo",
        donor_name="Luis Martinez",
        persona_id=persona.id,
        sede_id=sede.id,
    )
    db_session.add(donation)
    db_session.commit()

    resp = client.get("/api/donations/total", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data


def test_donations_summary_empty(client, db_session):
    """Summary sin donaciones retorna lista vacía."""
    _seed_admin(db_session)
    headers = _auth_headers(client)
    resp = client.get("/api/donations/summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_donations_summary_with_data(client, db_session):
    """Summary con donaciones retorna datos agrupados por mes."""
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client)

    donation = models.Donation(
        amount=100000,
        donation_type="Diezmo",
        donor_name="Test Donor",
        persona_id=persona.id,
        sede_id=sede.id,
    )
    db_session.add(donation)
    db_session.commit()

    resp = client.get("/api/donations/summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "month" in data[0]
    assert "amount" in data[0]
    assert isinstance(data[0]["amount"], (int, float))


def test_donation_certificate_success(client, db_session):
    """Certificado para donación existente con sede correcta."""
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client)

    donation = models.Donation(
        amount=120000,
        donation_type="Misiones",
        donor_name="Maria Gomez",
        persona_id=persona.id,
        sede_id=sede.id,
    )
    db_session.add(donation)
    db_session.commit()
    db_session.refresh(donation)

    resp = client.get(f"/api/donations/{donation.id}/certificate", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["donor"] == "Maria Gomez"
    assert data["amount"] == 120000
    assert "CERT-DON-" in data["certificate_id"]


def test_donation_certificate_not_found(client, db_session):
    """Certificado con ID inexistente → 404."""
    _seed_admin(db_session)
    headers = _auth_headers(client)
    fake_id = uuid.uuid4()
    resp = client.get(f"/api/donations/{fake_id}/certificate", headers=headers)
    assert resp.status_code == 404
    data = resp.json()
    assert "detail" in data


def test_donation_certificate_sede_mismatch(client, db_session):
    """Certificado con sede diferente a la del admin → 404."""
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client)

    # Crear donación en SEDE DIFERENTE a la del admin
    other_sede = models.Sede(
        id=uuid.uuid4(),
        nombre="Otra Sede",
        ciudad="Medellin",
        es_activa=True,
    )
    db_session.add(other_sede)
    db_session.flush()

    donation = models.Donation(
        amount=50000,
        donation_type="Diezmo",
        donor_name="Test",
        persona_id=persona.id,
        sede_id=other_sede.id,
    )
    db_session.add(donation)
    db_session.commit()
    db_session.refresh(donation)

    resp = client.get(f"/api/donations/{donation.id}/certificate", headers=headers)
    assert resp.status_code == 404


# ── MercadoPago: create-preference ─────────────────────────────────────


@_patch("backend.services.payments.create_donation_preference")
def test_mercadopago_create_preference_success(mock_create, client, db_session):
    """Create-preference exitoso → 200 con init_point."""
    _seed_admin(db_session)
    mock_create.return_value = {
        "id": "pref_123",
        "init_point": "https://www.mercadopago.com.co/checkout",
        "sandbox_init_point": "https://sandbox.mercadopago.com.co/checkout",
    }
    payload = {
        "amount": 50000,
        "title": "Donacion Test",
        "description": "Prueba",
        "donor_name": "Test Donor",
        "email": "donor@example.com",
    }
    resp = client.post("/api/donations/mercadopago/create-preference", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "pref_123"
    assert "init_point" in data
    assert "sandbox_init_point" in data


@_patch("backend.services.payments.create_donation_preference")
def test_mercadopago_create_preference_runtime_error(mock_create, client):
    """RuntimeError de MercadoPago → 501."""
    mock_create.side_effect = RuntimeError("MP no configurado")
    payload = {
        "amount": 50000,
        "title": "Donacion Test",
        "description": "Prueba",
        "donor_name": "Test Donor",
        "email": "donor@example.com",
    }
    resp = client.post("/api/donations/mercadopago/create-preference", json=payload)
    assert resp.status_code == 501
    assert "MP" in resp.json()["detail"]


@_patch("backend.services.payments.create_donation_preference")
def test_mercadopago_create_preference_generic_error(mock_create, client):
    """Error genérico en MercadoPago → 500."""
    mock_create.side_effect = ValueError("Algo salio mal")
    payload = {
        "amount": 50000,
        "title": "Donacion Test",
        "description": "Prueba",
        "donor_name": "Test Donor",
        "email": "donor@example.com",
    }
    resp = client.post("/api/donations/mercadopago/create-preference", json=payload)
    assert resp.status_code == 500


# ── MercadoPago: webhook ───────────────────────────────────────────────


def test_mercadopago_webhook_unconfigured(client, db_session):
    """Webhook sin MercadoPago configurado → 200 (graceful)."""
    _seed_admin(db_session)
    payload = {"type": "payment", "data": {"id": "123"}}
    resp = client.post("/api/donations/mercadopago/webhook", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@_patch("backend.services.payments.process_webhook_notification")
def test_mercadopago_webhook_approved_payment(mock_process, client, db_session):
    """Webhook con pago aprobado → registra donación en DB y retorna 200."""
    _seed_admin(db_session)

    class MockResult:
        status = "approved"
        amount = 100000
        donor_name = "Juan Perez"
        email = "juan@example.com"
        payment_id = "pay_123"

    mock_process.return_value = MockResult()

    payload = {"type": "payment", "data": {"id": "pay_123"}}
    resp = client.post("/api/donations/mercadopago/webhook", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # Verificar que se creó la donación en la base de datos
    donation = db_session.query(models.Donation).filter(models.Donation.donor_name == "Juan Perez").first()
    assert donation is not None
    assert donation.amount == 100000
    assert donation.reference_code == "MP-pay_123"
    assert donation.payment_method == "MercadoPago"


def test_mercadopago_webhook_invalid_json(client, db_session):
    """Webhook con JSON inválido → 200 (manejo graceful)."""
    _seed_admin(db_session)
    resp = client.post(
        "/api/donations/mercadopago/webhook",
        data="esto-no-es-json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ── MercadoPago: payment-status ────────────────────────────────────────


@_patch("backend.services.payments.get_payment_status")
def test_mercadopago_payment_status_success(mock_status, client, db_session):
    """Payment-status exitoso → 200 con datos del pago."""
    _seed_admin(db_session)
    headers = _auth_headers(client)

    class MockResult:
        payment_id = "pay_123"
        status = "approved"
        status_detail = "accredited"
        amount = 100000
        email = "test@example.com"
        donor_name = "Test Donor"

    mock_status.return_value = MockResult()

    resp = client.get("/api/donations/mercadopago/payments/pay_123", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"
    assert data["amount"] == 100000
    assert data["email"] == "test@example.com"


@_patch("backend.services.payments.get_payment_status")
def test_mercadopago_payment_status_runtime_error(mock_status, client, db_session):
    """RuntimeError en payment-status → 501."""
    _seed_admin(db_session)
    headers = _auth_headers(client)
    mock_status.side_effect = RuntimeError("MP no disponible")

    resp = client.get("/api/donations/mercadopago/payments/pay_123", headers=headers)
    assert resp.status_code == 501


@_patch("backend.services.payments.get_payment_status")
def test_mercadopago_payment_status_generic_error(mock_status, client, db_session):
    """Error genérico en payment-status → 500."""
    _seed_admin(db_session)
    headers = _auth_headers(client)
    mock_status.side_effect = ValueError("Error de conexion")

    resp = client.get("/api/donations/mercadopago/payments/pay_123", headers=headers)
    assert resp.status_code == 500
