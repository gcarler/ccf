# Revisión UI — Módulo de Proyectos CCF (Full-Stack)

**Fecha de auditoría:** 2026-07-23  
**Alcance:** Frontend + Backend + Base de datos del módulo de Proyectos  
**Objetivo:** Evaluar calidad, consistencia, seguridad y performance de todo el módulo.

---

## 1. Resumen Ejecutivo

El módulo de Proyectos es el más completo de la plataforma CCF: 46 endpoints API, 11 tablas en BD, 27 componentes frontend, y ~14,300 líneas de código. La arquitectura sigue un patrón limpio (API → CRUD → ORM) con multi-tenant estricto (Axioma 3) y RBAC de doble capa.

### Puntuación por Dimensión

| Dimensión | Puntuación | Comentario |
|-----------|------------|------------|
| Arquitectura Backend | 8/10 | Patrón API→CRUD→ORM limpio; separación clara |
| Seguridad / Auth | 9/10 | RBAC dual + Axioma 3 + IDOR protection |
| Modelado BD | 7/10 | UUID PKs, soft-delete, indexes, CHECK constraints |
| Calidad Backend | 7/10 | ORM puro, validación Pydantic, sin TODOs pendientes |
| Frontend Components | 5/10 | TaskDetailPanel monolítico (1,442 líneas) |
| Testing Backend | 7/10 | Tests de hooks + integración presentes |
| Testing Frontend | 3/10 | Solo 5 archivos de test (17% cobertura) |
| Storybook | 1/10 | 0 stories para 27 componentes (0%) |
| Performance | 6/10 | N+1 remediado en 6 puntos; 4 restantes |
| Transacciones | 5/10 | CRUD commits independientes; sin atomicidad garantizada |

**Puntuación general: 6.3/10**

---

## 2. Inventario del Módulo

### 2.1 Métricas Cuantitativas

| Capa | Archivos | Líneas | Descripción |
|------|----------|--------|-------------|
| **API Endpoints** | 1 | 2,523 | `api/projects.py` — 46 endpoints REST |
| **ORM Models** | 1 | 205 | `models_projects.py` — 11 tablas |
| **Pydantic Schemas** | 1 | 399 | `schemas/projects.py` — 27 schemas |
| **CRUD Layer** | 1 | 506 | `crud/projects.py` — 33 funciones |
| **Services** | 6 | ~600 | Notificaciones, intelligence, knowledge base |
| **Frontend Components** | 27 | ~5,881 | `components/projects/` |
| **Frontend Hooks** | 3 | 462 | `hooks/useProjects.ts`, `useProjectTasks.ts`, `useProjectPageData.ts` |
| **Frontend Context** | 1 | 58 | `ProjectUpdateContext.tsx` |
| **Frontend Types** | 1 | 120 | `types/projects.ts` |
| **App Routes** | 20 | 2,814 | `app/plataforma/projects/` |
| **Tests** | 5 | 928 | 2 component + 3 hook/integration |
| **Migrations** | 15 | ~1,200 | `alembic/versions/` |
| **TOTAL** | **~83** | **~14,996** | |

### 2.2 Tablas de Base de Datos

| Tabla | Columnas | PKs | FKs | Índices | Soft Delete |
|-------|----------|-----|-----|---------|-------------|
| `projects` | 11 | UUID | 2 (sede_id, owner_id) | 5 | ✅ |
| `project_tasks` | 15 | UUID | 3 (project_id, parent_id, assignee_id) | 6 | ✅ |
| `project_phases` | 7 | UUID | 1 (project_id) | 1 | ✅ |
| `project_milestones` | 8 | UUID | 1 (project_id) | 1 | ✅ |
| `project_comments` | 9 | UUID | 3 (project_id, task_id, author_id) | 3 | ✅ |
| `project_attachments` | 9 | UUID | 2 (task_id, uploader_id) | 2 | ✅ |
| `project_activity_logs` | 6 | UUID | 2 (project_id, persona_id) | 3 | ❌ |
| `project_whiteboards` | 8 | UUID | 1 (project_id) | 2 | ✅ |
| `project_documents` | 8 | UUID | 2 (project_id, author_id) | 3 | ✅ |
| `task_supplies` | 6 | UUID | 1 (task_id) | 1 | ✅ |
| `project_inbox_state` | 5 | UUID | 1 (persona_id) | 1 | ❌ |

