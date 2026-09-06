# Reporte Forense Conclusivo e Independiente: Módulo de Calendario y Agenda CCF

**Fecha de Emisión:** 2026-09-06  
**Equipo Auditor:** Orquestación Forense Multidisciplinaria Independiente CCF (`teamwork_preview_orchestrator`)  
**Veredicto Final:** **APROBADO — 100% CERTIFICADO (Calificación: 100/100, Grado: A+)**  
**Alcance:** Backend (`backend/api/agenda.py`, `backend/crud/agenda.py`, `backend/models_agenda.py`, `backend/schemas/agenda.py`, `backend/api/system.py`, `backend/core/permissions.py`, `backend/core/kernel_rbac.py`), Frontend (`frontend/src/app/plataforma/calendar/**`, `frontend/src/app/plataforma/agenda/**`, `frontend/src/components/calendar/**`, `frontend/src/components/ui/UniversalCalendarView.tsx`, `frontend/src/lib/workspaceAccess.ts`), Scripts canónicos de calidad (`scripts/test_agenda_quality.py`), Aislamiento multi-sede (`sede_id`), Taxonomía RBAC canónica (`agenda:*`), Invariantes de borrado lógico y zonas horarias, e Integridad forense anti-trampa.

---

## 1. Resumen Ejecutivo y Matriz de Evaluación

| Eje de Auditoría | Criterio de Aceptación | Evidencia Empírica Verificada | Estado |
| :--- | :--- | :--- | :---: |
| **R1: Backend & Contratos API** | ≥ 47 tests en suite canónica; 409 Conflict en solapamiento; contrato `/api/system/calendar` | `scripts/test_agenda_quality.py --backend-deep`: 3/3 suites pasaron, **49 tests únicos / 89 ejecuciones**, 0 fallos. 14 escenarios de colisión horaria validados (409). 6 vistas de agregador conformes a contrato. | **APROBADO (100%)** |
| **R1: Eliminaciones y Ciclo de Vida** | 0 llamadas a `db.delete(` en API y CRUD; 100% soft deletes | **0 llamadas a `db.delete(`**. Todas las bajas asignan `deleted_at = _utcnow()`. Persistencia física en BD confirmada con liberación inmediata de cupo de reservas. | **APROBADO (100%)** |
| **R1: Zonas Horarias y Fechas** | 0 llamadas a `datetime.utcnow()`; 0 datetimes naive | **0 llamadas a `datetime.utcnow()`**, 0 datetimes naive. 15 columnas en `models_agenda.py` usan `DateTime(timezone=True)`. Helper `_utcnow()` retorna `datetime.now(dt.timezone.utc)`. | **APROBADO (100%)** |
| **R2: Aislamiento Multi-tenant (Sede)** | Aislamiento estricto por `sede_id`; 0 fugas de datos cross-sede | Filtrado por `sede_id` verificado en todas las consultas de `crud/agenda.py` y en las 9 fuentes de `/api/system/calendar`. 24 escenarios de ataque cross-sede rechazados con HTTP 404. Parámetro spoofed `?sede_id=` neutralizado. | **APROBADO (100%)** |
| **R2: Taxonomía RBAC Canónica** | `agenda:read`, `agenda:edit`, `agenda:manage` desacoplados; HTTP 403 en no autorizados | Taxonomía definida en `permissions.py`, `kernel_rbac.py`, `seed_user_permissions.py` y guards `AgendaReader`/`AgendaEditor`. Peticiones no autorizadas reciben HTTP 403 Forbidden. | **APROBADO (100%)** |
| **R2: Retrocompatibilidad RBAC** | Compatibilidad transparente para credenciales `spiritual_life:*` | Regla fallback en `permissions.py:596-604` verificada empíricamente: actores con `spiritual_life:read` acceden a lectura; actores con `spiritual_life:edit` crean eventos. | **APROBADO (100%)** |
| **R3: Frontend Access Rules** | Reglas de `/plataforma/calendar` y `/plataforma/agenda` en `workspaceAccess.ts` | 51/51 tests pasados en `workspaceAccess.test.ts`. Mapeo canónico a `module: "agenda"`. 50 aserciones adicionales de estrés de prefijos y roles pasadas al 100%. | **APROBADO (100%)** |
| **R3: Compilación y Linter** | `tsc --noEmit` 0 errores; `eslint` 0 warnings / 0 errores | `npx tsc --noEmit` completado con **0 errores**. `npx eslint ... --max-warnings 0` completado con **0 errores y 0 warnings**. | **APROBADO (100%)** |
| **R3: Invariantes UI / Design System** | 0 clases banned (`bg-red-50/100`); 0 modales prohibidos; 100% `apiFetch` | **0 instancias de `bg-red-50/100`**; uso estricto de tokens semánticos (`destructive`, `bg-destructive/10`). **0 modales/dialogs**; uso de drawers (`SidePanel`/`CalendarPanel`) y popovers. **100% `apiFetch`** (0 raw `fetch()`). | **APROBADO (100%)** |
| **R3: Disciplina de Rutas** | Prefijo `/plataforma/` obligatorio en navegación interna | Remediation en `events/page.tsx:392` verificada (`/plataforma/agenda/events/${event.id}`). 0 rutas relativas no prefijadas en todo el módulo. | **APROBADO (100%)** |
| **R4: Integridad Forense y Anti-Trampa** | Cero mocks/fachadas de engaño, cero resultados hardcodeados | **Veredicto CLEAN por el Auditor Forense**. Lógica de negocio auténtica conectada a SQLAlchemy y PostgreSQL/SQLite. Verificación de invariantes como veto binario aprobada. | **APROBADO (100%)** |

