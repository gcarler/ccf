# Estado del Módulo de Vida Espiritual y Discipulado — CCF

**Actualizado:** 2026-09-06 (Auditoría Forense Integral — Certificación 100/100 A+)  
**Veredicto Oficial:** **100/100 (A+) — CERTIFICADO** ([`docs/AUDITORIA_FORENSE_VIDA_ESPIRITUAL_2026-09-06.md`](./AUDITORIA_FORENSE_VIDA_ESPIRITUAL_2026-09-06.md))  
**Audiencia:** desarrolladores, revisores de calidad, equipo pastoral y líderes de discipulado

---

> **TL;DR:** El módulo de Vida Espiritual y Discipulado cuenta con certificación canónica 100/100 (A+): modelo `SpiritualMilestone`, CRUD REST completo (6 endpoints en `/api/spiritual-life` + endpoints admin de insignias en `/api/admin`), guard RBAC canónico (`spiritual_life:read/edit/manage`), aislamiento multi-tenant estricto (`sede_id`), validación de catálogo canónico (`Decision_Fe`, `Bautismo_Aguas`, `Bautismo_Espiritu`, `Persona_Oficial`, `Liderazgo`), 41 tests de backend aprobados al 100% en 4 suites canónicas, y frontend usuario con **Ruta de Discipulado 100% conectada a datos reales** de base de datos. **Estado actual: CERRADO Y CERTIFICADO (100/100 A+).**

---

## 1. Propósito del módulo

Registrar, visualizar y administrar los hitos espirituales y el progreso de discipulado de las personas que hacen parte de CCF (decisión de fe, bautismo en aguas, bautismo del Espíritu, participación oficial, llamado al liderazgo) y vincularlos con:

- La línea de tiempo pastoral (`backend/crud/crm_/timeline.py`).
- El cálculo de salud pastoral (`backend/crud/crm_/health.py`).
- Los certificados de la Academia CCF (`/academy/me/certificates`).
- La Ruta de Discipulado del creyente en la plataforma (`/plataforma/spiritual-life`).

---

## 2. TL;DR — Mapa del módulo

| Capa | Ubicación | Tamaño / Estado |
|---|---|---|
| Modelo de datos | `backend/models_crm.py::SpiritualMilestone` | 1 tabla con soft delete y sede isolation |
| API Router | `backend/api/spiritual_life.py` | 6 endpoints CRUD en `/api/spiritual-life` + 2 en `/api/admin` |
| CRUD | `backend/crud/crm_/milestones.py` | Capa CRUD desacoplada (get, list, create, update, delete) |
| Schemas | `backend/schemas/operational.py` | `MilestoneCreate`, `MilestoneUpdate`, `Milestone` con catálogo canónico |
| Permisos | `backend/core/permissions.py`, `backend/core/kernel_rbac.py` | Taxonomía canónica `spiritual_life:read/edit/manage` |
| Frontend usuario | `frontend/src/app/plataforma/spiritual-life/**` | 3 páginas (dashboard dinámico, timeline, certificados) |
| Frontend admin | `frontend/src/app/plataforma/admin/spiritual-life/milestones/page.tsx` | Consola de hitos conectada a `/admin/milestones` |
| Tests | 4 suites canónicas (`test_spiritual_life_*.py`, `test_admin_milestones_uuid.py`) | **41 tests pasados (100% pass rate)** |
| Invariantes | Backend y Frontend | 0 `db.delete(`, 0 `datetime.utcnow`, 0 modales banned, 0 clases banned |
| Veredicto | Calidad Certificada | **100/100 (A+) — CERTIFICADO** |

---

## 3. Estado actual del módulo

### 3.1 Backend

