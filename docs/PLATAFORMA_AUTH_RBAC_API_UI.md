# Contrato Raiz — Plataforma Compartida

## 1. Alcance

Este documento cubre las piezas compartidas que condicionan a todos los modulos:

- auth v3
- RBAC y permisos por modulo
- cliente HTTP `apiFetch`
- layout y componentes UI base

## 2. Auth v3

Archivos:

- `backend/api/auth_v3.py`
- `backend/models_auth.py`

Contrato vigente:

- login canonico: `POST /api/v3/auth/login`
- refresh canonico: `POST /api/v3/auth/refresh`
- Google OAuth: `GET /api/v3/auth/google` y callback asociado
- sesiones y perfil via `/api/v3/auth/*`

Invariantes:

- `auth_users.id == personas.id`
- access token y refresh token se consideran fuente canonica de sesion
- el frontend no debe usar endpoints legacy `/api/auth/*` en codigo nuevo

## 3. RBAC / permisos

Archivo: `backend/core/permissions.py`.

Taxonomia actual de modulo:

- `crm`
- `finance`
- `projects`
- `cms`
- `academy`
- `messaging`
- `evangelism`
- `community`
- `spiritual_life`

Reglas:

- `manage` incluye `edit` y `read`
- `edit` incluye `read`
- `study` convive solo en `academy`
- los guards FastAPI deben salir de esta capa, no reinventarse por router

### 3.1. Módulos canónicos

| Id canónico | Niveles |
|---|---|
| `crm` | `read`, `edit`, `manage` |
| `finance` | `read`, `edit`, `manage` |
| `projects` | `read`, `edit`, `manage` |
| `cms` | `read`, `edit`, `manage` |
| `academy` | `read`, `study`, `edit`, `manage` |
| `messaging` | `read`, `edit` |
| `evangelism` | `read`, `edit`, `manage` |
| `community` | `read`, `edit`, `manage` |
| `spiritual_life` | `read`, `edit`, `manage` |

Alias legacy tolerados solo en compatibilidad de lectura:

- `finances` → `finance`
- `agenda` → `spiritual_life`

No deben usarse en código nuevo, seeds ni contratos admin.

### 3.2. Orden de resolución

1. bypass administrativo (`admin` / `system:config`)
2. `RolPlataforma` persistido en Auth v3
3. fallback `DEFAULT_ROLES` en `permissions.py`
4. compatibilidad Kernel RBAC, con normalización de aliases legacy

### 3.3. Matriz raíz por rol

La plataforma hoy tiene dos representaciones de roles:

- `DEFAULT_ROLES` en runtime/fallback
- `RolPlataforma` persistido y sembrado por `backend/management/seed_user_permissions.py`

Contrato operativo mínimo:

| Rol | Alcance mínimo garantizado |
|---|---|
| `ADMINISTRADOR` | `system:config` + `manage` en todos los módulos canónicos |
| `GESTOR` | `manage` en `crm`, `academy`, `projects`, `evangelism`, `community`, `messaging`; `finance:read`; `cms:edit`; `spiritual_life:manage` |
| `EDITOR` | `edit` en `crm`, `projects`, `evangelism`, `cms`, `community`, `messaging`, `spiritual_life`; `academy:read`; `finance:read` |
| `LECTOR` | `read` de todos los módulos en roles persistidos; fallback runtime mínimo puede ser más estrecho |
| `MIEMBRO` | `academy:study` + `profile:manage` |

### 3.4. Contrato de drift controlado

- La taxonomía canónica es `MODULE_PERMISSION_MAP`.
- `seed_user_permissions.py` debe usar solo ids canónicos.
- `kernel_rbac.py` puede normalizar aliases viejos para no romper datos heredados, pero no debe emitirlos.
- La UI admin (`/plataforma/admin/access`) debe usar los mismos ids canónicos.

Estado de cierre:

- `PEND-RBAC-ROOT-001` cerrada el **2026-07-16** con esta matriz raíz, normalización de aliases legacy en Kernel RBAC y seeds canónicos.

## 4. Admin / asignacion de permisos

Archivo: `backend/api/admin.py`.

Superficies base:

- roles de plataforma
- permisos por usuario
- auth role definitions
- user module roles

No romper:

- listado de roles
- lectura de permisos efectivos por usuario
- asignacion granular de permisos

## 5. Cliente HTTP canonico

Archivo: `frontend/src/lib/http.ts`.

Contrato:

- usar `apiFetch` para REST de plataforma
- inyecta token desde `sessionStorage`
- reintenta una vez tras refresh si recibe `401`
- si refresh falla, limpia sesion y redirige a `/login?expired=true`

No aprobar:

- nuevo `fetch()` directo donde corresponde `apiFetch`
- bypass del refresh compartido

## 6. UI base protegida

Documento canonico:

- `docs/PLATAFORMA_UI_BASE_PROTEGIDA.md`
- `docs/PLATAFORMA_MATRIZ_MODULAR.md`

Archivos base:

- `frontend/src/components/WorkspaceLayout.tsx`
- `frontend/src/components/ui/TableView.tsx`
- `frontend/src/components/ui/UniversalTableView.tsx`

Regla:

- cualquier cambio debe considerarse plataforma
- validar al menos CRM, proyectos y evangelismo
- errores de AG Grid o layout se tratan como regresiones compartidas
- no mezclar `themeQuartz` con CSS legacy de AG Grid

## 7. Pendientes de contrato

- `PEND-PLATFORM-SMOKE-001` cerrada el `2026-07-16`
- `PEND-UI-BASE-001` cerrada el `2026-07-16` en `PLATAFORMA_UI_BASE_PROTEGIDA.md`
- `PEND-PLATFORM-MATRIX-001` cerrada el `2026-07-16` en `PLATAFORMA_MATRIZ_MODULAR.md`
