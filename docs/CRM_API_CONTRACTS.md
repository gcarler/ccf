# Contratos API — CRM CCF

> **Objetivo:** fijar el contrato operativo del módulo CRM para backend, frontend, tests y agentes. El código sigue siendo la fuente final, pero este archivo evita cambios por intuición.

## 1. Reglas generales

- Prefijo backend: `/api/crm`
- Prefijo frontend plataforma: `apiFetch('/crm/...')` o endpoints dashboard dedicados como `/dashboard/crm`
- Identidad de persona: `personas.id` UUID
- Sede isolation: cross-sede debe responder `404` en endpoints endurecidos
- Los listados protegidos deben excluir `deleted_at` cuando aplique
- No devolver ORM crudo

## 2. Areas y routers

| Router | Archivo | Responsabilidad |
|---|---|---|
| `personas` | `backend/api/crm/personas.py` | directorio, page API, perfil, timeline, donations, mentorship |
| `persona_relations` | `backend/api/crm/persona_relations.py` | communications, ministries, positions, families, consolidation |
| `pastoral` | `backend/api/crm/pastoral.py` | casos, tasks, counseling, messaging, prayer, volunteers, analytics, groups |
| `pipelines` | `backend/api/crm/pipelines.py` | pipelines, etapas, reorder, kanban, automations |
| `resources` | `backend/api/crm/resources.py` | resource bank, plantillas, categorías, bitácora y campañas |

## 3. Personas

Rutas clave:

| Metodo | Ruta |
|---|---|
| `GET` | `/personas` |
| `GET` | `/personas/page` |
| `GET` | `/personas/me/profile` |
| `PATCH` | `/personas/me/profile` |
| `GET` | `/personas/{persona_id}` |
| `POST` | `/personas` |
| `PUT/PATCH` | `/personas/{persona_id}` |
| `DELETE` | `/personas/{persona_id}` |
| `GET` | `/personas/{persona_id}/timeline` |
| `GET` | `/personas/{persona_id}/donations` |
| `GET` | `/personas/{persona_id}/mentor-candidates` |
| `POST` | `/personas/{persona_id}/mentorship` |

Reglas:

- `persona_id` es UUID string.
- `page` es el contrato preferido para alto volumen.
- Cross-sede sobre detalle o subrutas debe devolver `404`.

## 4. Relaciones de persona

Rutas clave:

| Metodo | Ruta |
|---|---|
| `GET` | `/personas/{persona_id}/communications` |
| `GET` | `/personas/{persona_id}/ministries` |
| `GET` | `/personas/{persona_id}/crm-perfil` |
| `GET` | `/personas/{persona_id}/positions` |
| `GET` | `/personas/{persona_id}/consolidation` |
| `GET/POST/PATCH` | `/positions`, `/positions/{position_id}` |
| `POST/PATCH` | `/personas/{persona_id}/positions*` |
| `POST/PATCH` | `/personas/{persona_id}/ministries*` |
| `GET/POST` | `/families/` |
| `GET` | `/family/{family_id}` |

Reglas:

- Subrutas de persona heredan el mismo scope por sede.
- `families` solo debe exponer familias con miembros en la sede visible del actor.

## 5. Casos, tasks y pastoral

Rutas clave:

| Metodo | Ruta |
|---|---|
| `GET/POST` | `/casos` |
| `GET/PATCH/DELETE` | `/casos/{case_id}` |
| `GET` | `/casos/{case_id}/audit` |
| `GET/POST` | `/casos/{case_id}/interactions` |
| `GET/POST` | `/casos/{case_id}/tasks` |
| `PATCH` | `/casos/{case_id}/tasks/{task_id}` |
| `GET/POST` | `/casos/{case_id}/calls` |
| `GET/POST` | `/tasks`, `/tasks/` |
| `GET` | `/tasks/mine`, `/tasks/{task_id}` |
| `PATCH/DELETE` | `/tasks/{task_id}` |

Reglas:

- `CasoCRM` debe usar pipeline y etapa válidos de la misma sede.
- Reorder y stage changes no deben violar scope.
- `tasks/mine` depende del actor real, no de parámetros del cliente.

## 6. Pipeline y automations

Rutas clave:

| Metodo | Ruta |
|---|---|
| `GET/POST` | `/pipelines` |
| `GET/PUT/DELETE` | `/pipelines/{pipeline_id}` |
| `GET/POST` | `/pipelines/{pipeline_id}/stages` |
| `PUT/DELETE` | `/pipeline-stages/{stage_id}` |
| `PATCH` | `/pipeline/casos/reorder` |
| `GET` | `/pipeline/kanban/*` |
| `POST` | `/pipeline/kanban/drag-drop/*` |
| `GET/POST` | `/automations/palette`, `/automations/flows*` |
| `POST` | `/automations/branching/*`, `/automations/validate-graph`, `/scenarios/*` |

Reglas:

- `CasoCRM.atomic_sort_reorder` es el comportamiento canónico para reorder.
- Cambios en kanban y automations requieren smoke ampliado.
- Si se toca el builder, validar DAG, branching y concurrencia.

## 7. Counseling, messaging, prayer, volunteers

Rutas clave:

| Area | Rutas |
|---|---|
| Counseling | `/counseling/`, `/counseling/{ticket_id}`, `/counseling/{ticket_id}/copilot-draft`, `/counseling/lead/{lead_id}` |
| Messaging | `/messaging/send`, `/messaging/history`, `/messaging/history/{log_id}` |
| Prayer | `/prayer-requests/public`, `/prayer-requests`, `/prayer-requests/{request_id}` |
| Volunteers | `/volunteers`, `/volunteers/{persona_id}` |
| Groups/Radar | `/grupos`, `/grupos/{grupo_id}`, `/groups`, `/radar` |

Reglas:

- Groups dentro de CRM pueden depender de contratos de evangelismo.
- Prayer requests y counseling deben respetar `sede_id` cuando son privados.

## 8. Recursos y plantillas

Prefijo del router: `/resources`

Rutas clave:

| Metodo | Ruta |
|---|---|
| `GET/POST/PATCH/DELETE` | `/resources/categorias*` |
| `GET/POST/PATCH/DELETE` | `/resources/plantillas*` |
| `GET/POST/DELETE` | `/resources/plantillas/{plantilla_id}/adjuntos`, `/resources/adjuntos/{adjunto_id}` |
| `POST` | `/resources/plantillas/{plantilla_id}/enviar` |
| `POST` | `/resources/plantillas/{plantilla_id}/campaign` |
| `GET` | `/resources/plantillas/{plantilla_id}/bitacora`, `/resources/bitacora` |
| `GET/POST/PATCH/DELETE` | `/resources/automations*` |
| `GET/POST` | `/resources/system-templates*` |

Reglas:

- Plantillas, campañas y bitácora son parte del dominio CRM, no del módulo global de messaging.
- Al tocar envíos, validar también logs e adjuntos.

## 9. Dashboard CRM

La UI principal `frontend/src/app/plataforma/crm/CRMClient.tsx` consume:

- `GET /dashboard/crm`

Pendiente:

- Documentar shape exacta de `cards`, `growth_chart` y `pipeline_distribution`
- ID: `PEND-DASHBOARD-CONTRACT-001`

## 10. Códigos esperados

| Codigo | Uso |
|---|---|
| `200/201/204` | operación exitosa |
| `400` | input inválido o precondición de negocio |
| `401` | sin autenticación |
| `403` | autenticado sin permiso cuando el contrato no usa 404 por aislamiento |
| `404` | recurso inexistente o fuera de sede |
| `409` | conflicto explícito si el endpoint lo define |

## 11. Validación mínima

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_crm_domain.py \
  tests/test_crm_sede_isolation.py \
  tests/test_crm_runtime_security.py
```

Validación ampliada:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_crm_persona_mentorship.py \
  tests/test_crm_resource_bank.py \
  tests/test_crm_automations_dag.py \
  tests/test_crm_concurrency_adversarial.py
```
