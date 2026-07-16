# Plan de Calidad: Vistas Editables del Módulo de Proyectos

## Objetivo

Dejar documentado, con base en el código real, qué vistas del módulo de proyectos ya son editables, cuáles siguen parciales y qué falta para cerrar el contrato funcional sin introducir regresiones.

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

## Prioridad de Ejecución

1. Cerrar las piezas que ya están hechas pero son base compartida.
2. Completar las vistas que ya editan datos, pero aún tienen huecos de contrato.
3. Resolver las interacciones que siguen pendientes de la experiencia principal.
4. Revalidar backend, permisos y pruebas antes de dar el flujo por cerrado.

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

## Parcial

| Prioridad | Componente | Estado real | Qué está listo | Qué falta |
|-----------|------------|-------------|----------------|-----------|
| P0 | `frontend/src/components/projects/ProjectListView.tsx` | Parcial | Ya persiste cambios de estado, prioridad, fecha y asignado; quick-add funcional. | Reducir la dependencia de `localOverrides` y converger con el flujo compartido del hook. |
| P1 | `frontend/src/components/projects/ProjectMasterView.tsx` | Parcial | Título, descripción, estado y responsable ya son editables. | Falta hacer editables los nodos operativos y los hitos desde la misma vista. |
| P1 | `frontend/src/components/projects/PhaseManagerDrawer.tsx` | Parcial | La gestión de fases ya está conectada al contexto. | Falta cerrar el contrato de edición/validación si se quiere usar como fuente única de fases. |
| P2 | `frontend/src/app/plataforma/projects/[id]/page.tsx` | Parcial | La página ya orquesta vistas, drawers y contexto de actualización. | Sigue teniendo lógica de coordinación extensa y se beneficia de simplificación posterior. |

## Pendientes de cierre

- Reducción del estado local redundante en `ProjectListView`.
- Edición de nodos operativos e hitos en `ProjectMasterView`.
- Revalidación del backend de proyectos para permisos, contratos `PATCH/DELETE` y normalización de estados.
- Cierre de pruebas de integración entre lista, tabla, kanban, calendario y detalle.

## Orden operativo recomendado

1. Consolidar `ProjectListView` para reducir el estado local redundante.
2. Terminar `ProjectMasterView` con edición de nodos operativos e hitos.
3. Cerrar `PhaseManagerDrawer` si se quiere usar como fuente única de fases.
4. Revalidar backend, permisos y pruebas de integración.

## Verificación mínima

- TypeScript sin errores en los archivos tocados por el cambio funcional.
- Lint sin errores en las vistas editables.
- `useProjectTasks` cubierto por tests.
- Flujo manual probado entre `list`, `table`, `board`, `calendar` y `gantt`.
- No introducir cambios que alteren el contrato de navegación o las rutas públicas del módulo.

## Resumen operativo

- El bloque base ya está hecho.
- Las vistas más cercanas a terminar son `ProjectListView`, `ProjectMasterView`, `PhaseManagerDrawer` y la coordinación general de `page.tsx`.
- El trabajo pendiente real está concentrado en la reducción del estado local redundante y en el cierre del contrato entre frontend, backend y pruebas.
- Este documento sirve como referencia de ejecución y de auditoría, no como checklist ornamental.
