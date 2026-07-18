# Estado del Módulo de Proyectos — CCF

> **TL;DR (una linea):** Backend de Projects solido (11 modelos, router `/api/projects`, 23 componentes frontend, hook + contexto compartidos) y backlog original del modulo cerrado el `2026-07-16`.

**Propósito.** Handover canónico. Este archivo existe para que cada sesión nueva de trabajo pueda leerlo al inicio y arrancar con el contexto ya cargado, sin redescubrir el módulo de cero.

> **Cambios recientes (post handover 2026-07-15):**
> - `PARCIAL-LISTVIEW-001` cerrada el 2026-07-16. Hook + tests verdes.
> - `PARCIAL-MASTERVIEW-001` cerrada el 2026-07-16. MasterView self-sufficient + page.tsx cleanup. Hook + tests verdes.
> - `PARCIAL-PHASES-001` cerrada el 2026-07-16. PhaseManagerDrawer self-sufficient vía context + validacion reforzada + pre-flight orphan tasks. Hook + tests verdes.
> - `PARCIAL-PAGE-001` cerrada el 2026-07-16. Hook `useProjectPageData` + componente `ProjectViewsContent` extraídos; page.tsx 663→264 LOC.
> - `PEND-STATUS-NORM-001` cerrada el 2026-07-16. Backend ProjectStatus Literal + `BeforeValidator` legacy mapper; Alembic migration `20260717_0001` staged; Frontend `PROJECT_STATUSES` + `ProjectStatus` centralizado en constants.ts; `ProjectRecord.status` narrowed. Hook + tests verdes.
> - `PEND-RBAC-001` cerrada el 2026-07-16. Suite `tests/test_projects_rbac.py` (116 tests verdes) parametriza 4 roles canónicas (Administrador / Gestor / Editor / Miembro) sobre 14 endpoints de lectura + 16 endpoints de mutación en `/api/projects/*`. Baseline Miembro=403 en endpoints sin `project_id`/`task_id`; 404 en endpoints con `project_id`/`task_id` inexistente/out-of-scope (Axioma 3 / existence-leak safe); jerarquía `manage → edit → read` verificada; asimetría descubierta: `DELETE /projects/{id}` usa `require_staff_or_admin` (`academy:manage`) mientras que `PATCH /projects/{id}` usa `projects:edit` — Editor bloqueado en DELETE pero pasa PATCH; gap documentado: `PUT /phases` usa `projects:edit` (no `projects:manage`), Editor pasa por decoración actual divergente del docstring.
> - `PEND-VIEWS-E2E-001` cerrada el 2026-07-16. Suite `frontend/src/lib/__tests__/projects-views-integration.test.tsx` (8 tests verdes) valida el invariante arquitectónico "todas las vistas comparten `ProjectUpdateProvider`" con `MiniList` como vista-representante + `Harness` que mantiene el estado en `useState` y provee mutators in-memory. `ProjectKanbanBoard` mockeado como no-op (sus deps transitivas — dnd-kit + ag-grid + framer-motion + ConfirmActionDrawer con React legacy — tienen historial de cascading failures en jsdom). Smoke real del Kanban sigue cubierto por navegador manual. Cubre: throw fuera del Provider, render inicial en múltiples consumers, createTask/updateTask/deleteTask propaga a N consumidores, jerarquía `mutaciones concurrentes convergen`, y smoke de MiniList como vista-genérica consumidora.
> - `PEND-INBOX-CONTRACT-001` cerrada el 2026-07-16. Contrato documentado en §4.1 del handover. `GET /api/projects/inbox` agrega 2 superficies (comentarios no resueltos + tareas abiertas asignadas) en un solo feed con cap a `limit=50`, returntype `List[ProjectInboxItem]`. `POST /api/projects/inbox/{item_id}/read` upserta la marca de leído en `project_inbox_state` (UNIQUE `(persona_id, item_id)`). RBAC: `/inbox` requiere `projects:read` (admin/gestor/editor pasan; miembro 403); `/inbox/{id}/read` requiere `projects:edit`. Axioma 3: el feed se acota a `sede_id` del actor; superadmin ve todo.
> - Docstring de `list_inbox` sincronizado con §4.1 (2026-07-16). El docstring en `backend/api/projects.py::list_inbox` se reescribió para reflejar el contrato del handover como single source of truth (elimina drift futuro entre código y doc). Pytest `tests/test_projects_api.py::TestInbox` sigue verde (cambio puramente documental, sin mutar comportamiento).
> - **Actualizacion QA 2026-07-16:** `npm run test:e2e:projects:detail` ya no depende de arrancar Next manualmente. Usa `frontend/scripts/run-managed-playwright.mjs` para levantar `webServer` administrado y ejecutar la suite seeded del detalle de proyectos de forma repetible.

**Regla de uso.**

- Actualizar este doc al cerrar tareas, no antes.
- Las categorías `Hecho / Parcial / Pendiente` se interpretan igual que en `PLAN_PROYECTOS_CALIDAD.md`:
  - `Hecho` = capacidad principal ya implementada y usable.
  - `Parcial` = funciona, pero con huecos visibles o deuda de integración.
  - `Pendiente` = no resuelto o solo como mejora futura.
- No usar este doc como wishlist; solo reflejar lo que el código dice hoy.

---

## 1. TL;DR — Mapa del módulo

| Capa | Ubicación | Tamaño |
|---|---|---|
| Modelos | `backend/models_projects.py` | 11 clases: `Project`, `ProjectMilestone`, `ProjectActivityLog`, `ProjectWhiteboard`, `ProjectTask`, `ProjectAttachment`, `TaskSupply`, `ProjectComment`, `ProjectPhase`, `ProjectInboxState`, `ProjectDocument` |
| API Router | `backend/api/projects.py` | 2 160 LOC, montado en `/api/projects` |
| Tests de calidad | `scripts/test_projects_quality.py` | Crea data de prueba, valida API y permisos |
| Colección Postman | `docs/projects_api_postman_collection.json` | Listo para QA funcional |
| Componentes frontend | `frontend/src/components/projects/` | 23 componentes, 6 219 LOC en total. Recontar con `cd /root/ccf/frontend && wc -l src/components/projects/*.tsx \| tail -1` si cambia. |
| Hook compartido | `frontend/src/hooks/useProjectTasks.ts` | CRUD + rollback |
| Contexto compartido | `frontend/src/context/ProjectUpdateContext.tsx` | Estado project/tasks/phases/activities |
| Plan de calidad | `docs/PLAN_PROYECTOS_CALIDAD.md` | Plan operativo canónico del módulo dentro de la arquitectura modular |
| Acta histórica | `docs/PLAN_VISTAS_EDITABLES_PROYECTOS.md` | Cierre del frente histórico de vistas editables |

