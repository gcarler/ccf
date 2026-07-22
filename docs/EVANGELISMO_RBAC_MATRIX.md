# Matriz RBAC — Evangelismo CCF

> **Objetivo:** documentar el control de acceso real del módulo de evangelismo según el código vigente.
>
> **Fecha de verificación:** 2026-07-21
> **Fuente de verdad:** código backend en `backend/api/evangelism*` y `backend/core/permissions.py`

## 1. Resumen ejecutivo

El módulo de evangelismo ya no debe leerse como una superficie dominada por `require_pastor_or_admin`.

El estado actual del backend es híbrido, pero con una taxonomía canónica ya implantada:

- Guards canónicos del módulo:
  - `require_evangelism_read`
  - `require_evangelism_edit`
  - `require_evangelism_manage`
- Superficies contextuales que siguen usando `get_current_user`:
  - rutas personales tipo `mine`
  - asistencia de grupos por ownership/liderazgo
- Check-in rápido de visitantes en eventos:
  - `require_evangelism_edit` + alcance del evento y sede
- Scanner:
  - sigue montado con `require_module_access("evangelism", "...")`, equivalente funcional de los guards canónicos

## 2. Taxonomía canónica

Definida en `backend/core/permissions.py`:

| Acción | Permission key |
|---|---|
| Lectura | `evangelism:read` |
| Operación | `evangelism:edit` |
| Gestión | `evangelism:manage` |

Aliases usados por el módulo:

| Alias | Resolución |
|---|---|
| `require_evangelism_read` | `require_module_access("evangelism", "read")` |
| `require_evangelism_edit` | `require_module_access("evangelism", "edit")` |
| `require_evangelism_manage` | `require_module_access("evangelism", "manage")` |

## 3. Allowances por rol

Además de permisos granulares explícitos, `require_permission()` aplica bypass por rol:

| Rol normalizado | Lectura |
|---|---|
| `admin` / `administrador` | acceso total |
| `pastor` | acceso total a `evangelism:*` |
| `coordinador` | acceso automático a `evangelism:read` y `evangelism:edit`, no a `evangelism:manage` salvo permiso granular |

Consecuencia operativa:

- `coordinador` puede entrar a flujos operativos de lectura y edición si la ruta usa guards canónicos.
- `coordinador` no debe asumir acceso a creación/eliminación/configuración si la ruta exige `evangelism:manage`.
- `pastor` conserva bypass completo del módulo.

## 4. Modos reales de protección

Evangelismo usa hoy tres modos principales y un modo puntual:

1. Guards canónicos `require_evangelism_*`
2. `get_current_user` + validación contextual
3. `require_active_user`
4. `require_module_access("evangelism", "...")` en scanner

El guard histórico `require_pastor_or_admin` ya no debe considerarse fuente normal del módulo evangelismo.

## 5. Matriz por superficie

### 5.1 Router raíz y scanner

| Superficie | Guard real |
|---|---|
| `POST /scanner/generate/{persona_id}` | `require_module_access("evangelism", "manage")` |
| `POST /scanner/validate/{token}` | `require_module_access("evangelism", "read")` |

Lectura:

- Scanner ya está alineado con la taxonomía canónica.
- Documentalmente puede tratarse como equivalente a `require_evangelism_manage/read`.

### 5.2 Estrategias

Archivo: `backend/api/evangelism_main/main_estrategias.py`

| Superficie | Guard real |
|---|---|
| listados y detalle | `require_evangelism_read` |
| creación, actualización, borrado, generación de sesiones | `require_evangelism_manage` |

Lectura:

- Estrategias ya está migrado a la taxonomía canónica.
- No debe documentarse como `require_pastor_or_admin`.

### 5.3 Roles de estrategia y catálogo de excusas

Archivo: `backend/api/evangelism_main/main_roles.py`

| Superficie | Guard real |
|---|---|
| roles personalizados | `require_evangelism_manage` |
| excusas | `require_evangelism_manage` |

