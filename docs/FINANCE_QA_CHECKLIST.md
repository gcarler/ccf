# QA Checklist — Módulo Finance

**Actualizado:** 2026-07-25

---

## Backend — `/finance` (Legacy)

### Dashboard y resúmenes
- [x] `GET /api/finance/summary` retorna resumen financiero con gastos reales (no hardcodeados)
- [x] `GET /api/finance/funds` calcula egresos desde `ExpenseReport` reembolsados
- [x] `GET /api/finance/transactions` lista transacciones de la sede
- [x] Las transacciones se filtran por `sede_id` del usuario autenticado

### Donaciones y fondos
- [x] `GET /api/donation-categories` lista categorías
- [x] `POST /api/donation-categories` crea categoría
- [x] `GET /api/finance/funds` filtra fondos por sede
- [x] `POST /api/finance/register-donation` asocia donación a sede

---

## Backend — `/finance-suite` (Suite Completa)

### Cuentas bancarias
- [x] `POST /finance-suite/bank-accounts` crea cuenta con sede_id
- [x] `GET /finance-suite/bank-accounts` lista solo cuentas de la sede del usuario
- [x] `PATCH /finance-suite/bank-accounts/{id}` verifica sede antes de actualizar → HTTP 403 si mismatch
- [x] `POST /finance-suite/bank-transactions` actualiza `current_balance` de la cuenta (credit +, debit -)
- [x] Lock `with_for_update()` en actualización de balance (thread-safe)

### Plan de cuentas
- [x] `POST /finance-suite/chart-of-accounts` crea cuenta contable
- [x] `GET /finance-suite/chart-of-accounts` lista solo cuentas de la sede
- [x] Constraint único `(sede_id, code)` — no permite duplicados en misma sede

### Asientos contables
- [x] `POST /finance-suite/accounting-entries` valida partida doble (debit == credit, ≥2 líneas)
- [x] `GET /finance-suite/accounting-entries` paginado con skip/limit
- [x] `PATCH /finance-suite/accounting-entries/{id}/post` postea asiento (draft→posted, idempotente)
- [x] Cada cuenta referenciada existe en el plan de cuentas de la sede

### Facturación
- [x] `POST /finance-suite/sales-orders` crea orden de venta
- [x] `POST /finance-suite/invoices` crea factura con impuesto desde TaxConfiguration de la sede (fallback "CO")
- [x] `POST /finance-suite/invoices/{id}/payments` registra pago; actualiza status a partial/paid
- [x] Sobrepago rechazado (HTTP 400)
- [x] `POST /finance-suite/invoices/{id}/send-electronic` → HTTP 422 con mensaje amigable (no 501 genérico)
- [x] Badge `partial` visible en frontend (color info/azul)

### Gastos
- [x] `POST /finance-suite/expense-reports` crea reporte de gastos
- [x] `POST /finance-suite/expense-reports/{id}/submit` flujo draft→submitted
- [x] `POST /finance-suite/expense-reports/{id}/approve` flujo submitted→approved (aprobador ≠ empleado)
- [x] `POST /finance-suite/expense-reports/{id}/reject` flujo submitted→rejected
- [x] `POST /finance-suite/expense-reports/{id}/reimburse` flujo approved→reimbursed
- [x] Cross-sede: usuario de sede B no puede actuar sobre reportes de sede A

### Documentos
- [x] `POST /finance-suite/documents` crea documento con validación de `mime_type`
- [x] `GET /finance-suite/documents` lista documentos de la sede con filtro por tag
- [x] `DELETE /finance-suite/documents/{id}` soft-delete
- [x] `POST /finance-suite/document-tags` crea etiqueta con color
- [x] Frontend: toasts de éxito/error en todas las operaciones CRUD

### Firma digital
- [x] `POST /finance-suite/sign-requests` crea solicitud con firmantes
- [x] `POST /finance-suite/sign-requests/{id}/send` envía solicitud (draft→sent)
- [x] `POST /finance-suite/sign-requests/{id}/signers/{sid}/sign` firma con IP real del request
- [x] Frontend: IP no hardcodeada

---

## Multi-tenant

- [x] Transacciones de sede A no visibles desde sede B
- [x] Cuentas bancarias de sede A no modificables desde sede B (HTTP 403)
- [x] Facturas, gastos, documentos aislados por sede
- [x] Plan de cuentas aislado por sede

---

## Tests

- [x] `tests/test_finance_suite_api.py` — 33 casos: bank accounts, accounting, sales orders, invoices, expense reports, documents, sign requests
- [x] `test_update_bank_account_cross_sede_forbidden` — IDOR cross-sede → HTTP 403
- [x] `test_bank_transaction_updates_balance` — balance actualizado correctamente
- [x] Suite completa: `pytest tests/ -v` — 134 passed, 0 failures
