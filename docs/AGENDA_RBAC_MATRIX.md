# Matriz RBAC — Agenda / Calendar CCF

> **Objetivo:** fijar la matriz documental de permisos de agenda y su relacion con `calendar`, dejando explicito que agenda usa hoy la taxonomia compartida `spiritual_life:*`.

## 1. Fuentes inspeccionadas

- `backend/api/agenda.py`
- `backend/core/permissions.py`
- `backend/core/kernel_rbac.py`
- `backend/management/seed_user_permissions.py`
- `docs/ESTADO_AGENDA.md`
- `docs/AGENDA_API_CONTRACTS.md`

Fecha de verificacion: **2026-07-16**.

## 2. Taxonomia vigente

Agenda no tiene modulo RBAC propio. Usa la taxonomia compartida:

| Modulo RBAC | Accion | Permission key |
|---|---|---|
| `spiritual_life` | `read` | `spiritual_life:read` |
| `spiritual_life` | `edit` | `spiritual_life:edit` |
| `spiritual_life` | `manage` | `spiritual_life:manage` |

Alias relevante:

- `backend/core/kernel_rbac.py` canoniza `agenda -> spiritual_life`.

## 3. Guards reales en la API propietaria

`backend/api/agenda.py` define:

| Alias local | Guard real |
|---|---|
| `AgendaReader` | `require_module_access("spiritual_life", "read")` |
| `AgendaEditor` | `require_module_access("spiritual_life", "edit")` |

No hay endpoints en `agenda.py` usando `spiritual_life:manage` de forma directa.

## 4. Matriz por superficie

### 4.1 Eventos

| Metodo/Ruta | Guard |
|---|---|
| `GET /agenda/events` | `spiritual_life:read` |
| `GET /agenda/events/by-date-range` | `spiritual_life:read` |
| `GET /agenda/events/{event_id}` | `spiritual_life:read` |
| `POST /agenda/events` | `spiritual_life:edit` |
| `PUT /agenda/events/{event_id}` | `spiritual_life:edit` |
| `DELETE /agenda/events/{event_id}` | `spiritual_life:edit` |

### 4.2 Recursos fisicos

| Metodo/Ruta | Guard |
|---|---|
| `GET /agenda/resources` | `spiritual_life:read` |
| `POST /agenda/resources` | `spiritual_life:edit` |
| `PUT /agenda/resources/{resource_id}` | `spiritual_life:edit` |
| `DELETE /agenda/resources/{resource_id}` | `spiritual_life:edit` |

### 4.3 Participantes

| Metodo/Ruta | Guard |
|---|---|
| `GET /agenda/events/{event_id}/participants` | `spiritual_life:read` |
| `POST /agenda/participants` | `spiritual_life:edit` |
| `PUT /agenda/participants/{participant_id}` | `spiritual_life:edit` |
| `DELETE /agenda/participants/{participant_id}` | `spiritual_life:edit` |

### 4.4 Reservas

| Metodo/Ruta | Guard |
|---|---|
| `GET /agenda/events/{event_id}/reservations` | `spiritual_life:read` |
| `POST /agenda/reservations` | `spiritual_life:edit` |
| `PUT /agenda/reservations/{reservation_id}` | `spiritual_life:edit` |
| `DELETE /agenda/reservations/{reservation_id}` | `spiritual_life:edit` |

## 5. Lectura por rol canonico

Segun `backend/management/seed_user_permissions.py`:

| Rol | spiritual_life |
|---|---|
| `ADMINISTRADOR` | `spiritual_life:manage` |
| `GESTOR` | `spiritual_life:manage` |
| `EDITOR` | `spiritual_life:edit` |
| `LECTOR` | `spiritual_life:read` |
| `MIEMBRO` | sin permisos agenda/spiritual_life |

Interpretacion segura:

- `manage` hereda `edit` y `read`.
- `edit` hereda `read`.
- `LECTOR` puede consultar agenda pero no mutarla.
- `MIEMBRO` no debe acceder a la API propietaria de agenda.

## 6. Relacion con Calendar

`/plataforma/calendar` y `GET /api/system/calendar` no convierten a `calendar` en un modulo RBAC separado.

Reglas:

- La API propietaria de agenda sigue gobernada por `spiritual_life:*`.
- Si falla la agregacion de `system/calendar`, tratarlo como plataforma compartida hasta probar lo contrario.
- No documentar permisos de `calendar` como si fueran identicos a `agenda.py` sin revisar el endpoint agregador.

## 7. Riesgos de drift

1. Si se crea taxonomia `agenda:*` en el futuro, esta matriz y `kernel_rbac.py` deben actualizarse juntos.
2. `AGENDA_API_CONTRACTS.md` no debe hablar de modulo RBAC propio mientras el codigo siga en `spiritual_life:*`.
3. QA de `calendar` debe distinguir errores del CRUD agenda vs errores del agregador compartido.

## 8. Estado del pendiente

- `PEND-AGENDA-RBAC-001`: **cerrada el 2026-07-16** con esta matriz documental.
