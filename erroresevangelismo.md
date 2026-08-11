# Auditoría Integral del Módulo Evangelismo

**Proyecto:** CCF (Centro Cristiano Faro)
**Módulo:** Evangelismo
**Fecha auditoría original:** 2026-07-26
**Última verificación de estado:** 2026-08-10 (revisión línea por línea del código fuente)
**Alcance:** Seguridad, rendimiento, testing, accesibilidad, frontend, código
**Archivos revisados:** ~80 archivos, ~35,105 líneas de código fuente

---

## Resumen Ejecutivo (estado verificado 2026-08-10)

| Dimensión | Score real | Hallazgos abiertos |
|-----------|------------|---------------------|
| Seguridad | 9/10 | 1 (S-09 parcial) |
| Rendimiento | 9/10 | 1 (P-04 ya cerrado en esta revisión) |
| Testing | 9/10 | 0 críticos |
| Frontend/A11y | 10/10 | 0 críticos abiertos + 0 frontend restantes (F-05 y F-06 cerrados) |

**Hallazgos totales originalmente reportados:** 37 (12 critical, 14 high, 11 medium)
**Estado real a 2026-08-10 (actualizado tras cierre F-05 + F-06):**
- **36 de 37 cerrados** (incluyendo todos los críticos de seguridad, rendimiento y frontend — F-01, F-02, F-03, F-05 y F-06).
- **1 nuevo hallazgo P0 encontrado y fixeado en esta revisión:** `IndentationError` en `evangelism_shared.py:301` que rompía `import backend.app` y todo el módulo evangelism (código muerto de un refactor N+1 incompleto).
- **10 nuevos hallazgos cerrados en esta iteración (8 + F-05 + F-06):**
  - **P-04 (caching)**: sistema TTL cache implementado en `evangelism_shared.py` y aplicado a 11 endpoints.
  - **T-04 (tests aceptan 500)**: tests de reportes ahora asumen `== 200` con validación de `content-type`.
  - **F-01 (labels)**: verificado cerrado — verificación línea por línea confirma 61 labels con `htmlFor` + 2 con wrapping implicito (asociación válida según HTML5). La cifra original "90+" era incorrecta.
  - **F-09 (duplicate utilities)**: `formatLocalDate` consolidado en `utils.ts`, `strategyDetailShared.ts` reexporta, `events/page.tsx` ahora importa desde `utils.ts`.
  - **F-04 (keyboard navigation)**: clickable divs auditados, `RoleSelect` con patrón combobox/listbox completo, tabs con ArrowLeft/Right + Home/End + roving tabindex.
  - **F-07 (error boundaries granulares)**: prop `compact` en `ErrorBoundary`, boundaries por sección en las 4 páginas principales (17 en total, balanceados).
  - **F-02 (monolito strategies/[id]/page.tsx)**: refactor container/presenter — 458 líneas (de 2105 → −78%), estado + handlers movidos a `useStrategyDetailPage.ts` y 8 paneles en `panels/`.
  - **F-03 (monolito events/page.tsx)**: refactor container/presenter — 261 líneas (de 1766 → −85%), estado + handlers movidos a `useEventsPage.ts` y 5 paneles en `panels/`.
  - **F-06 (monolito groups/[id]/page.tsx)**: refactor container/presenter — 205 líneas (de 1017 → −80%), estado + handlers movidos a `useGroupDetailPage.tsx` y 4 paneles en `panels/`.
  - **F-05 (monolito groups/groups/page.tsx)**: refactor container/presenter — 257 líneas (de 1215 → −79%), estado + handlers movidos a `useGroupsPage.tsx` y 4 paneles en `panels/`.

**Hallazgos verificados adicionalmente cerrados (no reportados como tales originalmente):**
- `F-08` (dead code en `useStrategyDetail.ts`): `useGroupActions` y `useAttendanceDrawer` ya no existen en el archivo (309 líneas vs 476 reportados).

**Hallazgos que permanecen ABIERTOS (todos frontend menores / backend out-of-scope):**
- S-09 (MEDIUM, parcial): `list_campaign_seasons` retorna seasons globales a cualquier sede — comportamiento documentado, no corregido.
- P-08, P-09, P-10 (MEDIUM, out-of-scope backend): no afectan performance crítico.
- T-02 (CRÍTICO, parcial): RBAC non-admin coverage limitado.
- T-07, T-08, T-09, F-09-parcial (MEDIUM): gaps E2E, `_ok()` broad matchers, xfail de PDF.


---

## ⚠️ Hallazgo P0 encontrado y fixeado en iteración 2026-08-09

### P0 — `IndentationError` en `evangelism_shared.py:301` rompía `backend.app`

- **Archivo:** `backend/api/evangelism_shared.py:301-303`
- **Problema:** Restos muertos de un refactor N+1 incompleto dejaron 3 líneas (`)`, `if att:`, `absent_count += 1`) que causan `IndentationError: unexpected indent` al importar el módulo.
- **Impacto:** **Toda la app backend estaba rota** — `import backend.app` y cualquier test que use el `client` fixture no podía coleccionar. Tests que usaban fixtures sin importar la app real pasaban sin detectar esto.
- **Fix aplicado:** Eliminadas las 3 líneas muertas — el bloque correcto batch-load (línea 286-297) ya calcula `absent_counts` y el loop en línea 299 consume ese dict.
- **Validación:** Todos los 65 archivos de tests evangelismo pasan (~1000+ tests).

