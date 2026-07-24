# Matriz RBAC — CRM CCF

> **Contexto:** Este documento detalla la matriz de permisos. Para la visión general de arquitectura, reglas de negocio y flujos del CRM, ver **[docs/CRM_ARCHITECTURE.md](CRM_ARCHITECTURE.md)**.

## 1. Proposito

Este documento fija la matriz RBAC operativa de CRM contra el código actual. No define un ideal; documenta lo que hoy protegen los routers y dónde existen asimetrías o huecos.

## 2. Fuente de verdad inspeccionada

- `backend/api/crm/personas.py`
- `backend/api/crm/persona_relations.py`
- `backend/api/crm/pastoral.py`
- `backend/api/crm/pipelines.py`
- `backend/api/crm/resources.py`
- `backend/core/permissions.py`
- `backend/management/seed_user_permissions.py`

Fecha de lectura: `2026-07-16`

## 3. Niveles de permiso CRM

Permisos canónicos:

- `crm:read`
- `crm:edit`
- `crm:manage`

Jerarquía efectiva en `permissions.py`:

- `crm:manage` incluye `crm:edit` y `crm:read`
- `crm:edit` incluye `crm:read`

Observación clave:

- los routers CRM revisados no usan `require_module_access("crm", "manage")` como guard directo
- buena parte del módulo se divide en `crm:read` y `crm:edit`
- pipeline/kanban usa otra vía: `require_pastor_or_admin`

## 4. Matriz por rol canónico

### 4.1. Roles persistidos sembrados (`RolPlataforma`)

Contrato observado en `seed_user_permissions.py`:

| Rol | CRM efectivo esperado |
|---|---|
| `ADMINISTRADOR` | `crm:manage` |
| `GESTOR` | `crm:manage` |
| `EDITOR` | `crm:edit` |
| `LECTOR` | `crm:read` |
| `MIEMBRO` | sin permisos CRM |

### 4.2. Fallback runtime (`DEFAULT_ROLES`)

Contrato observado en `permissions.py`:

| Rol fallback | CRM efectivo esperado |
|---|---|
| `Administrador` | `crm:manage` |
| `Gestor` | `crm:manage` |
| `Editor` | `crm:edit` |
| `Lector` | sin permisos CRM; solo `academy:study` + `profile:manage` |
| `Miembro` | sin permisos CRM; solo `academy:study` + `profile:manage` |

Asimetría documentada:

- `LECTOR` persistido sí recibe `crm:read`
- `Lector` fallback runtime no recibe CRM

Esto significa que un usuario sin `RolPlataforma` persistido puede resolver distinto al contrato sembrado. No es ruido; es drift real de permisos.

## 5. Matriz por superficie CRM

| Superficie | Guard observado | Roles que pasan hoy |
|---|---|---|
| Personas, relaciones, timeline, donations, mentor candidates | `require_module_access("crm", "read")` | `ADMINISTRADOR`, `GESTOR`, `EDITOR`, `LECTOR` persistido |
| Crear/editar/borrar personas y asignar mentoría | `require_module_access("crm", "edit")` | `ADMINISTRADOR`, `GESTOR`, `EDITOR` |
| `PATCH /personas/me/profile` | `require_permission("profile:manage")` | cualquier rol autenticado con perfil propio |
| Casos, tasks, counseling, messaging history, prayer, volunteers, analytics, groups de solo lectura | `require_module_access("crm", "read")` | `ADMINISTRADOR`, `GESTOR`, `EDITOR`, `LECTOR` persistido |
| Mutaciones de casos, tasks, counseling, messaging send, prayer, volunteers, roles/settings CRM | `require_module_access("crm", "edit")` | `ADMINISTRADOR`, `GESTOR`, `EDITOR` |
| Recursos, plantillas, bitácora, automations resource-bank lectura | `require_module_access("crm")` o `require_module_access("crm", "read")` | `ADMINISTRADOR`, `GESTOR`, `EDITOR`, `LECTOR` persistido |
| Mutaciones de recursos, campañas, envíos, automations resource-bank | `require_module_access("crm", "edit")` | `ADMINISTRADOR`, `GESTOR`, `EDITOR` |
| Pipelines, stages, reorder, kanban y gran parte de scenarios pipeline | `require_pastor_or_admin` | solo roles que el helper trate como pastor/admin |

## 6. Excepcion mayor: pipeline no sigue la jerarquía CRM estándar

El subrouter `backend/api/crm/pipelines.py` no usa la misma matriz que personas/pastoral/resources para sus operaciones principales.

Superficies afectadas:

- `/pipelines*`
- `/pipeline-stages*`
- `/pipeline/casos/reorder`
- `/pipeline/kanban/*`
- varios `/scenarios/*`

Guard observado:

- `require_pastor_or_admin`

Implicación:

- tener `crm:read`, `crm:edit` o incluso `crm:manage` no prueba por sí solo acceso al pipeline
- la decisión final depende del helper `require_pastor_or_admin`
- CRM hoy no tiene una sola política RBAC homogénea en todas sus áreas

## 7. Endpoints auxiliares de automations (estado actual)

Revisado el `2026-07-24`: todos los endpoints auxiliares de automations en `backend/api/crm/pipelines.py` cuentan con guard explícito de auth/RBAC.

- Lectura de variables y catálogos: `require_module_access("crm", "read")`
- Validaciones y mutaciones de flujos: `require_module_access("crm", "edit")`
- Drag & drop de kanban: `require_pastor_or_admin` (coherente con el resto del módulo pipeline)

La lista histórica de endpoints sin guard ya fue cerrada. Queda documentada como referencia de la superficie protegida, no como deuda activa.

## 8. Reglas operativas para QA

Validar mínimo:

1. `ADMINISTRADOR` entra a todo CRM
2. `GESTOR` y `EDITOR` pasan personas, tasks, counseling y resources según `crm:read/edit`
3. `LECTOR` persistido solo lectura en superficies estándar CRM
4. `MIEMBRO` no debe entrar a superficies administrativas CRM
5. pipeline/kanban debe probarse aparte porque su gate no es el mismo
6. helpers de automations deben revisarse explícitamente si se tocan

## 9. Estado

- `PEND-RBAC-CRM-001` queda cerrada el `2026-07-16` como documentación de contrato actual
- se abre deuda técnica visible sobre drift de guards pipeline y helpers sin auth explícita
