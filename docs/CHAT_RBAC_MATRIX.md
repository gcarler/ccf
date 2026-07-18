# Matriz RBAC — Módulo Chat

**Actualizado:** 2026-07-18

---

## Permisos

| Acción | Permiso | Roles con acceso |
|---|---|---|
| Leer conversaciones propias | `chat:read` | MIEMBRO, EDITOR, GESTOR, ADMIN |
| Enviar mensajes | `chat:write` | MIEMBRO, EDITOR, GESTOR, ADMIN |
| Administrar conversaciones | `chat:manage` | GESTOR, ADMIN |
| Ver todas las conversaciones (sede) | `chat:admin` | ADMIN |

## Aislamiento

- Usuarios solo ven conversaciones donde son participantes
- Admin puede ver conversaciones de su sede
- Cross-sede retorna 404
