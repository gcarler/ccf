# Cierre Fase 1 RBAC — Evangelismo CCF

> **Fecha:** 2026-07-21
> **Sesión:** `ses_07920d108ffetL0k7sDn4nqLzo`
> **Commit:** `339539e9` (`refactor(evangelism): cierra Fase 1 RBAC — elimina paquete _evangelism_helpers y arregla fields obsoletos en tests`)
> **Estado:** ✅ Cerrada y validada

---

## 1. Contexto de retoma

El usuario pidió continuar con la calidad de la plataforma CCF. Tras recall de memoria (`ses_091db8811ffeMefcUERobaBSuT`, 2026-07-17) se identificó que el módulo de Evangelism tenía su **Fase 1 RBAC** en progreso:

- **Fase 0 (Diagnóstico)** ✅ completa
- **Fase 1 (Homogeneizar RBAC a `evangelism:*`)** 🔄 en progreso, diagnosis hecha, código sin editar
- **Fases 2–5** ⏳ pendientes (enum canónico de asistencia, descomponer strategies monolito, búsqueda remota personas, QA final + docs)

Al inspeccionar el árbol actual se descubrió que la infraestructura de la Fase 1 ya estaba hecha por sesiones intermedias. El último eslabón pendiente era un paquete **muerto** (`backend/api/_evangelism_helpers/`) que aún referenciaba el guard legacy vía el wrapper `require_pastor_or_admin_with_sede`.

## 2. Hallazgos operacionales al retomar

### 2.1 Cambios pendientes sin commit (42 archivos)

Al iniciar, el working tree de `/root/ccf` tenía **42 archivos frontend modificados sin commit**, todos bajo `frontend/src/app/plataforma/`. Inspección (`git diff` representativo por archivo):

- Patrón dominante (37 archivos): `AbortController`/`signal` en `apiFetch` para cancelar al desmontar (memory leak + race condition fix), `catch (err: any)` → `catch (err: unknown)` (strictness TS).
- Tipado de interfaces inline en `apiFetch<...>` (eliminar `any`).
- `cache: 'no-store'` en datos sensibles a refresh.
- 5 archivos restantes: subsets del mismo patrón (interfaces nuevas `SystemConfig`/`AuditEvent`, solo types `unknown`).

**Acción**: commit separado `chore(frontend): AbortController + tipos estrictos en 42 admin pages` (commit `682a529d`, +616 / −220) para limpiar el árbol antes de la Fase 1 RBAC.

### 2.2 Estado de la migración RBAC al retomar

Inspección de `backend/core/permissions.py`:

- ✅ **L641-644**: bypass `evangelism:*` para `pastor` (total) y `coordinador` (read+edit) ya añadido a `require_permission`
- ✅ **L690-715**: `require_pastor_or_admin` ya tiene docstring explicando que es un guard histórico **CRM**, no debe usarse en otros módulos
- ✅ **L735-737**: ya existen los guards canónicos `require_evangelism_read/edit/manage`

Inspección de callers de `require_pastor_or_admin` en módulo evangelism:

- Los routers principales (`main_estrategias.py`, `main_roles.py`, `grupos_*`, `events_*`, `multiplication`, `notifications`, etc.) **ya migrados** a `require_evangelism_*`.
- Quedaba SOLO `backend/api/_evangelism_helpers/_shared.py` (8 hits) + `__init__.py` (2 hits).

### 2.3 Verificación de que el paquete `_evangelism_helpers` era código muerto

```
rg -n '_evangelism_helpers' backend/ tests/ scripts/ 2>/dev/null
→ no retorna importadores externos
```

- Cero imports externos al paquete (ningún router, ningún test, ningún script).
- Los símbolos que exporta (`_get_scoped_strategy`, `_get_scoped_grupo`, `_get_scoped_sesion`, `_get_scoped_participante`, `_get_scoped_seguimiento`, `_actor_sede_or_none_evangelismo`) tienen **definiciones locales equivalentes** en `backend/crud/evangelism.py` (que es el canon CRUD defense-in-depth) y `backend/api/crm/_shared.py`.
- El comentario referenciante en `backend/crud/evangelism.py:43-45` ("cuando exista el paquete backend/api/_evangelism_helpers/_shared.py") era un marcador de una refactorización prevista que nunca se llevó a cabo — el paquete se creó vacío o cuasi-vacío y la lógica terminó en el CRUD directamente.

## 3. Acciones tomadas (Fase 1 cierre)

### 3.1 Baseline verde pre-cambios

Hallazgo crítico al correr la baseline: **smoke canónico fallaba** en `test_put_rename_grupo_sin_participantes` (1 fallo), y **suite amplia fallaba** en 4 tests del conjunto `TestGruposEndpoints`:

