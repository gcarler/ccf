# Auditoría Integral del Módulo Evangelismo

**Proyecto:** CCF (Centro Cristiano Faro)
**Módulo:** Evangelismo
**Fecha:** 2026-07-26
**Alcance:** Seguridad, rendimiento, testing, accesibilidad, frontend, código
**Archivos revisados:** ~80 archivos, ~35,105 líneas de código fuente

---

## Resumen Ejecutivo

| Dimensión | Score | Hallazgos |
|-----------|-------|-----------|
| Seguridad | 4/10 | 3 critical, 4 high, 2 medium |
| Rendimiento | 4/10 | 3 critical, 4 high, 3 medium |
| Testing | 5/10 | 3 critical, 3 high, 4 medium |
| Frontend/A11y | 4/10 | 3 critical, 3 high, 2 medium |
| **Total** | **~4.3/10** | **12 critical, 14 high, 11 medium** |

**Hallazgos totales: 37**
**Hallazgos de auditoría forense anterior ABIERTOS: 15 de 15** (0 cerrados)

---

## ⚠️ HALLAZGO CRÍTICO: Auditoría Forense Anterior NO Cerrada

La auditoría forense del 2026-07-25 (`docs/AUDITORIA_FORENSE_EVANGELISMO_2026-07-25.md`) identificó **15 hallazgos**, incluyendo **3 CRÍTICOS** de soft-delete resurrection. **NINGUNO ha sido cerrado.** Los 3 bugs críticos siguen abiertos y sin tests de regresión.

---

## 1. HALLAZGOS DE SEGURIDAD

### S-01 — CRÍTICO: `actualizar_participante` permite resurrectión de soft-deleted
- **Archivo:** `backend/crud/evangelism.py:504-508`
- **Problema:** Query NO filtra `deleted_at.is_(None)`. Un participante soft-deleteado puede ser mutado de vuelta a existencia.
- **Impacto:** Data integrity — registros eliminados reviven silenciosamente.
- **Status:** ABIERTO desde auditoría forense 2026-07-25 (F1-1).
- **Fix:** Agregar `.filter(ParticipanteGrupo.deleted_at.is_(None))`.

### S-02 — CRÍTICO: `submit_asistencia` upsert sin filtro `deleted_at`
- **Archivo:** `backend/crud/evangelism.py:604-611`
- **Problema:** El upsert busca registros existentes sin filtrar `deleted_at`. Un registro de asistencia soft-deleteado es encontrado y sobrescrito (resurrectado).
- **Impacto:** Data integrity — historial de asistencia corrupto.
- **Status:** ABIERTO desde auditoría forense 2026-07-25 (F1-2).
- **Fix:** Agregar `.filter(Asistencia.deleted_at.is_(None))` al upsert.

### S-03 — CRÍTICO: `remover_participante` permite doble eliminación
- **Archivo:** `backend/crud/evangelism.py:545-548`
- **Problema:** Misma falla que S-01 — sin filtro `deleted_at`. Permite "eliminar" registros ya eliminados.
- **Impacto:** Data integrity.
- **Status:** ABIERTO desde auditoría forense 2026-07-25 (F1-3).
- **Fix:** Agregar filtro `deleted_at`.

### S-04 — HIGH: `add_groups_attendance` handler tiene el mismo bug de resurrectión
- **Archivo:** `backend/api/evangelism_grupos/grupos_asistencias.py:218-225`
- **Problema:** El handler de bulk attendance search sin `deleted_at` — mismo vector que S-02 pero en el endpoint handler.
- **Impacto:** Resurrectión vía bulk attendance.
- **Nuevo:** No estaba en la auditoría forense original.

### S-05 — HIGH: 6 endpoints usan `manage` para operaciones read-only
- **Archivos:** `main_roles.py:40,104`, `events_main.py:242,332`, `evangelism_multiplication.py:132,294`
- **Problema:** Endpoints de solo lectura (GET) usan `require_evangelism_manage` en vez de `require_evangelism_read`.
- **Impacto:** Denegación funcional — usuarios con `evangelism:read` o `evangelism:edit` no pueden acceder a datos de solo lectura.
- **Status:** ABIERTO desde auditoría forense (F2-2).