### 2.3 Endpoints API (46 total)

| Recurso | GET | POST | PATCH | PUT | DELETE | Total |
|---------|-----|------|-------|-----|--------|-------|
| Projects | 2 | 1 | 1 | 0 | 1 | 5 |
| Tasks | 3 | 2 | 2 | 0 | 2 | 9 |
| Subtasks | 0 | 1 | 1 | 0 | 1 | 3 |
| Supplies | 1 | 1 | 1 | 0 | 1 | 4 |
| Attachments | 0 | 1 | 0 | 0 | 1 | 2 |
| Milestones | 1 | 1 | 1 | 0 | 1 | 4 |
| Phases | 1 | 0 | 0 | 1 | 0 | 2 |
| Comments | 1 | 2 | 1 | 0 | 1 | 5 |
| Inbox | 1 | 0 | 0 | 0 | 0 | 1 |
| Whiteboards | 2 | 1 | 0 | 0 | 1 | 4 |
| Wiki | 1 | 1 | 0 | 0 | 0 | 2 |
| Messages | 1 | 1 | 0 | 0 | 1 | 3 |
| Summary/Analytics | 3 | 0 | 0 | 0 | 0 | 3 |
| **TOTAL** | **17** | **12** | **5** | **1** | **10** | **46** |

---

## 3. Backend — Hallazgos Detallados

### 3.1 Fortalezas

| Hallazgo | Detalle |
|----------|---------|
| ✅ ORM puro | Cero queries SQL raw; todo usa SQLAlchemy query builder |
| ✅ Multi-tenant estricto | Axioma 3 enforced en cada endpoint con `user_sede` scope |
| ✅ RBAC dual | Module-level + project-level (role OR assignment-based) |
| ✅ IDOR protection | Validación de pertenencia antes de mutaciones en comments, messages, inbox |
| ✅ Validación Pydantic | `Field` constraints, `BeforeValidator` normalization, `field_validator` guards |
| ✅ Row-level locking | `with_for_update()` en phase rewrite y task creation |
| ✅ Sin TODOs pendientes | Todos los markers `PEND-*` están documentados como cerrados |
| ✅ Sin imports muertos | Todos los imports están activos |

### 3.2 Transacciones — Riesgo Medio

**Problema:** Cada función CRUD llama `db.commit()` independientemente.

```
crud/create_project() → db.commit()  ← transacción 1
api/_log_project_activity() → db.add()  ← pendiente
api endpoint → db.commit()  ← transacción 2
```

**Impacto:** Si falla entre medio, queda estado parcial. Hoy funciona porque `_log_project_activity` solo hace `db.add()` sin commit, pero es frágil.

**Archivos afectados:**
- `crud/projects.py` — Líneas 52, 96, 106, 115, 144, 154, 182, 221, 231, 241, etc.

### 3.3 N+1 Queries — 4 Restantes

Ya remediado en 6 puntos (comments batch, activities batch, inbox batch, messages batch, workload aggregation). Quedan:

| Archivo:Línea | Issue |
|---------------|-------|
| `api/projects.py:2015` | `create_comment` — query separada para Persona después de commit |
| `api/projects.py:2055` | `create_project_comment` — misma issue |
| `api/projects.py:2084` | `update_project_comment` — query separada para author persona |
| `api/projects.py:676` | `_prepare_task_for_response` — recursivo en subtasks |

### 3.4 Validación — Gaps

| Archivo:Línea | Campo | Issue |
|---------------|-------|-------|
| `schemas/projects.py:24` | `TaskSupplyBase.status` | Bare `str` sin validación de enum |
| `schemas/projects.py:32` | `TaskSupplyUpdate.quantity` | Sin `ge=0` — acepta negativos |
| `schemas/projects.py:389` | `ProjectMessageCreate.content` | Sin `min_length`/`max_length` |

