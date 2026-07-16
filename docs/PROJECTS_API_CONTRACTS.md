# Contratos API — Projects

## 1. Alcance

Este documento cubre el router `backend/api/projects.py`, montado en `/api/projects`.

Reglas base:

- Frontend plataforma usa `apiFetch('/projects/...')`.
- `projects` es un modulo autenticado y tenant-scoped por `sede_id`.
- `Project.owner_id` y `ProjectTask.assignee_id` referencian `personas.id`.
- Los permisos canónicos son `projects:read`, `projects:edit`, `projects:manage`.

Referencia RBAC:

- `docs/PROJECTS_RBAC_MATRIX.md`

## 2. CRUD de proyecto

| Metodo | Ruta | Permiso esperado |
|---|---|---|
| `GET` | `/projects` | `projects:read` |
| `POST` | `/projects` | `projects:edit` |
| `GET` | `/projects/{project_id}` | `projects:read` |
| `PATCH` | `/projects/{project_id}` | `projects:edit` |
| `DELETE` | `/projects/{project_id}` | `academy:manage` hoy |

Notas:

- `DELETE /projects/{id}` es la asimetría documentada de RBAC: usa `require_staff_or_admin` (`academy:manage`), no `projects:edit`.
- `DELETE` es soft delete.

- `PATCH` permite actualización parcial. `title` cuando se envía debe ser no vacío.

### 2.1 Validación de `title` en proyecto (`PEND-QUALITY-PROJECT-TITLE-NORM-001`, anotación diferida del code review del 2026-07-16, aplicada el mismo día)

`ProjectBase.title` y `ProjectUpdate.title` rechazan títulos vacíos:

- `min_length=1` (Pydantic devuelve **422** cuando `title` es `""`).
- `field_validator(mode='before')` ejecuta `.strip()` antes de validar,
  por lo que `"   "` también produce **422**.
- Aplica tanto a `POST /projects` como a `PATCH /projects/{id}`.

Cobertura:

- backend: `tests/test_projects_api.py::TestProjectsCRUD::test_create_project_with_empty_title_returns_422`,
  `test_create_project_with_whitespace_title_returns_422`,
  `test_update_project_with_empty_title_returns_422`.

Nota: el comportamiento previo del módulo permitía crear proyectos con
`título=""`. Endurecerlo es la anotación diferida que el code review del
2026-07-16 dejó explícita en `backend/schemas/projects.py`
(`PEND-QUALITY-PROJECT-TITLE-NORM-001`). La regla ahora es consistente
con `ProjectTaskBase.title`.

## 3. Fases

| Metodo | Ruta | Permiso esperado |
|---|---|---|
| `GET` | `/projects/{project_id}/phases` | `projects:read` |
| `PUT` | `/projects/{project_id}/phases` | `projects:manage` |

Notas:

- Decorador alineado con el docstring del endpoint ("Solo administradores y gestores"). `Editor` recibe **403**; `Gestor` y `Admin` pasan por jerarquía `manage → edit → read`.
- Baseline congelado en ``tests/test_projects_rbac.py::test_editor_blocked_from_put_phases`` (cierre ``PEND-QUALITY-PHASES-RBAC-001``).

## 4. Tareas

| Metodo | Ruta | Permiso esperado |
|---|---|---|
| `GET` | `/projects/tasks` | `projects:read` |
| `GET` | `/projects/tasks/{task_id}` | `projects:read` |
| `PATCH` | `/projects/tasks/{task_id}` | `projects:edit` |
| `GET` | `/projects/{project_id}/tasks` | `projects:read` |
| `POST` | `/projects/{project_id}/tasks` | `projects:edit` |
| `PATCH` | `/projects/{project_id}/tasks/{task_id}` | `projects:edit` |
| `DELETE` | `/projects/{project_id}/tasks/{task_id}` | `projects:edit` |

Invariantes:

- tareas fuera de la `sede_id` del actor no se exponen
- `status` de tarea debe pertenecer al set de fases válidas del proyecto
- `GET /projects/tasks` devuelve tareas asignadas a la persona autenticada

### 4.1 Validación de `title` (`PEND-QUALITY-TASK-CREATE-001`, cierre 2026-07-16)

`ProjectTaskBase.title` y `ProjectTaskUpdate.title` rechazan títulos vacíos:

- `min_length=1` (Pydantic devuelve **422** cuando `title` es `""`).
- `field_validator(mode="before")` ejecuta `.strip()` antes de validar, así
  que `"   "` también produce **422**.
- Aplica tanto a `POST /projects/{id}/tasks` como a `PATCH /projects/tasks/{id}`.

Cobertura:

- backend: `tests/test_projects_api.py::TestTasks::test_create_task_with_empty_title_returns_422`,
  `test_create_task_with_whitespace_title_returns_422`,
  `test_update_task_with_empty_title_returns_422`.
- frontend: `useProjectPageData.createTask` rechaza títulos vacíos con
  `toast.error("Ingresa un título para la tarea")` y no llega al backend.

La vista `list` en `ProjectViewsContent` sigue pasando `title: ''` como
literal al callback `onAddTask`, pero el guard del hook compartido lo
bloquea antes del round-trip.