### S-06 — HIGH: RBAC matrix documenta roles fantasma
- **Archivo:** `docs/EVANGELISMO_RBAC_MATRIX.md`
- **Problema:** Documenta roles GESTOR, EDITOR, LECTOR que no existen en el sistema de permisos actual.
- **Impacto:** Confusión en implementación y testing.
- **Status:** ABIERTO desde auditoría forense (F2-3).

### S-07 — HIGH: `require_event_access` retorna 403 en vez de 404 para cross-sede
- **Archivo:** `backend/api/evangelism_events/_shared.py:73-74`
- **Problema:** Inconsistencia — groups/strategies usan 404 para cross-sede, events usa 403.
- **Impacto:** Information leak — 403 confirma existencia del recurso.

### S-08 — MEDIUM: `_count_personas` en multiplication no filtra `deleted_at`
- **Archivo:** `backend/evangelism_multiplication.py:99-105`
- **Problema:** Cuenta participantes soft-deleteados en el conteo de membresía.
- **Impacto:** Conteos incorrectos para decidir si un grupo puede dividirse.

### S-09 — MEDIUM: CampaignSeasons no scoped por sede
- **Archivo:** `backend/api/evangelism_grupos/grupos_main.py:677-695`
- **Problema:** `list_campaign_seasons` retorna TODAS las seasons sin filtro de sede.
- **Impacto:** Un usuario de Sede A ve seasons de Sede B. (Puede ser intencional pero no documentado.)

---

## 2. HALLAZGOS DE RENDIMIENTO

### P-01 — CRÍTICO: N+1 de 3 niveles en `strategy_alerts`
- **Archivo:** `backend/api/evangelism_analytics.py:621-660`
- **Problema:** Loop groups → sessions → attendance per session. Con 20 grupos × 5 sesiones = 101 queries.
- **Impacto:** Latencia extrema en analytics.

### P-02 — CRÍTICO: N+1 en `strategy_groups_detail` sparklines
- **Archivo:** `backend/api/evangelism_analytics.py:917-962`
- **Problema:** `_sparkline(g)` ejecuta 2 queries por grupo + `_group_att` 2 más. 20 grupos = 61 queries.
- **Impacto:** El endpoint más lento del módulo.

### P-03 — CRÍTICO: `strategy_full_analytics` carga 6 tablas completas en memoria
- **Archivo:** `backend/api/evangelism_analytics.py:1059-1548`
- **Problema:** Carga ALL groups, sessions, attendance, participants, personas, CRM cases en memoria. Computa 10 dimensiones analíticas con nested loops. IRT computation es O(groups × new_persons × sessions × attendance).
- **Impacto:** Memory exhaustion para estrategias grandes. CPU intensivo.

### P-04 — HIGH: 0% caching en endpoints de analytics
- **Archivos:** `evangelism_analytics.py`, `evangelism_rankings.py`, `evangelism_reports.py`
- **Problema:** Ningún endpoint usa caching. Analytics, rankings y reports se recalculan en cada request.
- **Impacto:** Performance degradada en uso intensivo.

### P-05 — HIGH: N+1 en `list_grupos` por lazy loading
- **Archivo:** `backend/api/evangelism_grupos/grupos_main.py:140-160`
- **Problema:** `_serialize_grupo` accede a `g.lider.nombre_completo` y `g.participantes` — lazy load por cada grupo.
- **Impacto:** Con 50 grupos, 100+ queries extra.

### P-06 — HIGH: Missing composite indexes en `asistencias`
- **Archivo:** `backend/models_evangelism.py`
- **Problema:** Sin composite index en `(sesion_id, persona_id)` — query más frecuente del módulo.
- **Problema:** Sin composite index en `(grupo_id, activo)` — usado en toda query de participation.
- **Problema:** Sin composite index en `(grupo_id, fecha_sesion)` — usado en analytics.

### P-07 — HIGH: PDF/Excel generation síncrono
- **Archivo:** `backend/api/evangelism_reports.py:136-332`
- **Problema:** Generación de PDF (reportlab) y Excel (openpyxl) en request handler síncrono.
- **Impacto:** Bloquea el worker thread.