### 3.5 Silent Exception Swallowing

| Archivo:Línea | Issue |
|---------------|-------|
| `api/projects.py:713` | `_normalize_dates` — bare `except Exception` con solo debug log |
| `api/projects.py:2349` | `send_project_message` — catch `RuntimeError` en WebSocket broadcast sin log |

---

## 4. Base de Datos — Hallazgos Detallados

### 4.1 Stored Procedures y Triggers

| Nombre | Tipo | Propósito |
|--------|------|-----------|
| `fn_audit_trigger()` | Trigger function | Audit log en `admin_audit_logs` para projects y tasks |
| `fn_set_updated_at()` | Trigger function | Auto-update `updated_at` en todas las tablas |
| `fn_db_health_summary()` | Function | Métricas de salud de la BD |
| `refresh_dashboard_views()` | Function | Refresh materialized view `mv_projects_summary` |
| SQLite triggers (7) | Triggers | FTS search, activity logging, progress calculation |

### 4.2 Views Materializadas

| View | Propósito | Refresh |
|------|-----------|---------|
| `mv_projects_summary` | Métricas de portfolio (total, active, completed, overdue) | Manual via `refresh_dashboard_views()` |
| `view_user_workload` | Workload por usuario (open, critical, overdue) | Vista regular (auto-refresh) |

### 4.3 CHECK Constraints

| Tabla | Constraint | Valores Permitidos |
|-------|------------|-------------------|
| `project_tasks` | `chk_project_tasks_priority` | `low`, `medium`, `high`, `urgent` |
| `project_tasks` | `chk_project_tasks_status` | `todo`, `in_progress`, `review`, `completed`, `cancelled` |

**Gap:** El CHECK permite `cancelled` pero el API layer solo permite los 4 canonical statuses + phase slugs.

### 4.4 Foreign Key Map (19 relaciones)

```
sedes ←── projects.sede_id (SET NULL)
personas ←── projects.owner_id (SET NULL)
projects ←── project_tasks.project_id (CASCADE)
project_tasks ←── project_tasks.parent_id (CASCADE, self-ref)
personas ←── project_tasks.assignee_id (SET NULL)
projects ←── project_milestones.project_id (CASCADE)
projects ←── project_phases.project_id (CASCADE)
projects ←── project_comments.project_id (CASCADE)
project_tasks ←── project_comments.task_id (SET NULL)
personas ←── project_comments.author_id (SET NULL)
project_tasks ←── project_attachments.task_id (CASCADE)
personas ←── project_attachments.uploader_id (SET NULL)
projects ←── project_activity_logs.project_id (CASCADE)
personas ←── project_activity_logs.persona_id (SET NULL)
projects ←── project_whiteboards.project_id (CASCADE, UNIQUE)
projects ←── project_documents.project_id (CASCADE)
personas ←── project_documents.author_id (SET NULL)
project_tasks ←── task_supplies.task_id (CASCADE)
personas ←── project_inbox_state.persona_id (CASCADE)
```

### 4.5 Migraciones (15 archivos)

| Fecha | Archivo | Descripción |
|-------|---------|-------------|
| 2026-05-02 | `20260502_0002` | Crea `project_documents` y `project_whiteboards` |
| 2026-05-02 | `20260502_0004` | Drop `whiteboard_data` column, recrea SQLite triggers |
| 2026-05-22 | `20260522_0021` | Crea `view_user_workload` SQL VIEW |
| 2026-05-24 | `20260524_0022` | Crea materialized view `mv_projects_summary` |
| 2026-05-24 | `20260524_0023` | Audit triggers + CHECK constraints |
| 2026-05-24 | `20260524_0024` | `fn_set_updated_at()` trigger + FK indexes |
| 2026-05-24 | `20260524_0025` | Covering index `(project_id, order_index)` |
| 2026-05-24 | `20260524_0026` | Autovacuum tuning + table comments |
| 2026-05-28 | `20260528_0052` | **Redesign completo**: UUID PKs, FK to personas, FK to sedes |
| 2026-06-05 | `20260605` | Persona backfill |
| 2026-06-11 | `66557d00474b` | Fix FK constraints, add `deleted_at` to missing tables |
| 2026-06-11 | `5ff8ddf9dce0` | Drop `_compat_*` tables |
| 2026-07-01 | `20260701_0002` | Normalize labels/priority to canonical enums |
| 2026-07-10 | `20260710_0001` | Add `deleted_at` to remaining tables |
| 2026-07-17 | `20260717_0001` | Normalize project status to 5-value enum |

