"""
Tests for Finance Suite endpoints — bank accounts, accounting entries, sales orders,
invoices, expense reports, documents, sign requests.
"""
from __future__ import annotations

import uuid as _uuid

from backend import models
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin
from tests.conftest import seed_user_with_role as _seed_user_with_role

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _seed_sede(db_session) -> models.Sede:
    existing = db_session.query(models.Sede).first()
    if existing:
        return existing
    sede = models.Sede(
        id=_uuid.uuid4(), nombre="Sede Test", ciudad="Bogota", es_activa=True
    )
    db_session.add(sede)
    db_session.commit()
    db_session.refresh(sede)
    return sede


def _seed_chart_account(db_session, sede_id=None) -> models.ChartOfAccount:
    acc = models.ChartOfAccount(
        id=_uuid.uuid4(),
        code="1105",
        name="Bancos",
        account_type="asset",
        sede_id=sede_id,
        is_active=True,
    )
    db_session.add(acc)
    db_session.flush()
    return acc


def _seed_bank_account(db_session, sede_id=None) -> models.BankAccount:
    acct = models.BankAccount(
        id=_uuid.uuid4(),
        bank_name="Banco Test",
        account_number="1234567890",
        account_type="checking",
        currency="COP",
        current_balance=0,
        sede_id=sede_id,
    )
    db_session.add(acct)
    db_session.flush()
    return acct


# ═══════════════════════════════════════════════════════════════════════════════
# BANK ACCOUNTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_bank_account_crud(client, db_session):
    _seed_sede(db_session)
    _seed_admin(db_session)
    headers = _auth_headers(client)

    # Create
    resp = client.post("/api/finance-suite/bank-accounts", json={
        "bank_name": "Banco Davivienda",
        "account_number": "9876543210",
        "account_type": "savings",
        "currency": "COP",
    }, headers=headers)
    assert resp.status_code == 201
    acct_id = resp.json()["id"]

    # List
    resp2 = client.get("/api/finance-suite/bank-accounts", headers=headers)
    assert resp2.status_code == 200
    assert any(a["id"] == acct_id for a in resp2.json())

    # Update
    resp3 = client.patch(f"/api/finance-suite/bank-accounts/{acct_id}", json={
        "bank_name": "Banco Actualizado",
    }, headers=headers)
    assert resp3.status_code == 200
    assert resp3.json()["bank_name"] == "Banco Actualizado"


def test_bank_account_extra_forbid(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)

    resp = client.post("/api/finance-suite/bank-accounts", json={
        "bank_name": "Test",
        "account_number": "123",
        "evil_field": "inject",
    }, headers=headers)
    assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# CHART OF ACCOUNTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_chart_account_crud(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)

    resp = client.post("/api/finance-suite/chart-of-accounts", json={
        "code": "1110",
        "name": "Caja",
        "account_type": "asset",
    }, headers=headers)
    assert resp.status_code == 201
    acc_id = resp.json()["id"]

    resp2 = client.get("/api/finance-suite/chart-of-accounts", headers=headers)
    assert resp2.status_code == 200
    assert any(a["id"] == acc_id for a in resp2.json())


# ═══════════════════════════════════════════════════════════════════════════════
# ACCOUNTING ENTRIES
# ═══════════════════════════════════════════════════════════════════════════════

