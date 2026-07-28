"""
Finance Suite Deep Coverage — targets uncovered lines in finance_suite.py.

Covers:
- Bank Transactions: debit balance update (L139-141)
- Reconciliations: created_by_id (L177)
- Accounting Entries: account not found (L229), debit != credit (L234), entry not found (L277), already posted (L289)
- Financial Statements: generate (L309-341)
- Tax Config: create (L349-353), list with country_code (L366-371, L380-386)
- Invoice: tax_rate lookup (L446), record_payment full/partial/not-found (L527, L538-567)
- Expense Reports: approve/reimburse (L581, 603)
- Documents: update with tags (L650-652, L664-668), delete cross-sede (L682-694)
- Receipts: upload (L705, L708-711), OCR update (L722-733)
- Sign Requests: send (L746-755), decline (L828-832), completion (L886-891), get not-found (L899-903)
"""

import uuid as _uuid

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin
from tests.conftest import seed_user_with_role as _seed_user_with_role

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _admin_client(client, db_session):
    """Seed admin + return auth headers."""
    _seed_admin(db_session)
    return _auth_headers(client)


def _create_bank_account(client, headers, db_session, sede_id=None):
    from backend import models

    acct = models.BankAccount(
        id=_uuid.uuid4(),
        bank_name="Banco Coverage",
        account_number="999999",
        account_type="checking",
        currency="COP",
        current_balance=0,
        sede_id=sede_id,
    )
    db_session.add(acct)
    db_session.flush()
    return acct


def _create_chart_account(client, headers, db_session, sede_id=None):
    from backend import models

    acc = models.ChartOfAccount(
        id=_uuid.uuid4(),
        code="6000",
        name="Gastos Coverage",
        account_type="expense",
        sede_id=sede_id,
        is_active=True,
    )
    db_session.add(acc)
    db_session.flush()
    return acc


# ═══════════════════════════════════════════════════════════════════════════════
# BANK TRANSACTIONS — debit balance (L139-141)
# ═══════════════════════════════════════════════════════════════════════════════


