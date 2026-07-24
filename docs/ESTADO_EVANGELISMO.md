# Estado del Modulo de Evangelismo — CCF

> **TL;DR (una linea):** Evangelismo es una plataforma interna completa sobre `/api/evangelism` y `/plataforma/evangelism`: estrategias, grupos, sesiones, asistencia, eventos, rankings, multiplicacion, scanner y puente CRM. Tratarlo como modulo aislado antes de tocar CRM, proyectos o calendario.

**Proposito.** Handover canonico para que cualquier sesion nueva pueda trabajar evangelismo sin redescubrir el modulo ni mezclar arreglos con otros dominios. Este archivo debe leerse antes de editar rutas, permisos, asistencia, eventos, grupos o pantallas de evangelismo.

**Regla de uso.**

- Actualizar este doc al cerrar tareas, no antes.
- Las categorias `Hecho / Parcial / Pendiente` reflejan el codigo vigente.
- No usar este doc como wishlist. Si una capacidad no existe en codigo, se marca `Pendiente`.
- Evangelismo se valida como unidad propia. No corregir fallos de evangelismo desde CRM, proyectos o calendario salvo que el contrato cruzado lo exija.

---

## 1. Leer primero (cualquier agente)

```bash
cat /root/ccf/docs/ESTADO_EVANGELISMO.md
cat /root/ccf/docs/PLAN_EVANGELISMO_CALIDAD.md
cat /root/ccf/docs/EVANGELISMO_API_CONTRACTS.md
cat /root/ccf/docs/EVANGELISMO_RBAC_MATRIX.md
cat /root/ccf/docs/EVANGELISMO_QA_CHECKLIST.md
cat /root/ccf/docs/AUDITORIA_FLUJO_EVANGELISMO_CCF.md
```

## 2. Verificar entorno

```bash
python3 --version && node --version
```

Versiones verificadas en este host el **2026-07-16**:

- Python: **3.12.3**
- Node: **v24.15.0**

## 3. Recontar superficie vigente (por si drift)

```bash
wc -l /root/ccf/backend/api/evangelism*.py /root/ccf/backend/api/evangelism_*/*.py /root/ccf/backend/models_evangelism.py /root/ccf/backend/schemas/evangelism.py /root/ccf/backend/crud/evangelism.py /root/ccf/backend/services/evangelism_*.py 2>/dev/null | tail -1
wc -l /root/ccf/frontend/src/components/evangelism/*.tsx /root/ccf/frontend/src/app/plataforma/evangelism/**/*.tsx /root/ccf/frontend/src/app/plataforma/evangelism/*.tsx 2>/dev/null | tail -1
```

Conteo actual:

- Backend evangelismo directo: **10 823 LOC**
- Frontend evangelismo directo: **4 215 LOC**

## 4. Listar backlog completo (Parcial + Pendiente) por ID

```bash
grep -nE '^\d+\. \*\*.*\[(PARCIAL|PEND)-|^\| `(PARCIAL|PEND)-' /root/ccf/docs/ESTADO_EVANGELISMO.md
```

## 5. Smoke test

Smoke canónico:

```bash
cd /root/ccf
./venv/bin/python scripts/test_evangelism_quality.py
```

Smoke mínimo bruto:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_evangelism_triple7_flow.py \
  tests/test_evangelism_crm_bridge.py \
  tests/test_evangelism_reports_api.py \
  tests/test_calculo_sesiones.py
```