**Estado global:** La base del modulo quedo cerrada (backend solido, hook + contexto compartidos, drawers y vistas de escritura rapida funcionando). El backlog original de `Parcial` + `Pendiente` quedo resuelto el `2026-07-16`; cualquier trabajo nuevo debe abrirse con IDs nuevos.

> Tamaños y nombres verificados el **2026-07-16**. Re-verificar si se retoma tras >30 días porque el frontend de proyectos cambia rápido.

---

> **2026-07-16 — Cierre de `PARCIAL-LISTVIEW-001`:** El callback `handleChangeTask` ahora aplica mutex estricto: cuando `projectId` está set, **única ruta** es `useProjectTasks.updateTask({ optimistic: true })` (ya cubre optimistic + rollback; tests en `useProjectTasks.test.tsx`). El path legacy (`onTasksChange`/`onTaskUpdate`) sigue intacto para consumidores sin `projectId`. Se agrega `useEffect` de sync `hookTasks → onTasksChange` cuando `projectId` está set, para mantener en sincronía a las vistas hermanas (Kanban/Calendar/Dashboard) que leen `tasks` desde el padre. `Props` ahora lleva JSDoc explicando cuándo disparan los callbacks legacy. Verificaciones: typecheck OK, vitest 6/6 OK (`useProjectTasks.test.tsx`), smoke test 48/48 OK.

> **2026-07-16 — Cierre de `PARCIAL-MASTERVIEW-001`:** `ProjectMasterView` reescrito para ser self-sufficient. Consume `useProjectUpdate()` (updateProject, updateTask, reloadProject) y hace sus propias llamadas a `/projects/{id}/milestones[/...]`. Ahora soporta edición inline completa de hitos (PATCH/POST/DELETE + `InlineDatePicker` para `target_date`), creación inline desde una card dashed, y edición inline de tareas dentro de `NodeCard` (status toggle + rename preservando el prefijo `[...]`). `page.tsx` perdió 7 state variables y 5 handlers de hitos + la card aside del dashboard (que ahora vive dentro de MasterView). Verificaciones: typecheck OK, vitest 6/6 OK (`useProjectTasks.test.tsx`), smoke test 48/48 OK.

> **2026-07-16 — Cierre de `PARCIAL-PHASES-001`:** `PhaseManagerDrawer` reescrito self-sufficient. Consume `phases`/`tasks`/`reloadProject` directamente del `ProjectUpdateContext`. La API surface colapsa a `{projectId, onClose}` — se removieron las props `phases` y `onSaved`. Validación reforzada con `validateItems()`: ≥1 fase, name no vacío, slug único case-insensitive. **Pre-flight de tasks huérfanas**: bloquea el save si alguna tarea existente quedaría con `status` fuera del nuevo set de slugs (mitiga el rechazo del backend `_assert_status_in_project_phases` en PATCH posteriores). Slug visible read-only en UI para debugging. `page.tsx` simplificó el call site. Verificaciones: typecheck OK, vitest 6/6 OK (`useProjectTasks.test.tsx`), smoke test 48/48 OK.

---

## 2. Convenciones del módulo

- **Versiones mínimas del entorno:**
  - **Python ≥ 3.11** — inferido por uso de `dict[str, ...]` y `str | None` en `backend/`. El proyecto no declara `requires-python` en `pyproject.toml`. Verificado en este host: **3.12.3**.
  - **Node ≥ 20 LTS** — inferido por Next.js ≥ 14. El proyecto no declara `engines.node` en `frontend/package.json` ni `.nvmrc`. Verificado en este host: **v24.15.0**.
  - Verificar al retomar con `python3 --version && node --version`. Si tu host no cumple, ajustar antes de continuar.
- **Soft delete** universal vía `deleted_at` en todos los modelos del dominio.
- **`sede_id` FK** presente donde aplica para aislar datos por sede (revisar en cada nuevo modelo del dominio).
- **`Project.name` ↔ `Project.title`**: `name` es `@property` que delega a `title` para no romper consumidores legacy (`tests/test_crud_integration.py::TestProjectsCrud`). Mantener `title` como única fuente de verdad en código nuevo.
- **Estados de proyecto** (string libre hoy, normalización pendiente): `"planning" | "active" | …`.
- **Estados de tarea** (string libre hoy, normalización pendiente): `"todo" | "in_progress" | "review" | "completed"`.
- **Campos JSON**: `ProjectTask.labels` (`JSON`, default `[]`). `ProjectWhiteboard.elements_json` (`TEXT`, default `"[]"`).
- **Fechas**: siempre `DateTime(timezone=True)` y siempre con `_utcnow()` (`backend/models_shared.py`).
- **`ProjectDocument` vs `ProjectWhiteboard`** — NO son lo mismo.
  - `ProjectDocument` (`project_documents`) → **wiki** del proyecto (`content: Text`, editada por `ProjectWikiEditor`).
  - `ProjectWhiteboard` (`project_whiteboards`) → **pizarra visual** (`elements_json: Text`, editada por `ProjectWhiteboard.tsx`).
  No confundir al inspeccionar el modelo o el router.
- **Auth v3**: el login es vía `/api/v3/auth/login`. Los endpoints legacy `/api/auth/...` no se usan en scripts nuevos.
- **Punto de entrada UI**: `/plataforma/projects` (lista) y `/plataforma/projects/[id]` (detalle con orquestación de vistas).

---

## 3. Backend — Modelo de datos

```
Project ─┬─ tasks (ProjectTask, jerárquica vía parent_id)
         ├─ milestones (ProjectMilestone)
         ├─ activity_logs (ProjectActivityLog)
         ├─ phases (ProjectPhase)
         ├─ whiteboard (ProjectWhiteboard, 1:1)            ← pizarra visual
         ├─ documents (ProjectDocument, 1:N)               ← wiki del proyecto
         └─ comments (ProjectComment, opcionalmente atado a task_id)

ProjectTask ─┬─ subtasks (auto-FK parent_id)
             ├─ supplies (TaskSupply)
             └─ attachments (ProjectAttachment)

ProjectComment (project_id, opcional task_id, author_id)
ProjectInboxState (persona_id, item_id) — lectura por usuario
```

**Tablas principales (11, todas con `deleted_at` + `created_at` + `updated_at`):**

`projects`, `project_tasks`, `project_phases`, `project_milestones`, `project_comments`, `project_documents` (wiki), `project_whiteboards` (pizarra), `project_activity_logs`, `project_attachments`, `task_supplies`, `project_inbox_state` (per-user).