---

## 5. Frontend — Hallazgos Detallados

### 5.1 Componentes por Categoría

| Categoría | Componentes | Líneas Total |
|-----------|-------------|--------------|
| **Layout/Shell** | `ProjectsShell`, `ProjectViewsContent` | 221 |
| **Vistas** | `ProjectMasterView`, `ProjectListView`, `ProjectTableView`, `ProjectKanbanBoard`, `ProjectGanttView`, `ProjectCalendarView`, `TaskTableView`, `GanttView` | 2,133 |
| **Cards** | `ProjectCard`, `SortableTaskCard` | 350 |
| **Drawers** | `ProjectCreationDrawer`, `ProjectSettingsDrawer`, `TaskCreationDrawer`, `PhaseManagerDrawer` | 839 |
| **Paneles** | `TaskDetailPanel`, `TaskRouteTree` | 1,672 |
| **Colaboración** | `ProjectChatPanel`, `ProjectWhiteboard`, `ProjectWikiEditor`, `ProjectActivityFeed` | 1,246 |
| **Kanban** | `KanbanColumn`, `SortableTaskCard` | 363 |
| **Utilidades** | `TitleCellEditor`, `CommandsList`, `utils.ts` | 152 |

### 5.2 Componentes Críticos (>400 líneas)

| Componente | Líneas | Severidad | Issue |
|------------|--------|-----------|-------|
| `TaskDetailPanel.tsx` | **1,442** | 🔴 Crítico | Monolítico: details + subtasks + comments + activity + resizable panel |
| `ProjectWhiteboard.tsx` | 631 | 🟠 Alto | Fabric.js canvas + toolbar + AI drawing |
| `ProjectListView.tsx` | 579 | 🟠 Alto | Task list + comments + inline editors |
| `TaskTableView.tsx` | 453 | 🟡 Medio | AG Grid + filters + inline editors |
| `ProjectMasterView.tsx` | 409 | 🟡 Medio | Dashboard + milestones + inline editors |

### 5.3 Deuda de Tipos (`any`)

**Total: 43 usos en 9 archivos**

| Archivo | Usos | Contexto |
|---------|------|----------|
| `ProjectWikiEditor.tsx` | 15 | TipTap slash-command callbacks |
| `TaskTableView.tsx` | 11 | AG Grid row data y cell params |
| `TaskDetailPanel.tsx` | 6 | API response mapping |
| `GanttView.tsx` | 5 | Date-fns calculations |
| `wiki/CommandsList.tsx` | 3 | TipTap command types |
| `ProjectMasterView.tsx` | 1 | AnalyticCard |
| `PhaseManagerDrawer.tsx` | 1 | Phase data |
| `ProjectChatPanel.tsx` | 1 | WebSocket message |

### 5.4 Colores Hardcodeados

**Total: 31 ocurrencias en 14 archivos**

| Categoría | Archivos | Valores |
|-----------|----------|---------|
| **AG Grid theme** | `ProjectTableView.tsx`, `TaskTableView.tsx` | `#ffffff`, `#1e293b`, `#e2e8f0`, `#6366f1` |
| **Dark-mode backgrounds** | `ProjectChatPanel`, `KanbanColumn`, `ProjectListView`, `ProjectKanbanBoard`, `ProjectActivityFeed`, `GanttView`, `TaskDetailPanel` | `#1e1f21`, `#1a1b1d`, `#25262b`, `#252528` |
| **Color palettes** | `ProjectCreationDrawer`, `PhaseManagerDrawer` | `#2563eb`, `#0891b2`, `#16a34a`, `#f59e0b`, `#ef4444` |
| **CSS styles** | `ProjectWikiEditor.tsx` | `#94a3b8`, `#e2e8f0` |

