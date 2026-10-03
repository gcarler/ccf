# Auditoría de profesionalización — Proyectos (2026-10-03)

## Resumen ejecutivo

La certificación registrada el 2026-09-06 describe el estado de ese día, pero no constituye una garantía permanente. La revisión actual detectó un fallo reproducible del detalle del proyecto y una brecha de aislamiento en evaluación de automatizaciones; por ello, el módulo no debe presentarse hoy como “100/100” sin volver a ejecutar toda la matriz de QA.

Primer sprint implementado en `TKT-PROJECTS-PRO-01`:

- La serialización de tareas ya no sustituye la relación instrumentada `attachments` de SQLAlchemy. El schema de respuesta excluye adjuntos con `deleted_at`, evitando el fallo de flush/commit observado al calcular el resumen presupuestal del detalle.
- La evaluación de automatizaciones verifica que `task_id` pertenezca al proyecto de la ruta y que la tarea siga activa. Las condiciones de prioridad/estado/fase, cuando hay tarea, se contrastan con sus datos persistidos; el contexto del cliente no puede simular esos valores. Asignar o crear seguimientos exige que la persona destinataria pertenezca a la sede del actor.
- La pantalla de proyectos distingue carga inicial, error recuperable y vacío real; conserva la lista existente mientras actualiza y ofrece reintento.

## Evidencia y alcance

- Branch revisada: `feat/projects-frontend-ds-20261003`; HEAD previo: `51ab14b58bccf1b8c8d2e219620d8776ac37d1bd`.
- Auditoría exploratoria de API/CRUD, esquemas/modelos, rutas y pruebas del módulo; la corrida deliberadamente destructiva `scripts/test_projects_quality.py` no se ejecutó.
- Reproducción antes del arreglo: API + multi-tenant + RBAC = 144 passed, 1 failed (`TestProjectsCRUD.test_get_project_by_id`, HTTP 500 por `_sa_adapter`).
- Después del arreglo, la suite completa `test_projects_api.py + test_projects_multi_tenant.py + test_projects_rbac.py` = 248 passed (403.64 s), incluyendo detalle con adjunto soft-deleted y tarea cross-project.
- Frontend `ProjectsClient.test.tsx` = 6 passed; `npx tsc --noEmit` = PASS; `py_compile` y `git diff --check` = PASS.
- El router contiene 116 decoradores de rutas; `docs/ESTADO_PROYECTOS.md` y `docs/PROJECTS_API_CONTRACTS.md` aún hablan de 52 endpoints, por lo que la documentación de contrato requiere conciliación endpoint por endpoint.
- Ruff focalizado reporta 13 problemas existentes en los archivos inspeccionados (variables sin uso/nombres ambiguos, imports y f-strings); ninguno está en las líneas nuevas. Se deja su remediación fuera del primer sprint para no mezclar deuda ajena.

## Backlog priorizado y dueños sugeridos

| Prioridad | Hallazgo / resultado verificable | Capa / owner sugerido |
|---|---|---|
| P0 | Completar la suite API/RBAC/multi-tenant en verde y agregar prueba de asignación automatizada cross-sede; comprobar también `create_followup_task`. | Backend Projects + QA |
| P1 | Alinear los contratos/documentos con las 116 rutas actuales (la documentación afirma 52), corregir drift de RBAC y cubrir automatizaciones y detalle. Meta: cero rutas críticas sin contrato verificable. | Backend Projects + QA/Docs |
| P1 | Eliminar doble encabezado en lista/detalle y evitar que métricas globales desplacen calendario/Gantt/wiki; conservar la barra de métricas solo donde corresponda. | Frontend Projects |
| P1 | Recuperar las acciones de búsqueda/vistas en móvil sin alterar `WorkspaceToolbar` transversal sin revisión de blast-radius. | Plataforma UI + Projects |
| P1 | Añadir tests de carga/error/vacío y accesibilidad en vistas tabla, calendario, Gantt, wiki, detalle y formularios. Meta inicial: cada vista con al menos un flujo de teclado y un estado fallido cubierto. | Frontend QA + Projects |
| P2 | Añadir paginación/contrato de límites para `GET /projects` y medir consultas con relaciones. Meta: respuesta acotada y latencia p95 documentada sobre dataset representativo. | Backend Projects |
| P2 | Alinear títulos de proyectos/tareas: el schema acepta hasta 500 mientras columnas son `String(200)`. Si se amplía almacenamiento, incluir migración reversible. | Backend + DB |
| P2 | Cambiar montos Float a precisión decimal solo con decisión de producto y migración reversible; verificar reportes/redondeo antes del cambio. | Backend + DB/Finance |
| P2 | Revisar `any` restante en tareas, automatizaciones y reportes; reemplazarlo por contratos tipados sin reescribir componentes compartidos fuera del alcance. | Frontend Projects |

## Criterio de cierre del programa

No volver a declarar certificación global hasta que todas las suites de módulo definidas por `docs/PLAN_PROYECTOS_CALIDAD.md` pasen en el branch release, los contratos/RBAC estén reconciliados, E2E incluya la ruta autenticada de lista y detalle, y la auditoría de accesibilidad cubra todas las vistas visibles. Este primer sprint arregla dos defectos de backend y una experiencia de carga; no equivale a la profesionalización completa solicitada.
