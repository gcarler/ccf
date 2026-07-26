# Matriz RBAC — Módulo Finance

**Actualizado:** 2026-07-25

---

## Permisos

| Acción | Permiso requerido | Roles típicos |
|---|---|---|
| Ver resumen financiero | `finance:read` | MIEMBRO, EDITOR, GESTOR, ADMIN |
| Ver transacciones | `finance:read` | MIEMBRO, EDITOR, GESTOR, ADMIN |
| Ver cuentas bancarias | `finance:read` | EDITOR, GESTOR, ADMIN |
| Ver facturas / órdenes | `finance:read` | EDITOR, GESTOR, ADMIN |
| Ver reportes de gastos | `finance:read` | EDITOR, GESTOR, ADMIN |
| Ver documentos | `finance:read` | EDITOR, GESTOR, ADMIN |
| Registrar donaciones | `finance:edit` | EDITOR, GESTOR, ADMIN |
| Crear factura / orden de venta | `finance:edit` | EDITOR, GESTOR, ADMIN |
| Crear reporte de gastos | `finance:edit` | EDITOR, GESTOR, ADMIN |
| Enviar / aprobar gastos | `finance:edit` | GESTOR, ADMIN |
| Crear / modificar cuentas bancarias | `finance:edit` | GESTOR, ADMIN |
| Administrar fondos | `finance:edit` | GESTOR, ADMIN |
| Aprobar / rechazar gastos | `finance:edit` | GESTOR, ADMIN |
| Ver reportes administrativos | `finance:edit` | GESTOR, ADMIN |
| Crear solicitudes de firma | `finance:edit` | EDITOR, GESTOR, ADMIN |

---

## Endpoints `/finance` (Legacy)

| Endpoint | Permiso | Multi-tenant |
|---|---|---|
| `GET /finance/summary` | `finance:read` | ✅ sede_id |
| `GET /finance/funds` | `finance:read` | ✅ sede_id |
| `GET /finance/transactions` | `finance:read` | ✅ sede_id |
| `POST /finance/register-donation` | `finance:edit` | ✅ sede_id |
| `GET /finance/admin/funds` | `finance:edit` | ✅ sede_id |
| `POST /finance/admin/funds` | `finance:edit` | ✅ sede_id |
| `PATCH /finance/admin/funds/{id}` | `finance:edit` | ✅ sede_id |
| `GET /finance/impact` | Público | — |

---

## Endpoints `/finance-suite` (Suite Completa)

| Endpoint | Permiso | Multi-tenant |
|---|---|---|
| `GET /finance-suite/bank-accounts` | `finance:read` | ✅ sede_id |
| `POST /finance-suite/bank-accounts` | `finance:edit` | ✅ sede_id |
| `PATCH /finance-suite/bank-accounts/{id}` | `finance:edit` | ✅ verifica sede → 403 |
| `POST /finance-suite/bank-transactions` | `finance:edit` | ✅ sede_id + actualiza balance |
| `GET /finance-suite/chart-of-accounts` | `finance:read` | ✅ sede_id |
| `POST /finance-suite/chart-of-accounts` | `finance:edit` | ✅ sede_id, unique(sede, code) |
| `GET /finance-suite/accounting-entries` | `finance:read` | ✅ sede_id |
| `POST /finance-suite/accounting-entries` | `finance:edit` | ✅ valida partida doble |
| `PATCH /finance-suite/accounting-entries/{id}/post` | `finance:edit` | ✅ solo draft |
| `GET /finance-suite/sales-orders` | `finance:read` | ✅ sede_id |
| `POST /finance-suite/sales-orders` | `finance:edit` | ✅ sede_id |
| `GET /finance-suite/invoices` | `finance:read` | ✅ sede_id |
| `POST /finance-suite/invoices` | `finance:edit` | ✅ impuesto por sede |
| `POST /finance-suite/invoices/{id}/payments` | `finance:edit` | ✅ valida sobrepago |
| `POST /finance-suite/invoices/{id}/send-electronic` | `finance:edit` | ✅ error 422 amigable |
| `GET /finance-suite/expense-reports` | `finance:read` | ✅ sede_id |
| `POST /finance-suite/expense-reports` | `finance:edit` | ✅ sede_id |
| `POST /finance-suite/expense-reports/{id}/submit` | `finance:edit` | ✅ owner check |
| `POST /finance-suite/expense-reports/{id}/approve` | `finance:edit` | ✅ aprobador ≠ empleado |
| `POST /finance-suite/expense-reports/{id}/reimburse` | `finance:edit` | ✅ |
| `GET /finance-suite/documents` | `finance:read` | ✅ sede_id |
| `POST /finance-suite/documents` | `finance:edit` | ✅ mime_type validado |
| `DELETE /finance-suite/documents/{id}` | `finance:edit` | ✅ soft-delete |
| `POST /finance-suite/document-tags` | `finance:edit` | ✅ |
| `GET /finance-suite/sign-requests` | `finance:read` | ✅ sede_id |
| `POST /finance-suite/sign-requests` | `finance:edit` | ✅ sede_id |
| `POST /finance-suite/sign-requests/{id}/send` | `finance:edit` | ✅ |
| `POST /finance-suite/sign-requests/{id}/signers/{sid}/sign` | `finance:edit` | ✅ IP real |

---

## Aislamiento multi-tenant

- Todas las consultas filtran por `sede_id` del usuario autenticado (vía `get_user_sede_id()`)
- `PATCH /bank-accounts/{id}` verifica que `account.sede_id == user.sede_id` → HTTP 403 si no coincide
- Segregación de deberes en gastos: el aprobador no puede ser el mismo usuario que creó el reporte
- Schemas con `extra='forbid'` en todos los endpoints de escritura (previene mass-assignment)