### 5.5 Duplicación de Configuraciones

**STATUS_OPTIONS definido 3+ veces:**

| Archivo | Línea | Valores |
|---------|-------|---------|
| `ProjectListView.tsx` | 22-27 | `todo`, `in_progress`, `review`, `completed` con colores |
| `TaskTableView.tsx` | 35-40 | Mismos valores, ligeramente diferentes colores |
| `TaskDetailPanel.tsx` | 95-99 | `STATUS_MAP` con mismos valores |

**PRIORITY_OPTIONS definido 2+ veces:**

| Archivo | Línea | Valores |
|---------|-------|---------|
| `TaskTableView.tsx` | 43-48 | `low`, `medium`, `high`, `urgent` |
| `TaskDetailPanel.tsx` | (inline) | Mismos valores |

### 5.6 Storybook — 0% Cobertura

**Ningún componente de proyectos tiene stories.** Los 27 componentes no están documentados visualmente.

### 5.7 Testing — 17% Cobertura

| Tipo | Archivos | Cubre |
|------|----------|-------|
| Component tests | 2 | `ProjectTableView`, `TaskTableView` |
| Hook tests | 2 | `useProjectTasks`, `useProjectPageData` |
| Integration tests | 1 | Cross-view mutation consistency |
| **Sin tests** | 25 | Todos los drawers, panels, collaboration, views |

---

## 6. Rutas y Navegación

### 6.1 Mapa de Rutas (20 páginas)

```
/plataforma/projects/                    ← Layout raíz (server-side)
├── page.tsx                             ← Lista de proyectos (grid/table/list/board/kanban/calendar/gantt/wiki)
├── [id]/page.tsx                        ← Detalle de proyecto (dashboard/table/list/board/kanban/calendar/gantt/wiki/chat)
├── tasks/page.tsx                       ← Tareas globales (scope: mine/all)
├── inbox/page.tsx                       ← Bandeja de mensajes
├── general/page.tsx                     ← Canal general
├── comments/page.tsx                    ← Comentarios asignados
├── team/page.tsx                        ← Equipo / workload
├── responses/page.tsx                   ← Respuestas
├── more/page.tsx                        ← Portfolio summary
├── automations/page.tsx                 ← Automatizaciones
├── welcome/page.tsx                     ← Onboarding
├── loading.tsx                          ← Loading skeleton
└── error.tsx                            ← Error boundary

/plataforma/dashboard/projects/          ← Dashboard separado
└── page.tsx                             ← Dashboard de proyectos
```

### 6.2 Jerarquía de Layout

```
RootLayout
  └── ProjectsLayout (SERVER — fetch project list)
        └── ProjectsLayoutClient (dynamic sidebar)
              └── WorkspaceLayout
                    ├── WorkspaceMiniSidebar (S1)
                    ├── WorkspaceMainSidebar (S2 — dynamic)
                    ├── WorkspaceToolbar
                    └── {children}
                          └── ProjectsShell (breadcrumb + toolbar)
```

### 6.3 Guard de Autenticación

- **Middleware:** Redirect `/projects/**` → `/plataforma/projects/**`
- **ProtectedRoute:** `allowedPermissions=['projects:read']`
- **Cookie check:** `mesh_access` cookie en server-side

---

## 7. Recomendaciones Priorizadas

### 🔴 Alta Prioridad / Bajo Esfuerzo

| # | Acción | Capa | Beneficio |
|---|--------|------|-----------|
| 1 | **Extraer `STATUS_OPTIONS` y `PRIORITY_OPTIONS`** a `lib/projects/constants.ts` | Frontend | Eliminar 3+ definiciones duplicadas |
| 2 | **Eliminar `import React` innecesario** en 13 archivos | Frontend | Limpiar dead code |
| 3 | **Agregar `min_length`/`max_length`** a `ProjectMessageCreate.content` | Backend | Prevenir mensajes vacíos |
| 4 | **Agregar `ge=0`** a `TaskSupplyUpdate.quantity` | Backend | Prevenir cantidades negativas |
| 5 | **Eliminar query redundante** en `create_project_task` (line 925) | Backend | Optimizar performance |

