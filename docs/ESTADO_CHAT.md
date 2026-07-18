# Estado del Módulo Chat

**Actualizado:** 2026-07-18

---

## Resumen

Módulo de mensajería interna de la plataforma. Permite conversaciones entre usuarios con aislamiento multi-tenant.

| Métrica | Valor |
|---|---|
| Router | `backend/api/chat.py` |
| CRUD | `backend/crud/crm_/extended.py` |
| Modelos | `backend/models_conversation.py` |
| Schemas | `backend/schemas/chat.py` |
| Frontend | `frontend/src/app/plataforma/inbox/` |
| Tests | 32 (2 archivos) |
| Smoke script | `scripts/test_chat_quality.py` |

---

## Contrato canónico

- Conversaciones identificadas por UUID
- Participantes referencian `personas.id`
- Aislamiento multi-tenant via `get_user_sede_id()`
- Soft delete en mensajes

---

## Backend

| Aspecto | Detalle |
|---|---|
| Router | `backend/api/chat.py` |
| Schemas | `backend/schemas/chat.py` |
| Modelos | `backend/models_conversation.py` |
| CRUD | `backend/crud/crm_/extended.py` |

### Endpoints principales

- Envío de mensajes
- Listado de conversaciones
- Historial de mensajes
- Marcado de lectura

---

## Tests

| Métrica | Valor |
|---|---|
| Archivos | `tests/test_chat_api.py`, `tests/test_chat_sede_isolation.py` |
| Tests | 32 |
| Última ejecución | 32 passed |

---

## Documentación relacionada

- `docs/PLAN_CHAT_CALIDAD.md`
- `docs/AUDITORIA_FORENSE_CHAT.md`
- `docs/CHAT_API_CONTRACTS.md`
- `docs/CHAT_QA_CHECKLIST.md`
- `docs/CHAT_RBAC_MATRIX.md`
- `scripts/test_chat_quality.py`
