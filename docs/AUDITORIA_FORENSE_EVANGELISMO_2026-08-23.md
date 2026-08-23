# Auditoría Forense — Módulo Evangelismo (Completitud y Consistencia)

**Fecha:** 2026-08-23
**Ejecutada desde:** worktree propio `/root/ccf-evangelism` (rama `feature/evangelism-20260823`, base `origin/main` @ `67c99d3f`)
**Objetivo:** evaluar completitud, consistencia y confiabilidad operativa del módulo de evangelismo en backend, frontend, permisos, tests y documentación.
**Regla de lectura:** este documento registra el estado verificado en este corte. Complementa `ESTADO_EVANGELISMO.md` (handover canónico) y actualiza/cierra hallazgos de las auditorías forenses `2026-07-17` y `2026-07-25`.

---

## Resumen Ejecutivo

| Métrica | Resultado |
|---|---|
| Smoke mínimo (4 suites canónicas) | ✅ **20 passed, 1 xpassed** (10s) |
| Regresiones críticas (habilitación + roles custom) | ✅ **32 passed, 1 xfailed** (33s) |
| Suite amplia (`test_evangelism_module_coverage.py`) | ✅ **225 passed** (165s) |
| **Suite completa de tests del módulo (67 archivos)** | ✅ **1086 passed, 0 failed** (2 xfailed, 1 xpassed) |
| Typecheck frontend completo (`npx tsc --noEmit`) | ✅ **0 errores** |
| Lint frontend del módulo (`eslint --max-warnings=0`) | ✅ **0 problemas** |
| `datetime.utcnow()` en el módulo | ✅ 0 (solo helper `_utcnow()` con `timezone.utc`) |
| `require_pastor_or_admin` en código del módulo | ✅ 0 (solo referencias históricas en docs) |

**Veredicto global: APROBADO.** Los 3 bugs críticos de soft-delete de la auditoría del 07-25 (F1-1, F1-2, F1-3) están corregidos en `backend/crud/evangelism.py` con filtros `deleted_at.is_(None)` verificados. La suite completa del módulo (67 archivos, 1086 tests) pasa **sin fallos**.

---

## Alcance auditado

- Router raíz: `backend/api/evangelism.py` (incl. scanner de personas)
- Submódulos: `evangelism_main/`, `evangelism_grupos/`, `evangelism_events/`, `evangelism_analytics.py`, `evangelism_rankings.py`, `evangelism_multiplication.py`, `evangelism_notifications.py`, `evangelism_reports.py`, `evangelism_shared.py`
- CRUD: `backend/crud/evangelism.py`
- Modelos: `backend/models_evangelism.py` · Schemas: `backend/schemas/evangelism.py`
- Permisos: `backend/core/permissions.py` (guards `require_evangelism_*`)
- Frontend: `frontend/src/app/plataforma/evangelism/**` + `frontend/src/components/evangelism/**`
- Tests: `tests/test_evangelism_*.py` (67 archivos) + `tests/test_calculo_sesiones.py`
- Documentación: `docs/ESTADO_EVANGELISMO.md`, `docs/EVANGELISMO_API_CONTRACTS.md`, `docs/EVANGELISMO_RBAC_MATRIX.md`, `docs/EVANGELISMO_QA_CHECKLIST.md`

---

## Validaciones ejecutadas

### 1. Smoke mínimo (script canónico)

```bash
cd /root/ccf-evangelism
/root/ccf/venv/bin/python scripts/test_evangelism_quality.py
```

- `1. Smoke mínimo Evangelismo` — **20 passed, 1 xpassed** (10.05s)
- `2. Regresiones críticas Evangelismo` — **32 passed, 1 xfailed** (32.90s)
- RESUMEN: 2 passed, 0 failed

### 1.2 Suite amplia backend

```bash
/root/ccf/venv/bin/python -m pytest -q -o addopts="" tests/test_evangelism_module_coverage.py
```

Resultado: **225 passed in 161.42s**.

### 1.3 Suite completa de tests del módulo (67 archivos)

Ejecutada en 4 chunks (cada uno ≤ 4:17):

| Chunk | Resultado |
|---|---|
| `test_evangelism_module_coverage.py` | 225 passed |
| 18 archivos (triple7, analytics ×8, checkin ×2, cms_workspace, comprehensive, concurrent, coverage+coverage_gaps, crm_bridge, calculo_sesiones) | 386 passed |
| 25 archivos (crud, cross-sede, events_shared, followup, funnel_scope, grupos_sesiones, habilitación, integration, low_coverage, main_scanner, main_utils, multiplication…) | 258 passed, 1 xfailed |
| 23 archivos (notifications ×3, rankings ×3, reports ×6, roles, scanner, sesiones_asistencias, shared ×4, supplemental, triple7, quality_script) | 217 passed, 1 xfailed, 1 xpassed |
| **TOTAL** | **1086 passed, 0 failed** (2 xfailed, 1 xpassed) |

