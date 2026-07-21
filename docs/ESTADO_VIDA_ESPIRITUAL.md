# Estado del Módulo de Vida Espiritual — CCF

> **TL;DR:** El módulo de Vida Espiritual tiene una base funcional mínima: modelo `SpiritualMilestone`, dos endpoints backend y tres páginas frontend. Sin embargo, **no está al 100%**: faltan endpoints de administración, tests propios, validación de tipos de hitos y sincronización real entre frontend y backend.

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

**Hecho:**
- Modelo `SpiritualMilestone` con `deleted_at`, `sede_id`, `persona_id`, `type`, `event_date`, `minister_id`, `notes`.
- Endpoint `GET /api/spiritual-life/milestones/{persona_id}` para lectura de hitos propios o de personas de la misma sede.
- Endpoint `POST /api/spiritual-life/milestones` para crear hitos (requiere `require_admin`, es decir, `system:config`).
- CRUD completo en `backend/crud/crm_/milestones.py`.
- Integración con timeline pastoral y health score.

**Parcial:**
- `POST /milestones` usa `require_admin` en lugar de `spiritual_life:manage` o `spiritual_life:edit`.
- No hay endpoints para editar/eliminar un hito específico.
- No hay endpoint de listado administrativo (`/admin/milestones` no existe, aunque el frontend lo consume).
- El campo `type` es libre (`str`); no hay enum ni catálogo de tipos canónicos.
- No se valida que `persona_id` y `minister_id` pertenezcan a la sede del actor.

**Pendiente:**
- Endpoints REST completos: `GET /milestones`, `GET /milestones/{milestone_id}`, `PATCH /milestones/{milestone_id}`, `DELETE /milestones/{milestone_id}`.
- Endpoint `/spiritual-life/timeline` y `/spiritual-life/certificates` (hoy el frontend llama a `/academy/me/certificates` y a `/spiritual-life/milestones/{id}`).
- Normalización de tipos de hitos (`Decision_Fe`, `Bautismo_Aguas`, etc.).
- Tests propios del módulo (`tests/test_spiritual_life_*.py`).

### 3.2 Frontend

**Hecho:**
- Página de inicio (`/plataforma/spiritual-life`) con KPIs y definición visual de hitos.
- Página de línea de tiempo (`/plataforma/spiritual-life/timeline`).
- Página de certificados (`/plataforma/spiritual-life/certificates`).
- Layout con `WorkspaceLayout` y protección por `spiritual_life:read`.
- Consola administrativa de hitos (`/plataforma/admin/spiritual-life/milestones`).

**Parcial:**
- La página de inicio usa datos demo (`setMilestones(['Decision_Fe', 'Bautismo_Aguas'])`) si el perfil no trae hitos.
- Los enlaces internos usan rutas sin `/plataforma` (`/spiritual-life/timeline` en lugar de `/plataforma/spiritual-life/timeline`).
- La consola admin llama a `/admin/milestones`, endpoint que no existe en backend.
- Los botones de "Registrar Hito", "Descargar PDF", "Validar Código" no tienen acción real.

**Pendiente:**
- Conectar el dashboard a `/spiritual-life/milestones/{persona_id}` real.
- Implementar creación/edición/eliminación de hitos desde la consola admin.
- Normalizar tipos de hitos entre frontend y backend.
- Agregar tests E2E y de integración.

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
| `GET` | `/milestones/{persona_id}` | `get_current_user` | ✅ Funcional |
| `POST` | `/milestones` | `require_admin` | ⚠️ Guard incorrecto |

Rutas que el frontend asume pero no existen:

| Método | Ruta | Estado |
|---|---|---|
| `GET` | `/spiritual-life/timeline` | ❌ No existe |
| `GET` | `/spiritual-life/certificates` | ❌ No existe (frontend usa `/academy/me/certificates`) |
| `GET` | `/admin/milestones` | ❌ No existe |

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

| ID | Tarea | Prioridad |
|---|---|---|
| `SPIRITUAL-API-001` | Exponer PUT/PATCH/DELETE de milestones | P0 |
| `SPIRITUAL-API-002` | Crear endpoint administrativo de listado de milestones | P0 |
| `SPIRITUAL-API-003` | Normalizar `type` a enum/catálogo | P0 |
| `SPIRITUAL-RBAC-001` | Cambiar guard de POST a `spiritual_life:manage` | P0 |
| `SPIRITUAL-FRONT-001` | Conectar dashboard a datos reales | P1 |
| `SPIRITUAL-FRONT-002` | Implementar CRUD de milestones en consola admin | P1 |
| `SPIRITUAL-FRONT-003` | Corregir rutas internas (`/plataforma/spiritual-life/*`) | P1 |
| `SPIRITUAL-TEST-001` | Crear suite de tests backend | P1 |
| `SPIRITUAL-TEST-002` | Crear tests E2E de frontend | P2 |
| `SPIRITUAL-DOCS-001` | Mantener sincronizada documentación | Transversal |

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
