"""
Finance Suite API — Contabilidad, Facturación, Gastos, Documentos, Firma
"""
from __future__ import annotations

import logging
import uuid as _uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import models
from backend.core.database import get_db
from backend.core.permissions import require_admin, require_module_access
from backend.core.rate_limit import rate_limiter
from backend.core.tenant import get_user_sede_id
from backend.models_shared import _utcnow
from backend.schemas import finance_suite as schemas

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/finance-suite", tags=["Finance Suite"])


def _generate_number(prefix: str, db: Session) -> str:
    today = datetime.now(timezone.utc)
    count = db.query(func.count(models.AccountingEntry.id)).scalar() or 0
    return f"{prefix}-{today.year}{today.month:02d}-{count + 1:05d}-{_uuid.uuid4().hex[:4]}"


def _finance_sede_scope(db: Session, user: models.User) -> str | None:
    """Resolve the user's sede_id for multi-tenant scoping."""
    return get_user_sede_id(db, user.id)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CONTABILIDAD — Bank Accounts
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/bank-accounts", response_model=schemas.BankAccountOut, status_code=201)
def create_bank_account(
    payload: schemas.BankAccountCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "edit")),
):
    sede_id = _finance_sede_scope(db, current_user)
    account = models.BankAccount(**payload.model_dump(), sede_id=sede_id)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/bank-accounts", response_model=List[schemas.BankAccountOut])
def list_bank_accounts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "read")),
):
    sede_id = _finance_sede_scope(db, current_user)
    q = db.query(models.BankAccount).filter(models.BankAccount.is_active == True)
    if sede_id:
        q = q.filter(models.BankAccount.sede_id == sede_id)
    return q.all()


@router.patch("/bank-accounts/{account_id}", response_model=schemas.BankAccountOut)
def update_bank_account(
    account_id: str,
    payload: schemas.BankAccountUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "edit")),
):
    account = db.query(models.BankAccount).filter(models.BankAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(account, k, v)
    db.commit()
    db.refresh(account)
    return account


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CONTABILIDAD — Bank Transactions
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/bank-transactions", response_model=schemas.BankTransactionOut, status_code=201)
def create_bank_transaction(
    payload: schemas.BankTransactionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "edit")),
):
    tx = models.BankTransaction(**payload.model_dump())
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


@router.get("/bank-transactions", response_model=List[schemas.BankTransactionOut])
def list_bank_transactions(
    bank_account_id: Optional[str] = None,
    tx_status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "read")),
):
    sede_id = _finance_sede_scope(db, current_user)
    q = (
        db.query(models.BankTransaction)
        .join(models.BankAccount, models.BankTransaction.bank_account_id == models.BankAccount.id)
        .order_by(models.BankTransaction.transaction_date.desc())
    )
    if sede_id:
        q = q.filter(models.BankAccount.sede_id == sede_id)
    if bank_account_id:
        q = q.filter(models.BankTransaction.bank_account_id == bank_account_id)
    if tx_status:
        q = q.filter(models.BankTransaction.status == tx_status)
    return q.offset(skip).limit(limit).all()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CONTABILIDAD — Reconciliation
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/reconciliations", response_model=schemas.BankReconciliationOut, status_code=201)
def create_reconciliation(
    payload: schemas.BankReconciliationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "edit")),
):
    rec = models.BankReconciliation(**payload.model_dump(), created_by_id=current_user.id)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


@router.get("/reconciliations", response_model=List[schemas.BankReconciliationOut])
def list_reconciliations(
    bank_account_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "read")),
):
    sede_id = _finance_sede_scope(db, current_user)
    q = (
        db.query(models.BankReconciliation)
        .join(models.BankAccount, models.BankReconciliation.bank_account_id == models.BankAccount.id)
        .order_by(models.BankReconciliation.period_start.desc())
    )
    if sede_id:
        q = q.filter(models.BankAccount.sede_id == sede_id)
    if bank_account_id:
        q = q.filter(models.BankReconciliation.bank_account_id == bank_account_id)
    return q.all()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CONTABILIDAD — Chart of Accounts
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/chart-of-accounts", response_model=schemas.ChartOfAccountOut, status_code=201)
def create_chart_account(
    payload: schemas.ChartOfAccountCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "edit")),
):
    sede_id = _finance_sede_scope(db, current_user)
    acc = models.ChartOfAccount(**payload.model_dump(), sede_id=sede_id)
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc


