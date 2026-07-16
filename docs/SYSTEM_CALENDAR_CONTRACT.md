# Contrato Compartido — `/api/system/calendar`

> **Objetivo:** fijar el contrato operativo real del agregador `system/calendar`, que sirve a la vista `/plataforma/calendar` y cruza agenda, CRM, proyectos, evangelismo y cumpleaños. Este contrato pertenece a plataforma compartida.

## 1. Owner y alcance

**Owner tecnico:**

- backend: `backend/api/system.py::get_global_calendar`
- frontend consumidor principal: `frontend/src/app/plataforma/calendar/page.tsx`
- primitive de render: `frontend/src/components/ui/UniversalCalendarView.tsx`

**No pertenece solo a Agenda.**

- `agenda` es una fuente de eventos
- `system/calendar` es el agregador compartido

## 2. Endpoint

| Metodo | Ruta | Auth |
|---|---|---|
| `GET` | `/api/system/calendar` | `require_active_user` |

Query param actual:

| Param | Tipo | Valores |
|---|---|---|
| `view` | `str` | `todo`, `evangelismo`, `crm`, `proyectos`, `personal`, `cumpleanos` |

Default:

- `view=todo`

## 3. Shape de respuesta

Respuesta actual:

- `List[dict]`

Campos operativos esperados por el frontend:

| Campo | Tipo | Obligatorio | Notas |
|---|---|---|---|
| `id` | `str` | si | prefijos por fuente (`estrategia-`, `sesion-`, `crm-caso-`, `crm-tarea-`, `task-`, `milestone-`, `agenda-`, `birthday-`) |
| `title` | `str` | si | texto visible en calendario |
| `start` | `str` ISO datetime/date | si | el frontend lo convierte con `new Date(...)` |
| `end` | `str \| null` | no | puede ser `null` |
| `type` | `str` | si | debe coincidir con `frontend/src/types/calendar.ts` |
| `allDay` | `bool` | no | default frontend `false` si no viene |
| `href` | `str` | no | ruta de navegación interna |
| `location` | `str` | no | solo cuando aplica |

## 4. Tipos canonicos admitidos

El agregador debe emitir solo tipos que el frontend reconoce:

| Tipo | Fuente |
|---|---|
| `evangelism_strategy` | estrategias de evangelismo |
| `evangelism_session` | sesiones de grupo |
| `evangelism_event` | eventos evangelísticos CRM |
| `consolidation_case` | casos CRM con SLA |
| `consolidation_task` | tareas CRM abiertas |
| `task` | tareas de proyecto |
| `project_milestone` | hitos de proyecto |
| `agenda_event` | eventos manuales de agenda |
| `birthday` | cumpleaños |

Regla:

- no reintroducir aliases legacy como `crm_caso` o `crm_tarea`

## 5. Filtros por `view`

### `todo`

- incluye todas las fuentes activas y visibles por sede

### `evangelismo`

- `evangelism_strategy`
- `evangelism_session`
- `evangelism_event`

### `crm`

- `consolidation_case`
- `consolidation_task`

### `proyectos`

- `task`
- `project_milestone`

### `personal`

- `agenda_event`
- `birthday`
- eventos agenda filtrados al `organizador_persona_id` del actor cuando aplica

### `cumpleanos`

- `birthday`

## 6. Scope e invariantes

- requiere usuario activo autenticado
- usa `sede_id` del actor para todas las fuentes multi-tenant
- birthday filtra por `Persona.sede_id == sede_id`
- agenda personal usa `organizador_persona_id == persona_id` cuando `view=personal`
- proyectos permite `Project.sede_id == sede_id` o `NULL`

## 7. Hrefs canónicos

Rutas emitidas actualmente por el agregador:

| Tipo | `href` esperado |
|---|---|
| `evangelism_strategy` | `/plataforma/evangelism/strategies/{id}` |
| `evangelism_session` | `/plataforma/evangelism/grupos/{grupo_id}` |
| `evangelism_event` | `/plataforma/evangelism/events/{id}` |
| `consolidation_case` | `/plataforma/crm/pipeline/{id}` |
| `consolidation_task` | `/plataforma/crm/pipeline/{caso_id}` |
| `task` | `/plataforma/projects/{project_id}` |
| `project_milestone` | `/plataforma/projects/{project_id}` |
| `agenda_event` | `/plataforma/agenda/events/{id}` |
| `birthday` | `/plataforma/crm/personas/{id}` |

Regla:

- no reintroducir rutas legacy como `/plataforma/proyectos/...` o `/plataforma/evangelism/estrategias/...`

## 8. Drift corregido el 2026-07-16

Se corrigen y formalizan estos desalineamientos:

1. `crm_caso` -> `consolidation_case`
2. `crm_tarea` -> `consolidation_task`
3. `/plataforma/proyectos/{id}` -> `/plataforma/projects/{id}`
4. `/plataforma/evangelism/estrategias/{id}` -> `/plataforma/evangelism/strategies/{id}`

## 9. Gate minimo

- `./venv/bin/python scripts/test_agenda_quality.py`
- `./venv/bin/python -m pytest -q -o addopts='' tests/test_fixed_routes.py::TestSystemFixed::test_calendar`
- `./venv/bin/python -m pytest -q -o addopts='' tests/test_system_calendar_contract.py`

## 10. Estado

- `PEND-CALENDAR-EVENTS-CONTRACT-001`: **cerrada el 2026-07-16** con este documento.
