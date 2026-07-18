# Auditoría Forense — Módulo Administración

**Fecha:** 2026-07-18
**Objetivo:** evaluar completitud, consistencia y confiabilidad operativa del módulo de administración.

---

## Alcance auditado

- Router: `backend/api/admin.py` (40 endpoints)
- Modelos: `backend/models.py`, `backend/models_auth.py`, `backend/models_crm.py`, `backend/models_governance.py`
- Schemas: `backend/schemas/governance.py`
- Frontend: `frontend/src/app/plataforma/admin/**` (~30 páginas)
- Tests: `tests/test_admin_coverage.py` (53 tests)
- Docs: `docs/MODULO_ADMIN.md`, `docs/PLAN_ADMIN_CALIDAD.md`

---

## Validaciones ejecutadas

| Validación | Comando | Resultado |
|---|---|---|
| Tests | `pytest tests/test_admin_coverage.py -q --tb=short --no-cov` | **53 passed** |
| Multi-tenant (Axioma 3) | `rg -c 'get_user_sede_id|_scope_|_get_scoped_' admin.py` | **2 referencias** |
| Sin legacy | `rg -n "CCF-MBR|ForeignKey.*users\.id" admin.py` | **0 coincidencias** |
| Imports locales | `rg -n "^\s+import |^\s+from .* import " admin.py \| grep -v "^1:"` | **0 imports locales** |

---

## Resultados por dimensión

### D1 — Artefactos documentales: 2/6

| Artefacto | Estado |
|---|---|
| `docs/ESTADO_ADMIN.md` | ❌ |
| `docs/ADMIN_API_CONTRACTS.md` | ❌ |
| `docs/ADMIN_QA_CHECKLIST.md` | ❌ |
| `docs/ADMIN_RBAC_MATRIX.md` | ❌ |
| `docs/PLAN_ADMIN_CALIDAD.md` | ✅ |
| `scripts/test_admin_quality.py` | ❌ |

### D2 — Kernel Personas (Axioma 1) — ✅

| Verificación | Resultado |
|---|---|
| FK a personas usan `personas.id` (UUID) | ✅ |
| Sin tablas paralelas para personas | ✅ |
| `auth_users.id == personas.id` | ✅ |

### D3 — Multi-Tenant (Axioma 3) — ⚠️

| Verificación | Resultado |
|---|---|
| `list_admin_personas` filtra por `sede_id` | ✅ |
| `admin_stats` scope por sede | ✅ |
| CRUD defense-in-depth | ⚠️ Consultas directas, no vía CRUD layer |
| Cross-sede retorna 404 | ✅ |

### D4 — Auth v3 / Sin Legacy — ✅

| Verificación | Resultado |
|---|---|
| Sin rutas `/api/v2/` | ✅ |
| Sin `CCF-MBR` tokens | ✅ |
| Sin `ForeignKey("users.id")` | ✅ |
| Permisos via `MODULE_PERMISSION_MAP` | ✅ |

### D5 — Cobertura de tests — ✅

| Métrica | Valor |
|---|---|
| Tests existentes | 53 |
| Endpoints cubiertos | 40/40 (100%) |
| Smoke script | ❌ No existe |
| Ejecución | 53 passed |

### D6 — Consistencia frontend-backend — ⚠️

| Verificación | Resultado |
|---|---|
| Páginas existen para endpoints | ✅ ~30 páginas |
| Datos mock reemplazados | ✅ Dashboard usa `/admin/stats` |
| Contratos coinciden | ⚠️ Uso de `any` types sin alineación con schemas |

### D7 — Calidad de código — ⚠️

| Verificación | Resultado |
|---|---|
| Sin `any` en frontend | ⚠️ 12+ usos de `any` |
| Sin imports locales en backend | ✅ |
| Sin `console.error` sin feedback | ✅ Corregido |
| Sin colores hardcodeados | ⚠️ 33 archivos con colores hardcodeados |

---

## Hallazgos

| ID | Severidad | Hallazgo | Recomendación |
|---|---|---|---|
| ADM-C1 | Crítico | 5 de 6 artefactos documentales faltan | Crear `ESTADO_ADMIN.md`, `ADMIN_API_CONTRACTS.md`, `ADMIN_QA_CHECKLIST.md`, `ADMIN_RBAC_MATRIX.md`, `scripts/test_admin_quality.py` |
| ADM-G1 | Grave | Colores hardcodeados en 33 archivos frontend | Migrar a variables CSS del design system |
| ADM-G2 | Grave | Ausencia de smoke script canónico | Crear `scripts/test_admin_quality.py` |
| ADM-M1 | Medio | 12+ tipos `any` en frontend | Tipar con interfaces dedicadas |
| ADM-M2 | Medio | Consultas directas sin CRUD layer | Migrar a patrón CRUD para defense-in-depth |
| ADM-L1 | Leve | Schemas duplicados para roles | Unificar `/roles` y `/auth-role-definitions` |

---

## Plan de acción

| Prioridad | Tarea | Asociado |
|---|---|---|
| P1 | Crear `docs/ESTADO_ADMIN.md` | ADM-C1 |
| P2 | Crear `docs/ADMIN_API_CONTRACTS.md` | ADM-C1 |
| P3 | Crear `docs/ADMIN_QA_CHECKLIST.md` | ADM-C1 |
| P4 | Crear `docs/ADMIN_RBAC_MATRIX.md` | ADM-C1 |
| P5 | Crear `scripts/test_admin_quality.py` | ADM-C1, ADM-G2 |
| P6 | Migrar colores hardcodeados a CSS variables en frontend admin | ADM-G1 |
| P7 | Tipar componentes frontend con interfaces | ADM-M1 |