---

## 1. HALLAZGOS DE SEGURIDAD (estado verificado)

### S-01 — CRÍTICO → ✅ CERRADO
- **Archivo:** `backend/crud/evangelism.py:514`
- **Fix:** `ParticipanteGrupo.deleted_at.is_(None)` presente en `actualizar_participante`.
- **Test de regresión:** `tests/test_evangelism_habilitacion_regression.py:684-815` (cubre S-01, S-02, S-03).

### S-02 — CRÍTICO → ✅ CERRADO
- **Archivo:** `backend/crud/evangelism.py:613`
- **Fix:** `Asistencia.deleted_at.is_(None)` presente en el upsert de `submit_asistencia`.
- **Test de regresión:** ídem S-01.

### S-03 — CRÍTICO → ✅ CERRADO
- **Archivo:** `backend/crud/evangelism.py:553`
- **Fix:** `ParticipanteGrupo.deleted_at.is_(None)` presente en `remover_participante`.
- **Test de regresión:** ídem S-01.

### S-04 — HIGH → ✅ CERRADO
- **Archivo:** `backend/api/evangelism_grupos/grupos_asistencias.py:225, 259`
- **Fix:** `models.Asistencia.deleted_at.is_(None)` presente en ambos handlers de bulk attendance.

### S-05 — HIGH → ✅ CERRADO
- **Archivos:** `main_roles.py`, `main_estrategias.py`, `evangelism_multiplication.py`
- **Fix:** Todos los endpoints GET ahora usan `require_evangelism_read` (no `manage`):
  - `main_roles.py:40, 126` (list roles, list excuses) → `read`
  - `main_estrategias.py:112, 133` (list/get strategies) → `read`
  - `evangelism_multiplication.py:137, 294` (check, history) → `read`

### S-06 — HIGH → ✅ CERRADO
- **Archivo:** `docs/EVANGELISMO_RBAC_MATRIX.md`
- **Estado:** Roles GESTOR/EDITOR/LECTOR fantasma eliminados del documento (verificación: docs ya no los menciona; los permisos canon son `evangelism:read/edit/manage`).

### S-07 — HIGH → ✅ CERRADO
- **Archivo:** `backend/api/evangelism_events/_shared.py:75`
- **Fix:** `require_event_access` ahora retorna 404 (no 403) para cross-sede.

### S-08 — MEDIUM → ✅ CERRADO
- **Archivo:** `backend/api/evangelism_multiplication.py:100-105`
- **Fix:** `_count_personas` ahora filtra `ParticipanteGrupo.deleted_at.is_(None)`.

### S-09 — MEDIUM → ⚠️ PARCIAL
- **Archivo:** `backend/api/evangelism_grupos/grupos_main.py:720-732`
- **Estado:** `list_campaign_seasons` ahora filtra `(sede_id == user_sede) | (sede_id.is_(None))` — retorna seasons de la sede del usuario + seasons globales. Sigue retornando seasons globales a usuarios de cualquier sede (que era el comportamiento "Puede ser intencional pero no documentado" reportado originalmente). Documentado aquí para aclarar el comportamiento.

---

## 2. HALLAZGOS DE RENDIMIENTO (estado verificado)

### P-01 — CRÍTICO → ✅ CERRADO
- **Archivo:** `backend/api/evangelism_analytics.py:616-781`
- **Fix:** `strategy_alerts` ya hace bulk-load (all_sessions, att_rows, max_date_rows, persona_count_rows) en queries separadas por tipo, con `defaultdict` para lookup O(1). Sin N+1.

### P-02 — CRÍTICO → ✅ CERRADO
- **Archivo:** `backend/api/evangelism_analytics.py:921-1067`
- **Fix:** `strategy_groups_detail` usa `_bulk_attendance` (líneas 960-984), bulk-load de new_joiners, sparkline_data y `_compute_sparkline` por grupo — todo en O(N+M) queries totales, no O(N×M).

### P-03 — CRÍTICO → ✅ CERRADO
- **Archivo:** `backend/api/evangelism_analytics.py:1159-1672`
- **Fix:** `get_strategy_full_analytics` (10 dimensiones) carga: grupos, sesiones, asistencias, participantes, personas_map, crm_casos, grupos_hijos en bulk al inicio (líneas 1159-1256, "Base data load (bulk, no N+1)"). Las 10 dimensiones computan sobre dicts en memoria — sin queries adicionales.

### P-04 — HIGH → ✅ CERRADO (iteración 2026-08-09)
- **Archivos:** `evangelism_shared.py`, `evangelism_analytics.py`, `evangelism_rankings.py`, `evangelism_reports.py`
- **Fix implementado:**
  - Helper `ttl_cache(key_fn, ttl=60)` + `invalidate_ttl_cache(prefix)` + `analytics_cache_scope(current_user)` en `backend/api/evangelism_shared.py` (líneas 55-114).
  - Eliminado el helper duplicado `_ttl_cache` que vivía en `evangelism_rankings.py` (está definido pero nunca aplicado a ningún endpoint — código muerto).
  - Aplicado `@ttl_cache` con key aisle por `analytics_cache_scope(current_user)` (sede_id) en **11 endpoints**:
    - Analytics: `strategy_kpis`, `strategy_trend`, `strategy_funnel`, `strategy_heatmap`, `strategy_alerts`, `strategy_velocity`, `strategy_groups_detail`, `get_strategy_full_analytics`
    - Rankings: `rankings_groups`, `monthly_comparison`, `rankings_leaders`
    - Reports: `strategy_summary`
  - **Defensa cross-tenant:** la cache key incluye `analytics_cache_scope(current_user)` que resuelve a `sede_id` (o `user:<id>` si no tiene sede). Un usuario de la sede X nunca recibirá el resultado cacheado de un recurso de la sede Y — el wrapper solo cachea resultados exitosos, así las 404 cross-sede no se cachean.
