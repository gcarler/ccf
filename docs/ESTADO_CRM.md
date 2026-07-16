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

Pendiente del plan modular:

- Smoke frontend dedicado de CRM `[PEND-FRONTEND-E2E-CRM-001]`

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

**Estado global:** CRM tiene mucha cobertura de pruebas y mucha superficie funcional, pero todavia no tenia documentación canónica por módulo. Es el módulo más sensible porque concentra identidad, consolidación, automations y cruces con evangelismo.

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
| Recursos | `/resources/categorias`, `/resources/plantillas`, `/resources/adjuntos`, `/resources/bitacora`, `/resources/automations` |
| Prayer / Volunteers / Groups | `/prayer-requests*`, `/volunteers*`, `/grupos*`, `/groups`, `/radar`, `/leads/*` |

Detalle y contratos en `docs/CRM_API_CONTRACTS.md`.

---

## 10. Frontend — Mapa de pantallas

Rutas principales en `frontend/src/app/plataforma/crm/`:

| Ruta | Archivo | Estado |
|---|---|---|
| `/plataforma/crm` | `CRMClient.tsx`, `page.tsx` | Hecho — dashboard |
| `/plataforma/crm/personas` | `personas/page.tsx` | **Parcial** — ya tiene paginación real pero requiere smoke frontend dedicado |
| `/plataforma/crm/personas/[id]` | `personas/[id]/page.tsx` | Parcial — detalle complejo, cruza mentoría, timeline e insight |
| `/plataforma/crm/pipeline` | `pipeline/page.tsx` | Hecho funcional, muy sensible a contratos de reorder/kanban |
| `/plataforma/crm/tasks` | `tasks/page.tsx`, `tasks/mine/page.tsx`, `tasks/[id]/page.tsx` | Hecho funcional |
| `/plataforma/crm/counseling` | `counseling/page.tsx`, `[id]/page.tsx` | Hecho funcional |
| `/plataforma/crm/groups` | `groups/page.tsx`, `groups/admin/page.tsx`, `[id]/page.tsx` | Parcial — cruza evangelismo |
| `/plataforma/crm/messaging` | `messaging/page.tsx`, `automations/page.tsx`, `[id]/page.tsx` | Parcial por surface amplia |
| `/plataforma/crm/resources` | `resources/page.tsx`, `builder/page.tsx` | Hecho funcional |
| `/plataforma/crm/volunteers` | `volunteers/page.tsx`, `[id]/page.tsx` | Hecho funcional |
| `/plataforma/crm/prayers` | `prayers/page.tsx`, `[id]/page.tsx` | Hecho funcional |
| `/plataforma/crm/contacts` | `contacts/page.tsx`, `[id]/page.tsx` | Hecho funcional |

No existe todavía suite e2e CRM dedicada en `frontend/tests`.

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

### Parcial

1. **Directorio de personas** `[PARCIAL-PERSONAS-UI-001]` — funcional, pero sin smoke frontend dedicado ni checklist cerrado de filtros/selección masiva.
2. **Detalle de persona** `[PARCIAL-PERSONA-DETAIL-001]` — cruza insight, mentorship, timeline, roles y donaciones; requiere documentación más fina por flujo.
3. **Grupos CRM vs evangelismo** `[PARCIAL-GROUPS-BRIDGE-001]` — las vistas de grupos dentro de CRM dependen de contratos externos de evangelismo.
4. **Automations / pipeline builder** `[PARCIAL-AUTOMATIONS-001]` — fuerte cobertura backend, pero falta gate operativo por módulo y smoke de UI.
5. **Smoke frontend CRM** `[PARCIAL-FRONTEND-SMOKE-001]` — todavía no existe e2e dedicado bajo `frontend/tests`.
6. **Smoke canónico aún parcial** `[PARCIAL-SMOKE-CRM-001]` — `scripts/test_crm_quality.py` ya existe, pero todavía no cubre pipeline visual, concurrency y dashboard.

### Pendiente

1. **E2E CRM** `[PEND-FRONTEND-E2E-CRM-001]` — crear smoke de rutas críticas.
2. **Plan de calidad CRM** `[PEND-PLAN-CRM-001]` — crear documento equivalente a `PLAN_EVANGELISMO_CALIDAD.md` si el módulo empieza a cerrarse por fases.
3. **Matriz RBAC CRM** `[PEND-RBAC-CRM-001]` — documentar permisos por rol para personas, pipeline, counseling, tasks y resources.
4. **Contrato de dashboard CRM** `[PEND-DASHBOARD-CONTRACT-001]` — documentar `/dashboard/crm` porque la UI principal depende de ese endpoint.
5. **Ampliar smoke canónico** `[PEND-EXPAND-SMOKE-CRM-001]` — extender `scripts/test_crm_quality.py` a pipeline, dashboard y concurrency.

---

## 12. Archivos a leer antes de cambiar codigo

1. `docs/ESTADO_CRM.md`
2. `docs/CRM_API_CONTRACTS.md`
3. `docs/CRM_QA_CHECKLIST.md`
4. `backend/api/crm/__init__.py`
5. `backend/api/crm/personas.py`
6. `backend/api/crm/persona_relations.py`
7. `backend/api/crm/pastoral.py`
8. `backend/api/crm/pipelines.py`
9. `backend/api/crm/resources.py`
10. `backend/models_crm.py`
11. `backend/models_crm_pipeline.py`
12. `frontend/src/app/plataforma/crm/personas/page.tsx`
13. `frontend/src/app/plataforma/crm/personas/[id]/page.tsx`
14. `frontend/src/app/plataforma/crm/pipeline/page.tsx`

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
| `PARCIAL-PERSONAS-UI-001` | Directorio de personas sin smoke UI dedicado | `frontend/src/app/plataforma/crm/personas/page.tsx` |
| `PARCIAL-PERSONA-DETAIL-001` | Detalle de persona de alta complejidad | `frontend/src/app/plataforma/crm/personas/[id]/page.tsx` |
| `PARCIAL-GROUPS-BRIDGE-001` | Vistas CRM de grupos dependen de evangelismo | CRM groups + evangelism contracts |
| `PARCIAL-AUTOMATIONS-001` | Pipeline builder y automations sin gate operativo propio | `backend/api/crm/pipelines.py` + frontend CRM messaging/automations |
| `PARCIAL-FRONTEND-SMOKE-001` | CRM sin e2e dedicado | `frontend/tests` |
| `PARCIAL-SMOKE-CRM-001` | Script canónico existe, cobertura aún parcial | `scripts/test_crm_quality.py` |
| `PEND-FRONTEND-E2E-CRM-001` | Smoke frontend CRM | `frontend/tests/e2e/crm/` |
| `PEND-PLAN-CRM-001` | Plan de calidad CRM | `docs/PLAN_CRM_CALIDAD.md` |
| `PEND-RBAC-CRM-001` | Matriz RBAC CRM | docs + backend permissions |
| `PEND-DASHBOARD-CONTRACT-001` | Contrato del dashboard CRM | `/dashboard/crm` |
| `PEND-EXPAND-SMOKE-CRM-001` | Ampliar script CRM a pipeline/dashboard/concurrency | `scripts/test_crm_quality.py` |

Busqueda rapida:

```bash
grep -nE "PARCIAL-|PEND-" /root/ccf/docs/ESTADO_CRM.md
```
