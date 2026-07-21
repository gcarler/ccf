# Contratos API — Módulo Administración

**Actualizado:** 2026-07-21 (refactorización completa)
**Base path:** `/api/admin`
**Router:** `backend/api/admin.py`
**CRUD layer:** `backend/crud/admin.py`
**Schemas:** `backend/schemas/admin.py`

---

## Roles (consolidados)

Los roles se gestionan en un único sistema canónico. Los endpoints `/auth-role-definitions` han sido eliminados y consolidados en `/roles`.

### `GET /api/admin/roles`
Lista todos los roles con conteo de usuarios.
**Respuesta:** `List[AdminRoleRead]` → `[{ id: uuid, nombre: string, permisos: object, users_count: number }]`

### `POST /api/admin/roles`
Crea un nuevo rol. **201**.
**Body:** `AdminRoleCreate` → `{ name/nombre (req), permissions/permisos?: object|list }`
**Respuesta:** `AdminRoleRead`

### `PATCH /api/admin/roles/{role_id}`
Actualiza un rol.
**Body:** `AdminRoleUpdate` → `{ name/nombre?, permissions/permisos? }`
**Respuesta:** `AdminRoleRead`

### `DELETE /api/admin/roles/{role_id}`
Elimina un rol (solo sin usuarios asignados). **204** si ok, **409** si tiene usuarios.

---

## Permisos

### `GET /api/admin/permissions`
Lista permisos disponibles con niveles jerárquicos.
**Respuesta:** `{ permissions: object, modules: object, levels: object }`

---

## Usuarios Auth v3

### `GET /api/admin/users`
**Respuesta:** `List[AdminUserRead]`

### `GET /api/admin/users/{user_id}`
**Respuesta:** `AdminUserRead`

### `POST /api/admin/users` — **201**
**Body:** `AdminUserCreate` → `{ username, email, password (req), first_name, last_name, role, is_active? }`
**Respuesta:** `AdminUserRead`

### `PATCH /api/admin/users/{user_id}`
**Body:** `AdminUserUpdate` → `{ username?, email?, first_name?, last_name?, role?, is_active?, password? }`
**Respuesta:** `AdminUserRead`

### `DELETE /api/admin/users/{user_id}` — desactiva (is_active=false), **204**

### `PATCH /api/admin/users/{user_id}/role?role_id={uuid}`
**Respuesta:** `{ status, new_role, role_id, user: AdminUserRead }`

---

## Permisos de usuario

### `GET /api/admin/users/{user_id}/permissions`
**Respuesta:** `AdminUserPermissionsRead`

### `PUT /api/admin/users/{user_id}/permissions`
**Body:** `AdminUserPermissionSet` → `{ permissions: { "crm": "read", "projects": "manage" } }`
**Respuesta:** `{ status, user_id, override_permissions, effective_permissions }`

---

## Personas

### `GET /api/admin/personas`
Lista personas **filtradas por sede del admin**.
**Respuesta:** `List[AdminPersonaRead]`

---

## Ubicaciones

### `GET /api/admin/locations`
**Respuesta:** `List[AdminLocationRead]`

### `POST /api/admin/locations` — **201**
**Body:** `AdminLocationCreate` → `{ name (req), address?, phone? }`
**Respuesta:** `AdminLocationRead`

### `PATCH /api/admin/locations/{location_id}`
**Body:** `AdminLocationUpdate` → `{ name?, address?, phone?, is_active? }`
**Respuesta:** `AdminLocationRead`

### `DELETE /api/admin/locations/{location_id}` — **204**

---

## Canales sociales

### `GET /api/admin/socials`
**Respuesta:** `List[AdminSocialRead]`

### `POST /api/admin/socials` — **201**
**Body:** `AdminSocialCreate` → `{ platform (req), url (req), is_visible? }`
**Respuesta:** `AdminSocialRead`

### `PATCH /api/admin/socials/{social_id}`
**Body:** `AdminSocialUpdate` → `{ platform?, url?, is_visible? }`
**Respuesta:** `AdminSocialRead`

### `DELETE /api/admin/socials/{social_id}` — **204**

---

## Variables de sistema

### `GET /api/admin/variables`
**Respuesta:** `Dict[str, Any]` (key → value map)

### `POST /api/admin/variables`
**Body:** `AdminVariableCreate` → `{ key, value }`
**Respuesta:** `{ status: "success" }`

### `DELETE /api/admin/variables/{key}` — **204**

---

## Stats

### `GET /api/admin/stats`
**Respuesta:** `AdminStatsRead` → `{ personas, usuarios_activos, donaciones_mes, donantes_mes, personas_nuevas_mes, diezmos_mes, ofrendas_mes }`

---

## Auditoría

### `GET /api/admin/audit?limit=100`
**Respuesta:** `List[Dict]` — audit log entries

---

## Comentarios (moderación)

### `GET /api/admin/comments`
**Respuesta:** `List[AdminCommentRead]`

### `DELETE /api/admin/comments/{comment_id}` — soft delete, **200**

---

## Hitos espirituales

### `GET /api/admin/milestones`
**Respuesta:** `List[AdminMilestoneRead]`

### `POST /api/admin/milestones/award`
**Body:** `AdminMilestoneAward` → `{ persona_id (req), badge_id (req), awarded_by? }`
**Respuesta:** `{ status: "success", awarded: 1 }`

---

## Categorías de donación

### `GET /api/admin/donation-categories`
**Respuesta:** `List[AdminDonationCategoryRead]`

### `POST /api/admin/donation-categories` — **201**
**Body:** `AdminDonationCategoryCreate` → `{ name (req), description? }`
**Respuesta:** `AdminDonationCategoryRead`

### `PATCH /api/admin/donation-categories/{category_id}`
**Body:** `AdminDonationCategoryUpdate` → `{ name?, description?, color_code?, is_active? }`
**Respuesta:** `AdminDonationCategoryRead`

### `DELETE /api/admin/donation-categories/{category_id}` — **204**

---

## Automatizaciones CRM

### `GET /api/admin/automations`
**Respuesta:** `List[AutomationRuleRead]`

### `POST /api/admin/automations`
**Body:** `AutomationRuleCreate` → `{ name (req), trigger_type (req), action_type?, action_payload?, is_active? }`
**Respuesta:** `AutomationRuleRead`

### `PATCH /api/admin/automations/{rule_id}`
**Body:** `AutomationRuleUpdate` → `{ name?, trigger_type?, action_type?, action_payload?, is_active? }`
**Respuesta:** `AutomationRuleRead`

### `DELETE /api/admin/automations/{rule_id}` — soft delete, **200**

---

## Roles modulares granulares

### `GET /api/admin/user-module-roles`
**Respuesta:** `List[AdminModuleRoleRead]`

### `POST /api/admin/user-module-roles`
**Body:** `AdminModuleRoleAssign` → `{ user_id (req), modulo (req), rol_id (req) }`
**Respuesta:** `{ id, user_id, modulo, rol_id, created/updated }`

### `DELETE /api/admin/user-module-roles/{assignment_id}` — **204**

### `GET /api/admin/users-with-roles`
**Respuesta:** `List[AdminUserWithRolesRead]`

---

## Provisionamiento masivo

### `POST /api/admin/provision-accounts`
Crea cuentas para personas con email sin auth_user (max 50/batch). Usa ORM en vez de raw SQL.
**Respuesta:** `AdminProvisionResult` → `{ created, skipped, truncated, errors, accounts, message }`