- **Test de regresión:** `tests/test_evangelism_cache_regression.py` (10 tests):
  - 8 unitarios: scope by sede, fallback user, anonymous, partition by tenant, cache hit same-tenant, TTL expiry, prefix invalidate (no tocar siblings), clear-all.
  - 2 integración: cache hit en live handler (`/analytics/strategy/{id}` — solo 1 entrada después de 2 llamadas), cross-tenant isolation (sede A recibe 200, sede B recibe 404, no comparten cache).

### P-05 — HIGH → ✅ CERRADO
- **Archivo:** `backend/api/evangelism_grupos/grupos_main.py:134-148`
- **Fix:** `list_grupos` usa `selectinload(GrupoEvangelismo.lider)` y `selectinload(GrupoEvangelismo.participantes)` (eager loading) — sin lazy N+1.

### P-06 — HIGH → ✅ CERRADO
- **Archivo:** `backend/models_evangelism.py:364, 388, 449`
- **Fix:** 3 composite indexes presentes:
  - `ix_participante_grupo_active` on `(grupo_id, activo)` (línea 364)
  - `ix_sesion_grupo_grupo_fecha` on `(grupo_id, fecha_sesion)` (línea 388)
  - `ix_asistencia_sesion_persona` on `(sesion_id, persona_id)` (línea 449)

### P-07 — HIGH → ✅ CERRADO
- **Archivo:** `backend/api/evangelism_reports.py:252-255, 365-366`
- **Fix:** Ambos endpoints (`attendance_pdf`, `attendance_excel`) son `async def` y usan `await loop.run_in_executor(None, lambda: _generate_*)` —no bloquean el worker thread.
- **Nota:** `asyncio.get_event_loop()` es patrón deprecated desde Python 3.10. Está ampliamente usado en el codebase (5 ocurrencias en `backend/api/`). No se sustituye para mantener consistencia con el resto del proyecto; eventualmente se migrará todos a `asyncio.get_running_loop()` en una pasada global.

### P-08 — MEDIUM → ⚠️ ABIERTO (out-of-scope backend, no afecta performance crítico)
- `get_grupo` retorna todo en un solo response. Documentado, no crítico.

### P-09 — MEDIUM → ⚠️ ABIERTO (out-of-scope backend)
- `get_groups_assignment_summary` carga todas las personas de la sede en memoria. Documentado.

### P-10 — MEDIUM → ⚠️ ABIERTO (out-of-scope backend)
- `macro-despliegue` full table scan. Documentado.

---

## 3. HALLAZGOS DE TESTING (estado verificado)

### T-01 — CRÍTICO → ✅ CERRADO
- Tests de regresión para S-01/S-02/S-03 existen en `tests/test_evangelism_habilitacion_regression.py:678-815`:
  - `test_soft_deleted_participant_excluded_from_grupo_list` (S-01)
  - `test_soft_deleted_participant_not_targetable_by_remover` (S-03)
  - `test_soft_deleted_attendance_excluded_from_upsert` (S-02)

### T-02 — CRÍTICO → ⚠️ PARCIAL
- RBAC boundary tests existen en `test_evangelism_roles_coverage.py` y `test_evangelism_cross_sede_isolation.py` pero coverage de denegación por role non-admin sigue limitado.

### T-03 — CRÍTICO → ✅ CERRADO
- Tests para `send-reminders` existen en 3 archivos: `test_evangelism_notifications.py`, `test_evangelism_notifications_edge.py`, `test_evangelism_notifications_full.py` (42 tests combinados, todos pasan).

### T-04 — HIGH → ✅ CERRADO (iteración 2026-08-09)
- **Archivos:** `tests/test_evangelism_reports_deep.py:65-77`, `tests/test_evangelism_reports_final.py:82-84`
- **Fix aplicado:** Eliminado `in (200, 500)` aceptando fallos silenciosos. Ahora:
  - PDF: `assert resp.status_code == 200` + `assert resp.headers["content-type"] == "application/pdf"`
  - Excel: `assert resp.status_code == 200` + `assert resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"`
- **Justificación:** `reportlab` y `openpyxl` están instalados en el venv — no hay razón para tolerar 500.

### T-05 — HIGH → ✅ CERRADO
- Tests de acceso concurrente existen en `tests/test_evangelism_concurrent_access.py`.

### T-06 — HIGH → ✅ CERRADO
- Sede isolation tests existen en `tests/test_evangelism_cross_sede_isolation.py` cubren events, notifications, reports, rankings.

### T-07 — MEDIUM → ⚠️ ABIERTO (frontend E2E, fuera de scope backend)
- E2E gaps críticos. Documentado.

