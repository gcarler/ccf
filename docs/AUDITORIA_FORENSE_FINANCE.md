# Auditoría Forense — Módulo Finance

**Fecha original:** 2026-07-18
**Actualización:** 2026-07-25 — Post-correcciones Victory Confirmed

---

## Alcance auditado

- Routers: `backend/api/finance.py`, `backend/api/finance_suite.py`, `backend/api/donations.py`
- Modelos: `backend/models_finance_suite.py`
- Schemas: `backend/schemas/finance_suite.py`
- Frontend: `contabilidad/`, `facturacion/`, `gastos/`, `firma/`, `documentos/`
- Tests: `tests/test_finance_suite_api.py` (33 passed) · `tests/test_api_massive.py` (parcial)

---

## Auditoría 2026-07-25

### Hallazgos identificados y resueltos

| # | ID | Severidad | Hallazgo | Resolución |
|---|---|---|---|---|
| 1 | FIN-H01 | Alto | Gastos hardcodeados al 66% de ingresos en `/finance/summary` y `/finance/funds` | Reemplazado por query real a `ExpenseReport` (status=reimbursed, sede_id) |
| 2 | FIN-M14 | Medio | `country_code="CO"` hardcodeado en cálculo de impuesto en `create_invoice` | Lookup por `sede_id` con fallback a "CO" |
| 3 | FIN-IDOR | Grave | `PATCH /bank-accounts/{id}` sin verificar que la cuenta pertenece a la sede del usuario | Agregado check de `sede_id` → HTTP 403 en mismatch |
| 4 | — | Medio | Estado `"partial"` en Invoice asignado en código pero no documentado en el modelo | Agregado al comentario del campo `status` |
| 5 | — | Medio | `send-electronic` retornaba `501` sin mensaje útil; frontend mostraba error genérico | Cambiado a `422` con body estructurado; frontend muestra mensaje del servidor |
| 6 | FIN-H03 | Alto | `_generate_number` usaba `count(AccountingEntry.id)` para todos los tipos de documento | Mapeo prefix→modelo correcto: SO→SalesOrder, INV→Invoice, EXP→ExpenseReport |
| 7 | — | Medio | `POST /bank-transactions` no actualizaba `current_balance` de la cuenta | Agregado `with_for_update()` + actualización atómica de balance |
| 8 | — | Menor | `ChartOfAccount` sin `UniqueConstraint("sede_id", "code")` | Agregado `uq_chart_of_account_sede_code` |
| 9 | — | Menor | `documentos/page.tsx`: sin toasts en operaciones CRUD | Importado `toast` de sonner; todos los handlers tienen success/error |
| 10 | — | Menor | IP del firmante hardcodeada como `"127.0.0.1"` en frontend | Frontend: eliminado campo; Backend: captura `request.client.host` |
| 11 | — | Menor | `DocumentCreate.mime_type` sin validación | `@field_validator` con lista de tipos permitidos |

### Tests agregados

| Test | Qué verifica |
|---|---|
| `test_update_bank_account_cross_sede_forbidden` | IDOR: HTTP 403 al modificar cuenta de otra sede |
| `test_bank_transaction_updates_balance` | `current_balance` se incrementa/decrementa correctamente |

### Resultado

```
pytest tests/test_finance_suite_api.py tests/test_api_massive.py -v --tb=short
134 passed, 0 failures, 0 errors

Victory Auditor Gen 2 → VICTORY CONFIRMED ✅
```

---

## Auditoría inicial 2026-07-18

### Validaciones ejecutadas

| Validación | Resultado al 2026-07-18 | Estado actual |
|---|---|---|
| Multi-tenant (finance.py) | ⚠️ 0 referencias sede | ✅ Corregido |
| Multi-tenant (finance_suite.py) | ⚠️ 0 referencias sede | ✅ Corregido |
| Gastos calculados | ❌ Hardcodeado 66% | ✅ Corregido |
| IDOR bank accounts | ❌ Sin verificación sede | ✅ Corregido |
| Tests finance_suite | ❌ CERO tests | ✅ 33 tests |
| Artefactos documentales | ❌ 0/6 | ✅ 6/6 |

### Hallazgos originales (estado al 2026-07-18)

| ID | Severidad | Hallazgo |
|---|---|---|
| FIN-C1 | Crítico | 6/6 artefactos documentales faltantes |
| FIN-G1 | Grave | 0 referencias multi-tenant en endpoints financieros |
| FIN-M1 | Medio | 2 imports locales en finance.py |

Ver `PLAN_FINANCE_CALIDAD.md` para el listado completo de los 85 hallazgos originales.