### P-08 — MEDIUM: `get_grupo` retorna todo en un solo response
- **Archivo:** `backend/api/evangelism_grupos/grupos_main.py:472-518`
- **Problema:** Retorna lista completa de participantes, 20 sesiones con asistencia, trend de monitoreo, ausentes repetidos y alertas todo junto.
- **Impacto:** Respuestas multi-KB.

### P-09 — MEDIUM: `get_groups_assignment_summary` carga TODAS las personas
- **Archivo:** `backend/api/evangelism_grupos/grupos_main.py:205`
- **Problema:** `db.query(Persona).filter(sede_id == ...).all()` — carga todas las personas de la sede en memoria.
- **Impacto:** Memory exhaustion con sedes grandes.

### P-10 — MEDIUM: `macro-despliegue` full table scan
- **Archivo:** `backend/api/evangelism_analytics.py:862-873`
- **Problema:** `db.query(sesion_id, func.count(id)).group_by(sesion_id).all()` — scan completo de `asistencias`.

---

## 3. HALLAZGOS DE TESTING

### T-01 — CRÍTICO: 0 tests de regresión para bugs de soft-delete (S-01, S-02, S-03)
- **Archivo:** Tests existentes
- **Problema:** Los 3 bugs críticos de resurrectión no tienen tests de regresión. Si se fixean, no hay garantía de que no reaparezcan.
- **Impacto:** Regresiones silenciosas.

### T-02 — CRÍTICO: 0 tests RBAC boundary (403 para wrong role)
- **Archivo:** Tests existentes
- **Problema:** Ningún test verifica que un usuario con `evangelism:read` sea denegado en endpoints de `manage`. Solo 6 tests usan roles no-admin, y solo para negative testing.
- **Impacto:** Privilege escalation sin detección.

### T-03 — CRÍTICO: Endpoint `send-reminders` sin tests
- **Archivo:** `backend/api/evangelism_notifications.py`
- **Problema:** El único endpoint de notificaciones no tiene ningún test.
- **Impacto:** Funcionalidad completamente sin cobertura.

### T-04 — HIGH: False green en `test_evangelism_roles_coverage.py:104`
- **Archivo:** `tests/test_evangelism_roles_coverage.py:104`
- **Problema:** `assert resp.status_code in (200, 204, 404, 500)` — acepta 500 como válido.
- **Impacto:** Enmascara crashes del servidor.

### T-05 — HIGH: 0 tests de acceso concurrente
- **Archivos:** Todos los tests
- **Problema:** 0 tests para attendance double-submission, session toggle concurrent, group multiplication concurrent.
- **Impacto:** Race conditions sin detección.

### T-06 — HIGH: Sede isolation gaps
- **Archivos:** Tests
- **Problema:** Sin tests de cross-sede para: events, analytics, scanner, notifications.
- **Impacto:** Data leak entre sedes sin detección.

### T-07 — MEDIUM: E2E gaps críticos
- **Archivos:** `frontend/tests/e2e/evangelism/`
- **Problema:** Sin E2E para: strategy CRUD, group management, follow-up, analytics dashboard, reports, notifications, multiplication split.
- **Impacto:** Flujos principales sin cobertura E2E.

### T-08 — MEDIUM: `_ok()` broad matcher en 2 archivos (~30 tests)
- **Archivos:** `test_evangelism_coverage.py`, `test_evangelism_cms_workspace_more.py`
- **Problema:** `_ok()` acepta 400/403/404/405/422 como éxito.
- **Impacto:** False greens.

### T-09 — MEDIUM: PDF report test `xfail`
- **Archivo:** `tests/test_evangelism_reports_api.py`
- **Problema:** Test de PDF marcado como xfail porque reportlab no está instalado en CI.
- **Impacto:** Generación de PDF sin verificación en CI.

### T-10 — MEDIUM: Dead code en tests
- **Archivo:** `tests/test_evangelism_module_coverage.py`
- **Problema:** `_generate_codigo` es dead code documentado en auditoría forense pero no eliminado.

---

## 4. HALLAZGOS DE FRONTEND Y ACCESIBILIDAD

