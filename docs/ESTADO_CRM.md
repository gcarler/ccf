# Estado del Modulo de CRM — CCF

> **TL;DR (una linea):** CRM es el centro de consolidacion de CCF: personas, familias, pipeline pastoral, casos, tareas, consejeria, prayer requests, voluntariado, mensajeria, grupos, recursos y automatizaciones. Es el modulo con mas cruces hacia `personas`, `auth`, `sede_id`, evangelismo y proyectos.

**Proposito.** Handover canonico para que cualquier sesion nueva pueda trabajar CRM como unidad propia y no mezclar correcciones con evangelismo, proyectos o capas compartidas sin evidencia.

**Regla de uso.**

- Actualizar este doc al cerrar tareas, no antes.
- `Hecho / Parcial / Pendiente` reflejan el codigo actual.
- No usar este doc como wishlist.
- Si un cambio toca `Persona`, permisos, `apiFetch`, tablas compartidas o componentes UI base, tratarlo como cambio de plataforma, no solo de CRM.

---

## 1. Leer primero (cualquier agente)

```bash
cat /root/ccf/docs/ESTADO_CRM.md
cat /root/ccf/docs/CRM_API_CONTRACTS.md
cat /root/ccf/docs/CRM_RBAC_MATRIX.md
cat /root/ccf/docs/CRM_QA_CHECKLIST.md
cat /root/ccf/docs/PLAN_ARQUITECTURA_MODULAR_CCF.md
```

## 2. Verificar entorno

```bash
python3 --version && node --version
```

Versiones verificadas en este host el **2026-07-16**:

- Python: **3.12.3**
- Node: **v24.15.0**

## 3. Recontar superficie vigente (por si drift)

```bash
wc -l /root/ccf/backend/api/crm/*.py /root/ccf/backend/crud/crm.py /root/ccf/backend/crud/crm_/*.py /root/ccf/backend/models_crm.py /root/ccf/backend/models_crm_pipeline.py /root/ccf/backend/schemas/crm/*.py /root/ccf/backend/schemas/crm_pipeline.py /root/ccf/backend/schemas/crm_resources.py /root/ccf/backend/services/crm_resource_bank.py 2>/dev/null | tail -1
wc -l /root/ccf/frontend/src/app/plataforma/crm/**/*.tsx /root/ccf/frontend/src/app/plataforma/crm/*.tsx 2>/dev/null | tail -1
```

Conteo actual:

- Backend CRM directo: **13 806 LOC**
- Frontend CRM directo: **8 911 LOC**

## 4. Listar backlog completo (Parcial + Pendiente) por ID

```bash
grep -nE "PARCIAL-|PEND-" /root/ccf/docs/ESTADO_CRM.md
```

## 5. Smoke test

Smoke canonico:

```bash
cd /root/ccf
./venv/bin/python scripts/test_crm_quality.py
```

Smoke minimo bruto:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_crm_domain.py \
  tests/test_crm_sede_isolation.py \
  tests/test_crm_runtime_security.py
```

Smoke ampliado si se toca pipeline, visual, recursos, concurrencia o automations:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_crm_persona_mentorship.py \
  tests/test_crm_resource_bank.py \
  tests/test_crm_automations_dag.py \
  tests/test_crm_concurrency_adversarial.py
```

**Estado actual (2026-07-18):**
- Backend smoke mínimo: **47 passed** ✅
- Backend RBAC HTTP: **31 passed** ✅
- Frontend smoke dedicado (`npm run test:e2e:crm`): **14 passed** ✅
- Frontend deep smoke (`npm run test:e2e:crm:deep`): **17 passed** ✅
- Backend deep (`scripts/test_crm_quality.py --backend-deep --pipeline --concurrency`): **24 + 99 + 21 passed** ✅
- Auditoría canónica: los bloques equivalentes quedaron validados el **2026-07-18** con `47 passed` backend smoke, `31 passed` RBAC HTTP, `14 passed` frontend smoke, `17 passed` frontend deep y `5/5 suites` backend deep sobre el runner estable `build + next start` ✅

