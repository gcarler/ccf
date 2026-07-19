"""
Schemas for Finance Suite — Contabilidad, Facturación, Gastos, Documentos, Firma
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

orm_config: ConfigDict = ConfigDict(from_attributes=True)
forbid_config: ConfigDict = ConfigDict(extra='forbid')


# ═══════════════════════════════════════════════════════════════════════════════
# SHARED
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
# 0. FUND (models_crm.Fund)
# ═══════════════════════════════════════════════════════════════════════════════

class FundCreate(BaseModel):
    model_config = forbid_config
    name: str
    description: Optional[str] = None
    is_public: bool = False
    target_amount: Optional[Decimal] = None


class FundUpdate(BaseModel):
    model_config = forbid_config
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None
    target_amount: Optional[Decimal] = None


# ═══════════════════════════════════════════════════════════════════════════════
# 0b. DONATION PAYLOAD (for finance.py register_donation)
# ═══════════════════════════════════════════════════════════════════════════════

class RegisterDonationPayload(BaseModel):
    model_config = forbid_config
    fund_id: UUID
    amount: float
    donation_type: str = "Ofrenda"
    donor_name: Optional[str] = None
    persona_id: Optional[UUID] = None


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CONTABILIDAD
# ═══════════════════════════════════════════════════════════════════════════════

class BankAccountCreate(BaseModel):
    model_config = forbid_config
    bank_name: str = Field(max_length=200)
    account_number: str = Field(max_length=50)
    account_type: str = "checking"
    currency: str = "COP"


class BankAccountUpdate(BaseModel):
    model_config = forbid_config
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    account_type: Optional[str] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None


class BankAccountOut(BaseModel):
    model_config = orm_config
    id: UUID
    bank_name: str
    account_number: str
    account_type: str
    currency: str
    current_balance: Decimal
    is_active: bool
    created_at: datetime


class BankTransactionCreate(BaseModel):
    model_config = forbid_config
    bank_account_id: UUID
    transaction_date: date
    description: str
    reference: Optional[str] = None
    amount: Decimal
    transaction_type: str  # debit, credit
    external_id: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None


class BankTransactionOut(BaseModel):
    model_config = orm_config
    id: UUID
    bank_account_id: UUID
    transaction_date: date
    description: str
    reference: Optional[str]
    amount: Decimal
    transaction_type: str
    status: str
    reconciled_at: Optional[datetime]
    external_id: Optional[str]
    created_at: datetime


class BankReconciliationCreate(BaseModel):
    model_config = forbid_config
    bank_account_id: UUID
    period_start: date
    period_end: date
    starting_balance: Decimal
    ending_balance: Decimal
    bank_statement_balance: Decimal
    notes: Optional[str] = None


class BankReconciliationOut(BaseModel):
    model_config = orm_config
    id: UUID
    bank_account_id: UUID
    period_start: date
    period_end: date
    starting_balance: Decimal
    ending_balance: Decimal
    bank_statement_balance: Decimal
    status: str
    notes: Optional[str]
    created_at: datetime


class ChartOfAccountCreate(BaseModel):
    model_config = forbid_config
    code: str
    name: str
    account_type: str
    parent_id: Optional[UUID] = None


class ChartOfAccountOut(BaseModel):
    model_config = orm_config
    id: UUID
    code: str
    name: str
    account_type: str
    parent_id: Optional[UUID]
    is_active: bool
    created_at: datetime


class AccountingEntryLineCreate(BaseModel):
    model_config = forbid_config
    account_id: UUID
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    description: Optional[str] = None


class AccountingEntryCreate(BaseModel):
    model_config = forbid_config
    entry_date: date
    reference: Optional[str] = None
    description: str
    lines: List[AccountingEntryLineCreate]


class AccountingEntryLineOut(BaseModel):
    model_config = orm_config
    id: UUID
    account_id: UUID
    debit: Decimal
    credit: Decimal
    description: Optional[str]


class AccountingEntryOut(BaseModel):
    model_config = orm_config
    id: UUID
    entry_date: date
    reference: Optional[str]
    description: str
    total_debit: Decimal
    total_credit: Decimal
    status: str
    lines: List[AccountingEntryLineOut]
    created_at: datetime


class FinancialStatementCreate(BaseModel):
    model_config = forbid_config
    statement_type: str
    period_start: date
    period_end: date
    currency: str = "COP"


class FinancialStatementOut(BaseModel):
    model_config = orm_config
    id: UUID
    statement_type: str
    period_start: date
    period_end: date
    currency: str
    data_json: Dict[str, Any]
    created_at: datetime


class TaxConfigurationCreate(BaseModel):
    model_config = forbid_config
    country_code: str
    tax_name: str
    tax_rate: Decimal
    tax_type: str
    fiscal_id_label: str = "NIT"
    fiscal_id_regex: Optional[str] = None
    reporting_endpoint: Optional[str] = None


class TaxConfigurationOut(BaseModel):
    model_config = orm_config
    id: UUID
    country_code: str
    tax_name: str
    tax_rate: Decimal
    tax_type: str
    is_active: bool
    fiscal_id_label: str
    fiscal_id_regex: Optional[str]
    reporting_endpoint: Optional[str]
    created_at: datetime


# ═══════════════════════════════════════════════════════════════════════════════
# 2. FACTURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

class SalesOrderItemCreate(BaseModel):
    model_config = forbid_config
    description: str
    quantity: Decimal = Decimal("1")
    unit_price: Decimal


class SalesOrderCreate(BaseModel):
    model_config = forbid_config
    customer_name: str = Field(max_length=200)
    customer_email: Optional[str] = None
    customer_tax_id: Optional[str] = None
    order_date: date
    notes: Optional[str] = None
    items: List[SalesOrderItemCreate]


class SalesOrderItemOut(BaseModel):
    model_config = orm_config
    id: UUID
    description: str
    quantity: Decimal
    unit_price: Decimal
    total_price: Decimal


class SalesOrderOut(BaseModel):
    model_config = orm_config
    id: UUID
    order_number: str
    customer_name: str
    customer_email: Optional[str]
    customer_tax_id: Optional[str]
    total_amount: Decimal
    tax_amount: Decimal
    currency: str
    status: str
    order_date: date
    items: List[SalesOrderItemOut]
    created_at: datetime


class InvoiceItemCreate(BaseModel):
    model_config = forbid_config
    description: str
    quantity: Decimal = Decimal("1")
    unit_price: Decimal


class InvoiceCreate(BaseModel):
    model_config = forbid_config
    sales_order_id: Optional[UUID] = None
    customer_name: str = Field(max_length=200)
    customer_email: Optional[str] = None
    customer_tax_id: Optional[str] = None
    issue_date: date
    due_date: Optional[date] = None
    notes: Optional[str] = None
    items: List[InvoiceItemCreate]


class InvoiceItemOut(BaseModel):
    model_config = orm_config
    id: UUID
    description: str
    quantity: Decimal
    unit_price: Decimal
    total_price: Decimal


class InvoicePaymentCreate(BaseModel):
    model_config = forbid_config
    amount: Decimal
    payment_date: date
    payment_method: str = "transfer"
    reference: Optional[str] = None
    notes: Optional[str] = None


class InvoicePaymentOut(BaseModel):
    model_config = orm_config
    id: UUID
    amount: Decimal
    payment_date: date
    payment_method: str
    reference: Optional[str]
    created_at: datetime


class InvoiceOut(BaseModel):
    model_config = orm_config
    id: UUID
    invoice_number: str
    sales_order_id: Optional[UUID]
    customer_name: str
    customer_email: Optional[str]
    customer_tax_id: Optional[str]
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    currency: str
    status: str
    issue_date: date
    due_date: Optional[date]
    electronic_status: str
    items: List[InvoiceItemOut]
    payments: List[InvoicePaymentOut]
    created_at: datetime


# ═══════════════════════════════════════════════════════════════════════════════
# 3. GASTOS
# ═══════════════════════════════════════════════════════════════════════════════

class ExpenseItemCreate(BaseModel):
    model_config = forbid_config
    expense_date: date
    category: str
    description: str
    amount: Decimal
    currency: str = "COP"
    vendor: Optional[str] = None
    is_reimbursable: bool = True


class ExpenseReportCreate(BaseModel):
    model_config = forbid_config
    description: Optional[str] = None
    currency: str = "COP"
    items: List[ExpenseItemCreate]


class ExpenseItemOut(BaseModel):
    model_config = orm_config
    id: UUID
    expense_date: date
    category: str
    description: str
    amount: Decimal
    currency: str
    vendor: Optional[str]
    is_reimbursable: bool
    receipt: Optional["ExpenseReceiptOut"] = None
    created_at: datetime


class ExpenseReceiptCreate(BaseModel):
    model_config = forbid_config
    expense_item_id: UUID
    image_url: str
    thumbnail_url: Optional[str] = None


class ExpenseReceiptOut(BaseModel):
    model_config = orm_config
    id: UUID
    expense_item_id: UUID
    image_url: str
    thumbnail_url: Optional[str]
    ocr_text: Optional[str]
    ocr_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    ai_metadata_json: Optional[Dict[str, Any]]
    created_at: datetime


class ExpenseReportOut(BaseModel):
    model_config = orm_config
    id: UUID
    report_number: str
    employee_id: UUID
    description: Optional[str]
    total_amount: Decimal
    currency: str
    status: str
    submitted_at: Optional[datetime]
    approved_by_id: Optional[UUID]
    approved_at: Optional[datetime]
    reimbursed_at: Optional[datetime]
    items: List[ExpenseItemOut]
    created_at: datetime
    updated_at: datetime


# ═══════════════════════════════════════════════════════════════════════════════
# 4. DOCUMENTOS
# ═══════════════════════════════════════════════════════════════════════════════

class DocumentTagCreate(BaseModel):
    model_config = forbid_config
    name: str
    color: str = "#6B7280"


class DocumentTagOut(BaseModel):
    model_config = orm_config
    id: UUID
    name: str
    color: str
    is_ai_generated: bool
    created_at: datetime


class DocumentCreate(BaseModel):
    model_config = forbid_config
    title: str = Field(max_length=200)
    description: Optional[str] = None
    file_url: str = Field(max_length=2048)
    file_name: str
    file_size: int = 0
    mime_type: str
    document_type: str = "other"
    tag_ids: List[UUID] = []


class DocumentUpdate(BaseModel):
    model_config = forbid_config
    title: Optional[str] = None
    description: Optional[str] = None
    document_type: Optional[str] = None
    tag_ids: Optional[List[UUID]] = None
    status: Optional[str] = None


class DocumentOut(BaseModel):
    model_config = orm_config
    id: UUID
    title: str
    description: Optional[str]
    file_url: str
    file_name: str
    file_size: int
    mime_type: str
    document_type: str
    status: str
    ai_tags: List[str]
    ai_summary: Optional[str]
    ai_entities_json: Optional[Dict[str, Any]]
    tags: List[DocumentTagOut]
    created_at: datetime
    updated_at: datetime


# ═══════════════════════════════════════════════════════════════════════════════
# 5. FIRMA DIGITAL
# ═══════════════════════════════════════════════════════════════════════════════

class SignSignerCreate(BaseModel):
    model_config = forbid_config
    email: str
    full_name: str
    role: str = "signer"
    signing_order: int = 0
    persona_id: Optional[UUID] = None


class SignRequestCreate(BaseModel):
    model_config = forbid_config
    title: str = Field(max_length=200)
    description: Optional[str] = None
    document_url: str = Field(max_length=2048)
    expiry_date: Optional[datetime] = None
    country_code: str = "CO"
    legal_framework: str = "eidas"
    signers: List[SignSignerCreate]


class SignSignerOut(BaseModel):
    model_config = orm_config
    id: UUID
    email: str
    full_name: str
    role: str
    signing_order: int
    status: str
    signed_at: Optional[datetime]
    signature_image_url: Optional[str]


class SignRequestOut(BaseModel):
    model_config = orm_config
    id: UUID
    title: str
    description: Optional[str]
    document_url: str
    document_hash: Optional[str]
    status: str
    expiry_date: Optional[datetime]
    country_code: str
    legal_framework: str
    signers: List[SignSignerOut]
    created_at: datetime
    updated_at: datetime


class SignAction(BaseModel):
    model_config = forbid_config
    action: str  # sign, decline, remind
    ip_address: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None


# ═══════════════════════════════════════════════════════════════════════════════
# 6. MERCADOPAGO
# ═══════════════════════════════════════════════════════════════════════════════

class CreatePreferenceRequest(BaseModel):
    model_config = forbid_config
    amount: float = Field(gt=0)
    title: str = Field(default="Donación", max_length=200)
    description: Optional[str] = None
    donor_name: Optional[str] = None
    email: Optional[str] = None