### 🟠 Alta Prioridad / Medio Esfuerzo

| # | Acción | Capa | Beneficio |
|---|--------|------|-----------|
| 6 | **Descomponer `TaskDetailPanel.tsx`** (1,442 líneas) en sub-componentes | Frontend | Mantenibilidad |
| 7 | **Reemplazar 43 `any` types** con interfaces tipadas | Frontend | Type safety |
| 8 | **Consolidar colores dark-mode** a CSS variables | Frontend | Consistencia |
| 9 | **Remediar 4 N+1 restantes** en comment endpoints | Backend | Performance |
| 10 | **Unificar transacciones** — mover `db.commit()` fuera de CRUD | Backend | Atomicidad |

### 🟡 Media Prioridad / Alto Esfuerzo

| # | Acción | Capa | Beneficio |
|---|--------|------|-----------|
| 11 | **Crear shared AG Grid theme** con tokens del design system | Frontend | Consistencia visual |
| 12 | **Agregar tests** para drawers, panels, collaboration components | Frontend | Cobertura (17% → 60%) |
| 13 | **Crear stories** para 27 componentes de proyectos | Frontend | Documentación visual |
| 14 | **Tipar `TaskSupply.status`** como Literal enum en schema | Backend | Validación estricta |

### 🟢 Baja Prioridad / Impacto Largo Plazo

| # | Acción | Capa | Beneficio |
|---|--------|------|-----------|
| 15 | **Migrar `GanttView.tsx` legacy** a `UniversalGanttView` | Frontend | Eliminar duplicación |
| 16 | **Refactorizar `_normalize_dates`** sin bare `except Exception` | Backend | Robustez |
| 17 | **Agregar logging** a WebSocket broadcast failure | Backend | Observabilidad |

---

## 8. Métricas Cuantitativas

| Métrica | Valor |
|---------|-------|
| Total endpoints API | 46 |
| Total tablas BD | 11 |
| Total columnas BD | 87 |
| Total foreign keys | 19 |
| Total índices | 25 |
| Total migraciones | 15 |
| Total stored procedures/triggers | 9 |
| Total componentes frontend | 27 |
| Total hooks | 3 |
| Total rutas | 20 |
| Total líneas de código | ~14,996 |
| `any` types en frontend | 43 |
| Colores hardcodeados | 31 |
| Inline styles | 24 |
| Tests existentes | 5 archivos (928 líneas) |
| Stories existentes | 0 |
| Cobertura testing | 17% |
| Cobertura Storybook | 0% |
| Endpoints con auth | 46/46 (100%) |
| N+1 remediados | 6/10 (60%) |
| Tablas con soft-delete | 9/11 (82%) |

---

## 9. Conclusión

El módulo de Proyectos tiene una **base backend sólida** con seguridad robusta (RBAC dual + Axioma 3), ORM limpio, y validación Pydantic completa. Los 46 endpoints cubren CRUD completo para 11 entidades con multi-tenant estricto.

Los principales riesgos a atender son:

1. **Frontend monolítico**: `TaskDetailPanel.tsx` (1,442 líneas) necesita descomposición
2. **Deuda de tipos**: 43 usos de `any` en componentes críticos
3. **Testing gap**: Solo 17% de cobertura en frontend
4. **Transacciones**: CRUD commits independientes sin atomicidad garantizada
5. **Duplicación**: Configuraciones de status/priority definidas 3+ veces

Atacar las recomendaciones de alta prioridad consolidará el módulo, reducirá deuda técnica y mejorará la mantenibilidad a largo plazo.

---

*Documento generado el 2026-07-23 a partir de auditoría full-stack del módulo de Proyectos CCF.*