def test_create_accounting_entry(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)
    acc = _seed_chart_account(db_session)

    resp = client.post("/api/finance-suite/accounting-entries", json={
        "entry_date": "2026-01-15",
        "description": "Compra de material",
        "lines": [
            {"account_id": str(acc.id), "debit": "100000", "credit": "0"},
            {"account_id": str(acc.id), "debit": "0", "credit": "100000"},
        ],
    }, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "draft"
    assert len(data["lines"]) == 2


def test_create_entry_rejects_empty_lines(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)

    resp = client.post("/api/finance-suite/accounting-entries", json={
        "entry_date": "2026-01-15",
        "description": "Sin lineas",
        "lines": [],
    }, headers=headers)
    assert resp.status_code == 400


def test_create_entry_rejects_debit_and_credit(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)
    acc = _seed_chart_account(db_session)

    resp = client.post("/api/finance-suite/accounting-entries", json={
        "entry_date": "2026-01-15",
        "description": "Invalido",
        "lines": [
            {"account_id": str(acc.id), "debit": "50000", "credit": "50000"},
            {"account_id": str(acc.id), "debit": "0", "credit": "0"},
        ],
    }, headers=headers)
    assert resp.status_code == 400


def test_post_accounting_entry(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)
    acc = _seed_chart_account(db_session)

    # Create
    resp = client.post("/api/finance-suite/accounting-entries", json={
        "entry_date": "2026-01-15",
        "description": "Para postear",
        "lines": [
            {"account_id": str(acc.id), "debit": "100000", "credit": "0"},
            {"account_id": str(acc.id), "debit": "0", "credit": "100000"},
        ],
    }, headers=headers)
    assert resp.status_code == 201
    entry_id = resp.json()["id"]

    # Post
    resp2 = client.patch(f"/api/finance-suite/accounting-entries/{entry_id}/post", headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "posted"

    # Cannot post again
    resp3 = client.patch(f"/api/finance-suite/accounting-entries/{entry_id}/post", headers=headers)
    assert resp3.status_code == 400


def test_list_accounting_entries_with_skip_limit(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)
    acc = _seed_chart_account(db_session)

    for _ in range(3):
        client.post("/api/finance-suite/accounting-entries", json={
            "entry_date": "2026-01-15",
            "description": "Entry",
            "lines": [
                {"account_id": str(acc.id), "debit": "1000", "credit": "0"},
                {"account_id": str(acc.id), "debit": "0", "credit": "1000"},
            ],
        }, headers=headers)

    resp = client.get("/api/finance-suite/accounting-entries?skip=1&limit=1", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# SALES ORDERS
# ═══════════════════════════════════════════════════════════════════════════════

def test_create_sales_order(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)

    resp = client.post("/api/finance-suite/sales-orders", json={
        "customer_name": "Cliente Corp",
        "order_date": "2026-03-01",
        "items": [
            {"description": "Servicio A", "quantity": "2", "unit_price": "50000"},
        ],
    }, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["customer_name"] == "Cliente Corp"
    assert resp.json()["status"] == "draft"


def test_create_sales_order_empty_items(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)

    resp = client.post("/api/finance-suite/sales-orders", json={
        "customer_name": "Sin items",
        "order_date": "2026-03-01",
        "items": [],
    }, headers=headers)
    assert resp.status_code == 400


def test_list_sales_orders_skip(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)

    for i in range(3):
        client.post("/api/finance-suite/sales-orders", json={
            "customer_name": f"Cliente {i}",
            "order_date": "2026-03-01",
            "items": [{"description": "Item", "quantity": "1", "unit_price": "10000"}],
        }, headers=headers)

    resp = client.get("/api/finance-suite/sales-orders?skip=2&limit=1", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# INVOICES
# ═══════════════════════════════════════════════════════════════════════════════

def test_create_invoice(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)

    resp = client.post("/api/finance-suite/invoices", json={
        "customer_name": "Cliente Factura",
        "issue_date": "2026-04-01",
        "items": [
            {"description": "Servicio", "quantity": "1", "unit_price": "100000"},
        ],
    }, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["invoice_number"].startswith("INV-")
    assert data["status"] == "draft"


def test_create_invoice_empty_items(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)

    resp = client.post("/api/finance-suite/invoices", json={
        "customer_name": "Sin items",
        "issue_date": "2026-04-01",
        "items": [],
    }, headers=headers)
    assert resp.status_code == 400


def test_send_electronic_invoice_returns_501(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)

    # Create invoice first
    resp = client.post("/api/finance-suite/invoices", json={
        "customer_name": "Test",
        "issue_date": "2026-04-01",
        "items": [{"description": "X", "quantity": "1", "unit_price": "50000"}],
    }, headers=headers)
    inv_id = resp.json()["id"]

    resp2 = client.post(f"/api/finance-suite/invoices/{inv_id}/send-electronic", headers=headers)
    assert resp2.status_code == 501


# ═══════════════════════════════════════════════════════════════════════════════
# EXPENSE REPORTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_create_expense_report(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)

    resp = client.post("/api/finance-suite/expense-reports", json={
        "description": "Viaticos",
        "items": [{
            "expense_date": "2026-05-01",
            "category": "Transporte",
            "description": "Taxi",
            "amount": "25000",
        }],
    }, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["status"] == "draft"


def test_submit_expense_report(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client)

    # Create report (employee_id = current_user.id)
    resp = client.post("/api/finance-suite/expense-reports", json={
        "description": "Para submittear",
        "items": [{"expense_date": "2026-05-01", "category": "Otros", "description": "X", "amount": "10000"}],
    }, headers=headers)
    report_id = resp.json()["id"]

    # Submit (same user = employee)
    resp2 = client.post(f"/api/finance-suite/expense-reports/{report_id}/submit", headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "submitted"


def test_submit_expense_report_wrong_owner(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    other, _, _ = _seed_user_with_role(db_session, email="other@test.com", permisos={"finance": "edit"})

    # Create report as admin
    admin_headers = _auth_headers(client)
    resp = client.post("/api/finance-suite/expense-reports", json={
        "description": "Del admin",
        "items": [{"expense_date": "2026-05-01", "category": "Otros", "description": "X", "amount": "10000"}],
    }, headers=admin_headers)
    report_id = resp.json()["id"]

    # Other user tries to submit → 403
    other_headers = _auth_headers(client, email="other@test.com")
    resp2 = client.post(f"/api/finance-suite/expense-reports/{report_id}/submit", headers=other_headers)
    assert resp2.status_code == 403


def test_reject_expense_report_only_submitted(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    headers = _auth_headers(client)

    resp = client.post("/api/finance-suite/expense-reports", json={
        "description": "Draft report",
        "items": [{"expense_date": "2026-05-01", "category": "Otros", "description": "X", "amount": "10000"}],
    }, headers=headers)
    report_id = resp.json()["id"]

    # Cannot reject draft
    resp2 = client.post(f"/api/finance-suite/expense-reports/{report_id}/reject", headers=headers)
    assert resp2.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_document_crud(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)

    resp = client.post("/api/finance-suite/documents", json={
        "title": "Contrato de arrendamiento",
        "file_url": "https://storage.ccf.org/docs/contrato.pdf",
        "file_name": "contrato.pdf",
        "file_size": 1024,
        "mime_type": "application/pdf",
        "document_type": "contract",
        "tag_ids": [],
    }, headers=headers)
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    # List
    resp2 = client.get("/api/finance-suite/documents", headers=headers)
    assert resp2.status_code == 200
    assert any(d["id"] == doc_id for d in resp2.json())

    # Delete (archive)
    resp3 = client.delete(f"/api/finance-suite/documents/{doc_id}", headers=headers)
    assert resp3.status_code == 204


def test_document_max_length(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)

    resp = client.post("/api/finance-suite/documents", json={
        "title": "x" * 300,
        "file_url": "https://test.com/doc.pdf",
        "file_name": "doc.pdf",
        "file_size": 100,
        "mime_type": "application/pdf",
        "tag_ids": [],
    }, headers=headers)
    assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# SIGN REQUESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_sign_request_crud(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)

    resp = client.post("/api/finance-suite/sign-requests", json={
        "title": "Contrato de servicios",
        "document_url": "https://storage.ccf.org/docs/contrato.pdf",
        "country_code": "CO",
        "signers": [
            {"email": "signer@example.com", "full_name": "Juan Signer", "role": "signer"},
        ],
    }, headers=headers)
    assert resp.status_code == 201
    resp.json()["id"]
    assert len(resp.json()["signers"]) == 1


def test_send_sign_request_no_signers(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)

    resp = client.post("/api/finance-suite/sign-requests", json={
        "title": "Sin firmantes",
        "document_url": "https://test.com/doc.pdf",
        "signers": [],
    }, headers=headers)
    req_id = resp.json()["id"]

    # Send → should fail (no signers)
    resp2 = client.post(f"/api/finance-suite/sign-requests/{req_id}/send", headers=headers)
    assert resp2.status_code == 400


def test_send_and_sign_request(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)

    resp = client.post("/api/finance-suite/sign-requests", json={
        "title": "Para firmar",
        "document_url": "https://test.com/doc.pdf",
        "signers": [
            {"email": "signer@test.com", "full_name": "Test Signer"},
        ],
    }, headers=headers)
    req_id = resp.json()["id"]
    signer_id = resp.json()["signers"][0]["id"]

    # Send
    resp2 = client.post(f"/api/finance-suite/sign-requests/{req_id}/send", headers=headers)
    assert resp2.status_code == 200

    # Sign
    resp3 = client.post(
        f"/api/finance-suite/sign-requests/{req_id}/signers/{signer_id}/sign",
        json={"action": "sign"},
        headers=headers,
    )
    assert resp3.status_code == 200

    # Verify completed
    resp4 = client.get(f"/api/finance-suite/sign-requests/{req_id}", headers=headers)
    assert resp4.json()["status"] == "completed"


def test_sign_document_wrong_status(client, db_session):
    _seed_admin(db_session)
    headers = _auth_headers(client)

    resp = client.post("/api/finance-suite/sign-requests", json={
        "title": "Doble sign test",
        "document_url": "https://test.com/doc.pdf",
        "signers": [{"email": "s@test.com", "full_name": "S"}],
    }, headers=headers)
    req_id = resp.json()["id"]
    signer_id = resp.json()["signers"][0]["id"]

    # Send
    client.post(f"/api/finance-suite/sign-requests/{req_id}/send", headers=headers)

    # Sign
    client.post(f"/api/finance-suite/sign-requests/{req_id}/signers/{signer_id}/sign",
                json={"action": "sign"}, headers=headers)

    # Try to sign again → should fail (already signed)
    resp2 = client.post(f"/api/finance-suite/sign-requests/{req_id}/signers/{signer_id}/sign",
                        json={"action": "sign"}, headers=headers)
    assert resp2.status_code == 400
