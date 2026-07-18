# Auditoría Forense — Módulo Wiki

**Fecha:** 2026-07-18

---

## Alcance auditado

- Router: `backend/api/wiki.py`
- CRUD: `backend/crud/wiki.py`
- Modelos: `backend/models_wiki.py`
- Schemas: `backend/schemas/wiki.py`
- Frontend: `frontend/src/app/plataforma/wiki/`
- Tests: `tests/test_wiki.py` (28 passed, 2 failed)
- Docs: `docs/wiki/MODULO_WIKI.md`, `docs/wiki/PLAN_DE_TRABAJO_WIKI.md`

---

## Validaciones ejecutadas

| Validación | Resultado |
|---|---|
| Tests | **28 passed, 2 failed** |
| Multi-tenant | **2 referencias** a scope |
| Sin legacy | **0 coincidencias** |
| Imports locales | **1 import local** (`resolve_persona_id_for_user`) |

---

## Resultados

### D1 — Artefactos documentales: 2/6

| Artefacto | Estado |
|---|---|
| `docs/ESTADO_WIKI.md` | ❌ (tiene `MODULO_WIKI.md` pero no `ESTADO_WIKI.md`) |
| `docs/WIKI_API_CONTRACTS.md` | ❌ |
| `docs/WIKI_QA_CHECKLIST.md` | ❌ |
| `docs/WIKI_RBAC_MATRIX.md` | ❌ |
| `docs/PLAN_WIKI_CALIDAD.md` | ❌ (tiene `PLAN_DE_TRABAJO_WIKI.md` pero no `PLAN_WIKI_CALIDAD.md`) |
| `scripts/test_wiki_quality.py` | ❌ |

### D2-D4 — Axiomas — ✅

| Verificación | Resultado |
|---|---|
| Kernel Personas | ✅ `WikiPage.author_id` usa `personas.id` |
| Multi-Tenant | ✅ `sede_id` presente con scope |
| Sin Legacy | ✅ |

### D5 — Tests — ⚠️

| Métrica | Valor |
|---|---|
| Tests | 30 (28 passed, 2 failed) |
| Smoke script | ❌ No existe |

### D6-D7 — Calidad — ✅

| Verificación | Resultado |
|---|---|
| Imports locales | 1 (aceptable) |
| Frontend | ✅ `wiki/` con páginas funcionales |

---

## Hallazgos

| ID | Severidad | Hallazgo |
|---|---|---|
| WIK-C1 | Crítico | 6/6 artefactos documentales estándar faltan |
| WIK-C2 | Crítico | 2 tests fallando en `test_wiki.py` |