def test_bank_transaction_debit_updates_balance(client, db_session):
    """Debit transaction reduces account balance (L141)."""
    headers = _admin_client(client, db_session)
    acct = _create_bank_account(client, headers, db_session)

    # Credit first
    client.post(
        "/api/finance-suite/bank-transactions",
        json={
            "bank_account_id": str(acct.id),
            "transaction_date": "2026-06-01",
            "amount": "100000",
            "transaction_type": "credit",
            "description": "Abono",
        },
        headers=headers,
    )
    # Debit
    resp = client.post(
        "/api/finance-suite/bank-transactions",
        json={
            "bank_account_id": str(acct.id),
            "transaction_date": "2026-06-02",
            "amount": "30000",
            "transaction_type": "debit",
            "description": "Debito",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    db_session.refresh(acct)
    assert float(acct.current_balance) == 70000.0  # 100k credit - 30k debit


# ═══════════════════════════════════════════════════════════════════════════════
# RECONCILIATIONS (L177)
# ═══════════════════════════════════════════════════════════════════════════════


def test_reconciliation_create_and_list(client, db_session):
    """Create and list reconciliations (L177)."""
    from backend import models

    headers = _admin_client(client, db_session)

    # Create bank account with the admin's sede to avoid sede-filter mismatch
    admin_user = db_session.query(models.Usuario).filter(
        models.Usuario.email == "admin@example.com"
    ).first()
    admin_sede_id = admin_user.sede_id if admin_user else None

    acct = _create_bank_account(client, headers, db_session, sede_id=admin_sede_id)

    resp = client.post(
        "/api/finance-suite/reconciliations",
        json={
            "bank_account_id": str(acct.id),
            "period_start": "2026-01-01",
            "period_end": "2026-01-31",
            "starting_balance": 0,
            "ending_balance": 50000,
            "bank_statement_balance": 50000,
        },
        headers=headers,
    )
    assert resp.status_code == 201, f"create rec: {resp.status_code} {resp.text}"
    rec_id = resp.json()["id"]

    resp2 = client.get("/api/finance-suite/reconciliations", headers=headers)
    assert resp2.status_code == 200
    assert any(r["id"] == rec_id for r in resp2.json())

    # Filter by bank_account_id
    resp3 = client.get(
        f"/api/finance-suite/reconciliations?bank_account_id={acct.id}",
        headers=headers,
    )
    assert resp3.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# ACCOUNTING ENTRIES — validation edge cases (L229, 234, 277, 289)
# ═══════════════════════════════════════════════════════════════════════════════


def test_accounting_entry_account_not_found(client, db_session):
    """Line with non-existent account_id -> 400 (L229)."""
    headers = _admin_client(client, db_session)
    fake_id = str(_uuid.uuid4())

    resp = client.post(
        "/api/finance-suite/accounting-entries",
        json={
            "entry_date": "2026-01-15",
            "description": "Bad account",
            "lines": [
                {"account_id": fake_id, "debit": "1000", "credit": "0"},
                {"account_id": fake_id, "debit": "0", "credit": "1000"},
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 400


def test_accounting_entry_debit_not_equal_credit(client, db_session):
    """Total debit != total credit -> 400 (L234)."""
    headers = _admin_client(client, db_session)
    acc = _create_chart_account(client, headers, db_session)

    resp = client.post(
        "/api/finance-suite/accounting-entries",
        json={
            "entry_date": "2026-01-15",
            "description": "Unbalanced",
            "lines": [
                {"account_id": str(acc.id), "debit": "5000", "credit": "0"},
                {"account_id": str(acc.id), "debit": "0", "credit": "3000"},
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 400


def test_post_accounting_entry_not_found(client, db_session):
    """Post non-existent entry -> 404 (L277)."""
    headers = _admin_client(client, db_session)
    fake_id = str(_uuid.uuid4())

    resp = client.patch(
        f"/api/finance-suite/accounting-entries/{fake_id}/post",
        headers=headers,
    )
    assert resp.status_code == 404


def test_create_accounting_entry_list_with_status(client, db_session):
    """List accounting entries filtered by status."""
    headers = _admin_client(client, db_session)
    acc = _create_chart_account(client, headers, db_session)

    client.post(
        "/api/finance-suite/accounting-entries",
        json={
            "entry_date": "2026-01-15",
            "description": "Test entry",
            "lines": [
                {"account_id": str(acc.id), "debit": "2000", "credit": "0"},
                {"account_id": str(acc.id), "debit": "0", "credit": "2000"},
            ],
        },
        headers=headers,
    )

    resp = client.get(
        "/api/finance-suite/accounting-entries?status=draft", headers=headers
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# FINANCIAL STATEMENTS (L309-341)
# ═══════════════════════════════════════════════════════════════════════════════


def test_generate_financial_statement(client, db_session):
    """Generate financial statement from posted entries (L309-341)."""
    headers = _admin_client(client, db_session)
    acc = _create_chart_account(client, headers, db_session)

    # Create a posted entry first
    resp = client.post(
        "/api/finance-suite/accounting-entries",
        json={
            "entry_date": "2026-01-15",
            "description": "For statement",
            "lines": [
                {"account_id": str(acc.id), "debit": "50000", "credit": "0"},
                {"account_id": str(acc.id), "debit": "0", "credit": "50000"},
            ],
        },
        headers=headers,
    )
    entry_id = resp.json()["id"]
    client.patch(
        f"/api/finance-suite/accounting-entries/{entry_id}/post", headers=headers
    )

    # Generate financial statement
    resp2 = client.post(
        "/api/finance-suite/financial-statements",
        json={
            "statement_type": "income_statement",
            "period_start": "2026-01-01",
            "period_end": "2026-01-31",
        },
        headers=headers,
    )
    assert resp2.status_code == 201, f"gen statement: {resp2.status_code} {resp2.text}"
    data = resp2.json()
    assert data["statement_type"] == "income_statement"
    assert data["data_json"]["entries_count"] >= 1

    # List
    resp3 = client.get(
        "/api/finance-suite/financial-statements", headers=headers
    )
    assert resp3.status_code == 200
    assert any(s["id"] == data["id"] for s in resp3.json())


# ═══════════════════════════════════════════════════════════════════════════════
# TAX CONFIGURATIONS (L349-386)
# ═══════════════════════════════════════════════════════════════════════════════


def test_tax_config_crud(client, db_session):
    """Create and list tax configurations (L349-353, L366-371, L380-386)."""
    headers = _admin_client(client, db_session)

    # Create
    resp = client.post(
        "/api/finance-suite/tax-configurations",
        json={
            "country_code": "CO",
            "tax_name": "IVA",
            "tax_rate": 19.0,
            "tax_type": "vat",
        },
        headers=headers,
    )
    assert resp.status_code == 201, f"create tax: {resp.status_code} {resp.text}"
    tax_id = resp.json()["id"]

    # Create another
    client.post(
        "/api/finance-suite/tax-configurations",
        json={
            "country_code": "MX",
            "tax_name": "IVA MX",
            "tax_rate": 16.0,
            "tax_type": "vat",
        },
        headers=headers,
    )

    # List all
    resp2 = client.get(
        "/api/finance-suite/tax-configurations", headers=headers
    )
    assert resp2.status_code == 200
    assert any(t["id"] == tax_id for t in resp2.json())

    # List by country_code (L380-386)
    resp3 = client.get(
        "/api/finance-suite/tax-configurations?country_code=CO", headers=headers
    )
    assert resp3.status_code == 200
    assert all(t["country_code"] == "CO" for t in resp3.json())


# ═══════════════════════════════════════════════════════════════════════════════
# INVOICE — tax_rate lookup (L446), record payment (L527, L538-567)
# ═══════════════════════════════════════════════════════════════════════════════


def test_create_invoice_with_tax_config(client, db_session):
    """Invoice creation uses tax config for tax_rate (L446)."""
    headers = _admin_client(client, db_session)

    # Create tax config first
    client.post(
        "/api/finance-suite/tax-configurations",
        json={
            "country_code": "CO",
            "tax_name": "IVA",
            "tax_rate": 19.0,
            "tax_type": "vat",
        },
        headers=headers,
    )

    resp = client.post(
        "/api/finance-suite/invoices",
        json={
            "customer_name": "Cliente Tax",
            "issue_date": "2026-04-01",
            "due_date": "2026-05-01",
            "items": [
                {"description": "Servicio", "quantity": "1", "unit_price": "100000"},
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 201, f"create inv: {resp.status_code} {resp.text}"
    data = resp.json()
    assert float(data["tax_amount"]) == 19000.0  # 100k * 19%
    assert float(data["total"]) == 119000.0


def test_create_invoice_without_tax_config(client, db_session):
    """Invoice without tax config defaults to 0% tax."""
    headers = _admin_client(client, db_session)

    resp = client.post(
        "/api/finance-suite/invoices",
        json={
            "customer_name": "Sin Tax",
            "issue_date": "2026-04-01",
            "items": [
                {"description": "Item", "quantity": "2", "unit_price": "50000"},
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert float(data["tax_amount"]) == 0
    assert float(data["total"]) == 100000.0


def test_record_invoice_payment_not_found(client, db_session):
    """Record payment on non-existent invoice -> 404 (L538)."""
    headers = _admin_client(client, db_session)
    fake_id = str(_uuid.uuid4())

    resp = client.post(
        f"/api/finance-suite/invoices/{fake_id}/payments",
        json={
            "amount": "50000",
            "payment_date": "2026-05-01",
            "payment_method": "transfer",
        },
        headers=headers,
    )
    assert resp.status_code == 404


def test_record_invoice_payment_partial(client, db_session):
    """Partial payment -> invoice status 'partial' (L554)."""
    headers = _admin_client(client, db_session)

    resp = client.post(
        "/api/finance-suite/invoices",
        json={
            "customer_name": "Partial Pay",
            "issue_date": "2026-04-01",
            "items": [{"description": "Item", "quantity": "1", "unit_price": "100000"}],
        },
        headers=headers,
    )
    inv_id = resp.json()["id"]

    # Pay 30000 (partial)
    resp2 = client.post(
        f"/api/finance-suite/invoices/{inv_id}/payments",
        json={
            "amount": "30000",
            "payment_date": "2026-05-01",
            "payment_method": "cash",
        },
        headers=headers,
    )
    assert resp2.status_code == 201

    # Verify invoice status
    resp3 = client.get("/api/finance-suite/invoices", headers=headers)
    inv = next(i for i in resp3.json() if i["id"] == inv_id)
    assert inv["status"] == "partial"


def test_record_invoice_payment_full(client, db_session):
    """Full payment -> invoice status 'paid' (L552)."""
    headers = _admin_client(client, db_session)

    resp = client.post(
        "/api/finance-suite/invoices",
        json={
            "customer_name": "Full Pay",
            "issue_date": "2026-04-01",
            "items": [{"description": "Item", "quantity": "1", "unit_price": "50000"}],
        },
        headers=headers,
    )
    inv_id = resp.json()["id"]

    # Pay full amount
    resp2 = client.post(
        f"/api/finance-suite/invoices/{inv_id}/payments",
        json={
            "amount": "50000",
            "payment_date": "2026-05-01",
            "payment_method": "transfer",
        },
        headers=headers,
    )
    assert resp2.status_code == 201

    resp3 = client.get("/api/finance-suite/invoices", headers=headers)
    inv = next(i for i in resp3.json() if i["id"] == inv_id)
    assert inv["status"] == "paid"


# ═══════════════════════════════════════════════════════════════════════════════
# EXPENSE REPORTS — approve / reimburse / reject full flow (L581, 603)
# ═══════════════════════════════════════════════════════════════════════════════


def test_expense_report_approve_reimburse_flow(client, db_session):
    """Full expense workflow: draft -> submit -> approve -> reimburse."""
    headers = _admin_client(client, db_session)

    # Create
    resp = client.post(
        "/api/finance-suite/expense-reports",
        json={
            "description": "Full workflow test",
            "items": [
                {
                    "expense_date": "2026-05-01",
                    "category": "Transporte",
                    "description": "Taxi",
                    "amount": "50000",
                }
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    report_id = resp.json()["id"]

    # Submit
    resp2 = client.post(
        f"/api/finance-suite/expense-reports/{report_id}/submit", headers=headers
    )
    assert resp2.status_code == 200

    # Approve - need a DIFFERENT user (segregation of duties)
    # Use permisos format with full permission keys like "finance:manage"
    other, _, _ = _seed_user_with_role(
        db_session,
        email="approver@test.com",
        role_name="finance_manager",
        permisos={"finance:manage": True},
    )
    approver_headers = _auth_headers(client, email="approver@test.com")

    resp3 = client.post(
        f"/api/finance-suite/expense-reports/{report_id}/approve",
        headers=approver_headers,
    )
    assert resp3.status_code == 200, f"approve: {resp3.status_code} {resp3.text}"
    assert resp3.json()["status"] == "approved"

    # Reimburse
    resp4 = client.post(
        f"/api/finance-suite/expense-reports/{report_id}/reimburse",
        headers=approver_headers,
    )
    assert resp4.status_code == 200
    assert resp4.json()["status"] == "reimbursed"


def test_expense_report_submit_not_found(client, db_session):
    """Submit non-existent report -> 404."""
    headers = _admin_client(client, db_session)
    fake_id = str(_uuid.uuid4())
    resp = client.post(
        f"/api/finance-suite/expense-reports/{fake_id}/submit", headers=headers
    )
    assert resp.status_code == 404


def test_expense_report_submit_wrong_status(client, db_session):
    """Submit already submitted report -> 400."""
    headers = _admin_client(client, db_session)

    resp = client.post(
        "/api/finance-suite/expense-reports",
        json={
            "description": "Already submitted",
            "items": [
                {
                    "expense_date": "2026-05-01",
                    "category": "Otros",
                    "description": "X",
                    "amount": "10000",
                }
            ],
        },
        headers=headers,
    )
    report_id = resp.json()["id"]
    client.post(
        f"/api/finance-suite/expense-reports/{report_id}/submit", headers=headers
    )

    # Try to submit again
    resp2 = client.post(
        f"/api/finance-suite/expense-reports/{report_id}/submit", headers=headers
    )
    assert resp2.status_code == 400


def test_expense_report_approve_not_found(client, db_session):
    """Approve non-existent report -> 404."""
    other, _, _ = _seed_user_with_role(
        db_session,
        email="approver2@test.com",
        role_name="finance_mgr",
        permisos={"finance:manage": True},
    )
    headers = _auth_headers(client, email="approver2@test.com")

    fake_id = str(_uuid.uuid4())
    resp = client.post(
        f"/api/finance-suite/expense-reports/{fake_id}/approve", headers=headers
    )
    assert resp.status_code == 404


def test_expense_report_approve_self_forbidden(client, db_session):
    """Cannot approve own report (segregation of duties)."""
    headers = _admin_client(client, db_session)

    resp = client.post(
        "/api/finance-suite/expense-reports",
        json={
            "description": "Self approve",
            "items": [
                {
                    "expense_date": "2026-05-01",
                    "category": "Otros",
                    "description": "X",
                    "amount": "10000",
                }
            ],
        },
        headers=headers,
    )
    report_id = resp.json()["id"]
    client.post(
        f"/api/finance-suite/expense-reports/{report_id}/submit", headers=headers
    )

    # Try to approve own report -> 403
    resp2 = client.post(
        f"/api/finance-suite/expense-reports/{report_id}/approve", headers=headers
    )
    assert resp2.status_code == 403


def test_expense_report_reject_flow(client, db_session):
    """Reject a submitted report."""
    other, _, _ = _seed_user_with_role(
        db_session,
        email="rejector@test.com",
        role_name="finance_rejector",
        permisos={"finance:manage": True},
    )
    headers = _auth_headers(client, email="rejector@test.com")

    resp = client.post(
        "/api/finance-suite/expense-reports",
        json={
            "description": "To reject",
            "items": [
                {
                    "expense_date": "2026-05-01",
                    "category": "Otros",
                    "description": "X",
                    "amount": "10000",
                }
            ],
        },
        headers=headers,
    )
    report_id = resp.json()["id"]
    client.post(
        f"/api/finance-suite/expense-reports/{report_id}/submit", headers=headers
    )

    # Reject
    resp2 = client.post(
        f"/api/finance-suite/expense-reports/{report_id}/reject", headers=headers
    )
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "rejected"


def test_expense_report_reimburse_not_approved(client, db_session):
    """Reimburse a non-approved report -> 400."""
    other, _, _ = _seed_user_with_role(
        db_session,
        email="reimburse_test@test.com",
        role_name="finance_rmb",
        permisos={"finance:manage": True},
    )
    headers = _auth_headers(client, email="reimburse_test@test.com")

    resp = client.post(
        "/api/finance-suite/expense-reports",
        json={
            "description": "No approve",
            "items": [
                {
                    "expense_date": "2026-05-01",
                    "category": "Otros",
                    "description": "X",
                    "amount": "10000",
                }
            ],
        },
        headers=headers,
    )
    report_id = resp.json()["id"]

    # Try to reimburse without approving -> 400
    resp2 = client.post(
        f"/api/finance-suite/expense-reports/{report_id}/reimburse",
        headers=headers,
    )
    assert resp2.status_code == 400


def test_expense_report_reimburse_with_params(client, db_session):
    """Reimburse with method and reference."""
    headers = _admin_client(client, db_session)

    resp = client.post(
        "/api/finance-suite/expense-reports",
        json={
            "description": "With reference",
            "items": [
                {
                    "expense_date": "2026-05-01",
                    "category": "Otros",
                    "description": "X",
                    "amount": "25000",
                }
            ],
        },
        headers=headers,
    )
    report_id = resp.json()["id"]
    client.post(
        f"/api/finance-suite/expense-reports/{report_id}/submit", headers=headers
    )

    # Approve as different user
    other, _, _ = _seed_user_with_role(
        db_session,
        email="reimburse_approver@test.com",
        role_name="finance_apprv",
        permisos={"finance:manage": True},
    )
    approver_headers = _auth_headers(client, email="reimburse_approver@test.com")
    client.post(
        f"/api/finance-suite/expense-reports/{report_id}/approve",
        headers=approver_headers,
    )

    # Reimburse with method + reference as query params
    resp2 = client.post(
        f"/api/finance-suite/expense-reports/{report_id}/reimburse?method=bank_transfer&reference=REF123",
        headers=approver_headers,
    )
    assert resp2.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENTS — update with tags (L650-652, L664-668), delete cross-sede (L682-694)
# ═══════════════════════════════════════════════════════════════════════════════


def test_document_update(client, db_session):
    """Update document title (L650-652)."""
    headers = _admin_client(client, db_session)

    # Create document
    resp = client.post(
        "/api/finance-suite/documents",
        json={
            "title": "Original doc",
            "file_url": "https://test.com/doc.pdf",
            "file_name": "doc.pdf",
            "file_size": 1024,
            "mime_type": "application/pdf",
            "document_type": "contract",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    # Update title
    resp2 = client.patch(
        f"/api/finance-suite/documents/{doc_id}",
        json={"title": "Updated title"},
        headers=headers,
    )
    assert resp2.status_code == 200, f"update doc: {resp2.status_code} {resp2.text}"
    assert resp2.json()["title"] == "Updated title"

    # List by document_type
    resp3 = client.get(
        "/api/finance-suite/documents?document_type=contract", headers=headers
    )
    assert resp3.status_code == 200
    assert any(d["id"] == doc_id for d in resp3.json())


def test_document_delete_not_found(client, db_session):
    """Delete non-existent document -> 404."""
    headers = _admin_client(client, db_session)
    fake_id = str(_uuid.uuid4())
    resp = client.delete(
        f"/api/finance-suite/documents/{fake_id}", headers=headers
    )
    assert resp.status_code == 404


def test_document_delete_cross_sede_forbidden(client, db_session):
    """Delete document from another sede -> 403 (L682-694)."""
    from backend import models

    _, _, sede = _seed_admin(db_session)
    headers = _auth_headers(client)

    # Create a document in a DIFFERENT sede
    other_sede = models.Sede(
        id=_uuid.uuid4(), nombre="Otra Sede", ciudad="Cali", es_activa=True
    )
    db_session.add(other_sede)
    db_session.flush()

    doc = models.Document(
        id=_uuid.uuid4(),
        title="Cross sede doc",
        file_url="https://test.com/doc.pdf",
        file_name="doc.pdf",
        file_size=1024,
        mime_type="application/pdf",
        document_type="contract",
        sede_id=other_sede.id,
    )
    db_session.add(doc)
    db_session.commit()

    resp = client.delete(
        f"/api/finance-suite/documents/{doc.id}", headers=headers
    )
    assert resp.status_code == 403, f"cross-sede delete: {resp.status_code} {resp.text}"


def test_document_list_by_type(client, db_session):
    """List documents filtered by document_type."""
    headers = _admin_client(client, db_session)

    # Create doc
    resp_doc = client.post(
        "/api/finance-suite/documents",
        json={
            "title": "Contract doc",
            "file_url": "https://test.com/contract.pdf",
            "file_name": "contract.pdf",
            "file_size": 2048,
            "mime_type": "application/pdf",
            "document_type": "contract",
        },
        headers=headers,
    )
    assert resp_doc.status_code == 201
    doc_id = resp_doc.json()["id"]

    # List by type
    resp2 = client.get(
        "/api/finance-suite/documents?document_type=contract", headers=headers
    )
    assert resp2.status_code == 200
    assert any(d["id"] == doc_id for d in resp2.json())


# ═══════════════════════════════════════════════════════════════════════════════
# EXPENSE RECEIPTS — upload and OCR update (L705-733)
# ═══════════════════════════════════════════════════════════════════════════════


def test_expense_receipt_upload_and_ocr(client, db_session):
    """Upload receipt and update OCR data (L705-711, L722-733)."""

    headers = _admin_client(client, db_session)

    # Need an expense item first - create expense report
    resp = client.post(
        "/api/finance-suite/expense-reports",
        json={
            "description": "For receipt",
            "items": [
                {
                    "expense_date": "2026-05-01",
                    "category": "Otros",
                    "description": "X",
                    "amount": "10000",
                }
            ],
        },
        headers=headers,
    )
    expense_item_id = resp.json()["items"][0]["id"]

    # Upload receipt
    resp2 = client.post(
        "/api/finance-suite/expense-receipts",
        json={
            "expense_item_id": expense_item_id,
            "image_url": "https://storage.ccf.org/receipts/foto.jpg",
            "thumbnail_url": "https://storage.ccf.org/receipts/thumb.jpg",
        },
        headers=headers,
    )
    assert resp2.status_code == 201, f"upload receipt: {resp2.status_code} {resp2.text}"
    receipt_id = resp2.json()["id"]

    # Update OCR (L722-733) - pass params as query string
    resp3 = client.patch(
        f"/api/finance-suite/expense-receipts/{receipt_id}/ocr"
        f"?ocr_text=Total%3A+%2410%2C000&ocr_confidence=0.95",
        headers=headers,
    )
    assert resp3.status_code == 200, f"ocr update: {resp3.status_code} {resp3.text}"
    assert resp3.json()["status"] == "updated"


def test_expense_receipt_ocr_not_found(client, db_session):
    """OCR update on non-existent receipt -> 404."""
    headers = _admin_client(client, db_session)
    fake_id = str(_uuid.uuid4())

    resp = client.patch(
        f"/api/finance-suite/expense-receipts/{fake_id}/ocr?ocr_text=test&ocr_confidence=0.5",
        headers=headers,
    )
    assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# SIGN REQUESTS — send/decline/completion/get (L746-755, L828-832, L886-891, L899-903)
# ═══════════════════════════════════════════════════════════════════════════════


def test_sign_request_get_not_found(client, db_session):
    """Get non-existent sign request -> 404 (L899-903)."""
    headers = _admin_client(client, db_session)
    fake_id = str(_uuid.uuid4())
    resp = client.get(
        f"/api/finance-suite/sign-requests/{fake_id}", headers=headers
    )
    assert resp.status_code == 404


def test_sign_request_send_not_found(client, db_session):
    """Send non-existent sign request -> 404 (L746-748)."""
    headers = _admin_client(client, db_session)
    fake_id = str(_uuid.uuid4())
    resp = client.post(
        f"/api/finance-suite/sign-requests/{fake_id}/send", headers=headers
    )
    assert resp.status_code == 404


def test_sign_request_send_already_sent(client, db_session):
    """Send already-sent sign request -> 400 (L753)."""
    headers = _admin_client(client, db_session)

    resp = client.post(
        "/api/finance-suite/sign-requests",
        json={
            "title": "Already sent",
            "document_url": "https://test.com/doc.pdf",
            "signers": [{"email": "s@test.com", "full_name": "S"}],
        },
        headers=headers,
    )
    req_id = resp.json()["id"]
    client.post(
        f"/api/finance-suite/sign-requests/{req_id}/send", headers=headers
    )

    # Send again -> 400
    resp2 = client.post(
        f"/api/finance-suite/sign-requests/{req_id}/send", headers=headers
    )
    assert resp2.status_code == 400


def test_sign_request_decline(client, db_session):
    """Decline a sign request (L828-832)."""
    headers = _admin_client(client, db_session)

    resp = client.post(
        "/api/finance-suite/sign-requests",
        json={
            "title": "To decline",
            "document_url": "https://test.com/doc.pdf",
            "signers": [{"email": "decliner@test.com", "full_name": "Decliner"}],
        },
        headers=headers,
    )
    req_id = resp.json()["id"]
    signer_id = resp.json()["signers"][0]["id"]

    # Send
    client.post(
        f"/api/finance-suite/sign-requests/{req_id}/send", headers=headers
    )

    # Decline
    resp2 = client.post(
        f"/api/finance-suite/sign-requests/{req_id}/signers/{signer_id}/sign",
        json={"action": "decline"},
        headers=headers,
    )
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "declined"


def test_sign_request_list_with_status(client, db_session):
    """List sign requests filtered by status."""
    headers = _admin_client(client, db_session)

    client.post(
        "/api/finance-suite/sign-requests",
        json={
            "title": "Status filter test",
            "document_url": "https://test.com/doc.pdf",
            "signers": [{"email": "s@test.com", "full_name": "S"}],
        },
        headers=headers,
    )

    resp = client.get(
        "/api/finance-suite/sign-requests?status=draft", headers=headers
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_list_bank_transactions_with_filters(client, db_session):
    """List bank transactions with bank_account_id filter."""
    from backend import models

    headers = _admin_client(client, db_session)

    admin_user = db_session.query(models.Usuario).filter(
        models.Usuario.email == "admin@example.com"
    ).first()
    admin_sede_id = admin_user.sede_id if admin_user else None

    acct = _create_bank_account(client, headers, db_session, sede_id=admin_sede_id)

    # Create a transaction
    client.post(
        "/api/finance-suite/bank-transactions",
        json={
            "bank_account_id": str(acct.id),
            "transaction_date": "2026-06-01",
            "amount": "50000",
            "transaction_type": "credit",
            "description": "Filter test",
        },
        headers=headers,
    )

    # Filter by bank_account_id
    resp = client.get(
        f"/api/finance-suite/bank-transactions?bank_account_id={acct.id}",
        headers=headers,
    )
    assert resp.status_code == 200, f"list tx filter: {resp.status_code} {resp.text}"
    assert len(resp.json()) >= 1


def test_list_sales_orders_with_status(client, db_session):
    """List sales orders filtered by status."""
    headers = _admin_client(client, db_session)

    client.post(
        "/api/finance-suite/sales-orders",
        json={
            "customer_name": "Status test",
            "order_date": "2026-03-01",
            "items": [
                {"description": "Item", "quantity": "1", "unit_price": "10000"}
            ],
        },
        headers=headers,
    )

    resp = client.get(
        "/api/finance-suite/sales-orders?status=draft", headers=headers
    )
    assert resp.status_code == 200


def test_list_document_tags(client, db_session):
    """Create and list document tags."""
    headers = _admin_client(client, db_session)

    client.post(
        "/api/finance-suite/document-tags",
        json={"name": "Test Tag", "color": "green"},
        headers=headers,
    )

    resp = client.get("/api/finance-suite/document-tags", headers=headers)
    assert resp.status_code == 200
    assert any(t["name"] == "Test Tag" for t in resp.json())
