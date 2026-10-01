"""Unit and integration tests for Multi-Level Expense Approval in Finance Suite.

Circuit:
  draft -> pastor_review -> central_authorization -> approved -> disbursed
  (with rejection branch and audit trail)

Enforces:
  - Segregation of duties (cannot approve own report)
  - Zero external payment gateways (transfer / cash / caja menor only)
  - Full audit trail recording actor UUID and transition notes
"""

import uuid
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from backend import models
from backend.core.database import SessionLocal
from tests.conftest import auth_headers, seed_admin, seed_user_with_role


@pytest.fixture
def finance_env(client: TestClient, db_session):
    admin, admin_persona, sede = seed_admin(db_session)
    admin_headers = auth_headers(client, email=admin.email, password="testpass123")

    # Requester user
    requester, requester_persona, _ = seed_user_with_role(
        db_session,
        role_name=f"role_requester_{uuid.uuid4().hex[:6]}",
        permisos={"finance:read": "allow", "finance:edit": "allow"},
        sede_id=sede.id,
        email=f"requester_{uuid.uuid4().hex[:6]}@ccf.org",
    )
    requester_headers = auth_headers(client, email=requester.email, password="testpass123")

    # Pastor de sede
    pastor, pastor_persona, _ = seed_user_with_role(
        db_session,
        role_name=f"role_pastor_{uuid.uuid4().hex[:6]}",
        permisos={"finance:read": "allow", "finance:edit": "allow", "finance:manage": "allow"},
        sede_id=sede.id,
        email=f"pastor_{uuid.uuid4().hex[:6]}@ccf.org",
    )
    pastor_headers = auth_headers(client, email=pastor.email, password="testpass123")

    return {
        "admin": admin,
        "admin_headers": admin_headers,
        "requester": requester,
        "requester_headers": requester_headers,
        "pastor": pastor,
        "pastor_headers": pastor_headers,
        "sede": sede,
    }


def test_complete_multi_level_approval_flow(client: TestClient, finance_env):
    admin_h = finance_env["admin_headers"]
    requester = finance_env["requester"]
    requester_h = finance_env["requester_headers"]
    pastor = finance_env["pastor"]
    pastor_h = finance_env["pastor_headers"]

    # 1. Requester creates draft report
    create_payload = {
        "description": "Gastos de papelería y refrigerio escuela bíblica",
        "currency": "COP",
        "items": [
            {
                "expense_date": "2026-10-01",
                "category": "materials",
                "description": "Resmas de papel y marcadores",
                "amount": "45000.00",
                "currency": "COP",
                "vendor": "Papelería Central",
                "is_reimbursable": True,
            }
        ],
    }
    res = client.post("/api/finance-suite/expense-reports", json=create_payload, headers=requester_h)
    assert res.status_code == 201, res.text
    report_data = res.json()
    report_id = report_data["id"]
    assert report_data["status"] == "draft"

    # 2. Requester submits draft report -> pastor_review
    sub_res = client.post(
        f"/api/finance-suite/expense-reports/{report_id}/submit",
        json={"notes": "Listo para revisión pastoral"},
        headers=requester_h,
    )
    assert sub_res.status_code == 200
    assert sub_res.json()["status"] == "pastor_review"

    # 3. Segregation of duties: requester cannot approve their own report
    self_approve = client.post(
        f"/api/finance-suite/expense-reports/{report_id}/pastor-approve",
        headers=requester_h,
    )
    assert self_approve.status_code == 403

    # 4. Pastor de sede reviews and endorses -> central_authorization
    pastor_res = client.post(
        f"/api/finance-suite/expense-reports/{report_id}/pastor-approve",
        json={"notes": "Aprobado por el pastor de sede. Actividad autorizada."},
        headers=pastor_h,
    )
    assert pastor_res.status_code == 200
    assert pastor_res.json()["status"] == "central_authorization"

    # 5. Central administration authorizes -> approved
    central_res = client.post(
        f"/api/finance-suite/expense-reports/{report_id}/central-approve",
        json={"notes": "Presupuesto verificado por Contabilidad Central."},
        headers=admin_h,
    )
    assert central_res.status_code == 200
    assert central_res.json()["status"] == "approved"

    # 6. Rejection of external payment gateway (Mandatory CCF Rule)
    gateway_disburse = client.post(
        f"/api/finance-suite/expense-reports/{report_id}/disburse",
        json={"method": "stripe", "reference": "ch_123"},
        headers=admin_h,
    )
    assert gateway_disburse.status_code == 400
    assert "no permitidas" in gateway_disburse.text

    # 7. Internal disbursement (transfer / cash / caja menor) -> disbursed
    disburse_res = client.post(
        f"/api/finance-suite/expense-reports/{report_id}/disburse",
        json={"method": "transfer", "reference": "TRANSF-BANCOLOMBIA-9921", "notes": "Caja menor reembolsada"},
        headers=admin_h,
    )
    assert disburse_res.status_code == 200
    assert disburse_res.json()["status"] == "disbursed"

    # 8. Check full audit trail
    audit_res = client.get(
        f"/api/finance-suite/expense-reports/{report_id}/audit-trail",
        headers=admin_h,
    )
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert audit_data["status"] == "disbursed"
    history = audit_data["approval_history"]
    assert len(history) >= 4

    transitions = [(h["from_status"], h["to_status"]) for h in history]
    assert ("draft", "pastor_review") in transitions
    assert ("pastor_review", "central_authorization") in transitions
    assert ("central_authorization", "approved") in transitions
    assert ("approved", "disbursed") in transitions


def test_rejection_flow_with_reason(client: TestClient, finance_env):
    admin_h = finance_env["admin_headers"]
    requester_h = finance_env["requester_headers"]
    pastor_h = finance_env["pastor_headers"]

    create_payload = {
        "description": "Gastos no autorizados",
        "currency": "COP",
        "items": [
            {
                "expense_date": "2026-10-01",
                "category": "travel",
                "description": "Transporte no presupuestado",
                "amount": "120000.00",
                "currency": "COP",
                "is_reimbursable": True,
            }
        ],
    }
    res = client.post("/api/finance-suite/expense-reports", json=create_payload, headers=requester_h)
    report_id = res.json()["id"]

    # Submit
    client.post(f"/api/finance-suite/expense-reports/{report_id}/submit", headers=requester_h)

    # Pastor rejects with explicit reason
    reject_res = client.post(
        f"/api/finance-suite/expense-reports/{report_id}/reject",
        json={"reason": "El rubro de transporte de esta actividad no fue aprobado en el comité."},
        headers=pastor_h,
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "rejected"
    assert "no fue aprobado" in reject_res.json()["rejection_reason"]

    # Cannot disburse a rejected report
    disburse_attempt = client.post(
        f"/api/finance-suite/expense-reports/{report_id}/disburse",
        headers=admin_h,
    )
    assert disburse_attempt.status_code == 400
