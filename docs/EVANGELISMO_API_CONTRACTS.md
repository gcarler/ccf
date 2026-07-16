# Contratos API — Evangelismo CCF

> **Objetivo:** documentar el contrato operativo de `/api/evangelism` para que frontend, tests y agentes no cambien endpoints por intuicion. El detalle definitivo vive en codigo; este archivo fija la forma esperada y los riesgos.

Referencia obligatoria de permisos: `docs/EVANGELISMO_RBAC_MATRIX.md`.

## 1. Reglas generales

- Prefijo backend: `/api/evangelism`.
- Prefijo usado por frontend con `apiFetch`: `/evangelism`.
- No usar `fetch` directo en pantallas plataforma salvo excepcion existente y justificada.
- Toda persona es `personas.id` UUID.
- Estrategias y grupos se filtran por `sede_id`.
- Sesiones y asistencias heredan sede por grupo.
- Listados activos excluyen `deleted_at`.
- Evangelismo no usa hoy un solo esquema de guard. Conviven `require_pastor_or_admin`, `require_active_user`, checks contextuales con `get_current_user` y una superficie puntual con `require_module_access("evangelism", action)`.

## 2. Acciones de permiso esperadas

| Accion | Uso esperado |
|---|---|
| `read` | listar/ver estrategias, grupos, sesiones, reportes visibles |
| `edit` | crear/editar asistencia, seguimiento, sesiones operativas |
| `manage` | crear/eliminar estrategias, roles, configuracion, acciones masivas |

`PEND-RBAC-EVANGELISM-001` queda cerrada el **2026-07-16** con `docs/EVANGELISMO_RBAC_MATRIX.md`.

## 3. Estrategias

Archivos:

- `backend/api/evangelism_main/main_estrategias.py`
- `backend/schemas/evangelism.py`

Rutas:

| Metodo | Ruta | Contrato |
|---|---|---|
| `GET` | `/strategies` | Lista estrategias visibles por sede |
| `GET` | `/strategies/{strategy_id}` | Detalle de estrategia |
| `POST` | `/strategies` | Crea estrategia |
| `PUT` | `/strategies/{strategy_id}` | Actualiza estrategia |
| `DELETE` | `/strategies/{strategy_id}` | Soft delete / eliminacion controlada |
| `POST` | `/strategies/{strategy_id}/generate-sessions` | Genera sesiones segun frecuencia |

Reglas:

- `strategy_id` es UUID string.
- No crear sesiones para grupos eliminados.
- Generacion debe respetar frecuencia y sede.
- Esta superficie usa `require_pastor_or_admin`; no asumir `evangelism:manage` directo.

## 4. Roles de estrategia y excusas

Archivo: `backend/api/evangelism_main/main_roles.py`.

Rutas:

| Metodo | Ruta |
|---|---|
| `GET/POST` | `/strategies/{strategy_id}/roles` |
| `DELETE` | `/strategies/{strategy_id}/roles/{role_id}` |
| `GET/POST/PATCH/DELETE` | `/excuses` y `/excuses/{excusa_id}` |
| `POST` | `/excuses/seed` |

Reglas:

- El frontend debe enviar `nombre_rol`.
- La estrategia se identifica por UUID.
- No retornar ORM crudo.

## 5. Grupos

Archivo: `backend/api/evangelism_grupos/grupos_main.py`.

Rutas:

| Metodo | Ruta canonica | Alias |
|---|---|---|
| `GET` | `/grupos` | `/groups` |
| `GET` | `/grupos/mine` | `/groups/mine` |
| `GET` | `/grupos/{grupo_id}` | `/groups/{grupo_id}`, `/micro/{grupo_id}` |
| `POST` | `/grupos` | `/groups` |
| `PUT` | `/grupos/{grupo_id}` | `/groups/{grupo_id}` |
| `DELETE` | `/grupos/{grupo_id}` | `/groups/{grupo_id}` |
| `GET/POST/PATCH` | `/grupos/seasons` | `/groups/seasons` |
| `GET` | `/grupos/analytics` | `/groups/analytics` |
| `POST` | `/grupos/visitors` | `/groups/visitors` |

Reglas:

- `grupo_id` es UUID.
- `estrategia_id`/`evangelism_strategy_id` apunta a estrategia de la misma sede.
- `mine` debe tener comportamiento documentado por rol antes de cambiarlo.
- Delete debe respetar soft delete.
- `/grupos` y `/groups` administrativos usan `require_pastor_or_admin`; `mine` usa auth + chequeo contextual.

## 6. Sesiones

Archivo: `backend/api/evangelism_grupos/grupos_sesiones.py`.

Rutas:

| Metodo | Ruta |
|---|---|
| `GET/POST` | `/sessions` |
| `GET/PUT/DELETE` | `/sessions/{session_id}` |
| `PATCH` | `/sessions/{session_id}/habilitacion` |
| `POST` | `/strategies/{strategy_id}/habilitar-todas` |
| `POST` | `/strategies/{strategy_id}/deshabilitar-todas` |
| `GET/POST` | `/grupos/sessions` y `/groups/sessions` |
| `GET` | `/grupos/sessions/mine/pending` y `/groups/sessions/mine/pending` |
| `GET` | `/personas/search` |

