# Arquitectura del Módulo Admin — Plataforma CCF

**Versión:** 2026-07-24
**Ruta base frontend:** `/plataforma/admin`
**Ruta base API:** `/api/admin`
**Router backend:** `backend/api/admin.py`
**Módulo CRUD:** `backend/crud/admin.py`
**Schemas:** `backend/schemas/admin.py`

---

## 1. Propósito y Alcance

El **módulo Admin** es el centro de control de la plataforma CCF. Su responsabilidad principal es:

- Gestionar **usuarios** de la plataforma (`auth_users`).
- Gestionar **roles de plataforma** (`RolPlataforma`) y sus permisos.
- Asignar **permisos granulares** por módulo a través de roles modulares (`UsuarioRolModulo`) y overrides personales (`UsuarioPermisoOverride`).
- Administrar configuración transversal: sedes, canales sociales, variables de sistema, categorías de donación, hitos espirituales, automatizaciones y auditoría.
- Proveer un punto central para moderación de contenido (comentarios del foro) y provisionamiento masivo de cuentas.

> **Regla de oro:**
> - Cualquier operación de **escritura** en el módulo Admin requiere `system:config` (rol `ADMINISTRADOR` o `Super administrador`).
> - Las operaciones de **lectura administrativa** (`/permissions`, `/audit`, `/users`, `/stats`, `/comments`, etc.) también requieren `system:config`.
> - Solo algunas listas públicas/consultivas (`/locations`, `/socials`, `/milestones`, `/donation-categories`, `/automations`) usan `require_active_user`.

---