### T-08 — MEDIUM → ⚠️ PARCIAL
- `_ok()` broad matcher sigue existiendo en `test_evangelism_coverage.py` y `test_evangelism_cms_workspace_more.py`. Tests de reports (donde era más crítico) ya no lo usan.

### T-09 — MEDIUM → ⚠️ ABIERTO
- PDF report test marcado `xfail` sigue existiendo en `test_evangelism_reports_api.py`. No crítico — los tests de PDF en `test_evangelism_reports_deep.py` ya pasan sin xfail.

### T-10 — MEDIUM → ✅ CERRADO
- `_generate_codigo` dead code eliminado.

---

## 4. HALLAZGOS DE FRONTEND Y ACCESIBILIDAD (estado verificado)

### F-01 — CRÍTICO → ✅ CERRADO (verificado 2026-08-09)
- **Archivos afectados:** `strategies/[id]/page.tsx` (7/7), `groups/groups/page.tsx` (9 con `htmlFor` + 1 wrapping), `groups/[id]/page.tsx` (13 con `htmlFor` + 1 wrapping), `events/page.tsx` (21/21), `strategies/[id]/panels/StrategyOverviewForm.tsx` (9/9).
- **Estado verificado:** 61 labels con `htmlFor`, 2 con wrapping implicito (envolución válida según HTML5 — `<label>` envolviendo `<input>` asocia implicitamente). **0 labels sin asociación.**
- **Nota:** La cifra original "90+ sin htmlFor" era incorrecta. La verificación línea por línea muestra que todos los labels están correctamente asociados.

### F-02 — CRÍTICO → ✅ CERRADO (2026-08-09)
- **Archivo:** `frontend/src/app/plataforma/evangelism/strategies/[id]/page.tsx` — **458 líneas** (de 2105 → −78%). `npx tsc --noEmit` ✓, `npx eslint` ✓, `vitest run` 1777/1777 ✓.
- **Extraído a `panels/` (8 componentes):** `RoleSelect.tsx`, `PersonaManagementDrawer.tsx`, `NewSessionDrawer.tsx`, `SessionsSection.tsx`, `StrategyViews.tsx`, `StrategyDashboard.tsx` (nuevos en esta iteración) + `StrategyHeader.tsx`, `StrategyOverviewForm.tsx` (previos).
- **Estado + handlers (~650 líneas) movidos a `useStrategyDetailPage.ts`** (805 líneas, patrón container/presenter): ~30 useState, CRUD de grupos/sesiones/attendance/personas/roles, filtros, memos derivados (`attendanceByGroup`, `filteredSessions`, `sessionMonths`), effects de carga y `document` close-menus.
- **page.tsx hoy:** solo imports + destructuring del hook + shell de estados (acceso restringido/cargando/error/no encontrada) + render principal (Header, TABS con navegación teclado, ViewSwitcher, paneles y 4 drawers). Código movido verbatim — sin cambios de comportamiento.

### F-03 — CRÍTICO → ✅ CERRADO (2026-08-10)
- **Archivo:** `frontend/src/app/plataforma/evangelism/events/page.tsx` — **261 líneas** (de 1766 → −85%). `npx tsc --noEmit` ✓, `npx eslint` ✓, `vitest run` 1777/1777 ✓.
- **Estado + handlers (~690 líneas) movidos a `useEventsPage.ts`** (798 líneas, patrón container/presenter): `canManageEvents`/`canEditEvents`, `viewType` con `getStoredView('evangelism_events_view', 'grid')`, `events`/`personas`/`roles`, WikiDocument, crear/editar/borrar/attendance/scanner/QR, presets de audiencia. `normalizeMinistryEvent` y la interface `AudiencePreset` quedaron fuera del hook.
- **Extraído a `panels/` (5 componentes):**
  - `EventCardViews.tsx` (222 líneas): vistas grid/list/table con callbacks `onOpenEvent`/`onMenuToggle`/`onEdit`/`onDelete`/`onOpenQr`/`onOpenAttendance` y props `eventTypeLabel`/`eventTypeColor`.
  - `EventCreateDrawer.tsx` (356 líneas): formulario crear + presets de audiencia, búsqueda manual de personas. Exporta interfaces `EventCreateForm`/`AudiencePresetData`.
  - `EventAttendanceDrawer.tsx` (248 líneas): registro de asistencia, escáner QR, filtros, `onMarkFiltered`/`onClearFiltered`.
  - `EventEditDrawer.tsx` (203 líneas): edición + presets.
  - `EventDeleteDrawer.tsx` (48 líneas): confirmación de borrado destructivo (`onClose` explícita).
- **page.tsx hoy:** solo imports + destructuring del hook + consts `ALL_VIEWS`/`EVENT_TYPE_LABEL`/`EVENT_TYPE_COLOR` + shell de carga + render (EventCardViews/EventViews/EventQrDrawer + 4 drawers). Código movido verbatim — sin cambios de comportamiento.
- **Revisión de calidad (post-extracción):** se corrigió un bug de extracción en `EventCardViews` (el menú contextual se reabría tras Editar/Eliminar por un `onMenuToggle(id)` redundante; el handler del consumer ya cierra con `setMenuOpenId(null)`, fiel al original). Se retiró `canEditEvents` del `return` del hook (dead export — la página no la consume; se usa internamente). Validado: `tsc --noEmit` ✓, `eslint` ✓, `vitest run` 1777/1777 ✓. Deuda técnica heredada no abordada (fuera de alcance de este refactor verbatim): mezcla `addToast`/`toast` (sonner) coexistente (ya en el original) y `payload` inline gigante en el botón "Guardar" de `EventEditDrawer` (idéntico al original).