**Hecho y Certificado:**
- Modelo `SpiritualMilestone` con `deleted_at`, `sede_id`, `persona_id`, `type`, `event_date`, `minister_id`, `notes`.
- CRUD REST completo: `GET /milestones` (listado con sede filter), `GET /milestones/{persona_id}`, `POST /milestones`, `GET /milestone/{milestone_id}`, `PATCH /milestone/{milestone_id}`, `DELETE /milestone/{milestone_id}` (soft delete).
- Guard RBAC canónico: `spiritual_life:read` para lecturas, `spiritual_life:edit` para PATCH/DELETE, `spiritual_life:manage` para POST.
- Sede isolation estricto en todos los endpoints (`_assert_persona_in_sede`, `_assert_milestone_in_sede`) mitigando BOLA con HTTP 404 neutro.
- Enum de tipos canónicos (`Decision_Fe`, `Bautismo_Aguas`, `Bautismo_Espiritu`, `Persona_Oficial`, `Liderazgo`) vía Pydantic `Field(pattern=...)` en `MilestoneCreate`/`MilestoneUpdate`. Tipos inválidos retornan HTTP 422.
- CRUD desacoplado en `backend/crud/crm_/milestones.py` (get, get_milestones, list, create, update, delete).
- Endpoint admin de insignias: `GET /admin/milestones` devuelve `AdminMilestoneRead` con estadísticas de obtención.
- Endpoint admin de award: `POST /admin/milestones/award` con soporte estricto de UUID.
- Integración con timeline pastoral y health score.
- 41 tests de backend aprobados al 100% en 4 suites canónicas.

### 3.2 Frontend

**Hecho y Certificado:**
- Página de inicio (`/plataforma/spiritual-life`) con KPIs y definición visual de hitos — **conectada a datos reales** (`/spiritual-life/milestones/{user.id}`).
- **Ruta de Discipulado (`DISCIPULADO_STEPS`)**: 100% dinámica, calculada reactivamente desde los hitos reales obtenidos de la base de datos (0 datos demo).
- Componente `SpiritualTimelinePanel`: soporte unificado y robusto para claves UUID (`id`) y `milestone_id`.
- Página de línea de tiempo (`/plataforma/spiritual-life/timeline`) — conectada a `/spiritual-life/milestones/{user.id}`, con AbortController + `cache: 'no-store'`.
- Página de certificados (`/plataforma/spiritual-life/certificates`) — conectada a `/academy/me/certificates`.
- Layout con `WorkspaceLayout` y protección por `spiritual_life:read`.
- Consola administrativa de hitos (`/plataforma/admin/spiritual-life/milestones`) — conectada al endpoint real `/admin/milestones`.
- Todos los router paths corregidos (`/plataforma/spiritual-life/*`).
- Botón "Administrar Hitos" en timeline visible solo para `spiritual_life:manage`.
- 0 errores TypeScript (`tsc --noEmit`), 0 warnings ESLint, 0 clases Tailwind vetadas, 0 modales prohibidos.

### 3.3 RBAC Canónico

**Taxonomía canónica implementada y validada:**

| Módulo | Acción | Permission key | Endpoint Asociado |
|---|---|---|---|
| `spiritual_life` | `read` | `spiritual_life:read` | `GET /milestones`, `GET /milestones/{persona_id}`, `GET /milestone/{id}` |
| `spiritual_life` | `edit` | `spiritual_life:edit` | `PATCH /milestone/{id}`, `DELETE /milestone/{id}` |
| `spiritual_life` | `manage` | `spiritual_life:manage` | `POST /milestones` |

---

## 4. Modelo de datos

```
SpiritualMilestone
├── id (UUID, PK)
├── sede_id (UUID → sedes.id, nullable)
├── persona_id (UUID → personas.id, required)
├── type (str, required, validado por catálogo canónico)
├── event_date (date, required)
├── minister_id (UUID → personas.id, nullable)
├── notes (text, nullable)
├── created_at (datetime, UTC)
└── deleted_at (datetime, UTC, nullable)  ← soft delete
```

Relaciones:
- `persona` → `Persona`
- `minister` → `Persona`

