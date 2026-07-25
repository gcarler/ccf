# Auditoría Forense — Módulo Evangelismo (Completitud y Consistencia)

**Fecha:** 2026-07-25
**Objetivo:** Evaluar completitud, consistencia y confiabilidad operativa del módulo de evangelismo en backend, frontend, permisos, tests y documentación.
**Alcance:** 103 archivos, ~28,000 LOC (8,529 API + 2,114 CRUD/Schema/Model + 7,702 tests backend + 957 tests E2E + 4,215 frontend + 2,000 docs)

---

## Resumen Ejecutivo

| Severidad | Hallazgos | Estado |
|-----------|-----------|--------|
| **Crítico** | 1 | Abierto |
| **Alta** | 4 | 1 resuelto, 3 abiertos |
| **Media** | 6 | Abiertos |
| **Baja** | 3 | Abiertos |

**Hallazgo más relevante:** 3 funciones CRUD permiten resucitar registros soft-deletados (`actualizar_participante`, `remover_participante`, `submit_asistencia`) porque no filtran por `deleted_at` antes de buscar el registro objetivo.

---

## Fase 1: Completitud Backend

### 1.1 Inventario de Endpoints

| Sub-módulo | Endpoints | Método principal | Estado |
|------------|-----------|-----------------|--------|
| Estrategias | 6 | CRUD + generate-sessions | ✓ Completo |
| Roles personalizados | 5 | CRUD + seed excusas | ✓ Completo |
| Grupos | 14 | CRUD + seasons + analytics + visitors + mine | ✓ Completo |
| Sesiones | 12 | CRUD + bulk habilitar/deshabilitar + search personas | ✓ Completo |
| Asistencia | 8 | submit + bulk + follow-up CRUD | ✓ Completo |
| Eventos | 15 | CRUD + attendance + roles + analytics + export + dashboard | ✓ Completo |
| Scanner | 2 | generate + validate | ✓ Completo |
| Analytics | 8 | KPIs + trend + funnel + heatmap + alerts + velocity + groups + full | ✓ Completo |
| Reports | 3 | PDF + Excel + summary | ✓ Completo |
| Rankings | 3 | groups + monthly + leaders | ✓ Completo |
| Multiplication | 3 | check + split + history | ✓ Completo |
| Notifications | 1 | send-reminders | ✓ Completo |
| **TOTAL** | **81** | | **100% con handler funcional** |

**No se encontraron stubs ni endpoints sin implementación.**

### 1.2 CRUD ↔ API Mapping

| Operación | CRUD Function | Soft-Delete Filter | Sede Filter |
|-----------|--------------|-------------------|-------------|
| Listar estrategias | `get_estrategias` | ✓ | ✓ |
| Obtener estrategia | `get_estrategia` | ✓ | ✗ (PK only) |
| Crear estrategia | `create_estrategia` | N/A | ✓ |
| Actualizar estrategia | `update_estrategia` | ✓ | ✓ |
| Eliminar estrategia | `delete_estrategia` | ✓ | ✓ |
| Listar roles | `get_roles_personalizados` | ✓ | ✗ (by strategy) |
| Crear rol | `create_rol_personalizado` | ✓ (parent) | ✓ |
| Eliminar rol | `delete_rol_personalizado` | ✓ | ✓ |
| Listar participantes | `get_participantes` | ✓ | ✗ (by group) |
| Agregar participante | `agregar_participante` | N/A | ✓ |
| Actualizar participante | `actualizar_participante` | **✗ BUG** | ✓ |
| Remover participante | `remover_participante` | **✗ BUG** | ✓ |
| Submit asistencia | `submit_asistencia` | **✗ BUG** | ✓ |
| Seguimientos | `get_seguimientos` | ✓ | ✓ |
| Crear seguimiento | `create_seguimiento` | ✓ (parent) | ✓ |
| Actualizar seguimiento | `update_seguimiento` | ✓ | ✓ |
| Pendientes seguimiento | `get_pendientes_seguimiento` | ✓ | ✓ |
| Eliminar seguimiento | `delete_seguimiento` | ✓ | ✓ |
| Motivos excusa | `get_motivos_excusa` | ✗ (global) | ✗ (global) |
| Crear excusa | `create_motivo_excusa` | N/A | ✗ (global) |
| Actualizar excusa | `update_motivo_excusa` | ✗ | ✗ (global) |
| Eliminar excusa | `delete_motivo_excusa` | ✗ | ✗ (global) |
| Seed excusas | `seed_motivos_excusa` | N/A | ✗ (global) |