### F-01 — CRÍTICO: 90+ labels sin `htmlFor`/`id`
- **Archivos:** Todas las páginas evangelismo
- **Problema:** Prácticamente ningún `<label>` está programáticamente asociado a su input. Screen readers no pueden conectar labels con controles.
- **Archivos afectados:** strategies/[id]/page.tsx (7 labels), groups/groups/page.tsx (9), groups/[id]/page.tsx (13), events/page.tsx (18+), StrategyOverviewForm.tsx (8).

### F-02 — CRÍTICO: Strategy detail page 2005 líneas
- **Archivo:** `strategies/[id]/page.tsx`
- **Problema:** 2005 líneas, ~30 useState hooks, 7 vistas inline, CRUD de grupos, sesiones, attendance, roles todo en un componente.
- **Impacto:** Mantenibilidad crítica.

### F-03 — CRÍTICO: Events page 1736 líneas
- **Archivo:** `events/page.tsx`
- **Problema:** 1736 líneas, 8 vistas inline, CRUD de eventos, attendance, QR, scanner, audience presets todo en un componente.

### F-04 — HIGH: Keyboard navigation rota
- **Archivos:** strategies/[id]/page.tsx, groups/groups/page.tsx, events/page.tsx
- **Problema:** Clickable `<div>` sin `tabIndex`, `role`, ni `onKeyDown`. `RoleSelect` custom dropdown sin keyboard support. Tabs sin arrow-key navigation.
- **Impacto:** CRM inaccesible por teclado.

### F-05 — HIGH: Groups page 1442 líneas
- **Archivo:** `groups/groups/page.tsx`
- **Problema:** 1442 líneas, group CRUD, participant management, role assignment, attendance, filters.

### F-06 — HIGH: Group detail page 1001 líneas
- **Archivo:** `groups/[id]/page.tsx`
- **Problema:** 1001 líneas, session management, attendance, reports, monitoring.

### F-07 — HIGH: Sin error boundaries granulares
- **Archivos:** Todas las páginas evangelismo
- **Problema:** Solo `ModuleErrorBoundary` a nivel de módulo. Un error en cualquier sub-componente crashea toda la página.

### F-08 — MEDIUM: Dead code en `useStrategyDetail.ts`
- **Archivo:** `strategies/[id]/useStrategyDetail.ts`
- **Problema:** `useGroupActions` (line 305-372) y `useAttendanceDrawer` (line 406-476) están exportados pero nunca importados.

### F-09 — MEDIUM: Duplicate utilities
- **Archivos:** 4 archivos
- **Problema:** `getErrorMessage` definido idénticamente en 4 lugares. `formatLocalDate` en 2 lugares. `toAttendanceStatus` en 2 lugares.

---

## 5. RESUMEN POR SEVERIDAD

| Severidad | Cantidad | IDs |
|-----------|----------|-----|
| 🔴 Crítica | 12 | S-01, S-02, S-03, P-01, P-02, P-03, T-01, T-02, T-03, F-01, F-02, F-03 |
| 🟠 Alta | 14 | S-04, S-05, S-06, S-07, P-04, P-05, P-06, P-07, T-04, T-05, T-06, F-04, F-05, F-06 |
| 🟡 Media | 11 | S-08, S-09, P-08, P-09, P-10, T-07, T-08, T-09, T-10, F-07, F-08, F-09 |
| **Total** | **37** | |

---

## 6. ESTADO DE AUDITORÍA FORENSE ANTERIOR

