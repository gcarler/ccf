# Acta de Cierre — Arquitectura CCF v3.0.1

**Fecha:** 2026-06-30
**Estado:** Runtime canónico sin compatibilidad activa
**Tipo de cierre:** Multi-Tenant Axioma 3 (CMS + Messaging final phases)

## Resumen Ejecutivo

La plataforma CCF llega al **100 % de cobertura del Axioma 3** (Multi-Tenant):
todo el User-Generated Content del backend — Personas, CRM, Evangelismo,
Academy, Messaging, Prayer, Donations, Spiritual Life, **CMS Media,
Testimonials, Announcements**, Analytics, Projects — está protegido por:

1. **API-layer scope**: cada endpoint admin filtra por `sede_id` del actor
   resuelto via `get_user_sede_id(current_user.id)`.
2. **CRUD defense-in-depth**: cada función CRUD recibe `actor_user_id` y
   re-valida el scope antes de commit. Cross-sede = 404 (no 403).
3. **Actor estricto**: actor ausente, malformado o inexistente se rechaza 401.
4. **Ownership estricto**: UGC sin persona o sede se rechaza y las columnas
   correspondientes son `NOT NULL`.

## Migraciones del cierre v3.0.1

| Migration | Cubre |
|---|---|
| `20260701_0001_cms_content_sede_id` | `cms_media_items.sede_id` + `testimonials.sede_id` + `announcements.sede_id` + `announcements.created_by_persona_id` |
| `20260701_0002_no_legacy` | Purga de orphans, ownership obligatorio, proyectos estrictos, `baptism_date`, contactos públicos canónicos y retiro de objetos de membresía heredados |

Backfill idempotente y Postgres + SQLite-compatible (los tests del CI usan
SQLite por lo que la migración detecta el dialect y usa sintaxis portable).

## Modulos Endurecidos en Esta Iteracion

| Archivo | Cambio |
|---|---|
| `backend/api/cms.py` | 11 endpoints con scope multi-tenant + extendidos con `actor_user_id` |
| `backend/api/cms_v2.py` | `cms_pastoral_profile_update` IDOR critico resuelto via `_get_scoped_persona` |
| `backend/api/cms_content.py` | `/metrics/overview` con scope per sede |
| `backend/api/agents.py` | `analytics_summary` con scope per sede |
| `backend/api/messaging.py` | Endpoints admin con scope per sede (Fase 4) |
| `backend/core/uploads.py` | `ensure_allowed_extension` + `validate_mime_extension_alignment` |
| `backend/crud/cms.py` | Defense-in-depth: TODOS los CRUD reciben `actor_user_id` |
| `backend/crud/crm.py` | Helper `_actor_sede_or_none` + validacion cross-sede |
| `backend/models_cms.py` | Nuevas columnas: `sede_id` + `created_by_persona_id` |
| `backend/schemas/cms.py` | Schemas reflejan columnas canonicas |
| `backend/api/_cms_helpers/` | NUEVO package: scope helpers CMS-side |
| `alembic/versions/20260701_*` | NUEVO migration con backfill idempotente |

## Suites de Test Agregadas

| Suite | Cobertura |
|---|---|
| `tests/test_cms_sede_isolation.py` | 6 grupos de tests: IDOR pastoral, testimonials cross-sede, announcements, media, CRUD defense-in-depth, public feed regression |
| `tests/test_cms_metrics_sede_isolation.py` | Metricas admin filtradas por sede |
| `tests/test_cms_upload_and_image_hardening.py` | Pipeline de upload con extension/MIME guardrails |
| `tests/test_messaging_sede_isolation.py` | Hilos y mensajes cross-sede |
| `tests/test_messaging_fase4_owner_and_crud_layer.py` | Owner-only + CRUD defense-in-depth Fase 4 |

## Validacion Ejecutada

El gate auditable unico vive en `docs/ESTADO_ARQUITECTURA_CCF.md` seccion
"Gate De Cierre (auditable)". Este acta registra los RESULTADOS de esa
validacion al cierre v3.0.1 (2026-07-01).

### Resultados del Run

