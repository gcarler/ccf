# Matriz RBAC — Módulo Administración

**Actualizado:** 2026-07-18

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

| Endpoint | Permiso mínimo | Método |
|---|---|---|
| `/admin/*` (escritura) | `system:config` o rol ADMINISTRADOR | POST/PUT/PATCH/DELETE |
| `/admin/*` (lectura) | `system:config` o rol ADMINISTRADOR | GET |
| `/admin/locations` | `require_active_user` (lectura) | GET |
| `/admin/socials` | `require_active_user` (lectura) | GET |
| `/admin/milestones` | `require_active_user` (lectura) | GET |
| `/admin/donation-categories` | `require_active_user` (lectura) | GET |
| `/admin/automations` | `require_active_user` (lectura) | GET |
| `/admin/users/*` | `system:config` o ADMINISTRADOR | Todos |
| `/admin/roles/*` | `system:config` o ADMINISTRADOR | Todos |
| `/admin/variables` | `require_admin` | Todos |
| `/admin/stats` | `require_admin` | GET |
| `/admin/provision-accounts` | `require_admin` | POST |

---

## Roles modulares (auth_user_module_roles)

Los roles modulares permiten asignar permisos granulares por módulo. Por ejemplo, un usuario puede ser GESTOR en CRM pero MIEMBRO en Academy.

| Módulo | Levels |
|---|---|
| crm | read, edit, manage |
| academy | read, study, edit, manage |
| projects | read, edit, manage |
| finance | read, edit, manage |
| cms | read, edit, manage, publish |
| messaging | read, edit, manage |
| evangelism | read, edit, manage |
| community | read, edit, manage |
| spiritual_life | read, edit, manage |

---

## Override de permisos

Los permisos personalizados se almacenan en un rol `PERSONALIZADO_{USER_ID}` para no modificar roles compartidos. `profile:manage` siempre se preserva. `system:config` se preserva si el usuario ya lo tenía (evita lockout).
