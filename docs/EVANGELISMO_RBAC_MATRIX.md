# Matriz RBAC — Evangelismo CCF

> **Objetivo:** documentar el control de acceso real del modulo evangelismo segun el codigo vigente, evitando asumir que todo `/api/evangelism/*` esta protegido de forma uniforme por `evangelism:*`.

## 1. Fuentes inspeccionadas

- `backend/api/evangelism.py`
- `backend/api/evangelism_main/main_estrategias.py`
- `backend/api/evangelism_main/main_roles.py`
- `backend/api/evangelism_grupos/grupos_main.py`
- `backend/api/evangelism_grupos/grupos_sesiones.py`
- `backend/api/evangelism_grupos/grupos_asistencias.py`
- `backend/api/evangelism_events/events_main.py`
- `backend/api/evangelism_events/events_participantes.py`
- `backend/api/evangelism_events/events_checkin.py`
- `backend/api/evangelism_notifications.py`
- `backend/api/evangelism_multiplication.py`
- `backend/api/evangelism_rankings.py`
- `backend/api/evangelism_reports.py`
- `backend/api/evangelism_analytics.py`
- `backend/core/permissions.py`
- `backend/management/seed_user_permissions.py`

Fecha de verificacion: **2026-07-16**.

## 2. Permisos canonicos del modulo

`backend/core/permissions.py` define la taxonomia:

| Modulo | Accion | Permission key |
|---|---|---|
| `evangelism` | `read` | `evangelism:read` |
| `evangelism` | `edit` | `evangelism:edit` |
| `evangelism` | `manage` | `evangelism:manage` |

## 3. Seed canonico vs fallback runtime

Asignacion canonica en `backend/management/seed_user_permissions.py`:

| Rol | Evangelism |
|---|---|
| `ADMINISTRADOR` | `evangelism:manage` |
| `GESTOR` | `evangelism:manage` |
| `EDITOR` | `evangelism:edit` |
| `LECTOR` | `evangelism:read` |
| `MIEMBRO` | sin permisos evangelism |

Regla importante:

- El seed canonico si define evangelismo.
- El fallback `DEFAULT_ROLES` en `backend/core/permissions.py` no es una matriz completa del modulo y no debe usarse como fuente documental para evangelismo.

## 4. Modos reales de proteccion

Evangelismo hoy usa **cuatro modos de acceso**, no uno solo:

1. `require_pastor_or_admin`
2. `require_active_user`
3. `get_current_user` + chequeo contextual de liderazgo, pertenencia o ownership
4. `require_module_access("evangelism", "...")` en endpoints puntuales

Esto significa que `evangelism:*` existe como taxonomia, pero el modulo no esta homogeneamente migrado a esa taxonomia.

## 5. Matriz por superficie

### 5.1 Estrategias, roles y configuracion

| Superficie | Guard real | Observacion |
|---|---|---|
| `main_estrategias.py` | `require_pastor_or_admin` | lista, detalle, creacion, actualizacion, generacion de sesiones |
| `main_roles.py` | `require_pastor_or_admin` | roles personalizados y catalogo de excusas |
| `evangelism_notifications.py` | `require_pastor_or_admin` | recordatorios operativos |
| `evangelism_multiplication.py` | `require_pastor_or_admin` | check, split, history |

### 5.2 Grupos y sesiones

| Superficie | Guard real | Observacion |
|---|---|---|
| `/grupos`, `/groups`, CRUD y resumenes | `require_pastor_or_admin` | gestion administrativa de grupos |
| `/grupos/mine`, `/groups/mine` | `get_current_user` + chequeo contextual | acceso por liderazgo, ownership o rol operativo |
| `/sessions`, `/grupos/sessions`, `/groups/sessions` | mayoritariamente `require_pastor_or_admin` | CRUD y operaciones masivas |
| `/grupos/sessions/mine/pending` | `get_current_user` + chequeo contextual | pendiente personal por liderazgo/pertenencia |

### 5.3 Asistencia y follow-up

| Superficie | Guard real | Observacion |
|---|---|---|
| `GET/POST /sessions/{id}/attendance` | `get_current_user` + `_can_manage_grupo(...)` | no usa `evangelism:edit` directo |
| `GET/POST /grupos/sessions/{id}/attendance` | `get_current_user` + `_can_manage_grupo(...)` | acceso contextual al grupo |
| `GET /follow-up/pending` y mutaciones afines | mezcla de `require_pastor_or_admin` y checks contextuales | revisar archivo propietario antes de asumir permisos |

### 5.4 Eventos

| Superficie | Guard real | Observacion |
|---|---|---|
| CRUD principal y dashboards administrativos | `require_pastor_or_admin` | alta administracion de eventos |
| analytics/participacion/check-in visibles al actor logueado | `require_active_user` | acceso autenticado, no necesariamente admin |
| assignments | `require_pastor_or_admin` | administracion del evento |
| endpoint puntual en `events_main.py` | `require_module_access("evangelism", "read")` | no es la regla global del modulo |

### 5.5 Rankings, reportes y analytics

| Superficie | Guard real |
|---|---|
| `evangelism_rankings.py` | `require_active_user` |
| `evangelism_reports.py` | `require_active_user` |
| `evangelism_analytics.py` | `require_active_user` |

### 5.6 Scanner

| Ruta | Guard real |
|---|---|
| `POST /scanner/generate/{persona_id}` | `require_module_access("evangelism", "manage")` |
| `POST /scanner/validate/{token}` | `require_module_access("evangelism", "read")` |

## 6. Lectura por rol operativo

| Rol | Lectura documental segura |
|---|---|
| `ADMINISTRADOR` | debe pasar todas las superficies propietarias del modulo |
| `GESTOR` | por seed canonico tiene `evangelism:manage`, pero algunas rutas ademas dependen del guard pastoral/admin |
| `EDITOR` | tiene `evangelism:edit`, pero no hay garantia de acceso a superficies gobernadas por `require_pastor_or_admin` |
| `LECTOR` | tiene `evangelism:read`, util sobre scanner/guards modulares puntuales; no garantiza acceso a superficies con guard pastoral/admin |
| `MIEMBRO` | sin permisos evangelism; solo podria entrar donde el guard sea `require_active_user` o contextual y el flujo real lo permita |

## 7. Riesgos de drift

1. `EVANGELISMO_API_CONTRACTS.md` no debe afirmar que todo el modulo usa `require_module_access("evangelism", ...)`.
2. QA no debe tratar un `401/403` en evangelismo como bug automatico sin revisar primero el tipo de guard.
3. Un cambio de permisos en `seed_user_permissions.py` no migra por si solo las superficies que siguen usando `require_pastor_or_admin`.
4. Si el objetivo futuro es homogeneizar el modulo a `evangelism:*`, eso requiere trabajo de backend, tests y rollout; no se debe documentar como si ya existiera.

## 8. Reglas QA derivadas

- Validar por separado:
  - superficies `require_pastor_or_admin`
  - superficies `require_active_user`
  - superficies contextuales de grupo/asistencia
  - scanner con `evangelism:*`
- Ante un cambio de permisos, actualizar:
  - `docs/ESTADO_EVANGELISMO.md`
  - `docs/EVANGELISMO_API_CONTRACTS.md`
  - `docs/EVANGELISMO_QA_CHECKLIST.md`
  - esta matriz

## 9. Estado del pendiente

- `PEND-RBAC-EVANGELISM-001`: **cerrada el 2026-07-16** con esta matriz documental.