**FK claves:**

- `Project.owner_id` → `personas.id` (no `auth_users.id` — el owner es la persona ministerial).
- `ProjectTask.assignee_id` → `personas.id`.
- `User` vive en `auth_users` y comparte PK con `personas.id` (ver `models_auth.py`).

---

## 4. Backend — API surface (resumen)

Rutas montadas en `/api/projects` (ver `backend/api/projects.py` para contratos exactos):

- `POST /` — crear proyecto
- `GET /` — listar (`?limit=`, filtros)
- `GET /{id}` — detalle (incluye `tasks`, `phases`, `milestones`)
- `PATCH /{id}` — actualizar (status, title, owner, color, etc.)
- `DELETE /{id}` — soft delete
- `GET /{id}/tasks` — tareas del proyecto
- `POST /{id}/tasks` — crear tarea
- `GET /{id}/milestones` — listar hitos
- `GET /{id}/wiki` — leer `ProjectDocument`
- `POST /{id}/comments` — crear comentario (global o atado a `task_id`)
- `GET /comments?project_id={id}` — listar comentarios
- `GET /tasks`, `GET /tasks/{id}`, `PATCH /tasks/{id}`, `DELETE /tasks/{id}` — CRUD global de tareas
- `POST /tasks/{task_id}/supplies`, list / patch / delete — supplies por tarea
- `GET /inbox?limit=20`, `GET /activities?limit=20` — feeds
- `GET /summary`, `GET /workload` — métricas portfolio

> **Gaps abiertos en backend (documentados, no pertenecen ya al backlog original):**
> - Asimetria RBAC en `DELETE /projects/{id}` vs `PATCH /projects/{id}` (política confirmada).
> - Necesidad futura de una matriz RBAC mas compacta separada del handover.

> **Referencia útil:** el patrón `CasoCRM.atomic_sort_reorder` en `backend/models_crm_pipeline.py` ya implementa sede-isolation + lock+rollback para batch reorders. Reusarlo si se necesita un endpoint `PATCH /api/projects/tasks/reorder` para el future del Kanban.

### 4.1. Contrato de `GET /api/projects/inbox` (cierre PEND-INBOX-CONTRACT-001)

El inbox es un **feed unificado por persona** que combina dos superficies del módulo Projects en una sola respuesta. Documenta el comportamiento actual implementado en `backend/api/projects.py::list_inbox` + `mark_inbox_read`.

**Endpoint**: `GET /api/projects/inbox?limit=N` (default 50, máx 200).

**Response shape**: `List[ProjectInboxItem]` (Pydantic, `backend/schemas/projects.py`):

| Campo | Tipo | Comentario |
|---|---|---|
| `id` | `str` | Composite `"comment-<comment.id>"` o `"task-<task.id>"` — ÚTIL como `item_id` en `POST /inbox/{item_id}/read`. |
| `type` | `str` | Literal `"comment"` o `"task_assigned"`. |
| `user` | `str` | Nombre del autor (comments) o del project.owner (tasks). Fallback `"Usuario"`/`"Equipo"`. |
| `content` | `str` | Comments: primeros **120 chars** del contenido. Tasks: literal `"Tarea asignada: {task.title}"`. |
| `project` | `str` | `Project.title` del proyecto asociado. |
| `project_id` | `str` (uuid) | FK al proyecto. |
| `task_id` | `Optional[str]` (uuid) | Sólo en comments attached a task, o en items `task_assigned`. |
| `task_title` | `Optional[str]` | Sólo en items `task_assigned`. |
| `is_read` | `bool` | Resuelto vía tabla `project_inbox_state` (default `false`). Por persona. |
| `created_at` | `datetime` | Comments: `comment.created_at`. Tasks: `task.updated_at`. |

**Las dos superficies**:

1. **Comentarios no resueltos** (`type="comment"`, `~is_resolved` + excluye auto-comentarios por `author_id != persona_id`). Orden: `created_at desc`, top-N.
2. **Tareas abiertas asignadas al actor** (`type="task_assigned"`, `assignee_id == persona_id` + `status != "completed"` + no soft-deletada). Orden: `updated_at desc`, top-N.

Ambas corren independientemente con cap `limit` cada una; el resultado se trunca a `limit` items totales al final.

**Marca de leído**: `POST /api/projects/inbox/{item_id}/read` upserta `ProjectInboxState` (UNIQUE constraint `uq_persona_project_item` sobre `(persona_id, item_id)`). Race-condition fix: replace check-then-act con try/except IntegrityError → update path. Responde `{ok: true, item_id: <item_id>}`.

**RBAC** (validado por `tests/test_projects_rbac.py`):

- `GET /inbox` requiere `projects:read` (decorador). Admin/gestor/editor pasan; Miembro = **403** (baseline PEND-RBAC-001 documentado).
- `POST /inbox/{id}/read` requiere `projects:edit`. Admin/gestor/editor pasan; Miembro = **403**.

**Axioma 3 (multi-tenant)**:

- Sedes sentadas: sólo ven items de proyectos cuya `Project.sede_id == user_sede`. Cross-sede unread comments + out-of-sede assigned tasks filtrados server-side.
- Superadmin (`user_sede = None`): ve todo, consistente con `list_projects`/`list_whiteboards`/`list_activities`.
- Proyectos soft-deleted se excluyen del join.
- Tareas con `status="completed"` (terminal) se excluyen de la superficie `task_assigned`.
- Comments resueltos (`is_resolved=True`) se excluyen de la superficie `comment`.

**Performance characteristics**:

- N+1 fix (Sprint 1.1): un único `IN (...)` batch por superficie para resolver `author_name` / `project_title` + un batch `IN (...)` para resolver los `is_read` desde `project_inbox_state`. Sin queries dentro del loop de serialización.
- `selectinload(Project.owner)` evita N+1 al resolver `user` en items `task_assigned`.

**Diferencias explícitas con `GET /api/projects/activities`**:

- `activities` es bitácora cruda universal por proyecto (generalmente útil para auditoría); `inbox` es feed normalizado por persona con estado de lectura.
- `activities` no requiere consentimiento a items por persona; `inbox` requiere autenticación y filtra por `persona_id` derivada del JWT.

**Cross-reference**: tests de RBAC específicos para inbox en `tests/test_projects_rbac.py::TestMiembroBaseline::test_miembro_read_returns_403` parametrizados sobre `/api/projects/inbox` (read) y `TestMiembroBaseline::test_miembro_write_returns_403` sobre `/api/projects/inbox/{uuid}/read` (marca de leído).

---

