# API Contracts — Módulo Finance

**Actualizado:** 2026-07-25
**Base URL:** `/api`

---

## `/finance` — Router Legacy (Dashboard / Donaciones / Fondos)

### GET /finance/summary

Retorna resumen financiero del mes actual de la sede del usuario.

**Auth:** `finance:read`
**Multi-tenant:** Filtrado por `sede_id` del usuario autenticado.

**Response 200:**
```json
{
  "total_income": 5000000,
  "total_expense": 1200000,
  "balance": 3800000,
  "total_donations": 3,
  "month": "2026-07"
}
```

> ⚠️ `total_expense` se calcula desde `ExpenseReport` con `status="reimbursed"` del mes actual.
> No es un porcentaje hardcodeado.

---

### GET /finance/funds

Retorna fondos y balance consolidado de la sede.

**Auth:** `finance:read`
**Multi-tenant:** Filtrado por `sede_id`.

**Response 200:**
```json
{
  "fondos": [...],
  "total_ingresos": 5000000,
  "egresos_mes": 1200000,
  "balance": 3800000
}
```

---

### GET /finance/transactions

Lista transacciones de la sede con paginación.

**Auth:** `finance:read`
**Query params:** `skip`, `limit` (default 50)

---

### GET /finance/impact

Endpoint **público**. Retorna métricas de impacto misional.

**Auth:** No requerida
**Cache:** 120s en memoria (por proceso)

---

## `/finance-suite` — Suite Completa

### Cuentas Bancarias

#### POST /finance-suite/bank-accounts
Crea cuenta bancaria para la sede del usuario.

**Auth:** `finance:edit` | **Body:**
```json
{
  "bank_name": "Banco Davivienda",
  "account_number": "9876543210",
  "account_type": "checking",
  "currency": "COP",
  "current_balance": 0
}
```

#### GET /finance-suite/bank-accounts
Lista cuentas de la sede. `?limit=50`

#### PATCH /finance-suite/bank-accounts/{account_id}
Actualiza cuenta. **Verifica que la cuenta pertenezca a la sede del usuario → HTTP 403 si mismatch.**

#### POST /finance-suite/bank-transactions
Registra transacción y **actualiza `current_balance`** de la cuenta (credit → suma, debit → resta). Usa `SELECT FOR UPDATE` para prevenir race conditions.

**Body:**
```json
{
  "bank_account_id": "uuid",
  "transaction_type": "credit",
  "amount": 500000,
  "description": "Depósito"
}
```

---

### Plan de Cuentas

#### POST /finance-suite/chart-of-accounts
**Constraint:** `(sede_id, code)` es único — no se permiten códigos duplicados en la misma sede.

**Body:**
```json
{
  "code": "1105",
  "name": "Bancos",
  "account_type": "asset",
  "is_active": true
}
```

#### GET /finance-suite/chart-of-accounts
Lista cuentas contables de la sede. `?limit=200`

---

### Asientos Contables

#### POST /finance-suite/accounting-entries
Valida partida doble: `sum(debit) == sum(credit)`, mínimo 2 líneas, cada cuenta debe existir en el plan de cuentas de la sede.

**Body:**
```json
{
  "entry_date": "2026-07-25",
  "description": "Pago proveedor",
  "lines": [
    {"account_id": "uuid", "debit": 100000, "credit": 0, "description": "..."},
    {"account_id": "uuid", "debit": 0, "credit": 100000, "description": "..."}
  ]
}
```

#### PATCH /finance-suite/accounting-entries/{id}/post
Transición `draft → posted`. Idempotente: re-postear un asiento ya posteado retorna el asiento sin error.

---

### Facturación

#### POST /finance-suite/sales-orders
Crea orden de venta. Requiere ≥1 ítem.

#### GET /finance-suite/sales-orders
Lista órdenes de la sede. `?skip=0&limit=50`

#### POST /finance-suite/invoices
Crea factura. El impuesto se busca desde `TaxConfiguration` activa de la sede. Fallback a `country_code="CO"`.

**Estados:** `draft` → `sent` → `partial` → `paid` | `overdue` | `cancelled`

> `partial`: pago recibido pero insuficiente. `paid`: total cubierto. Sobrepago retorna HTTP 400.

#### POST /finance-suite/invoices/{id}/send-electronic
Envía factura electrónica.

**Nota:** La integración con operadores de FE no está implementada. Retorna `HTTP 422` con:
```json
{
  "code": "ELECTRONIC_INVOICING_NOT_CONFIGURED",
  "message": "La facturación electrónica no está habilitada para esta sede. Contacte al administrador."
}
```

---

### Gastos

Flujo de estados: `draft → submitted → approved → reimbursed` | `rejected`

**Segregación de deberes:** El aprobador no puede ser el mismo usuario que creó el reporte.

#### POST /finance-suite/expense-reports
#### POST /finance-suite/expense-reports/{id}/submit
#### POST /finance-suite/expense-reports/{id}/approve
#### POST /finance-suite/expense-reports/{id}/reject
#### POST /finance-suite/expense-reports/{id}/reimburse

---

### Documentos

#### POST /finance-suite/documents
`mime_type` validado contra lista permitida: `application/pdf`, `application/msword`, `application/vnd.openxmlformats-officedocument.*`, `image/jpeg`, `image/png`, `image/webp`, `text/plain`, `text/csv`.

#### GET /finance-suite/documents
Filtrable por tag. `?limit=100`

#### DELETE /finance-suite/documents/{id}
Soft-delete (setea `deleted_at`).

#### POST /finance-suite/document-tags
Crea etiqueta con color hex.

---

### Firma Digital

Flujo: `draft → sent → completed` | `expired` | `cancelled`

Roles de firmante: `signer`, `witness`, `approver`
Marcos legales: `eidas` (UE), `ueta` (USA), `simple`

#### POST /finance-suite/sign-requests
#### POST /finance-suite/sign-requests/{id}/send
#### GET /finance-suite/sign-requests/{id}
#### POST /finance-suite/sign-requests/{id}/signers/{signer_id}/sign

**Body:**
```json
{
  "action": "sign"
}
```

> La IP del firmante es capturada automáticamente por el backend desde `request.client.host`.
> No debe enviarse desde el cliente.

---

## Schemas — Validaciones generales

- Todos los schemas de entrada usan `extra='forbid'` (previene mass-assignment)
- `mime_type` en `DocumentCreate` requiere tipo MIME permitido
- `AccountingEntryCreate` requiere ≥2 líneas con `sum(debit) == sum(credit)`
- `SignRequestCreate` requiere ≥1 firmante
- `SalesOrderCreate` e `InvoiceCreate` requieren ≥1 ítem

## Errores comunes

| HTTP | Situación |
|---|---|
| 400 | Pago supera total de factura / partida doble no cuadra |
| 403 | Intento de modificar recurso de otra sede |
| 404 | Recurso no encontrado |
| 409 | Acción inválida para el estado actual |
| 422 | Validación fallida / factura electrónica no configurada |
