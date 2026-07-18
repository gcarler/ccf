# Matriz RBAC — Projects CCF

> **Objetivo:** fijar la matriz RBAC operativa de Projects contra el codigo actual. Este documento no describe un ideal futuro; documenta los guards reales, las asimetrias vigentes y el baseline verificado por `tests/test_projects_rbac.py`.

## 1. Fuentes inspeccionadas

- `backend/api/projects.py`
- `tests/test_projects_rbac.py`
- `docs/ESTADO_PROYECTOS.md`
- `docs/PROJECTS_API_CONTRACTS.md`

Fecha de verificacion: **2026-07-16**.

## 2. Taxonomia canonica

Projects usa la taxonomia:

| Modulo | Accion | Permission key |
|---|---|---|
| `projects` | `read` | `projects:read` |
| `projects` | `edit` | `projects:edit` |
| `projects` | `manage` | `projects:manage` |

Jerarquia verificada en la suite:

- `manage -> edit -> read`
- `edit -> read`

## 3. Roles canonicamente verificados

La suite `tests/test_projects_rbac.py` valida estas cuatro superficies de rol:

| Rol | Lectura documental segura |
|---|---|
| `Administrador` | acceso completo |
| `Gestor` | `projects:manage`, cubre lectura y mutacion |
| `Editor` | `projects:edit`, cubre lectura y mutaciones `edit`, pero no huecos que exigen otro guard |
| `Miembro` | baseline actual: `403` en toda la API Projects |

## 4. Matriz por superficie

### 4.1 CRUD de proyecto

| Ruta | Guard real | Observacion |
|---|---|---|
| `GET /projects` | `projects:read` | lectura normal |
| `POST /projects` | `projects:edit` | creacion permitida a Editor/Gestor/Admin |
| `GET /projects/{id}` | `projects:read` | detalle |
| `PATCH /projects/{id}` | `projects:edit` | actualizacion normal |
| `DELETE /projects/{id}` | `academy:manage` | asimetria real; no usa `projects:*` |

### 4.2 Fases

| Ruta | Guard real | Observacion |
|---|---|---|
| `GET /projects/{id}/phases` | `projects:read` | lectura normal |
| `PUT /projects/{id}/phases` | `require_project_access("manage")` | alineado con docstring ("Solo Admin/Gestor"). Editor recibe 403; Gestor/Admin pasan. Miembro recibe **404** para project_id inexistente/cross-sede (Axioma 3). **Gap cerrado** (`PEND-QUALITY-PHASES-RBAC-001`, 2026-07-16) |

### 4.3 Tareas y extensiones

| Superficie | Guard real |
|---|---|
| tareas base | `projects:read` / `projects:edit` segun metodo |
| subtasks | `projects:edit` |
| supplies | `projects:read` / `projects:edit` |
| attachments | `projects:edit` |

### 4.4 Comentarios, inbox y portfolio

| Ruta | Guard real |
|---|---|
| `GET /projects/comments` | `projects:read` |
| `POST/PATCH/DELETE /projects/comments...` | `projects:edit` |
| `GET /projects/summary` | `projects:read` |
| `GET /projects/workload` | `projects:read` |
| `GET /projects/activities` | `projects:read` |
| `GET /projects/inbox` | `projects:read` |
| `POST /projects/inbox/{item_id}/read` | `projects:edit` |
| `GET /projects/whiteboards` | `projects:read` |

### 4.5 Wiki, whiteboard, mensajes y milestones

| Superficie | Guard real |
|---|---|
| wiki | `require_project_access("read"/"edit")` |
| whiteboard | `require_project_access("read"/"edit")` |
| mensajes | `require_module_access("projects", "read"/"edit")` |
| milestones | `require_module_access("projects", "read"/"edit")` |

**Nota sobre mensajes y milestones:** estos endpoints usan
`require_module_access` en lugar de `require_project_access`. Esto es una
**decisión consciente**: migrarlos a `require_project_access` abriría la
puerta a que un rol `Miembro` asignado al proyecto accediera a mensajes y
hitos, rompiendo el baseline documentado de que `Miembro` no tiene acceso al
módulo Projects. Por tanto, `Miembro` recibe **403** en estas rutas (incluso
con `project_id` en el path). Admin/Gestor/Editor siguen pasando, y para
ellos `_ensure_project` garantiza 404 cross-sede.

## 5. Baseline por rol

### Administrador

- debe pasar toda la superficie auditada

### Gestor

- debe pasar toda la superficie auditada del modulo
- el `DELETE /projects/{id}` tambien pasa porque tiene permisos de nivel alto

### Editor

- pasa lectura y mutaciones `projects:edit`
- queda bloqueado en `DELETE /projects/{id}` por la asimetria `academy:manage`
- pasa `PUT /projects/{id}/phases` por el guard actual, aunque el docstring sugiera una politica mas dura

### Miembro

