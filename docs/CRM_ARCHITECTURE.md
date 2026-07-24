# Arquitectura del Módulo CRM — Plataforma CCF

> **Documento canónico de arquitectura, reglas de negocio y contratos del módulo CRM.**
> Este archivo es la puerta de entrada para cualquier agente que necesite entender o modificar el CRM.
> Para el estado operativo, backlog y resultados de validación, ver `docs/ESTADO_CRM.md`.
> Para el detalle de endpoints, ver `docs/CRM_API_CONTRACTS.md`.
> Para la matriz de permisos, ver `docs/CRM_RBAC_MATRIX.md`.
> Para el checklist de QA, ver `docs/CRM_QA_CHECKLIST.md`.

---

## 1. Propósito y Alcance

El módulo **CRM (Customer Relationship Management / Consolidación)** de CCF es el centro operativo de gestión de personas, pastoral, pipelines de consolidación y recursos de comunicación.

**Responsabilidades principales:**

- **Directorio de personas:** creación, edición, búsqueda, filtrado, timeline y perfil completo.
- **Gestión pastoral:** casos, tareas, consejería, oraciones, voluntarios, mensajería y grupos.
- **Pipeline de consolidación:** pipelines configurables por sede, etapas, casos y kanban.
- **Recursos y comunicaciones:** plantillas de mensaje, campañas, bitácora de envíos y banco de recursos.
- **Automatizaciones:** flujos de automatización CRM con nodos, edges y evaluación DAG.
- **Puentes con otros módulos:** evangelismo (grupos, estrategias), academy, agenda y plataforma base.

**Principio rector:** el CRM es un módulo sensible que cruza identidad (`personas`), permisos (`auth`), sedes (`sedes`) y otros módulos. Cualquier cambio que toque personas, permisos, `apiFetch`, tablas compartidas o componentes base debe tratarse como cambio de plataforma, no solo de CRM.

---