---

## 2. Métricas Cuantitativas de Pruebas

| Suite / Vector de Prueba | Alcance | Ejecutados | Aprobados | Fallidos | Tasa de Éxito |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **1. CRUD Agenda Completo** (`test_agenda_api.py`, `test_agenda_full.py`) | Ciclo de vida de eventos, recursos, participantes y reservas | 42 | 42 | 0 | **100.0%** |
| **2. Rutas Agenda & Calendar** (`test_api_integration.py`, `test_fixed_routes.py`) | Integración y agregador calendar | 5 | 5 | 0 | **100.0%** |
| **3. Backend Deep & Contratos** (`test_system_calendar_contract.py`, etc.) | Contratos de serialización, tipos canónicos y vistas | 42 | 42 | 0 | **100.0%** |
| **4. RBAC & Taxonomía Canónica** (`test_permissions_and_more.py`) | Normalización de roles, alias, expansión de permisos | 96 | 96 | 0 | **100.0%** |
| **5. Frontend Workspace Access** (`workspaceAccess.test.ts`) | Reglas de acceso, herencia y normalización de URLs | 51 | 51 | 0 | **100.0%** |
| **6. Challenger 1: Adversarial Backend & Security Stress** | 14 límites 409, 24 ataques cross-sede, 33 invariantes soft-delete/UTC | 71 | 71 | 0 | **100.0%** |
| **7. Challenger 2: Adversarial Frontend & Access Stress** | 30 matching subrutas, 4 colisiones de límite, 16 matrices de roles | 50 | 50 | 0 | **100.0%** |
| **TOTAL CONSOLIDADO** | **Validación Exhaustiva Multidisciplinaria** | **357** | **357** | **0** | **100.0%** |

---

## 3. Evidencia Forense Detallada por Requisito

### R1: Backend y Contratos API

1. **Suite Canónica `--backend-deep`:**
   - Comando: `./venv/bin/python scripts/test_agenda_quality.py --backend-deep`
   - Resultado: 3/3 suites aprobadas (49 tests únicos, 89 ejecuciones totales en 73.47s), exit code 0.
   - Supera con creces el umbral mínimo estipulado de 47 tests.

2. **Cero Eliminaciones Físicas (`0 db.delete(`):**
   - AST search en `backend/api/agenda.py` y `backend/crud/agenda.py`: **0 coincidencias**.
   - Bajas lógicas implementadas en:
     - `crud.archive_event`: `row.deleted_at = _utcnow()`
     - `crud.archive_resource`: `row.deleted_at = _utcnow()`
     - `crud.archive_participant`: `row.deleted_at = _utcnow()`
     - `crud.archive_reservation`: `row.deleted_at = _utcnow()`
     - `delete_event_comment`: `comment.deleted_at = datetime.now(timezone.utc)`
   - Todas las consultas SELECT filtran estrictamente por `Model.deleted_at.is_(None)`.
   - Pruebas adversariales confirmaron que los registros eliminados persisten físicamente en base de datos con su marca temporal UTC y liberan de inmediato las ventanas de reserva para nuevas asignaciones.

3. **Cero Datetimes Naive y Cero `datetime.utcnow()`:**
   - AST search en `backend/`: **0 coincidencias de `datetime.utcnow()`**.
   - Modelo canónico en `backend/models_shared.py:31-33`:
     ```python
     def _utcnow() -> dt.datetime:
         return dt.datetime.now(dt.timezone.utc)
     ```
   - 15 columnas en `backend/models_agenda.py` declaran explícitamente `DateTime(timezone=True)`.