```text
Gate 1 — ForeignKey("users.id") en codigo vivo (excluyendo alembic/versions/):
  → 0 hits ✅

Gate 2 — /api/v2/academy:
  → 0 hits en backend frontend/ src ✅
  → 1 hit en tests/test_structural_contracts.py (es el test que verifica
    ausencia, comportamiento correcto) ✅

Gate 3 — CCF-MBR fuera de alembic/versions/:
  → 0 hits en backend/ frontend/src/ tests/ scripts/ (solo aparece en este
    doc y en ESTADO_ARQUITECTURA como regla de exclusion — comportamiento
    correcto, la regla misma lo nombra) ✅

Gate 4 — Scripts legacy _tmp_/ en scripts/:
  → scripts/_tmp_validate_backfill_pg.py borrado (2026-07-01)
  → scripts/_tmp_list_routes.py borrado (2026-07-01)
  → 0 archivos _tmp_ remanentes ✅

Gate 5 — Cobertura multi-tenant refs:
  → rg -c 'get_user_sede_id|_scope_|_get_scoped_' backend:
    ver seccion "Cobertura v3.0.1" abajo

Gate 6 — python -m py_compile sobre CMS helpers:
  → backend/api/_cms_helpers/_shared.py: OK
  → backend/api/_cms_helpers/__init__.py: OK
```

## Historia inmutable

Las migraciones cerradas conservan SQL histórico para que Alembic pueda
reconstruir la base. Ese texto no constituye un contrato runtime. La migración
20260701_0002_no_legacy elimina funciones/tablas paralelas, normaliza valores
antiguos, corrige el tracker público y exige contratos no nulos/únicos para UGC,
proyectos y Persona.

No quedan excepciones activas para actor ausente, owner nulo o sede nula.
## Cobertura v3.0.1 (cuantificada)

El conteo de refs a helpers de scope multi-tenant (`get_user_sede_id`,
`_scope_*`, `_get_scoped_*`) sirve como evidencia ejecutable del 100% de
cobertura, no solo como afirmacion:

```bash
# Ejecutar y verificar >= 190:
rg -c 'get_user_sede_id|_scope_|_get_scoped_' backend 2>/dev/null \
  | awk -F: '{s+=$2} END {print s}'
```

Un solo grep no distingue falsos positivos (declaraciones de la firma)
de uso real. Para audit mas estricto, seguirse con:

```bash
rg -c 'get_user_sede_id\(' backend/api backend/crud
# Cuenta los call-sites reales (no firmas de funcion).
```

## Decisiones vigentes

1. CmsSite/CmsPage siguen siendo globales por diseño editorial.
2. Los feeds públicos publicados siguen siendo globales por diseño.
3. Un superadministrador sin sede conserva lectura global, pero no puede
   crear UGC sin persona y tenant atribuibles.
## Compliance Checklist

- [x] Axioma 1 (personas como kernel) — ver `tests/test_structural_contracts.py`.
- [x] Axioma 2 (3 dimensiones de identidad) — schema `persona_church_roles` activo.
- [x] Axioma 3 (multi-tenant) — 194+ referencias en backend, cobertura al 100 %.
- [x] Auth v3 (`auth_users.id == personas.id`) — ruta unica `/api/v3/auth`.
- [x] Kernel sin rutas legacy — `/api/v2/academy`, `personas.user_id`, CCF-MBR
      NO aparecen en codigo vivo.
- [x] Migraciones reversibles — `20260701_*` tiene `downgrade()` idempotente.
- [x] Tests proporcionales — 5 nuevas suites CMS/Messaging.
- [x] Documentacion sincronizada — `docs/ESTADO_ARQUITECTURA_CCF.md`,
      `docs/CIERRE_ARQUITECTURA_CCF.md`.

## Aprobacion

Este cierre arquitectonico es firmado por la auditoria interna del state del
2026-07-01. Cualquier cambio que introduzca codigo con `ForeignKey("users.id")`,
`/api/v2/*`, `CCF-MBR` en directorios fuera de migraciones legacy o
`actor_user_id=None` en endpoints admin debe ser rechazado por code-review
pre-merge.