- baseline actual verificado:
  - **403** en endpoints de módulo sin `project_id`/`task_id` específico (ej. `GET /api/projects`, `GET /api/projects/summary`, `POST /api/projects`, etc.).
  - **404** en endpoints con `project_id` o `task_id` protegidos por `require_project_access` cuando el recurso no existe o no pertenece a la sede del actor (Axioma 3 / existence-leak safe).
- **política confirmada**: el rol `Miembro` no existe en el contexto del módulo Projects; no tiene acceso al módulo
- cualquier cambio de granularidad debe romper la suite y abrir decision explicita

## 6. Asimetrias, drift y politicas formalizadas

1. `DELETE /projects/{id}` no responde al contrato canonico de `projects:*`; usa `academy:manage`.
   - **Estado actual** (`PEND-QUALITY-RBAC-ASYMMETRY-001`, cierre
     2026-07-16): **politica confirmada**, no gap. Ver §6.1 abajo.
2. `PUT /projects/{id}/phases` ya está alineado con el docstring.
   - **Estado actual** (`PEND-QUALITY-PHASES-RBAC-001`, cierre 2026-07-16): **gap cerrado**. El guard es `projects:manage`; `Editor` recibe **403**. El test `TestPermissionGranularityGaps::test_editor_blocked_from_put_phases` congela el comportamiento.
3. El baseline `Miembro = 403` es intencionalmente estricto y hoy forma parte del contrato documentado.
4. Si cambia un guard en `projects.py`, deben actualizarse a la vez esta matriz, `PROJECTS_API_CONTRACTS.md` y `tests/test_projects_rbac.py`.

### 6.1 Política de borrado de proyecto (cierre 2026-07-16)

`DELETE /api/projects/{id}` se mantiene deliberadamente bajo
`require_staff_or_admin` (`academy:manage`) y no bajo `projects:edit`. Un
borrado de proyecto arrastra:

- `ProjectTask` (y su cascada de supplies/subtasks/attachments)
- `ProjectMilestone`
- `ProjectPhase`
- `ProjectWikiEditor` (ProjectDocument)
- `ProjectWhiteboard`
- `ProjectComment`
- `ProjectActivityLog`

Es una **operación destructiva de módulo**, no de proyecto. Editor pasa
`PATCH /projects/{id}` (con `projects:edit`) pero recibe **403** en
`DELETE`. La politica queda congelada por
`tests/test_projects_rbac.py::test_delete_project_requires_academy_manage_per_policy`.

## 7. Gate minimo para cambios RBAC en Projects

- `./venv/bin/python scripts/test_projects_quality.py`
- `./venv/bin/python -m pytest -q -o addopts='' tests/test_projects_rbac.py`
- actualizar:
  - `docs/PROJECTS_RBAC_MATRIX.md`
  - `docs/PROJECTS_API_CONTRACTS.md`
  - `docs/PROJECTS_QA_CHECKLIST.md`

## 8. Estado

- `PEND-RBAC-001`: **cerrada el 2026-07-16**.
- la matriz compacta de Projects queda formalizada en este documento el **2026-07-16**.

---

## 9. Hardenings cruzados (defensa en profundidad)

Más allá de los guards explícitos documentados en §4, existen helpers internos en `backend/api/projects.py` que refuerzan Axioma 3 y la integridad de mutaciones. No son permisos por sí mismos, pero documentan cómo se evita drift cross-sede y datos inválidos en operaciones ya autenticadas.

### 9.1 `_assert_assignee_in_sede` (api/projects.py:299-339)

Endurecimiento de Axioma 3 sobre payloads PATCH/POST que llevan `assignee_id`. Sin este check, un actor de `sede_a` podría inyectar un UUID de persona de `sede_b` y el backend lo persistiría silenciosamente. Comportamiento resumido:

- `assignee_id` falsy (`None` o vacío) → silent skip (sin asignado).
- `user_sede = None` (superadmin) → sin filtro de scope.
- En cualquier otro caso: la persona debe existir **AND** pertenecer a la sede del actor. Personas con `sede_id NULL` se tratan como untagged y se bloquean.
- Existence-leak safe: devuelve **404** (nunca `403`) en mismatch.

Aplicado en: `create_project_task`, `update_task` (PATCH flat), `update_project_task` (PATCH nested), `create_subtask`, `update_subtask` (5 callsites total: api/projects.py:725, 988, 1518, 1677, 1734).

### 9.2 `_assert_status_in_project_phases` (api/projects.py:341-401)

Rechaza `task.status` que no pertenezca al set de slugs activos del proyecto. Status code **400** (regla de negocio, no 422 de validación estática). Reglas:

