# Estado del Módulo Support

**Actualizado:** 2026-07-18

---

## Resumen

Módulo de soporte y tickets de ayuda. Gestiona solicitudes de soporte, base de conocimiento y tutoriales.

| Métrica | Valor |
|---|---|
| Routers | `backend/api/support.py`, `backend/api/support_kb.py` |
| CRUD | `backend/crud/crm_/support.py` |
| Frontend | `frontend/src/app/plataforma/support/` (kb, history, contact, tickets, tutorials) |
| Tests | `tests/test_support_tables_api.py` (7 passed) |
| Docs | `docs/AUDITORIA_FORENSE_SUPPORT.md` |

---

## Backend

| Endpoint | Propósito |
|---|---|
| `GET/POST /api/support/tickets` | CRUD de tickets |
| `GET/POST /api/support/kb` | Base de conocimiento |
| `POST /api/support/contact` | Formulario de contacto |

---

## Tests

| Métrica | Valor |
|---|---|
| Tests | 7/7 passed |
| Smoke | `scripts/test_fase3_quality.py` |

## Hallazgos abiertos

| ID | Severidad | Hallazgo |
|---|---|---|
| SUP-M1 | Medio | 0 referencias multi-tenant en support.py |
