# Estado del Módulo Finance

**Actualizado:** 2026-07-18

---

## Resumen

Módulo financiero de la plataforma. Gestiona transacciones, donaciones, categorías, tesorería, fondos y reportes financieros.

| Métrica | Valor |
|---|---|
| Routers | `backend/api/finance.py`, `backend/api/finance_suite.py`, `backend/api/donations.py` |
| Modelos | `backend/models_finance_suite.py` |
| Schemas | `backend/schemas/finance_suite.py` |
| Frontend | `frontend/src/app/plataforma/finances/`, `contabilidad/`, `facturacion/`, `gastos/`, `firma/`, `documentos/` |
| Tests | `tests/test_finance_api.py` (5 passed, 1 xpassed) |
| Docs | Sin documentación dedicada |

---

## Backend

| Router | Propósito |
|---|---|
| `backend/api/finance.py` | Transacciones, resúmenes, reportes |
| `backend/api/finance_suite.py` | Suite financiera avanzada |
| `backend/api/donations.py` | Donaciones y categorías |

---

## Hallazgos abiertos

| ID | Severidad | Hallazgo |
|---|---|---|
| FIN-G1 | Grave | 0 referencias multi-tenant en endpoints financieros |

---

## Documentación relacionada

- `docs/FINANCE_API_CONTRACTS.md`
- `docs/FINANCE_QA_CHECKLIST.md`
- `docs/FINANCE_RBAC_MATRIX.md`
- `scripts/test_finance_quality.py`