- Causa raíz: los tests mandaban `{"nombre": "..."}` al PUT/POST `/api/evangelism/grupos/{id}` pero el schema `GrupoEvangelismoCreate/Update` (con `ConfigDict(extra="forbid")`) exige campo `name` (no `nombre`).
- Tests afectados:
  - `tests/test_evangelism_custom_role_regression.py::TestHappyPathSigueFuncionando::test_put_rename_grupo_sin_participantes`
  - `tests/test_evangelism_module_coverage.py::TestGruposEndpoints::test_create_grupo_minimo` (también `lugar` → `zone`)
  - `tests/test_evangelism_module_coverage.py::TestGruposEndpoints::test_update_grupo_basico`
  - `tests/test_evangelism_module_coverage.py::TestGruposEndpoints::test_update_grupo_404`
  - `tests/test_evangelism_module_coverage.py::TestGruposEndpoints::test_update_grupo_soft_deleted_404`

**Fix**: cambio `nombre` → `name` en los 5 tests, y `lugar` → `zone` en el test de create.

**Baseline verde confirmada**: smoke 2/2 suites (19 passed + 1 xfailed) y suite amplia 226/226 passed en 147s.

### 3.2 Eliminación radical del paquete muerto

Decisión del usuario vía `question` tool: "Confirmar eliminación (Recommended)".

Acciones:

- `rm -rf backend/api/_evangelism_helpers/` (elimina `__init__.py` 33 LOC + `_shared.py` 354 LOC = −387 líneas).
- Actualización del comentario referenciante en `backend/crud/evangelism.py:38-46` para reflejar que la lógica vive en el CRUD directamente (sin referencia al paquete inexistente).

### 3.3 Validación post-cierre

- Smoke canónico: `./venv/bin/python scripts/test_evangelism_quality.py` → 2/2 suites verdes (19 passed + 1 xfailed).
- Suite amplia: `./venv/bin/python -m pytest -q -o addopts='' tests/test_evangelism_module_coverage.py` → 226/226 passed en 155s.
- Verificación de imports Python: `python -c "import backend.api"` → exit 0 (nada roto).
- Grep final: `rg require_pastor_or_admin backend/api/evangelism* backend/api/evangelism_*/` → **0 hits** ✅

### 3.4 Commit atómico

```
refactor(evangelism): cierra Fase 1 RBAC — elimina paquete _evangelism_helpers y arregla fields obsoletos en tests
```

Commit `339539e9` (5 archivos, +8 / −395 líneas). Cambios:
- `D backend/api/_evangelism_helpers/__init__.py` (eliminado)
- `D backend/api/_evangelism_helpers/_shared.py` (eliminado)
- `M backend/crud/evangelism.py` (comentario referenciante actualizado)
- `M tests/test_evangelism_custom_role_regression.py` (1 test fix `nombre`→`name`)
- `M tests/test_evangelism_module_coverage.py` (4 tests fix `nombre`→`name`, `lugar`→`zone`)

## 4. Estado final de la Fase 1

| Métrica | Antes | Después |
|---|---|---|
| Hits de `require_pastor_or_admin` en `backend/api/evangelism*` | ~30+ (sesión 091db8811) → 10 al retomar (solo `_evangelism_helpers`) | **0** |
| Paquete `_evangelism_helpers` | Existente (387 LOC en 2 archivos) | Eliminado |
| Bug radical `crm:manage`-coincidence en evangelism | Latente vía wrapper `require_pastor_or_admin_with_sede` | Cerrado |
| Tests con campo obsoleto `nombre` en `/grupos` | 5 | 0 (corregidos a `name`) |
| Smoke canónico | 1 fallo encontrado | 2/2 suites verdes (19 passed + 1 xfailed) |
| Suite amplia | 4 fallos encontrados | 226/226 verdes |

## 5. Actualización documental

Se actualizaron 4 documentos del módulo:

1. **`docs/ESTADO_EVANGELISMO.md`**:
   - Añadida entrada "Actualizacion QA 2026-07-21 (cierre Fase 1 RBAC — wrapper legacy)" tras la sección 115 (línea ~117).
   - Añadida entrada 6 en "Cerrado recientemente" con el cierre formal.
   - Actualizada fila de `PARCIAL-RUNTIME-AUTH-001` en la tabla de IDs estables (sección 14).
2. **`docs/EVANGELISMO_RBAC_MATRIX.md`**:
   - Actualizada fecha de verificación de 2026-07-18 a 2026-07-21.
   - Añadida SECTION 10 "Verificación post-cierre (2026-07-21)" con comandos verificables y resultados.
   - Detallado el cierre del wrapper legacy en sección 9 "Estado documental".
3. **`docs/EVANGELISMO_QA_CHECKLIST.md`**:
   - Corregida la línea 133 obsoleta (decía "EDITOR puede quedar fuera de superficies con `require_pastor_or_admin` aunque tenga `evangelism:edit`" — tras la migración esto ya no aplica).
   - Añadida nota explicativa sobre el cierre del wrapper legacy.