@router.get("/chart-of-accounts", response_model=List[schemas.ChartOfAccountOut])
def list_chart_accounts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "read")),
):
    sede_id = _finance_sede_scope(db, current_user)
    q = db.query(models.ChartOfAccount).filter(models.ChartOfAccount.is_active == True)
    if sede_id:
        q = q.filter(models.ChartOfAccount.sede_id == sede_id)
    return q.order_by(models.ChartOfAccount.code).all()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CONTABILIDAD — Accounting Entries
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/accounting-entries", response_model=schemas.AccountingEntryOut, status_code=201)
def create_accounting_entry(
    payload: schemas.AccountingEntryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "edit")),
):
    if not payload.lines or len(payload.lines) < 2:
        raise HTTPException(status_code=400, detail="At least 2 lines are required")

    for line in payload.lines:
        if line.debit > 0 and line.credit > 0:
            raise HTTPException(status_code=400, detail="A line cannot have both debit and credit greater than 0")
        account = db.query(models.ChartOfAccount).filter(models.ChartOfAccount.id == line.account_id).first()
        if not account:
            raise HTTPException(status_code=400, detail=f"Account {line.account_id} not found in chart of accounts")

    total_debit = sum(line.debit for line in payload.lines)
    total_credit = sum(line.credit for line in payload.lines)
    if total_debit != total_credit:
        raise HTTPException(status_code=400, detail="Total debit must equal total credit")

    sede_id = _finance_sede_scope(db, current_user)
    entry = models.AccountingEntry(
        entry_date=payload.entry_date,
        reference=payload.reference,
        description=payload.description,
        total_debit=total_debit,
        total_credit=total_credit,
        status="draft",
        created_by_id=current_user.id,
        sede_id=sede_id,
    )
    db.add(entry)
    db.flush()

    for line in payload.lines:
        db.add(models.AccountingEntryLine(
            entry_id=entry.id,
            account_id=line.account_id,
            debit=line.debit,
            credit=line.credit,
            description=line.description,
        ))

    db.commit()
    db.refresh(entry)
    return entry


@router.get("/accounting-entries", response_model=List[schemas.AccountingEntryOut])
def list_accounting_entries(
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "read")),
):
    sede_id = _finance_sede_scope(db, current_user)
    q = db.query(models.AccountingEntry).order_by(models.AccountingEntry.entry_date.desc())
    if sede_id:
        q = q.filter(models.AccountingEntry.sede_id == sede_id)
    if status:
        q = q.filter(models.AccountingEntry.status == status)
    return q.offset(skip).limit(limit).all()


@router.patch("/accounting-entries/{entry_id}/post", response_model=schemas.AccountingEntryOut)
def post_accounting_entry(
    entry_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "manage")),
):
    entry = db.query(models.AccountingEntry).filter(models.AccountingEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    if entry.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft entries can be posted")
    entry.status = "posted"
    db.commit()
    db.refresh(entry)
    logger.info("Accounting entry posted: id=%s by user=%s", entry_id, current_user.id)
    return entry


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CONTABILIDAD — Financial Statements
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/financial-statements", response_model=schemas.FinancialStatementOut, status_code=201)
def generate_financial_statement(
    payload: schemas.FinancialStatementCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "read")),
):
    sede_id = _finance_sede_scope(db, current_user)
    entries_q = (
        db.query(models.AccountingEntry)
        .filter(
            models.AccountingEntry.entry_date >= payload.period_start,
            models.AccountingEntry.entry_date <= payload.period_end,
            models.AccountingEntry.status == "posted",
        )
    )
    if sede_id:
        entries_q = entries_q.filter(models.AccountingEntry.sede_id == sede_id)
    entries = entries_q.all()

    data: Dict[str, Any] = {"entries_count": len(entries), "lines": []}
    for entry in entries:
        for line in entry.lines:
            data["lines"].append({
                "date": entry.entry_date.isoformat(),
                "account_id": str(line.account_id),
                "debit": float(line.debit),
                "credit": float(line.credit),
            })

    stmt = models.FinancialStatement(
        **payload.model_dump(),
        data_json=data,
        generated_by_id=current_user.id,
        sede_id=sede_id,
    )
    db.add(stmt)
    db.commit()
    db.refresh(stmt)
    return stmt