## 5. Frontend — Mapa de componentes

`frontend/src/components/projects/` (23 archivos `.tsx` + dir `wiki/`).

### Vistas (dentro de `frontend/src/components/projects/`)

| Archivo | LOC | Estado |
|---|---:|---|
| `ProjectsShell.tsx` | medio | Hecho — orquestador shell |
| `ProjectListView.tsx` | 560 | Hecho |
| `ProjectCard.tsx` | varios | Hecho (grid + tabla con inline edit + alta/baja) |
| `ProjectTableView.tsx` | medio | Hecho |
| `ProjectMasterView.tsx` | medio | Hecho |
| `TaskTableView.tsx` | 455 | Hecho — editable, agrupable, abre detalle por doble click |
| `ProjectKanbanBoard.tsx` + `KanbanColumn.tsx` + `SortableTaskCard.tsx` | — | Hecho — drag&drop persistente, inline edit de título/fecha/prioridad/asignado |
| `ProjectGanttView.tsx` | medio | Hecho — click/drag/resize conectado a fechas |
| `ProjectCalendarView.tsx` | medio | Hecho — click crea con `due_date` prellenada, drag reubica |
| `ProjectWhiteboard.tsx` | 631 | Hecho |

> **Importante: las vistas universales NO están en este directorio.**
> - `UniversalGanttView.tsx` y `UniversalCalendarView.tsx` viven en `frontend/src/components/ui/` y son reusables (también fuera de proyectos).
> - `ProjectsClient.tsx` (la page de Next.js que monta `ProjectsShell` + tabla) vive en `frontend/src/app/plataforma/projects/ProjectsClient.tsx`, NO en `components/projects/`. Buscarlo allí cuando se modifique routing o layout.

### Drawers / paneles

- `ProjectCreationDrawer.tsx`, `ProjectSettingsDrawer.tsx` — drawers de proyecto (Hecho)
- `PhaseManagerDrawer.tsx` — Hecho
- `TaskCreationDrawer.tsx`, `TaskDetailPanel.tsx` (1 442 LOC) — Hecho
- `ProjectWikiEditor.tsx`, `ProjectChatPanel.tsx`, `ProjectActivityFeed.tsx` — Hecho
- `TaskRouteTree.tsx`, `TitleCellEditor.tsx` — auxiliares
- `GanttView.tsx` (legacy) — revisar si sigue en uso o se puede eliminar. Cómo decidirlo: `grep -rn "from .*components/projects/GanttView" /root/ccf/frontend/src 2>/dev/null` y `grep -rn "GanttView" /root/ccf/frontend/src/app /root/ccf/frontend/src/pages 2>/dev/null`. Si no hay imports, es seguro borrar.
- `utils.ts` (no es `.tsx`) — helpers locales del directorio

### Página Next.js que monta todo

- `frontend/src/app/plataforma/projects/ProjectsClient.tsx` — orquestación cliente del listado.
- `frontend/src/app/plataforma/projects/[id]/page.tsx` — detalle por proyecto; orquestacion simplificada y apoyada por `useProjectPageData` + `ProjectViewsContent`.

### Compartido externo al directorio

- `frontend/src/hooks/useProjectTasks.ts` — CRUD compartido con rollback
- `frontend/src/context/ProjectUpdateContext.tsx` — estado project/tasks/phases/activities
- `frontend/src/components/ui/` — `UniversalGanttView.tsx`, `UniversalCalendarView.tsx`, `inline-editors/` (editores reutilizables: status, prioridad, fecha, persona, texto)
- `frontend/src/lib/__tests__/useProjectTasks.test.tsx` — cobertura del hook

---

## 6. Estado del módulo (consolidado)

### Hecho (no tocar sin motivo)

- Backend models + router + soft delete + sede isolation.
- Hook `useProjectTasks` con tests.
- Contexto compartido.
- Editores inline reutilizables.
- Drag&drop + resize + creación rápida en Gantt, Kanban, Calendar, Table.
- Paneles paralelos (Wiki, Chat, ActivityFeed, Whiteboard) operativos.
- Script de calidad + Postman collection.

### Parcial

- No quedan items activos del backlog original marcados como `Parcial`.
- Mantener la seccion por compatibilidad de lectura; nuevos parciales deben abrirse con IDs nuevos.

### Pendiente

- No quedan items activos del backlog original marcados como `Pendiente`.
- Las deudas actuales son transversales o decisiones conscientes de RBAC, no trabajo abierto del plan inicial.

### Backlog nuevo post-cierre

- **Todos los 4 items del backlog nuevo post-cierre fueron cerrados el `2026-07-16` (ver §10).**
  La matriz viva ya no tiene IDs activos en este bloque. El plan integral
  del modulo de proyectos queda cerrado sin pendientes abiertos.
- **`GAP-CROSS-SEDE-404-001` cerrado 2026-07-17** — se corrigió `require_project_access` en `backend/api/projects.py` para validar la sede del proyecto/task antes de devolver 403, devolviendo 404 para recursos de otra sede (Axioma 3 / existence-leak safe). Los 7 tests de `TestCrossSedeSecurity` pasan. Se actualizaron `tests/test_projects_rbac.py` y `docs/PROJECTS_RBAC_MATRIX.md` para reflejar el nuevo baseline de `Miembro` (403/404 según el endpoint). Ver `docs/PLAN_PROYECTOS_CALIDAD.md` §8.2 T8.

---

## 7. Cómo arrancar / cómo probar

### Smoke rápido (datos + asserts)

```bash
cd /root/ccf
./venv/bin/python scripts/test_projects_quality.py
```

Crea 3 usuarios de prueba (`prueba1/2/3@ccf.test` / `prueba123`), un proyecto "Creatividad" con 5 tareas, 4 fases kanban, 3 hitos, 1 wiki y 6 comentarios. Verifica 8 secciones con asserts `✓`/`✗`. Termina con `RESUMEN: N passed, M failed`. Si backend está caído, falla en la sección 9 (API).

### QA funcional con Postman

Abrir `ccf/docs/projects_api_postman_collection.json` en Postman. Variables: `base_url`, `token`, `project_id`, `task_id`, `supply_id`.

### Tests unitarios del hook

```bash
cd /root/ccf/frontend
# Usar el script del runner del frontend; ver package.json (jest/vitest)
```

### Typecheck frontend (área projects)

```bash
cd /root/ccf/frontend
# No hay barrel index.ts en components/projects/, así que el chequeo
# correcto es a nivel del proyecto, filtrando después por los archivos
# del módulo:
npx tsc --noEmit -p tsconfig.json 2>&1 | grep -E '^ccf/frontend/src/(components/projects|hooks/useProjectTasks|context/ProjectUpdateContext|app/plataforma/projects)' | head -80
```