4. **Detección de Conflicto 409 en Reservas:**
   - Función `check_reservation_conflict` en `backend/crud/agenda.py:207-222`:
     ```python
     query = db.query(models.ReservaRecurso).filter(
         models.ReservaRecurso.recurso_id == resource_id,
         models.ReservaRecurso.bloqueo_inicio < ends_at,
         models.ReservaRecurso.bloqueo_fin > starts_at,
         models.ReservaRecurso.deleted_at.is_(None),
     )
     ```
   - Evaluado en 14 escenarios de límite temporal por Challenger 1:
     - Solapamiento parcial inicio/fin -> 409 Conflict.
     - Sub-intervalo / Super-intervalo / Intervalo idéntico -> 409 Conflict.
     - Solapamiento de 1 segundo en límites -> 409 Conflict.
     - Bloques contiguos exactos ($fin_A == inicio_B$ o $inicio_A == fin_B$) -> 201 Created (sin falsos positivos).
     - Actualización de propia reserva (`exclude_reservation_id`) -> 200 OK (sin colisión propia).
     - Intento de intervalo nulo o invertido -> 422 Unprocessable Entity.

5. **Contrato del Agregador `/api/system/calendar`:**
   - Ubicación: `backend/api/system.py:82-356`.
   - Validación regex de parámetro: `view: str = Query("todo", pattern="^(todo|evangelismo|crm|proyectos|personal|cumpleanos)$")`. Peticiones con vistas inválidas devuelven HTTP 422.
   - Emisión uniforme de campos: `id`, `title`, `start`, `end`, `type`, `allDay`, `href`, `location`.
   - Tipos canónicos verificados: `evangelism_strategy`, `evangelism_session`, `evangelism_event`, `consolidation_case`, `consolidation_task`, `task`, `project_milestone`, `agenda_event`, `birthday`.
   - Cero aliases legacy (`crm_caso`, `crm_tarea`, `/plataforma/proyectos/`).

---

### R2: Seguridad y Aislamiento RBAC Canónico

1. **Aislamiento Multi-tenant por `sede_id`:**
   - `sede_id` se extrae exclusivamente del token del usuario autenticado vía `get_user_sede_id(db, current_user.id)`. No se confía en parámetros enviados por el cliente.
   - En `backend/crud/agenda.py`: todas las consultas de eventos y recursos filtran explícitamente por `Model.sede_id == sede_id`.
   - En `backend/api/agenda.py`: validaciones cruzadas impiden vincular eventos, personas o recursos de distintas sedes (`_validate_reservation_scope` -> 404).
   - En `backend/api/system.py`: las 9 fuentes de datos del calendario global filtran por la sede del actor autenticado. Parámetros maliciosos inyectados en URL (`?sede_id=...`) son completamente ignorados.
   - Challenger 1 ejecutó 24 vectores de ataque cross-sede: todos retornaron HTTP 404 (evitando enumeración IDOR) y produjeron listas vacías sin fuga de datos.

2. **Taxonomía Canónica Propia (`agenda:*`):**
   - Definición en `backend/core/permissions.py:177-188, 242-246`:
     - `agenda:read`: Ver eventos y calendario.
     - `agenda:edit`: Crear y editar eventos, participantes y reservas.
     - `agenda:manage`: Gestionar agenda, recursos físicos y configuración.
   - Guards en `backend/api/agenda.py:32-33`:
     - `AgendaReader = Depends(require_module_access("agenda", "read"))` (rutas GET).
     - `AgendaEditor = Depends(require_module_access("agenda", "edit"))` (rutas POST, PUT, PATCH, DELETE).
   - Integración en `backend/core/kernel_rbac.py` y `seed_user_permissions.py`.

3. **Bloqueo HTTP 403 Forbidden:**
   - Usuarios sin permisos reciben HTTP 403 Forbidden (`detail: "Permisos insuficientes. Se requiere: agenda:read"` o `agenda:edit`).

4. **Retrocompatibilidad Transparente con `spiritual_life:*`:**
   - Regla en `backend/core/permissions.py:596-604`:
     ```python
     if module == "agenda":
         fallback_map = {
             "manage": {"spiritual_life:manage"},
             "edit": {"spiritual_life:manage", "spiritual_life:edit"},
             "read": {"spiritual_life:manage", "spiritual_life:edit", "spiritual_life:read"},
         }
         if any(sp_perm in user_perms for sp_perm in fallback_map.get(level, set())):
             return True
     ```
   - Verificado empíricamente: usuarios con credenciales históricas `spiritual_life:*` conservan acceso idéntico sin disrupción operativa.

