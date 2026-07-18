# Estado del Módulo Donations

**Actualizado:** 2026-07-18

---

## Resumen

Módulo de donaciones. Gestiona el registro de donaciones, categorías y reportes asociados.

| Métrica | Valor |
|---|---|
| Router | `backend/api/donations.py` |
| CRUD | `backend/crud/crm_/donations.py` |
| Frontend | Comparte con Finance (`frontend/src/app/plataforma/finances/`) |
| Tests | `tests/test_donations_api.py` (4 passed, 1 xfailed, 2 xpassed) |
| Docs | `docs/AUDITORIA_FORENSE_DONATIONS.md` |

---

## Backend

| Endpoint | Propósito |
|---|---|
| `GET /api/donations` | Listar donaciones |
| `POST /api/donations` | Registrar donación |
| `GET /api/donation-categories` | Categorías de donación |

---

## Tests

| Métrica | Valor |
|---|---|
| Tests | 4 passed, 1 xfailed, 2 xpassed |
| Smoke | `scripts/test_fase3_quality.py` |

## Hallazgos

| ID | Severidad | Hallazgo |
|---|---|---|
| DON-M1 | Medio | 5 imports locales en donations.py |