### Credenciales de prueba

- `admin@ccf.com` (rol ADMIN)
- `prueba1@ccf.test` / `prueba123` (MIEMBRO — sin acceso a projects hoy)
- `prueba2@ccf.test` / `prueba123` (EDITOR — acceso a projects)
- `prueba3@ccf.test` / `prueba123` (GESTOR — acceso a projects)

---

## 8. Próximos pasos recomendados (orden operativo)

1. ~~Cerrar las 4 piezas marcadas `Parcial` en §6...~~ Todas (`LISTVIEW-001`, `MASTERVIEW-001`, `PHASES-001`, `PAGE-001`) cerradas el 2026-07-16.
2. ~~Normalizar `status` (proyecto/tarea) con un `Enum` o tabla catálogo y propagar al router + frontend.~~ ✅ Cerrada 2026-07-16.
3. ~~Validar permisos granulares por rol sobre `/api/projects/*` con una suite RBAC paramétrica.~~ ✅ Cerrada 2026-07-16 (`tests/test_projects_rbac.py`, 116 tests verdes).
4. ~~Cerrar pruebas de integración entre vistas (ProjectKanbanBoard ↔ TaskTableView ↔ CalendarView ↔ GanttView) verificando que mutaciones se propagan vía `ProjectUpdateProvider` sin recarga.~~ ✅ Cerrada 2026-07-16 (`frontend/src/lib/__tests__/projects-views-integration.test.tsx`, 8 tests verdes).
5. ~~Documentar el contrato de `GET /api/projects/inbox` (alcance, roles, formato de items).~~ ✅ Cerrada 2026-07-16 (sub-sección §4.1 más abajo: `ProjectInboxItem` schema, RBAC por nivel, Axioma 3, upsert semantics de `POST /inbox/{id}/read`).
6. Nuevo backlog post-cierre:
   - ~~`PEND-QUALITY-TASK-CREATE-001`: bloquear tareas con `title=''` creadas desde la vista `list`.~~ ✅ Cerrado 2026-07-16.
   - ~~`PEND-QUALITY-PHASE-SYNC-001`: resetear `phases` correctamente cuando el API devuelve `[]`.~~ ✅ Cerrado 2026-07-16.
   - ~~`PEND-QUALITY-INBOX-SCOPE-001`: excluir comentarios/proyectos soft-deleted y validar `item_id` real antes de marcar `read`.~~ ✅ Cerrado 2026-07-16.
   - ~~`PEND-QUALITY-RBAC-ASYMMETRY-001`: alinear o formalizar la politica de borrado de proyectos.~~ ✅ Cerrado 2026-07-16 como **política confirmada**.
   - `BASELINE-MIEMBRO-001`: política de acceso del rol `Miembro` en Projects. ✅ Cerrado 2026-07-16 como **política confirmada**: `Miembro` no tiene acceso al módulo; recibe 403 en endpoints sin `project_id`/`task_id` y 404 en endpoints con `project_id`/`task_id` inexistente/out-of-scope (Axioma 3 / existence-leak safe). El rol no existe en el contexto del módulo. La asignación de tareas/proyectos es delegación interna para usuarios con acceso al módulo, no vía de acceso para `Miembro`. Docs: `PROJECTS_RBAC_MATRIX.md` §5 y §10.3; `PLAN_PROYECTOS_CALIDAD.md` §8.8; `PROJECTS_QA_CHECKLIST.md` §5.

> **Backlog operativo cerrado (2026-07-16):** las 4 piezas `Parcial` iniciales (LISTVIEW-001, MASTERVIEW-001, PHASES-001, PAGE-001) y las 4 piezas `Pendiente` (STATUS-NORM-001, RBAC-001, VIEWS-E2E-001, INBOX-CONTRACT-001) estan todas en `Hecho`. Este handover queda sin IDs activos en §6. Cualquier nuevo trabajo abre un nuevo ID con el mismo formato (`PARCIAL-...-NNN` para refactors parciales; `PEND-...-NNN` para features nuevas). La consistencia entre Kanban/Table/Calendar/Gantt depende del contrato **`useProjectTasks` + `ProjectUpdateContext`**; cualquier mutacion desde una vista profunda debe pasar por el hook para que las demas vistas se enteren sin recarga.
   - crear tarea en `TasksTableView` → debe aparecer reflejada en Kanban, Calendar, Gantt sin recarga (vía `useProjectTasks.create` + `ProjectUpdateContext`).
   - mover tarea en Kanban → debe reordenarse consistentemente en Table y Calendar (vía `update` con `status` + sort).
   - editar `due_date` en Gantt → debe reflejarse en TaskDetailPanel y Calendar (vía `update` con `due_date`).
   - Si una de estas falla después de un cambio, sospechoso #1: una vista escribiendo estado local en lugar de delegar al hook compartido.

---

## 9. Archivos a leer primero al retomar

1. Este doc (`docs/ESTADO_PROYECTOS.md`) — visión general
2. `docs/PROJECTS_API_CONTRACTS.md` — contratos API y gaps RBAC
3. `docs/PROJECTS_QA_CHECKLIST.md` — smoke, ampliaciones y checks manuales
4. `docs/PROJECTS_RBAC_MATRIX.md` — matriz compacta de permisos y asimetrias reales
5. `docs/PLAN_PROYECTOS_CALIDAD.md` — orden operativo canónico del módulo
6. `docs/PLAN_VISTAS_EDITABLES_PROYECTOS.md` — acta histórica del frente de vistas editables
7. `backend/models_projects.py` — modelo de datos
8. `backend/api/projects.py` — superficie API
9. `scripts/test_projects_quality.py` — flujo real esperado
9. `docs/projects_api_postman_collection.json` — contratos REST

## 10. Tabla de IDs estables (referencia rápida)

Para que cualquier LLM (Freebuff/Kimi/Claude/GPT/Gemini) pueda hacer referencia inequívoca:

