# Módulo Administración — Gestión Central

**Actualizado:** 2026-07-18
**Ruta base frontend:** `/plataforma/admin`
**Ruta base API:** `/api/admin`
**Router backend:** `backend/api/admin.py`

---

## Arquitectura

El módulo de Administración provee la interfaz de gestión central de la plataforma CCF. Cubre: usuarios, roles, permisos, personas, finanzas, contenido web, auditoría y configuración del sistema.

### Dependencias

| Dependencia | Propósito |
|---|---|
| `backend.core.permissions` | `require_admin`, `require_active_user`, `MODULE_PERMISSION_MAP` |
| `backend.models_auth` | `Usuario`, `RolPlataforma`, `UsuarioRolModulo` |
| `backend.models_crm` | `Persona` |
| `backend.models_shared` | `_utcnow` |
| `backend.schemas.governance` | `AutomationRuleRead`, `AutomationRuleCreate`, `AutomationRuleUpdate` |

### Árbol de frontend

```
/plataforma/admin/
├── page.tsx                    # Dashboard principal (KPIs, tesorería, agentes AI)
├── layout.tsx                  # Sidebar con 4 secciones de navegación
├── access/                     # Gestión granular de permisos por módulo
├── actas/                      # Actas / minutas
├── analytics/
│   ├── candidates/             # Candidatos a bautismo
│   └── web-vitals/             # Web Vitals
├── announcements/              # Anuncios (CRUD + vistas múltiples)
├── assets/                     # Assets / recursos
├── audit/                      # Auditoría / log de seguridad
├── cms/                        # Redirige a /plataforma/cms
├── comments/                   # Moderación de foro
├── content/                    # Gestión de contenido académico
├── dashboard/
│   ├── page.tsx                # Dashboard alternativo
│   └── radar/                  # Radar del pastor
├── donations/                  # Donaciones (CRUD)
├── error.tsx                   # Error boundary
├── familias/                   # Familias
├── finance/                    # Finanzas (dashboard + transacciones)
├── identity/                   # Identidad de plataforma
├── intelligence/               # Inteligencia / analytics
├── inventory/                  # Inventario de activos
├── maintenance/                # Mantenimiento
├── ministerios/                # Ministerios (CRUD)
├── mission-impact/             # Impacto misionero
├── personas/                   # Personas (listado con búsqueda)
├── reports/                    # Reportes
├── roles/                      # Roles de plataforma (CRUD + permisos)
├── settings/                   # Configuración del sistema
├── spiritual-life/
│   └── milestones/             # Hitos espirituales (badges)
├── submissions/                # Calificaciones
├── talents/                    # Talentos
├── testimonials/               # Testimonios
├── theme/                      # Tema visual
└── users/                      # Usuarios (CRUD + provisionamiento masivo)
```

---

## Endpoints API

### Roles de Plataforma

#### `GET /api/admin/roles`
Lista todos los roles con conteo de usuarios vinculados.

**Respuesta:**
```json
[
  {
    "id": "uuid-string",
    "name": "ADMINISTRADOR",
    "permissions": { "system:config": "allow", ... },
    "users_count": 5
  }
]
```

#### `POST /api/admin/roles`
Crea un nuevo rol.

**Body:**
```json
{
  "name": "string (requerido)",
  "permissions": { "module:perm": "allow" }
}
```

**Respuesta:** `{ "id": "uuid", "name": "string" }`

#### `PATCH /api/admin/roles/{role_id}`
Actualiza permisos de un rol existente.

**Body:** `{ "permissions": { "module:perm": "allow" } }`

#### `DELETE /api/admin/roles/{role_id}`
Elimina un rol (solo si no tiene usuarios asignados). Retorna 409 si hay usuarios vinculados.

---

### Permisos

#### `GET /api/admin/permissions`
Lista todos los permisos disponibles con niveles jerárquicos.

**Respuesta:**
```json
{
  "permissions": ["crm:read", "crm:write", ...],
  "modules": { "crm": ["read", "write", "manage"], ... },
  "levels": { ... }
}
```

---

### Gestión de Usuarios (Auth v3)

#### `GET /api/admin/users`
Lista usuarios de `auth_users` con sus roles y permisos.

#### `GET /api/admin/users/{user_id}`
Obtiene un usuario por UUID.

#### `POST /api/admin/users`
Crea usuario Auth v3 (crea Persona mínima + Usuario).

**Body:**
```json
{
  "username": "string (requerido)",
  "email": "string (requerido)",
  "password": "string (requerido)",
  "first_name": "string",
  "last_name": "string",
  "role": "ADMINISTRADOR | GESTOR | EDITOR | MIEMBRO | LECTOR"
}
```

#### `PATCH /api/admin/users/{user_id}`
Actualiza campos de usuario (username, email, password, is_active, rol_plataforma_id, role).

#### `DELETE /api/admin/users/{user_id}`
Desactiva un usuario (soft delete: `is_active = false`).