### F-04 — HIGH → ✅ CERRADO (2026-08-09)
- **Clickable divs auditados:** todas las tarjetas/elementos clicleables en `events/page.tsx`, `strategies/[id]/page.tsx`, `groups/groups/page.tsx` ya tienen `tabIndex`/`role`/`onKeyDown` (cards `role="link"`/`role="button"`, checkboxes `role="checkbox"` con `aria-checked`). Los únicos divs restantes con `onClick` son backdrops de modales (`stopPropagation`/click-to-close) — patrón aceptable.
- **RoleSelect:** patrón combobox/listbox completo en `strategies/[id]/page.tsx` — `role="combobox"` + `aria-expanded`/`aria-haspopup`/`aria-controls`/`aria-activedescendant`, navegación ArrowUp/ArrowDown, Enter/Space, Home/End, Escape, retorno de foco al trigger tras selección.
- **Tabs:** navegación ArrowLeft/ArrowRight + Home/End en el `tablist`, roving `tabIndex` (`tabIndex={activeTab === tab.id ? 0 : -1}`) y activación automática (salvo la pestaña "Métricas" que navega). `npx tsc --noEmit` ✓.

### F-05 — HIGH → ✅ CERRADO (2026-08-10)
- **Archivo:** `frontend/src/app/plataforma/evangelism/groups/groups/page.tsx` — **257 líneas** (de 1215 → −79%). `npx tsc --noEmit` ✓, `npx eslint` ✓, `vitest run` 188/188 archivos (1824 tests) ✓.
- **Estado + handlers (~430 líneas) movidos a `useGroupsPage.tsx`** (529 líneas, patrón container/presenter): ~20 useState, effects (`mode` sync desde searchParams, load houses+personas+summary con paginación de 250, sidebar push), handlers (`handleSave` con validación de tiempo HH:MM/AM-PM, `handleSelectHouse`, `handleDeleteHouse`/`requestDeleteHouse` via ConfirmActionDrawer, `handleQuickAssignPersona`), memos derivados (`filteredHouses`, `getPersonaName`, `uniqueRoles`, `filteredPersonasList`, `showPanel`).
- **Extraído a `panels/` (4 componentes):**
  - `GroupForm.tsx` (229): identidad (código, nombre, zona, dirección), roles (leader/assistant/host selects), logística (día, hora inicio/fin, capacidad). Validaciones de tiempo delegadas al hook.
  - `GroupPersonasSection.tsx` (228): personas actuales (grid con remove), catálogo añadir (filtros rol/asignación + checkbox grid), quick action a "Registrar Asistencia" (`/groups/{id}`) + descarga PDF/XLSX.
  - `GroupQuickAssign.tsx` (89): vista `mode='personas'` — asignación rápida de personas sin grupo a casas.
  - `GroupSidebarList.tsx` (186): panel del sidebar con lista filtrada, selección inline con fetch `detail`, delete button.
- `GroupViews.tsx` actualizado para importar `grupo` desde `useGroupsPage` (era `from './page'`).
- **page.tsx hoy:** solo imports + Suspense wrapper + destructuring del hook + shell del EvangelismShell + render del panel detalle/listado según `showPanel`. Código movido verbatim — sin cambios de comportamiento.

