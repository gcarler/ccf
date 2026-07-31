"""
Finance Suite API Coverage Tests — targets the uncovered regions in finance_suite.py.

Covers:
- Bank Accounts CRUD (lines 49-92)
- Bank Transactions CRUD (lines 99-142)
- Reconciliation CRUD (lines 149-178)
- Chart of Accounts CRUD (lines 185-199)
- Accounting Entries (lines 220+)
- Sales Orders (lines 300+)
- Invoices (lines 400+)
- Expense Reports (lines 500+)
- Documents (lines 600+)
- Sign Requests (lines 700+)
"""

import uuid
from datetime import datetime, timezone

import pytest

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="finance@test.com")
    headers = _auth_headers(client, email="finance@test.com", password="testpass123")
    return {"c": client, "h": headers}


# ═══════════════════════════════════════════════════════════════════════════════
# BANK ACCOUNTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestBankAccounts:
    def test_create_bank_account(self, full):
        c, h = full["c"], full["h"]
        resp = c.post(
            "/api/finance-suite/bank-accounts",
            json={"bank_name": "Banco Test", "account_number": "123456"},
            headers=h,
        )
        assert _ok(resp.status_code), f"create: {resp.status_code} {resp.text}"
        assert resp.json()["bank_name"] == "Banco Test"

    def test_list_bank_accounts(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/finance-suite/bank-accounts", headers=h)
        assert _ok(resp.status_code)

    def test_update_bank_account(self, full):
        c, h = full["c"], full["h"]
        resp = c.post(
            "/api/finance-suite/bank-accounts",
            json={"bank_name": "Original Bank", "account_number": "111"},
            headers=h,
        )
        assert _ok(resp.status_code)
        aid = resp.json()["id"]
        resp = c.patch(
            f"/api/finance-suite/bank-accounts/{aid}",
            json={"bank_name": "Updated Bank"},
            headers=h,
        )
        assert _ok(resp.status_code)
        assert resp.json()["bank_name"] == "Updated Bank"

    def test_update_bank_account_not_found(self, full):
        c, h = full["c"], full["h"]
        resp = c.patch(
            f"/api/finance-suite/bank-accounts/{uuid.uuid4()}",
            json={"bank_name": "X"},
            headers=h,
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# BANK TRANSACTIONS
# ═══════════════════════════════════════════════════════════════════════════════


class TestBankTransactions:
    def test_create_transaction(self, full):
        c, h = full["c"], full["h"]
        # Create account first
        resp = c.post(
            "/api/finance-suite/bank-accounts",
            json={"bank_name": "TX Bank", "account_number": "222"},
            headers=h,
        )
        assert _ok(resp.status_code)
        aid = resp.json()["id"]
        # Create transaction
        resp = c.post(
            "/api/finance-suite/bank-transactions",
            json={
                "bank_account_id": aid,
                "transaction_date": datetime.now(timezone.utc).date().isoformat(),
                "amount": 1000.00,
                "transaction_type": "credit",
                "description": "Test deposit",
            },
            headers=h,
        )
        assert _ok(resp.status_code), f"create_tx: {resp.status_code} {resp.text}"

    def test_list_transactions(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/finance-suite/bank-transactions", headers=h)
        assert _ok(resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# RECONCILIATIONS
# ═══════════════════════════════════════════════════════════════════════════════


class TestReconciliations:
    def test_create_reconciliation(self, full):
        c, h = full["c"], full["h"]
        resp = c.post(
            "/api/finance-suite/bank-accounts",
            json={"bank_name": "Rec Bank", "account_number": "333"},
            headers=h,
        )
        assert _ok(resp.status_code)
        aid = resp.json()["id"]
        now = datetime.now(timezone.utc)
        resp = c.post(
            "/api/finance-suite/reconciliations",
            json={
                "bank_account_id": aid,
                "period_start": now.date().isoformat(),
                "period_end": now.date().isoformat(),
                "starting_balance": 0,
                "ending_balance": 5000.00,
                "bank_statement_balance": 5000.00,
            },
            headers=h,
        )
        assert _ok(resp.status_code), f"create_rec: {resp.status_code} {resp.text}"

    def test_list_reconciliations(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/finance-suite/reconciliations", headers=h)
        assert _ok(resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# CHART OF ACCOUNTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestChartOfAccounts:
    def test_create_chart_account(self, full):
        c, h = full["c"], full["h"]
        resp = c.post(
            "/api/finance-suite/chart-of-accounts",
            json={"code": "1000", "name": "Cash", "account_type": "asset"},
            headers=h,
        )
        assert _ok(resp.status_code), f"create: {resp.status_code} {resp.text}"

    def test_list_chart_accounts(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/finance-suite/chart-of-accounts", headers=h)
        assert _ok(resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# ACCOUNTING ENTRIES
# ═══════════════════════════════════════════════════════════════════════════════


class TestAccountingEntries:
    def test_create_accounting_entry(self, full):
        c, h = full["c"], full["h"]
        # Create chart accounts first
        resp = c.post(
            "/api/finance-suite/chart-of-accounts",
            json={"code": "5000", "name": "Expense", "account_type": "expense"},
            headers=h,
        )
        assert _ok(resp.status_code)
        debit_id = resp.json()["id"]
        resp = c.post(
            "/api/finance-suite/chart-of-accounts",
            json={"code": "1000", "name": "Cash", "account_type": "asset"},
            headers=h,
        )
        assert _ok(resp.status_code)
        credit_id = resp.json()["id"]
        # Create entry
        resp = c.post(
            "/api/finance-suite/accounting-entries",
            json={
                "entry_date": datetime.now(timezone.utc).date().isoformat(),
                "description": "Test entry",
                "lines": [
                    {"account_id": debit_id, "debit": 100.00, "credit": 0},
                    {"account_id": credit_id, "debit": 0, "credit": 100.00},
                ],
            },
            headers=h,
        )
        assert _ok(resp.status_code), f"create_entry: {resp.status_code} {resp.text}"

    def test_list_accounting_entries(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/finance-suite/accounting-entries", headers=h)
        assert _ok(resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# SALES ORDERS
# ═══════════════════════════════════════════════════════════════════════════════


class TestSalesOrders:
    def test_create_sales_order(self, full):
        c, h = full["c"], full["h"]
        resp = c.post(
            "/api/finance-suite/sales-orders",
            json={
                "customer_name": "Test Customer",
                "order_date": datetime.now(timezone.utc).date().isoformat(),
                "items": [{"description": "Item 1", "quantity": 1, "unit_price": 50.00}],
            },
            headers=h,
        )
        assert _ok(resp.status_code), f"create_so: {resp.status_code} {resp.text}"

    def test_list_sales_orders(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/finance-suite/sales-orders", headers=h)
        assert _ok(resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# INVOICES
# ═══════════════════════════════════════════════════════════════════════════════


class TestInvoices:
    def test_create_invoice(self, full):
        c, h = full["c"], full["h"]
        resp = c.post(
            "/api/finance-suite/invoices",
            json={
                "customer_name": "Invoice Customer",
                "issue_date": datetime.now(timezone.utc).date().isoformat(),
                "items": [{"description": "Service", "quantity": 1, "unit_price": 200.00}],
            },
            headers=h,
        )
        assert _ok(resp.status_code), f"create_inv: {resp.status_code} {resp.text}"

    def test_list_invoices(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/finance-suite/invoices", headers=h)
        assert _ok(resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPENSE REPORTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestExpenseReports:
    def test_create_expense_report(self, full):
        c, h = full["c"], full["h"]
        resp = c.post(
            "/api/finance-suite/expense-reports",
            json={
                "description": "Test Expense",
                "items": [
                    {
                        "description": "Lunch",
                        "amount": 25.00,
                        "expense_date": datetime.now(timezone.utc).date().isoformat(),
                        "category": "food",
                    }
                ],
            },
            headers=h,
        )
        assert _ok(resp.status_code), f"create_exp: {resp.status_code} {resp.text}"

    def test_list_expense_reports(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/finance-suite/expense-reports", headers=h)
        assert _ok(resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestDocuments:
    def test_create_document(self, full):
        c, h = full["c"], full["h"]
        resp = c.post(
            "/api/finance-suite/documents",
            json={
                "title": "Test Doc",
                "file_url": "/uploads/test.pdf",
                "file_name": "test.pdf",
                "file_size": 1024,
                "mime_type": "application/pdf",
                "document_type": "contract",
            },
            headers=h,
        )
        assert _ok(resp.status_code), f"create_doc: {resp.status_code} {resp.text}"

    def test_list_documents(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/finance-suite/documents", headers=h)
        assert _ok(resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════════
# SIGN REQUESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestSignRequests:
    def test_create_sign_request(self, full):
        c, h = full["c"], full["h"]
        resp = c.post(
            "/api/finance-suite/sign-requests",
            json={
                "title": "Sign Test",
                "document_url": "/uploads/contract.pdf",
                "signers": [{"email": "signer@test.com", "full_name": "Test Signer"}],
            },
            headers=h,
        )
        assert _ok(resp.status_code), f"create_sign: {resp.status_code} {resp.text}"

    def test_list_sign_requests(self, full):
        c, h = full["c"], full["h"]
        resp = c.get("/api/finance-suite/sign-requests", headers=h)
        assert _ok(resp.status_code)
