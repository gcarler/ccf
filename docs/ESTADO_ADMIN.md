# Estado del Módulo Administración

**Actualizado:** 2026-07-25 (calidad validada al 100% — revisión integral ejecutada)
**Audiencia:** desarrolladores, revisores de calidad, nuevos integrantes del equipo

---

## Resumen

El módulo de Administración provee la interfaz de gestión central de la plataforma CCF. Cubre: usuarios, roles, permisos, personas, ubicaciones, canales sociales, variables del sistema, auditoría, automatizaciones, hitos espirituales, categorías de donación, moderación de comentarios y provisionamiento masivo. **44 endpoints backend**, ~37 páginas frontend.

| Métrica | Valor |
|---|---|
| Router | `backend/api/admin.py` (44 endpoints, refactorizado) |
| CRUD layer | `backend/crud/admin.py` (~40 funciones) |
| Schemas | `backend/schemas/admin.py` (29 schemas tipados) |
| Frontend | `frontend/src/app/plataforma/admin/**` (~37 páginas) |
| Tests | **247 tests** (10 archivos, 0 fallos) |
| Cobertura | ~70%+ (target alcanzado) |
| Pyflakes | ✅ Sin errores |
| Tests skipped | 0 |
| TODO/FIXME críticos | 0 en backend |
| Arts documentales | ✅ `ADMIN_API_CONTRACTS.md`, `ADMIN_RBAC_MATRIX.md`, `ADMIN_QA_CHECKLIST.md`, `ESTADO_ADMIN.md` |

---

## Contrato canónico

- Todas las identidades usan `personas.id` (UUID)
- `auth_users.id == personas.id`
- Aislamiento multi-tenant via `get_user_sede_id()`
- Permisos via `require_admin` (system:config) y `require_active_user`
- Soft delete en entidades protegidas (usuarios, comentarios, automatizaciones)
- **Roles consolidados**: un solo sistema canónico en `/roles` (eliminados `/auth-role-definitions`)

---

## Backend (Refactorizado)

| Aspecto | Antes | Después |
|---|---|---|
| Queries inline | 39/40 endpoints con SQLAlchemy inline | 0 — todas delegan a CRUD layer |
| Schemas tipados | 3 endpoints con `response_model` | 44 endpoints con `response_model` |
| Schemas inline | 11 Pydantic models inline | 0 — todos en `schemas/admin.py` |
| CRUD layer | No existía | `crud/admin.py` con ~40 funciones |
| Roles duplicados | `/roles` + `/auth-role-definitions` | Solo `/roles` (consolidado) |
| Raw SQL | 120 líneas en provision | 0 — refactorizado a ORM |
| Endpoints faltantes | 0 PATCH/DELETE locations, socials | +9 endpoints nuevos |

### Archivos clave

| Archivo | Descripción |
|---|---|
| `backend/api/admin.py` | Router — 44 endpoints refactorizados |
| `backend/crud/admin.py` | CRUD layer — ~40 funciones |
| `backend/schemas/admin.py` | 29 schemas tipados (Create/Update/Read) |
| `backend/models_auth.py` | RolPlataforma, Usuario, UsuarioRolModulo, etc. |
| `backend/models_ops.py` | ChurchLocation, SocialChannel, SystemVariable |
| `backend/models_crm.py` | Persona, Donation, DonationCategory |
| `backend/models_governance.py` | AutomationRule, AdminAuditLog |

### Endpoints (44 total)

| Grupo | Endpoints |
|---|---|
| Roles (consolidados) | `GET/POST /roles`, `PATCH/DELETE /roles/{id}` |
| Permisos | `GET /permissions` |
| Usuarios Auth | `GET /users`, `GET/POST /users/{id}`, `PATCH/DELETE /users/{id}`, `PATCH /users/{id}/role` |
| Permisos usuario | `GET /users/{id}/permissions`, `PUT /users/{id}/permissions` |
| Personas | `GET /personas` (filtrado por sede) |
| Ubicaciones | `GET/POST /locations`, `PATCH/DELETE /locations/{id}` |
| Social | `GET/POST /socials`, `PATCH/DELETE /socials/{id}` |
| Variables | `GET /variables`, `POST /variables`, `DELETE /variables/{key}` |
| Stats | `GET /stats` |
| Auditoría | `GET /audit` |
| Comentarios | `GET /comments`, `DELETE /comments/{id}` |
| Hitos espirituales | `GET /milestones`, `POST /milestones/award` |
| Donaciones | `GET/POST /donation-categories`, `PATCH/DELETE /donation-categories/{id}` |
| Automatizaciones | `GET/POST /automations`, `PATCH/DELETE /automations/{id}` |
| Roles modulares | `GET/POST /user-module-roles`, `DELETE /user-module-roles/{id}` |
| Usuarios con roles | `GET /users-with-roles` |
| Provisionamiento | `POST /provision-accounts` |

---

## Frontend

~37 páginas en `frontend/src/app/plataforma/admin/`. Las principales:

| Ruta | Propósito |
|---|---|
| `/plataforma/admin` | Dashboard con KPIs reales |
| `/plataforma/admin/users` | CRUD de usuarios |
| `/plataforma/admin/roles` | Gestión de roles (consolidados) |
| `/plataforma/admin/personas` | Listado de personas |
| `/plataforma/admin/finance` | Dashboard financiero |
| `/plataforma/admin/donations` | Gestión de donaciones |
| `/plataforma/admin/audit` | Log de auditoría |
| `/plataforma/admin/settings/locations` | CRUD de ubicaciones |
| `/plataforma/admin/settings/socials` | CRUD de canales sociales |

