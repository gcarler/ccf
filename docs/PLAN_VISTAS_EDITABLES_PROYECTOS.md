# Plan de Calidad: Vistas Editables del Módulo de Proyectos

## Objetivo

Dejar documentado, con base en el código real, qué vistas del modulo de proyectos quedaron editables y cerradas tras la ejecucion del plan original, y que deuda tecnica transversal sigue viva fuera de ese plan.

## Criterio de estado

- `Hecho`: ya existe en el repo actual y cumple su contrato principal.
- `Parcial`: funciona, pero aún tiene huecos visibles, deuda de integración o una experiencia incompleta.
- `Pendiente`: no está resuelto en el código actual o solo queda como mejora futura.

## Regla de lectura

- `Hecho` no significa perfecto, significa que la capacidad principal ya está implementada y usable.
- `Parcial` debe reservarse para piezas activas que todavía requieren cierre de UX, integración o pruebas.
- `Pendiente` se usa solo cuando el comportamiento aún no existe o no está validado en el código actual.

## Nombres corregidos

- `GanttView` ahora es `ProjectGanttView` + `UniversalGanttView`.
- `ProjectEditForm` no es el refactor real; el componente vigente es `ProjectSettingsDrawer`.
- `ProjectWikiEditor`, `ProjectChatPanel`, `ProjectListView`, `TaskTableView`, `ProjectCalendarView`, `ProjectMasterView` y `ProjectKanbanBoard` son los nombres reales que usa la app.

## Estado del plan

- El plan original de vistas editables quedo cerrado el `2026-07-16`.
- Las cuatro piezas inicialmente marcadas como `Parcial` ya fueron resueltas en codigo y revalidadas.
- Las piezas transversales que estaban en `Pendiente` para poder dar el modulo por cerrado tambien quedaron cubiertas.
- Los documentos complementarios vigentes para retomar el modulo ahora son:
  - `docs/ESTADO_PROYECTOS.md`
  - `docs/PROJECTS_API_CONTRACTS.md`
  - `docs/PROJECTS_QA_CHECKLIST.md`

## Hecho

