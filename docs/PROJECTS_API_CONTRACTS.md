# Contratos API — Projects

## 1. Alcance

Este documento cubre el router `backend/api/projects.py`, montado en `/api/projects`.

Reglas base:

- Frontend plataforma usa `apiFetch('/projects/...')`.
- `projects` es un modulo autenticado y tenant-scoped por `sede_id`.
- `Project.owner_id` y `ProjectTask.assignee_id` referencian `personas.id`.
- Los permisos canónicos son `projects:read`, `projects:edit`, `projects:manage`.

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

## 3. Fases

| Metodo | Ruta | Permiso esperado |
|---|---|---|
| `GET` | `/projects/{project_id}/phases` | `projects:read` |
| `PUT` | `/projects/{project_id}/phases` | `projects:edit` hoy |

Notas:

- El docstring declara intención más restrictiva, pero el comportamiento real actual permite `Editor` por `projects:edit`.
- Cualquier cambio aquí debe romper explícitamente `tests/test_projects_rbac.py`.

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
  - `Miembro`: `403` en toda la API projects hoy

## 11. Gaps documentados

1. `DELETE /projects/{id}` usa `academy:manage`, no `projects:*`.
2. `PUT /projects/{id}/phases` permite `Editor` por decoración actual.
3. La matriz RBAC aún vive repartida entre `ESTADO_PROYECTOS.md` y `tests/test_projects_rbac.py`; falta una matriz canónica por rol más compacta.