## 5. Subtasks, supplies y attachments

### Subtasks

| Metodo | Ruta | Permiso esperado |
|---|---|---|
| `POST` | `/projects/{project_id}/tasks/{task_id}/subtasks` | `projects:edit` |
| `PATCH` | `/projects/{project_id}/tasks/{task_id}/subtasks/{subtask_id}` | `projects:edit` |
| `DELETE` | `/projects/{project_id}/tasks/{task_id}/subtasks/{subtask_id}` | `projects:edit` |

### Supplies

| Metodo | Ruta | Permiso esperado |
|---|---|---|
| `GET` | `/projects/{project_id}/tasks/{task_id}/supplies` | `projects:read` |
| `POST` | `/projects/{project_id}/tasks/{task_id}/supplies` | `projects:edit` |
| `PATCH` | `/projects/{project_id}/tasks/{task_id}/supplies/{supply_id}` | `projects:edit` |
| `DELETE` | `/projects/{project_id}/tasks/{task_id}/supplies/{supply_id}` | `projects:edit` |

### Attachments

| Metodo | Ruta | Permiso esperado |
|---|---|---|
| `POST` | `/projects/{project_id}/tasks/{task_id}/attachments` | `projects:edit` |
| `DELETE` | `/projects/{project_id}/tasks/{task_id}/attachments/{attachment_id}` | `projects:edit` |

## 6. Comentarios

| Metodo | Ruta | Permiso esperado |
|---|---|---|
| `GET` | `/projects/comments` | `projects:read` |
| `POST` | `/projects/comments` | `projects:edit` |
| `POST` | `/projects/{project_id}/comments` | `projects:edit` |
| `PATCH` | `/projects/comments/{comment_id}` | `projects:edit` |
| `DELETE` | `/projects/comments/{comment_id}` | `projects:edit` |

Notas:

- `GET /projects/comments` soporta `limit`, `offset` y `project_id`.
- el inbox reutiliza comentarios no resueltos como una de sus superficies.

## 7. Inbox, activities, portfolio

| Metodo | Ruta | Permiso esperado |
|---|---|---|
| `GET` | `/projects/summary` | `projects:read` |
| `GET` | `/projects/workload` | `projects:read` |
| `GET` | `/projects/activities` | `projects:read` |
| `GET` | `/projects/inbox` | `projects:read` |
| `POST` | `/projects/inbox/{item_id}/read` | `projects:edit` |
| `GET` | `/projects/whiteboards` | `projects:read` |

Inbox:

- mezcla comentarios no resueltos + tareas abiertas asignadas
- `item_id` es compuesto (`comment-*` / `task-*`)
- `POST /inbox/{item_id}/read` hace upsert en `project_inbox_state`

### 7.1 Endurecimiento del inbox (`PEND-QUALITY-INBOX-SCOPE-001`, cierre 2026-07-16)

- `GET /api/projects/inbox` ahora filtra `Project.deleted_at IS NULL` en
  ambas superficies (comentarios + tareas). Antes, un proyecto
  soft-deleted podía dejar comentarios fantasma en el feed del actor.
- `POST /api/projects/inbox/{item_id}/read` rechaza con **404** cualquier
  `item_id` que no corresponda a una entrada real del inbox del actor
  (existencia-leak safe). El helper interno
  `_inbox_item_exists_for_actor` valida prefijo (`comment-` / `task-`),
  pertenencia a proyecto no soft-deleted, alcance de `sede_id` y, para
  tasks, asignación + estado no terminal.

Cobertura:

- `tests/test_projects_api.py::TestInbox::test_inbox_excludes_comments_from_soft_deleted_project`
- `tests/test_projects_api.py::TestInbox::test_inbox_excludes_tasks_from_soft_deleted_project`
- `tests/test_projects_api.py::TestInbox::test_mark_inbox_read_with_invalid_id_returns_404`
- `tests/test_projects_api.py::TestInbox::test_mark_inbox_read_with_other_actor_item_returns_404`

## 8. Wiki, whiteboard y mensajes

### Wiki

| Metodo | Ruta | Permiso esperado |
|---|---|---|
| `GET` | `/projects/{project_id}/wiki` | `projects:read` |
| `POST` | `/projects/{project_id}/wiki` | `projects:edit` |

### Whiteboard

| Metodo | Ruta | Permiso esperado |
|---|---|---|
| `GET` | `/projects/{project_id}/whiteboard` | `projects:read` |
| `POST` | `/projects/{project_id}/whiteboard` | `projects:edit` |
| `DELETE` | `/projects/{project_id}/whiteboard` | `projects:edit` |

### Mensajes del proyecto

| Metodo | Ruta | Permiso esperado |
|---|---|---|
| `GET` | `/projects/{project_id}/messages` | `projects:read` |
| `POST` | `/projects/{project_id}/messages` | `projects:edit` |
| `DELETE` | `/projects/{project_id}/messages/{message_id}` | `projects:edit` |

## 9. Milestones