| ID | Pieza | Archivo |
|---|---|---|
| `PARCIAL-LISTVIEW-001` | ✅ **Hecho 2026-07-16** — ProjectListView reduce deps localOverrides + converge con useProjectTasks. Mutex estricto en `handleChangeTask` + `useEffect` que sincroniza `hookTasks` hacia el padre cuando `projectId` está set; JSDoc aclaratorio en `Props`. | `frontend/src/components/projects/ProjectListView.tsx` |
| `PARCIAL-MASTERVIEW-001` | ✅ **Hecho 2026-07-16** — ProjectMasterView edición de nodos + hitos. Reescrito para ser self-sufficient vía `useProjectUpdate()`: edición inline de hitos (title/target_date/is_completed/create/delete con `window.confirm`) + edición inline de tareas en `NodeCard` (status toggle + rename preservando prefijo). `page.tsx` perdió la card aside de hitos y los handlers/estado asociados. | `frontend/src/components/projects/ProjectMasterView.tsx` + `frontend/src/app/plataforma/projects/[id]/page.tsx` |
| `PARCIAL-PHASES-001` | ✅ **Hecho 2026-07-16** — PhaseManagerDrawer contrato único de fases. Reescrito self-sufficient: consume `phases`/`tasks`/`reloadProject` del `ProjectUpdateContext`; API surface colapsa a `{projectId, onClose}`. Validación: ≥1 fase, name no vacío, slug único case-insensitive. Pre-flight de tasks huérfanas: bloquea save si algún `task.status` quedaría fuera del nuevo set de slugs (mitiga `_assert_status_in_project_phases` del backend). Draft en localStorage preservado. | `frontend/src/components/projects/PhaseManagerDrawer.tsx` |
| `PARCIAL-PAGE-001` | ✅ **Hecho 2026-07-16** — Page de detalle `/projects/[id]` simplificación. Hook `useProjectPageData` (176 LOC) centraliza fetching & mutaciones; componente `ProjectViewsContent` (165 LOC) renderiza el switcher según `viewType` consumiendo de `ProjectUpdateContext` (sin prop-drilling). `page.tsx` reducido a 264 LOC (era 663) y queda como orquestador (auth/router/URL sync/drawers/TaskDetailPanel). 3 fixes post-review aplicados: `useAuth` destructura `{ user, hasPermission, token }` (token real en `handleDeleteProject`), `handleDeleteFromPanel` consolidado en una sola secuencia, y `ProjectActivityFeed` movido al dashboard view de `ProjectViewsContent` (sin aside oculto en mobile). | `frontend/src/app/plataforma/projects/[id]/page.tsx` + `frontend/src/hooks/useProjectPageData.ts` + `frontend/src/components/projects/ProjectViewsContent.tsx` |
| `PEND-STATUS-NORM-001` | ✅ **Hecho 2026-07-16** — Normalizar `status` (proyecto y tarea). Backend `ProjectStatus = Annotated[Literal['planning','active','on_hold','completed','archived'], BeforeValidator(_normalize_project_status_value)]` mapea legacy `paused\|stopped→on_hold`, `done\|finished→completed`, `cancelled\|closed→archived`. `ProjectBase.status` y `ProjectUpdate.status` narrowed. TaskStatus queda `str` (kanban dinámico). Alembic migration `20260717_0001_normalize_project_status.py` staged (no auto-aplica DDL; ejecutar `alembic upgrade head` cuando el operador lo decida). Frontend `PROJECT_STATUSES`/`ProjectStatus`/`PROJECT_STATUS_LABELS` centralizados en `lib/projects/constants.ts`; `ProjectRecord.status` narrowed; `InlineProjectStatusPicker` re-exporta desde constants. | `backend/schemas/projects.py` + `alembic/versions/20260717_0001_normalize_project_status.py` + `frontend/src/lib/projects/constants.ts` + `frontend/src/types/projects.ts` + `frontend/src/components/ui/inline-editors/InlineProjectStatusPicker.tsx` |
| `PEND-RBAC-001` | ✅ **Hecho 2026-07-16** — Suite RBAC parametrizada sobre 4 roles canónicas contra 30 endpoints del router `projects.py`. Descubrimientos clave: baseline **Miembro = 403** en endpoints sin `project_id`/`task_id`; **404** en endpoints con `project_id`/`task_id` inexistente/out-of-scope (Axioma 3 / existence-leak safe); jerarquía `manage → edit → read` funciona (Gestor cubre edit/read por expand); **asimetría DELETE/PATCH** en `/projects/{id}` (DELETE usa `require_staff_or_admin`=`academy:manage`, PATCH usa `projects:edit`); **gap `PUT /phases`** (decorador `projects:edit`, no `projects:manage`; Editor pasa RBAC contrario al docstring). Helpers: `_ensure_role_with_default_perms`/`_seed_role_user` materializan `RolPlataforma` con permisos canónicos desde `DEFAULT_ROLES` (cierra el hoyo del stub `permisos={"default":"allow"}` de `seed_user_with_role`). 116/116 pasan; matriz re-parametrizable para extensiones (subtasks/supplies/attachments quedan como cobertura representativa, agregables). | `tests/test_projects_rbac.py` |
| `PEND-VIEWS-E2E-001` | ✅ **Hecho 2026-07-16** — Suite vitest de integración cross-view (`frontend/src/lib/__tests__/projects-views-integration.test.tsx`, 8 tests verdes). Valida el invariante: todas las vistas dentro de un mismo `ProjectUpdateProvider` leen del MISMO `tasks` array; mutaciones (`createTask`/`updateTask`/`deleteTask`) se propagan a N consumers sin recarga explícita. Estrategia: `MiniList` (helper trivial con `data-*` attributes que expone status/priority/due_date) actúa como vista-representante; `Harness` mantiene `tasks` en `useState` y provee mutators in-memory; `ProjectKanbanBoard` mockeado como `() => null` (deps transitivas con historial de fallos jsdom: dnd-kit + ag-grid-enterprise + framer-motion + ConfirmActionDrawer con React legacy). Smoke real del Kanban sigue cubierto por navegador manual contra el dev server. Cubre:  throw fuera del Provider (regression guard), render inicial en 2 consumers, createTask/updateTask/deleteTask propaga a N consumers, mutaciones concurrentes convergen al estado final, smoke de MiniList como vista consumidora genérica. | `frontend/src/lib/__tests__/projects-views-integration.test.tsx` |
| `PEND-INBOX-CONTRACT-001` | ✅ **Hecho 2026-07-16** — Contrato documentado del inbox unificado. `GET /api/projects/inbox?limit=50` devuelve `List[ProjectInboxItem]` con dos superficies en el mismo feed: (a) **comentarios no resueltos** (`type="comment"`, `~is_resolved` + excluye auto-comentarios) orden `created_at desc`; (b) **tareas abiertas asignadas al actor** (`type="task_assigned"`, `assignee_id==persona_id` + `status!="completed"` + no soft-deletada) orden `updated_at desc`. `id` es composite `"comment-{id}"` / `"task-{id}"`, mismo shape que `item_id` en `POST /api/projects/inbox/{item_id}/read`. `POST` upserta `project_inbox_state` (UNIQUE `(persona_id, item_id)`). RBAC: GET→`projects:read`, POST→`projects:edit` (member=403, validado por `tests/test_projects_rbac.py`). Axioma 3: feed acotado a `sede_id` del actor; superadmin (`user_sede=null`) ve todo. Detalle completo en este handover §4.1. | `backend/api/projects.py` + §4.1 |
| `PEND-QUALITY-TASK-CREATE-001` | ✅ **Hecho 2026-07-16** — Bloquear `title: ''` en tasks. Backend `ProjectTaskBase.title` y `ProjectTaskUpdate.title` con `min_length=1` + `field_validator(mode='before')` que `.strip()` (422 con `''` o `'   '`). Frontend `useProjectPageData.createTask` rechaza título vacío localmente con `toast.error('Ingresa un título para la tarea')`. La vista `list` en `ProjectViewsContent` sigue pasando `title: ''` literal al callback, pero el guard del hook la bloquea antes del round-trip. Tests: `test_create_task_with_empty_title_returns_422`, `test_create_task_with_whitespace_title_returns_422`, `test_update_task_with_empty_title_returns_422` en `tests/test_projects_api.py::TestTasks`. Doc: `PROJECTS_API_CONTRACTS.md` §4.1. | `backend/schemas/projects.py` + `frontend/src/hooks/useProjectPageData.ts` + `tests/test_projects_api.py` + `docs/PROJECTS_API_CONTRACTS.md` |
| `PEND-QUALITY-PHASE-SYNC-001` | ✅ **Hecho 2026-07-16** — Reset explícito de phases al navegar. `useProjectPageData.loadProject` reescribe `setPhases(Array.isArray(phasesData) ? phasesData : [])` siempre (antes solo aplicaba si `length > 0`, lo que preservaba fases stale del proyecto anterior cuando el API respondía `[]`). Smoke de navegación agregado. Doc: `PROJECTS_API_CONTRACTS.md` §11.1. | `frontend/src/hooks/useProjectPageData.ts` + `docs/PROJECTS_API_CONTRACTS.md` |
| `PEND-QUALITY-INBOX-SCOPE-001` | ✅ **Hecho 2026-07-16** — Endurecer `/projects/inbox`. `list_inbox` ahora filtra `Project.deleted_at IS NULL` en ambas superficies (comentarios + tareas). Helper `_inbox_item_exists_for_actor` valida prefijo (`comment-<uuid>` / `task-<uuid>`), pertenencia a `sede_id` del actor, proyecto no soft-deleted y (para tasks) asignación + estado no terminal antes del upsert. `mark_inbox_read` devuelve **404** ante `item_id` arbitrario. Tests: 4 nuevos en `TestInbox` (`test_inbox_excludes_comments_from_soft_deleted_project`, `test_inbox_excludes_tasks_from_soft_deleted_project`, `test_mark_inbox_read_with_invalid_id_returns_404`, `test_mark_inbox_read_with_other_actor_item_returns_404`). Doc: `PROJECTS_API_CONTRACTS.md` §7.1. | `backend/api/projects.py` (+ helper `_inbox_item_exists_for_actor`) + `tests/test_projects_api.py` + `docs/PROJECTS_API_CONTRACTS.md` |
| `PEND-QUALITY-RBAC-ASYMMETRY-001` | ✅ **Hecho 2026-07-16** — Política confirmada (NO gap). `DELETE /api/projects/{id}` se mantiene deliberadamente bajo `require_staff_or_admin` (`academy:manage`); la asimetría frente a `PATCH /projects/{id}` (`projects:edit`) es **política confirmada**, no bug. Justificación: el borrado de proyecto arrastra tareas, hitos, wiki, pizarra, comentarios y bitácora ministerial, y se considera operación destructiva de módulo. Editor pasa `PATCH` pero recibe **403** en `DELETE`; Gestor/Admin pasan ambas. Docstring de `delete_project` documenta la política. Test renombrado: `test_delete_project_requires_academy_manage_per_policy` (mantiene el mismo baseline congelado). Si en el futuro se decide alinear `DELETE` con `projects:*`, este test y los docs deben actualizarse explícitamente. Doc: `PROJECTS_RBAC_MATRIX.md` §6 y §6.1 + `PROJECTS_API_CONTRACTS.md` §11. | `backend/api/projects.py` (docstring) + `tests/test_projects_rbac.py` (rename) + `docs/PROJECTS_RBAC_MATRIX.md` + `docs/PROJECTS_API_CONTRACTS.md` |
| `PEND-QUALITY-PROJECT-TITLE-NORM-001` | ✅ **Hecho 2026-07-16** — Endurecer `title` en proyecto. Anotación diferida del code review del `2026-07-16` que dejé pendiente en `backend/schemas/projects.py` ("si en el futuro se quiere endurecer también el título de proyecto, abrir un ID nuevo"). Cierre aplicando el mismo patrón que `ProjectTaskBase.title`: `min_length=1` + `field_validator(mode='before')` con `.strip()` en `ProjectBase.title` y `ProjectUpdate.title`. Tests: 3 nuevos en `TestProjectsCRUD` (`test_create_project_with_empty_title_returns_422`, `test_create_project_with_whitespace_title_returns_422`, `test_update_project_with_empty_title_returns_422`). Doc: `PROJECTS_API_CONTRACTS.md` §2.1. | `backend/schemas/projects.py` + `tests/test_projects_api.py` + `docs/PROJECTS_API_CONTRACTS.md` |
| `PEND-FRONTEND-E2E-PROJECTS-001` | ✅ **Hecho 2026-07-16** — smoke frontend Projects dedicado para listado, tareas e inbox con guard de consola/API/assets, sin depender de la suite demo seed. | `frontend/tests/e2e/projects/smoke.spec.ts` |
| `PEND-FRONTEND-E2E-PROJECTS-DETAIL-001` | ✅ **Hecho 2026-07-16** — smoke profundo seeded del detalle de proyecto para dashboard, list y calendar con guards de consola/API/assets reutilizando `seed-projects-demo`. | `frontend/tests/e2e/projects/detail.spec.ts` |
| `PEND-QUALITY-PHASES-RBAC-001` | ✅ **Hecho 2026-07-16 / Reforzado 2026-07-17** — Cerrar el drift RBAC de `PUT /projects/{id}/phases`. Backend: decorador cambiado a `require_project_access("manage")` (antes `require_module_access("projects", "manage")`). Editor recibe **403** para proyecto existente en su sede y **404** (Axioma 3) para project_id inexistente/cross-sede. Tests: `test_editor_blocked_from_put_phases` (assert 404) + `test_editor_blocked_from_put_phases_existing_project` (assert 403). `test_gestor_can_modify_phases` se mantiene verde (Gestor tiene `projects:manage`). Docs: §3 PROJECTS_API_CONTRACTS, §4.2 PROJECTS_RBAC_MATRIX + top-level docstring de `test_projects_rbac.py` actualizados. | `backend/api/projects.py` + `tests/test_projects_rbac.py` + `docs/PROJECTS_API_CONTRACTS.md` + `docs/PROJECTS_RBAC_MATRIX.md` + `docs/PLAN_PROYECTOS_CALIDAD.md` |