**Hallazgos:**
- **3 funciones CRUD con `deleted_at` faltante** (ver Fase 3)
- **No existen CRUD functions dedicadas** para `GrupoEvangelismo` y `SesionGrupo` — se gestionan directamente en los handlers de API

### 1.3 Schema ↔ API

| Entidad | Create | Update | Response | extra="forbid" | from_attributes |
|---------|--------|--------|----------|----------------|-----------------|
| Estrategia | ✓ | ✓ | ✓ | ✓ | ✓ |
| Rol Personalizado | ✓ | ✗ (no schema) | ✓ | ✓ | ✓ |
| Participante | ✓ | ✓ | ✓ | ✓ | ✓ |
| Asistencia Sesión | ✓ | ✓ | ✓ | ✓ | ✓ |
| Registro Seguimiento | ✓ | ✓ | ✓ | ✓ | ✓ |
| Motivo Excusa | ✓ | ✓ | ✓ | ✓ | ✓ |
| Bulk Asistencia | ✓ | N/A | N/A | ✓ | N/A |
| Grupo Evangelismo | ✓ | ✓ | **✗ MISSING** | ✓ | N/A |
| Sesión Grupo | ✓ | ✓ | ✓ | ✓ | ✓ |
| Asistencia Grupo | ✓ | N/A | N/A | ✓ | N/A |

**Hallazgos:**
- **`GrupoEvangelismoResponse` no existe** — los endpoints de grupo retornan `dict` manual en lugar de schema tipado
- **`RolPersonalizadoEstrategiaUpdate` no existe** — los roles no tienen endpoint PUT (solo DELETE + recreate)
- **`RegistroSeguimientoResponse`** es el único Response schema con `extra="forbid"` (inconsistente)

### 1.4 Model ↔ Schema

Todos los campos en Response schemas existen como columnas o `@hybrid_property` en los modelos. Sin drift detectado.

### 1.5 Orphan Endpoints

No se encontraron endpoints sin consumidor frontend. Todos los endpoints son consumidos por al menos una página.

### 1.6 Soft-Delete Completeness

| Modelo | Tiene `deleted_at` | Filtra en lectura | Estado |
|--------|-------------------|-------------------|--------|
| EstrategiaEvangelismo | ✓ | ✓ | OK |
| GrupoEvangelismo | ✓ | ✓ (en handler) | OK |
| SesionGrupo | ✓ | ✓ (en handler) | OK |
| Asistencia | ✓ | **✗ en upsert** | **BUG** |
| RegistroSeguimiento | ✓ | ✓ | OK |
| ParticipanteGrupo | ✓ | **✗ en update/remove** | **BUG** |
| MotivoExcusa | ✓ | **✗** (global) | Diseño intencional |
| LogAuditoria | ✓ | ✗ | Sin consumo |

---

## Fase 2: Consistencia RBAC

### 2.1 RBAC Uniformity

| Endpoint | Guard Used | Estado |
|----------|-----------|--------|
| 75 de 81 endpoints | `require_evangelism_read/edit/manage` | ✓ |
| `GET/PUT /grupos/{id}` | `get_current_user` + `_can_manage_grupo` | ⚠ Design |
| `GET/POST /grupos/sessions/{id}/attendance` | `get_current_user` + `_can_manage_grupo` | ⚠ Design |
| `POST /scanner/generate` | `require_module_access("evangelism", "manage")` | ⚠ Stylistic |
| `POST /scanner/validate` | `require_module_access("evangelism", "read")` | ⚠ Stylistic |