> Nota: la corrida simple con todos los archivos juntos excede el timeout de la sesión (supera ~10 min); la suite completa es igualmente estable por chunks, sin fallos.

### 1.4 Typecheck y lint frontend

```bash
cd frontend && npx tsc --noEmit          # 0 errores (proyecto completo)
npx eslint 'src/app/plataforma/evangelism/**/*.{ts,tsx}' 'src/components/evangelism/**/*.{ts,tsx}' --max-warnings=0   # 0 problemas
```

---

## Estado de hallazgos previos

### Auditoría 2026-07-25 — cerrados

| ID | Hallazgo | Estado 2026-08-23 |
|---|---|---|
| F1-1 | `actualizar_participante` sin filtro `deleted_at` | ✅ **CORREGIDO** — `crud/evangelism.py` filtra `deleted_at.is_(None)` (línea ~522) |
| F1-2 | `submit_asistencia` upsert puede resucitar soft-deleted | ✅ **CORREGIDO** — upsert filtra `Asistencia.deleted_at.is_(None)` (línea ~621) |
| F1-3 | `remover_participante` sin filtro `deleted_at` | ✅ **CORREGIDO** — filtra `deleted_at.is_(None)` (línea ~561) |
| F2-1 | 4 endpoints con `get_current_user` (design) | ✅ **CORREGIDO** — `grupos_mine` → `require_evangelism_read`; event attendance → `require_evangelism_edit`; checkin/visitors → `require_evangelism_edit` |
| F2-2 | 6 endpoints de lectura con `require_evangelism_manage` | ✅ **CORREGIDO** — `GET roles`, `GET excuses`, `analytics/global`, `dashboard-stats`, `multiplication/check`, `multiplication/history` ahora `require_evangelism_read` |
| F3-1 | No existía `GrupoEvangelismoResponse` | ✅ **CORREGIDO** — schema existe en `schemas/evangelism.py:560`; `grupos` serializa con `_serialize_grupo` |
| F3-2 | No existía `RolPersonalizadoEstrategiaUpdate` | ✅ **CORREGIDO** — `PUT /strategies/{id}/roles/{role_id}` usa el schema |
| F4-1 | `test_evangelism_roles_coverage.py` whitellist 500 | ✅ **CORREGIDO** — asserts ahora `in (200, 201)` y `== 404` |
| F5-2 | QA checklist sin analytics/reports/notifications | ✅ **CORREGIDO** — checklist cubre analytics, reports y notificaciónes |
| F6-3 | `_generate_codigo` dead code | ✅ **ELIMINADO** — sin referencias |

### Auditoría 2026-07-17 — cerrados

| ID | Hallazgo | Estado 2026-08-23 |
|---|---|---|
| F1 | Frontend modela módulo con roles legacy (`isPastoralOrAdmin`) | ✅ **CORREGIDO** — `EvangelismShell` y `EvangelismClient` usan `hasModuleAccess('evangelism', 'read'/'manage')` |
| F2 | `GET /events/` con chequeo manual de rol dentro del handler | ✅ **CORREGIDO** — guard canónico `require_evangelism_read`; sin bifurcación manual por rol |
| F4 | Gate frontend profundo no confiable (Playwright EPERM) | ⚠️ **NO APLICA EN ESTA SESIÓN** — no se ejecutó Playwright (entorno de auditoría estable, ver Excepciones) |
| F5 | Cobertura RBAC no-admin baja | ✅ **MEJORADO** — `test_evangelism_module_coverage.py` incluye casos con `evangelism:read` grant (sede), `scanner/validate` cross-sede y `coordinador` negativo |
| F7 | Monolitos frontend (design debt) | ✅ **MEJORADO** — decomposición: `strategies/[id]` pasó de 2678 → **460 LOC** (+ hooks `useStrategyDetailPage.ts` 817); `events/page.tsx` 1722 → **263**; `groups/[id]` 1002 → **205** |

---

## Verificaciones estáticas del checklist CCF (§6)

| Chequeo | Resultado |
|---|---|
| `datetime.utcnow()` en backend del módulo | ✅ 0 (helper `_utcnow()` con `timezone` en `crud/evangelism.py` / `main_utils.py`) |
| `require_pastor_or_admin` en código del módulo | ✅ 0 (solo en docs de referencia) |
| Guards `require_evangelism_*` en routers | ✅ Taxonomía canónica, con bypass por rol `pastor`/`coordinador` |
| `get_user_sede_id`/`_scope_` refs en backend evangelism | ✅ 11 refs en archivos del módulo + helpers CRUD |
| `sede_id` en models (UGC) | ✅ en estrategia/grupo/sesion/asistencia/seguimiento |
| `extra="forbid"` en 21 schemas del módulo | ✅ |
| `DateTime(timezone=True)` | ✅ 32 columnas en `models_evangelism.py` |
| UUID PKs | ✅ 13 modelos con `UUID(as_uuid=True), primary_key=True` |
| `db.delete(` hard en módulo | ✅ 0 (soft deletes via `deleted_at`/`activo`) |
| `JSON` vs `JSONB` | ✅ `JSON` (detalles_cambio, phases, etc.) |
| `_utcnow` en `events_registrations.py` | ✅ helper con `timezone` |
| `legacy` substring en módulo | ✅ 0 |
| `fetch(` crudo en frontend | ✅ 0 |
| `any` explícito en frontend | ✅ 0 |
| `<Modal>`/`<Dialog>`/`AlertDialog` en frontend | ✅ 0 (26 archivos usan `Drawer`) |
| tokens semánticos vs colores planos | ✅ solo 2 usos residuales de `bg-red-50`/`hover:bg-red-500/10` (severidad Baja, ver Hallazgos) |

