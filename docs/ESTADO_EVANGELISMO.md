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
grep -nE "PARCIAL-|PEND-" /root/ccf/docs/ESTADO_EVANGELISMO.md
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
npx playwright test tests/e2e/evangelism/sessions-detail.spec.ts tests/e2e/evangelism/rankings-multiplication.spec.ts
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

**Estado global:** El modulo tiene base funcional y flujo canonico auditado. Quedan riesgos vivos en cobertura amplia de `test_evangelism_module_coverage.py`, contratos mixtos historicos y permisos/401 visibles en pantallas cuando el token o acceso del usuario no coincide con el modulo.

---

## 7. Convenciones del modulo

- **Ruta plataforma:** `/plataforma/evangelism`.
- **Ruta API:** `/api/evangelism`.
- **Cliente frontend:** usar `apiFetch('/evangelism/...', { token })`; no construir URLs absolutas ni saltar a `/api` manualmente en pantallas plataforma.
- **Auth y permisos:** los endpoints usan `require_module_access("evangelism", "...")`. Los 401/403 se investigan en sesion/permisos antes de cambiar contratos.
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
| `/plataforma/evangelism/strategies/[id]` | `strategies/[id]/page.tsx` | **Parcial** — archivo muy grande, mezcla grupos, sesiones, asistencia, roles, follow-up y vistas |
| `/plataforma/evangelism/strategies/[id]/analytics` | `strategies/[id]/analytics/page.tsx` | Hecho funcional, validar performance |
| `/plataforma/evangelism/groups` | `groups/page.tsx` | Hecho funcional, requiere validar permisos en runtime |
| `/plataforma/evangelism/groups/[id]` | `groups/[id]/page.tsx` | Hecho funcional, asistencia y detalle de grupo |
| `/plataforma/evangelism/events` | `events/page.tsx` | Parcial segun cobertura historica de eventos |
| `/plataforma/evangelism/events/[id]` | `events/[id]/page.tsx`, tabs | Parcial segun cobertura historica de eventos |
| `/plataforma/evangelism/rankings` | `rankings/page.tsx`, componentes | Hecho funcional |
| `/plataforma/evangelism/multiplication` | `multiplication/page.tsx` | Parcial por validaciones backend abiertas |
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

### Parcial

1. **Detalle de estrategia** `[PARCIAL-STRATEGY-PAGE-001]` — `frontend/src/app/plataforma/evangelism/strategies/[id]/page.tsx` concentra demasiadas responsabilidades. Separar grupos, sesiones, asistencia, roles y seguimiento en componentes/hooks locales antes de seguir creciendo.
2. **Eventos evangelisticos** `[PARCIAL-EVENTS-001]` — la matriz historica marca fallos de serializacion, roles, duplicados y attendance-history. Revalidar con `tests/test_evangelism_module_coverage.py` antes de tocar UI de eventos.
3. **Multiplicacion** `[PARCIAL-MULTIPLICATION-001]` — endpoints existen, pero la matriz historica exige validar 404/400 en grupo inexistente, inactivo, lider invalido y pocos participantes.
4. **Follow-up** `[PARCIAL-FOLLOWUP-001]` — flujo existe, pero la cobertura amplia historica senala serializacion y dispatch de 404 en seguimiento.
5. **Permisos runtime UI** `[PARCIAL-RUNTIME-AUTH-001]` — errores 401 en `/evangelism/grupos` y `/evangelism/sessions` deben resolverse revisando token, rol y `require_module_access`, no ocultando errores en frontend.
6. **Smoke canónico aún parcial** `[PARCIAL-SMOKE-EVANGELISM-001]` — `scripts/test_evangelism_quality.py` ya existe, pero todavía no cubre frontend ni cobertura profunda completa.

### Pendiente

1. **Descomposicion de estrategia** `[PEND-STRATEGY-DECOMPOSE-001]` — extraer hooks/componentes desde `strategies/[id]/page.tsx` y cubrirlos con prueba enfocada.
2. **Contrato unico de eventos** `[PEND-EVENTS-CONTRACT-001]` — cerrar response schemas y serializacion ORM -> dict en eventos/roles/asistencia.
3. **Contrato unico de sesiones FARO/groups** `[PEND-SESSIONS-CONTRACT-001]` — consolidar aliases `/grupos`, `/groups`, posibles rutas FARO y respuestas.
4. **RBAC documentado por rol** `[PEND-RBAC-EVANGELISM-001]` — documentar ADMIN / GESTOR / EDITOR / MIEMBRO sobre estrategias, grupos, sesiones, asistencia, reportes y eventos.
5. **Busqueda remota de personas** `[PEND-PERSONAS-SEARCH-001]` — evolucionar asistencia a busqueda remota con debounce para volumen alto.
6. **Ampliar smoke canónico** `[PEND-EXPAND-SMOKE-EVANGELISM-001]` — extender `scripts/test_evangelism_quality.py` a frontend y cobertura más profunda.

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
| `PARCIAL-STRATEGY-PAGE-001` | Detalle de estrategia demasiado grande | `frontend/src/app/plataforma/evangelism/strategies/[id]/page.tsx` |
| `PARCIAL-EVENTS-001` | Eventos: serializacion/roles/attendance | `backend/api/evangelism_events/` + `frontend/src/app/plataforma/evangelism/events/` |
| `PARCIAL-MULTIPLICATION-001` | Validaciones de multiplicacion | `backend/api/evangelism_multiplication.py` |
| `PARCIAL-FOLLOWUP-001` | Seguimiento y respuestas | `backend/api/evangelism_grupos/grupos_asistencias.py` |
| `PARCIAL-RUNTIME-AUTH-001` | 401 runtime en pantallas | permisos + token + `require_module_access` |
| `PARCIAL-SMOKE-EVANGELISM-001` | Script canónico existe, cobertura aún parcial | `scripts/test_evangelism_quality.py` |
| `PEND-STRATEGY-DECOMPOSE-001` | Separar page de estrategia | frontend evangelism strategy detail |
| `PEND-EVENTS-CONTRACT-001` | Contrato unico eventos | `backend/api/evangelism_events/` |
| `PEND-SESSIONS-CONTRACT-001` | Contrato unico sesiones/aliases | `backend/api/evangelism_grupos/grupos_sesiones.py` |
| `PEND-RBAC-EVANGELISM-001` | RBAC por rol documentado | backend permissions + tests |
| `PEND-PERSONAS-SEARCH-001` | Busqueda remota personas asistencia | frontend + `/evangelism/personas/search` |
| `PEND-EXPAND-SMOKE-EVANGELISM-001` | Ampliar script Evangelismo | `scripts/test_evangelism_quality.py` |

Busqueda rapida:

```bash
grep -nE "PARCIAL-|PEND-" /root/ccf/docs/ESTADO_EVANGELISMO.md
```
