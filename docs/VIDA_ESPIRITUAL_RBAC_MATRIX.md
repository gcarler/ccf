# Matriz RBAC — Vida Espiritual CCF

> **Objetivo:** fijar la matriz RBAC operativa del módulo Vida Espiritual contra el código actual y el estado deseado.

## 1. Taxonomía canónica

| Módulo | Acción | Permission key |
|---|---|---|
| `spiritual_life` | `read` | `spiritual_life:read` |
| `spiritual_life` | `edit` | `spiritual_life:edit` |
| `spiritual_life` | `manage` | `spiritual_life:manage` |

Jerarquía:

- `manage → edit → read`
- `edit → read`

## 2. Roles canónicos

| Rol | Permisos efectivos en Vida Espiritual |
|---|---|
| `Administrador` | `spiritual_life:manage` (acceso total) |
| `Gestor` | `spiritual_life:manage` (acceso total) |
| `Editor` | `spiritual_life:edit` (lectura + mutación) |
| `Lector` | `spiritual_life:read` (solo lectura) |
| `Miembro` | Sin acceso al módulo (o solo lectura de su propia información) |

## 3. Matriz por superficie

| Ruta | Guard esperado | Observación |
|---|---|---|
| `GET /spiritual-life/milestones/{persona_id}` | `spiritual_life:read` | Hoy usa `get_current_user`; debe migrar a `require_module_access("spiritual_life", "read")` |
| `GET /spiritual-life/milestones` | `spiritual_life:read` | Pendiente |
| `POST /spiritual-life/milestones` | `spiritual_life:manage` | Hoy usa `require_admin` (`system:config`); debe migrar |
| `PATCH /spiritual-life/milestones/{id}` | `spiritual_life:edit` | Pendiente |
| `DELETE /spiritual-life/milestones/{id}` | `spiritual_life:edit` | Pendiente |
| `GET /spiritual-life/timeline` | `spiritual_life:read` | Pendiente |
| `GET /spiritual-life/certificates` | `spiritual_life:read` | Pendiente / proxy a Academia |

## 4. Frontend

| Ruta | Permiso mínimo | Observación |
|---|---|---|
| `/plataforma/spiritual-life` | `spiritual_life:read` | Protegido por `WorkspaceLayout` |
| `/plataforma/spiritual-life/timeline` | `spiritual_life:read` | Protegido por layout |
| `/plataforma/spiritual-life/certificates` | `spiritual_life:read` | Protegido por layout |
| `/plataforma/admin/spiritual-life/milestones` | `spiritual_life:manage` | Debe protegerse explícitamente |

## 5. Decisiones de diseño

1. **POST /spiritual-life/milestones** debe usar `spiritual_life:manage`, no `system:config`.
2. **Editor** puede crear/editar/eliminar milestones de personas de su sede.
3. **Gestor/Admin** tienen acceso total.
4. **Miembro** no accede al módulo administrativo; solo ve su propia línea de tiempo si se le habilita en el futuro.
5. Axioma 3: cross-sede debe devolver 404 (existence-leak safe).

## 6. Estado actual vs. deseado

| Aspecto | Actual | Deseado |
|---|---|---|
| Guard GET | `get_current_user` | `spiritual_life:read` |
| Guard POST | `require_admin` | `spiritual_life:manage` |
| Guard PATCH | No existe endpoint | `spiritual_life:edit` |
| Guard DELETE | No existe endpoint | `spiritual_life:edit` |
| Frontend admin | Sin guard explícito | `spiritual_life:manage` |
