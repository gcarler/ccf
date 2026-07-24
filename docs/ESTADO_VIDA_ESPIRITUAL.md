# Estado del Módulo de Vida Espiritual — CCF

> **TL;DR:** El módulo de Vida Espiritual tiene base funcional completa: modelo `SpiritualMilestone`, CRUD REST backend (GET list/detail, POST create, PATCH update, DELETE soft-delete), guard RBAC canónico (`spiritual_life:read/edit/manage`), sede isolation, enum de tipos de hitos, 10 tests backend, y endpoint admin de insignias (`/admin/milestones`). El frontend usuario está conectado a datos reales. **Estado actual: P0 cerrado, P1 frontend cerrado.**

---

## 1. Propósito del módulo

Registrar, visualizar y administrar los hitos espirituales de las personas que hacen parte de CCF (decisión de fe, bautismo en aguas, bautismo del Espíritu, participación oficial, llamado al liderazgo) y vincularlos con:

- La línea de tiempo pastoral (`backend/crud/crm_/timeline.py`).
- El cálculo de salud pastoral (`backend/crud/crm_/health.py`).
- Los certificados de la Academia CCF.

---

## 2. TL;DR — Mapa del módulo

| Capa | Ubicación | Tamaño / Estado |
|---|---|---|
| Modelo de datos | `backend/models_crm.py::SpiritualMilestone` | 1 tabla con soft delete y sede isolation |
| API Router | `backend/api/spiritual_life.py` | 2 endpoints (GET/POST milestones) |
| CRUD | `backend/crud/crm_/milestones.py` | 4 funciones (get/create/update/delete) |
| Schemas | `backend/schemas/operational.py::MilestoneCreate/Milestone` | Básicos, sin enum de tipos |
| Permisos | `backend/core/permissions.py`, `backend/core/kernel_rbac.py` | `spiritual_life:read/edit/manage` |
| Frontend usuario | `frontend/src/app/plataforma/spiritual-life/**` | 3 páginas (home, timeline, certificates) |
| Frontend admin | `frontend/src/app/plataforma/admin/spiritual-life/milestones/page.tsx` | Consola de hitos (mock / endpoint no conectado) |
| Tests | `tests/test_api_comprehensive.py`, `tests/test_api_integration.py` | Solo smoke de endpoints inexistentes |

---

## 3. Estado actual del módulo

### 3.1 Backend

**Hecho (P0 cerrado):**
- Modelo `SpiritualMilestone` con `deleted_at`, `sede_id`, `persona_id`, `type`, `event_date`, `minister_id`, `notes`.
- CRUD REST completo: `GET /milestones` (listado con sede filter), `GET /milestones/{persona_id}`, `POST /milestones`, `GET /milestone/{milestone_id}`, `PATCH /milestone/{milestone_id}`, `DELETE /milestone/{milestone_id}` (soft delete).
- Guard RBAC canónico: `spiritual_life:read` para lecturas, `spiritual_life:edit` para PATCH/DELETE, `spiritual_life:manage` para POST.
- Sede isolation en todos los endpoints (`_assert_persona_in_sede`, `_assert_milestone_in_sede`).
- Enum de tipos canónicos (`Decision_Fe`, `Bautismo_Aguas`, `Bautismo_Espiritu`, `Persona_Oficial`, `Liderazgo`) vía Pydantic `Field(pattern=...)` en `MilestoneCreate`/`MilestoneUpdate`.
- CRUD completo en `backend/crud/crm_/milestones.py` (get/get_milestones/list/create/update/delete).
- Endpoint admin de insignias: `GET /admin/milestones` (`backend/api/admin.py:650`) devuelve `AdminMilestoneRead` con estadísticas de obtención.
- Endpoint admin de award: `POST /admin/milestones/award` (`backend/api/admin.py:664`).
- Integración con timeline pastoral y health score.
- 10 tests backend en `tests/test_spiritual_life_api.py` (CRUD + RBAC + validación de tipos + cross-sede).

**Sin deuda P0 pendiente.**

### 3.2 Frontend

**Hecho (P1 cerrado):**
- Página de inicio (`/plataforma/spiritual-life`) con KPIs y definición visual de hitos — **conectada a datos reales** (`/spiritual-life/milestones/{user.id}`).
- Página de línea de tiempo (`/plataforma/spiritual-life/timeline`) — conectada a `/spiritual-life/milestones/{user.id}`, con AbortController + `cache: 'no-store'`.
- Página de certificados (`/plataforma/spiritual-life/certificates`).
- Layout con `WorkspaceLayout` y protección por `spiritual_life:read`.
- Consola administrativa de hitos (`/plataforma/admin/spiritual-life/milestones`) — conectada al endpoint real `/admin/milestones`.
- Todos los router paths corregidos (`/plataforma/spiritual-life/*`).
- Botón "Administrar Hitos" en timeline visible solo para `spiritual_life:manage`.

**Sin deuda P1 pendiente.**

### 3.2.1 Frontend restante (menor, no bloqueante)

- Página de inicio: `DISCIPULADO_STEPS` sigue hardcodeado (datos demo de pasos de discipulado). No hay backend para esto aún.
- Página de certificados: redirige a `/academy/me/certificates`. No hay endpoint `/spiritual-life/certificates` dedicado.

### 3.3 RBAC

**Taxonomía canónica:**

| Módulo | Acción | Permission key |
|---|---|---|
| `spiritual_life` | `read` | `spiritual_life:read` |
| `spiritual_life` | `edit` | `spiritual_life:edit` |
| `spiritual_life` | `manage` | `spiritual_life:manage` |

