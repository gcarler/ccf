# Contratos API — Evangelismo CCF

> **Objetivo:** fijar el contrato operativo real de `/api/evangelism` para frontend, tests y mantenimiento.
>
> **Fecha de verificación:** 2026-07-17
> **Fuente de verdad:** código en `backend/api/evangelism*.py`, `backend/schemas/evangelism.py`, `backend/core/permissions.py`

## 1. Reglas generales

- Prefijo backend: `/api/evangelism`
- Prefijo frontend vía `apiFetch`: `/evangelism`
- Todas las pantallas de plataforma deben usar `apiFetch`
- Toda identidad de persona en evangelismo debe resolverse contra `personas.id`
- Estrategias y grupos respetan `sede_id`
- Sesiones, asistencias, analytics, rankings y reportes respetan sede a través de grupo o validación directa
- Los listados activos excluyen `deleted_at` cuando la entidad soporta soft delete

## 2. Modelo de acceso

Evangelismo se documenta desde la taxonomía canónica del módulo:

| Acción | Permission key |
|---|---|
| leer | `evangelism:read` |
| operar | `evangelism:edit` |
| gestionar | `evangelism:manage` |

Pero no toda ruta es RBAC puro:

- Superficies administrativas usan `require_evangelism_*`
- Rutas personales y de asistencia de grupo usan `get_current_user` + validación contextual
- Check-in rápido de visitantes en eventos usa `require_active_user`
- Scanner usa `require_module_access("evangelism", ...)`, equivalente funcional a la taxonomía canónica

Referencia obligatoria: [EVANGELISMO_RBAC_MATRIX.md](/root/ccf/docs/EVANGELISMO_RBAC_MATRIX.md)

## 3. Router canónico

Archivo: `backend/api/evangelism.py`

El router principal monta:

- eventos
- grupos
- estrategias
- roles y excusas
- multiplicación
- notificaciones
- rankings
- reportes
- analytics
- scanner

## 4. Estrategias

Archivo: `backend/api/evangelism_main/main_estrategias.py`

| Método | Ruta | Guard |
|---|---|---|
| `GET` | `/strategies` | `require_evangelism_read` |
| `GET` | `/strategies/{strategy_id}` | `require_evangelism_read` |
| `GET` | `/strategies/{strategy_id}/metrics` | `require_evangelism_read` |
| `POST` | `/strategies` | `require_evangelism_manage` |
| `PUT` | `/strategies/{strategy_id}` | `require_evangelism_manage` |
| `DELETE` | `/strategies/{strategy_id}` | `require_evangelism_manage` |
| `POST` | `/strategies/{strategy_id}/generate-sessions` | `require_evangelism_manage` |

Reglas:

- `strategy_id` es UUID
- Estrategias se filtran por sede
- Crear estrategia sin `sede_id` derivable del usuario debe fallar
- La proyección de fases a proyectos para `evento_masivo` es auxiliar y no debe romper la estrategia si falla

## 5. Roles de estrategia y excusas

Archivo: `backend/api/evangelism_main/main_roles.py`

| Método | Ruta | Guard |
|---|---|---|
| `GET` | `/strategies/{strategy_id}/roles` | `require_evangelism_manage` |
| `POST` | `/strategies/{strategy_id}/roles` | `require_evangelism_manage` |
| `DELETE` | `/strategies/{strategy_id}/roles/{role_id}` | `require_evangelism_manage` |
| `GET` | `/excuses` | `require_evangelism_manage` |
| `POST` | `/excuses` | `require_evangelism_manage` |
| `PATCH` | `/excuses/{excusa_id}` | `require_evangelism_manage` |
| `DELETE` | `/excuses/{excusa_id}` | `require_evangelism_manage` |
| `POST` | `/excuses/seed` | `require_evangelism_manage` |

Reglas:

- `strategy_id` y `role_id` son UUID
- Los roles personalizados deben pertenecer a la estrategia y sede válidas
- El catálogo de excusas no debe retornar ORM crudo

## 6. Grupos

Archivo: `backend/api/evangelism_grupos/grupos_main.py`

| Método | Ruta canónica | Alias | Guard |
|---|---|---|---|
| `GET` | `/grupos` | `/groups` | `require_evangelism_read` |
| `GET` | `/grupos/mine` | `/groups/mine` | `get_current_user` |
| `GET` | `/grupos/{grupo_id}` | `/groups/{grupo_id}`, `/micro/{grupo_id}` | `require_evangelism_read` |
| `POST` | `/grupos` | `/groups` | `require_evangelism_manage` |
| `PUT` | `/grupos/{grupo_id}` | `/groups/{grupo_id}` | `require_evangelism_manage` |
| `DELETE` | `/grupos/{grupo_id}` | `/groups/{grupo_id}` | `require_evangelism_manage` |
| `GET/POST/PATCH` | `/grupos/seasons` | `/groups/seasons` | canónico según operación |
| `GET` | `/grupos/analytics` | `/groups/analytics` | `require_evangelism_read` |
| `POST` | `/grupos/visitors` | — | `require_evangelism_manage` |

Reglas:

- `grupo_id` es UUID
- Los aliases `/grupos` y `/groups` deben mantener la misma forma contractual
- `mine` es contextual: liderazgo/ownership, no solo permiso granular
- El detalle administrativo serializa dicts compatibles con frontend, no ORM crudo

## 7. Sesiones

Archivo: `backend/api/evangelism_grupos/grupos_sesiones.py`

| Método | Ruta | Guard |
|---|---|---|
| `GET` | `/grupos/sessions`, `/groups/sessions` | `require_evangelism_read` |
| `GET` | `/grupos/sessions/mine/pending`, `/groups/sessions/mine/pending` | `get_current_user` |
| `POST` | `/grupos/sessions`, `/groups/sessions` | `require_evangelism_manage` |
| `GET` | `/sessions` | `require_evangelism_read` |
| `POST` | `/sessions` | `require_evangelism_manage` |
| `GET` | `/sessions/{session_id}` | `require_evangelism_read` |
| `PUT` | `/sessions/{session_id}` | `require_evangelism_manage` |
| `DELETE` | `/sessions/{session_id}` | `require_evangelism_manage` |
| `PATCH` | `/sessions/{session_id}/habilitacion` | `require_evangelism_manage` |
| `POST` | `/strategies/{strategy_id}/habilitar-todas` | `require_evangelism_manage` |
| `POST` | `/strategies/{strategy_id}/deshabilitar-todas` | `require_evangelism_manage` |
| `GET` | `/personas/search` | `get_current_user` |

Reglas:

- `session_id` es UUID
- La sesión debe pertenecer a grupo activo/no eliminado
- La búsqueda remota de personas devuelve `{"results": [...]}` y requiere mínimo 3 caracteres
- `mine/pending` es flujo contextual por liderazgo o rol pastoral

## 8. Asistencia y follow-up de grupos

Archivo: `backend/api/evangelism_grupos/grupos_asistencias.py`

| Método | Ruta | Guard |
|---|---|---|
| `GET/POST` | `/grupos/sessions/{session_id}/attendance`, `/groups/sessions/{session_id}/attendance` | `get_current_user` + `_can_manage_grupo(...)` |
| `GET/POST` | `/sessions/{session_id}/attendance` | equivalente operativo según router propietario |
| `GET` | `/follow-up/pending` | `require_evangelism_read` |
| `GET/POST` | `/follow-up/{asistencia_id}` | lectura/escritura según operación |
| `PATCH` | `/follow-up/{seguimiento_id}` | `require_evangelism_edit` |

Reglas:

- La sesión debe existir y no estar eliminada
- Solo sesiones `HABILITADO` aceptan reportes de asistencia
- El plazo de reporte debe respetarse si existe `report_deadline`
- El flujo de asistencia es contextual al grupo, no global
- Los estados de asistencia deben normalizarse con `evangelism_shared.py`

## 9. Eventos

Archivos:

- `backend/api/evangelism_events/events_main.py`
- `backend/api/evangelism_events/events_participantes.py`
- `backend/api/evangelism_events/events_checkin.py`

### 9.1 CRUD y administración de eventos

| Método | Ruta | Guard |
|---|---|---|
| `GET` | `/events/` | `require_evangelism_read` |
| `POST` | `/events/` | `require_evangelism_manage` |
| `GET` | `/events/{event_id}` | guard contextual del archivo propietario |
| `PUT` | `/events/{event_id}` | `require_evangelism_manage` |
| `DELETE` | `/events/{event_id}` | `require_evangelism_manage` |
| `PUT` | `/events/{event_id}/audience` | `require_evangelism_manage` |
| `GET` | `/events/dashboard-stats` | `require_evangelism_manage` |
| `GET` | `/events/analytics/global` | `require_evangelism_manage` |

### 9.2 Analytics y export

| Método | Ruta | Guard |
|---|---|---|
| `GET` | `/events/{event_id}/analytics` | `require_evangelism_read` |
| `GET` | `/events/{event_id}/sessions/{session_date}/export` | `require_evangelism_read` |

### 9.3 Participación y asignaciones

| Método | Ruta | Guard |
|---|---|---|
| `GET` | `/events/{event_id}/attendance` | archivo propietario |
| `POST` | `/attendance` | archivo propietario |
| `POST` | `/attendance/bulk` | archivo propietario |
| `GET` | `/events/{event_id}/sessions/{session_date}` | archivo propietario |
| `POST` | `/events/{event_id}/assignments` | `require_evangelism_manage` |

### 9.4 Visitantes

| Método | Ruta | Guard |
|---|---|---|
| `POST` | `/events/{event_id}/sessions/{session_date}/visitors` | `require_active_user` + `require_event_access(...)` |

### 9.5 Roles de evento e historial

| Método | Ruta | Guard |
|---|---|---|
| `GET` | `/events/roles`, `/roles` | lectura administrativa del archivo propietario |
| `POST` | `/events/roles`, `/roles` | `require_evangelism_manage` |
| `PUT` | `/events/roles/{role_id}`, `/roles/{role_id}` | `require_evangelism_manage` |
| `DELETE` | `/events/roles/{role_id}`, `/roles/{role_id}` | `require_evangelism_manage` |
| `GET` | `/events/personas/{persona_id}/attendance-history`, `/personas/{persona_id}/attendance-history` | `require_evangelism_read` |

Reglas:

- `event_id` y `role_id` se resuelven como strings o UUID según el endpoint propietario
- `EventAudienceUpdate` exige roles cuando `target_audience == "ROLE"`
- `DELETE /events/{event_id}` es soft delete operativo: estado cancelado + `deleted_at`
- `attendance/bulk` debe responder `400` si recibe IDs inválidos, no ignorarlos silenciosamente
- El check-in rápido de visitantes evita duplicados de attendance para misma persona/fecha/evento

## 10. Multiplicación

Archivo: `backend/api/evangelism_multiplication.py`

| Método | Ruta | Guard |
|---|---|---|
| `GET` | `/multiplication/check` | `require_evangelism_manage` |
| `POST` | `/multiplication/split` | `require_evangelism_manage` |
| `GET` | `/multiplication/history` | `require_evangelism_manage` |

Contratos de shape relevantes:

- `check` devuelve lista de items con:
  - `grupo_id`
  - `grupo_nombre`
  - `lider_nombre`
  - `total_personas`
  - `excede_umbral`
  - `sugerencia`
- `split` devuelve:
  - `ok`
  - `mensaje`
  - `grupo_original`
  - `nuevo_grupo`
  - `personas_transferidas`