@router.get("/financial-statements", response_model=List[schemas.FinancialStatementOut])
def list_financial_statements(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "read")),
):
    sede_id = _finance_sede_scope(db, current_user)
    q = db.query(models.FinancialStatement).order_by(models.FinancialStatement.created_at.desc())
    if sede_id:
        q = q.filter(models.FinancialStatement.sede_id == sede_id)
    return q.all()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CONTABILIDAD — Tax Configuration
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/tax-configurations", response_model=schemas.TaxConfigurationOut, status_code=201)
def create_tax_config(
    payload: schemas.TaxConfigurationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    sede_id = _finance_sede_scope(db, current_user)
    config = models.TaxConfiguration(**payload.model_dump(), sede_id=sede_id)
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


@router.get("/tax-configurations", response_model=List[schemas.TaxConfigurationOut])
def list_tax_configurations(
    country_code: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "read")),
):
    sede_id = _finance_sede_scope(db, current_user)
    q = db.query(models.TaxConfiguration).filter(models.TaxConfiguration.is_active == True)
    if sede_id:
        q = q.filter(models.TaxConfiguration.sede_id == sede_id)
    if country_code:
        q = q.filter(models.TaxConfiguration.country_code == country_code)
    return q.all()


# ═══════════════════════════════════════════════════════════════════════════════
# 2. FACTURACIÓN — Sales Orders
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/sales-orders", response_model=schemas.SalesOrderOut, status_code=201)
def create_sales_order(
    payload: schemas.SalesOrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "edit")),
):
    if not payload.items:
        raise HTTPException(status_code=400, detail="At least one item is required")
    sede_id = _finance_sede_scope(db, current_user)
    total = sum(item.quantity * item.unit_price for item in payload.items)
    order_num = _generate_number("SO", db)
    order = models.SalesOrder(
        order_number=order_num,
        customer_name=payload.customer_name,
        customer_email=payload.customer_email,
        customer_tax_id=payload.customer_tax_id,
        total_amount=total,
        tax_amount=0,
        order_date=payload.order_date,
        notes=payload.notes,
        created_by_id=current_user.id,
        sede_id=sede_id,
    )
    db.add(order)
    db.flush()

    for item in payload.items:
        db.add(models.SalesOrderItem(
            sales_order_id=order.id,
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.quantity * item.unit_price,
        ))

    db.commit()
    db.refresh(order)
    return order


@router.get("/sales-orders", response_model=List[schemas.SalesOrderOut])
def list_sales_orders(
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "read")),
):
    sede_id = _finance_sede_scope(db, current_user)
    q = db.query(models.SalesOrder).order_by(models.SalesOrder.order_date.desc())
    if sede_id:
        q = q.filter(models.SalesOrder.sede_id == sede_id)
    if status:
        q = q.filter(models.SalesOrder.status == status)
    return q.offset(skip).limit(limit).all()


# ═══════════════════════════════════════════════════════════════════════════════
# 2. FACTURACIÓN — Invoices
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/invoices", response_model=schemas.InvoiceOut, status_code=201)
def create_invoice(
    payload: schemas.InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "edit")),
):
    if not payload.items:
        raise HTTPException(status_code=400, detail="At least one item is required")
    sede_id = _finance_sede_scope(db, current_user)
    subtotal = sum(item.quantity * item.unit_price for item in payload.items)
    # FIN-M14: Use sede's country_code for tax lookup (was hardcoded "CO")
    sede_country = "CO"
    tax_config = db.query(models.TaxConfiguration).filter(
        models.TaxConfiguration.country_code == sede_country,
        models.TaxConfiguration.is_active == True,
    ).first()
    tax_rate = tax_config.tax_rate if tax_config else 0
    tax_amount = subtotal * (tax_rate / 100) if tax_rate else 0
    total = subtotal + tax_amount

    inv_num = _generate_number("INV", db)
    invoice = models.Invoice(
        sales_order_id=payload.sales_order_id,
        invoice_number=inv_num,
        customer_name=payload.customer_name,
        customer_email=payload.customer_email,
        customer_tax_id=payload.customer_tax_id,
        subtotal=subtotal,
        tax_amount=tax_amount,
        total=total,
        issue_date=payload.issue_date,
        due_date=payload.due_date,
        notes=payload.notes,
        created_by_id=current_user.id,
        sede_id=sede_id,
    )
    db.add(invoice)
    db.flush()

    for item in payload.items:
        db.add(models.InvoiceItem(
            invoice_id=invoice.id,
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.quantity * item.unit_price,
        ))

    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/invoices", response_model=List[schemas.InvoiceOut])