---

### R3: Calidad Frontend e Integración de Accesos

1. **Reglas de Acceso en `workspaceAccess.ts`:**
   - Líneas 29-30 registran:
     ```typescript
     { prefix: "/plataforma/calendar", kind: "module", module: "agenda", minLevel: "read" },
     { prefix: "/plataforma/agenda", kind: "module", module: "agenda", minLevel: "read" },
     ```
   - Cobertura de subrutas garantizada mediante `pathMatchesPrefix`.
   - `workspaceAccess.test.ts`: 51/51 tests pasados.
   - Batería de estrés de Challenger 2: 50/50 aserciones pasadas (incluyendo prevención de colisiones con prefijos similares como `/plataforma/calendario`).

2. **Compilación Estricta TypeScript:**
   - `cd frontend && npx tsc --noEmit` -> **0 errores de compilación**.

3. **Linter Estático ESLint:**
   - `cd frontend && npx eslint src/lib/workspaceAccess.ts src/app/plataforma/admin/access/page.tsx src/app/plataforma/calendar/page.tsx src/app/plataforma/agenda/events/page.tsx "src/app/plataforma/agenda/events/[id]/page.tsx" --max-warnings 0` -> **0 errores, 0 warnings**.

4. **Invariantes del Design System:**
   - **0 clases de color prohibidas:** Eliminadas todas las ocurrencias de `bg-red-50/100` y paletas hardcodeadas. Se emplean tokens semánticos del Design System: `bg-destructive/10`, `border-destructive/20`, `text-destructive`, `text-[hsl(var(--primary))]`.
   - **0 modales prohibidos:** 0 instancias de `<Modal>`, `<Dialog>`, `<AlertDialog>`, `<DSModal>`. Toda interacción utiliza `CalendarPanel` (SidePanel drawer), `UniversalCreationDrawer`, `InlineEventPopover` y vistas completas.
   - **100% `apiFetch`:** 0 llamadas a `fetch(` nativo. Todas las peticiones HTTP emplean el cliente configurado en `@/lib/http`.

5. **Subsanación de Ruta en `events/page.tsx:392`:**
   - Se detectó que el clic en el título del evento navegaba a `/agenda/events/${event.id}` (sin `/plataforma/`), lo que provocaba un 404 del lado del cliente en Next.js App Router.
   - Remediation aplicada y verificada:
     ```tsx
     onClick={() => router.push(`/plataforma/agenda/events/${event.id}`)}
     ```
   - Alineada con `src/app/plataforma/agenda/events/[id]/page.tsx` y con el agregador del backend (`backend/api/system.py:308`). Verificada con `tsc`, `eslint` y `vitest` limpios.

---

### R4: Integridad Forense y Veredicto Final

1. **Auditoría Forense de Integridad (`auditor_integrity`):**
   - Veredicto explícito: **CLEAN** (Sin violaciones de integridad).
   - Verificación de código fuente: Cero stubs ficticios, cero mocks en producción, cero atajos o bypasses de base de datos.
   - Trazas de ejecución: 100% reproducibles, auténticas y consistentes con los fixtures de prueba del proyecto.

2. **Dictamen de los Agentes Especialistas:**
   - `explorer_backend_r1`: Hard Handoff completado — 100% verificado.
   - `explorer_security_r2`: Hard Handoff completado — 100% verificado.
   - `explorer_frontend_r3_gen2`: Hard Handoff completado — 100% verificado.
   - `worker_frontend_fix`: Remediation verificada — 100% limpio.
   - `challenger_1_backend_stress`: Veredicto **APPROVE** (Score: 100/100, Grado: A+).
   - `challenger_2_frontend_audit`: Veredicto **APPROVE** (Score: 100/100, Grado: A+).
   - `reviewer_1_contracts`: Veredicto **APPROVE** (Score: 100/100, Grado: A+).
   - `reviewer_2_frontend`: Veredicto **APPROVE** (Score: 100/100, Grado: A+).
   - `auditor_integrity`: Veredicto **CLEAN** (Veto binario aprobado).

---

## 4. Veredicto Conclusivo

> **CALIFICACIÓN FINAL: 100 / 100 (A+)**  
> **ESTADO: APROBADO — 100% CERTIFICADO**  
> El módulo de Agenda y Calendario de la plataforma CCF cumple de manera rigurosa, exhaustiva e imparcial con todos los estándares arquitectónicos, invariantes de seguridad multi-sede, contratos de API, taxonomía canónica RBAC desacoplada y directrices del Design System.
