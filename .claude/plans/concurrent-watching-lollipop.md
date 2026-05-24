# Plan: Sistema de Permisos por Módulo para Visitantes/Estudiantes

## Contexto

Actualmente cualquier usuario autenticado (incluyendo "visitante"/"estudiante") puede acceder a módulos que no debería (CRM, CMS, Evangelismo, Proyectos, Finanzas, etc.) porque:
- La mayoría de módulos usan `require_active_user` como único guard → cualquier usuario logueado pasa
- El frontend no tiene guards de ruta en la mayoría de los layouts
- El sidebar muestra todos los módulos a todos (excepto evangelismo que se filtra por rol admin/pastor)

El sistema de permisos ya existe en `backend/core/permissions.py` (`require_permission()`, `UserPermission` override, `Role` catalog) pero no se aplica consistentemente.

**Objetivo:** Usuario "visitante"/"estudiante" solo puede acceder a:
1. Su perfil (editar nombre, documento, WhatsApp, info personal)
2. Academia (inscribirse en cursos, estudiar, evaluaciones)

El administrador puede otorgar acceso a otros módulos por usuario.

---

## Implementación

### Fase 1: Backend - Utilidades de permisos + endpoint

#### 1.1 Agregar `get_user_effective_permissions()` y `require_module_access()` en `permissions.py`

**Archivo:** `/root/ccf/backend/core/permissions.py`

- Función `get_user_effective_permissions(db, user) → dict` que computa permisos efectivos desde Role model + UserPermission override + admin bypass
- Factory `require_module_access(module, min_level="read")` que mapea módulo → permission key usando `MODULE_PERMISSION_MAP` y llama `require_permission()`
- Agregar a `MODULE_PERMISSION_MAP`: `evangelism`, `community`, `spiritual_life` con sus niveles
- Agregar a `PERMISSIONS` las nuevas claves (evangelism:read/edit/manage, community:read/edit/manage, spiritual_life:read/edit/manage)
- Agregar "Estudiante" a `DEFAULT_ROLES` con permisos `academy:study` + `profile:manage`

#### 1.2 Incluir permisos en `/auth/me` + nuevo endpoint `/auth/me/permissions`

**Archivo:** `/root/ccf/backend/schemas/identity.py`
- Agregar campo opcional `permissions: Optional[Dict[str, str]]` al schema `User`

**Archivo:** `/root/ccf/backend/api/auth.py`
- Modificar endpoint `GET /me` para incluir `permissions` usando `get_user_effective_permissions()`
- Agregar `GET /me/permissions` endpoint standalone

#### 1.3 Reforzar guards en APIs de módulos

Reemplazar `require_active_user` por el guard específico del módulo en estos archivos:

| Archivo | Cambio |
|---|---|
| `api/projects.py` | `require_active_user` → `require_module_access("projects", "read"/"edit"/"manage")` |
| `api/finance.py` | `require_active_user` → `require_module_access("finance", "read"/"manage")` |
| `api/cms.py` | `require_active_user` → `require_module_access("cms", "read"/"edit"/"manage")` |
| `api/academy.py` | `require_active_user` → `require_module_access("academy", "study")` en enroll/submit |
| `api/community.py` | Agregar `require_module_access("community", ...)` donde no hay guard |
| `api/messaging.py` | `require_active_user` → `require_module_access("messaging", "read"/"edit")` |

Los endpoints que usan `require_pastor_or_admin` se quedan igual (CRM, evangelismo).

---

### Fase 2: Frontend - Guards de ruta y sidebar

#### 2.1 Exponer permisos en AuthContext

**Archivo:** `/root/ccf/frontend/src/context/AuthContext.tsx`
- Extender tipo `user` para incluir `permissions?: Record<string, string>`
- Agregar métodos `hasModuleAccess(module, minLevel)` y `hasPermission(perm)` en el context
- Cargar permisos desde `GET /auth/me` al inicializar sesión
- Cachear permisos en memoria mientras la sesión esté activa

#### 2.2 Extender ProtectedRoute con `allowedPermissions`

**Archivo:** `/root/ccf/frontend/src/components/ProtectedRoute.tsx`
- Agregar prop `allowedPermissions?: string[]`
- Si `allowedPermissions` está definido, verificar que el usuario tenga al menos uno de esos permisos
- Si no tiene permisos, redirigir a `/plataforma/academy`

#### 2.3 Sidebar filtrado por permisos

