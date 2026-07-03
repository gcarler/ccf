"""
Finance Suite Models — Contabilidad, Facturación, Gastos, Documentos, Firma
"""
from __future__ import annotations

import enum as _enum
import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.models_shared import Base, _utcnow

# ═══════════════════════════════════════════════════════════════════════════════
# 1. CONTABILIDAD (Accounting)
# ═══════════════════════════════════════════════════════════════════════════════

class FiscalCountry(_enum.Enum):
    CO = "CO"  # Colombia — DIAN
    MX = "MX"  # México — SAT
    US = "US"  # Estados Unidos — IRS
    CL = "CL"  # Chile — SII
    PE = "PE"  # Perú — SUNAT


class BankAccount(Base):
    __tablename__ = "bank_accounts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    bank_name = Column(String(100), nullable=False, index=True)
    account_number = Column(String(50), nullable=False, index=True)
    account_type = Column(String(30), default="checking", index=True)  # checking, savings
    currency = Column(String(10), default="COP", index=True)
    current_balance = Column(Numeric(14, 2), default=0)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    transactions = relationship("BankTransaction", back_populates="bank_account", cascade="all, delete-orphan")
    reconciliations = relationship("BankReconciliation", back_populates="bank_account", cascade="all, delete-orphan")


class BankTransaction(Base):
    __tablename__ = "bank_transactions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_account_id = Column(UUID(as_uuid=True), ForeignKey("bank_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_date = Column(Date, nullable=False, index=True)
    description = Column(Text, nullable=False)
    reference = Column(String(100), nullable=True, index=True)
    amount = Column(Numeric(14, 2), nullable=False)
    transaction_type = Column(String(20), nullable=False, index=True)  # debit, credit
    status = Column(String(20), default="pending", index=True)  # pending, reconciled, disputed
    reconciled_at = Column(DateTime(timezone=True), nullable=True)
    reconciled_by_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    external_id = Column(String(100), nullable=True, index=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    bank_account = relationship("BankAccount", back_populates="transactions")
    reconciliation_lines = relationship("ReconciliationLine", back_populates="bank_transaction", cascade="all, delete-orphan")


class BankReconciliation(Base):
    __tablename__ = "bank_reconciliations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_account_id = Column(UUID(as_uuid=True), ForeignKey("bank_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date, nullable=False, index=True)
    starting_balance = Column(Numeric(14, 2), nullable=False)
    ending_balance = Column(Numeric(14, 2), nullable=False)
    bank_statement_balance = Column(Numeric(14, 2), nullable=False)
    status = Column(String(20), default="in_progress", index=True)  # in_progress, reconciled, closed
    notes = Column(Text, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    bank_account = relationship("BankAccount", back_populates="reconciliations")
    lines = relationship("ReconciliationLine", back_populates="reconciliation", cascade="all, delete-orphan")


class ReconciliationLine(Base):
    __tablename__ = "reconciliation_lines"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reconciliation_id = Column(UUID(as_uuid=True), ForeignKey("bank_reconciliations.id", ondelete="CASCADE"), nullable=False, index=True)
    bank_transaction_id = Column(UUID(as_uuid=True), ForeignKey("bank_transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    is_matched = Column(Boolean, default=False, index=True)
    difference = Column(Numeric(14, 2), default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    reconciliation = relationship("BankReconciliation", back_populates="lines")
    bank_transaction = relationship("BankTransaction", back_populates="reconciliation_lines")


class ChartOfAccount(Base):
    __tablename__ = "chart_of_accounts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    code = Column(String(20), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    account_type = Column(String(30), nullable=False, index=True)  # asset, liability, equity, revenue, expense
    parent_id = Column(UUID(as_uuid=True), ForeignKey("chart_of_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    children = relationship("ChartOfAccount", backref="parent", remote_side=[id])


class AccountingEntry(Base):
    __tablename__ = "accounting_entries"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    entry_date = Column(Date, nullable=False, index=True)
    reference = Column(String(100), nullable=True, index=True)
    description = Column(Text, nullable=False)
    total_debit = Column(Numeric(14, 2), nullable=False)
    total_credit = Column(Numeric(14, 2), nullable=False)
    status = Column(String(20), default="draft", index=True)  # draft, posted, reversed
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    lines = relationship("AccountingEntryLine", back_populates="entry", cascade="all, delete-orphan")


class AccountingEntryLine(Base):
    __tablename__ = "accounting_entry_lines"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_id = Column(UUID(as_uuid=True), ForeignKey("accounting_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("chart_of_accounts.id", ondelete="RESTRICT"), nullable=False, index=True)
    debit = Column(Numeric(14, 2), default=0)
    credit = Column(Numeric(14, 2), default=0)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    entry = relationship("AccountingEntry", back_populates="lines")


class FinancialStatement(Base):
    __tablename__ = "financial_statements"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    statement_type = Column(String(30), nullable=False, index=True)  # balance_sheet, income_statement, cash_flow
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date, nullable=False, index=True)
    currency = Column(String(10), default="COP")
    data_json = Column(JSON, default=dict)
    generated_by_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class TaxConfiguration(Base):
    __tablename__ = "tax_configurations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    country_code = Column(String(10), nullable=False, index=True)
    tax_name = Column(String(100), nullable=False)
    tax_rate = Column(Numeric(5, 2), nullable=False)
    tax_type = Column(String(30), nullable=False, index=True)  # iva, retencion, reteiva, etc.
    is_active = Column(Boolean, default=True, index=True)
    fiscal_id_label = Column(String(50), default="NIT")  # NIT, RFC, RUT, etc.
    fiscal_id_regex = Column(String(100), nullable=True)
    reporting_endpoint = Column(String(255), nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. FACTURACIÓN (Invoicing)
# ═══════════════════════════════════════════════════════════════════════════════

class SalesOrder(Base):
    __tablename__ = "sales_orders"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    customer_name = Column(String(200), nullable=False)
    customer_email = Column(String(200), nullable=True)
    customer_tax_id = Column(String(50), nullable=True, index=True)
    total_amount = Column(Numeric(14, 2), nullable=False)
    tax_amount = Column(Numeric(14, 2), default=0)
    currency = Column(String(10), default="COP")
    status = Column(String(20), default="draft", index=True)  # draft, confirmed, invoiced, cancelled
    order_date = Column(Date, nullable=False, index=True)
    notes = Column(Text, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    items = relationship("SalesOrderItem", back_populates="sales_order", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="sales_order")


class SalesOrderItem(Base):
    __tablename__ = "sales_order_items"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sales_order_id = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    description = Column(Text, nullable=False)
    quantity = Column(Numeric(10, 2), default=1)
    unit_price = Column(Numeric(14, 2), nullable=False)
    total_price = Column(Numeric(14, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    sales_order = relationship("SalesOrder", back_populates="items")


class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    sales_order_id = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True, index=True)
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    customer_name = Column(String(200), nullable=False)
    customer_email = Column(String(200), nullable=True)
    customer_tax_id = Column(String(50), nullable=True, index=True)
    subtotal = Column(Numeric(14, 2), nullable=False)
    tax_amount = Column(Numeric(14, 2), default=0)
    total = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(10), default="COP")
    status = Column(String(20), default="draft", index=True)  # draft, sent, paid, overdue, cancelled
    issue_date = Column(Date, nullable=False, index=True)
    due_date = Column(Date, nullable=True, index=True)
    electronic_id = Column(String(100), nullable=True, index=True)
    electronic_status = Column(String(30), default="not_sent", index=True)  # not_sent, sent, accepted, rejected
    electronic_response = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    sales_order = relationship("SalesOrder", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("InvoicePayment", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    description = Column(Text, nullable=False)
    quantity = Column(Numeric(10, 2), default=1)
    unit_price = Column(Numeric(14, 2), nullable=False)
    total_price = Column(Numeric(14, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    invoice = relationship("Invoice", back_populates="items")


class InvoicePayment(Base):
    __tablename__ = "invoice_payments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Numeric(14, 2), nullable=False)
    payment_date = Column(Date, nullable=False, index=True)
    payment_method = Column(String(30), default="transfer")  # transfer, cash, card, check
    reference = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    invoice = relationship("Invoice", back_populates="payments")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. GASTOS (Expenses)
# ═══════════════════════════════════════════════════════════════════════════════

class ExpenseReport(Base):
    __tablename__ = "expense_reports"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False, index=True)
    report_number = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    total_amount = Column(Numeric(14, 2), default=0)
    currency = Column(String(10), default="COP")
    status = Column(String(20), default="draft", index=True)  # draft, submitted, approved, rejected, reimbursed
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    approved_by_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    reimbursement_method = Column(String(30), nullable=True)  # transfer, cash
    reimbursement_reference = Column(String(100), nullable=True)
    reimbursed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    employee = relationship("Persona", foreign_keys=[employee_id])
    approver = relationship("Persona", foreign_keys=[approved_by_id])
    items = relationship("ExpenseItem", back_populates="expense_report", cascade="all, delete-orphan")


class ExpenseItem(Base):
    __tablename__ = "expense_items"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    expense_report_id = Column(UUID(as_uuid=True), ForeignKey("expense_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    expense_date = Column(Date, nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(10), default="COP")
    vendor = Column(String(150), nullable=True)
    is_reimbursable = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    expense_report = relationship("ExpenseReport", back_populates="items")
    receipt = relationship("ExpenseReceipt", back_populates="expense_item", uselist=False, cascade="all, delete-orphan")


class ExpenseReceipt(Base):
    __tablename__ = "expense_receipts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    expense_item_id = Column(UUID(as_uuid=True), ForeignKey("expense_items.id", ondelete="CASCADE"), nullable=False, index=True)
    image_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=True)
    ocr_text = Column(Text, nullable=True)
    ocr_confidence = Column(Float, nullable=True)
    ai_metadata_json = Column(JSON, default=dict)
    uploaded_by_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    expense_item = relationship("ExpenseItem", back_populates="receipt")


# ═══════════════════════════════════════════════════════════════════════════════
# 4. DOCUMENTOS (Documents)
# ═══════════════════════════════════════════════════════════════════════════════

class Document(Base):
    __tablename__ = "documents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    file_url = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, default=0)
    mime_type = Column(String(100), nullable=False)
    document_type = Column(String(50), default="other", index=True)  # invoice, contract, receipt, report, other
    status = Column(String(20), default="active", index=True)  # active, archived
    ai_tags = Column(JSON, default=list)
    ai_summary = Column(Text, nullable=True)
    ai_entities_json = Column(JSON, default=dict)
    uploaded_by_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    tags = relationship("DocumentTagLink", back_populates="document", cascade="all, delete-orphan")


class DocumentTag(Base):
    __tablename__ = "document_tags"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    color = Column(String(10), default="#6B7280")
    is_ai_generated = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        UniqueConstraint("sede_id", "name", name="uq_document_tag_sede_name"),
    )


class DocumentTagLink(Base):
    __tablename__ = "document_tag_links"
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("document_tags.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    document = relationship("Document", back_populates="tags")
    tag = relationship("DocumentTag")


# ═══════════════════════════════════════════════════════════════════════════════
# 5. FIRMA DIGITAL (Sign)
# ═══════════════════════════════════════════════════════════════════════════════

class SignRequest(Base):
    __tablename__ = "sign_requests"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    document_url = Column(String(500), nullable=False)
    document_hash = Column(String(128), nullable=True)
    status = Column(String(20), default="draft", index=True)  # draft, sent, completed, expired, cancelled
    expiry_date = Column(DateTime(timezone=True), nullable=True)
    country_code = Column(String(10), default="CO", index=True)
    legal_framework = Column(String(50), default="eidas", index=True)  # eidas, ueta, simple
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    signers = relationship("SignSigner", back_populates="sign_request", cascade="all, delete-orphan")


class SignSigner(Base):
    __tablename__ = "sign_signers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sign_request_id = Column(UUID(as_uuid=True), ForeignKey("sign_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=True, index=True)
    email = Column(String(200), nullable=False)
    full_name = Column(String(200), nullable=False)
    role = Column(String(50), default="signer")  # signer, witness, approver
    signing_order = Column(Integer, default=0)
    status = Column(String(20), default="pending", index=True)  # pending, sent, viewed, signed, declined
    signed_at = Column(DateTime(timezone=True), nullable=True)
    signature_image_url = Column(String(500), nullable=True)
    ip_address = Column(String(50), nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    sign_request = relationship("SignRequest", back_populates="signers")
