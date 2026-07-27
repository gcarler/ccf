"""
Extended API tests for backend.api.finance_suite — covering remaining endpoints.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from backend import models
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="fin_ext@test.com")
    headers = _auth_headers(client, email="fin_ext@test.com", password="testpass123")
    return {"c": client, "h": headers}


class TestInvoicePayments:
    def test_not_found(self, full):
        assert full["c"].post(f"/api/finance-suite/invoices/{uuid.uuid4()}/payments",
            json={"amount": 100, "payment_date": datetime.now(timezone.utc).date().isoformat(),
                  "payment_method": "transfer"}, headers=full["h"]).status_code == 404

    def test_record(self, full, db_session):
        c, h, sede = full["c"], full["h"], db_session.query(models.Sede).first()
        inv = models.Invoice(id=uuid.uuid4(), invoice_number=f"INV-{uuid.uuid4().hex[:6]}",
            customer_name="Test", subtotal=500, total=500, status="issued",
            sede_id=sede.id, issue_date=datetime.now(timezone.utc).date())
        db_session.add(inv)
        db_session.commit()
        assert _ok(c.post(f"/api/finance-suite/invoices/{inv.id}/payments",
            json={"amount": 500, "payment_date": datetime.now(timezone.utc).date().isoformat(),
                  "payment_method": "transfer"}, headers=h).status_code)


class TestElectronicInvoice:
    def test_not_found(self, full):
        assert full["c"].post(f"/api/finance-suite/invoices/{uuid.uuid4()}/send-electronic",
            headers=full["h"]).status_code == 404

    def test_not_configured(self, full, db_session):
        c, h, sede = full["c"], full["h"], db_session.query(models.Sede).first()
        inv = models.Invoice(id=uuid.uuid4(), invoice_number=f"EI-{uuid.uuid4().hex[:6]}",
            customer_name="Test", subtotal=100, total=100, status="issued",
            sede_id=sede.id, issue_date=datetime.now(timezone.utc).date())
        db_session.add(inv)
        db_session.commit()
        assert c.post(f"/api/finance-suite/invoices/{inv.id}/send-electronic", headers=h).status_code == 422


class TestExpenseWorkflow:
    def test_submit_not_found(self, full):
        assert full["c"].post(f"/api/finance-suite/expense-reports/{uuid.uuid4()}/submit",
            headers=full["h"]).status_code == 404

    def test_submit(self, full, db_session):
        c, h, sede = full["c"], full["h"], db_session.query(models.Sede).first()
        user = db_session.query(models.Usuario).first()
        r = models.ExpenseReport(id=uuid.uuid4(), report_number=f"EXP-{uuid.uuid4().hex[:6]}",
            employee_id=user.id, total_amount=100, status="draft", sede_id=sede.id)
        db_session.add(r)
        db_session.commit()
        assert _ok(c.post(f"/api/finance-suite/expense-reports/{r.id}/submit", headers=h).status_code)

    def test_submit_wrong_status(self, full, db_session):
        c, h, sede = full["c"], full["h"], db_session.query(models.Sede).first()
        user = db_session.query(models.Usuario).first()
        r = models.ExpenseReport(id=uuid.uuid4(), report_number=f"EW-{uuid.uuid4().hex[:6]}",
            employee_id=user.id, total_amount=100, status="submitted", sede_id=sede.id)
        db_session.add(r)
        db_session.commit()
        assert c.post(f"/api/finance-suite/expense-reports/{r.id}/submit", headers=h).status_code == 400

    def test_submit_wrong_owner(self, full, db_session):
        c, h, sede = full["c"], full["h"], db_session.query(models.Sede).first()
        from tests.conftest import seed_user_with_role
        other, _, _ = seed_user_with_role(db_session, email="other_fin@test.com")
        r = models.ExpenseReport(id=uuid.uuid4(), report_number=f"EWO-{uuid.uuid4().hex[:6]}",
            employee_id=other.id, total_amount=100, status="draft", sede_id=sede.id)
        db_session.add(r)
        db_session.commit()
        assert c.post(f"/api/finance-suite/expense-reports/{r.id}/submit", headers=h).status_code == 403

    def test_approve_not_found(self, full):
        assert full["c"].post(f"/api/finance-suite/expense-reports/{uuid.uuid4()}/approve",
            headers=full["h"]).status_code == 404

    def test_approve_wrong_status(self, full, db_session):
        c, h, sede = full["c"], full["h"], db_session.query(models.Sede).first()
        r = models.ExpenseReport(id=uuid.uuid4(), report_number=f"EA-{uuid.uuid4().hex[:6]}",
            employee_id=uuid.uuid4(), total_amount=100, status="draft", sede_id=sede.id)
        db_session.add(r)
        db_session.commit()
        assert c.post(f"/api/finance-suite/expense-reports/{r.id}/approve", headers=h).status_code == 400

    def test_reject_not_found(self, full):
        assert full["c"].post(f"/api/finance-suite/expense-reports/{uuid.uuid4()}/reject",
            headers=full["h"]).status_code == 404

    def test_reject_wrong_status(self, full, db_session):
        c, h, sede = full["c"], full["h"], db_session.query(models.Sede).first()
        r = models.ExpenseReport(id=uuid.uuid4(), report_number=f"ER-{uuid.uuid4().hex[:6]}",
            employee_id=uuid.uuid4(), total_amount=100, status="draft", sede_id=sede.id)
        db_session.add(r)
        db_session.commit()
        assert c.post(f"/api/finance-suite/expense-reports/{r.id}/reject", headers=h).status_code == 400


class TestSignWorkflow:
    def test_send_not_found(self, full):
        assert full["c"].post(f"/api/finance-suite/sign-requests/{uuid.uuid4()}/send",
            headers=full["h"]).status_code == 404
    def test_sign_not_found(self, full):
        assert full["c"].post(f"/api/finance-suite/sign-requests/{uuid.uuid4()}/sign",
            headers=full["h"]).status_code == 404
    def test_decline_not_found(self, full):
        assert full["c"].post(f"/api/finance-suite/sign-requests/{uuid.uuid4()}/decline",
            headers=full["h"]).status_code == 404


class TestAccountingPost:
    def test_not_found(self, full):
        assert full["c"].patch(f"/api/finance-suite/accounting-entries/{uuid.uuid4()}/post",
            headers=full["h"]).status_code == 404

    def test_post(self, full, db_session):
        c, h, sede = full["c"], full["h"], db_session.query(models.Sede).first()
        ca = models.ChartOfAccount(id=uuid.uuid4(), code="2000", name="Revenue",
            account_type="revenue", sede_id=sede.id)
        db_session.add(ca)
        db_session.flush()
        entry = models.AccountingEntry(id=uuid.uuid4(), entry_date=datetime.now(timezone.utc).date(),
            description="Test", status="draft", total_debit=100, total_credit=100)
        db_session.add(entry)
        db_session.flush()
        db_session.add(models.AccountingEntryLine(id=uuid.uuid4(), entry_id=entry.id,
            account_id=ca.id, debit=100, credit=0))
        db_session.add(models.AccountingEntryLine(id=uuid.uuid4(), entry_id=entry.id,
            account_id=ca.id, debit=0, credit=100))
        db_session.commit()
        assert _ok(c.patch(f"/api/finance-suite/accounting-entries/{entry.id}/post", headers=h).status_code)