**Detalle:**
- Los 4 endpoints con `get_current_user` realizan autorización interna vía `_can_manage_grupo(db, current_user, house)` — permite a líderes de grupo acceder sus propios grupos sin necesitar `evangelism:read` blanket. Es diseño deliberado (per-resource RBAC), no privilege escalation.
- Los 2 endpoints scanner usan `require_module_access` (funcionalmente equivalente a `require_evangelism_*` pero estilísticamente distinto).

### 2.2 Sede Isolation

| Superficie | Sede Filter | Estado |
|------------|-------------|--------|
| Estrategias (list/create/update/delete) | ✓ | OK |
| Grupos (list/create/update/delete) | ✓ | OK |
| Sesiones (list/create/update/delete) | ✓ | OK |
| Asistencia (submit/bulk) | ✓ | OK |
| Seguimientos (list/create/update/delete) | ✓ | OK |
| Eventos (list/create/update/delete) | ✓ | OK |
| Analytics | ✓ | OK |
| Reports | ✓ | OK |
| Rankings | ✓ | OK |
| Multiplication | ✓ | OK |
| Scanner (generate/validate) | ✓ | OK |
| Motivos Excusa | ✗ (global) | Diseño intencional |

### 2.3 Endpoints con `require_evangelism_manage` para operaciones de solo lectura

| Endpoint | Guard | Operación | Observación |
|----------|-------|-----------|-------------|
| `GET /strategies/{id}/roles` | manage | Lectura | Podría ser `read` |
| `GET /excuses` | manage | Lectura | Podría ser `read` |
| `GET /events/analytics/global` | manage | Lectura | Podría ser `read` |
| `GET /events/dashboard-stats` | manage | Lectura | Podría ser `read` |
| `GET /multiplication/check` | manage | Lectura | Podría ser `read` |
| `GET /multiplication/history` | manage | Lectura | Podría ser `read` |

**Impacto:** Usuarios con `evangelism:read` o `evangelism:edit` no pueden acceder a datos de lectura que deberían ser visibles.

---

## Fase 3: Consistencia de Datos

### 3.1 Enum Consistency

| Enum | Modelo | Schema | Shared | Estado |
|------|--------|--------|--------|--------|
| EstadoAsistencia | `EstadoAsistenciaEnum` (ASISTIO/FALTO/EXCUSA) | `EstadoAsistenciaEnum` + `StatusAsistenciaCanonico` | `normalize_attendance_status` | ✓ Consistente |
| HabilitacionSesion | `HabilitacionSesionEnum` | `HabilitacionSesionEnum` | N/A | ✓ Consistente |
| Frecuencia | `FrecuenciaEnum` | `FrecuenciaEnum` | N/A | ✓ Consistente |
| TipoSeguimiento | `TipoSeguimientoEnum` | `TipoSeguimientoEnum` | N/A | ✓ Consistente |

El `StatusAsistenciaCanonico` (PRESENT/ABSENT/EXCUSED/FIRST_TIME) es la fuente unica para escritura; las variantes historicas son absorbidas por `_normalize_status_alias`.

### 3.2 Soft-Delete Bugs (CRÍTICO)

#### BUG-1: `actualizar_participante` permite mutar registros soft-deletados

**Archivo:** `backend/crud/evangelism.py:495`
**Evidencia:** El query inicial no filtra por `deleted_at.is_(None)`:
```python
part = db.query(models.ParticipanteGrupo).filter(
    models.ParticipanteGrupo.id == participante_id
).first()
```
**Impacto:** Un participante soft-deletado puede ser reactivado o modificado.
**Severidad:** Crítico

#### BUG-2: `remover_participante` permite desactivar registros soft-deletados

**Archivo:** `backend/crud/evangelism.py:536`
**Evidencia:** Mismo patrón que BUG-1 — sin filtro `deleted_at`.
**Impacto:** Un participante soft-deletado puede ser marcado como `activo=False` (doble eliminación).
**Severidad:** Alta

#### BUG-3: `submit_asistencia` puede resucitar asistencias soft-deletadas

