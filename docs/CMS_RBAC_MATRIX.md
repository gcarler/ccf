# Matriz RBAC — CMS CCF

## 1. Proposito

Este documento fija la matriz RBAC operativa de CMS contra el código actual. Documenta lo que hoy hacen los routers, no lo que deberían hacer idealmente.

CMS no tiene una sola superficie homogénea. La lectura correcta exige separar:

- `backend/api/cms/v1.py` (CMS v1, compatibilidad de media)
- `backend/api/cms_v2/` (CMS v2 modular)
- `backend/api/enterprise_cms.py` (Enterprise CMS)

## 2. Fuente de verdad inspeccionada

- `backend/api/cms/v1.py`
- `backend/api/cms_v2/`
- `backend/api/enterprise_cms.py`
- `backend/core/permissions.py`
- `backend/management/seed_user_permissions.py`

Fecha de lectura: `2026-07-16`

## 3. Permisos canónicos CMS

Permisos canónicos:

- `cms:read`
- `cms:edit`
- `cms:manage`

Jerarquía efectiva:

- `cms:manage` incluye `cms:edit` y `cms:read`
- `cms:edit` incluye `cms:read`

## 4. Capas reales de autorización

### 4.1. Roles persistidos sembrados (`RolPlataforma`)

Contrato observado en `seed_user_permissions.py`:

| Rol | CMS efectivo esperado |
|---|---|
| `ADMINISTRADOR` | `cms:manage` |
| `GESTOR` | `cms:edit` |
| `EDITOR` | `cms:edit` |
| `LECTOR` | `cms:read` |
| `MIEMBRO` | sin CMS |

### 4.2. Fallback runtime (`DEFAULT_ROLES`)

Contrato observado en `permissions.py`:

| Rol fallback | CMS efectivo esperado |
|---|---|
| `Administrador` | `cms:manage` |
| `Gestor` | sin CMS explícito |
| `Editor` | sin CMS explícito |
| `Lector` | sin CMS |
| `Miembro` | sin CMS |

Asimetría relevante:

- seed persistido sí otorga CMS a `GESTOR`, `EDITOR` y `LECTOR`
- fallback runtime no documenta CMS para esos roles

En CMS, depender del fallback runtime no es equivalente a depender del `RolPlataforma` persistido.

## 5. Matriz por superficie

### 5.1. CMS v1 (`backend/api/cms/v1.py`)

| Superficie | Guard observado | Roles que pasan hoy |
|---|---|---|
| contenido público de testimonios/anuncios servido por CMS v2 | público | cualquiera |
| listados admin testimonials/announcements | `require_module_access("cms", "read")` | `ADMINISTRADOR`, `GESTOR`, `EDITOR`, `LECTOR` persistido |
| create/update/delete testimonials/announcements | `require_module_access("cms", "read")` | mismos que arriba |
| media list/detail | `require_module_access("cms", "read")` + scope de sede | usuarios con `cms:read` y sede válida |
| media create/update/optimize/upload/edit | `require_module_access("cms", "edit")` + `CMS_EDITOR_ROLES` + scope de sede | `ADMINISTRADOR`, `GESTOR`, `EDITOR` persistidos |
| media soft-delete | `require_module_access("cms", "edit")` + `CMS_EDITOR_ROLES` + scope de sede | `ADMINISTRADOR`, `GESTOR`, `EDITOR` persistidos |
| media hard-delete (`permanent=true`) / cleanup | `require_module_access("cms", "edit")` + `CMS_PUBLISHER_ROLES` + scope de sede | `ADMINISTRADOR`, `COORDINADOR`, `PASTOR` persistidos |
| metrics | `require_module_access("cms", "read")` | `ADMINISTRADOR`, `GESTOR`, `EDITOR`, `LECTOR` persistido |

Corrección aplicada:

- las mutaciones editoriales de media v1 conservan el permiso granular `cms:edit` y aplican `CMS_EDITOR_ROLES`, igual que CMS v2
- el soft-delete sigue siendo editorial; el hard-delete (`permanent=true`) y cleanup requieren `CMS_PUBLISHER_ROLES`
- esto impide que un rol nominal `LECTOR` con un grant manual aislado de `cms:edit` atraviese v1 de forma distinta a v2
- las lecturas siguen usando `cms:read` y mantienen el scope por sede

### 5.2. CMS v2 (`backend/api/cms_v2/`)

Patrón observado:

- lectura admin/preview interna: `cms:read`
- creación/edición/borrado/workflow/schedule/images optimize: `cms:edit`
- rutas públicas usan rate limiting y no exigen auth CMS

