# Estado del Módulo Administración

**Actualizado:** 2026-07-18
**Audiencia:** desarrolladores, revisores de calidad, nuevos integrantes del equipo

---

## Resumen

El módulo de Administración provee la interfaz de gestión central de la plataforma CCF. Cubre: usuarios, roles, permisos, personas, finanzas, contenido web, auditoría y configuración del sistema. 40 endpoints backend, ~30 páginas frontend.

| Métrica | Valor |
|---|---|
| Router | `backend/api/admin.py` (40 endpoints) |
| Frontend | `frontend/src/app/plataforma/admin/**` (~30 páginas) |
| Tests | 53 tests — cobertura 100% de endpoints |
| Artefactos documentales | ✅ `MODULO_ADMIN.md`, `PLAN_ADMIN_CALIDAD.md`, `AUDITORIA_FORENSE_ADMIN.md` |
| Smoke script | `scripts/test_admin_quality.py` |

---

## Contrato canónico

- Todas las identidades usan `personas.id` (UUID)
- `auth_users.id == personas.id`
- Aislamiento multi-tenant via `get_user_sede_id()`
- Permisos via `require_admin` y `require_active_user`
- Soft delete en entidades protegidas (usuarios, comentarios, automatizaciones)

---

## Backend

| Aspecto | Detalle |
|---|---|
| Router principal | `backend/api/admin.py` |
| Schemas | `backend/schemas/governance.py` (AutomationRuleRead/Create/Update, AdminAuditLog, SetVariableBody) |
| Modelos usados | `models.py`, `models_auth.py`, `models_crm.py`, `models_governance.py` |
| CRUD | `crud/audit.py` + consultas directas |

### Endpoints (40 total)

| Grupo | Endpoints |
|---|---|
| Roles | `GET/POST /roles`, `PATCH/DELETE /roles/{id}` |
| Permisos | `GET /permissions` |
| Usuarios Auth | `GET /users`, `GET/POST /users/{id}`, `PATCH/DELETE /users/{id}`, `PATCH /users/{id}/role` |
| Permisos usuario | `GET/PUT /users/{id}/permissions` |
| Personas | `GET /personas` (filtrado por sede) |
| Ubicaciones | `GET/POST /locations` |
| Social | `GET /socials` |
| Variables | `GET/POST /variables` |
| Stats | `GET /stats` |
| Auditoría | `GET /audit` |
| Comentarios | `GET /comments`, `DELETE /comments/{id}` |
| Hitos espirituales | `GET /milestones`, `POST /milestones/award` |
| Donaciones | `GET/POST /donation-categories` |
| Automatizaciones | `GET/POST /automations`, `PATCH/DELETE /automations/{id}` |
| Roles modulares | `GET/POST /auth-role-definitions`, `PATCH/DELETE /auth-role-definitions/{id}` |
| Roles por módulo | `GET/POST /user-module-roles`, `DELETE /user-module-roles/{id}` |
| Usuarios con roles | `GET /users-with-roles` |
| Provisionamiento | `POST /provision-accounts` |

---

## Frontend

~30 páginas en `frontend/src/app/plataforma/admin/`. Las principales:

| Ruta | Propósito |
|---|---|
| `/plataforma/admin` | Dashboard con KPIs reales |
| `/plataforma/admin/users` | CRUD de usuarios |
| `/plataforma/admin/roles` | Gestión de roles y permisos |
| `/plataforma/admin/personas` | Listado de personas |
| `/plataforma/admin/finance` | Dashboard financiero |
| `/plataforma/admin/donations` | Gestión de donaciones |
| `/plataforma/admin/audit` | Log de auditoría |
| `/plataforma/admin/cms` | Redirige a CMS |

---

## Tests

| Métrica | Valor |
|---|---|
| Archivo | `tests/test_admin_coverage.py` |
| Tests | 53 |
| Endpoints cubiertos | 40/40 (100%) |
| Última ejecución | 53 passed |

---

## Hallazgos abiertos

| ID | Severidad | Hallazgo |
|---|---|---|
| ADM-G1 | Grave | Colores hardcodeados en 33 archivos frontend |
| ADM-M1 | Medio | 12+ tipos `any` en frontend |
| ADM-M2 | Medio | Consultas directas sin CRUD layer |
| ADM-L1 | Leve | Schemas duplicados para roles |

---

## Documentación relacionada

- `docs/MODULO_ADMIN.md` — Documentación completa del módulo
- `docs/PLAN_ADMIN_CALIDAD.md` — Plan de calidad
- `docs/AUDITORIA_FORENSE_ADMIN.md` — Auditoría forense
- `docs/ADMIN_API_CONTRACTS.md` — Contratos de API
- `docs/ADMIN_QA_CHECKLIST.md` — Checklist de calidad
- `docs/ADMIN_RBAC_MATRIX.md` — Matriz de permisos
- `scripts/test_admin_quality.py` — Smoke script canónico