| ID | Severidad | Hallazgo | Status | Test de regresión |
|----|-----------|----------|--------|-------------------|
| F1-1 | 🔴 Crítico | `actualizar_participante` sin `deleted_at` | **ABIERTO** | ❌ No |
| F1-2 | 🔴 Crítico | `submit_asistencia` upsert sin `deleted_at` | **ABIERTO** | ❌ No |
| F1-3 | 🟠 Alto | `remover_participante` sin `deleted_at` | **ABIERTO** | ❌ No |
| F2-1 | 🟠 Alto | 4 endpoints con guard incorrecto | **ABIERTO** | ❌ No |
| F2-2 | 🟠 Alto | 6 endpoints con `manage` en read-only | **ABIERTO** | ❌ No |
| F2-3 | 🟠 Alto | RBAC matrix documenta roles fantasma | **ABIERTO** | N/A |
| F3-1 | 🟡 Medio | `GrupoEvangelismoResponse` missing | **ABIERTO** | N/A |
| F3-2 | 🟡 Medio | `RolPersonalizadoEstrategiaUpdate` missing | **ABIERTO** | N/A |
| F4-1 | 🟡 Medio | Test acepta 500 | **ABIERTO** | ❌ Este ES el test |
| F4-2 | 🟡 Medio | RBAC non-admin coverage mínimo | **ABIERTO** | ❌ No |
| F5-1 | 🟡 Medio | 3 páginas >1500 LOC | **ABIERTO** | N/A |
| F5-2 | 🟡 Medio | QA checklist incompleto | **ABIERTO** | N/A |
| F6-1 | 🟢 Bajo | API contracts docs stale | **ABIERTO** | N/A |
| F6-2 | 🟢 Bajo | LOC counts stale | **ABIERTO** | N/A |
| F6-3 | 🟢 Bajo | `_generate_codigo` dead code | **ABIERTO** | N/A |

**Resultado: 0 de 15 hallazgos cerrados. 3 críticos sin fix ni test.**

---

## 7. PLAN DE ACCIÓN RECOMENDADO

### Fase 1: Seguridad — CRÍTICO (3 días)
1. **FIX S-01/S-02/S-03:** Agregar `deleted_at.is_(None)` a `actualizar_participante`, `submit_asistencia`, `remover_participante`
2. **FIX S-04:** Agregar `deleted_at` filter a `add_groups_attendance` handler
3. **FIX S-05:** Downgrade `manage` → `read` en 6 endpoints read-only
4. **Tests:** Agregar tests de regresión para los 3 bugs de soft-delete

### Fase 2: Rendimiento (4 días)
1. **FIX P-01/P-02:** Batch queries para analytics (eliminate N+1)
2. **FIX P-03:** Paginación o streaming para `strategy_full_analytics`
3. **FIX P-04:** Implementar caching para analytics y rankings
4. **FIX P-06:** Agregar composite indexes
5. **FIX P-07:** Mover PDF/Excel a BackgroundTasks

### Fase 3: Testing (4 días)
1. **FIX T-01:** Tests de regresión para soft-delete bugs
2. **FIX T-02:** RBAC boundary tests (403 para wrong role)
3. **FIX T-03:** Tests para `send-reminders`
4. **FIX T-04:** Eliminar 500 del test whitelist
5. **FIX T-05:** Concurrent access tests
6. **FIX T-06:** Sede isolation tests para events, analytics, scanner

### Fase 4: Frontend (4 días)
1. **FIX F-01:** Agregar `htmlFor`/`id` a 90+ labels
2. **FIX F-02:** Refactor strategies/[id]/page.tsx (2005 líneas)
3. **FIX F-03:** Refactor events/page.tsx (1736 líneas)
4. **FIX F-04:** Agregar keyboard access a clickable divs
5. **FIX F-07:** Agregar error boundaries granulares
6. **FIX F-08/F-09:** Eliminar dead code y duplicate utilities

---

## 8. CRONOGRAMA

| Fase | Días | Hallazgos |
|------|------|-----------|
| 1. Seguridad | 3 | 7 hallazgos (3 critical, 4 high) |
| 2. Rendimiento | 4 | 7 hallazgos (3 critical, 4 high) |
| 3. Testing | 4 | 7 hallazgos (3 critical, 3 high, 1 medium) |
| 4. Frontend | 4 | 6 hallazgos (3 critical, 3 high) |
| **Total** | **15 días** | **37 hallazgos** |

---

## 9. CRITERIOS DE ACEPTACIÓN

1. Los 3 bugs de soft-delete están fixeados y tienen tests de regresión
2. `add_groups_attendance` handler tiene filtro `deleted_at`
3. 6 endpoints read-only usan `read` en vez de `manage`
4. N+1 eliminados en analytics endpoints
5. Composite indexes en `asistencias` y `grupo_participantes`
6. PDF/Excel generation en BackgroundTasks
7. 0 tests aceptan 500 como válido
8. RBAC boundary tests para evangelism:read, evangelism:edit, evangelism:manage
9. 90+ labels con `htmlFor`/`id`
10. strategies/[id]/page.tsx < 500 líneas
11. Error boundaries en cada sección principal

