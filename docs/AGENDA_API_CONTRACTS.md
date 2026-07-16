# Contratos API — Agenda / Calendar

## 1. Alcance

Este documento cubre:

- API propietaria de agenda: `/api/agenda/*`
- dependencia compartida de la UI de calendario: `GET /api/system/calendar`

Referencia RBAC: `docs/AGENDA_RBAC_MATRIX.md`.
Referencia agregador compartido: `docs/SYSTEM_CALENDAR_CONTRACT.md`.

## 2. Reglas de contrato

- Frontend usa `apiFetch`.
- `agenda` es autenticada y tenant-scoped.
- `calendar` agrega eventos de varias fuentes; no debe mutar `agenda` de forma directa sin pasar por su contrato.
- Agenda usa hoy `spiritual_life:*`; no existe aun taxonomia `agenda:*` en codigo.

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

Contrato formal:

- ver `docs/SYSTEM_CALENDAR_CONTRACT.md`

Resumen operativo:

- owner: plataforma compartida
- auth: `require_active_user`
- `view` soporta `todo`, `evangelismo`, `crm`, `proyectos`, `personal`, `cumpleanos`
- respuesta: lista de eventos serializables con `id`, `title`, `start`, `end`, `type`, `allDay`, `href`, `location`
- no reintroducir aliases legacy de `type` ni `href`

## 5. Pendientes de contrato

- `PEND-CALENDAR-EVENTS-CONTRACT-001` cerrada el **2026-07-16** con `docs/SYSTEM_CALENDAR_CONTRACT.md`
- `PEND-AGENDA-RBAC-001` cerrada el **2026-07-16** con `docs/AGENDA_RBAC_MATRIX.md`