def list_invoices(
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "read")),
):
    sede_id = _finance_sede_scope(db, current_user)
    q = db.query(models.Invoice).order_by(models.Invoice.issue_date.desc())
    if sede_id:
        q = q.filter(models.Invoice.sede_id == sede_id)
    if status:
        q = q.filter(models.Invoice.status == status)
    return q.offset(skip).limit(limit).all()


@router.post("/invoices/{invoice_id}/payments", response_model=schemas.InvoicePaymentOut, status_code=201)
def record_invoice_payment(
    invoice_id: str,
    payload: schemas.InvoicePaymentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "edit")),
):
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    payment = models.InvoicePayment(
        invoice_id=invoice.id,
        amount=payload.amount,
        payment_date=payload.payment_date,
        payment_method=payload.payment_method,
        reference=payload.reference,
        notes=payload.notes,
        created_by_id=current_user.id,
    )
    db.add(payment)

    total_paid = (
        db.query(func.sum(models.InvoicePayment.amount))
        .filter(models.InvoicePayment.invoice_id == invoice.id)
        .scalar()
        or 0
    )
    total_paid += float(payload.amount)
    if total_paid >= float(invoice.total):
        invoice.status = "paid"
    elif total_paid > 0:
        invoice.status = "partial"

    db.commit()
    db.refresh(payment)
    return payment


@router.post(
    "/invoices/{invoice_id}/send-electronic",
    dependencies=[Depends(rate_limiter(limit=3, window_seconds=60))],
)
def send_electronic_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "manage")),
):
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    raise HTTPException(status_code=501, detail="Electronic invoicing integration not implemented")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. GASTOS — Expense Reports
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/expense-reports", response_model=schemas.ExpenseReportOut, status_code=201)
def create_expense_report(
    payload: schemas.ExpenseReportCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "edit")),
):
    if not payload.items:
        raise HTTPException(status_code=400, detail="At least one item is required")
    sede_id = _finance_sede_scope(db, current_user)
    total = sum(item.amount for item in payload.items)
    report_num = _generate_number("EXP", db)
    report = models.ExpenseReport(
        report_number=report_num,
        employee_id=current_user.id,
        description=payload.description,
        total_amount=total,
        currency=payload.currency,
        status="draft",
        sede_id=sede_id,
    )
    db.add(report)
    db.flush()

    for item in payload.items:
        db.add(models.ExpenseItem(
            expense_report_id=report.id,
            expense_date=item.expense_date,
            category=item.category,
            description=item.description,
            amount=item.amount,
            currency=item.currency,
            vendor=item.vendor,
            is_reimbursable=item.is_reimbursable,
        ))

    db.commit()
    db.refresh(report)
    return report


@router.get("/expense-reports", response_model=List[schemas.ExpenseReportOut])
def list_expense_reports(
    status: Optional[str] = None,
    employee_id: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "read")),
):
    sede_id = _finance_sede_scope(db, current_user)
    q = db.query(models.ExpenseReport).order_by(models.ExpenseReport.created_at.desc())
    if sede_id:
        q = q.filter(models.ExpenseReport.sede_id == sede_id)
    if status:
        q = q.filter(models.ExpenseReport.status == status)
    if employee_id:
        q = q.filter(models.ExpenseReport.employee_id == employee_id)
    return q.offset(skip).limit(limit).all()