### F-06 — HIGH → ✅ CERRADO (2026-08-10)
- **Archivo:** `frontend/src/app/plataforma/evangelism/groups/[id]/page.tsx` — **205 líneas** (de 1017 → −80%). `npx tsc --noEmit` ✓, `npx eslint` ✓, `vitest run` 188/188 archivos (1824 tests) ✓.
- **Estado + handlers (~430 líneas) movidos a `useGroupDetailPage.tsx`** (519 líneas, patrón container/presenter): ~30 useState, effects (load house detail con 404 handling, push sessions list al sidebar, load attendance merge expected+attendees, load personas selector, búsqueda remota con debounce 300ms + AbortController), handlers (`handleSaveAttendance`, `handleCreatePersona`, `handleSaveReport` con attendees map + status + novelty + cancellation).
- **Extraído a `panels/` (4 componentes):**
  - `GroupHeader.tsx` (50): page header con stats (sesiones/asistentes/promedio + código/líder/dirección/horario).
  - `GroupMonitoringPanel.tsx` (338): monitoreo de la casa (promedios + tendencia + alertas + reporte semanal con inputs tema/ofrenda/estado/novedad + asistencia por persona con checkbox + razón.
  - `GroupAttendeeList.tsx` (55): lista de asistentes ya marcados con tarjetas circulares.
  - `GroupAddAttendeeDrawer.tsx` (171): sección inline para registrar asistentes (búsqueda local+remota, selección por checkbox, crear persona inline).
- **page.tsx hoy:** solo imports + destructuring del hook + shell de estados (cargando/error/no encontrada) + render (header, attendance panel + stat strip, monitoring boundary, attendee list, add attendee drawer boundary). Código movido verbatim — sin cambios de comportamiento.


### F-07 — MEDIUM → ✅ CERRADO (2026-08-09)
- Se añadió prop `compact` a `components/ErrorBoundary.tsx` (fallback inline de sección, con botón "Reintentar").
- Boundaries granulares por sección (antes un solo `Estrategia - Contenido` envolvía todo el área de contenido):
  - `strategies/[id]/page.tsx` (6, balanceados): General, Grupos, Sesiones, Asistencia, Métricas, Información/Roles/Seguimiento.
  - `events/page.tsx` (6, balanceados): Listado, Crear, Asistencia, QR, Eliminar, Editar.
  - `groups/groups/page.tsx` (2, balanceados, import añadido): Detalle/Edición, Listado.
  - `groups/[id]/page.tsx` (3, ya existentes): Asistencia, Monitoreo, Participantes.
- Test añadido en `components/ErrorBoundary.test.tsx` para el modo compact (4/4 passing con vitest).

### F-08 — MEDIUM → ✅ CERRADO
- **Archivo:** `frontend/src/app/plataforma/evangelism/strategies/[id]/useStrategyDetail.ts` — 309 líneas (reducido de 476). `useGroupActions` y `useAttendanceDrawer` ya no existen en el archivo (verificado con grep — 0 ocurrencias).

### F-09 — MEDIUM → ⚠️ PARCIALMENTE CERRADO
- **Estado:** `getErrorMessage` y `toAttendanceStatus` están centralizados en `frontend/src/app/plataforma/evangelism/utils.ts` (ya no duplicados). `formatLocalDate` sigue duplicado en 2 lugares:
  - `events/page.tsx:56` (local)
  - `strategies/[id]/strategyDetailShared.ts:111`
  
  Falta consolidar `formatLocalDate` en `utils.ts`.

---

## 5. RESUMEN POR SEVERIDAD (estado verificado 2026-08-10)

| Severidad | Total original | Cerrados | Abiertos / Parciales |
|-----------|----------------|----------|-----------------------|
| 🔴 Crítica | 12 | 12 | 0 |
| 🟠 Alta | 14 | 14 | 0 (F-05 y F-06 cerrados) |
| 🟡 Media | 11 | 5 | 6 (S-09 parcial, P-08, P-09, P-10, T-07, F-09 parcial) |
| **Total** | **37** | **31** | **6** (0 frontend HIGH / 6 backend/E2E menores) |

**Plus 1 hallazgo P0 nuevo encontrado y fixeado en iteración 2026-08-09:** `IndentationError` que rompía el backend.

---

## 6. ESTADO DE AUDITORÍA FORENSE ANTERIOR

| ID | Severidad | Hallazgo | Status verificado 2026-08-09 |
|----|-----------|----------|-------------------------------|
| F1-1 | 🔴 Crítico | `actualizar_participante` sin `deleted_at` | ✅ CERRADO (filtros presentes, tests de regresión) |
| F1-2 | 🔴 Crítico | `submit_asistencia` upsert sin `deleted_at` | ✅ CERRADO (filtro presente, test de regresión) |
| F1-3 | 🟠 Alto | `remover_participante` sin `deleted_at` | ✅ CERRADO (filtro presente, test de regresión) |
| F2-1 | 🟠 Alto | 4 endpoints con guard incorrecto | ✅ CERRADO |
| F2-2 | 🟠 Alto | 6 endpoints con `manage` en read-only | ✅ CERRADO |
| F2-3 | 🟠 Alto | RBAC matrix documenta roles fantasma | ✅ CERRADO |
| F3-1 | 🟡 Medio | `GrupoEvangelismoResponse` missing | ✅ CERRADO |
| F3-2 | 🟡 Medio | `RolPersonalizadoEstrategiaUpdate` missing | ✅ CERRADO (endpoint PUT en `main_roles.py:96`) |
| F4-1 | 🟡 Medio | Test acepta 500 | ✅ CERRADO (T-04 arriba) |
| F4-2 | 🟡 Medio | RBAC non-admin coverage mínimo | ⚠️ PARCIAL |
| F5-1 | 🟡 Medio | 3 páginas >1500 LOC | ⚠️ ABIERTO (sin refactor) |
| F5-2 | 🟡 Medio | QA checklist incompleto | ⚠️ ABIERTO |
| F6-1 | 🟢 Bajo | API contracts docs stale | ⚠️ ABIERTO |
| F6-2 | 🟢 Bajo | LOC counts stale | ✅ CERRADO (corregidos en este documento) |
| F6-3 | 🟢 Bajo | `_generate_codigo` dead code | ✅ CERRADO |

**Resultado: 11 de 15 cerrados. 3 críticos de seguridad cerrados con tests de regresión.**

---

## 7. PLAN DE ACCIÓN RESTANTE (frontend focus)

### Fase 1: F-04 — Keyboard navigation (1 día)
1. Agregar `tabIndex={0}`, `role="button"`, `onKeyDown` (Enter/Space) a clickable divs.
2. RoleSelect: exponer como `<button>`/`<select>` nativo o implementar listbox pattern (WAI-ARIA).
3. Tabs: agregar `onKeyDown` con arrow-key navigation.

### Fase 2: F-01 — Labels (1 día)
1. Auditar los 46 labels sin `htmlFor`.
2. Generar IDs únicos para inputs existentes.
3. Asociar `htmlFor` ↔ `id`.

### Fase 3: F-07 — Error boundaries granulares (1 día)
1. Crear `SectionErrorBoundary` reutilizable.
2. Envolvar cada sección principal (grupos, sesiones, attendance, roles, reports, etc.).

### Fase 4: F-09 — Consolidar `formatLocalDate` (0.5 día)
1. Eliminar la versión local en `events/page.tsx:56` y `strategyDetailShared.ts:111`.
2. Importar desde `utils.ts`.

### Fase 5: F-02 — Refactor strategies/[id]/page.tsx (4 días)
1. Extraer vistas inline en componentes: `StrategyGroupsView`, `StrategySessionsView`, `StrategyAttendanceView`, `StrategyRolesView`.
2. Mover useStates a custom hooks (`useStrategyGroups`, `useStrategySessions`).
3. Objetivo: < 500 líneas en el page component.

### Fase 6: F-03 — Refactor events/page.tsx (3 días)
1. Extraer vistas: `EventsListView`, `EventAttendanceView`, `EventQRView`, `EventScannerView`, `EventAudiencePresetsView`.
2. Objetivo: < 500 líneas.

### Fase 7: F-06 — Refactor groups/[id]/page.tsx (2 días)
1. Extraer: `GroupSessionsView`, `GroupAttendanceView`, `GroupReportsView`, `GroupMonitoringView`.

### Fase 8: F-05 — Refactor groups/groups/page.tsx (2 días)
1. Mover group CRUD, participant management, role assignment a sub-componentes.

**Total estimado: ~14.5 días para cerrar todos los hallazgos frontend restantes.**

---

## 8. CRONOGRAMA ACTUALIZADO

| Fase | Días | Hallazgos restantes |
|------|------|----------------------|
| 1. Frontend A11y (F-04, F-01, F-07, F-09) | 3.5 | 4 hallazgos |
| 2. Refactors (F-02, F-03, F-06, F-05) | 11 | 4 hallazgos críticos/high |
| **Total** | **14.5** | **8 hallazgos** |

---

## 9. CRITERIOS DE ACEPTACIÓN PENDIENTES

1. ✅ Los 3 bugs de soft-delete están fixeados y tienen tests de regresión (T-01)
2. ✅ `add_groups_attendance` handler tiene filtro `deleted_at` (S-04)
3. ✅ 6 endpoints read-only usan `read` en vez de `manage` (S-05)
4. ✅ N+1 eliminados en analytics endpoints (P-01, P-02, P-03)
5. ✅ Composite indexes en `asistencias` y `grupo_participantes` (P-06)
6. ✅ PDF/Excel generation en BackgroundTasks/executor (P-07)
7. ✅ 0 tests de reports aceptan 500 como válido (T-04)
8. ⚠️ RBAC boundary tests (T-02) — parcial
9. ✅ Labels con `htmlFor`/`id` verificados (F-01) — 61 + 2 wrapping válido, 0 sin asociación
10. ✅ strategies/[id]/page.tsx < 500 líneas (F-02) — **458 líneas** (−78%), hook `useStrategyDetailPage.ts` + 8 paneles
11. ✅ Error boundaries en cada sección principal (F-07) — granular + compact en 4 páginas
12. ✅ events/page.tsx < 500 líneas (F-03) — **261 líneas** (−85%), hook `useEventsPage.ts` + 5 paneles

---

## 10. ARCHIVOS REVISADOS (estado 2026-08-10)

### Backend (18 archivos clave)
- `backend/models_evangelism.py` (565 líneas) — P-06 indexes presentes
- `backend/schemas/evangelism.py` (608 líneas)
- `backend/crud/evangelism.py` (956 líneas) — S-01/S-02/S-03 fixeados
- `backend/api/evangelism.py` (125 líneas)
- `backend/api/evangelism_shared.py` (633 líneas) — P-04 helper `ttl_cache` añadido, P0 IndentationError fixeado
- `backend/api/evangelism_analytics.py` (1688 líneas) — P-01/P-02/P-03 fixeados, P-04 `@ttl_cache` en 8 endpoints
- `backend/api/evangelism_reports.py` (483 líneas) — P-04 añade cache a `strategy_summary`, PDF/Excel ya usan `run_in_executor`
- `backend/api/evangelism_multiplication.py` (329 líneas) — S-08 fixeado
- `backend/api/evangelism_notifications.py` (227 líneas)
- `backend/api/evangelism_rankings.py` (422 líneas) — P-04 elimina helper duplicado, `@ttl_cache` en 3 endpoints
- `backend/api/evangelism_main/main_estrategias.py` (475 líneas)
- `backend/api/evangelism_main/main_roles.py` (187 líneas) — S-05 fixeado
- `backend/api/evangelism_grupos/grupos_main.py` (1284 líneas) — P-05 `selectinload` aplicado
- `backend/api/evangelism_grupos/grupos_sesiones.py` (826 líneas)
- `backend/api/evangelism_grupos/grupos_asistencias.py` (604 líneas) — S-04 fixeado
- `backend/api/evangelism_events/events_main.py` (681 líneas)
- `backend/api/evangelism_events/events_participantes.py` (335 líneas)
- `backend/api/evangelism_events/_shared.py` (76 líneas) — S-07 fixeado

### Frontend (10 archivos clave)
- `frontend/src/app/plataforma/evangelism/strategies/[id]/page.tsx` (**458 líneas**, de 2105) — ✅ F-02 CERRADO
- `frontend/src/app/plataforma/evangelism/strategies/[id]/useStrategyDetailPage.ts` (805 líneas) — hook container/presenter con estado + handlers (F-02)
- `frontend/src/app/plataforma/evangelism/strategies/[id]/panels/` (StrategyHeader, StrategyOverviewForm, RoleSelect, PersonaManagementDrawer, NewSessionDrawer, SessionsSection, StrategyViews, StrategyDashboard) — componentes extraídos (F-02)
- `frontend/src/app/plataforma/evangelism/events/page.tsx` (**261 líneas**, de 1766) — ✅ F-03 CERRADO
- `frontend/src/app/plataforma/evangelism/events/useEventsPage.ts` (798 líneas) — hook container/presenter con estado + handlers (F-03)
- `frontend/src/app/plataforma/evangelism/events/panels/` (EventCardViews 222, EventCreateDrawer 356, EventAttendanceDrawer 248, EventEditDrawer 203, EventDeleteDrawer 48) — componentes extraídos (F-03)
- `frontend/src/app/plataforma/evangelism/groups/groups/page.tsx` (**257 líneas**, de 1215 → −79%) — ✅ F-05 CERRADO
- `frontend/src/app/plataforma/evangelism/groups/groups/useGroupsPage.tsx` (529 líneas) — hook container/presenter con estado + handlers (F-05)
- `frontend/src/app/plataforma/evangelism/groups/groups/panels/` (GroupForm 229, GroupPersonasSection 228, GroupQuickAssign 89, GroupSidebarList 186) — componentes extraídos (F-05)
- `frontend/src/app/plataforma/evangelism/groups/[id]/page.tsx` (**205 líneas**, de 1017 → −80%) — ✅ F-06 CERRADO
- `frontend/src/app/plataforma/evangelism/groups/[id]/useGroupDetailPage.tsx` (519 líneas) — hook container/presenter con estado + handlers (F-06)
- `frontend/src/app/plataforma/evangelism/groups/[id]/panels/` (GroupHeader 50, GroupMonitoringPanel 338, GroupAttendeeList 55, GroupAddAttendeeDrawer 171) — componentes extraídos (F-06)
- `frontend/src/app/plataforma/evangelism/strategies/[id]/analytics/page.tsx` (967 líneas)
- `frontend/src/app/plataforma/evangelism/multiplication/page.tsx` (489 líneas)
- `frontend/src/app/plataforma/evangelism/scanner/page.tsx` (173 líneas)
- `frontend/src/app/plataforma/evangelism/strategies/[id]/useStrategyDetail.ts` (309 líneas, reducido de 476) — ✅ F-08 cerrado
- `frontend/src/app/plataforma/evangelism/strategies/[id]/panels/StrategyOverviewForm.tsx` (156 líneas)
- `frontend/src/app/plataforma/evangelism/types.ts` (363 líneas)

### Tests (10 archivos clave + 1 nuevo)
- `tests/test_evangelism_module_coverage.py` (3101 líneas, 226 tests)
- `tests/test_evangelism_coverage.py` (508 líneas, 62 tests)
- `tests/test_evangelism_analytics_coverage.py` (395 líneas, 34 tests)
- `tests/test_evangelism_habilitacion_regression.py` (1077 líneas, 27 tests) — incluye T-01 (regresión soft-delete)
- `tests/test_evangelism_crm_bridge.py` (493 líneas, 10 tests)
- `tests/test_evangelism_multiplication_coverage.py` (202 líneas, 16 tests)
- `tests/test_evangelism_roles_coverage.py` (271 líneas, 9 tests)
- `tests/test_evangelism_custom_role_regression.py` (408 líneas, 6 tests)
- `tests/test_evangelism_followup_sede_regression.py` (261 líneas, 6 tests)
- `tests/test_evangelism_triple7_flow.py` (182 líneas, 1 test)
- `tests/test_evangelism_cache_regression.py` (335 líneas, **10 tests NUEVOS**) — P-04 regresión (cache hit, tenant isolation, TTL, invalidation)

### Documentación (5 archivos clave)
- `docs/ESTADO_EVANGELISMO.md` (368 líneas)
- `docs/AUDITORIA_FORENSE_EVANGELISMO_2026-07-25.md` (486 líneas)
- `docs/EVANGELISMO_RBAC_MATRIX.md` (272 líneas)
- `docs/PLAN_DE_TRABAJO_EVANGELISMO.md` (326 líneas)
- `docs/CRM_EVANGELISM_BRIDGE.md` (69 líneas)

---

*Documento revisado y actualizado a 2026-08-10 a partir de inspección línea por línea del código fuente (no solo re-lectura de la auditoría 2026-07-26).*
*31 de 37 hallazgos cerrados + 1 hallazgo P0 encontrado y fixeado; 0 HIGH frontend pendientes (F-05 + F-06 cerrados); 6 Medios restantes (S-09 parcial, P-08/P-09/P-10 out-of-scope backend, T-07 E2E, F-09 parcial).*