**Problema actual:** el endpoint de creación usa `require_admin` (`system:config`) en lugar de `spiritual_life:manage`. Esto rompe la taxonomía canónica.

---

## 4. Modelo de datos

```
SpiritualMilestone
├── id (UUID, PK)
├── sede_id (UUID → sedes.id, nullable)
├── persona_id (UUID → personas.id, required)
├── type (str, required)  ← debe normalizarse a enum/catálogo
├── event_date (date, required)
├── minister_id (UUID → personas.id, nullable)
├── notes (text, nullable)
├── created_at (datetime)
└── deleted_at (datetime, nullable)  ← soft delete
```

Relaciones:
- `persona` → `Persona`
- `minister` → `Persona`

---

## 5. API surface actual

Rutas montadas en `/api/spiritual-life`:

| Método | Ruta | Guard | Estado |
|---|---|---|---|
| `GET` | `/milestones` | `spiritual_life:read` | ✅ Funcional |
| `GET` | `/milestones/{persona_id}` | `spiritual_life:read` | ✅ Funcional |
| `POST` | `/milestones` | `spiritual_life:manage` | ✅ Funcional |
| `GET` | `/milestone/{milestone_id}` | `spiritual_life:read` | ✅ Funcional |
| `PATCH` | `/milestone/{milestone_id}` | `spiritual_life:edit` | ✅ Funcional |
| `DELETE` | `/milestone/{milestone_id}` | `spiritual_life:edit` | ✅ Funcional (soft delete) |

Rutas admin de insignias en `/api/admin`:

| Método | Ruta | Guard | Estado |
|---|---|---|---|
| `GET` | `/admin/milestones` | `require_active_user` | ✅ Funcional |
| `POST` | `/admin/milestones/award` | `require_admin` | ✅ Funcional |

### Rutas que el frontend asume pero no existen en `/spiritual-life`:

| Método | Ruta | Estado |
|---|---|---|
| `GET` | `/spiritual-life/timeline` | ❌ No existe (frontend lee `/milestones/{persona_id}` directamente) |
| `GET` | `/spiritual-life/certificates` | ❌ No existe (frontend usa `/academy/me/certificates`) |

---

## 6. Convenciones y decisiones de diseño

- **Soft delete:** todos los registros usan `deleted_at`.
- **Sede isolation:** el modelo tiene `sede_id`, pero los endpoints no la validan aún.
- **Tipos de hitos:** actualmente son strings libres. Se propone normalizar a un catálogo canónico:
  - `Decision_Fe`
  - `Bautismo_Aguas`
  - `Bautismo_Espiritu`
  - `Persona_Oficial`
  - `Liderazgo`
- **Health score:** los milestones aportan puntos al health score pastoral (ver `backend/crud/crm_/health.py`).
- **Timeline:** los milestones aparecen en la línea de tiempo pastoral unificada.

---

## 7. Cómo probar

### Smoke rápido

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' tests/test_api_comprehensive.py::TestSpiritualLifeEndpoints tests/test_api_integration.py::TestSpiritualLifeAPI
```

### Tests propios (pendientes)

```bash
./venv/bin/python -m pytest -q -o addopts='' tests/test_spiritual_life_api.py
```

---

## 8. Backlog activo

Ver `docs/PLAN_VIDA_ESPIRITUAL_CALIDAD.md` para el plan detallado.

| ID | Tarea | Prioridad | Estado |
|---|---|---|---|
| `SPIRITUAL-API-001` | Exponer PUT/PATCH/DELETE de milestones | P0 | ✅ Cerrado |
| `SPIRITUAL-API-002` | Crear endpoint administrativo de listado de milestones | P0 | ✅ Cerrado (`GET /admin/milestones`) |
| `SPIRITUAL-API-003` | Normalizar `type` a enum/catálogo | P0 | ✅ Cerrado (Pydantic pattern) |
| `SPIRITUAL-RBAC-001` | Cambiar guard de POST a `spiritual_life:manage` | P0 | ✅ Cerrado |
| `SPIRITUAL-FRONT-001` | Conectar dashboard a datos reales | P1 | ✅ Cerrado |
| `SPIRITUAL-FRONT-002` | Implementar CRUD de milestones en consola admin | P1 | ✅ Cerrado (consola sigue /admin/milestones) |
| `SPIRITUAL-FRONT-003` | Corregir rutas internas (`/plataforma/spiritual-life/*`) | P1 | ✅ Cerrado |
| `SPIRITUAL-TEST-001` | Crear suite de tests backend | P1 | ✅ Cerrado (10 tests) |
| `SPIRITUAL-TEST-002` | Crear tests E2E de frontend | P2 | ⬜ Pendiente |
| `SPIRITUAL-DOCS-001` | Mantener sincronizada documentación | Transversal | ✅ Cerrado (esta actualización) |

---

## 9. Archivos a leer primero

1. `docs/ESTADO_VIDA_ESPIRITUAL.md` (este archivo)
2. `docs/VIDA_ESPIRITUAL_API_CONTRACTS.md`
3. `docs/VIDA_ESPIRITUAL_RBAC_MATRIX.md`
4. `docs/PLAN_VIDA_ESPIRITUAL_CALIDAD.md`
5. `backend/api/spiritual_life.py`
6. `backend/crud/crm_/milestones.py`
7. `backend/models_crm.py::SpiritualMilestone`
8. `frontend/src/app/plataforma/spiritual-life/**`
9. `frontend/src/app/plataforma/admin/spiritual-life/milestones/page.tsx`