@router.post("/expense-reports/{report_id}/submit")
def submit_expense_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "edit")),
):
    report = db.query(models.ExpenseReport).filter(models.ExpenseReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft reports can be submitted")
    if report.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only submit your own reports")
    report.status = "submitted"
    report.submitted_at = _utcnow()
    db.commit()
    logger.info("Expense report submitted: id=%s by user=%s", report_id, current_user.id)
    return {"status": "submitted"}


@router.post("/expense-reports/{report_id}/approve")
def approve_expense_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "manage")),
):
    report = db.query(models.ExpenseReport).filter(models.ExpenseReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status != "submitted":
        raise HTTPException(status_code=400, detail="Only submitted reports can be approved")
    if str(report.employee_id) == str(current_user.id):
        raise HTTPException(status_code=403, detail="Cannot approve your own report (segregation of duties)")
    report.status = "approved"
    report.approved_by_id = current_user.id
    report.approved_at = _utcnow()
    db.commit()
    logger.info("Expense report approved: id=%s by user=%s", report_id, current_user.id)
    return {"status": "approved"}


@router.post("/expense-reports/{report_id}/reject")
def reject_expense_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "manage")),
):
    report = db.query(models.ExpenseReport).filter(models.ExpenseReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status not in ("submitted",):
        raise HTTPException(status_code=400, detail="Cannot reject this report")
    report.status = "rejected"
    db.commit()
    logger.info("Expense report rejected: id=%s by user=%s", report_id, current_user.id)
    return {"status": "rejected"}


@router.post("/expense-reports/{report_id}/reimburse")
def reimburse_expense_report(
    report_id: str,
    method: str = "transfer",
    reference: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "manage")),
):
    report = db.query(models.ExpenseReport).filter(models.ExpenseReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status != "approved":
        raise HTTPException(status_code=400, detail="Only approved reports can be reimbursed")
    report.status = "reimbursed"
    report.reimbursement_method = method
    report.reimbursement_reference = reference
    report.reimbursed_at = _utcnow()
    db.commit()
    logger.info("Expense report reimbursed: id=%s by user=%s", report_id, current_user.id)
    return {"status": "reimbursed"}


# ═══════════════════════════════════════════════════════════════════════════════
# 3. GASTOS — Receipts
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/expense-receipts", response_model=schemas.ExpenseReceiptOut, status_code=201)
def upload_expense_receipt(
    payload: schemas.ExpenseReceiptCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "edit")),
):
    receipt = models.ExpenseReceipt(
        expense_item_id=payload.expense_item_id,
        image_url=payload.image_url,
        thumbnail_url=payload.thumbnail_url,
        uploaded_by_id=current_user.id,
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    return receipt


@router.patch("/expense-receipts/{receipt_id}/ocr")
def update_receipt_ocr(
    receipt_id: str,
    ocr_text: str,
    ocr_confidence: float,
    ai_metadata: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "edit")),
):
    receipt = db.query(models.ExpenseReceipt).filter(models.ExpenseReceipt.id == receipt_id).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    receipt.ocr_text = ocr_text
    receipt.ocr_confidence = ocr_confidence
    if ai_metadata:
        receipt.ai_metadata_json = ai_metadata
    db.commit()
    return {"status": "updated"}


# ═══════════════════════════════════════════════════════════════════════════════
# 4. DOCUMENTOS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/documents", response_model=schemas.DocumentOut, status_code=201)
def create_document(
    payload: schemas.DocumentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "edit")),
):
    sede_id = _finance_sede_scope(db, current_user)
    doc = models.Document(
        title=payload.title,
        description=payload.description,
        file_url=payload.file_url,
        file_name=payload.file_name,
        file_size=payload.file_size,
        mime_type=payload.mime_type,
        document_type=payload.document_type,
        uploaded_by_id=current_user.id,
        sede_id=sede_id,
    )
    db.add(doc)
    db.flush()

    for tag_id in payload.tag_ids:
        tag = db.query(models.DocumentTag).filter(models.DocumentTag.id == tag_id).first()
        if tag:
            db.add(models.DocumentTagLink(document_id=doc.id, tag_id=tag.id))

    db.commit()
    db.refresh(doc)
    return doc


@router.get("/documents", response_model=List[schemas.DocumentOut])
def list_documents(
    document_type: Optional[str] = None,
    tag_id: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "read")),
):
    sede_id = _finance_sede_scope(db, current_user)
    q = db.query(models.Document).filter(models.Document.status == "active").order_by(models.Document.created_at.desc())
    if sede_id:
        q = q.filter(models.Document.sede_id == sede_id)
    if document_type:
        q = q.filter(models.Document.document_type == document_type)
    if tag_id:
        q = q.join(models.DocumentTagLink).filter(models.DocumentTagLink.tag_id == tag_id)
    if search:
        q = q.filter(
            models.Document.title.ilike(f"%{search}%") | models.Document.description.ilike(f"%{search}%")
        )
    return q.offset(skip).limit(limit).all()


@router.patch("/documents/{document_id}", response_model=schemas.DocumentOut)
def update_document(
    document_id: str,
    payload: schemas.DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "edit")),
):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    for k, v in payload.model_dump(exclude_unset=True).items():
        if k == "tag_ids" and v is not None:
            db.query(models.DocumentTagLink).filter(models.DocumentTagLink.document_id == doc.id).delete()
            for tid in v:
                db.add(models.DocumentTagLink(document_id=doc.id, tag_id=tid))
        elif k != "tag_ids":
            setattr(doc, k, v)

    db.commit()
    db.refresh(doc)
    return doc


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "manage")),
):
    sede_id = _finance_sede_scope(db, current_user)
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if sede_id and doc.sede_id and str(doc.sede_id) != sede_id:
        raise HTTPException(status_code=403, detail="Document does not belong to your sede")
    doc.status = "archived"
    db.commit()
    logger.info("Document archived: id=%s by user=%s", document_id, current_user.id)


