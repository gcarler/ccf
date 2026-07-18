# Auditoría Forense — Módulo de Evangelismo CCF

Fecha: 2026-07-17

> **Objetivo:** evaluar completitud, consistencia y confiabilidad operativa del módulo de evangelismo en backend, frontend, permisos, tests y documentación.
>
> **Regla de lectura:** este documento registra hallazgos abiertos. No reemplaza `ESTADO_EVANGELISMO.md` como handover canónico.

## Alcance auditado

- Router raíz: `backend/api/evangelism.py`
- Submódulos:
  - `backend/api/evangelism_main/*`
  - `backend/api/evangelism_grupos/*`
  - `backend/api/evangelism_events/*`
  - `backend/api/evangelism_multiplication.py`
  - `backend/api/evangelism_notifications.py`
  - `backend/api/evangelism_rankings.py`
  - `backend/api/evangelism_reports.py`
  - `backend/api/evangelism_analytics.py`
- Permisos: `backend/core/permissions.py`
- Frontend:
  - `frontend/src/app/plataforma/evangelism/**`
  - `frontend/src/components/evangelism/**`
- QA:
  - `scripts/test_evangelism_quality.py`
  - `tests/test_evangelism_*`
  - `frontend/tests/e2e/evangelism/*`
- Documentación:
  - `docs/ESTADO_EVANGELISMO.md`
  - `docs/EVANGELISMO_API_CONTRACTS.md`
  - `docs/EVANGELISMO_RBAC_MATRIX.md`
  - `docs/PLAN_EVANGELISMO_CALIDAD.md`
  - `docs/PLAN_DE_TRABAJO_EVANGELISMO.md`
  - `docs/EVANGELISMO_QA_CHECKLIST.md`

## Validaciones ejecutadas

### Backend

```bash
cd /root/ccf
./venv/bin/python scripts/test_evangelism_quality.py --backend-deep
```

Resultado:

- smoke mínimo: `18 passed, 1 xfailed`
- regresiones críticas: `19 passed, 1 xfailed`
- cobertura amplia backend: `219 passed`

### Frontend

```bash
cd /root/ccf
./venv/bin/python scripts/test_evangelism_quality.py --frontend-deep
```

Resultado:

- falló
- error observado: `Process from config.webServer exited early`

Prueba de aislamiento:

```bash
cd /root/ccf/frontend
npm run dev -- -p 4173
```

Resultado:

- `Error: listen EPERM: operation not permitted 0.0.0.0:4173`

## Hallazgos

### F1. El frontend sigue modelando evangelismo como módulo “pastoral o administrativo”, contradiciendo la migración backend a `evangelism:*`

Severidad: **Crítico**

Archivos:

- `frontend/src/components/evangelism/EvangelismShell.tsx`
- `frontend/src/app/plataforma/evangelism/EvangelismClient.tsx`
- `frontend/src/app/plataforma/evangelism/strategies/[id]/page.tsx`
- `frontend/src/app/plataforma/evangelism/groups/page.tsx`
- `frontend/src/app/plataforma/evangelism/groups/[id]/page.tsx`

Evidencia:

- `EvangelismShell` calcula `isPastoralOrAdmin = ['admin', 'administrador', 'pastor'].includes(role)`
- `EvangelismClient` bloquea estrategias con `canManageStrategies = ['admin', 'administrador', 'pastor']...`
- `strategies/[id]/page.tsx` usa `canManageStrategySurface = ['admin', 'administrador', 'pastor']...`
- El copy visible todavía dice: “Este módulo requiere rol pastoral o administrativo.”

Impacto:

- usuarios con `evangelism:read`
- usuarios con `evangelism:edit`
- `coordinador`
- roles granulares sembrados en Auth v3

pueden quedar:

- excluidos de vistas válidas
- sin navegación a estrategias
- con estados de acceso restringido falsos
- desalineados respecto al backend real

Conclusión:

- la migración RBAC backend no está consumida orgánicamente por el frontend
- el módulo sigue acoplado a una taxonomía legacy de rol, aunque el backend ya no lo esté

### F2. `GET /api/evangelism/events/` rompe la taxonomía canónica de permisos por un chequeo manual de rol

Severidad: **Alta**

Archivo:

- `backend/api/evangelism_events/events_main.py`

Evidencia:

- la ruta depende de `require_evangelism_read`
- inmediatamente después vuelve a filtrar con:
  - `if _get_user_role(current_user) not in {"admin", "administrador", "pastor"}:`
  - `raise HTTPException(... "Se requiere: evangelism:manage")`

Impacto:

- `coordinador` con allowance de `evangelism:read` queda bloqueado
- un rol granular con `evangelism:read` queda bloqueado
- el mensaje de error pide `manage` aunque la dependencia principal es `read`

Conclusión:

- la ruta publica una semántica RBAC y ejecuta otra
- hoy el contrato de lectura de eventos no es confiable

### F3. La superficie de eventos sigue mezclando `evangelism:*` con rutas operativas abiertas a cualquier usuario activo asignado

Severidad: **Alta**

Archivos:

- `backend/api/evangelism_events/events_main.py`
- `backend/api/evangelism_events/events_participantes.py`
- `backend/api/evangelism_events/events_checkin.py`
- `backend/api/evangelism_events/_shared.py`

Evidencia:

- detalle de evento: `require_active_user` + `require_event_access(...)`
- attendance report: `require_active_user` + `require_event_access(...)`
- `POST /attendance`: `require_active_user`
- `POST /attendance/bulk`: `require_active_user`
- check-in rápido visitante: `require_active_user`
- `require_event_access` habilita admin/pastor o asignados al evento

Impacto:

- la superficie de eventos no es homogénea
- un usuario sin permisos explícitos de evangelismo puede operar sobre eventos si está asignado
- esto puede ser correcto de negocio, pero hoy no está expresado como contrato primario del módulo

Conclusión:

- aquí no hay necesariamente bug funcional
- sí hay inconsistencia estructural entre la taxonomía canónica del módulo y el modelo operativo real de eventos
- este punto exige decisión de producto/arquitectura, no solo refactor

### F4. El gate canónico de frontend profundo del módulo no es confiable hoy

Severidad: **Alta**

Archivos:

- `scripts/test_evangelism_quality.py`
- `frontend/scripts/run-managed-playwright.mjs`
- `frontend/playwright.config.ts`

Evidencia:

- `./venv/bin/python scripts/test_evangelism_quality.py --frontend-deep` falló
- Playwright reportó `Process from config.webServer exited early`
- el arranque aislado `npm run dev -- -p 4173` falló con `EPERM` al bindear `0.0.0.0:4173`

Impacto:

- el gate canónico del módulo no es reproducible en el entorno actual
- la narrativa “QA profundo oficial en verde” no se puede sostener automáticamente en esta sesión
- una auditoría posterior podría leer “cobertura profunda disponible” cuando la ejecución real está rota

Conclusión:

- esto puede ser un problema del entorno o de cómo Playwright arranca `next dev`
- de cualquier forma, hoy es un hallazgo operativo del módulo, porque invalida el camino oficial de validación frontend

### F5. La cobertura backend es amplia, pero la confianza RBAC está sobredimensionada porque casi todo se prueba desde `admin`

Severidad: **Media-Alta**

Archivos:

- `tests/test_evangelism_module_coverage.py`
- `tests/test_evangelism_triple7_flow.py`
- `tests/test_evangelism_coverage.py`

Evidencia:

- el fixture principal `full(...)` siembra `admin + sede + estrategia + grupos + sesiones`
- la mayoría del módulo se valida con headers de admin
- no hay una matriz equivalente de pruebas sistemáticas para:
  - `coordinador`
  - `lector`
  - `editor`
  - rol granular con `evangelism:read/edit/manage`