Pendiente del plan modular:

- Cobertura profunda del detalle de persona `[PARCIAL-FRONTEND-SMOKE-001]` — **HECHO** con mocks en `persona-detail.spec.ts`, `dashboard.spec.ts` y `groups-admin.spec.ts`
- Cobertura profunda de `messaging`, `resources` y `pipeline` visual — **HECHO** dentro del circuito `test:e2e:crm:deep`

---

## 6. TL;DR — Mapa del modulo

| Capa | Ubicacion | Tamano |
|---|---|---:|
| Router canonico | `backend/api/crm/__init__.py` | agrega personas, relaciones, pastoral, pipelines y recursos |
| API personas | `backend/api/crm/personas.py` | personas, perfil, timeline, donations, mentorship |
| API relaciones | `backend/api/crm/persona_relations.py` | comunicaciones, ministerios, posiciones, familias, consolidation |
| API pastoral | `backend/api/crm/pastoral.py` | casos, tasks, counseling, prayer, volunteers, analytics, groups, messaging |
| API pipelines | `backend/api/crm/pipelines.py` | pipelines, etapas, reorder, kanban, automations |
| API recursos | `backend/api/crm/resources.py` | plantillas, categorias, adjuntos, campañas, bitacora, resource bank |
| Modelos base CRM | `backend/models_crm.py` | personas relacionadas, eventos, consejeria, oraciones, voluntariado y mas |
| Modelos pipeline | `backend/models_crm_pipeline.py` | pipelines, etapas, casos, interacciones, tareas |
| CRUD | `backend/crud/crm.py`, `backend/crud/crm_/` | dominio repartido por subareas |
| Servicio | `backend/services/crm_resource_bank.py` | banco de recursos |
| UI principal | `frontend/src/app/plataforma/crm/**` | dashboard, personas, pipeline, tasks, counseling, groups, messaging, resources, volunteers |
| Tests backend | `tests/test_crm_*.py` | dominio, seguridad, isolation, automations, concurrencia, visual, stress |

**Estado global:** CRM quedó cerrado operativamente al **100%** y revalidado el **2026-07-18** para esta línea de trabajo: contratos, bridge con evangelismo, builder de automatizaciones, smoke vivo autenticado, backend profundo y cobertura frontend profunda pasan sobre el código y el harness actual. Sigue siendo un módulo sensible por identidad, consolidación, automations y cruces con evangelismo, pero ya no queda deuda abierta de cierre funcional dentro del plan actual.

---

## 7. Convenciones del modulo

- **Ruta plataforma:** `/plataforma/crm`
- **Ruta API:** `/api/crm`
- **Cliente frontend:** usar `apiFetch(...)` o `apiFetch('/dashboard/crm', ...)` según el contrato del dashboard.
- **Identidad canonica:** `personas.id` UUID es la clave real de la persona.
- **Auth:** `auth_users.id == personas.id` es contrato global.
- **Sede isolation:** endpoints endurecidos deben aplicar `sede_id` y devolver `404` cross-sede, no `403`.
- **Soft delete:** casos, tasks y registros operativos protegidos no deben asumir hard delete.
- **Pipeline:** reorder debe respetar atomicidad y scope por sede.
- **Bridge evangelismo -> CRM:** no hardcodear pipeline ni etapa.

---

## 8. Backend — Modelo de datos

CRM se divide en dos dominios principales:

```text
Persona / Family / Ministry / Messaging / Counseling / Prayer / Volunteers / Events
PipelineCRM / EtapaPipeline / CasoCRM / InteraccionCRM / TareaCRM
```

Piezas clave en `backend/models_crm.py`:

- `Family`
- `ChatMessage`
- `Conversation`, `ConversationParticipant`
- `CrmEvent`, `EventAssignment`, `EventAttendance`
- `CounselingTicket`
- `PrayerRequest`
- `Ministry`
- `Persona` y relaciones asociadas en el archivo completo

