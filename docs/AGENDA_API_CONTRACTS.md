# Contratos API — Agenda / Calendar

## 1. Alcance

Este documento cubre:

- API propietaria de agenda: `/api/agenda/*`
- dependencia compartida de la UI de calendario: `GET /api/system/calendar`

## 2. Reglas de contrato

- Frontend usa `apiFetch`.
- `agenda` es autenticada y tenant-scoped.
- `calendar` agrega eventos de varias fuentes; no debe mutar `agenda` de forma directa sin pasar por su contrato.

## 3. `/api/agenda/*`

Archivo: `backend/api/agenda.py`.

| Metodo | Ruta | Permiso esperado |
|---|---|---|
| `GET` | `/agenda/events` | `spiritual_life:read` |
| `GET` | `/agenda/events/by-date-range` | `spiritual_life:read` |
| `POST` | `/agenda/events` | `spiritual_life:edit` |
| `GET` | `/agenda/events/{event_id}` | `spiritual_life:read` |
| `PUT` | `/agenda/events/{event_id}` | `spiritual_life:edit` |
| `DELETE` | `/agenda/events/{event_id}` | `spiritual_life:edit` |
| `GET` | `/agenda/resources` | `spiritual_life:read` |
| `POST` | `/agenda/resources` | `spiritual_life:edit` |
| `PUT` | `/agenda/resources/{resource_id}` | `spiritual_life:edit` |
| `DELETE` | `/agenda/resources/{resource_id}` | `spiritual_life:edit` |
| `GET` | `/agenda/events/{event_id}/participants` | `spiritual_life:read` |
| `POST` | `/agenda/participants` | `spiritual_life:edit` |
| `PUT` | `/agenda/participants/{participant_id}` | `spiritual_life:edit` |
| `DELETE` | `/agenda/participants/{participant_id}` | `spiritual_life:edit` |
| `GET` | `/agenda/events/{event_id}/reservations` | `spiritual_life:read` |
| `POST` | `/agenda/reservations` | `spiritual_life:edit` |
| `PUT` | `/agenda/reservations/{reservation_id}` | `spiritual_life:edit` |
| `DELETE` | `/agenda/reservations/{reservation_id}` | `spiritual_life:edit` |

Invariantes:

- evento inexistente retorna `404`
- `end > start` en `by-date-range`
- persona participante debe pertenecer a la misma sede del actor
- reservas no deben operar sobre recursos/eventos de otra sede
- conflictos de horario en reservas retornan `409`

## 4. `GET /api/system/calendar`

Estado:

- contrato compartido usado por `/plataforma/calendar/page.tsx`
- agrega eventos de multiples modulos para la UI
- contrato formal detallado pendiente en `PEND-CALENDAR-EVENTS-CONTRACT-001`

Minimo que no debe romperse:

- respuesta lista de eventos serializables
- `id`, `title`, `start` y `type` utilizables por la UI
- sin 401/403/500 inesperados para usuarios con acceso valido

## 5. Pendientes de contrato

- `PEND-CALENDAR-EVENTS-CONTRACT-001`
- `PEND-AGENDA-RBAC-001`
