# Matriz RBAC — Módulo Administración

**Actualizado:** 2026-07-21 (refactorización completa)

---

## Roles de plataforma

| Rol | Permisos base |
|---|---|
| **ADMINISTRADOR** | `system:config`, todos los módulos en manage |
| **GESTOR** | Lectura/edición en módulos asignados |
| **EDITOR** | Lectura/escritura en contenido, sin gestión de usuarios |
| **MIEMBRO** | `profile:manage`, `academy:study` |
| **LECTOR** | Solo lectura |

---

## Permisos requeridos por endpoint

### Roles (consolidados)

| Endpoint | Permiso mínimo | Métodos |
|---|---|---|
| `/admin/roles` | `require_admin` (system:config) | GET, POST |
| `/admin/roles/{id}` | `require_admin` | PATCH, DELETE |

### Usuarios

| Endpoint | Permiso mínimo | Métodos |
|---|---|---|
| `/admin/users` | `require_admin` | GET, POST |
| `/admin/users/{id}` | `require_admin` | GET, PATCH, DELETE |
| `/admin/users/{id}/role` | `require_admin` | PATCH |
| `/admin/users/{id}/permissions` | `require_admin` | GET, PUT |
| `/admin/users-with-roles` | `require_admin` | GET |

### Permisos

| Endpoint | Permiso mínimo | Métodos |
|---|---|---|
| `/admin/permissions` | `require_admin` | GET |

### Roles modulares

| Endpoint | Permiso mínimo | Métodos |
|---|---|---|
| `/admin/user-module-roles` | `require_admin` | GET, POST |
| `/admin/user-module-roles/{id}` | `require_admin` | DELETE |

### Lectura general (require_active_user)

| Endpoint | Permiso mínimo | Métodos |
|---|---|---|
| `/admin/locations` | `require_active_user` | GET |
| `/admin/socials` | `require_active_user` | GET |
| `/admin/milestones` | `require_active_user` | GET |
| `/admin/donation-categories` | `require_active_user` | GET |
| `/admin/automations` | `require_active_user` | GET |

### Escritura (require_admin)

| Endpoint | Permiso mínimo | Métodos |
|---|---|---|
| `/admin/locations` | `require_admin` | POST, PATCH, DELETE |
| `/admin/locations/{id}` | `require_admin` | PATCH, DELETE |
| `/admin/socials` | `require_admin` | POST, PATCH, DELETE |
| `/admin/socials/{id}` | `require_admin` | PATCH, DELETE |
| `/admin/variables` | `require_admin` | POST, DELETE |
| `/admin/variables/{key}` | `require_admin` | DELETE |
| `/admin/donation-categories` | `require_admin` | POST, PATCH, DELETE |
| `/admin/donation-categories/{id}` | `require_admin` | PATCH, DELETE |
| `/admin/automations` | `require_admin` | POST |
| `/admin/automations/{id}` | `require_admin` | PATCH, DELETE |
| `/admin/milestones/award` | `require_admin` | POST |
| `/admin/stats` | `require_admin` | GET |
| `/admin/provision-accounts` | `require_admin` | POST |

### Auditoría y moderación

| Endpoint | Permiso mínimo | Métodos |
|---|---|---|
| `/admin/audit` | `require_admin` | GET |
| `/admin/comments` | `require_admin` | GET |
| `/admin/comments/{id}` | `require_admin` | DELETE |

### Multi-tenant

| Regla | Aplicación |
|---|---|
| Sede-scoping | Todas las consultas de personas filtran por `sede_id` del admin |
| Global admin bypass | Super Administrador ve todas las sedes |
| User visibility | `list_admin_users`, `get_admin_user` filtran por sede (excepto global admin) |
| Module roles | `remove_user_module_role` verifica sede del usuario target |

---

## Roles modulares (auth_user_module_roles)

| Módulo | Levels |
|---|---|
| crm | read, edit, manage |
| academy | read, study, edit, manage |
| projects | read, edit, manage |
| finance | read, edit, manage |
| cms | read, edit, manage, publish |
| messaging | read, edit, manage |
| evangelism | read, edit, manage |