| Superficie | Guard observado | Roles que pasan hoy |
|---|---|---|
| section types, sites, themes, menus, pages, sections, global blocks, categories, tags, posts, analytics internas, preview | `require_module_access("cms", "read")` | `ADMINISTRADOR`, `GESTOR`, `EDITOR`, `LECTOR` persistido |
| create/update/delete de esos mismos recursos | `require_module_access("cms", "edit")` | `ADMINISTRADOR`, `GESTOR`, `EDITOR` persistidos |
| workflow publish/unpublish y schedule | `require_module_access("cms", "edit")` | `ADMINISTRADOR`, `GESTOR`, `EDITOR` persistidos |
| endpoints públicos `public_theme`, `public_menu`, `public_page`, sitemap, robots, pastoral-team, analytics públicas, track_page_view` | públicos con rate limit | cualquiera |

Conclusión:

- CMS v2 sí separa razonablemente lectura y mutación
- la superficie pública no debe confundirse con RBAC CMS interno

### 5.3. Enterprise CMS (`backend/api/enterprise_cms.py`)

Patrón observado:

- los endpoints ahora expresan `cms:read` para lecturas y `cms:manage` para mutaciones
- la autorización queda visible en la firma del router, no escondida sólo en autenticación implícita

| Superficie | Guard observado | Roles que pasan hoy |
|---|---|---|
| audit logs | `cms:read` | `ADMINISTRADOR` y roles con `cms:read` explícito |
| content permissions | `cms:read` / `cms:manage` | lectura para `cms:read`; mutación para `cms:manage` |
| notifications | `cms:read` / `cms:manage` | lectura para `cms:read`; mutación para `cms:manage` |
| webhooks | `cms:read` / `cms:manage` | lectura para `cms:read`; mutación para `cms:manage` |
| custom types / entries / versions / rollback | `cms:read` / `cms:manage` | lectura para `cms:read`; mutación para `cms:manage` |
| glossary, search, promotions, sessions, media folders, redirects, broken links | `cms:read` / `cms:manage` | lectura para `cms:read`; mutación para `cms:manage` |

Hallazgo operativo:

- Enterprise CMS ya no depende sólo de autenticación para la superficie revisada
- la lectura y la mutación quedaron separadas con `cms:read` y `cms:manage`

## 6. Lectura correcta por rol

| Rol | CMS v1 | CMS v2 | Enterprise CMS |
|---|---|---|---|
| `ADMINISTRADOR` | lectura + mutación | lectura + mutación | lectura + mutación |
| `GESTOR` persistido | lectura + mutación v1 | lectura + mutación v2 | lectura si tiene `cms:read`; mutación sólo con `cms:manage` |
| `EDITOR` persistido | lectura + mutación v1 | lectura + mutación v2 | lectura si tiene `cms:read`; mutación sólo con `cms:manage` |
| `LECTOR` persistido | solo lectura; mutaciones bloqueadas por `CMS_EDITOR_ROLES` | solo lectura v2 | lectura sólo si tiene `cms:read`; sin mutación |
| `MIEMBRO` | sin CMS | sin CMS | sin CMS salvo permiso explícito añadido |

## 7. Riesgos y drift documentados

1. CMS v1 conserva endpoints de compatibilidad, pero sus mutaciones de media ya están alineadas con el guard nominal de v2.
2. CMS v2 sigue siendo la superficie canónica para páginas, posts, workflow y contenido nuevo.
3. Enterprise CMS ya expresa RBAC por `cms:*` en el borde del router; la deuda activa se concentra ahora en la migración documental y de consumidores legacy.
4. seed persistido y fallback runtime siguen sin ser equivalentes para `GESTOR`, `EDITOR` y `LECTOR`.

## 8. Reglas operativas para QA

Validar mínimo:

1. `ADMINISTRADOR` entra a toda la superficie interna CMS
2. `GESTOR` y `EDITOR` deben poder mutar CMS v2
3. `LECTOR` no debe mutar CMS; v1 y v2 deben conservar la misma barrera nominal además del permiso granular
4. preview, publicado y público se prueban por separado
5. enterprise se valida como superficie aparte; auth no equivale a permiso CMS correcto

## 9. Estado

- `PEND-RBAC-CMS-001` se corrige en esta auditoría: mutaciones v1 de media alineadas con v2 y documentadas aquí
- `PEND-RBAC-ENTERPRISE-CMS-001` queda cerrada el `2026-07-16` con guards `cms:read` / `cms:manage` en el borde del router
- la deuda técnica visible queda concentrada en la evolución normal de CMS v1 y en cambios futuros de contrato, no en Enterprise CMS
