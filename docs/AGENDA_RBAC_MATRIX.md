# Matriz RBAC — Agenda / Calendar CCF

> **Objetivo:** fijar la matriz documental de permisos canónicos de agenda y su relación con `calendar`, documentando la taxonomía independiente propia `agenda:*` y la retrocompatibilidad con `spiritual_life:*`.

## 1. Fuentes inspeccionadas

- `backend/api/agenda.py`
- `backend/core/permissions.py`
- `backend/core/kernel_rbac.py`
- `backend/management/seed_user_permissions.py`
- `frontend/src/lib/workspaceAccess.ts`
- `docs/ESTADO_AGENDA.md`
- `docs/AUDITORIA_FORENSE_AGENDA_2026-09-06.md`
- `docs/AGENDA_API_CONTRACTS.md`

Fecha de certificación: **2026-09-06** (Auditoría Forense Multi-Agente 100/100 A+).

## 2. Taxonomia canónica vigente

Agenda cuenta con su propia taxonomía RBAC desacoplada en `MODULE_PERMISSION_MAP["agenda"]`:

| Modulo RBAC | Accion | Permission key | Descripción |
|---|---|---|---|
| `agenda` | `read` | `agenda:read` | Ver eventos y calendario de la agenda |
| `agenda` | `edit` | `agenda:edit` | Crear y editar eventos, participantes y reservas |
| `agenda` | `manage` | `agenda:manage` | Gestionar agenda, recursos físicos y configuración |

### Retrocompatibilidad Transparente:
Para evitar regresiones en usuarios o roles legacy, `backend/core/permissions.py` y `backend/core/kernel_rbac.py` implementan una regla de fallback automática:
- Actores con `spiritual_life:manage` satisfacen `agenda:manage`, `agenda:edit` y `agenda:read`.
- Actores con `spiritual_life:edit` satisfacen `agenda:edit` y `agenda:read`.
- Actores con `spiritual_life:read` satisfacen `agenda:read`.

## 3. Guards reales en la API propietaria

`backend/api/agenda.py` define:

| Alias local | Guard real | Permiso Canónico |
|---|---|---|
| `AgendaReader` | `require_module_access("agenda", "read")` | `agenda:read` |
| `AgendaEditor` | `require_module_access("agenda", "edit")` | `agenda:edit` |

Adicionalmente, se cuenta con named guards en `permissions.py`:
- `require_agenda_read = require_module_access("agenda", "read")`
- `require_agenda_edit = require_module_access("agenda", "edit")`
- `require_agenda_manage = require_module_access("agenda", "manage")`

## 4. Matriz por superficie

### 4.1 Eventos

| Metodo/Ruta | Guard | Permiso Requerido |
|---|---|---|
| `GET /agenda/events` | `AgendaReader` | `agenda:read` |
| `GET /agenda/events/by-date-range` | `AgendaReader` | `agenda:read` |
| `GET /agenda/events/{event_id}` | `AgendaReader` | `agenda:read` |
| `POST /agenda/events` | `AgendaEditor` | `agenda:edit` |
| `PUT /agenda/events/{event_id}` | `AgendaEditor` | `agenda:edit` |
| `DELETE /agenda/events/{event_id}` | `AgendaEditor` | `agenda:edit` |

### 4.2 Recursos fisicos

| Metodo/Ruta | Guard | Permiso Requerido |
|---|---|---|
| `GET /agenda/resources` | `AgendaReader` | `agenda:read` |
| `POST /agenda/resources` | `AgendaEditor` | `agenda:edit` |
| `PUT /agenda/resources/{resource_id}` | `AgendaEditor` | `agenda:edit` |
| `DELETE /agenda/resources/{resource_id}` | `AgendaEditor` | `agenda:edit` |

### 4.3 Participantes

| Metodo/Ruta | Guard | Permiso Requerido |
|---|---|---|
| `GET /agenda/events/{event_id}/participants` | `AgendaReader` | `agenda:read` |
| `POST /agenda/participants` | `AgendaEditor` | `agenda:edit` |
| `PUT /agenda/participants/{participant_id}` | `AgendaEditor` | `agenda:edit` |
| `DELETE /agenda/participants/{participant_id}` | `AgendaEditor` | `agenda:edit` |

### 4.4 Reservas

| Metodo/Ruta | Guard | Permiso Requerido |
|---|---|---|
| `GET /agenda/events/{event_id}/reservations` | `AgendaReader` | `agenda:read` |
| `POST /agenda/reservations` | `AgendaEditor` | `agenda:edit` |
| `PUT /agenda/reservations/{reservation_id}` | `AgendaEditor` | `agenda:edit` |
| `DELETE /agenda/reservations/{reservation_id}` | `AgendaEditor` | `agenda:edit` |

## 5. Matriz por rol canonico

Según `DEFAULT_ROLES` en `backend/core/permissions.py` y `KERNEL_ROLE_PERMISSIONS` en `backend/core/kernel_rbac.py`:

| Rol | Nivel Canónico | Permisos Efectivos Agenda |
|---|---|---|
| `Super administrador` | `manage` | `agenda:manage`, `agenda:edit`, `agenda:read` |
| `Administrador` | `manage` | `agenda:manage`, `agenda:edit`, `agenda:read` |
| `Gestor` | `manage` | `agenda:manage`, `agenda:edit`, `agenda:read` |
| `Editor` | `edit` | `agenda:edit`, `agenda:read` |
| `Lector` | `read` | `agenda:read` |
| `Miembro` | `read` | `agenda:read` |
| `Estudiante` | `read` | `agenda:read` |
| `Aspirante` | `read` | `agenda:read` |

Interpretación segura:
- `manage` hereda `edit` y `read`.
- `edit` hereda `read`.
- `LECTOR`, `MIEMBRO`, `ESTUDIANTE` y `ASPIRANTE` pueden consultar agenda pero no mutarla.
- Intentos de creación o edición sin `agenda:edit` retornan `403 Forbidden`.

## 6. Relacion con Calendar

`/plataforma/calendar` y `GET /api/system/calendar`:
- La ruta frontend `/plataforma/calendar` y `/plataforma/agenda` están protegidas a nivel de workspace por `workspaceAccess.ts` requiriendo `module: "agenda", minLevel: "read"`.
- `GET /api/system/calendar` agrega eventos de varias fuentes (agenda, evangelismo, proyectos, crm, cumpleaños) y requiere autenticación activa (`require_active_user`).
- El acceso administrativo y gestión de roles se realiza visualmente desde `/plataforma/admin/access` bajo la clave de módulo `agenda`.

## 7. Cierre de Deuda Técnica y Certificación

1. `PEND-AGENDA-RBAC-001`: cerrada con la formalización de la matriz documental.
2. `PARCIAL-AGENDA-RBAC-001`: **CERRADA Y RESUELTA** el **2026-09-06**. La taxonomía canónica `agenda:read`, `agenda:edit`, `agenda:manage` fue implementada y validada en todo el stack.
3. Certificación: **100/100 (A+)** ratificada por auditoría forense independiente y multi-agente Sentinel.