### 5.4 Grupos

Archivo: `backend/api/evangelism_grupos/grupos_main.py`

| Superficie | Guard real |
|---|---|
| `/grupos`, `/groups`, resúmenes y analytics | `require_evangelism_read` o `require_evangelism_manage` según operación |
| detalle de grupo y asistencia | `get_current_user` + ownership/liderazgo contextual |
| creación, edición y delete | `require_evangelism_manage` |
| `/grupos/mine`, `/groups/mine` | `get_current_user` + ownership/liderazgo |

Lectura:

- La superficie administrativa de grupos ya está migrada a `evangelism:*`.
- Las rutas `mine` siguen siendo contextuales por diseño.

### 5.5 Sesiones

Archivo: `backend/api/evangelism_grupos/grupos_sesiones.py`

| Superficie | Guard real |
|---|---|
| listados y detalle operativo | `require_evangelism_read` |
| creación y mutaciones administrativas | `require_evangelism_manage` |
| `/grupos/sessions/mine/pending` | `get_current_user` + ownership/liderazgo |
| `/personas/search` | `get_current_user` |

Lectura:

- Las sesiones administrativas ya están sobre guards canónicos.
- `mine/pending` y la búsqueda remota de personas conservan una entrada contextual/autenticada.

### 5.6 Asistencia y follow-up de grupos

Archivo: `backend/api/evangelism_grupos/grupos_asistencias.py`

| Superficie | Guard real |
|---|---|
| lectura/escritura de asistencia por sesión de grupo | `get_current_user` + `_can_manage_grupo(...)` |
| follow-up visible | `require_evangelism_read` |
| mutaciones de follow-up | `require_evangelism_edit` |

Lectura:

- La asistencia de grupos no es un flujo “global” de RBAC puro; depende del grupo concreto.
- Esto es intencional y debe seguir documentado como acceso contextual.

### 5.7 Eventos

Archivos:

- `backend/api/evangelism_events/events_main.py`
- `backend/api/evangelism_events/events_participantes.py`
- `backend/api/evangelism_events/events_checkin.py`

| Superficie | Guard real |
|---|---|
| listar/ver analytics/export básico | `require_evangelism_read` |
| CRUD, dashboards administrativos, audiencia, roles, assignments | `require_evangelism_manage` |
| operaciones operativas de participación | `require_evangelism_edit` o `require_evangelism_manage` según endpoint |
| check-in rápido de visitantes | `require_evangelism_edit` + `require_event_access(...)` |

Lectura:

- Eventos ya no debe describirse como superficie basada en `require_pastor_or_admin`.
- El check-in de visitante exige `evangelism:edit` y alcance de sede del evento.

### 5.8 Multiplicación

Archivo: `backend/api/evangelism_multiplication.py`

| Superficie | Guard real |
|---|---|
| check | `require_evangelism_manage` |
| split | `require_evangelism_manage` |
| history | `require_evangelism_manage` |

### 5.9 Notificaciones

Archivo: `backend/api/evangelism_notifications.py`

| Superficie | Guard real |
|---|---|
| `POST /notifications/send-reminders` | `require_evangelism_manage` |

### 5.10 Rankings, reportes y analytics

Archivos:

- `backend/api/evangelism_rankings.py`
- `backend/api/evangelism_reports.py`
- `backend/api/evangelism_analytics.py`

| Superficie | Guard real |
|---|---|
| rankings | `require_evangelism_read` |
| reportes | `require_evangelism_read` |
| analytics | `require_evangelism_read` |

Además del guard, Analytics, Scanner, Estrategias y creación de Grupos resuelven
el recurso dentro de la sede autenticada. El permiso nunca sustituye el alcance
de tenant.

## 6. Lectura por rol operativo

