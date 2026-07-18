# Contratos API — Módulo Administración

**Actualizado:** 2026-07-18
**Base path:** `/api/admin`
**Router:** `backend/api/admin.py`

---

## Roles

### `GET /api/admin/roles`
Lista todos los roles con conteo de usuarios.

**Respuesta:** `[{ id: uuid, name: string, permissions: object, users_count: number }]`

### `POST /api/admin/roles`
Crea un nuevo rol.

**Body:** `{ name: string (req), permissions?: object }`

### `PATCH /api/admin/roles/{role_id}`
Actualiza permisos de un rol.

**Body:** `{ permissions: object }`

### `DELETE /api/admin/roles/{role_id}`
Elimina un rol (solo sin usuarios asignados). **204** si ok, **409** si tiene usuarios.

---

## Permisos

### `GET /api/admin/permissions`
Lista permisos disponibles con niveles jerárquicos.

---

## Usuarios Auth v3

### `GET /api/admin/users`
### `GET /api/admin/users/{user_id}`
### `POST /api/admin/users`
**Body:** `{ username, email, password (req), first_name?, last_name?, role? }`
### `PATCH /api/admin/users/{user_id}`
**Body:** `{ username?, email?, password?, is_active?, role?, role_id?, rol_plataforma_id? }`
### `DELETE /api/admin/users/{user_id}` → desactiva (is_active=false), **204**
### `PATCH /api/admin/users/{user_id}/role?role_id={uuid}`

---

## Permisos de usuario

### `GET /api/admin/users/{user_id}/permissions`
### `PUT /api/admin/users/{user_id}/permissions`
**Body:** `{ "crm": "read", "projects": "manage", "academy": "study" }`

---

## Personas

### `GET /api/admin/personas`
Lista personas **filtradas por sede del admin**.

---

## Ubicaciones

### `GET /api/admin/locations`
### `POST /api/admin/locations`
**Body:** `{ nombre (req), address?, pastor?, type? }`

---

## Canales sociales

### `GET /api/admin/socials`

---

## Variables de sistema

### `GET /api/admin/variables`
### `POST /api/admin/variables`
**Body:** `{ key: string, value: string }`

---

## Stats

### `GET /api/admin/stats`
**Respuesta:** `{ personas, usuarios_activos, donaciones_mes, donantes_mes, personas_nuevas_mes, diezmos_mes, ofrendas_mes }`

---

## Auditoría

### `GET /api/admin/audit?limit=100`

---

## Comentarios (moderación)

### `GET /api/admin/comments`
### `DELETE /api/admin/comments/{comment_id}` → soft delete

---

## Hitos espirituales

### `GET /api/admin/milestones`
### `POST /api/admin/milestones/award`
**Body:** `{ badge_id, persona_ids: [uuid] }`

---

## Categorías de donación

### `GET /api/admin/donation-categories`
### `POST /api/admin/donation-categories`
**Body:** `{ nombre (req), descripcion?, color? }`

---

## Automatizaciones CRM

### `GET /api/admin/automations`
### `POST /api/admin/automations`
**Body (AutomationRuleCreate):** `{ name (req), trigger_type (req), action_type?, action_payload?, is_active? }`
### `PATCH /api/admin/automations/{rule_id}`
**Body (AutomationRuleUpdate):** `{ name?, trigger_type?, action_type?, action_payload?, is_active? }`
### `DELETE /api/admin/automations/{rule_id}` → soft delete

---

## Roles modulares granulares

### `GET /api/admin/auth-role-definitions`
### `POST /api/admin/auth-role-definitions`
**Body:** `{ nombre (req), permisos? }`
### `PATCH /api/admin/auth-role-definitions/{role_id}`
**Body:** `{ nombre?, permisos? }`
### `DELETE /api/admin/auth-role-definitions/{role_id}` → **204** o **409** si tiene usuarios

### `GET /api/admin/user-module-roles`
### `POST /api/admin/user-module-roles`
**Body:** `{ user_id (req), modulo (req), rol_id (req) }`
### `DELETE /api/admin/user-module-roles/{assignment_id}` → **204**

### `GET /api/admin/users-with-roles`

---

## Provisionamiento masivo

### `POST /api/admin/provision-accounts`
Crea cuentas para personas con email sin auth_user.
**Respuesta:** `{ created, skipped, errors, accounts: [{ email, username, temp_password }] }`