- Slugs soft-deleted (`ProjectPhase.deleted_at IS NOT NULL`) son excluidos por `crud.get_project_phases`; no son asignables.
- `status` vacío o `None` se trata como "no en el payload" (no fuerza valor).
- **Fallback canónico**: si el proyecto no tiene fases activas (fixtures de test que crean proyecto sin pasar por `create_default_phases`), se acepta el set `{todo, in_progress, review, completed}`. Allow-list cerrado, no fallback libre.
- Race window: existe entre el snapshot read y el `setattr(task, "status", ...)` si otra request llama a `set_project_phases` simultáneamente. Mitigaciones (`SELECT … FOR SHARE`, optimistic locking) deferidas hasta que endpoints Kanban necesiten mayor throughput.

Aplicado en: `create_project_task`, `update_task`, `update_project_task`.

### 9.3 `_validate_whiteboard_json` (api/projects.py:403-412)

Rechaza el literal `"undefined"` (bug recurrente donde cliente JS llama a `JSON.stringify(undefined)` por error) y JSON malformado con **400**. Aplicado en `update_project_whiteboard` antes de persistir.

### 9.4 Compat maps internos (api/projects.py:426-444)

Mapeos defensivos aplicados en `_normalize_task_payload` (pre-Pydantic/INSERT) y `_normalize_task_enums` (post-SELECT/UPDATE):

| Campo | Valor legacy | Canónico |
|---|---|---|
| `priority` | `normal` | `medium` |
| `status` | `done` | `completed` |
| `status` | `blocked` | `todo` |
| `status` | `pending` | `todo` |

Estos mappings son **internos** (no se exponen como `BeforeValidator` global). Operan en **dos paths**:

- **INSERT/UPDATE** (vía `_normalize_task_payload`, llamado en `create_project_task`, `update_task`, `update_project_task`, `create_subtask`, `update_subtask`): convierte antes de validar Pydantic.
- **Read response shaping** (vía `_normalize_task_enums`, llamado en `_prepare_task_for_response`, que a su vez alimenta `get_task`, `get_project`, `list_projects`, `list_all_my_tasks`): convierte **después** de SELECT para que el cliente siempre vea el enum canónico.

Cubrir ambos paths garantiza que valores legacy que aún persistan en filas viejas (pre `PEND-STATUS-NORM-001`) se expongan ya normalizados sin requerir DDL inmediato.

### 9.5 `_CANONICAL_PHASE_SLUGS` (api/projects.py:419)

Set fallback `{todo, in_progress, review, completed}` usado por `_assert_status_in_project_phases` cuando el proyecto no tiene filas activas en `project_phases`. Solo aplica en fixtures de test que crean proyecto directamente sin pasar por `create_default_phases`. Producción siempre bootstrap default phases vía `create_project`, por lo que esta rama es defensiva.

---

## 10. Onboarding de roles para desarrolladores

Resumen de políticas que todo desarrollador del módulo Projects debe conocer para no sorprenderse al tocar guards o tests.

### 10.1 Política de borrado de proyectos

- `DELETE /api/projects/{id}` requiere `academy:manage` (`require_staff_or_admin`), NO `projects:edit`.
- Un Editor puede editar un proyecto (`PATCH`) pero **no puede borrarlo**.
- El borrado es soft-delete y arrastra tareas, hitos, fases, wiki, pizarra, comentarios y bitácora.
- Está congelado por `tests/test_projects_rbac.py::test_delete_project_requires_academy_manage_per_policy`.

### 10.2 Política de fases

- `PUT /api/projects/{id}/phases` requiere `projects:manage`.
- El docstring y el guard están alineados: solo `Administrador` y `Gestor` pueden reordenar/renombrar fases.
- `Editor` recibe **403** en este endpoint. El test `TestPermissionGranularityGaps::test_editor_blocked_from_put_phases` congela el comportamiento.

### 10.3 Baseline del rol `Miembro`

- `Miembro` recibe **403** en endpoints de módulo sin `project_id`/`task_id` específico.
- `Miembro` recibe **404** en endpoints con `project_id`/`task_id` protegidos por `require_project_access` cuando el recurso no existe o no pertenece a su sede (Axioma 3 / existence-leak safe).
- **Política confirmada**: el rol `Miembro` no existe en el contexto del módulo Projects. La asignación de tareas/proyectos a una persona es un mecanismo de delegación interna para usuarios que ya tienen acceso al módulo, no una vía de acceso para el rol `Miembro`.
- Cualquier apertura de granularidad debe romper `tests/test_projects_rbac.py` y requerir decisión explícita.

### 10.4 Checklist antes de tocar guards

- [ ] Revisar `tests/test_projects_rbac.py` para entender el baseline.
- [ ] Actualizar `PROJECTS_API_CONTRACTS.md`, `PROJECTS_RBAC_MATRIX.md` y `PROJECTS_QA_CHECKLIST.md` si cambia un guard.
- [ ] Ejecutar `./venv/bin/python scripts/test_projects_quality.py` y `./venv/bin/python -m pytest -q -o addopts='' tests/test_projects_rbac.py`.
