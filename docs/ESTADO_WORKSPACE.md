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

---

## Pendientes

### PEND-WORKSPACE-001 — Mover snapshots de feature flags fuera del árbol de git

**Problema.** La suite de tests del módulo regenera en runtime los archivos `backend/data/feature_flags_*.ndjson` (audit, notifications, snapshot_history) en cada corrida. Al quedar trackeados en git, cada ejecución ensucia el working tree y obliga a revertir manualmente (p. ej. `feature_flags_notifications.ndjson` reverted tras el commit de tests de la sesión 2026-08-02).

**Causa raíz.** `backend/data/feature_flags*.ndjson` ya está en `.gitignore` como *snapshot regenerado bajo demanda*, pero los archivos actuales fueron trackeados antes de esa entrada (git no aplica ignore a archivos ya versionados).

**Fix propuesto.**

- Mover los snapshots de runtime a un directorio fuera del árbol versionado (p. ej. `backend/data/runtime/` o `storage/`) y apuntar el módulo workspace a esa ruta, **o**
- `git rm --cached backend/data/feature_flags_*.ndjson` para des-trackearlos y dejar que el `.gitignore` existente los excluya, regenerándose bajo demanda.

**Gate mínimo para cerrar.**

- `./venv/bin/python -m pytest tests/test_workspace_*.py tests/test_system_final.py`
- `git status --short` limpio después de la corrida (sin modificaciones de runtime).
- `scripts/test_workspace_quality.py` (smoke del módulo).