**Archivo:** `backend/crud/evangelism.py:604-611`
**Evidencia:** El upsert busca registros existentes sin filtro `deleted_at`:
```python
existing = db.query(models.Asistencia).filter(
    models.Asistencia.sesion_id == sesion_uuid,
    models.Asistencia.persona_id == payload.persona_id,
).first()
```
**Impacto:** Una asistencia soft-deletada puede ser "revivida" por un upsert subsiguiente.
**Severidad:** Crítico

### 3.3 Sede Isolation Deep Dive

| Entidad | Join Chain para Sede | Estado |
|---------|---------------------|--------|
| Asistencia | asistencia → sesion → grupo → sede | ✓ |
| Seguimiento | seguimiento → asistencia → sesion → grupo → sede | ✓ |
| HistorialEmbudo | No tiene filtro sede (global) | ⚠ Diseño |
| MotivosExcusa | No tiene filtro sede (global) | ⚠ Diseño |

### 3.4 Type Drift Frontend ↔ Backend

| Tipo Frontend | Schema Backend | Coincidencia |
|---------------|----------------|--------------|
| `Strategy` (types.ts:108) | `EstrategiaEvangelismoResponse` | ✓ |
| `StrategyGroup` (types.ts:138) | No hay Response schema | ⚠ sin schema |
| `SessionRow` (types.ts:155) | `SesionGrupoResponse` | ✓ |
| `HabilitacionResponse` (types.ts:192) | Respuesta inline en handler | ✓ |
| `GroupDetailResponse` (types.ts:238) | No hay Response schema | ⚠ sin schema |
| `MultiplicationCheckItem` (types.ts:326) | Respuesta inline en handler | ✓ |
| `SplitResponse` (types.ts:346) | Respuesta inline en handler | ✓ |

### 3.5 Dead Code

**`_generate_codigo`** (`crud/evangelism.py:145`): Función definida pero nunca llamada. `create_estrategia` genera códigos con `f"EVG-{str(db_obj.id)[:8]}"`.

---

## Fase 4: Testing — Cobertura y Calidad

### 4.1 Test Count by Area

| Archivo | Tests | Cobertura |
|---------|-------|-----------|
| `test_evangelism_module_coverage.py` | 226 | Suite amplia |
| `test_evangelism_coverage.py` | 62 | Cobertura general |
| `test_evangelism_cms_workspace_more.py` | 63 | CMS/workspace |
| `test_evangelism_analytics_coverage.py` | 34 | Analytics |
| `test_evangelism_shared_coverage.py` | 30 | Shared utils |
| `test_evangelism_multiplication_coverage.py` | 16 | Multiplicación |
| `test_evangelism_habilitacion_regression.py` | 14 | Habilitación |
| `test_evangelism_crm_bridge.py` | 10 | CRM bridge |
| `test_evangelism_estrategias_coverage.py` | 10 | Estrategias |
| `test_evangelism_roles_coverage.py` | 9 | Roles |
| `test_evangelism_scanner_coverage.py` | 9 | Scanner |
| `test_evangelism_grupos_sesiones_coverage.py` | 7 | Grupos/sesiones |
| `test_evangelism_custom_role_regression.py` | 6 | Roles custom |
| `test_evangelism_followup_sede_regression.py` | 6 | Follow-up sede |
| `test_evangelism_reports_coverage.py` | 6 | Reports |
| `test_evangelism_quality_script.py` | 5 | Quality script |
| `test_evangelism_checkin_coverage.py` | 4 | Check-in |
| `test_evangelism_reports_api.py` | 4 | Reports API |
| `test_evangelism_triple7_flow.py` | 1 | Triple7 flow |
| **TOTAL** | **522** | |

### 4.2 RBAC Test Coverage

| Tipo de test | Cantidad | Archivos |
|-------------|----------|----------|
| Tests con admin fixture | ~480 | Todos |
| Tests con rol `coordinador` | 1 (cross-sede negative) | `module_coverage.py:2707` |
| Tests con `evangelism:read` permission | 3 | `module_coverage.py:2516,2534,2581` |
| Tests con `pastor` role | 2 | `shared_coverage.py`, `cms_workspace_more.py` |

**La cobertura RBAC no-admin es extremadamente baja** — solo 1 test positivo con `coordinador` y 3 tests con permiso granular. El resto son tests de admin.