## 2. Visión General de Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                  │
│              /plataforma/admin/*                            │
│  ├─ page.tsx      → Dashboard con KPIs y tareas de agentes │
│  ├─ users/        → CRUD de usuarios auth v3                │
│  ─ roles/        → Roles de plataforma y permisos          │
│  ├─ access/       → Asignación de permisos granulares       │
│  ├─ settings/     → Sedes, redes, variables, perfil       │
│  └─ ...                                           │
└───────────────────────────┬─────────────────────────────────┘
                            │ API REST /api/admin
┌───────────────────────────▼─────────────────────────────────┐
│                        Backend (FastAPI)                    │
│              backend/api/admin.py                            │
│  ├─ /roles, /users, /permissions                           │
│  ─ /locations, /socials, /variables                      │
│  ─ /user-module-roles, /users-with-roles                  │
│  └─ /automations, /audit, /comments, ...                 │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                  Lógica de Negocio (CRUD)                  │
│              backend/crud/admin.py                          │
│  ├─ Gestión de roles, usuarios, permisos                   │
│  ├─ Sede-scoping de usuarios y personas                     │
│  └─ Provisionamiento masivo de cuentas                      │
└────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                        Base de Datos                        │
│  PostgreSQL + SQLAlchemy ORM                                │
│  ├─ auth_users, auth_roles, auth_user_module_roles        │
│  ├─ auth_user_permission_overrides                         │
│  ├─ church_locations, social_channels, system_variables    │
│  └─ admin_audit_logs, automation_rules, ...                │
└─────────────────────────────────────────────────────────────┘
```

### Dependencias Clave

| Archivo | Propósito |
|---|---|
| `backend.core.permissions` | Taxonomía de permisos, guards `require_admin`, `require_active_user`, resolución de permisos efectivos |
| `backend.models_auth` | `Usuario`, `RolPlataforma`, `UsuarioRolModulo`, `UsuarioPermisoOverride` |
| `backend.models_crm` | `Persona` |
| `backend.models_ops` | `ChurchLocation`, `SocialChannel`, `SystemVariable` |
| `backend.models_governance` | `AdminAuditLog`, `AutomationRule` |
| `backend.core.audit` | `record_admin_action` |

---

## 3. Organización del Código

### Backend

```
backend/
├── api/admin.py              # Router FastAPI con ~39 endpoints
├── crud/admin.py             # Lógica de negocio del Admin
├── schemas/admin.py          # Schemas Pydantic typed
├── models_auth.py            # Modelos de autenticación y roles
├── core/permissions.py       # Sistema de permisos y guards
└── core/audit.py             # Registro de acciones de admin
```

### Frontend

```
frontend/src/app/plataforma/admin/
├── page.tsx                  # Dashboard principal
├── layout.tsx                # Sidebar con navegación por secciones
├── access/                   # Gestión granular de permisos
├── users/                    # Usuarios
├── roles/                    # Roles de plataforma
├── settings/                 # Configuración (sedes, redes, variables, perfil)
├── personas/                 # Personas de la sede
├── audit/                    # Auditoría
├── comments/                 # Moderación de foro
├── milestones/               # Hitos espirituales
├── donation-categories/      # Categorías de donación
├── automations/              # Reglas de automatización
└── ...                       # Otros módulos administrativos
```

---

## 4. Modelo de Datos y Entidades Clave

### 4.1 Usuario (`Usuario` — `auth_users`)

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | UUID | FK a `personas.id` (1:1) |
| `sede_id` | UUID | Sede a la que pertenece el usuario |
| `username` | CITEXT | Único, case-insensitive |
| `email` | CITEXT | Único |
| `password_hash` | str | Hash de contraseña |
| `rol_plataforma_id` | UUID | Rol de plataforma base |
| `is_active` | bool | Soft-delete lógico |
| `xp` | int | Puntos de experiencia / gamificación |

**Relaciones importantes:**
- `Usuario.persona` → `Persona`
- `Usuario.rol_plataforma` → `RolPlataforma`
- `Usuario.roles_modulares` → `[UsuarioRolModulo]`
- `Usuario.permiso_override` → `UsuarioPermisoOverride`

### 4.2 Rol de Plataforma (`RolPlataforma` — `auth_roles`)

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | UUID | UUID v4 |
| `nombre` | str | Nombre único (ej. `ADMINISTRADOR`) |
| `permisos` | JSON | Mapa `{ "crm:read": "allow", ... }` |
| `deleted_at` | datetime | Soft-delete |

Los roles de plataforma son **compartidos** entre usuarios. Un rol puede tener permisos de cualquier módulo, pero por convención se usan para representar roles transversales (ADMINISTRADOR, GESTOR, EDITOR, MIEMBRO, LECTOR).

### 4.3 Rol Modular (`UsuarioRolModulo` — `auth_user_module_roles`)

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | UUID | UUID v4 |
| `user_id` | UUID | FK a `auth_users.id` |
| `modulo` | str | Nombre del módulo (`crm`, `academy`, etc.) |
| `rol_id` | UUID | FK a `auth_roles.id` |
| `deleted_at` | datetime | Soft-delete |

Permite asignar a un usuario un rol específico para un módulo concreto. La tabla de roles (`auth_roles`) es la misma que para roles de plataforma; la diferencia semántica es quién la consume.

### 4.4 Override de Permisos (`UsuarioPermisoOverride`)

| Campo | Tipo | Descripción |
|---|---|---|
| `user_id` | UUID | FK única a `auth_users.id` |
| `permisos` | JSON | Mapa de permisos adicionales o restrictivos |

Se utiliza cuando un administrador asigna permisos modulares directamente a un usuario sin crear un rol ad-hoc. No reemplaza el rol de plataforma; se **suma** a él.

### 4.5 Entidades de Configuración

| Entidad | Tabla | Descripción |
|---|---|---|
| `ChurchLocation` | `church_locations` | Sedes / anexos de la iglesia (accesible vía `from backend import models`) |
| `SocialChannel` | `social_channels` | Redes sociales oficiales |
| `SystemVariable` | `system_variables` | Variables globales de sistema |
| `DonationCategory` | `donation_categories` | Categorías de recaudación |
| `Medalla` / `MedallaUsuario` | `auth_badges` / `auth_user_badges` | Hitos espirituales |
| `AutomationRule` | `automation_rules` | Reglas de automatización pastoral |
| `AdminAuditLog` | `admin_audit_logs` | Trazabilidad de acciones de admin |

---

## 5. Reglas de Negocio Centrales

### 5.1 Jerarquía de Permisos y Resolución

La resolución de permisos efectivos de un usuario sigue este orden:

1. **Admin bypass:** si el rol normalizado es `admin` / `administrador` / `super administrador`, se otorgan todos los permisos.
2. **Permisos del rol de plataforma:** se leen de `RolPlataforma.permisos`.
3. **Permisos de roles modulares:** se recorren las asignaciones activas (`UsuarioRolModulo`) y se añaden los permisos del rol asignado cuya clave comience con `{modulo}:`.
4. **Override personal:** se fusionan los permisos de `UsuarioPermisoOverride`.
5. **Defaults canónicos:** si no hay permisos previos, se usa `DEFAULT_ROLES` en `backend/core/permissions.py`.

### 5.2 Niveles de Permiso por Módulo

```python
PERMISSION_LEVELS = {
    "read": {"read"},
    "edit": {"read", "edit"},
    "manage": {"read", "edit", "manage"},
}
```

Un nivel superior **implica** los inferiores. Por ejemplo, `crm:manage` implica `crm:edit` y `crm:read`.

### 5.3 Roles de Plataforma Canónicos (`DEFAULT_ROLES`)

| Rol | Permisos base |
|---|---|
| **Super administrador** | `system:config` + todos los módulos en `manage` |
| **Administrador** | Todos los módulos en `manage` |
| **Gestor** | `crm`, `projects`, `academy` en `manage`; `messaging:edit` |
| **Editor** | `crm`, `projects`, `academy` en `edit`; `messaging:edit` |
| **Miembro / Lector / Estudiante / Aspirante** | `academy:study`, `profile:manage` |

### 5.4 Guards y Dependencias FastAPI

| Guard | Permiso requerido | Uso típico |
|---|---|---|
| `require_admin` | `system:config` | Escritura en Admin |
| `require_active_user` | Usuario autenticado activo | Lectura general |
| `require_module_access(module, level)` | Permiso del módulo | Otros módulos de la plataforma |

### 5.5 Sede-Isolation

- Los usuarios de Admin solo pueden ver/modificar usuarios y personas de su misma `sede_id`.
- El **Super administrador** (`Super administrador` / `superadmin`) ve todas las sedes. Esta lógica se implementa en `backend/crud/admin.py` mediante el helper `_is_global_admin(user)`.
- `list_admin_users`, `get_admin_user`, `change_user_role`, etc., aplican `_visible_auth_users_query`.
- `remove_user_module_role` hace join con `Usuario` para verificar `sede_id`.

### 5.6 Soft Delete y Eliminación de Roles

- Roles, sedes, canales, variables y categorías usan `deleted_at` para borrado lógico.
- Un rol solo puede eliminarse si **no tiene usuarios activos** ni asignaciones modulares activas; de lo contrario se retorna `409 Conflict`.
- Al soft-deletear un rol o variable, se renombra su clave/nombre único para permitir reutilización futura.

> **Nota sobre documentación histórica:** `docs/MODULO_ADMIN.md` documentaba dos problemas que ya fueron resueltos:
> - `GET /api/admin/personas` ahora filtra por `sede_id` del administrador.
> - `POST /api/admin/variables` ahora acepta body JSON (`AdminVariableCreate`) en lugar de query params.
> Este documento (`ADMIN_ARCHITECTURE.md`) refleja el estado actual del código.

### 5.7 Provisionamiento Masivo

- `POST /api/admin/provision-accounts` crea cuentas `auth_users` para personas con email que aún no tengan usuario.
- Límite: 50 por llamada (`batch_limit`).
- Genera contraseñas temporales aleatorias de 12 caracteres.
- Username: prefijo del email normalizado; si hay colisión, se añade sufijo numérico.
- Rol por defecto: `MIEMBRO`.

---

## 6. Contratos de API por Área

### 6.1 Roles de Plataforma

```
GET    /api/admin/roles              → PaginatedResponse[AdminRoleRead]
POST   /api/admin/roles              → AdminRoleRead (201)
PATCH  /api/admin/roles/{role_id}    → AdminRoleRead
DELETE /api/admin/roles/{role_id}    → 204 (o 409 si tiene usuarios)
```

### 6.2 Usuarios

```
GET    /api/admin/users              → PaginatedResponse[AdminUserRead]
GET    /api/admin/users/{user_id}    → AdminUserRead
POST   /api/admin/users              → AdminUserRead (201)
PATCH  /api/admin/users/{user_id}    → AdminUserRead
DELETE /api/admin/users/{user_id}    → 204 (desactiva is_active)
PATCH  /api/admin/users/{user_id}/role → { status, new_role, role_id, user }
```

### 6.3 Permisos y Roles Modulares

```
GET    /api/admin/permissions                 → { permissions, modules, levels }
GET    /api/admin/users/{id}/permissions    → AdminUserPermissionsRead
PUT    /api/admin/users/{id}/permissions    → { status, override_permissions, effective_permissions }
GET    /api/admin/user-module-roles         → PaginatedResponse[AdminModuleRoleRead]
POST   /api/admin/user-module-roles         → { id, user_id, modulo, rol_id }
DELETE /api/admin/user-module-roles/{id}   → 204
GET    /api/admin/users-with-roles          → PaginatedResponse[AdminUserWithRolesRead]
```

### 6.4 Configuración

```
GET    /api/admin/locations             → PaginatedResponse[AdminLocationRead]
POST   /api/admin/locations             → AdminLocationRead (201)
PATCH  /api/admin/locations/{id}        → AdminLocationRead
DELETE /api/admin/locations/{id}        → 204

GET    /api/admin/socials               → PaginatedResponse[AdminSocialRead]
POST   /api/admin/socials               → AdminSocialRead (201)
PATCH  /api/admin/socials/{id}          → AdminSocialRead
DELETE /api/admin/socials/{id}          → 204

GET    /api/admin/variables             → { key: value }
POST   /api/admin/variables             → { status: "success" }
DELETE /api/admin/variables/{key}      → 204
```

### 6.5 Auditoría, Moderación y Automatizaciones

```
GET    /api/admin/audit?limit=...       → list[dict]
GET    /api/admin/comments              → PaginatedResponse[AdminCommentRead]
DELETE /api/admin/comments/{id}        → { status: "success" }
GET    /api/admin/milestones            → PaginatedResponse[AdminMilestoneRead]
POST   /api/admin/milestones/award      → { status, awarded }
GET    /api/admin/donation-categories   → PaginatedResponse[AdminDonationCategoryRead]
POST   /api/admin/donation-categories   → AdminDonationCategoryRead (201)
GET    /api/admin/automations           → PaginatedResponse[AutomationRuleRead]
POST   /api/admin/automations           → AutomationRuleRead
PATCH  /api/admin/automations/{id}      → AutomationRuleRead
DELETE /api/admin/automations/{id}      → { status: "success" }
POST   /api/admin/provision-accounts    → AdminProvisionResult
GET    /api/admin/stats                 → AdminStatsRead
```

---

## 7. Sistema de Permisos Granulares en Detalle

### 7.1 Taxonomía de Permisos

Los permisos canónicos tienen la forma `modulo:nivel`:

```
crm:read, crm:edit, crm:manage
finance:read, finance:edit, finance:manage
projects:read, projects:edit, projects:manage
cms:read, cms:edit, cms:manage
academy:read, academy:study, academy:edit, academy:manage
evangelism:read, evangelism:edit, evangelism:manage
community:read, community:edit, community:manage
spiritual_life:read, spiritual_life:edit, spiritual_life:manage
wiki:read, wiki:edit
messaging:read, messaging:edit
system:config
profile:manage
```

### 7.2 Mapeo Módulo → Niveles (`MODULE_PERMISSION_MAP`)

```python
MODULE_PERMISSION_MAP = {
    "crm": {"read": "crm:read", "edit": "crm:edit", "manage": "crm:manage"},
    "finance": {"read": "finance:read", "edit": "finance:edit", "manage": "finance:manage"},
    "projects": {"read": "projects:read", "edit": "projects:edit", "manage": "projects:manage"},
    "cms": {"read": "cms:read", "edit": "cms:edit", "manage": "cms:manage"},
    "academy": {"read": "academy:read", "study": "academy:study", "edit": "academy:edit", "manage": "academy:manage"},
    "messaging": {"read": "messaging:read", "edit": "messaging:edit"},
    "evangelism": {"read": "evangelism:read", "edit": "evangelism:edit", "manage": "evangelism:manage"},
    "community": {"read": "community:read", "edit": "community:edit", "manage": "community:manage"},
    "spiritual_life": {"read": "spiritual_life:read", "edit": "spiritual_life:edit", "manage": "spiritual_life:manage"},
    "wiki": {"read": "wiki:read", "edit": "wiki:edit", "manage": "wiki:edit"},
}
```

### 7.3 Asignación de Permisos por Módulo

El endpoint `PUT /api/admin/users/{user_id}/permissions` recibe:

```json
{
  "crm": "manage",
  "academy": "study",
  "projects": "read"
}
```

`set_user_permissions` expande cada par a los permisos concretos usando `expand_module_permissions` y los guarda en `UsuarioPermisoOverride`. El rol de plataforma original **no se modifica**.

### 7.4 Asignación de Roles Modulares

El endpoint `POST /api/admin/user-module-roles` recibe:

```json
{
  "user_id": "uuid",
  "modulo": "crm",
  "rol_id": "uuid"
}
```

Requisitos del CRUD:
- El usuario destino debe estar visible para el admin actual.
- El rol debe existir.
- El rol debe contener **al menos un permiso** del módulo asignado.
- Si ya existe una asignación para ese módulo, se actualiza (upsert lógico por soft-delete).

---

## 8. Frontend: Estructura y Flujo de Datos

### 8.1 Layout y Navegación

`frontend/src/app/plataforma/admin/layout.tsx` define el `SIDEBAR_SECTIONS`, una estructura de navegación agrupada por secciones administrativas. La barra lateral permite acceso rápido a:

- Dashboard
- Usuarios y roles
- Permisos / acceso
- Configuración (sedes, redes, variables)
- Finanzas, donaciones, contenido académico, etc.

### 8.2 Dashboard Principal

`frontend/src/app/plataforma/admin/page.tsx` muestra:

- KPIs de plataforma (personas, usuarios activos, donaciones del mes).
- Tareas de agentes AI y testimonios pendientes.
- Paneles de insights con `ViewSwitcher` (grid/list).

### 8.3 Patrón de Autenticación

Todas las páginas del Admin usan el hook `useAuth()` para obtener el `token`. Las peticiones al backend se hacen mediante el cliente API canónico de la plataforma con el header `Authorization: Bearer <token>`.

### 8.4 Convenciones de UI

- `ViewSwitcher` para alternar entre vistas grid/list.
- `AdminShell` y `AdminHero` como componentes de layout compartidos (aunque `AdminHero` está poco utilizado).
- `useToast()` para notificaciones.

---

## 9. Testing y QA

### 9.1 Archivos de Tests

| Archivo | Enfoque |
|---|---|
| `tests/test_admin_coverage.py` | Suite amplia con clases por área funcional |
| `tests/test_admin_refactored.py` | Tests refactorizados del CRUD de Admin |
| `tests/test_admin_users_uuid.py` | CRUD de usuarios con UUID |
| `tests/test_admin_roles_uuid.py` | CRUD de roles con UUID |
| `tests/test_admin_personas_uuid.py` | Listado de personas |
| `tests/test_admin_milestones_uuid.py` | Asignación de insignias |
| `tests/test_admin_automations.py` | Automatizaciones |

### 9.2 Validaciones Recomendadas

```bash
# Tests del módulo Admin
cd /root/ccf && ./venv/bin/python -m pytest tests/test_admin*.py -q

# Lint / pyflakes
cd /root/ccf && ./venv/bin/python -m pyflakes backend/api/admin.py backend/crud/admin.py backend/schemas/admin.py
```

---

## 10. Guía Operativa para Agentes

### 10.1 Cómo Agregar un Nuevo Endpoint de Admin

1. Añadir la función en `backend/crud/admin.py` (lógica de negocio + sede-scoping).
2. Añadir schemas en `backend/schemas/admin.py` si es necesario.
3. Registrar el endpoint en `backend/api/admin.py` con el guard correcto (`require_admin` para escritura, `require_active_user` para lectura pública).
4. Registrar la acción de auditoría con `record_admin_action` si es una operación de escritura.
5. Agregar/actualizar tests en `tests/test_admin_*.py`.

### 10.2 Semilla de Roles por Defecto

Para crear los roles de plataforma canónicos en una instalación nueva, ejecutar:

```bash
cd /root/ccf
PYTHONPATH=/root/ccf python backend/management/seed_user_permissions.py
```

Este script crea `ADMINISTRADOR`, `GESTOR`, `EDITOR`, `LECTOR` y `MIEMBRO` con los permisos definidos en `DEFAULT_ROLES` / `MODULE_PERMISSION_MAP`.

### 10.2 Cómo Agregar un Nuevo Módulo al Sistema de Permisos

1. Añadir entradas en `PERMISSIONS` en `backend/core/permissions.py`.
2. Añadir el módulo y sus niveles en `MODULE_PERMISSION_MAP`.
3. Opcionalmente añadir el módulo a `DEFAULT_ROLES`.
4. Actualizar la UI de permisos en `frontend/src/app/plataforma/admin/access/`.

### 10.3 Gotchas y Convenciones

- **No confundir rol de plataforma con rol modular:** la misma tabla `auth_roles` se usa para ambos, pero semánticamente son distintos.
- **Los nombres de roles se normalizan:** el CRUD usa `ROLE_ALIASES` para mapear aliases (ej. `admin` → `ADMINISTRADOR`).
- **Sede-scoping:** siempre usar `_visible_auth_users_query` / `_visible_auth_user` para no exponer usuarios de otras sedes.
- **Permisos efectivos:** usar `get_user_effective_permissions(db, user)` para obtener el set final de permisos.
- **Soft-delete:** no usar `.delete()`; asignar `deleted_at = _utcnow()`.
- **UUIDs:** los endpoints reciben `role_id`, `user_id`, etc., como strings y los convierten a `uuid.UUID` internamente.

---

## 11. Referencias Cruzadas

- `docs/MODULO_ADMIN.md` — Documentación operativa y contratos de API detallados.
- `docs/ADMIN_RBAC_MATRIX.md` — Matriz de permisos por endpoint.
- `backend/api/admin.py`
- `backend/crud/admin.py`
- `backend/schemas/admin.py`
- `backend/core/permissions.py`
- `backend/models_auth.py`