Piezas clave en `backend/models_crm_pipeline.py`:

- `PipelineCRM`
- `EtapaPipeline`
- `CasoCRM`
- enums `TipoPipelineEnum`, `EstadoCasoEnum`, `PrioridadCasoEnum`, `CanalOrigenEnum`

Punto sensible:

- `CasoCRM.atomic_sort_reorder(...)` ya es referencia canónica de reorder con validación de `sede_id` y lock transaccional.

---

## 9. Backend — API surface

Router canonico: `backend/api/crm/__init__.py`

Subrouters incluidos:

- `personas`
- `persona_relations`
- `pastoral`
- `pipelines`
- `resources`

Areas principales:

| Area | Rutas clave |
|---|---|
| Personas | `/personas`, `/personas/page`, `/personas/{id}`, `/personas/{id}/timeline`, `/personas/{id}/donations`, `/personas/{id}/mentor-candidates`, `/personas/{id}/mentorship` |
| Relaciones | `/personas/{id}/communications`, `/ministries`, `/positions`, `/families`, `/family/{id}`, `/consolidation` |
| Casos | `/casos`, `/casos/{id}`, `/casos/{id}/audit`, `/casos/{id}/interactions`, `/casos/{id}/tasks`, `/casos/{id}/calls` |
| Tasks | `/tasks`, `/tasks/mine`, `/tasks/{id}` |
| Counseling | `/counseling/`, `/counseling/{id}`, `/counseling/{id}/copilot-draft` |
| Messaging | `/messaging/send`, `/messaging/history` |
| Pipelines | `/pipelines`, `/pipelines/{id}`, `/pipelines/{id}/stages`, `/pipeline/casos/reorder`, `/pipeline/kanban/*`, `/automations/*` |
| Recursos | `/resources/categorias`, `/resources/plantillas`, `/resources/adjuntos`, `/resources/bitacora`, `/resources/automations`, `/resources/automation-edges` |
| Prayer / Volunteers / Groups | `/prayer-requests*`, `/volunteers*`, `/grupos*`, `/groups`, `/radar`, `/leads/*` |

Detalle y contratos en `docs/CRM_API_CONTRACTS.md`.

---

## 10. Frontend — Mapa de pantallas

Rutas principales en `frontend/src/app/plataforma/crm/`:

| Ruta | Archivo | Estado |
|---|---|---|
| `/plataforma/crm` | `CRMClient.tsx`, `page.tsx` | Hecho — dashboard |
| `/plataforma/crm/personas` | `personas/page.tsx` | Hecho funcional con smoke vivo autenticado de búsqueda y navegación al detalle |
| `/plataforma/crm/personas/[id]` | `personas/[id]/page.tsx` | Hecho funcional con smoke profundo y navegación viva desde directorio |
| `/plataforma/crm/pipeline` | `pipeline/page.tsx` | Hecho funcional, muy sensible a contratos de reorder/kanban |
| `/plataforma/crm/tasks` | `tasks/page.tsx`, `tasks/mine/page.tsx`, `tasks/[id]/page.tsx` | Hecho funcional |
| `/plataforma/crm/counseling` | `counseling/page.tsx`, `[id]/page.tsx` | Hecho funcional |
| `/plataforma/crm/groups` | `groups/page.tsx`, `groups/admin/page.tsx`, `[id]/page.tsx` | Hecho funcional con bridge evangelismo encapsulado y smoke real/admin |
| `/plataforma/crm/messaging` | `messaging/page.tsx`, `automations/page.tsx`, `[id]/page.tsx` | Hecho funcional con cobertura profunda |
| `/plataforma/crm/resources` | `resources/page.tsx`, `builder/page.tsx`, `builder/[id]/page.tsx` | Hecho funcional con builder canónico por id |
| `/plataforma/crm/volunteers` | `volunteers/page.tsx`, `[id]/page.tsx` | Hecho funcional |
| `/plataforma/crm/prayers` | `prayers/page.tsx`, `[id]/page.tsx` | Hecho funcional |
| `/plataforma/crm/contacts` | `contacts/page.tsx`, `[id]/page.tsx` | Hecho funcional |