### 4.3 False Green Detection

| Archivo | Estado | Detalle |
|---------|--------|---------|
| `test_evangelism_analytics_coverage.py` | ✓ Fixed | `_ok()` ya no acepta 500 |
| `test_evangelism_roles_coverage.py:104` | **✗ Abierto** | `assert resp.status_code in (200, 204, 404, 500)` — aún acepta 500 |

### 4.4 E2E Coverage

| Archivo | Tests | Flujos cubiertos |
|---------|-------|------------------|
| `sessions-detail.spec.ts` | 6 | Sesiones, asistencia, detalle |
| `rankings-multiplication.spec.ts` | 4 | Rankings, multiplicación |
| `events-scanner.spec.ts` | 4 | Eventos, scanner, check-in |
| `smoke.spec.ts` | dinámico | Dashboard, groups, rankings |
| **TOTAL** | **14 + dinámico** | |

**Flujos sin E2E:** analytics, reports, notifications, follow-up, roles.

### 4.5 Quality Script

`scripts/test_evangelism_quality.py` orquesta:
- Smoke mínimo (4 archivos)
- Regresiones críticas (2 archivos)
- Backend profundo (1 archivo, 226 tests)
- Frontend smoke (npm run test:e2e:evangelism)
- Frontend deep (npm run test:e2e:evangelism:deep)

**Cobertura del script:** ✓ Todos los sub-módulos están cubiertos por al menos una suite.

---

## Fase 5: Frontend — Completitud y Consistencia

### 5.1 Page Completeness

| Ruta | Archivo | LOC | Estado |
|------|---------|-----|--------|
| `/plataforma/evangelism` | `EvangelismClient.tsx` + `page.tsx` | — | ✓ |
| `/plataforma/evangelism/strategies/[id]` | `page.tsx` | 2,005 | ✓ (monolito) |
| `/plataforma/evangelism/groups` | `groups/page.tsx` | — | ✓ |
| `/plataforma/evangelism/groups/[id]` | `groups/[id]/page.tsx` | 1,001 | ✓ |
| `/plataforma/evangelism/events` | `events/page.tsx` | 1,736 | ✓ |
| `/plataforma/evangelism/events/[id]` | `events/[id]/page.tsx` + tabs | — | ✓ |
| `/plataforma/evangelism/rankings` | `rankings/page.tsx` | — | ✓ |
| `/plataforma/evangelism/multiplication` | `multiplication/page.tsx` | — | ✓ |
| `/plataforma/evangelism/scanner` | `scanner/page.tsx` | — | ✓ |

### 5.2 Component Completeness

| Componente | Importado por | Estado |
|------------|--------------|--------|
| `EvangelismShell.tsx` | Todas las páginas | ✓ |
| `StrategyCreationDrawer.tsx` | `EvangelismClient.tsx` | ✓ |
| `ConfirmActionDrawer.tsx` | Múltiples páginas | ✓ |
| `panels/StrategyHeader.tsx` | `strategies/[id]/page.tsx` | ✓ |
| `panels/StrategyOverviewForm.tsx` | `strategies/[id]/page.tsx` | ✓ |
| `panels/GroupCreationDrawer.tsx` | `strategies/[id]/page.tsx` | ✓ |
| `panels/AttendanceDrawer.tsx` | `strategies/[id]/page.tsx` | ✓ |
| `panels/CustomRolesPanel.tsx` | `strategies/[id]/page.tsx` | ✓ |

### 5.3 Type Safety

**0 errores TypeScript en `evangelism/`** — `npx tsc --noEmit` clean para el módulo.

### 5.4 Monolith Check

| Archivo | LOC | Umbral | Estado |
|---------|-----|--------|--------|
| `strategies/[id]/page.tsx` | 2,005 | >1500 | ⚠ Monolito |
| `events/page.tsx` | 1,736 | >1500 | ⚠ Monolito |
| `groups/[id]/page.tsx` | 1,001 | >1000 | ⚠ Grande |
| `useStrategyDetail.ts` | 476 | <500 | ✓ OK |

### 5.5 Hook Decomposition