**Archivo:** `/root/ccf/frontend/src/components/WorkspaceMiniSidebar.tsx`
- Reemplazar el filtro hardcodeado de evangelismo con filtro genérico basado en permisos
- Solo mostrar módulos para los que el usuario tenga `module:read`

**Archivo:** `/root/ccf/frontend/src/components/WorkspaceLayout.tsx`
- Generalizar el filtro de secciones del S2 sidebar (actualmente solo filtra evangelismo)
- Filtrar items de navegación según permisos del usuario (`user.permissions`)

#### 2.4 Agregar `allowedPermissions` a layouts de módulos

| Layout | `allowedPermissions` |
|---|---|
| `academy/layout.tsx` | ninguno (accesible para todos) |
| `crm/layout.tsx` | `['crm:read']` |
| `cms/layout.tsx` | `['cms:read']` |
| `community/layout.tsx` | `['community:read']` |
| `groups/layout.tsx` | `['community:read']` |
| `spiritual-life/layout.tsx` | `['spiritual_life:read']` |
| `inbox/layout.tsx` | `['messaging:read']` |
| `tasks/layout.tsx` | `['projects:read']` |
| `support/layout.tsx` | ninguno (disponible para todos) |
| Páginas de finanzas, proyectos | `['finance:read']`, `['projects:read']` |

---

### Fase 3: Admin UI - Gestión de permisos de módulos

#### 3.1 Agregar nuevos módulos al panel de acceso

**Archivo:** `/root/ccf/frontend/src/app/plataforma/admin/access/page.tsx`
- Agregar `evangelism`, `community`, `spiritual_life` al array `MODULES` (línea 39-46)
- Agregar entries correspondientes en `PERMISSION_SCOPE`

---

### Fase 4: Migración y defaults

#### 4.1 Permisos por defecto al registrar usuario

**Archivo:** `/root/ccf/backend/api/auth.py`
- Al crear usuario vía registro o Google OAuth, asignar `UserPermission` con permisos según DEFAULT_ROLES
- "estudiante" → `academy:study` + `profile:manage`
- "aspirante" → `academy:read` + `profile:manage`

#### 4.2 Script de migración para usuarios existentes

**Archivo nuevo:** `/root/ccf/backend/management/seed_user_permissions.py`
- Iterar todos los usuarios sin `UserPermission` y crear uno según su rol

---

## Archivos a modificar (resumen)

**Backend (5 archivos):**
- `backend/core/permissions.py` — funciones nuevas, ampliar MODULE_PERMISSION_MAP, DEFAULT_ROLES
- `backend/api/auth.py` — `/me` con permisos, `/me/permissions`, permisos por defecto en registro
- `backend/schemas/identity.py` — campo permissions en User schema
- `backend/api/projects.py` — cambiar guards
- `backend/api/academy.py` — cambiar guards
- `backend/api/finance.py`, `backend/api/cms.py`, `backend/api/community.py`, `backend/api/messaging.py` — cambiar guards

**Frontend (4 archivos):**
- `frontend/src/context/AuthContext.tsx` — user.permissions, hasModuleAccess, hasPermission
- `frontend/src/components/ProtectedRoute.tsx` — allowedPermissions prop
- `frontend/src/components/WorkspaceMiniSidebar.tsx` — filtro genérico
- `frontend/src/components/WorkspaceLayout.tsx` — sidebar sections filtering
- Layouts de cada módulo — agregar `allowedPermissions`
- `frontend/src/app/plataforma/admin/access/page.tsx` — nuevos módulos

**Nuevo archivo:**
- `backend/management/seed_user_permissions.py` — migración

---

## Verificación

1. **Backend:** Autenticar como "estudiante", llamar `GET /api/auth/me` → debe mostrar solo `academy:study` + `profile:manage`
2. **Backend:** Llamar `GET /api/finance/summary` como estudiante → 403
3. **Backend:** Llamar `GET /api/academy/courses` como estudiante → 200
4. **Frontend:** Login como estudiante → sidebar solo muestra Academia, Perfil, Inbox
5. **Frontend:** Navegar a `/plataforma/crm` → redirige a academia
6. **Frontend:** Login como admin → sidebar muestra todos los módulos
7. **Admin:** En `/plataforma/admin/access` otorgar CRM a un estudiante → recargar sidebar debe mostrar CRM
8. **Migración:** Ejecutar script en BD de staging → todos los usuarios existentes tienen UserPermission