4. **`docs/PLAN_EVANGELISMO_CALIDAD.md`**:
   - Actualizada fecha a 2026-07-21.
   - Reescrita la sección "Fase 1 — QA runtime de permisos" como cerrada con ID `PARCIAL-RUNTIME-AUTH-001`.
   - Actualizado el backlog vivo: `PARCIAL-RUNTIME-AUTH-001` movido a "Cerrado y no reabrir", `PARCIAL-STRATEGY-PAGE-001` y `PEND-STRATEGY-DECOMPOSE-001` re-categorizados como "Disciplina operativa continua" (no deuda pendiente).

Adicionalmente, se creó este documento `docs/CIERRA_FASE1_RBAC_2026-07-21.md` como bitácora detallada del cierre.

## 6. Próxima fase: Fase 2 — Descomposición de estrategia

Según `docs/PLAN_EVANGELISMO_CALIDAD.md` sección 5, la **Fase 2** aborda `PARCIAL-STRATEGY-PAGE-001` y `PEND-STRATEGY-DECOMPOSE-001`. Aunque ambos IDs están marcados como cerrados el 2026-07-18 en el ESTADO (consolidación en `useStrategyDetail.ts`), la PLAN los mantiene como "Disciplina operativa continua".

**Estado actual de `strategies/[id]/page.tsx`**:

- La extracción inicial de 7 hooks funcionales a `useStrategyDetail.ts` ya está hecha (2026-07-18): `useStrategy`, `useCustomRoles`, `useGroups`, `useSessions`, `useMetrics`, `useFollowUps`, `useRemotePersonaSearch`, `useSessionActions`, `useGroupActions`, `useAttendanceDrawer`.
- La `page.tsx` mantiene su estructura visual intacta; los hooks encapsulan fetching y estado.

**Orden recomendado para Fase 2** (a confirmar con el usuario):

1. **Leer y medir** `strategies/[id]/page.tsx` (LOC, complejidad por panel/tabs,Imports)
2. **Concurrentemente leer** `useStrategyDetail.ts` para entender el contrato estable (qué debería ya no mezclarse)
3. **Identificar paneles/tabs aún inlinados** en `page.tsx` que deberían ser componentes dedicados (StrategyGroupsPanel, StrategySessionsPanel, StrategyMetricsPanel, StrategyFollowUpsPanel, etc.)
4. **Congelar contrato actual** entre `page.tsx` ↔ `useStrategyDetail.ts` (tipos compartidos en `frontend/src/app/plataforma/evangelism/types.ts` o equivalente)
5. **Extraer paneles** a `components/evangelism/strategy/*` con props tipadas y sin duplicar fetches
6. **Validar cada extracción** con `npm run test:e2e:evangelism:deep` (cubre sesiones, rankings, multiplication, events/scanner) + `npm run lint` + typecheck
7. **Criterio de salida**: page.tsx como orquestador puro, menos lógica de negocio embebida, fetches centralizados y cancelables vía hooks existentes, cero regresiones de layout/permisos/rutas

**Comandos de validación de Fase 2**:

```bash
cd /root/ccf
# Baseline backend (no debe cambiar):
./venv/bin/python scripts/test_evangelism_quality.py
./venv/bin/python -m pytest -q -o addopts='' tests/test_evangelism_module_coverage.py
# Frontend e2e + lint + typecheck (deben quedar verdes):
cd /root/ccf/frontend
npm run test:e2e:evangelism
npm run test:e2e:evangelism:deep
npm run lint
npm run typecheck
```

**Pre-condiciones para Fase 2**:

- Árbol limpio (✅ tras commit `339539e9`)
- Baseline backend verde (✅ smoke 2/2 + suite 226/226)
- Frontend arrancable (verificar antes de empezar)
- El frontend e2e requiere Playwright instalado y `webServer` administrado vía `frontend/scripts/run-managed-playwright.mjs`

## 7. Notas para el siguiente agente

- `require_pastor_or_admin` SOLO sigue en módulos **CRM legítimos** (`backend/api/analytics.py`, `backend/api/crm/pipelines.py`) y su definición base en `backend/core/permissions.py:690`. NO debe usarse en ningún módulo que no sea CRM. El docstring L693-698 de `permissions.py` lo documenta oficialmente.
- Cualquier nuevo router evangelism debe usar `require_evangelism_read/edit/manage` vía `require_module_access("evangelism", <level>)`. NO crear nuevos wrappers con `require_pastor_or_admin`.
- La `suite amplia` ahora incluye `test_evangelism_custom_role_regression.py` (19 tests de RBAC que protegen el bug radical original); cualquier cambio en guards que reabra el bug `crm:manage`-coincidence fallará la suite.
- Si aparece un nuevo uso de `nombre`/`lugar` u otro campo obsoleto en PUT/POST `/grupos`, corregir a `name`/`zone` (u otros del schema `GrupoEvangelismoCreate/Update` con `extra=forbid`). El gate strict de schema detecta estos drifts.