## 2. Visión General de Arquitectura

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                       │
│  Next.js 14+ (App Router)                                                   │
│  /plataforma/crm/*                                                          │
│  - page.tsx / CRMClient.tsx          → Dashboard principal                  │
│  - /personas, /pipeline, /tasks, /counseling, /groups, /messaging, ...      │
│  - Componentes compartidos: apiFetch, DSSkeleton, DSMetric, DSChart         │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ HTTP / JSON
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND                                        │
│  FastAPI — Prefijo /api/crm                                                 │
│  Router canónico: backend/api/crm/__init__.py                               │
│  - personas          → backend/api/crm/personas.py                          │
│  - persona_relations → backend/api/crm/persona_relations.py                 │
│  - pastoral          → backend/api/crm/pastoral.py                          │
│  - pipelines         → backend/api/crm/pipelines.py                       │
│  - resources         → backend/api/crm/resources.py                         │
│  Dashboard separado: /api/dashboard/crm                                     │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ SQLAlchemy / Alembic
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BASE DE DATOS                                  │
│  PostgreSQL                                                                 │
│  - backend/models_crm.py           → Personas, familias, eventos, ...       │
│  - backend/models_crm_pipeline.py  → Pipelines, etapas, casos, tareas      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Tecnologías y dependencias clave

| Capa | Tecnología | Archivos clave |
|---|---|---|
| Frontend | Next.js 14+, React, TypeScript, Tailwind, Lucide | `frontend/src/app/plataforma/crm/**` |
| Cliente HTTP | `apiFetch` (`frontend/src/lib/http.ts`) | Usado en todas las páginas CRM |
| Backend | FastAPI, SQLAlchemy, Pydantic | `backend/api/crm/**`, `backend/schemas/crm/**` |
| Auth/Permisos | `require_module_access`, `require_pastor_or_admin` | `backend/core/permissions.py` |
| Multi-tenant | `get_user_sede_id` — Axioma 3 | `backend/core/tenant.py` |
| Base de datos | PostgreSQL, Alembic | `backend/models_crm.py`, `backend/models_crm_pipeline.py` |

---

## 3. Organización del Código

### 3.1 Backend

| Archivo / Paquete | Responsabilidad |
|---|---|
| `backend/api/crm/__init__.py` | Router canónico. Agrupa e incluye todos los sub-routers. Exporta helpers de serialización compartidos. |
| `backend/api/crm/personas.py` | CRUD de personas, perfil propio, mentoría, candidatos a mentor, timeline y donaciones. |
| `backend/api/crm/persona_relations.py` | Relaciones de persona: comunicaciones, ministerios, posiciones, familias, consolidación. |
| `backend/api/crm/pastoral.py` | Casos, tareas, mensajería, counseling, oraciones, voluntarios, roles, analytics, grupos. |
| `backend/api/crm/pipelines.py` | Pipelines, etapas, kanban, reorder, drag & drop, automatizaciones y validaciones de flujo. |
| `backend/api/crm/resources.py` | Categorías, plantillas, adjuntos, envíos, campañas, bitácora, automatizaciones resource-bank. |
| `backend/api/crm/_shared.py` | Helpers de serialización y scoping multi-tenant (`_get_scoped_*`). |
| `backend/crud/crm.py` | CRUD legacy/consolidado de personas. |
| `backend/crud/crm_/*.py` | CRUD por subdominio: `personas.py`, `tasks.py`, `events.py`, `extended.py`, `resources.py`, etc. |
| `backend/models_crm.py` | Modelos SQLAlchemy de personas, familias, eventos, recursos, automatizaciones. |
| `backend/models_crm_pipeline.py` | Modelos SQLAlchemy de pipelines, etapas, casos, interacciones y tareas. |
| `backend/schemas/crm/base.py` | Schemas Pydantic base: personas, tareas, eventos, counseling, prayer, donations. |
| `backend/schemas/crm/pipeline.py` | Schemas de pipeline y etapas. |
| `backend/schemas/crm/resources.py` | Schemas de recursos, plantillas, campañas, bitácora. |
| `backend/services/crm_resource_bank.py` | Servicio de banco de recursos. |
| `backend/services/automation_engine.py` | Motor de ejecución de automatizaciones. |

### 3.2 Frontend

| Ruta / Archivo | Responsabilidad |
|---|---|
| `frontend/src/app/plataforma/crm/page.tsx` | Entry point del dashboard. |
| `frontend/src/app/plataforma/crm/CRMClient.tsx` | Dashboard principal. Consume `/api/dashboard/crm`. |
| `frontend/src/app/plataforma/crm/personas/page.tsx` | Directorio de personas (listado, filtros, búsqueda). |
| `frontend/src/app/plataforma/crm/personas/[id]/page.tsx` | Detalle de persona (MESH insight, timeline, mentoría). |
| `frontend/src/app/plataforma/crm/pipeline/page.tsx` | Vista kanban del pipeline. |
| `frontend/src/app/plataforma/crm/tasks/**` | Listado de tareas, tareas propias y detalle. |
| `frontend/src/app/plataforma/crm/counseling/**` | Tickets de consejería. |
| `frontend/src/app/plataforma/crm/groups/**` | Grupos (bridge con evangelismo). |
| `frontend/src/app/plataforma/crm/messaging/**` | Mensajería y automatizaciones. |
| `frontend/src/app/plataforma/crm/resources/**` | Biblioteca de recursos y builder de plantillas. |
| `frontend/src/app/plataforma/crm/volunteers/**` | Voluntarios y turnos. |
| `frontend/src/app/plataforma/crm/prayers/**` | Peticiones de oración. |
| `frontend/src/components/crm/**` | Componentes reutilizables: `CrmShell`, `CrmTableView`, `PipelineKanbanBoard`, etc. |

---

## 4. Modelo de Datos y Entidades Clave

El CRM se divide en **dos dominios principales** modelados en archivos separados.

### 4.1 Dominio persona-pastoral (`backend/models_crm.py`)

| Entidad | Descripción |
|---|---|
| `Persona` | Identidad canónica de una persona. `personas.id` UUID es clave primaria y coincide con `auth_users.id`. |
| `Family` | Familia a la que pertenece una persona. |
| `ChatMessage` / `Conversation` / `ConversationParticipant` | Mensajería interna. |
| `CrmEvent` / `EventAssignment` / `EventAttendance` | Eventos, asignaciones y asistencia. |
| `CounselingTicket` | Tickets de consejería pastoral. |
| `PrayerRequest` | Peticiones de oración (pueden ser públicas o privadas). |
| `Ministry` | Ministerios de la iglesia y asignaciones. |
| `Donation` / `DonationCategory` / `Fund` | Donaciones y fondos asociados a personas. |
| `VolunteerShift` / `VolunteerSkill` | Voluntariado y habilidades. |
| `PersonaMentorship` | Relación mentor-aprendiz entre personas. |
| `CrmAutomation` / `CrmAutomationFlow` / `CrmAutomationNode` / `CrmAutomationEdge` / `PendingCrmAction` | Automatizaciones y flujos. |
| `PlantillaMensaje` / `CategoriaRecurso` / `RecursoAdjunto` / `BitacoraEnvioPlantilla` | Recursos de comunicación. |
| `RoleDefinition` / `PersonaRoleLink` | Definición de roles y asignaciones. |

### 4.2 Dominio pipeline (`backend/models_crm_pipeline.py`)

| Entidad | Descripción |
|---|---|
| `PipelineCRM` | Pipeline configurable por sede y tipo (`NUEVOS_VISITANTES`, `CONSEJERIA`, `RETENCION`, `VOLUNTARIADO`). |
| `EtapaPipeline` | Etapa dentro de un pipeline. Orden secuencial y color visual. |
| `CasoCRM` | Caso/ticket que fluye por el pipeline. Tiene origen, prioridad, estado, SLA y sort_order. |
| `InteraccionCRM` | Bitácora de interacciones de un caso (llamada, WhatsApp, email, etc.). |
| `TareaCRM` | Tarea asociada a un caso o persona. |
| `CrmReorderLock` / `CrmDragDropEvent` | Auxiliares de concurrencia y audit de reorder/drag-drop. |

### 4.3 Relaciones clave

```text
Persona 1──N CasoCRM
Persona 1──N TareaCRM
Persona 1──N VolunteerShift
Persona 1──N Donation
Persona N──M Ministry (via PersonaMinistryAssignment)
Persona N──M Position (via PersonaPosition)

Family 1──N Persona

PipelineCRM 1──N EtapaPipeline
PipelineCRM 1──N CasoCRM
EtapaPipeline 1──N CasoCRM
CasoCRM 1──N InteraccionCRM
CasoCRM 1──N TareaCRM

CrmAutomationFlow 1──N CrmAutomationNode
CrmAutomationNode 1──N CrmFlowBranch
PlantillaMensaje 1──N RecursoAdjunto
PlantillaMensaje 1──N BitacoraEnvioPlantilla
```

---

## 5. Reglas de Negocio Centrales

### 5.1 Sede Isolation (Axioma 3)

- Cada persona, caso, pipeline y plantilla pertenece a una `sede_id`.
- Los endpoints deben filtrar por la sede del usuario autenticado.
- Ante un intento de acceso cross-sede, el contrato es devolver **404** (no 403) para no filtrar la existencia del recurso.
- Helper canónico: `get_user_sede_id(db, user.id)`.
- Helpers de scoping en `backend/api/crm/_shared.py`: `_get_scoped_persona`, `_get_scoped_family`, `_get_scoped_task`, `_get_scoped_plantilla`, etc.

### 5.2 Identidad universal

- `auth_users.id == personas.id` es un contrato global de plataforma.
- No se debe asumir que una persona existe sin auth asociado.

### 5.3 Soft delete

- Las entidades operativas (casos, tareas, plantillas, recursos, eventos, etc.) usan `deleted_at` para borrado lógico.
- Las consultas administrativas deben filtrar `deleted_at IS NULL`.
- `Persona` no tiene `deleted_at`; usa `estado_vital = "INACTIVO"` para soft-delete.

### 5.4 Pipeline y reorder atómico

- `CasoCRM.atomic_sort_reorder(...)` es el único mecanismo canónico para reordenar casos.
- Reglas:
  - Valida que todos los casos pertenezcan a la sede del usuario.
  - Valida que las etapas destino pertenezcan al pipeline del caso.
  - Usa `WITH FOR UPDATE` para evitar condiciones de carrera.
  - Normaliza `sort_order` (sin duplicados, sin nulos).
  - En drag & drop, `atomic_reorder_branching_eval` detecta cambios de etapa y genera `PendingCrmAction` para automatizaciones con trigger `stage_change`.

### 5.5 Automatizaciones

- Las automatizaciones (`CrmAutomation`) se definen como trigger + acción.
- Los flujos (`CrmAutomationFlow`) permiten nodos y edges para modelar DAGs.
- Helper de validación: `validate_three_node_path` garantiza que un flujo tenga al menos 3 nodos.
- El motor en `backend/services/automation_engine.py` procesa las acciones pendientes.

### 5.6 Recursos y mensajería

- `PlantillaMensaje` soporta variables `{{var}}`.
- Cada envío se registra en `BitacoraEnvioPlantilla`.
- Los adjuntos se almacenan con referencia a SeaweedFS (`seaweed_fid`) o URL local.

### 5.7 Contrato del dashboard

- El dashboard CRM vive en `/api/dashboard/crm` (no en `/api/crm`).
- Shape mínima:
  - `cards: MetricCard[]`
  - `growth_chart: ChartDataPoint[]`
  - `pipeline_funnel: FunnelStage[]`
- `CRMClient.tsx` consume solo `cards`, `growth_chart` y `pipeline_funnel`.

---

## 6. Contratos API

### 6.1 Prefijos

| Capa | Prefijo | Ejemplo |
|---|---|---|
| Backend CRM | `/api/crm` | `GET /api/crm/personas` |
| Dashboard CRM | `/api/dashboard/crm` | `GET /api/dashboard/crm` |
| Frontend | `/plataforma/crm` | `/plataforma/crm/personas` |

### 6.2 Áreas del router canónico

| Área | Router | Rutas principales |
|---|---|---|
| Personas | `personas` | `/personas`, `/personas/page`, `/personas/{id}`, `/personas/{id}/timeline`, `/personas/{id}/donations`, `/personas/{id}/mentor-candidates`, `/personas/{id}/mentorship`, `/personas/me/profile` |
| Relaciones | `persona_relations` | `/personas/{id}/communications`, `/personas/{id}/ministries`, `/personas/{id}/positions`, `/personas/{id}/consolidation`, `/families`, `/positions` |
| Pastoral | `pastoral` | `/casos`, `/tasks`, `/counseling`, `/prayer-requests`, `/volunteers`, `/groups`, `/messaging`, `/roles`, `/analytics` |
| Pipelines | `pipelines` | `/pipelines`, `/pipeline-stages`, `/pipeline/casos/reorder`, `/pipeline/kanban/*`, `/automations/*`, `/scenarios/*` |
| Recursos | `resources` | `/resources/categorias`, `/resources/plantillas`, `/resources/adjuntos`, `/resources/bitacora`, `/resources/automations`, `/resources/system-templates` |

### 6.3 Códigos HTTP

| Código | Uso |
|---|---|
| `200` / `201` / `204` | Éxito. |
| `400` | Input inválido o precondición de negocio no cumplida. |
| `401` | Sin autenticación. |
| `403` | Autenticado pero sin permiso (cuando no aplica sede isolation). |
| `404` | Recurso inexistente o fuera de sede. |
| `409` | Conflicto explícito según el endpoint. |

### 6.4 UUIDs

- Todos los IDs de recursos CRM son UUIDs.
- En endpoints REST se reciben como string.

Para el detalle completo de cada endpoint, ver **`docs/CRM_API_CONTRACTS.md`**.

---

## 7. Seguridad y Permisos (RBAC)

### 7.1 Permisos canónicos

| Permiso | Descripción |
|---|---|
| `crm:read` | Lectura de personas, casos, recursos, etc. |
| `crm:edit` | Creación, edición y borrado lógico de registros CRM. |
| `crm:manage` | Acceso total (incluye `crm:edit` y `crm:read`). |
| `profile:manage` | Permite editar el perfil propio (`/personas/me/profile`). |

### 7.2 Roles y permisos efectivos

| Rol persistido | CRM efectivo |
|---|---|
| `ADMINISTRADOR` | `crm:manage` |
| `GESTOR` | `crm:manage` |
| `EDITOR` | `crm:edit` |
| `LECTOR` | `crm:read` (solo si está persistido) |
| `MIEMBRO` | Sin acceso CRM |

**Nota importante:** el fallback runtime del rol `Lector` no recibe permisos CRM. Esto genera una asimetría documentada: `LECTOR` persistido sí puede leer, `Lector` runtime no.

### 7.3 Excepción del pipeline

- Las operaciones de pipeline, kanban y reorder no usan `require_module_access`.
- Usan el helper `require_pastor_or_admin`.
- Implicación: tener `crm:manage` no garantiza por sí solo acceso al pipeline.

### 7.4 Helpers auxiliares de automatización

- Revisados y protegidos con `require_module_access("crm", "read")` o `require_module_access("crm", "edit")` según corresponda.
- Drag & drop de kanban usa `require_pastor_or_admin`.

Para el detalle completo, ver **`docs/CRM_RBAC_MATRIX.md`**.

---

## 8. Frontend: Estructura y Flujo de Datos

### 8.1 Entry points

- `/plataforma/crm` → dashboard principal (`CRMClient.tsx`).
- Navegación lateral o tarjetas de acceso rápido a personas, pipeline, consejería, etc.

### 8.2 Cliente de API

- Todas las peticiones al backend usan `apiFetch` desde `frontend/src/lib/http.ts`.
- El token se extrae del `AuthContext`.
- Ejemplo: `apiFetch('/crm/personas', { token })`.

### 8.3 Patrones de UI

- **Dashboard:** métricas (`DSMetric`), gráficos (`DSChart`) y tarjetas de acceso rápido.
- **Directorio:** tabla (`CrmTableView`) con filtros, búsqueda y paginación.
- **Pipeline:** kanban (`PipelineKanbanBoard`) con columnas, tarjetas y drag & drop.
- **Detalle de persona:** MESH insight, timeline, mentoría y contribuciones.

### 8.4 Bridge con evangelismo

- Los grupos dentro del CRM consumen contratos del módulo de evangelismo.
- Se debe validar que los contratos cruzados no se rompan al cambiar evangelismo.

---

## 9. Testing y QA

### 9.1 Smoke canónico

```bash
cd /root/ccf
./venv/bin/python scripts/test_crm_quality.py
```

### 9.2 Backend mínimo

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_crm_domain.py \
  tests/test_crm_sede_isolation.py \
  tests/test_crm_runtime_security.py
```

### 9.3 Backend ampliado

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_crm_persona_mentorship.py \
  tests/test_crm_resource_bank.py \
  tests/test_crm_automations_dag.py \
  tests/test_crm_concurrency_adversarial.py
```

### 9.4 Frontend E2E

```bash
cd /root/ccf/frontend
npm run test:e2e:crm      # smoke mínimo (14 tests)
npm run test:e2e:crm:deep # circuito profundo (17 tests)
```

### 9.5 Checklist de cierre

- Smoke backend relevante pasa.
- Rutas afectadas probadas manualmente con consola abierta.
- No hay errores `401/403/404/500` no explicados.
- Si se altera un contrato, se actualiza `docs/CRM_API_CONTRACTS.md`.
- Si cambia RBAC, se actualiza `docs/CRM_RBAC_MATRIX.md`.
- Se actualiza `docs/ESTADO_CRM.md` con el estado y la fecha.

Para más detalle, ver **`docs/CRM_QA_CHECKLIST.md`**.

---

## 10. Guía Operativa para Agentes

### 10.1 Antes de tocar código

1. Leer `docs/ESTADO_CRM.md` para conocer el estado actual y pendientes.
2. Identificar si el cambio es de CRM puro o cruza con otra área (auth, sedes, evangelismo, UI base).
3. Revisar `docs/CRM_API_CONTRACTS.md` y `docs/CRM_RBAC_MATRIX.md`.
4. Localizar los endpoints, schemas y modelos afectados.

### 10.2 Al modificar personas

- Validar sede isolation con `_get_scoped_persona` o equivalente.
- Recordar que `PersonaCreate` tiene `extra="forbid"` — no inyectar campos inesperados en el payload.
- El `sede_id` se hereda del usuario autenticado, no del cliente.

### 10.3 Al modificar pipeline

- Usar `CasoCRM.atomic_sort_reorder` para cualquier reorder.
- Probar concurrencia con `tests/test_crm_concurrency_adversarial.py`.
- Recordar que el pipeline usa `require_pastor_or_admin`, no `crm:*`.

### 10.4 Al modificar recursos

- Validar scope de plantilla con `_get_scoped_plantilla`.
- Los envíos deben dejar traza en `BitacoraEnvioPlantilla`.
- Las campañas deben respetar el scope por sede.

### 10.5 Al modificar automatizaciones

- Validar DAG (sin ciclos, sin nodos huérfanos).
- Probar con `tests/test_crm_automations_dag.py`.
- Asegurar que los endpoints auxiliares tengan guard RBAC explícito.

### 10.6 Orden recomendado de trabajo

1. Reproducir la ruta/endpoint con el rol correcto.
2. Correr smoke mínimo.
3. Hacer el cambio.
4. Correr smoke relevante.
5. Si toca frontend, probar manualmente y ejecutar E2E CRM.
6. Actualizar documentación (`ESTADO_CRM.md`, `CRM_API_CONTRACTS.md`, `CRM_RBAC_MATRIX.md` si aplica).
7. Commit atomico.

---

## 11. Historial de cambios en esta documentación

| Fecha | Cambio |
|---|---|
| 2026-07-24 | Creación de `docs/CRM_ARCHITECTURE.md` como documento canónico de arquitectura, reglas de negocio y contratos del CRM. |

---

**Última actualización:** 2026-07-24