---

## 10. ARCHIVOS REVISADOS

### Backend (18 archivos clave)
- `backend/models_evangelism.py` (544 líneas)
- `backend/schemas/evangelism.py` (608 líneas)
- `backend/crud/evangelism.py` (962 líneas)
- `backend/api/evangelism.py` (125 líneas)
- `backend/api/evangelism_shared.py` (682 líneas)
- `backend/api/evangelism_analytics.py` (1548 líneas)
- `backend/api/evangelism_reports.py` (461 líneas)
- `backend/api/evangelism_multiplication.py` (331 líneas)
- `backend/api/evangelism_notifications.py` (230 líneas)
- `backend/api/evangelism_rankings.py` (418 líneas)
- `backend/api/evangelism_main/main_estrategias.py` (475 líneas)
- `backend/api/evangelism_main/main_roles.py` (163 líneas)
- `backend/api/evangelism_grupos/grupos_main.py` (1214 líneas)
- `backend/api/evangelism_grupos/grupos_sesiones.py` (826 líneas)
- `backend/api/evangelism_grupos/grupos_asistencias.py` (609 líneas)
- `backend/api/evangelism_events/events_main.py` (681 líneas)
- `backend/api/evangelism_events/events_participantes.py` (335 líneas)
- `backend/api/evangelism_events/_shared.py` (75 líneas)

### Frontend (10 archivos clave)
- `frontend/src/app/plataforma/evangelism/strategies/[id]/page.tsx` (2005 líneas)
- `frontend/src/app/plataforma/evangelism/events/page.tsx` (1736 líneas)
- `frontend/src/app/plataforma/evangelism/groups/groups/page.tsx` (1442 líneas)
- `frontend/src/app/plataforma/evangelism/groups/[id]/page.tsx` (1001 líneas)
- `frontend/src/app/plataforma/evangelism/strategies/[id]/analytics/page.tsx` (967 líneas)
- `frontend/src/app/plataforma/evangelism/multiplication/page.tsx` (489 líneas)
- `frontend/src/app/plataforma/evangelism/scanner/page.tsx` (173 líneas)
- `frontend/src/app/plataforma/evangelism/strategies/[id]/useStrategyDetail.ts` (476 líneas)
- `frontend/src/app/plataforma/evangelism/strategies/[id]/panels/StrategyOverviewForm.tsx` (156 líneas)
- `frontend/src/app/plataforma/evangelism/types.ts` (363 líneas)

### Tests (10 archivos clave)
- `tests/test_evangelism_module_coverage.py` (3101 líneas, 226 tests)
- `tests/test_evangelism_coverage.py` (508 líneas, 62 tests)
- `tests/test_evangelism_analytics_coverage.py` (395 líneas, 34 tests)
- `tests/test_evangelism_habilitacion_regression.py` (668 líneas, 14 tests)
- `tests/test_evangelism_crm_bridge.py` (493 líneas, 10 tests)
- `tests/test_evangelism_multiplication_coverage.py` (202 líneas, 16 tests)
- `tests/test_evangelism_roles_coverage.py` (124 líneas, 9 tests)
- `tests/test_evangelism_custom_role_regression.py` (408 líneas, 6 tests)
- `tests/test_evangelism_followup_sede_regression.py` (261 líneas, 6 tests)
- `tests/test_evangelism_triple7_flow.py` (182 líneas, 1 test)

### Documentación (5 archivos clave)
- `docs/ESTADO_EVANGELISMO.md` (368 líneas)
- `docs/AUDITORIA_FORENSE_EVANGELISMO_2026-07-25.md` (486 líneas)
- `docs/EVANGELISMO_RBAC_MATRIX.md` (272 líneas)
- `docs/PLAN_DE_TRABAJO_EVANGELISMO.md` (326 líneas)
- `docs/CRM_EVANGELISM_BRIDGE.md` (69 líneas)

---

*Documento generado a partir de auditoría integral del módulo Evangelismo de CCF (2026-07-26).*
*37 hallazgos: 12 critical, 14 high, 11 medium.*
*15 hallazgos de auditoría forense anterior ABIERTOS (0 cerrados).*
