from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from backend import models
from tests.conftest import auth_headers, seed_admin, seed_user_with_role


def _finance_user(db_session, email: str, sede_id):
    return seed_user_with_role(
        db_session,
        role_name=f"finance_scope_{uuid.uuid4().hex[:8]}",
        email=email,
        sede_id=sede_id,
        permisos={"finance:manage": "allow"},
    )


def test_finance_mutations_reject_cross_sede_bank_account(client, db_session):
    _, _, sede_a = seed_admin(db_session, email="finance_scope_admin@example.com")
    _, _, sede_b = _finance_user(db_session, "finance_scope_actor@example.com", uuid.uuid4())
    account = models.BankAccount(
        id=uuid.uuid4(),
        sede_id=sede_a.id,
        bank_name="Sede A Bank",
        account_number="A-001",
        account_type="checking",
        currency="COP",
        current_balance=1000,
    )
    db_session.add(account)
    db_session.commit()

    actor_headers = auth_headers(client, email="finance_scope_actor@example.com")
    response = client.post(
        "/api/finance-suite/bank-transactions",
        json={
            "bank_account_id": str(account.id),
            "transaction_date": "2026-08-01",
            "description": "Cross-sede attempt",
            "amount": "500",
            "transaction_type": "credit",
        },
        headers=actor_headers,
    )

    assert response.status_code == 404
    db_session.refresh(account)
    assert float(account.current_balance) == 1000.0
    assert db_session.query(models.BankTransaction).filter_by(bank_account_id=account.id).count() == 0


def test_finance_mutations_reject_cross_sede_accounting_and_invoice(client, db_session):
    _, _, sede_a = seed_admin(db_session, email="finance_scope_admin2@example.com")
    _, _, sede_b = _finance_user(db_session, "finance_scope_actor2@example.com", uuid.uuid4())
    chart = models.ChartOfAccount(
        id=uuid.uuid4(),
        sede_id=sede_a.id,
        code="9001",
        name="Cuenta sede A",
        account_type="asset",
        is_active=True,
    )
    invoice = models.Invoice(
        id=uuid.uuid4(),
        sede_id=sede_a.id,
        invoice_number=f"INV-SCOPE-{uuid.uuid4().hex[:8]}",
        customer_name="Cliente sede A",
        subtotal=100,
        tax_amount=0,
        total=100,
        issue_date=date(2026, 8, 1),
    )
    db_session.add_all([chart, invoice])
    db_session.commit()

    actor_headers = auth_headers(client, email="finance_scope_actor2@example.com")
    entry_response = client.post(
        "/api/finance-suite/accounting-entries",
        json={
            "entry_date": "2026-08-01",
            "description": "Cross-sede journal",
            "lines": [
                {"account_id": str(chart.id), "debit": "100", "credit": "0"},
                {"account_id": str(chart.id), "debit": "0", "credit": "100"},
            ],
        },
        headers=actor_headers,
    )
    payment_response = client.post(
        f"/api/finance-suite/invoices/{invoice.id}/payments",
        json={"amount": "100", "payment_date": "2026-08-01"},
        headers=actor_headers,
    )

    assert entry_response.status_code == 400
    assert payment_response.status_code == 404
    assert db_session.query(models.AccountingEntry).count() == 0
    assert db_session.query(models.InvoicePayment).filter_by(invoice_id=invoice.id).count() == 0


def test_global_search_hides_cross_sede_and_deleted_projects(client, db_session):
    _, _, sede_a = seed_admin(db_session, email="search_scope_admin@example.com")
    _, _, sede_b = seed_user_with_role(
        db_session,
        role_name=f"search_scope_{uuid.uuid4().hex[:8]}",
        email="search_scope_actor@example.com",
        sede_id=uuid.uuid4(),
        permisos={},
    )
    project_a = models.Project(
        id=uuid.uuid4(), sede_id=sede_b.id, title="Scope visible project", description="scope marker"
    )
    project_b = models.Project(
        id=uuid.uuid4(), sede_id=sede_a.id, title="Scope hidden project", description="scope marker"
    )
    deleted_project = models.Project(
        id=uuid.uuid4(), sede_id=sede_a.id, title="Scope deleted project", description="scope marker", deleted_at=datetime.now(timezone.utc)
    )
    db_session.add_all([project_a, project_b, deleted_project])
    db_session.flush()
    db_session.add_all(
        [
            models.ProjectTask(id=uuid.uuid4(), project_id=project_a.id, title="Scope visible task"),
            models.ProjectTask(id=uuid.uuid4(), project_id=project_b.id, title="Scope hidden task"),
            models.ProjectTask(id=uuid.uuid4(), project_id=deleted_project.id, title="Scope deleted task"),
        ]
    )
    db_session.commit()

    actor_headers = auth_headers(client, email="search_scope_actor@example.com")
    response = client.get("/api/system/search?q=scope", headers=actor_headers)

    assert response.status_code == 200
    items = response.json()["items"]
    ids = {str(item["id"]) for item in items}
    assert str(project_a.id) in ids
    assert str(project_b.id) not in ids
    assert str(deleted_project.id) not in ids
    assert all(str(item.get("project_id", "")) not in {str(project_b.id), str(deleted_project.id)} for item in items if item["type"] == "task")