> **PARCIAL-PAGE-001 (cierre 2026-07-16):** Hook `useProjectPageData` (176 LOC) encapsula fetching & mutaciones (project/tasks/phases/activities + loadProject, createTask, updateProject, updateTask, deleteTask + error/reloadKey). Componente `ProjectViewsContent` (165 LOC) renderiza el switcher según `viewType` consumiendo del `ProjectUpdateContext` (sin prop-drilling). `page.tsx` reducido a 264 LOC (era 663) y queda como orquestador (auth/router/URL sync/drawers/TaskDetailPanel). 3 fixes post-review aplicados: `useAuth` ahora destructura `{ user, hasPermission, token }` para que `handleDeleteProject` use el token real (antes ambos ternarios eran undefined), `handleDeleteFromPanel` consolidado en una sola secuencia (sin doble cierre), y `ProjectActivityFeed` movido al dashboard view de `ProjectViewsContent` (visible en todos los breakpoints).

> **PEND-STATUS-NORM-001 (cierre 2026-07-16):** Backend `ProjectStatus = Annotated[Literal['planning','active','on_hold','completed','archived'], BeforeValidator(_normalize_project_status_value)]` mapea legacy values losslessly y narrowed `ProjectBase.status`/`ProjectUpdate.status`. `TaskStatus` permanece `str` por diseño (kanban slug dinámico via `_assert_status_in_project_phases`). Alembic `20260717_0001_normalize_project_status.py` staged (UPDATE legacy→canónico + fallback a 'planning' para valores no reconocidos; CHECK constraint commented-out para deferir aplicación al operador). Frontend `PROJECT_STATUSES` + `ProjectStatus` + `PROJECT_STATUS_LABELS` + `getValidProjectStatus` centralizados en `lib/projects/constants.ts`; `ProjectRecord.status: ProjectStatus`; `InlineProjectStatusPicker` re-exporta desde constants (mantiene labels locales "En Marcha"/"Alcanzado" para preservar UX dashboard).