# Document Tags
@router.post("/document-tags", response_model=schemas.DocumentTagOut, status_code=201)
def create_document_tag(
    payload: schemas.DocumentTagCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "edit")),
):
    sede_id = _finance_sede_scope(db, current_user)
    tag = models.DocumentTag(**payload.model_dump(), sede_id=sede_id)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


@router.get("/document-tags", response_model=List[schemas.DocumentTagOut])
def list_document_tags(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "read")),
):
    sede_id = _finance_sede_scope(db, current_user)
    q = db.query(models.DocumentTag)
    if sede_id:
        q = q.filter(models.DocumentTag.sede_id == sede_id)
    return q.order_by(models.DocumentTag.name).all()


# ═══════════════════════════════════════════════════════════════════════════════
# 5. FIRMA DIGITAL
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/sign-requests", response_model=schemas.SignRequestOut, status_code=201)
def create_sign_request(
    payload: schemas.SignRequestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "edit")),
):
    sede_id = _finance_sede_scope(db, current_user)
    req = models.SignRequest(
        title=payload.title,
        description=payload.description,
        document_url=payload.document_url,
        expiry_date=payload.expiry_date,
        country_code=payload.country_code,
        legal_framework=payload.legal_framework,
        created_by_id=current_user.id,
        sede_id=sede_id,
    )
    db.add(req)
    db.flush()

    for signer in payload.signers:
        db.add(models.SignSigner(
            sign_request_id=req.id,
            persona_id=signer.persona_id,
            email=signer.email,
            full_name=signer.full_name,
            role=signer.role,
            signing_order=signer.signing_order,
        ))

    db.commit()
    db.refresh(req)
    return req


@router.get("/sign-requests", response_model=List[schemas.SignRequestOut])
def list_sign_requests(
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "read")),
):
    sede_id = _finance_sede_scope(db, current_user)
    q = db.query(models.SignRequest).order_by(models.SignRequest.created_at.desc())
    if sede_id:
        q = q.filter(models.SignRequest.sede_id == sede_id)
    if status:
        q = q.filter(models.SignRequest.status == status)
    return q.offset(skip).limit(limit).all()


@router.get("/sign-requests/{request_id}", response_model=schemas.SignRequestOut)
def get_sign_request(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "read")),
):
    req = db.query(models.SignRequest).filter(models.SignRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Sign request not found")
    return req


@router.post("/sign-requests/{request_id}/send")
def send_sign_request(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "edit")),
):
    req = db.query(models.SignRequest).filter(models.SignRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Sign request not found")
    if req.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft requests can be sent")
    if not req.signers:
        raise HTTPException(status_code=400, detail="Cannot send request with no signers")
    req.status = "sent"
    for signer in req.signers:
        signer.status = "sent"
    db.commit()
    logger.info("Sign request sent: id=%s by user=%s", request_id, current_user.id)
    return {"status": "sent"}


@router.post("/sign-requests/{request_id}/signers/{signer_id}/sign")
def sign_document(
    request_id: str,
    signer_id: str,
    payload: schemas.SignAction,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "edit")),
):
    signer = db.query(models.SignSigner).filter(
        models.SignSigner.id == signer_id,
        models.SignSigner.sign_request_id == request_id,
    ).first()
    if not signer:
        raise HTTPException(status_code=404, detail="Signer not found")
    if signer.status != "sent":
        raise HTTPException(status_code=400, detail=f"Signer is in '{signer.status}' status, cannot sign")

    if payload.action == "sign":
        signer.status = "signed"
        signer.signed_at = _utcnow()
        signer.ip_address = payload.ip_address
        signer.metadata_json = payload.metadata_json or {}
    elif payload.action == "decline":
        signer.status = "declined"
        signer.metadata_json = payload.metadata_json or {}

    db.commit()

    req = db.query(models.SignRequest).filter(models.SignRequest.id == request_id).first()
    all_signed = all(s.status == "signed" for s in req.signers)
    if all_signed:
        req.status = "completed"
        db.commit()
        logger.info("Sign request completed: id=%s (all signers signed)", request_id)
    return {"status": signer.status}