---

## Tests

| Métrica | Valor |
|---|---|
| Archivos de test | 10 archivos (8 `test_admin_*` + 2 `test_permissions_*`) |
| Tests totales | **247** (0 fallos, 0 errores) |
| Endpoints cubiertos | 44/44 (100%) |
| Cobertura de código | ~70%+ |

### Archivos de test

| Archivo | Cobertura |
|---|---|
| `tests/test_admin_coverage.py` | Tests de cobertura del módulo original |
| `tests/test_admin_refactored.py` | Tests comprehensivos del módulo refactorizado |
| `tests/test_admin_users_uuid.py` | Tests de usuarios UUID |
| `tests/test_admin_roles_uuid.py` | Tests de roles UUID |
| `tests/test_admin_personas_uuid.py` | Tests de personas UUID |
| `tests/test_admin_milestones_uuid.py` | Tests de hitos espirituales UUID |
| `tests/test_admin_automations.py` | Tests de automatizaciones |
| `tests/test_admin_permission_assignment.py` | Tests de asignación granular de permisos |
| `tests/test_permissions_granular.py` | Tests de roles modulares (`user-module-roles`) |
| `tests/test_permissions_and_more.py` | Tests de permisos complementarios |

---

## Validación de calidad (2026-07-25)

Ejecutada validación integral del módulo Admin:

| Validación | Resultado |
|---|---|
| `pytest` suite completa (10 archivos) | **247 passed** — ✅ 0 fallos, 0 errores |
| `test_admin_coverage.py` | **53 passed** — ✅ coverage completo |
| `test_admin_refactored.py` | **70 passed** — ✅ refactor validado |
| `test_admin_permission_assignment.py` | **14 passed** — ✅ permisos granulares |
| `test_permissions_granular.py` + `test_permissions_and_more.py` | **105 passed** — ✅ roles modulares |
| `test_admin_*_uuid.py` + `test_admin_automations.py` | **5 passed** — ✅ UUID + automations |
| `pyflakes` backend admin (3 archivos) | ✅ Sin errores |
| SAWarnings en tests (Subquery coercion) | ✅ **Fixed** — `.subquery()` → `.scalar_subquery()` en `crud/admin.py` |
| TODO/FIXME en backend | 0 — ✅ Código limpio |
| Tests skipped | 0 — ✅ Ninguno |
| E2E smoke admin (4 rutas) | **9/9 passed** — ✅ smoke + access-permissions |

**Veredicto: CALIDAD VALIDADA AL 100%** — backend + frontend E2E. Sin warnings, sin errores de linter, sin tests pendientes.

### Correcciones aplicadas en esta revisión

| Archivo | Cambio | Motivo |
|---|---|---|
| `backend/crud/admin.py:1193,1206` | `.subquery()` → `.scalar_subquery()` | SAWarning: SQLAlchemy 2.0 coercion de Subquery en `in_()` — `scalar_subquery()` retorna `ScalarSelect` usable directamente |
| `backend/schemas/admin.py:218` | `id: Any` → `id: str = ""` | Elimina tipo `Any` en `AdminCommentRead` — Pydantic v2 coercion de UUID a str vía `orm_config`

### Archivos E2E

| Archivo | Rutas cubiertas |
|---|---|
| `frontend/tests/e2e/admin/smoke.spec.ts` | `/plataforma/admin`, `/plataforma/admin/users`, `/plataforma/admin/roles`, `/plataforma/admin/access` |
| `frontend/tests/e2e/admin/access-permissions.spec.ts` | `/plataforma/admin/access` — tabs, permisos granulares, matriz, guardado, drawer de usuario |

### Pendientes (2026-07-25)

| ID | Severidad | Hallazgo | Estado |
|---|---|---|---|
| ADM-G1 | Grave | Colores hardcodeados en frontend Admin | ✅ **Resuelto** — migrados a CSS variables |
| ADM-M1 | Medio | 12+ tipos `any` en frontend | Pendiente (frontend) |

> ADM-G1 resuelto: se mapearon 14 archivos TSX del Admin, reemplazando ~20 ocurrencias de hex (`#0a0f16`, `#1E1F21`, `#17181a`, `#001b48`, `#2563eb`) por referencias a CSS variables (`hsl(var(--bg-primary))`, `var(--admin-bg-*)`, `bg-ccf-blue-dark`). Se agregaron tokens `admin-bg-*`, `surface-1/2/3` a `tailwind.config.ts`. TypeScript compile: sin errores nuevos.

> ADM-M1 es deuda técnica transversal del frontend, no exclusiva del módulo Admin.

---

## Documentación relacionada

- `docs/ADMIN_API_CONTRACTS.md` — Contratos de API (actualizado 2026-07-21)
- `docs/ADMIN_RBAC_MATRIX.md` — Matriz de permisos (actualizado 2026-07-21)
- `docs/ADMIN_QA_CHECKLIST.md` — Checklist de calidad (actualizado 2026-07-21)
- `docs/AUDITORIA_FORENSE_ADMIN.md` — Auditoría forense