Smoke ampliado, si se toca API de eventos, roles, grupos o multiplicacion:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' tests/test_evangelism_module_coverage.py
```

Smoke frontend, si se toca UI:

```bash
cd /root/ccf/frontend
npm run test:e2e:evangelism
npm run test:e2e:evangelism:deep
```

---

## 6. TL;DR — Mapa del modulo

| Capa | Ubicacion | Tamano |
|---|---|---:|
| Modelos | `backend/models_evangelism.py` | 11 tablas/clases principales |
| API router canonico | `backend/api/evangelism.py` | Montado en `/api/evangelism` |
| API split | `backend/api/evangelism_main/`, `evangelism_grupos/`, `evangelism_events/` | Estrategias, roles, grupos, sesiones, asistencia, eventos |
| API analitica | `backend/api/evangelism_analytics.py`, `evangelism_reports.py`, `evangelism_rankings.py`, `evangelism_multiplication.py`, `evangelism_notifications.py` | Reportes, rankings, multiplicacion, recordatorios |
| Schemas | `backend/schemas/evangelism.py` | Contratos Pydantic del modulo |
| CRUD | `backend/crud/evangelism.py` | Acceso directo compartido |
| Servicios | `backend/services/evangelism_crm_bridge.py`, `evangelism_projection.py`, `calculo_sesiones.py` | CRM bridge, proyeccion temporal, generacion de sesiones |
| UI shell | `frontend/src/components/evangelism/EvangelismShell.tsx` | Shell compartido |
| UI principal | `frontend/src/app/plataforma/evangelism/**` | Dashboard, estrategias, grupos, eventos, rankings, scanner, multiplicacion |
| Tests backend | `tests/test_evangelism_*.py`, `tests/test_calculo_sesiones.py` | Regresion y cobertura |
| Tests e2e | `frontend/tests/e2e/evangelism/` | Sesiones, rankings, multiplicacion |

**Estado global:** **Certificado internamente — 100% del plan maestro.** La certificación cubre seguridad por sede/RBAC, contratos por vertical, UI tipada, flujos de negocio y gates reproducibles. El despliegue productivo continúa por su pipeline normal y reversible; no es parte de esta certificación de código.
**Actualización de certificación 2026-07-18:** las fases 0 a 6 del plan maestro quedaron ejecutadas. Evidencia final: backend profundo/expandido, matriz de permisos de dos sedes, typecheck, Playwright administrado en `passed`, `git diff --check` y commit atómico de Evangelismo.
**Actualizacion QA 2026-07-16:** la cobertura profunda frontend ya no depende de arrancar Next manualmente. `npm run test:e2e:evangelism` y `npm run test:e2e:evangelism:deep` usan `frontend/scripts/run-managed-playwright.mjs` para levantar `webServer` administrado y ejecutar las suites profundas de sesiones, rankings y multiplication de forma repetible.
**Actualizacion QA 2026-07-16 (events/scanner):** la cobertura profunda frontend ahora tambien cubre `/plataforma/evangelism/events`, `/plataforma/evangelism/events/[id]` y `/plataforma/evangelism/scanner` con `frontend/tests/e2e/evangelism/events-scanner.spec.ts`. La validacion ejecutada fue `npm run test:e2e:evangelism:deep` (`13 passed`) y `npm run test:e2e:evangelism` (`13 passed, 3 skipped`).
**Actualizacion QA 2026-07-16 (script canonico):** `scripts/test_evangelism_quality.py` ya expone `--frontend-smoke`, `--frontend-deep` y `--expanded` como gates oficiales del modulo. La validacion ejecutada fue `./venv/bin/python scripts/test_evangelism_quality.py --frontend-deep` (`3 passed, 0 failed` a nivel de suites; incluye `13 passed` en Playwright deep).

**Actualizacion QA 2026-07-17 (RBAC radical):** Se migro todo el modulo de `require_pastor_or_admin` (guard historico que delegaba en `crm:manage`) a la taxonomia canonica `evangelism:read/edit/manage`. 14 archivos backend modificados. `backend/core/permissions.py` ahora incluye los guards `require_evangelism_read`, `require_evangelism_edit`, `require_evangelism_manage` mas el bypass por rol para `pastor` (acceso total) y `coordinador` (read/edit). Smoke minimo (37 passed) y suite amplia (219 passed) verificados post-migracion. Cero referencias a `require_pastor_or_admin` en modulo evangelismo.

**Actualizacion QA 2026-07-21 (cierre Fase 1 RBAC — wrapper legacy):** Se completo el ultimo eslabon legacy de la migracion RBAC radical al eliminar el paquete `backend/api/_evangelism_helpers/` (codigo muerto desde la migracion del 2026-07-17). El wrapper `require_pastor_or_admin_with_sede` era la unica referencia evangelism al guard `crm:manage`-coincidence; ningun router lo importaba, funciones equivalentes viven en `backend/crud/evangelism.py:_actor_sede_or_none_evangelismo`. Modulo evangelism ahora verificadamente 100% libre de `require_pastor_or_admin` (grep 0 hits). Comentario referenciante en `backend/crud/evangelism.py` actualizado. Bug secundario corregido: 5 tests usaban campo obsoleto `nombre` en PUT/POST `/grupos` cuando el schema `GrupoEvangelismoCreate/Update` con `extra="forbid"` exige `name`. Validacion fresca: smoke 2/2 (19 passed + 1 xfailed) y suite amplia 226/226 verdes. Commit `339539e9`.

**Actualizacion QA 2026-07-17 (enum canonico de estados):** `evangelism_shared.py` migrado a usar `StatusAsistenciaCanonico` como fuente de verdad unica. Los sets `ATTENDED_STATES`, `ABSENT_STATES`, `EXCUSED_STATES`, `FIRST_TIME_STATES` ahora se derivan del enum. Las funciones `_attended()` y `_is_primera_vez()` en `evangelism_analytics.py` migradas a `normalize_attendance_status`. Validado con suite amplia (219 passed).

**Actualizacion QA 2026-07-17 (descomposicion frontend):** Se extrajeron 7 hooks funcionales de `strategies/[id]/page.tsx` a `useStrategyDetail.ts`: `useStrategy`, `useCustomRoles`, `useGroups`, `useSessions`, `useMetrics`, `useFollowUps`, `useRemotePersonaSearch`, `useSessionActions`, `useGroupActions`, `useAttendanceDrawer`. La page mantiene su estructura visual intacta; los hooks encapsulan fetching y estado.

**Actualizacion QA 2026-07-18 (cierre estrategia + eventos):** `strategies/[id]/page.tsx` consume los hooks canonicos del modulo para estrategia, roles, grupos, sesiones, metricas, seguimiento, busqueda remota y acciones de sesiones; se elimino la doble fuente de verdad respecto a `useStrategyDetail.ts` y se realineo el tipado al contrato canonico de `../../types`. En paralelo se cerro la inconsistencia de soft-delete de eventos CRM: `backend/models_crm.py` recupero `deleted_at`, `backend/api/evangelism_events/events_main.py` y `backend/crud/crm_/events.py` consultan solo eventos activos, y la migracion `20260718_0001_crm_events_deleted_at.py` persiste el contrato.

**Actualizacion QA 2026-07-18 (analytics):** `tests/test_evangelism_analytics_coverage.py` ya no acepta `500` como resultado valido; una regresion interna de analytics ahora falla la suite. Validado con `34 passed`.

**Actualizacion QA 2026-07-17 (busqueda remota de personas):** `PEND-PERSONAS-SEARCH-001` cerrada. El endpoint `GET /personas/search` existe con debounce, filtro sede (3 chars minimo) y AbortController en frontend. Consumido desde asistencia y grupo. No requiere cambios adicionales.

**Actualizacion documental 2026-07-16:** `PEND-RBAC-EVANGELISM-001` queda cerrada con `docs/EVANGELISMO_RBAC_MATRIX.md`. La matriz confirma que el modulo no esta homogeneamente migrado a `evangelism:*`.
**Actualizacion operativa 2026-07-16:** `tests/test_evangelism_module_coverage.py` paso en verde (`219 passed`), por lo que `PARCIAL-EVENTS-001`, `PARCIAL-MULTIPLICATION-001`, `PARCIAL-FOLLOWUP-001`, `PEND-EVENTS-CONTRACT-001` y `PEND-SESSIONS-CONTRACT-001` dejan de ser backlog activo y pasan a historial de cierre validado.
**Actualizacion UI 2026-07-16:** se alineo la superficie de estrategias con el guard real del backend. `EvangelismShell`, el dashboard de estrategias y `strategies/[id]/page.tsx` ya no disparan fetches de estrategias/grupos/sesiones para usuarios fuera de `admin/administrador/pastor`; muestran estado de acceso restringido en lugar de provocar `401/403` estructurales.

---

## 7. Convenciones del modulo

- **Ruta plataforma:** `/plataforma/evangelism`.
- **Ruta API:** `/api/evangelism`.
- **Cliente frontend:** usar `apiFetch('/evangelism/...', { token })`; no construir URLs absolutas ni saltar a `/api` manualmente en pantallas plataforma.
- **Auth y permisos:** Desde la migracion RBAC del 2026-07-17, todo el modulo usa la taxonomia canonica `evangelism:*` via los guards `require_evangelism_read`, `require_evangelism_edit` y `require_evangelism_manage` definidos en `backend/core/permissions.py`. El guard historico `require_pastor_or_admin` fue eliminado del modulo. `pastor` tiene bypass total (`evangelism:*`); `coordinador` tiene `evangelism:read` y `evangelism:edit`. Ver `docs/EVANGELISMO_RBAC_MATRIX.md`.
- **Identidad de personas:** todo participante o visitante debe apuntar a `personas.id` UUID.
- **Sede isolation:** estrategias y grupos tienen `sede_id`; sesiones y asistencias heredan scope por grupo.
- **Soft delete:** no asumir hard delete en grupos, sesiones o registros operativos. Revisar `deleted_at` en lecturas.
- **Estados de asistencia:** normalizar con `backend/api/evangelism_shared.py`; evitar variantes nuevas desde frontend.
- **Sesiones:** pueden nacer `DESHABILITADO`; la asistencia solo debe registrarse cuando la sesion esta habilitada.
- **CRM bridge:** la creacion de casos de visitante vive en `backend/services/evangelism_crm_bridge.py`; no hardcodear pipeline ni etapa.

---

## 8. Backend — Modelo de datos

Tablas principales en `backend/models_evangelism.py`:

| Clase | Tabla | Rol |
|---|---|---|
| `CampaignSeason` | `campaign_seasons` | Temporadas/campanas para grupos |
| `Sede` | `sedes` | Scope organizacional |
| `LogAuditoria` | `logs_auditoria` | Auditoria |
| `CategoriaEstrategia` | `categorias_estrategia` | Catalogo de estrategia |
| `MotivoExcusa` | `motivos_excusa` | Catalogo de excusas |
| `EstrategiaEvangelismo` | `estrategias_evangelismo` | Estrategia principal |
| `RolPersonalizadoEstrategia` | `estrategia_roles_personalizados` | Roles por estrategia |
| `GrupoEvangelismo` | `grupos_evangelismo` | Grupo/celula/FARO |
| `ParticipanteGrupo` | `grupo_participantes` | Integrantes por grupo |
| `SesionGrupo` | `sesiones_grupo` | Sesiones programadas |
| `Asistencia` | `asistencias` | Asistencia y primera vez |
| `RegistroSeguimiento` | `registros_seguimiento` | Seguimiento post-asistencia |
| `HistorialEmbudo` | `historial_embudo` | Embudo evangelistico |

Enums relevantes:

- `RolEnGrupoEnum`
- `EstadoAsistenciaEnum`
- `TipoSeguimientoEnum`
- `FrecuenciaEnum`
- `EstadoSesionEnum`
- `HabilitacionSesionEnum`

Flujo canonico:

```text
EstrategiaEvangelismo
  -> GrupoEvangelismo
    -> ParticipanteGrupo
    -> SesionGrupo
      -> Asistencia
        -> RegistroSeguimiento
        -> CasoCRM via evangelism_crm_bridge
```

---

## 9. Backend — API surface

Router canonico: `backend/api/evangelism.py`.

Incluye:

- `evangelism_events`
- `evangelism_grupos`
- `evangelism_main` estrategias y roles
- `evangelism_multiplication`
- `evangelism_notifications`
- `evangelism_rankings`
- `evangelism_reports`
- `evangelism_analytics`

Rutas principales:

| Area | Rutas |
|---|---|
| Estrategias | `GET/POST /strategies`, `GET/PUT/DELETE /strategies/{id}`, `POST /strategies/{id}/generate-sessions` |
| Roles/excusas | `/strategies/{id}/roles`, `/excuses`, `/excuses/seed` |
| Grupos | `GET/POST /grupos`, `GET/PUT/DELETE /grupos/{id}`, aliases `/groups` |
| Sesiones | `GET/POST /sessions`, `GET/PUT/DELETE /sessions/{id}`, `PATCH /sessions/{id}/habilitacion` |
| Asistencia | `/sessions/{id}/attendance`, `/grupos/sessions/{id}/attendance`, aliases `/groups/sessions/...` |
| Seguimiento | `/follow-up/pending`, `/follow-up/{asistencia_id}`, `PATCH /follow-up/{seguimiento_id}` |
| Eventos | `/events/`, `/events/{id}`, `/events/{id}/attendance`, `/events/{id}/analytics`, `/events/{id}/sessions/{date}` |
| Scanner | `/scanner/generate/{persona_id}`, `/scanner/validate/{token}` |
| Rankings | `/rankings/groups`, `/rankings/monthly-comparison`, `/rankings/leaders` |
| Multiplicacion | `/multiplication/check`, `/multiplication/split`, `/multiplication/history` |
| Reportes | `/reports/group/{grupo_id}/attendance-pdf`, `/attendance-excel`, `/reports/strategy/{strategy_id}/summary` |
| Analytics | `/analytics/strategy/{id}`, `/trend`, `/funnel`, `/heatmap`, `/alerts`, `/velocity`, `/groups`, `/full` |

---

## 10. Frontend — Mapa de pantallas

`frontend/src/app/plataforma/evangelism/`:

| Ruta | Archivo | Estado |
|---|---|---|
| `/plataforma/evangelism` | `EvangelismClient.tsx`, `page.tsx` | Hecho — dashboard/orquestador |
| `/plataforma/evangelism/strategies/[id]` | `strategies/[id]/page.tsx` | Hecho — detalle alineado a hooks canonicos, contratos tipados y drawers operativos |
| `/plataforma/evangelism/strategies/[id]/analytics` | `strategies/[id]/analytics/page.tsx` | Hecho funcional, validar performance |
| `/plataforma/evangelism/groups` | `groups/page.tsx` | Hecho funcional |
| `/plataforma/evangelism/groups/[id]` | `groups/[id]/page.tsx` | Hecho funcional, asistencia y detalle de grupo |
| `/plataforma/evangelism/events` | `events/page.tsx` | Hecho funcional con gate profundo de creacion, asistencia y scanner |
| `/plataforma/evangelism/events/[id]` | `events/[id]/page.tsx`, tabs | Hecho funcional con gate profundo de detalle, agenda y analitica |
| `/plataforma/evangelism/rankings` | `rankings/page.tsx`, componentes | Hecho funcional |
| `/plataforma/evangelism/multiplication` | `multiplication/page.tsx` | Hecho funcional |
| `/plataforma/evangelism/scanner` | `scanner/page.tsx` | Hecho funcional, depende de permisos |

Componentes compartidos:

- `frontend/src/components/evangelism/EvangelismShell.tsx`
- `frontend/src/components/evangelism/StrategyCreationDrawer.tsx`
- `frontend/src/components/evangelism/ConfirmActionDrawer.tsx`

---

## 11. Estado del modulo

### Hecho

- Router canonico `/api/evangelism` compuesto por subrouters.
- Modelos principales con UUID en estrategia/grupo/persona.
- Sede isolation auditada en caminos principales de estrategia, grupo, sesion y asistencia.
- Soft delete en grupos/sesiones/asistencia donde aplica.
- Generacion de sesiones por frecuencia con servicio dedicado.
- Habilitacion/deshabilitacion de sesiones.
- Registro de asistencia y seguimiento.
- Puente Evangelismo -> CRM sin pipeline/etapa hardcodeados.
- Reportes PDF/Excel por grupo y resumen por estrategia.
- Rankings de grupos, lideres y comparacion mensual.
- Multiplicacion de grupos con endpoints propios.
- Scanner de personas con token `CCF-PER`.
- Confirmaciones destructivas via `ConfirmActionDrawer` en UI auditada.
- Detalle de estrategia alineado a hooks canonicos y sin doble fuente de verdad entre `page.tsx` y `useStrategyDetail.ts`.
- Eventos evangelisticos alineados a soft-delete real de `CrmEvent` con migracion dedicada.

### Parcial

- Ninguno.

### Pendiente

- Ninguno.

### Cerrado Fase 2 — Descomposición de estrategia (2026-07-24)

20. **Drift de tipos `strategyDetailShared.ts` ↔ `types.ts`** `[NUEVO-DRIFT-TYPES-001]` — cerrada el `2026-07-24`. Eliminadas 4 interfaces duplicadas drifted (`Strategy`, `StrategyGroup`, `SessionRow`, `HabilitacionEstado`) que ninguna caller importaba desde `strategyDetailShared`. Reducción 185→141 LOC. Sustituido tipo hackish `typeof Users` por `LucideIcon` idiomático. Commit `51c2a0a0`. Ver `docs/CIERRA_FASE2_EVANGELISMO_2026-07-24.md`.

21. **Sede-isolation en follow-up** `[NUEVO-FOLLOWUP-SEDE-001]` — cerrada el `2026-07-24`. CRUD `get_seguimientos` y `get_pendientes_seguimiento` ahora filtran por `sede_id` via join `seguimiento→asistencia→sesion→grupo→sede`. `update_seguimiento` añade `deleted_at.is_(None)` al query inicial. Handlers `GET /follow-up/pending` y `GET /follow-up/{asistencia_id}` pasan `require_user_sede_id` al CRUD. Smoke 2/2 + suite 226/226 verde. Commit `b346586e`.

22. **Test falso follow-up + badge tipo** `[NUEVO-FOLLOWUP-TEST-BADGE-001]` — cerrada el `2026-07-24`. Test `test_pending_followups` apiuntaba a `/asistencias/pending-follow-ups` (path inexistente, _ok acepta 404 → falso verde). Ahora apunta al path real `/follow-up/pending`. Badge `tipo` en page.tsx comparaba minusculas vs enum mayusculas — los 3 variants actuales ahora matchean via `.toLowerCase().includes(...)`. Commit `09192539`.

### Cerrado recientemente (Fase 0/1)

1. **RBAC evangelismo migrado** `[PEND-RBAC-EVANGELISM-001]` — cerrada el `2026-07-17` con migracion radical de `require_pastor_or_admin` a `evangelism:read/edit/manage` en los 14 archivos del modulo. Se agregaron guards `require_evangelism_*`, bypasses por rol (pastor/coordinador), y se eliminaron todas las referencias a `require_pastor_or_admin` del modulo.
2. **Enum canonico estados asistencia** `[PEND-ATTENDANCE-ENUM-001]` — cerrada el `2026-07-17`. `StatusAsistenciaCanonico` es ahora la fuente de verdad unica en `evangelism_shared.py`. Sets derivados del enum. Funciones `_attended()` y `_is_primera_vez()` migradas.
3. **Descomposicion hooks frontend** `[PEND-STRATEGY-DECOMPOSE-001]` — cerrada el `2026-07-18`. `strategies/[id]/page.tsx` consume los hooks canonicos del modulo y elimina duplicacion estructural de fetch/search/session actions.
4. **Busqueda remota de personas** `[PEND-PERSONAS-SEARCH-001]` — cerrada el `2026-07-17`. Endpoint `GET /personas/search` funcional con debounce, filtro sede y AbortController. Consumido desde frontend en asistencia (grupos) y visitor search.
5. **RBAC documentado por rol** `[PEND-RBAC-EVANGELISM-001]` — cerrada el `2026-07-16` con [EVANGELISMO_RBAC_MATRIX.md](/root/ccf/docs/EVANGELISMO_RBAC_MATRIX.md). Se conserva aqui solo como referencia historica del cierre mas reciente.
6. **Cierre Fase 1 RBAC — wrapper legacy** `[PARCIAL-RUNTIME-AUTH-001]` — cerrada el `2026-07-21`. Se elimino el paquete muerto `backend/api/_evangelism_helpers/` (sin importadores externos desde la migracion del `2026-07-17`). Su wrapper `require_pastor_or_admin_with_sede` era la unica referencia evangelism al guard `crm:manage`-coincidence historico. Funciones equivalentes viven en `backend/crud/evangelism.py:_actor_sede_or_none_evangelismo`. Modulo evangelism verificadamente 100% libre de `require_pastor_or_admin` (grep 0 hits). Bug secundario corregido: 5 tests usaban campo obsoleto `nombre` en PUT/POST `/grupos` cuando el schema exige `name`. Smoke 2/2 + suite amplia 226/226 verdes. Commit `339539e9`.
7. **Eventos evangelisticos** `[PARCIAL-EVENTS-001]` — cobertura amplia del modulo valida serializacion, roles, attendance y contratos asociados; cierre operativo confirmado el `2026-07-16` con `tests/test_evangelism_module_coverage.py` (`219 passed`).
8. **Multiplicacion** `[PARCIAL-MULTIPLICATION-001]` — validacion backend de `check/split/history` confirmada por la suite amplia el `2026-07-16`.
9. **Follow-up** `[PARCIAL-FOLLOWUP-001]` — contratos de seguimiento y respuestas validados por la suite amplia el `2026-07-16`.
10. **Contrato unico de eventos** `[PEND-EVENTS-CONTRACT-001]` — cierre operativo confirmado por la suite amplia el `2026-07-16`.
11. **Contrato unico de sesiones FARO/groups** `[PEND-SESSIONS-CONTRACT-001]` — aliases y contratos de sesiones validados por la suite amplia el `2026-07-16`.
12. **Permisos runtime UI** `[PARCIAL-RUNTIME-AUTH-001]` — cierre secundario el `2026-07-21` (entrada 6 de esta lista). La homologacion inicial del `2026-07-17` se completa ahora con la eliminacion del wrapper legacy.
13. **Smoke canónico frontend profundo** `[PARCIAL-SMOKE-EVANGELISM-001]` — cerrada el `2026-07-16` con `scripts/test_evangelism_quality.py`; el script raíz ya orquesta backend base y gates frontend vía `--frontend-smoke`, `--frontend-deep` y `--expanded`.
14. **Ampliar smoke canónico** `[PEND-EXPAND-SMOKE-EVANGELISM-001]` — cerrada el `2026-07-16` al formalizar el modo expandido y el gate frontend profundo desde `scripts/test_evangelism_quality.py`.
15. **Smoke frontend Evangelismo** `[PEND-FRONTEND-E2E-EVANGELISM-001]` — cerrada el `2026-07-16` con `frontend/tests/e2e/evangelism/smoke.spec.ts`; cubre dashboard, groups y rankings con guard de consola/API/assets.
16. **Smoke frontend profundo Evangelismo** `[PEND-FRONTEND-E2E-EVANGELISM-DEEP-001]` — cerrada el `2026-07-16` integrando `frontend/tests/e2e/evangelism/sessions-detail.spec.ts` y `frontend/tests/e2e/evangelism/rankings-multiplication.spec.ts` al runner modular del módulo.
17. **Smoke frontend profundo events/scanner** `[PEND-FRONTEND-E2E-EVANGELISM-EVENTS-SCANNER-001]` — cerrada el `2026-07-16` con `frontend/tests/e2e/evangelism/events-scanner.spec.ts`; cubre creación de eventos, asistencia con scanner, detalle con agenda/analítica y validación standalone del escáner.
18. **Detalle de estrategia** `[PARCIAL-STRATEGY-PAGE-001]` — cerrada el `2026-07-18`. Se consolido ownership de datos y acciones en `useStrategyDetail.ts`, se elimino la duplicacion estructural de la page y se revalido con lint + frontend profundo.
19. **Soft-delete de eventos CRM** `[PEND-CRM-EVENTS-SOFT-DELETE-001]` — cerrada el `2026-07-18`. `CrmEvent` recupero `deleted_at`, el router de eventos consulta solo activos y la migracion `20260718_0001_crm_events_deleted_at.py` deja el contrato persistido.

---

## 12. Archivos a leer antes de cambiar codigo

1. `docs/ESTADO_EVANGELISMO.md` — este handover.
2. `docs/PLAN_EVANGELISMO_CALIDAD.md` — orden de trabajo por fases.
3. `docs/EVANGELISMO_API_CONTRACTS.md` — contratos API, permisos y codigos esperados.
4. `docs/EVANGELISMO_QA_CHECKLIST.md` — checklist manual y automatizado.
5. `docs/AUDITORIA_FLUJO_EVANGELISMO_CCF.md` — flujo canonico y correcciones ya aplicadas.
6. `backend/models_evangelism.py` — modelo de datos.
7. `backend/schemas/evangelism.py` — contratos Pydantic.
8. `backend/api/evangelism.py` — router canonico.
9. `backend/api/evangelism_main/main_estrategias.py` — estrategias y generacion de sesiones.
10. `backend/api/evangelism_grupos/grupos_main.py` — grupos, seasons, analytics, visitantes.
11. `backend/api/evangelism_grupos/grupos_sesiones.py` — sesiones y habilitacion.
12. `backend/api/evangelism_grupos/grupos_asistencias.py` — asistencia y seguimiento.
13. `backend/api/evangelism_events/` — eventos y check-in.
14. `backend/services/evangelism_crm_bridge.py` — integracion CRM.
15. `frontend/src/app/plataforma/evangelism/strategies/[id]/page.tsx` — pantalla mas sensible.
16. `frontend/src/components/evangelism/` — shell/drawers compartidos.

---

## 13. Orden operativo recomendado

1. Reproducir el fallo con el usuario y anotar ruta exacta, rol y endpoint que falla.
2. Correr el smoke minimo del modulo.
3. Clasificar el fallo: auth/RBAC, contrato API, sede isolation, soft delete, serializacion, o UI state.
4. Corregir en la capa propietaria.
5. Repetir smoke minimo.
6. Si se toca frontend, correr e2e de evangelismo o al menos cargar `/plataforma/evangelism` y la ruta afectada con consola limpia.
7. Actualizar este doc solo si cambia estado, contrato, backlog o comando de validacion.

---

## 14. Tabla de IDs estables

| ID | Pieza | Archivo o area |
|---|---|---|
| `PARCIAL-STRATEGY-PAGE-001` | Cerrada el 2026-07-18. Ownership de datos y acciones consolidado en hooks canonicos; page revalidada con lint + E2E profundo. | `frontend/src/app/plataforma/evangelism/strategies/[id]/page.tsx` + `useStrategyDetail.ts` |
| `PEND-STRATEGY-DECOMPOSE-001` | Cerrada el 2026-07-18. La page ya consume hooks canonicos y elimina duplicacion estructural de fetch/search/session actions. | `useStrategyDetail.ts` + page.tsx |
| `PEND-PERSONAS-SEARCH-001` | Cerrada el 2026-07-17. Endpoint remoto + AbortController en frontend | `backend/api/evangelism_grupos/grupos_sesiones.py` + `useStrategyDetail.ts` |
| `PEND-RBAC-EVANGELISM-001` | Cerrada el 2026-07-17. Migracion radical a taxonomia evangelism:* | 14 archivos backend evangelismo |
| `PEND-ATTENDANCE-ENUM-001` | Cerrada el 2026-07-17. StatusAsistenciaCanonico como fuente unica | `backend/api/evangelism_shared.py` + `backend/schemas/evangelism.py` |
| `PARCIAL-SMOKE-EVANGELISM-001` | Cerrada el 2026-07-16. Script raíz ya orquesta backend base y gates frontend con flags formales. | `scripts/test_evangelism_quality.py` |
| `PEND-EXPAND-SMOKE-EVANGELISM-001` | Cerrada el 2026-07-16. Modo expandido y gate frontend profundo definidos desde el script canónico. | `scripts/test_evangelism_quality.py` |
| `PARCIAL-EVENTS-001` | Cerrada el 2026-07-16 tras validacion completa de la suite amplia del modulo. | `backend/api/evangelism_events/` + `frontend/src/app/plataforma/evangelism/events/` |
| `PARCIAL-MULTIPLICATION-001` | Cerrada el 2026-07-16 tras validacion de `/multiplication/check`, `/split` y `/history` en la suite amplia. | `backend/api/evangelism_multiplication.py` |
| `PARCIAL-FOLLOWUP-001` | Cerrada el 2026-07-16 tras validacion de follow-up y respuestas en la suite amplia. | `backend/api/evangelism_grupos/grupos_asistencias.py` |
| `PEND-EVENTS-CONTRACT-001` | Cerrada el 2026-07-16. Contrato de eventos validado por `tests/test_evangelism_module_coverage.py`. | `backend/api/evangelism_events/` |
| `PEND-SESSIONS-CONTRACT-001` | Cerrada el 2026-07-16. Contratos y aliases de sesiones validados por `tests/test_evangelism_module_coverage.py`. | `backend/api/evangelism_grupos/grupos_sesiones.py` |
| `PARCIAL-RUNTIME-AUTH-001` | Cerrada el 2026-07-17 (migracion RBAC) + 2026-07-21 (wrapper legacy). Migracion RBAC completa: guards evangelism:* en todos los routers + eliminacion del wrapper legacy `require_pastor_or_admin_with_sede` via borrado del paquete muerto `backend/api/_evangelism_helpers/`. | 14 archivos backend + `backend/core/permissions.py` + `backend/api/_evangelism_helpers/` (eliminado) |
| `PEND-CRM-EVENTS-SOFT-DELETE-001` | Cerrada el 2026-07-18. `CrmEvent.deleted_at` restaurado y persistido por migracion para alinear soft-delete de eventos. | `backend/models_crm.py` + `backend/api/evangelism_events/events_main.py` + `alembic/versions/20260718_0001_crm_events_deleted_at.py` |

Busqueda rapida:

```bash
grep -nE '^\d+\. \*\*.*\[(PARCIAL|PEND)-|^\| `(PARCIAL|PEND)-' /root/ccf/docs/ESTADO_EVANGELISMO.md
```