Existe suite e2e CRM dedicada en `frontend/tests/e2e/crm/`, con smoke mínimo y circuito profundo canónico.

---

## 11. Estado del modulo

### Hecho

- Router canonico `/api/crm` separado por dominios.
- CRUD principal de personas, familias, casos, tasks, pipelines y recursos.
- Cross-sede hardening cubierto por tests.
- Pipeline con reorder atómico por sede.
- Banco de recursos, plantillas y campañas.
- Mentoría de personas y candidatos de mentor.
- Dashboard CRM en frontend.
- **Contrato lazy de wiki compartida CRM** alineado el **2026-07-18**: `useWikiDocument` dejó de depender de páginas presembradas y `GET /api/wiki/pages/{page_key}` materializa documento virtual vacío para superficies colaborativas como `crm_pipeline_wiki_notes`.
- **Contrato dashboard alineado (2026-07-16):** corregido drift `pipeline_distribution` → `pipeline_funnel` en `CRMClient.tsx:94`; frontend usa `cards` + `growth_chart` + `pipeline_funnel` según contrato `CrmDashboard`.

### Parcial

No quedan frentes parciales activos dentro del plan de cierre fino ejecutado y revalidado al **2026-07-18**. Los IDs históricos se conservan abajo como trazabilidad, pero su estado real en esta fecha es **cerrado**.

### Pendiente

1. **E2E CRM** `[PEND-FRONTEND-E2E-CRM-001]` — cerrada el 2026-07-16 con `frontend/tests/e2e/crm/smoke.spec.ts`; fija smoke mínimo de dashboard, personas y pipeline con guard de consola/API/assets.
2. **Plan de calidad CRM** `[PEND-PLAN-CRM-001]` — cerrada el 2026-07-16 en `docs/PLAN_CRM_CALIDAD.md`; fija fases operativas para personas, dashboard, pipeline, bridge con evangelismo y smoke frontend.
3. **Matriz RBAC CRM** `[PEND-RBAC-CRM-001]` — cerrada el 2026-07-16 en `CRM_RBAC_MATRIX.md`; documenta la matriz real por superficie y deja explícitas las asimetrías entre roles persistidos, fallback runtime y pipeline.
4. **Contrato de dashboard CRM** `[PEND-DASHBOARD-CONTRACT-001]` — cerrada el 2026-07-16 en `docs/CRM_API_CONTRACTS.md`; fija la shape operativa de `GET /api/dashboard/crm` y la separa del router `/api/crm`.
5. **Ampliar smoke canónico** `[PEND-EXPAND-SMOKE-CRM-001]` — cerrado operacionalmente y revalidado el **2026-07-18** para el alcance actual mediante `npm run test:e2e:crm`, `npm run test:e2e:crm:deep`, backend smoke `46 passed` y RBAC HTTP `31 passed`.

**Actualizacion QA 2026-07-18:** el runner `frontend/scripts/run-managed-playwright.mjs` quedó estabilizado estructuralmente: limpia `.next`, hace `build` limpio, arranca `next start` en un puerto dedicado, espera readiness explícita y luego ejecuta Playwright. También `scripts/test_crm_quality.py` quedó ajustado para hacer streaming de los checks frontend largos. Con esa base, el cierre del CRM quedó validado con `npm run test:e2e:crm` = **14 passed**, `npm run test:e2e:crm:deep` = **17 passed**, backend smoke = **47 passed**, RBAC HTTP = **31 passed** y backend deep = **5/5 suites verdes**.

---

## 12. Archivos a leer antes de cambiar codigo