| Rol | Lectura segura |
|---|---|
| `ADMINISTRADOR` | acceso completo |
| `GESTOR` con `evangelism:manage` | acceso completo en superficies canónicas del módulo |
| `EDITOR` con `evangelism:edit` | lectura y operación, no gestión |
| `LECTOR` con `evangelism:read` | solo lectura en superficies canónicas |
| `COORDINADOR` | lectura y edición por allowance, más acceso contextual de grupos propios |
| `PASTOR` | acceso total por allowance |
| `MIEMBRO` | solo donde exista flujo autenticado/contextual y el código lo permita |

## 7. Riesgos de drift que esta matriz evita

1. No volver a documentar evangelismo como si `require_pastor_or_admin` siguiera gobernando el módulo.
2. No tratar un `403` de una ruta contextual como bug sin revisar ownership o sede.
3. No asumir que todo `evangelism:*` equivale a acceso completo para `coordinador`.
4. No mezclar flujos administrativos con flujos operativos contextuales en QA.

## 8. Reglas de QA derivadas

- Validar por separado:
  - rutas `read`
  - rutas `edit`
  - rutas `manage`
  - rutas contextuales (`mine`, asistencia por grupo)
  - scanner
  - check-in visitante de eventos
- Si cambia el guard real de una superficie, actualizar:
  - `docs/ESTADO_EVANGELISMO.md`
  - `docs/EVANGELISMO_API_CONTRACTS.md`
  - `docs/EVANGELISMO_QA_CHECKLIST.md`
  - esta matriz

## 9. Estado documental

- `PEND-RBAC-EVANGELISM-001`: cerrada
- Esta versión reemplaza la lectura histórica previa del `2026-07-16`
- A partir del `2026-07-17`, la fuente documental correcta para permisos del módulo debe partir de `evangelism:*` y luego detallar excepciones contextuales
- **2026-07-21 (cierre Fase 1 — wrapper legacy)**: el paquete `backend/api/_evangelism_helpers/` se eliminó por completo. Era código muerto sin importadores externos desde la migración del `2026-07-17`. Su wrapper `require_pastor_or_admin_with_sede` era la única conexión residual de evangelism al guard `require_pastor_or_admin` historico (que delega en `crm:manage`). Funciones equivalentes viven en `backend/crud/evangelism.py:_actor_sede_or_none_evangelismo` (con validación UUID robusta + persona + sede). Tras el cierre: `grep require_pastor_or_admin backend/api/evangelism* backend/api/evangelism_*= 0 hits`. Commit `339539e9`.

## 10. Verificación post-cierre (2026-07-21)

Comando de verificación RBAC radical:

```bash
cd /root/ccf
# Debe retornar 0 hits en módulo evangelism:
rg -n 'require_pastor_or_admin' backend/api/evangelism.py backend/api/evangelism_*.py backend/api/evangelism_*/ 2>/dev/null
# Debe retornar solo módulos CRM legítimos (analytics.py, crm/pipelines.py) y la definición en permissions.py:
rg -n 'require_pastor_or_admin' backend/ 2>/dev/null
# Smoke + suite amplia:
./venv/bin/python scripts/test_evangelism_quality.py
./venv/bin/python -m pytest -q -o addopts='' tests/test_evangelism_module_coverage.py
```

Resultado de esta verificación ejecutada el `2026-07-21`:

- `rg require_pastor_or_admin backend/api/evangelism*` → **0 hits** ✅
- `rg require_pastor_or_admin backend/` → **solo** `backend/core/permissions.py` (definición), `backend/api/analytics.py` (CRM) y `backend/api/crm/pipelines.py` (CRM) → ✅ ese guard es legítimo en CRM, lo que documenta el docstring L693-698 de `permissions.py`
- Smoke canónico → 2/2 suites verdes (19 passed + 1 xfailed) ✅
- Suite amplia → 226/226 passed en 155s ✅ (antes 219; +7 tests de `test_evangelism_custom_role_regression.py` cubriendo el bug RBAC original)