| Prioridad | Componente | Estado real | Alcance actual |
|-----------|------------|-------------|----------------|
| P0 | `frontend/src/hooks/useProjectTasks.ts` | Hecho | CRUD de tareas con `fetch`, `create`, `update`, `delete` y `move`, con rollback en error. |
| P0 | `frontend/src/context/ProjectUpdateContext.tsx` | Hecho | Contexto compartido para `project`, `tasks`, `phases`, `activities` y mutaciones desde vistas profundas. |
| P0 | `frontend/src/components/ui/inline-editors/` | Hecho | Editores inline reutilizables para estado, prioridad, fecha, persona, texto y estado de proyecto. |
| P0 | `frontend/src/components/projects/ProjectSettingsDrawer.tsx` | Hecho | Drawer real de edición de proyecto: título, descripción, estado, responsable y color. |
| P0 | `frontend/src/components/projects/ProjectGanttView.tsx` + `frontend/src/components/ui/UniversalGanttView.tsx` | Hecho | Click, arrastre y resize de barras conectados a actualización de fechas. |
| P0 | `frontend/src/app/plataforma/projects/ProjectsClient.tsx` + `frontend/src/components/projects/ProjectCard.tsx` | Hecho | Vista de proyectos con edición inline real en grid y tabla, más alta/baja de proyectos. |
| P1 | `frontend/src/components/projects/TaskDetailPanel.tsx` | Hecho | Panel de detalle editable de tarea con actualizaciones directas de campos y sub-recursos. |
| P1 | `frontend/src/components/projects/ProjectWikiEditor.tsx` | Hecho | Editor de wiki operativo y sincronizado. |
| P1 | `frontend/src/components/projects/ProjectChatPanel.tsx` | Hecho | Panel de chat operativo y sincronizado. |
| P1 | `frontend/src/lib/__tests__/useProjectTasks.test.tsx` | Hecho | Cobertura de CRUD base y rollback del hook compartido. |
| P1 | `frontend/src/components/projects/TaskTableView.tsx` | Hecho | Tabla editable con editores inline, agrupación, filtros y apertura de detalle por doble clic. |
| P1 | `frontend/src/components/projects/ProjectKanbanBoard.tsx` + `frontend/src/components/projects/KanbanColumn.tsx` + `frontend/src/components/projects/SortableTaskCard.tsx` | Hecho | Drag & drop persistente, edición inline de título, fecha, prioridad y asignado, más menú de acción. |
| P1 | `frontend/src/components/projects/ProjectCalendarView.tsx` + `frontend/src/components/ui/UniversalCalendarView.tsx` | Hecho | Click en día vacío abre creación con `due_date` prellenada, click en evento abre detalle y el arrastre de eventos reubica fechas. |
| P0 | `frontend/src/components/projects/ProjectListView.tsx` | Hecho | Convergencia con `useProjectTasks`, mutex estricto de mutaciones y sync hacia consumidores hermanos. |
| P1 | `frontend/src/components/projects/ProjectMasterView.tsx` | Hecho | Edicion inline de hitos y nodos operativos desde la misma vista, usando el contexto compartido. |
| P1 | `frontend/src/components/projects/PhaseManagerDrawer.tsx` | Hecho | Fuente unica de fases con validacion reforzada y bloqueo de tareas huerfanas antes de guardar. |
| P2 | `frontend/src/app/plataforma/projects/[id]/page.tsx` + `frontend/src/hooks/useProjectPageData.ts` + `frontend/src/components/projects/ProjectViewsContent.tsx` | Hecho | Orquestacion simplificada, menos prop drilling y separacion clara entre datos, vistas y shell. |
| P2 | `backend/schemas/projects.py` + `frontend/src/lib/projects/constants.ts` | Hecho | Normalizacion de `ProjectStatus` y centralizacion de labels/tipos del estado del proyecto. |
| P2 | `tests/test_projects_rbac.py` | Hecho | Matriz RBAC parametrica que documenta baseline actual, gaps y jerarquia `manage -> edit -> read`. |
| P2 | `frontend/src/lib/__tests__/projects-views-integration.test.tsx` | Hecho | Suite de integracion cross-view para verificar propagacion de mutaciones via `ProjectUpdateProvider`. |
| P2 | `backend/api/projects.py` + `docs/PROJECTS_API_CONTRACTS.md` | Hecho | Contrato funcional y documental de `/projects/inbox` y sus permisos asociados. |

## Backlog original

- No quedan items activos del plan original de vistas editables.
- Cualquier trabajo nuevo debe abrirse con un ID nuevo en `ESTADO_PROYECTOS.md`.
- Las deudas que siguen vivas ya no pertenecen a este plan; pertenecen a arquitectura, RBAC de plataforma o mejoras futuras.

## Backlog nuevo post-cierre

- `PEND-QUALITY-TASK-CREATE-001` — bloquear tareas con titulo vacio creadas desde la vista `list`, cerrando frontend, backend y pruebas.
- `PEND-QUALITY-PHASE-SYNC-001` — evitar que `phases` quede stale cuando el API responde `[]` en el detalle de proyecto.
- `PEND-QUALITY-INBOX-SCOPE-001` — endurecer `/projects/inbox` y `/projects/inbox/{item_id}/read` frente a soft delete, ownership e ids arbitrarios.
- `PEND-QUALITY-RBAC-ASYMMETRY-001` — decidir y cerrar la asimetria entre `PATCH /projects/{id}` y `DELETE /projects/{id}`.
- El detalle vivo de estos items debe mantenerse en `ESTADO_PROYECTOS.md`.

## Verificación mínima

- TypeScript sin errores en los archivos tocados por el cambio funcional.
- Lint sin errores en las vistas editables.
- `useProjectTasks` cubierto por tests.
- Flujo manual probado entre `list`, `table`, `board`, `calendar` y `gantt`.
- No introducir cambios que alteren el contrato de navegación o las rutas públicas del módulo.
- Smoke canónico del modulo pasando con `scripts/test_projects_quality.py`.
- Contratos API y QA complementaria delegados a `PROJECTS_API_CONTRACTS.md` y `PROJECTS_QA_CHECKLIST.md`.

## Resumen operativo

- El bloque base y el backlog original quedaron cerrados.
- Este documento ya no funciona como lista de pendientes; funciona como acta de cierre del plan de vistas editables.
- El estado vivo del modulo y el backlog nuevo post-cierre deben seguirse en `ESTADO_PROYECTOS.md`.