| Metodo | Ruta | Permiso esperado |
|---|---|---|
| `GET` | `/projects/{project_id}/milestones` | `projects:read` |
| `POST` | `/projects/{project_id}/milestones` | `projects:edit` |
| `PATCH` | `/projects/{project_id}/milestones/{milestone_id}` | `projects:edit` |
| `DELETE` | `/projects/{project_id}/milestones/{milestone_id}` | `projects:edit` |

## 10. Contratos de seguridad y tenant

- `tests/test_projects_multi_tenant.py` es la referencia de Axioma 3.
- `tests/test_projects_rbac.py` es la referencia de permisos por rol.
- Baseline actual documentado:
  - `Administrador`: acceso completo
  - `Gestor`: `projects:manage`
  - `Editor`: `projects:edit`
  - `Miembro`: `403` en toda la API projects (política confirmada, 2026-07-16). El rol `Miembro` no existe en el contexto del módulo Projects. La asignación de tareas/proyectos a una persona es un mecanismo de delegación interna para usuarios que ya tienen acceso al módulo, no una vía de acceso para el rol `Miembro`.

## 11. Asimetrías y políticas formalizadas

1. `DELETE /projects/{id}` usa `academy:manage`, no `projects:*`.
   - **Estado actual** (`PEND-QUALITY-RBAC-ASYMMETRY-001`, cierre
     2026-07-16): **política confirmada**, no gap. El borrado de
     proyecto arrastra tareas, hitos, wiki, pizarra, comentarios y
     bitácora ministerial; se mantiene deliberadamente bajo
     `require_staff_or_admin` (`academy:manage`) para que sólo
     Gestor/Admin puedan ejecutarlo. Editor sigue bloqueado en DELETE
     aunque pase PATCH.
   - Test que congela la política:
     `tests/test_projects_rbac.py::test_delete_project_requires_academy_manage_per_policy`.
   - Si en el futuro se decide alinear DELETE con `projects:*`, este
     test (y `PROJECTS_RBAC_MATRIX.md` §6) deben actualizarse.
2. `PUT /projects/{id}/phases` requiere `projects:manage`.
   - **Estado actual** (`PEND-QUALITY-PHASES-RBAC-001`, cierre 2026-07-16): **gap cerrado**. El decorador fue alineado con el docstring; `Editor` recibe **403** y `Gestor`/`Admin` pasan. El test `TestPermissionGranularityGaps::test_editor_blocked_from_put_phases` congela el comportamiento.
3. La matriz RBAC compacta vive en `docs/PROJECTS_RBAC_MATRIX.md`; mantenerla sincronizada con `tests/test_projects_rbac.py`.

### 11.1 Phase sync (`PEND-QUALITY-PHASE-SYNC-001`, cierre 2026-07-16)

`useProjectPageData.loadProject` reescribe `setPhases(...)` siempre con
el resultado del round-trip (incluso cuando el array viene vacío), para
que navegar entre proyectos / volver a cargar no arrastre columnas
stale del proyecto anterior. Se conserva el sync legacy al padre
cuando `projectId` está set.

---

## 12. Hardenings cruzados (helpers internos)

Más allá de los guards RBAC documentados en §4, existen helpers internos en el router que refuerzan Axioma 3 y la integridad de mutaciones. NO son permisos explícitos pero documentan las defensas adicionales que el código aplica **antes** de persistir mutaciones correctamente autenticadas. Detalle complementario en `PROJECTS_RBAC_MATRIX.md §9`.

### 12.1 `_assert_assignee_in_sede` (api/projects.py:299-339)

Cierra una vulnerabilidad histórica donde un actor de `sede_a` podía inyectar un UUID de persona de `sede_b` en el cuerpo del PATCH. Aplicado en **5 callsites**: `create_project_task`, `update_task`, `update_project_task`, `create_subtask`, `update_subtask`. Comportamiento:

- Falsy `assignee_id` → silent skip.
- `user_sede = None` (superadmin) → sin filtro.
- Persona con `sede_id NULL` → bloqueada (untagged).
- Mismatch → **404** (existence-leak safe, nunca 403).

### 12.2 `_assert_status_in_project_phases` (api/projects.py:341-401)

Aplicado en `create_project_task`, `update_task`, `update_project_task`. Status code **400** (regla de negocio que depende de DB state, no validación estática). Ver `PROJECTS_RBAC_MATRIX.md §9.2` para detalle de fallback canónico y race window.

### 12.3 `_validate_whiteboard_json` (api/projects.py:403-412)

Aplicado en `update_project_whiteboard`. Rechaza `"undefined"` literal y JSON malformado con 400. Mitiga un bug recurrente donde el frontend accidentalmente llama `JSON.stringify(undefined)`.

### 12.4 Compat task mappings (api/projects.py:426-444)

Helpers `_normalize_task_payload` y `_normalize_task_enums` aplican migraciones lossless antes de INSERT/UPDATE y después de read. Tabla completa y detalle de los dos paths en `PROJECTS_RBAC_MATRIX.md §9.4`. Re-exponer los mappings canónicos en la capa de tipos TypeScript del frontend pendiente de ID nuevo.