> **PEND-RBAC-001 (cierre 2026-07-16):** Suite RBAC en `tests/test_projects_rbac.py` (116 tests, sin DB modificada). Matriz parametrizada: (a) 14 endpoints `GET` × 4 roles + (b) 16 endpoints `POST/PUT/PATCH/DELETE/comentarios` × 4 roles. Fixtures `role_headers` crea admin (vía `seed_admin`) + Gestor/Editor/Miembro con `RolPlataforma` alineado a `DEFAULT_ROLES` (cierra el hoyo de `permisos={"default":"allow"}` que tenía `seed_user_with_role`). **Asimetría descubierta**: `delete_project` está protegido con `require_staff_or_admin = require_permission("academy:manage")` mientras su primo `update_project` usa `projects:edit` — Editor (con `projects:edit`) pasa PATCH pero recibe 403 en DELETE; documentado en `TestPermissionHierarchy::test_editor_blocked_from_delete_project`. **Gap documentado**: `PUT /projects/{id}/phases` usa `projects:edit` aunque el docstring del endpoint declara "Solo administradores y gestores" — `TestPermissionGranularityGaps::test_editor_passes_put_phases_rbac_gap` captura el estado actual como baseline revierte-cuando-se-promueva. **Baseline Miembro**: endpoints sin `project_id`/`task_id` → 403; endpoints con `project_id`/`task_id` protegidos por `require_project_access` y recurso inexistente/out-of-scope → 404 (Axioma 3). Cualquier futuro debate sobre granularidad de Miembro romperá estos tests y obligará a un análisis explícito del modelo de permisos. Ver `BASELINE-MIEMBRO-001` en §6 y §10 para la política confirmada post-cierre.

> **PEND-VIEWS-E2E-001 (cierre 2026-07-16):** Suite vitest en `frontend/src/lib/__tests__/projects-views-integration.test.tsx` (8 tests verdes). Decisión arquitectónica clave: **MiniList** (helper trivial con `data-*` attrs) actúa como vista-representante para evitar la cascada de mocks transitivos de las vistas reales. **ProjectKanbanBoard** se mockea como `() => null` por dos motivos: (a) sus deps transitivas (`@dnd-kit/core`+`sortable`, `SymbolicTaskCard` con `useSortable`, `ConfirmActionDrawer` con `React.useState` legacy, `KanbanColumn` con `useDroppable`) tienen historial de cascading mock+import errors en jsdom; (b) el invariante que esta suite valida (la PROPAGACIÓN de mutaciones a través del Context) no depende del render real del Kanban — MiniList + Harness lo cubre completo. Smoke del Kanban real queda cubierto por navegador contra el dev server. Mutations mockeadas: `createTask`/`updateTask`/`deleteTask` se ejecutan in-memory sobre un `useState` del Harness (sin red). Tests cubren: throw fuera del Provider (regression guard), render inicial en 2 MiniList, propagación de `createTask`/`updateTask({status})`/`updateTask({due_date})`/`deleteTask` a 2 consumidores, mutaciones concurrentes convergen al último write (`Mutaciones concurrentes convergen`), y smoke directo contra MiniList+Provider real.

> **PEND-INBOX-CONTRACT-001 (cierre 2026-07-16):** Contrato consolidado en `ccf/docs/ESTADO_PROYECTOS.md` §4.1 (este handover). El inbox **NO** es redundante con `activities`: `activities` es bitácora cruda de mutaciones con `kind`/`description`; `inbox` es un feed normalizado por-persona con merge de 2 superficies (comentarios no resueltos + tareas abiertas asignadas) y estado `is_read` por item-id. Modelo `ProjectInboxState` (UNIQUE `(persona_id, item_id)`) sostiene el upsert atómico de `mark_inbox_read`. RBAC cubierto transversalmente por `tests/test_projects_rbac.py` (PEND-RBAC-001 deja Miembro=403 explícito como baseline).

Búsqueda rápida para cualquier sesión:

```bash
grep -nE "PARCIAL-|PEND-" /root/ccf/docs/ESTADO_PROYECTOS.md
```