`strategies/[id]/page.tsx` importa 8 hooks desde `useStrategyDetail.ts`:
- `useCustomRoles`, `useFollowUps`, `useGroups`, `useMetrics`
- `useRemotePersonaSearch`, `useSessionActions`, `useSessions`, `useStrategy`

**No hay implementaciones inline duplicadas** — la page delega completamente al hook.

### 5.6 Frontend RBAC

**LIMPIO.** `EvangelismShell.tsx` y `EvangelismClient.tsx` usan `hasModuleAccess('evangelism', 'read'/'manage')` — sin `isPastoralOrAdmin` ni `['admin', 'administrador', 'pastor'].includes(role)`.

---

## Fase 6: Documentación vs Realidad

### 6.1 API Contracts

| Discrepancia | Tipo |
|-------------|------|
| `GET /grupos/assignment-summary` — no documentado | Ruta faltante en doc |
| `GET /macro-despliegue` — no documentado | Ruta faltante en doc |
| `GET /strategies/{id}/metrics` — ubicación documentada incorrecta | Doc dice `main_estrategias.py`, real en `grupos_main.py` |
| Guard de `GET/POST /grupos/mine` — doc dice `get_current_user`, real es `require_evangelism_read` | Guard desactualizado |
| Guard de `POST /grupos/visitors` — doc dice `manage`, real es `edit` | Guard desactualizado |

### 6.2 RBAC Matrix

| Discrepancia | Severidad |
|-------------|-----------|
| Matriz documenta `GESTOR con evangelism:manage` — no existe en `DEFAULT_ROLES` | **Alta** |
| Matriz documenta `EDITOR con evangelism:edit` — no existe en `DEFAULT_ROLES` | **Alta** |
| Matriz documenta `LECTOR con evangelism:read` — no existe en `DEFAULT_ROLES` | **Alta** |

**Los roles GESTOR/EDITOR/LECTOR con permisos evangelism explícitos son fabricados en la documentación.** El acceso real depende de `UsuarioRolModulo` o `UsuarioPermisoOverride` runtime, no de `DEFAULT_ROLES`.

### 6.3 QA Checklist

| Sub-módulo | Cubierto en checklist |
|------------|----------------------|
| Estrategias | ✓ |
| Grupos | ✓ |
| Sesiones | ✓ |
| Asistencia | ✓ |
| Eventos | ✓ |
| Analytics | **✗** |
| Reports | **✗** |
| Rankings | ✓ |
| Multiplicación | ✓ |
| Scanner | ✓ |
| Notifications | **✗** |

### 6.4 LOC Counts (ESTADO_EVANGELISMO.md)

| Métrica | Documentado | Real | Drift |
|---------|-------------|------|-------|
| Backend LOC | 10,823 | 11,106 | +283 |
| Frontend LOC | 4,215 | 4,309 | +94 |

---

## Tabla Consolidada de Hallazgos