Reglas:

- `session_id` es UUID.
- Sesion pertenece a grupo activo y no eliminado.
- Asistencia requiere `HABILITADO`.
- Aliases `/grupos` y `/groups` deben devolver la misma forma.
- Pendiente: `PEND-SESSIONS-CONTRACT-001`.
- La mayoria de estas rutas usan `require_pastor_or_admin`, pero `/mine/pending` usa auth + chequeo contextual.

## 7. Asistencia y seguimiento

Archivo: `backend/api/evangelism_grupos/grupos_asistencias.py`.

Rutas:

| Metodo | Ruta |
|---|---|
| `GET/POST` | `/sessions/{session_id}/attendance` |
| `GET/POST` | `/grupos/sessions/{session_id}/attendance` |
| `GET/POST` | `/groups/sessions/{session_id}/attendance` |
| `GET` | `/follow-up/pending` |
| `GET/POST` | `/follow-up/{asistencia_id}` |
| `PATCH` | `/follow-up/{seguimiento_id}` |

Reglas:

- Estados de asistencia deben pasar por normalizacion compartida.
- Primera vez puede activar CRM bridge.
- Seguimiento debe retornar schema Pydantic, no ORM.
- Errores de asistencia inexistente deben ser 404.
- La asistencia se protege con `get_current_user` + validacion contextual del grupo; no por `evangelism:edit` puro.

## 8. Eventos

Archivos:

- `backend/api/evangelism_events/events_main.py`
- `backend/api/evangelism_events/events_participantes.py`
- `backend/api/evangelism_events/events_checkin.py`

Rutas:

| Metodo | Ruta |
|---|---|
| `GET/POST` | `/events/` |
| `GET/PUT/DELETE` | `/events/{event_id}` |
| `PUT` | `/events/{event_id}/audience` |
| `GET` | `/events/analytics/global` |
| `GET` | `/events/dashboard-stats` |
| `GET` | `/events/{event_id}/analytics` |
| `GET/POST` | `/events/{event_id}/attendance` |
| `POST` | `/attendance`, `/attendance/bulk` |
| `GET` | `/events/{event_id}/sessions/{session_date}` |
| `POST` | `/events/{event_id}/assignments` |
| `POST` | `/events/{event_id}/sessions/{session_date}/visitors` |
| `GET/POST/PUT/DELETE` | `/events/roles`, `/roles` |

Reglas:

- No devolver ORM crudo en eventos, roles ni attendance history.
- Duplicados de check-in deben responder controladamente, no violar constraint.
- Roles de sistema bloqueados no deben eliminarse sin fallback valido.
- Pendiente: `PEND-EVENTS-CONTRACT-001`.
- Eventos mezcla `require_pastor_or_admin`, `require_active_user` y al menos un endpoint con `require_module_access("evangelism", "read")`.

## 9. Rankings, reportes, analytics y multiplicacion

Archivos:

- `backend/api/evangelism_rankings.py`
- `backend/api/evangelism_reports.py`
- `backend/api/evangelism_analytics.py`
- `backend/api/evangelism_multiplication.py`

Rutas clave:

| Area | Rutas |
|---|---|
| Rankings | `/rankings/groups`, `/rankings/monthly-comparison`, `/rankings/leaders` |
| Reportes | `/reports/group/{grupo_id}/attendance-pdf`, `/attendance-excel`, `/reports/strategy/{strategy_id}/summary` |
| Analytics | `/analytics/strategy/{id}`, `/trend`, `/funnel`, `/heatmap`, `/alerts`, `/velocity`, `/groups`, `/full` |
| Multiplicacion | `/multiplication/check`, `/multiplication/split`, `/multiplication/history` |

Reglas:

- Reportes y rankings deben respetar sede y soft delete.
- Multiplicacion debe retornar 400/404 para precondiciones invalidas, no 500.
- Analytics debe evitar N+1 en caminos principales.
- Rankings, reportes y analytics usan `require_active_user`, no `evangelism:read` uniforme.

## 10. Scanner

Archivo: `backend/api/evangelism.py`.

Rutas:

| Metodo | Ruta |
|---|---|
| `POST` | `/scanner/generate/{persona_id}` |
| `POST` | `/scanner/validate/{token}` |

Reglas:

- Token esperado: `CCF-PER-{persona_id}-{secret}`.
- Hash persistido en persona.
- Token vencido o invalido retorna 403.
- Persona inexistente retorna 404.
- Scanner es la superficie alineada explicitamente con `evangelism:manage` y `evangelism:read`.

## 11. Codigos esperados

| Codigo | Uso |
|---|---|
| `200/201/204` | Operacion exitosa segun metodo |
| `400` | Input invalido o precondicion de negocio |
| `401` | Sin sesion/token valido |
| `403` | Usuario autenticado sin permiso o sesion no habilitada para asistencia |
| `404` | Recurso inexistente o fuera de scope |
| `409` | Duplicado si el endpoint define conflicto explicito |

## 12. Validacion de contratos

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' tests/test_evangelism_module_coverage.py
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_evangelism_triple7_flow.py \
  tests/test_evangelism_crm_bridge.py \
  tests/test_evangelism_reports_api.py \
  tests/test_calculo_sesiones.py
```
