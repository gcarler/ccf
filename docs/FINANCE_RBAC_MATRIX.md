# Matriz RBAC — Módulo Finance

**Actualizado:** 2026-07-18

---

## Permisos

| Acción | Permiso | Roles con acceso |
|---|---|---|
| Ver resumen financiero | `finance:read` | MIEMBRO, EDITOR, GESTOR, ADMIN |
| Ver transacciones | `finance:read` | MIEMBRO, EDITOR, GESTOR, ADMIN |
| Registrar donaciones | `finance:write` | EDITOR, GESTOR, ADMIN |
| Administrar fondos | `finance:manage` | GESTOR, ADMIN |
| Ver reportes administrativos | `finance:manage` | GESTOR, ADMIN |

## Endpoints

| Endpoint | Permiso requerido |
|---|---|
| `GET /finance/summary` | `finance:read` |
| `GET /finance/funds` | `finance:read` |
| `GET /finance/transactions` | `finance:read` |
| `POST /finance/donations` | `finance:write` |
| `GET /finance/admin/funds` | `finance:manage` |
| `POST /finance/admin/funds` | `finance:manage` |
| `PATCH /finance/admin/funds/{id}` | `finance:manage` |
| `DELETE /finance/admin/funds/{id}` | `finance:manage` |
| `GET /finance/impact` | Público |

## Aislamiento multi-tenant

- Todas las transacciones y donaciones están aisladas por `sede_id`
- Usuarios solo ven datos de su sede
- Cross-sede retorna datos vacíos (no error)