#### `PATCH /api/admin/users/{user_id}/role`
Asigna un rol de plataforma por UUID.

**Query params:** `role_id` (UUID string)

---

### Permisos de Usuario

#### `GET /api/admin/users/{user_id}/permissions`
Obtiene permisos actuales de un usuario (rol + override).

#### `PUT /api/admin/users/{user_id}/permissions`
Asigna permisos modulares a un usuario.

**Body:**
```json
{
  "crm": "read",
  "projects": "manage",
  "academy": "study"
}
```
Niveles válidos por módulo: `read`, `edit`, `manage` (y `study` para academy).

Crea un rol personalizado `PERSONALIZADO_{USER_ID}` para no modificar roles compartidos.

---

### Personas

#### `GET /api/admin/personas`
Lista todas las personas para administración.

**⚠️ Nota:** Este endpoint actualmente **no filtra por `sede_id`**, lo que viola el aislamiento multi-tenant. Pendiente de corrección (ver PLAN_ADMIN_CALIDAD.md A1).

**Respuesta:**
```json
[
  {
    "id": "uuid",
    "first_name": "...",
    "last_name": "...",
    "email": "...",
    "phone": "...",
    "church_role": "..."
  }
]
```

---

### Ubicaciones (Sedes)

#### `GET /api/admin/locations`
Lista todas las sedes de la iglesia.

#### `POST /api/admin/locations`
Crea una nueva sede.

**Body:**
```json
{
  "nombre": "string (requerido)",
  "address": "string",
  "pastor": "string",
  "type": "Sede | Anexo"
}
```

---

### Canales Sociales

#### `GET /api/admin/socials`
Lista canales sociales oficiales.

---

### Variables de Sistema

#### `GET /api/admin/variables`
Obtiene variables de configuración global.

**Respuesta:** `{ "key1": "value1", "key2": "value2" }`

#### `POST /api/admin/variables`
Define o actualiza una variable de sistema.

**Parámetros (query):** `key` (string), `value` (string)

⚠️ Actualmente usa query params en vez de body JSON. Pendiente de migración.

---

### Auditoría

#### `GET /api/admin/audit?limit=100`
Obtiene el historial de auditoría del sistema.

**Respuesta:**
```json
[
  {
    "id": "uuid",
    "actor_persona_id": "uuid",
    "action": "string",
    "resource_type": "string",
    "resource_id": "string",
    "created_at": "ISO datetime",
    "metadata": {}
  }
]
```

---

### Moderación de Foro

#### `GET /api/admin/comments`
Lista todos los comentarios para moderación.

#### `DELETE /api/admin/comments/{comment_id}`
Elimina un comentario (soft delete: `deleted_at`).

---

### Hitos Espirituales (Badges)

#### `GET /api/admin/milestones`
Lista hitos espirituales con estadísticas de obtención.

#### `POST /api/admin/milestones/award`
Asigna un hito a una lista de personas.

**Body:**
```json
{
  "badge_id": "uuid",
  "persona_ids": ["uuid1", "uuid2"]
}
```

---

### Categorías de Donación

#### `GET /api/admin/donation-categories`
Lista categorías de recaudación.

#### `POST /api/admin/donation-categories`
Crea una nueva categoría.

**Body:**
```json
{
  "nombre": "string (requerido)",
  "descripcion": "string",
  "color": "blue"
}
```

---

### Automatizaciones CRM

#### `GET /api/admin/automations`
Lista reglas de automatización.

**Schema respuesta:** `AutomationRuleRead`

#### `POST /api/admin/automations`
Crea una regla de automatización.

**Body** (`AutomationRuleCreate`):
```json
{
  "name": "string (requerido)",
  "trigger_type": "string (requerido)",
  "action_type": "string",
  "action_payload": {},
  "is_active": true
}
```

#### `PATCH /api/admin/automations/{rule_id}`
Actualiza una regla.

**Body** (`AutomationRuleUpdate`): campos opcionales `name`, `trigger_type`, `action_type`, `action_payload`, `is_active`

#### `DELETE /api/admin/automations/{rule_id}`
Elimina una regla (soft delete: `deleted_at`).

---

### Roles Modulares Granulares

#### `GET /api/admin/auth-role-definitions`
Lista todas las definiciones de roles (`RolPlataforma`).

#### `POST /api/admin/auth-role-definitions`
Crea un nuevo rol.

**Body:** `{ "nombre": "string", "permisos": {} }`

#### `PATCH /api/admin/auth-role-definitions/{role_id}`
Actualiza permisos o nombre de un rol.

#### `DELETE /api/admin/auth-role-definitions/{role_id}`
Elimina un rol (solo si no está asignado). Retorna 409 si tiene usuarios.

#### `GET /api/admin/user-module-roles`
Lista asignaciones de roles modulares.

#### `POST /api/admin/user-module-roles`
Asigna un rol modular a un usuario.

