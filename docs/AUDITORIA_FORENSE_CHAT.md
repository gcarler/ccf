# Auditoría Forense — Módulo Chat

**Fecha:** 2026-07-18
**Objetivo:** evaluar completitud, consistencia y confiabilidad operativa del módulo de chat.

---

## Alcance auditado

- Router: `backend/api/chat.py`
- CRUD: `backend/crud/crm_/extended.py`
- Modelos: `backend/models_conversation.py`
- Schemas: `backend/schemas/chat.py`
- Frontend: `frontend/src/app/plataforma/inbox/`
- Tests: `tests/test_chat_api.py`, `tests/test_chat_sede_isolation.py`
- Docs: `docs/PLAN_CHAT_CALIDAD.md`

---

## Validaciones ejecutadas

| Validación | Resultado |
|---|---|
| Tests | `test_chat_api.py + test_chat_sede_isolation.py: 32 passed` |
| Multi-tenant (Axioma 3) | **5 referencias** a `get_user_sede_id` / `_scope_` |
| Sin legacy | **0 coincidencias** CCF-MBR o FK users.id |
| Imports locales | **0 imports locales** |

---

## Resultados por dimensión

### D1 — Artefactos documentales: 1/6

| Artefacto | Estado |
|---|---|
| `docs/ESTADO_CHAT.md` | ❌ |
| `docs/CHAT_API_CONTRACTS.md` | ❌ |
| `docs/CHAT_QA_CHECKLIST.md` | ❌ |
| `docs/CHAT_RBAC_MATRIX.md` | ❌ |
| `docs/PLAN_CHAT_CALIDAD.md` | ✅ |
| `scripts/test_chat_quality.py` | ❌ |

### D2-D4 — Axiomas arquitectónicos — ✅

| Verificación | Resultado |
|---|---|
| Kernel Personas (Axioma 1) | ✅ Conversaciones usan persona_id (UUID) |
| Multi-Tenant (Axioma 3) | ✅ 5 referencias a scope |
| Sin Legacy (Axioma 4) | ✅ Sin CCF-MBR, sin FK users.id |

### D5 — Cobertura de tests — ✅

| Métrica | Valor |
|---|---|
| Tests existentes | 32 (2 archivos) |
| Smoke script | ❌ No existe |
| Ejecución | 32 passed |

### D6-D7 — Calidad — ⚠️

| Verificación | Resultado |
|---|---|
| Páginas frontend existen | ✅ `inbox/` |
| Smoke script | ❌ |
| Calidad de código | ✅ Sin issues graves |

---

## Hallazgos

| ID | Severidad | Hallazgo |
|---|---|---|
| CHT-C1 | Crítico | 5 de 6 artefactos documentales faltan |
| CHT-G1 | Grave | Ausencia de smoke script canónico |