| ID | Severidad | Hallazgo | Archivo(s) | Línea(s) | Estado |
|----|-----------|---------|------------|----------|--------|
| F1-1 | **Crítico** | `actualizar_participante` no filtra `deleted_at` — puede mutar registros soft-deletados | `crud/evangelism.py` | 495 | Abierto |
| F1-2 | **Crítico** | `submit_asistencia` upsert no filtra `deleted_at` — puede resucitar asistencias soft-deletadas | `crud/evangelism.py` | 604-611 | Abierto |
| F1-3 | **Alta** | `remover_participante` no filtra `deleted_at` — puede desactivar registros soft-deletados | `crud/evangelism.py` | 536 | Abierto |
| F2-1 | **Alta** | 4 endpoints usan `get_current_user` en vez de `require_evangelism_*` (design inconsistency) | `grupos_main.py`, `grupos_asistencias.py` | varies | Abierto |
| F2-2 | **Alta** | 6 endpoints usan `require_evangelism_manage` para operaciones de solo lectura | `main_roles.py`, `events_main.py`, `multiplication.py` | varies | Abierto |
| F2-3 | **Alta** | RBAC matrix documenta roles GESTOR/EDITOR/LECTOR que no existen en DEFAULT_ROLES | `docs/EVANGELISMO_RBAC_MATRIX.md` | §6 | Abierto |
| F3-1 | **Media** | `GrupoEvangelismoResponse` no existe — endpoints retornan `dict` manual | `schemas/evangelism.py` | — | Abierto |
| F3-2 | **Media** | `RolPersonalizadoEstrategiaUpdate` no existe — roles sin PUT | `schemas/evangelism.py` | — | Abierto |
| F4-1 | **Media** | `test_evangelism_roles_coverage.py` acepta 500 como válido | `tests/test_evangelism_roles_coverage.py` | 104 | Abierto |
| F4-2 | **Media** | Cobertura RBAC no-admin extremadamente baja (1 test positivo con coordinador) | `tests/` | — | Abierto |
| F5-1 | **Media** | 3 páginas >1500 LOC (monolitos) | `strategies/[id]/page.tsx`, `events/page.tsx`, `groups/[id]/page.tsx` | — | Abierto |
| F5-2 | **Media** | QA checklist no cubre analytics, reports, notifications | `docs/EVANGELISMO_QA_CHECKLIST.md` | — | Abierto |
| F6-1 | **Baja** | API contracts documenta guards desactualizados | `docs/EVANGELISMO_API_CONTRACTS.md` | §3 | Abierto |
| F6-2 | **Baja** | LOC counts en ESTADO_EVANGELISMO.md desactualizados | `docs/ESTADO_EVANGELISMO.md` | 47-48 | Abierto |
| F6-3 | **Baja** | `_generate_codigo` es dead code | `crud/evangelism.py` | 145 | Abierto |

---

## Lo que está sólido

1. **100% de endpoints con handler funcional** — ningún stub
2. **Sede isolation completa** en todas las superficies auditadas (excepto global tables)
3. **Frontend RBAC limpio** — sin `isPastoralOrAdmin` ni hardcoding de roles
4. **0 errores TypeScript** en evangelismo
5. **522 tests backend** — suite amplia validada
6. **Enum consistency** completa entre modelo/schema/shared
7. **Soft-delete correcto** en estrategias, grupos, sesiones, seguimientos
8. **Hook decomposition** exitosa — `useStrategyDetail.ts` consolidado

---

## Recomendaciones (orden priorizado)

### Inmediato (esta sesión)

1. **FIX BUG-1:** Agregar `.filter(deleted_at.is_(None))` a `actualizar_participante` en `crud/evangelism.py:495`
2. **FIX BUG-2:** Agregar `.filter(deleted_at.is_(None))` a `remover_participante` en `crud/evangelism.py:536`
3. **FIX BUG-3:** Agregar `.filter(deleted_at.is_(None))` al upsert de `submit_asistencia` en `crud/evangelism.py:604`
4. **FIX F4-1:** Eliminar `500` de la whitelist en `test_evangelism_roles_coverage.py:104`

### Próxima sesión

5. **FIX F2-2:** Cambiar `require_evangelism_manage` a `require_evangelism_read` en los 6 endpoints de solo lectura
6. **FIX F2-3:** Corregir RBAC matrix — eliminar roles fabricados o documentar que dependen de configuración runtime
7. **FIX F5-2:** Agregar analytics, reports, notifications al QA checklist

### Futuro

8. Crear `GrupoEvangelismoResponse` schema y migrar endpoints de grupo
9. Agregar tests RBAC no-admin positivos (coordinador, lector, editor)
10. Continuar descomposición de monolitos (events/page.tsx, groups/[id]/page.tsx)

---

## Comandos de Validación

```bash
# Smoke mínimo
cd /root/ccf && ./venv/bin/python scripts/test_evangelism_quality.py

# Suite amplia
cd /root/ccf && ./venv/bin/python -m pytest -q -o addopts= --no-cov tests/test_evangelism_module_coverage.py

# TypeScript
cd /root/ccf/frontend && npx tsc --noEmit 2>&1 | grep evangelism/ | wc -l  # debe ser 0

# Frontend E2E
cd /root/ccf/frontend && npm run test:e2e:evangelism
```