**Body:**
```json
{
  "user_id": "uuid",
  "modulo": "crm | academy | projects | ...",
  "rol_id": "uuid"
}
```

#### `DELETE /api/admin/user-module-roles/{assignment_id}`
Elimina una asignación (soft delete: `deleted_at`).

#### `GET /api/admin/users-with-roles`
Lista todos los usuarios con sus roles de plataforma y modulares.

---

### Provisionamiento Masivo

#### `POST /api/admin/provision-accounts`
Crea cuentas de plataforma para todas las personas con email que aún no tienen `auth_user`.

- username = prefijo del email
- password = aleatoria 12 caracteres
- rol = MIEMBRO

**Respuesta:**
```json
{
  "created": 10,
  "skipped": 2,
  "errors": [],
  "accounts": [
    { "email": "...", "username": "...", "temp_password": "..." }
  ],
  "message": "..."
}
```

---

## Schemas Pydantic

Definidos en `backend/schemas/governance.py`:

### `AutomationRuleRead`
| Campo | Tipo | Descripción |
|---|---|---|
| id | UUID | ID de la regla |
| name | str | Nombre |
| trigger_type | str | Tipo de evento disparador |
| action_type | str? | Tipo de acción |
| action_payload | dict | Payload de la acción |
| is_active | bool | Activa/inactiva |
| last_run | datetime? | Última ejecución |

### `AutomationRuleCreate`
Mismos campos que `AutomationRuleRead` sin `id`, `last_run`.

### `AutomationRuleUpdate`
Todos los campos opcionales.

### `AdminAuditLog`
| Campo | Tipo | Descripción |
|---|---|---|
| id | UUID | ID del log |
| actor_persona_id | str? | Persona que realizó la acción |
| action | str | Acción realizada |
| resource_type | str? | Tipo de recurso afectado |
| resource_id | str? | ID del recurso |
| ip_address | str? | IP del actor |
| severity | str | "info", "warning", "error" |
| metadata | dict | Metadatos adicionales |
| created_at | datetime | Fecha del evento |

---

## Componentes Compartidos

| Componente | Ubicación | Propósito |
|---|---|---|
| `AdminShell` | `components/admin/AdminShell.tsx` | Layout con toolbar + breadcrumbs |
| `AdminHero` | `components/admin/AdminHero.tsx` | Encabezado visual con acciones |

---

## Tests

Archivo: `tests/test_admin_coverage.py`

**Cobertura actual:** ~32% (estimado)
**Fixture:** `full(client, db_session)` — crea admin + sede + headers auth

### Estructura de tests

| Clase | Propósito | Tests |
|---|---|---|
| `TestSimpleCRUD` | GET endpoints básicos | 11 |
| `TestCRUDWithData` | POST con creación | 5 |
| `TestUserManagement` | CRUD usuarios + role change | 7 |
| `TestPermissionsRoles` | Permisos y roles | 5 |
| `TestSettingsConfig` | Settings y variables | 3 |
| `TestAuditComments` | Auditoría, comentarios, milestones | 5 |
| `TestAllOtherEndpoints` | ✅ ELIMINAR — duplica tests anteriores |

⚠️ **Problemas conocidos:**
- `TestAllOtherEndpoints` duplica tests sin aportar cobertura
- Payloads de tests no coinciden con schemas Pydantic (usan nombres en español)
- Sin assertions de contenido (solo status code)
- No hay tests de verificación de `sede_id`

---

## Permisos Requeridos

| Ruta | Permiso mínimo |
|---|---|
| `/admin/*` | `system:config` o rol ADMINISTRADOR |
| `/admin/locations` | `require_active_user` (lectura) |
| `/admin/socials` | `require_active_user` (lectura) |
| `/admin/milestones` | `require_active_user` (lectura) |
| `/admin/donation-categories` | `require_active_user` (lectura) |
| `/admin/automations` | `require_active_user` (lectura) |
| Endpoints de escritura | `require_admin` |

---

## Issues Conocidos

1. **Aislamiento multi-tenant:** `GET /api/admin/personas` no filtra por `sede_id`
2. **API inconsistente:** `POST /api/admin/variables` usa query params en vez de body JSON
3. **Serialización:** `_serialize_automation` usa `rule.id` (UUID object) en vez de `str(rule.id)`
4. **Dashboard mock:** KPIs del dashboard principal son datos hardcodeados
5. **Tests duplicados:** `TestAllOtherEndpoints` es redundante
6. **Componentes subutilizados:** `AdminHero` solo se usa en 2 de 30 páginas

---

## Referencias

- `backend/api/admin.py` — router con 39 endpoints
- `frontend/src/app/plataforma/admin/` — 32 páginas frontend
- `tests/test_admin_coverage.py` — tests de cobertura
- `docs/PLAN_ADMIN_CALIDAD.md` — plan de mejoras priorizadas
