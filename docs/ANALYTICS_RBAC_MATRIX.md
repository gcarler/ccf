# RBAC Matrix — Analytics

**Creado:** 2026-07-26

---

## Roles y permisos

| Endpoint | Pastor | Admin | Otros |
|---|---|---|---|
| `GET /api/analytics/radar` | ✅ Allow | ✅ Allow | ❌ 403 |
| `GET /api/analytics/dashboard-metrics` | ✅ Allow | ✅ Allow | ❌ 403 |
| `GET /api/analytics/events/summary` | ✅ Allow | ✅ Allow | ❌ 403 |

## Guard utilizado

`require_pastor_or_admin` — permite acceso a usuarios con rol PASTOR o ADMIN (permiso `system:config`).

## Multi-tenant

El scope por sede se aplica en todos los endpoints vía `crud.get_user_sede_id(db, current_user.id)`.