---

## 5. API surface canónica

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

---

## 6. Convenciones y decisiones de diseño

- **Soft delete:** todos los registros usan `deleted_at` sin llamadas destructivas a `db.delete(`.
- **Sede isolation (Axioma 3):** 100% implementada y validada mediante `_assert_persona_in_sede` y `_assert_milestone_in_sede`, mitigando BOLA con HTTP 404 neutro.
- **Catálogo canónico de hitos:**
  - `Decision_Fe`
  - `Bautismo_Aguas`
  - `Bautismo_Espiritu`
  - `Persona_Oficial`
  - `Liderazgo`
- **Health score:** los milestones aportan puntos al health score pastoral (ver `backend/crud/crm_/health.py`).
- **Timeline:** los milestones aparecen en la línea de tiempo pastoral unificada.

---

## 7. Cómo probar

### Suite Canónica de Calidad (41 tests)

```bash
cd /root/ccf
./venv/bin/python scripts/test_spiritual_life_quality.py
```

O ejecución directa con pytest:
```bash
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_spiritual_life_api.py \
  tests/test_spiritual_life_extended.py \
  tests/test_spiritual_life_gap.py \
  tests/test_admin_milestones_uuid.py
```

### Verificación Frontend
```bash
cd /root/ccf/frontend
npx tsc --noEmit
npx eslint src/app/plataforma/spiritual-life src/components/spiritual --max-warnings 0
npm test src/lib/workspaceAccess.test.ts
```

---

## 8. Backlog activo

Ver `docs/PLAN_VIDA_ESPIRITUAL_CALIDAD.md` para el plan detallado.

| ID | Tarea | Prioridad | Estado |
|---|---|---|---|
| `SPIRITUAL-API-001` | Exponer PATCH/DELETE de milestones | P0 | ✅ Cerrado |
| `SPIRITUAL-API-002` | Crear endpoint administrativo de listado de milestones | P0 | ✅ Cerrado (`GET /admin/milestones`) |
| `SPIRITUAL-API-003` | Normalizar `type` a enum/catálogo | P0 | ✅ Cerrado (Pydantic pattern) |
| `SPIRITUAL-RBAC-001` | Guard de POST a `spiritual_life:manage` | P0 | ✅ Cerrado |
| `SPIRITUAL-FRONT-001` | Conectar dashboard a datos reales | P1 | ✅ Cerrado |
| `SPIRITUAL-FRONT-002` | Ruta de Discipulado dinámica (0 datos demo) | P1 | ✅ Cerrado |
| `SPIRITUAL-FRONT-003` | Corregir rutas internas (`/plataforma/spiritual-life/*`) | P1 | ✅ Cerrado |
| `SPIRITUAL-TEST-001` | Crear suite de tests backend (41 tests) | P1 | ✅ Cerrado |
| `SPIRITUAL-TEST-002` | Tests de control de acceso frontend (51 tests) | P1 | ✅ Cerrado |
| `SPIRITUAL-DOCS-001` | Certificación forense documental 100/100 A+ | Transversal | ✅ Cerrado (`AUDITORIA_FORENSE_VIDA_ESPIRITUAL_2026-09-06.md`) |

---

## 9. Archivos canónicos de referencia

1. `docs/ESTADO_VIDA_ESPIRITUAL.md` (este archivo)
2. `docs/AUDITORIA_FORENSE_VIDA_ESPIRITUAL_2026-09-06.md` (Dictamen oficial 100/100 A+)
3. `docs/PLAN_VIDA_ESPIRITUAL_CALIDAD.md`
4. `docs/VIDA_ESPIRITUAL_API_CONTRACTS.md`
5. `docs/VIDA_ESPIRITUAL_RBAC_MATRIX.md`
6. `docs/VIDA_ESPIRITUAL_QA_CHECKLIST.md`
7. `scripts/test_spiritual_life_quality.py`