- `history` devuelve:
  - `grupo_id`
  - `grupo_nombre`
  - `parent_group_id`
  - `parent_group_nombre`
  - `notes_historial`
  - `created_at`
  - `personas_actuales`
  - `lider_nombre`

Reglas:

- `split` debe devolver `400` o `404` en precondiciones inválidas, no `500`
- Toda operación queda acotada a la sede del usuario

## 11. Notificaciones

Archivo: `backend/api/evangelism_notifications.py`

| Método | Ruta | Guard |
|---|---|---|
| `POST` | `/notifications/send-reminders` | `require_evangelism_manage` |

## 12. Rankings, reportes y analytics

### Rankings

Archivo: `backend/api/evangelism_rankings.py`

| Método | Ruta | Guard |
|---|---|---|
| `GET` | `/rankings/groups` | `require_evangelism_read` |
| `GET` | `/rankings/monthly-comparison` | `require_evangelism_read` |
| `GET` | `/rankings/leaders` | `require_evangelism_read` |

### Reportes

Archivo: `backend/api/evangelism_reports.py`

| Método | Ruta | Guard |
|---|---|---|
| `GET` | `/reports/group/{grupo_id}/attendance-pdf` | `require_evangelism_read` |
| `GET` | `/reports/group/{grupo_id}/attendance-excel` | `require_evangelism_read` |
| `GET` | `/reports/strategy/{strategy_id}/summary` | `require_evangelism_read` |

### Analytics

Archivo: `backend/api/evangelism_analytics.py`

| Método | Ruta | Guard |
|---|---|---|
| `GET` | `/analytics/strategy/{id}` | `require_evangelism_read` |
| `GET` | `/analytics/strategy/{id}/trend` | `require_evangelism_read` |
| `GET` | `/analytics/strategy/{id}/funnel` | `require_evangelism_read` |
| `GET` | `/analytics/strategy/{id}/heatmap` | `require_evangelism_read` |
| `GET` | `/analytics/strategy/{id}/alerts` | `require_evangelism_read` |
| `GET` | `/analytics/strategy/{id}/velocity` | `require_evangelism_read` |
| `GET` | `/analytics/strategy/{id}/groups` | `require_evangelism_read` |
| `GET` | `/analytics/strategy/{id}/full` | `require_evangelism_read` |

Reglas:

- Estas superficies ya no deben documentarse como `require_active_user`
- Deben respetar sede y soft delete

## 13. Scanner

Archivo: `backend/api/evangelism.py`

| Método | Ruta | Guard |
|---|---|---|
| `POST` | `/scanner/generate/{persona_id}` | `require_module_access("evangelism", "manage")` |
| `POST` | `/scanner/validate/{token}` | `require_module_access("evangelism", "read")` |

Reglas:

- Formato esperado: `CCF-PER-{persona_id}-{secret}`
- El secreto persistido se guarda como hash
- Token vencido o inválido responde `403`
- Persona inexistente responde `404`

## 14. Códigos esperados

| Código | Uso |
|---|---|
| `200/201/204` | operación exitosa |
| `400` | input inválido o precondición de negocio |
| `401` | token/sesión inválida |
| `403` | sin permiso, fuera de contexto o sesión no habilitada |
| `404` | recurso inexistente o fuera de alcance |
| `409` | conflicto explícito si el endpoint lo define |

## 15. Validación recomendada

Backend mínimo:

```bash
cd /root/ccf
./venv/bin/python scripts/test_evangelism_quality.py
```

Backend ampliado:

```bash
cd /root/ccf
./venv/bin/python scripts/test_evangelism_quality.py --backend-deep
```

Frontend:

```bash
cd /root/ccf
./venv/bin/python scripts/test_evangelism_quality.py --frontend-smoke
./venv/bin/python scripts/test_evangelism_quality.py --frontend-deep
```