1. `docs/ESTADO_CRM.md`
2. `docs/CRM_API_CONTRACTS.md`
3. `docs/CRM_RBAC_MATRIX.md`
4. `docs/CRM_QA_CHECKLIST.md`
5. `backend/api/crm/__init__.py`
6. `backend/api/crm/personas.py`
7. `backend/api/crm/persona_relations.py`
8. `backend/api/crm/pastoral.py`
9. `backend/api/crm/pipelines.py`
10. `backend/api/crm/resources.py`
11. `backend/models_crm.py`
12. `backend/models_crm_pipeline.py`
13. `frontend/src/app/plataforma/crm/personas/page.tsx`
14. `frontend/src/app/plataforma/crm/personas/[id]/page.tsx`
15. `frontend/src/app/plataforma/crm/pipeline/page.tsx`

---

## 13. Orden operativo recomendado

1. Reproducir con ruta exacta y rol real.
2. Identificar si el problema es de CRM puro o de plataforma compartida.
3. Correr smoke mínimo.
4. Si toca personas/auth/sede/permisos, revisar antes contratos globales.
5. Si toca pipeline, validar reorder y kanban.
6. Si toca groups dentro de CRM, validar contratos cruzados con evangelismo.
7. Si toca frontend, probar manualmente las rutas críticas del checklist.

---

## 14. Tabla de IDs estables

| ID | Pieza | Archivo o area |
|---|---|---|
| `PARCIAL-PERSONAS-UI-001` | ✅ Cerrado y revalidado 2026-07-18 — directorio y navegación viva verificados en `personas-live.spec.ts` | `frontend/src/app/plataforma/crm/personas/page.tsx` |
| `PARCIAL-PERSONA-DETAIL-001` | ✅ Cerrado y revalidado 2026-07-18 — detalle profundo validado en `persona-detail.spec.ts` y navegación viva desde directorio | `frontend/src/app/plataforma/crm/personas/[id]/page.tsx` |
| `PARCIAL-GROUPS-BRIDGE-001` | ✅ Cerrado y revalidado 2026-07-18 — bridge CRM↔evangelismo validado en smoke mockeado y live | CRM groups + evangelism contracts |
| `PARCIAL-AUTOMATIONS-001` | ✅ Cerrado y revalidado 2026-07-18 — builder usa contrato estable `automation-edges` con gateway Next compatible new/legacy y smoke live verde | `backend/api/crm/resources.py` + frontend CRM automations builder |
| `PARCIAL-FRONTEND-SMOKE-001` | ✅ Cerrado y revalidado 2026-07-18 — `npm run test:e2e:crm` verde con 14 tests | `frontend/tests/e2e/crm/` |
| `PARCIAL-SMOKE-CRM-001` | ✅ Cerrado y revalidado 2026-07-18 — circuito profundo verde con 17 tests y backend base verde | `scripts/test_crm_quality.py` |
| `PEND-FRONTEND-E2E-CRM-001` | ✅ **Hecho 2026-07-16** — smoke frontend CRM dedicado para dashboard, personas y pipeline con guard de consola/API/assets. | `frontend/tests/e2e/crm/smoke.spec.ts` |
| `PEND-PLAN-CRM-001` | ✅ **Hecho 2026-07-16** — plan de calidad CRM documentado por fases, con foco en personas, dashboard, pipeline, bridge con evangelismo y smoke frontend. | `docs/PLAN_CRM_CALIDAD.md` |
| `PEND-RBAC-CRM-001` | ✅ **Hecho 2026-07-16** — matriz RBAC CRM documentada con contrato actual, asimetría `LECTOR` persistido vs fallback runtime y excepción de pipeline/automations. | `docs/CRM_RBAC_MATRIX.md` |
| `PEND-DASHBOARD-CONTRACT-001` | ✅ **Hecho 2026-07-16** — contrato del dashboard CRM documentado con shape `CrmDashboard` y consumo real desde `CRMClient.tsx`. | `docs/CRM_API_CONTRACTS.md` |
| `PEND-EXPAND-SMOKE-CRM-001` | Ampliar script CRM a pipeline/dashboard/concurrency | `scripts/test_crm_quality.py` |

Busqueda rapida histórica:

```bash
grep -nE "PARCIAL-|PEND-" /root/ccf/docs/ESTADO_CRM.md
```