---

## Hallazgos abiertos

| ID | Severidad | Hallazgo | Evidencia | Recomendación |
|---|---|---|---|---|
| G-01 | **Media** | `docs/EVANGELISMO_API_CONTRACTS.md` desactualizado | la línea 107 dice `GET /grupos/mine → get_current_user` pero el código real usa `require_evangelism_read` (línea 180, `grupos_main.py`); la línea 114 documenta `POST /grupos/visitors → require_evangelism_manage` y el código real usa `require_evangelism_edit`; `GET /strategies/{id}/roles` también aparece como `manage` cuando hoy es `read`. Rutas `assignment-summary` y `macro-despliegue` (existentes) no figuran en el doc. | Actualizar contratos al estado real del código |
| G-02 | **Media** | `docs/ESTADO_EVANGELISMO.md` LOC counts desactualizados (doc dice ~11 300 backend y 4 215 frontend; real backend directo incl. models/crud/schemas ≈ 13 000, frontend con repetidos dir ≈ 16 690). | `wc -l` 2026-08-23 | Actualizar sección 3 con conteo actual |
| G-03 | **Baja** | 2 usos de colores planos `bg-red-50`/`hover:bg-red-500/10` (p. ej. `StrategyHeader.tsx:43`, `groups/page.tsx:366`) | tokens semánticos accesibles (`--destructive`) para el fondo también | Migrar a `bg-[hsl(var(--destructive)/10%)]` o similar |
| G-04 | **Baja** | `test_evangelism_roles_coverage.py::test_delete_role` marcado `xfail(strict=False)` por issue de CRUD en test DB — no es fallo, pero el xfail no estricto puede enmascarar una regresión futura | pytest.mark.xfail(strict=False) | Convertir a test real una vez resuelto el path CRUD en fixtures o usar `strict=True` |
| G-05 | Baja | `evangelism_events/events_checkin.py` y analytics usan distintos helpers `_utcnow()` (duplicado menor) | 1 helper por archivo evento en vez de uno canónico | Unificar en `evangelism_shared.py` |

**No se detectaron:** endpoints sin handler, schemas faltantes en grupos, dead code relevante, endpoints con única-semántica-huérfana, drift de tipos frontend↔backend (0 errores TS), `extra="forbid"` inconsistente.

---

## Tabla consolidada de resultados (checks)

| # | Check | Comando | Resultado |
|---|---|---|---|
| 1 | smoke mínimo | `scripts/test_evangelism_quality.py` | ✅ 20 passed |
| 2 | regresiones críticas | idem | ✅ 32 passed |
| 3 | suite amplia | `pytest test_evangelism_module_coverage.py` | ✅ 225 passed |
| 4 | suite completa (67 archivos) | `pytest tests/test_evangelism_*.py + calculo_sesiones` | ✅ 1086 passed |
| 5 | typecheck | `npx tsc --noEmit` | ✅ 0 errores |
| 6 | lint módulo | `eslint --max-warnings=0` | ✅ 0 |
| 7 | RBAC matriz | grep `GESTOR/EDITOR/LECTOR` en docs | ✅ nota aclaratoria presente en matriz |

---

## Conclusión y recomendaciones

**Veredicto: APROBADO.** El módulo de evangelismo vuelve a estar en verde en su suite completa (1086 tests+ lint+ typecheck), se cerraron los bugs críticos de soft-delete detectados en 07-25 y la descomposición del frontend redujo los monolitos a rangos sanos. No hay bloqueantes de merge.

**Recomendaciones de orden para la página siguiente:**
1. Actualizar `docs/EVANGELISMO_API_CONTRACTS.md` (G-01) y conteos LOC del ESTADO (G-02) — edición documental.
2. Migrar los 2 tonos planos rojos a tokens semánticos (G-03).
3. Unificar helper de tiempo `_utcnow()` en `evangelism_shared.py` (G-05).
4. Revisar `xfail(strict=False)` del test de delete_role (G-04).

**Excepciones de la sesión:** no se ejecutó Playwright E2E (entorno de auditoría estable; el gate E2E oficial del módulo debe correrse en el pipeline con `E2E_*` configurados).