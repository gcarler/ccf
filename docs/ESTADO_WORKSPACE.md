# Estado del Módulo Workspace

**Actualizado:** 2026-07-18

---

## Resumen

Módulo de espacio de trabajo transversal. Proporciona pizarra (whiteboard), tareas, calendario, bandeja de entrada y gestión de flags/incidentes. Usado por todos los módulos como infraestructura compartida.

| Métrica | Valor |
|---|---|
| Router | `backend/api/workspace.py` + sub-routers (audit, flags, compliance, incidents, config) |
| Frontend | `frontend/src/app/plataforma/whiteboard/`, `tasks/`, `calendar/` |
| Tests | `tests/test_workspace_api.py` (1 xfailed, 3 xpassed) |
| Docs | `docs/AUDITORIA_TRANSVERSAL_WORKSPACE.md` |

---

## Backend

| Aspecto | Detalle |
|---|---|
| Router | `backend/api/workspace.py` |
| Sub-routers | audit, flags, compliance, incidents, config |

### Submódulos

| Sub-router | Propósito |
|---|---|
| `_audit.py` | Auditoría de eventos |
| `_flags.py` | Banderas/incidentes |
| `_incidents.py` | Gestión de incidentes |
| `_compliance.py` | Cumplimiento |
| `workspace_config.py` | Configuración de workspace |

---

## Frontend

| Ruta | Propósito |
|---|---|
| `/plataforma/whiteboard` | Pizarra colaborativa |
| `/plataforma/tasks` | Gestión de tareas |
| `/plataforma/calendar` | Calendario |

---

## Tests

| Métrica | Valor |
|---|---|
| Archivo | `tests/test_workspace_api.py` |
| Tests | 4 (1 xfailed, 3 xpassed) |
| Smoke script | `scripts/test_workspace_quality.py` |
