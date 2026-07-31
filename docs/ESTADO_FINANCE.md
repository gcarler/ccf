# Estado del Módulo Finance

**Actualizado:** 2026-07-25

---

## Resumen

Módulo financiero de la plataforma CCF. Gestiona contabilidad, facturación, gastos, documentos, firma digital, donaciones y reportes de tesorería. Compuesto por dos routers: `finance` (v1, dashboard/donaciones/fondos) y `finance-suite` (suite completa avanzada).

| Métrica | Valor |
|---|---|
| Routers | `backend/api/finance.py`, `backend/api/finance_suite.py`, `backend/api/donations.py` |
| Modelos | `backend/models_finance_suite.py` (16 modelos SQLAlchemy) |
| Schemas | `backend/schemas/finance_suite.py` (30+ schemas Pydantic v2, todos con `extra='forbid'`) |
| Frontend | `contabilidad/`, `facturacion/`, `gastos/`, `firma/`, `documentos/`, `admin/finance/treasury/` |
| Tests | `tests/test_finance_suite_api.py` (33 casos) · suite completa: 134 passed, 0 failures |
| Última auditoría | **2026-07-25** — 10 bugs corregidos, Victory Confirmed ✅ |

---

## Backend

| Router | Prefijo | Propósito |
|---|---|---|
| `backend/api/finance.py` | `/finance` | Dashboard, donaciones, fondos (v1) |
| `backend/api/finance_suite.py` | `/finance-suite` | Contabilidad, facturación, gastos, documentos, firma |
| `backend/api/donations.py` | `/donations` | Donaciones, categorías, MercadoPago |

### Submódulos de finance-suite

| Área | Recursos |
|---|---|
| Contabilidad | Bank accounts, transactions, reconciliaciones, chart of accounts, accounting entries, estados financieros, tax config |
| Facturación | Sales orders, invoices, pagos de facturas, factura electrónica |
| Gastos | Expense reports, items, recibos (con OCR/IA), flujo draft→submitted→approved→reimbursed |
| Documentos | Documents, tags (con IA summary), archivo centralizado |
| Firma Digital | Sign requests, signers, flujo draft→sent→completed, multi-país (CO, MX, US, CL, PE) |

---

## Seguridad

| Control | Estado |
|---|---|
| Multi-tenancy (`sede_id`) | ✅ Implementado en todos los endpoints de finance-suite |
| Segregación de deberes (gastos) | ✅ Aprobador ≠ empleado |
| IDOR en bank accounts | ✅ Corregido 2026-07-25 — PATCH verifica sede |
| Schemas con `extra='forbid'` | ✅ Todos los schemas de entrada previenen mass-assignment |
| Rate limiting | ✅ En `/invoices/{id}/send-electronic` y `/donations` |
| Validación de mime_type en documentos | ✅ Corregido 2026-07-25 |
| IP de firmante | ✅ Corregido 2026-07-25 — capturada del request real |

---

## Hallazgos corregidos — 2026-07-25

| ID | Severidad | Descripción | Archivo |
|---|---|---|---|
| FIN-H01 | Alto | Gastos hardcodeados al 66% de ingresos en dashboard | `finance.py` |
| FIN-M14 | Medio | País hardcodeado `"CO"` en cálculo de impuesto | `finance_suite.py` |
| FIN-IDOR | Grave | IDOR en `update_bank_account` sin verificación de sede | `finance_suite.py` |
| — | Medio | Estado `partial` no documentado en modelo Invoice | `models_finance_suite.py` |
| — | Medio | Endpoint factura electrónica retornaba 501 genérico | `finance_suite.py` |
| FIN-H03 | Alto | Numeración de documentos usaba contador cruzado entre tipos | `finance_suite.py` |
| — | Medio | `current_balance` no se actualizaba al crear BankTransaction | `finance_suite.py` |
| — | Menor | `ChartOfAccount` sin UniqueConstraint `(sede_id, code)` | `models_finance_suite.py` |
| — | Menor | Sin toasts de feedback en módulo Documentos (frontend) | `documentos/page.tsx` |
| — | Menor | IP hardcodeada `127.0.0.1` en firma digital | `firma/page.tsx` + `finance_suite.py` |
| — | Menor | Sin validación de `mime_type` en `DocumentCreate` schema | `schemas/finance_suite.py` |

---

## Hallazgos abiertos

Ninguno de los identificados en la auditoría de 2026-07-25. Para el backlog histórico de hallazgos de la auditoría 2026-07-18 (principalmente mejoras de type-safety frontend y código antiguo), ver `PLAN_FINANCE_CALIDAD.md`.

---

## Documentación relacionada

- [`docs/FINANCE_QA_CHECKLIST.md`](FINANCE_QA_CHECKLIST.md)
- [`docs/FINANCE_RBAC_MATRIX.md`](FINANCE_RBAC_MATRIX.md)
- [`docs/PLAN_FINANCE_CALIDAD.md`](PLAN_FINANCE_CALIDAD.md)
- [`docs/AUDITORIA_FORENSE_FINANCE.md`](AUDITORIA_FORENSE_FINANCE.md)
