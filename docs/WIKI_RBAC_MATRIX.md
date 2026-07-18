# Matriz RBAC — Módulo Wiki

**Actualizado:** 2026-07-18

---

## Permisos

| Acción | Permiso | Roles con acceso |
|---|---|---|
| Leer páginas wiki | `wiki:read` | TODOS los roles autenticados |
| Crear/editar páginas | `wiki:edit` | EDITOR, GESTOR, ADMIN |
| Eliminar páginas | `wiki:edit` | EDITOR, GESTOR, ADMIN |
| Administrar wiki | `wiki:manage` | GESTOR, ADMIN |

## Implementación

Los permisos se validan via `require_module_access("wiki", "...")` en el router.

| Endpoint | Permiso requerido |
|---|---|
| `GET /wiki/pages` | `wiki:read` |
| `GET /wiki/pages/{key}` | `wiki:read` |
| `GET /wiki/pages/{key}/versions` | `wiki:read` |
| `GET /wiki/categories` | `wiki:read` |
| `POST /wiki/pages/{key}` | `wiki:edit` |
| `PATCH /wiki/pages/{key}` | `wiki:edit` |
| `DELETE /wiki/pages/{key}` | `wiki:edit` |

## Aislamiento

- Todo el contenido está aislado por `sede_id`
- Usuarios solo ven páginas de su sede
- Cross-sede retorna 404