Impacto:

- la migración RBAC puede romperse sin que la suite principal lo detecte
- la cobertura de 219 tests mide alcance funcional más que coherencia de permisos

Conclusión:

- la calidad backend es buena en contratos
- la calidad RBAC todavía no es proporcional a la complejidad del cambio de permisos

### F6. Una suite de coverage de analytics acepta `500` como resultado permitido

Severidad: **Media**

Archivo:

- `tests/test_evangelism_analytics_coverage.py`

Evidencia:

- helper `_ok(status)` retorna verdadero para:
  - `200, 201, 400, 403, 404, 405, 422, 500`

Impacto:

- se puede enmascarar una regresión real de analytics
- la suite da señal de “cobertura” pero tolera fallo interno del servidor

Conclusión:

- este archivo sirve para ejecutar líneas, no para garantizar comportamiento estable
- no debe usarse como evidencia fuerte de robustez

### F7. La deuda estructural del frontend sigue siendo alta y localizada en pocas pantallas de gran superficie

Severidad: **Media**

Archivos críticos:

- `frontend/src/app/plataforma/evangelism/strategies/[id]/page.tsx` — `2678` líneas
- `frontend/src/app/plataforma/evangelism/events/page.tsx` — `1722` líneas
- `frontend/src/app/plataforma/evangelism/groups/[id]/page.tsx` — `1002` líneas
- `frontend/src/app/plataforma/evangelism/strategies/[id]/useStrategyDetail.ts` — `454` líneas

Evidencia adicional:

- uso extendido de `any`
- fetches y efectos distribuidos en varias pantallas
- abort/cancelación inconsistente fuera de algunos flujos ya corregidos

Impacto:

- eleva riesgo de regresión
- dificulta hacer cumplir permisos por capacidad real
- hace más costosa cualquier expansión de tests o tipado

Conclusión:

- la descomposición iniciada no alcanza todavía el punto de seguridad estructural

### F8. La documentación canónica todavía sobredeclara el estado de la migración RBAC

Severidad: **Media**

Archivo:

- `docs/ESTADO_EVANGELISMO.md`

Evidencia:

- afirma: “todo el módulo usa la taxonomía canónica `evangelism:*`”
- afirma: “cero referencias a `require_pastor_or_admin` en módulo evangelismo”

Realidad observada:

- sí desapareció `require_pastor_or_admin`
- pero persisten:
  - `require_active_user`
  - `get_current_user`
  - access checks contextuales
  - gating frontend por rol legacy

Impacto:

- una sesión nueva puede creer que la migración RBAC está completa de punta a punta
- el próximo cambio puede tocar frontend o eventos con supuestos falsos

Conclusión:

- backend principal migrado: sí
- módulo orgánico completo, no

## Diagnóstico final

### Lo que está sólido

- contratos backend principales
- sede isolation en superficies auditadas
- soft delete en grupos, sesiones y eventos
- smoke backend mínimo
- regresiones críticas backend
- cobertura amplia backend

### Lo que no está cerrado

- traducción orgánica de la migración RBAC al frontend
- modelo de permisos definitivo para eventos
- confiabilidad del gate frontend profundo
- cobertura de permisos por rol no-admin
- limpieza estructural de pantallas grandes
- consistencia documental del estado real del módulo

## Recomendación de trabajo

La siguiente sesión no debe empezar corrigiendo detalles aislados.

Debe abordarse en este orden:

1. definir el modelo real de acceso del módulo después de la migración
2. alinear frontend con esa decisión
3. blindar eventos
4. reparar el gate profundo frontend
5. agregar cobertura RBAC no-admin
6. continuar la descomposición estructural

La ejecución concreta vive en [PLAN_DE_TRABAJO_EVANGELISMO.md](/root/ccf/docs/PLAN_DE_TRABAJO_EVANGELISMO.md).
