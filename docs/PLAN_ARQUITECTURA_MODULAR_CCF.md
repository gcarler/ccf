# Plan de Arquitectura Modular — CCF

> **Objetivo:** reducir errores redundantes en la plataforma CCF mediante contratos por modulo, smoke tests por modulo y gates proporcionales al cambio. CCF no opera como microservicios; opera como monolito modular y necesita disciplina de contratos.

## 1. Diagnostico

La plataforma comparte runtime, base de datos, auth, permisos, sede, frontend y componentes UI. Por eso un cambio en una pieza compartida puede romper varios modulos aunque el usuario lo perciba como una pantalla aislada.

Problemas recurrentes observados:

- Respuestas API cambian sin contrato documentado.
- UI consume endpoints con permisos no validados por rol real.
- Componentes compartidos afectan varios modulos.
- Cambios de un modulo se mezclan con cambios de plataforma.
- No todos los modulos tienen smoke test canonico.
- El pre-push valida salud general, pero no siempre corre la suite del modulo tocado.
- La base documental modular ya esta estandarizada; la deuda principal se movio a gates, e2e y contratos cruzados.

Decision arquitectonica:

```text
CCF = monolito modular con contratos fuertes
No = microservicios
No = modulos aislados tecnicamente
Si = modulos funcionales con ownership, docs, QA y gates propios
```

## 2. Principios obligatorios

1. Un cambio pertenece a un modulo o a plataforma compartida.
2. Si toca plataforma compartida, se valida impacto en todos los modulos criticos.
3. Cada modulo debe tener `ESTADO_*`, contratos API si aplica, checklist QA y smoke test.
4. Un commit debe representar una unidad coherente.
5. Las piezas compartidas no se modifican como efecto secundario de un arreglo local.
6. Auth, RBAC, `personas.id`, `sede_id`, `apiFetch`, layout, AG Grid, migraciones y modelos compartidos son plataforma.
7. Un bug de modulo se corrige en la capa propietaria: backend, frontend, datos, permisos o contrato.

## 3. Clasificacion de cambios

### Cambio de modulo

Ejemplos:

- `frontend/src/app/plataforma/evangelism/**`
- `backend/api/evangelism_*`
- `frontend/src/components/projects/**`
- `backend/api/projects.py`

Regla:

- Leer docs del modulo.
- Correr smoke del modulo.
- No tocar plataforma compartida salvo causa demostrada.

### Cambio de plataforma compartida

Ejemplos:

- `backend/core/permissions.py`
- `backend/core/security.py`
- `backend/models_auth.py`
- `backend/models_crm.py` cuando afecta `Persona`
- `frontend/src/lib/api*`
- `frontend/src/components/ui/TableView.tsx`
- `frontend/next.config.mjs`
- `frontend/src/app/plataforma/layout.tsx`
- migraciones que alteran tablas compartidas

Regla:

- Tratar como cambio de plataforma.
- Correr smoke general y smoke de modulos dependientes.
- Documentar blast radius y rollback.

## 4. Modulos y estado documental

| Modulo | Estado doc | Falta |
|---|---|---|
| Proyectos | `docs/ESTADO_PROYECTOS.md`, `PLAN_PROYECTOS_CALIDAD.md`, `PROJECTS_API_CONTRACTS.md`, `PROJECTS_RBAC_MATRIX.md`, `PROJECTS_QA_CHECKLIST.md`, `PLAN_VISTAS_EDITABLES_PROYECTOS.md`, `scripts/test_projects_quality.py`, `frontend/tests/e2e/projects/smoke.spec.ts`, `frontend/tests/e2e/projects/detail.spec.ts` | extender demo seeded a roundtrip multiusuario |
| Evangelismo | `ESTADO_EVANGELISMO.md`, `PLAN_EVANGELISMO_CALIDAD.md`, `EVANGELISMO_API_CONTRACTS.md`, `EVANGELISMO_RBAC_MATRIX.md`, `EVANGELISMO_QA_CHECKLIST.md`, `scripts/test_evangelism_quality.py`, `frontend/tests/e2e/evangelism/smoke.spec.ts`, `frontend/tests/e2e/evangelism/sessions-detail.spec.ts`, `frontend/tests/e2e/evangelism/rankings-multiplication.spec.ts`, `frontend/tests/e2e/evangelism/events-scanner.spec.ts` | runtime auth UI, strategy page monolítica y búsqueda remota de personas |
| CRM | `ESTADO_CRM.md`, `PLAN_CRM_CALIDAD.md`, `CRM_API_CONTRACTS.md`, `CRM_RBAC_MATRIX.md`, `CRM_QA_CHECKLIST.md`, `scripts/test_crm_quality.py`, `frontend/tests/e2e/crm/smoke.spec.ts`, `frontend/tests/e2e/crm/persona-detail.spec.ts` | ampliar smoke a groups bridge, messaging y resources |
| Academy | `ESTADO_ACADEMY.md`, `PLAN_ACADEMY_CALIDAD.md`, `ACADEMY_API_CONTRACTS.md`, `ACADEMY_RBAC_MATRIX.md`, `ACADEMY_QA_CHECKLIST.md`, `scripts/test_academy_quality.py`, `frontend/tests/e2e/academy/smoke.spec.ts`, `frontend/tests/e2e/academy/profile-detail.spec.ts` | ampliar certificates, rutas duplicadas y flows admin |
| CMS | `ESTADO_CMS.md`, `PLAN_CMS_CALIDAD.md`, `CMS_API_CONTRACTS.md`, `CMS_RBAC_MATRIX.md`, `CMS_QA_CHECKLIST.md`, `scripts/test_cms_quality.py`, `frontend/tests/e2e/cms/smoke.spec.ts`, `frontend/tests/e2e/cms/pages-preview.spec.ts`, `PLAN_CMS_100.md` | builder, enterprise profundo y checklist visual preview/publicado |
| Messaging/Community | `ESTADO_MESSAGING_COMMUNITY.md`, `PLAN_MESSAGING_CALIDAD.md`, `MESSAGING_COMMUNITY_API_CONTRACTS.md`, `MESSAGING_COMMUNITY_RBAC_MATRIX.md`, `MESSAGING_COMMUNITY_QA_CHECKLIST.md`, `scripts/test_messaging_quality.py`, `frontend/tests/e2e/messaging/smoke.spec.ts`, `frontend/tests/e2e/messaging/direct-messages.spec.ts` | contrato chat + ampliar bridge CRM |
| Agenda/Calendar | `ESTADO_AGENDA.md`, `PLAN_AGENDA_CALIDAD.md`, `AGENDA_API_CONTRACTS.md`, `SYSTEM_CALENDAR_CONTRACT.md`, `AGENDA_RBAC_MATRIX.md`, `AGENDA_QA_CHECKLIST.md`, `scripts/test_agenda_quality.py`, `frontend/tests/e2e/agenda/smoke.spec.ts`, `frontend/tests/e2e/agenda/calendar-events.spec.ts` | taxonomía RBAC propia pendiente y profundidad en reservas/participantes |
| Auth/Admin/RBAC | `ESTADO_PLATAFORMA_COMPARTIDA.md`, `PLAN_PLATAFORMA_COMPARTIDA_CALIDAD.md`, `PLATAFORMA_AUTH_RBAC_API_UI.md`, `PLATAFORMA_AUTH_RUNTIME_CONTRACT.md`, `PLATAFORMA_UI_BASE_PROTEGIDA.md`, `PLATAFORMA_MATRIZ_MODULAR.md`, `PLATAFORMA_COMPARTIDA_QA_CHECKLIST.md`, `scripts/test_platform_quality.py` | seguimiento de RBAC por modulo vive en cada handover |

Complemento transversal obligatorio:

- `docs/BACKLOG_DRIFT_TRANSVERSAL_CCF.md` — patrones repetitivos cross-modulo, owner correcto y gates minimos.
- `docs/MATRIZ_COBERTURA_MODULAR_CCF.md` — cobertura documental y de smoke por modulo, con huecos abiertos reales.
- `docs/ARRANQUE_MODULAR_CCF.md` — entrada operativa uniforme por modulo para leer contexto, listar backlog y correr el smoke correcto sin reinterpretar ownership.

## 5. Entregables por modulo

Cada modulo debe tener:

1. `docs/ESTADO_<MODULO>.md`
2. `docs/<MODULO>_API_CONTRACTS.md` si expone API propia
3. `docs/<MODULO>_QA_CHECKLIST.md`
4. `scripts/test_<modulo>_quality.py` o suite pytest canonica documentada
5. IDs estables `PARCIAL-*` y `PEND-*`
6. Mapa de rutas frontend
7. Mapa de routers backend
8. Matriz RBAC minima
9. Lista de dependencias compartidas
10. Clasificacion contra backlog transversal de drift si el patron reaparece en varios modulos
11. Entrada de arranque alineada con `docs/ARRANQUE_MODULAR_CCF.md`

## 6. Matriz de smoke tests inicial

| Area tocada | Validacion minima |
|---|---|
| Arquitectura/base | `tests/test_smoke.py`, `tests/test_structural_contracts.py`, `tests/test_arquitectura_100pct.py` |
| Evangelismo | `tests/test_evangelism_triple7_flow.py`, `tests/test_evangelism_crm_bridge.py`, `tests/test_evangelism_reports_api.py`, `tests/test_calculo_sesiones.py` |
| Evangelismo amplio | `tests/test_evangelism_module_coverage.py` |
| Proyectos | `scripts/test_projects_quality.py`, `tests/test_projects_api.py`, `tests/test_projects_multi_tenant.py` |
| CRM | `tests/test_crm_domain.py`, `tests/test_crm_sede_isolation.py`, `tests/test_crm_runtime_security.py` |
| Academy | `tests/test_academy_api.py`, `tests/test_academy_domain.py` |
| CMS | `tests/test_cms_domain.py`, `tests/test_cms_sede_isolation.py`, `tests/test_cms_upload_and_image_hardening.py` |
| Messaging | `tests/test_messaging.py`, `tests/test_messaging_api.py`, `tests/test_messaging_sede_isolation.py` |
| Frontend compartido | `cd frontend && npm run build` + rutas criticas en Playwright |

Esta matriz es baseline; debe ajustarse al crear scripts canonicos por modulo.

## 7. Fases de implementacion

### Fase 1 — Gobierno documental

**ID:** `MOD-F1-DOCS`

Entregables:

- Crear este plan raiz.
- Completar docs faltantes de CRM.
- Completar docs faltantes de Academy.
- Completar docs faltantes de CMS.
- Completar docs faltantes de Agenda/Calendar.
- Completar doc de plataforma compartida: Auth/RBAC/API/UI.
- Uniformar la entrada operativa de todos los modulos en un bootstrap compartido.

Criterio de salida:

- Cada modulo critico tiene estado canonico.
- Cada doc tiene comandos de arranque y backlog estable.
- Existe una entrada operativa uniforme para no redescubrir el mismo contexto en cada sesion.

### Fase 2 — Smoke scripts canonicos

**ID:** `MOD-F2-SMOKE`

Entregables:

- `scripts/test_evangelism_quality.py`
- `scripts/test_crm_quality.py`
- `scripts/test_academy_quality.py`
- `scripts/test_cms_quality.py`
- `scripts/test_messaging_quality.py`
- `scripts/test_agenda_quality.py`
- `scripts/test_platform_quality.py`

Regla:

- Cada script debe imprimir resumen `passed/failed`.
- Debe crear o reutilizar datos de prueba de forma idempotente.
- Debe fallar con codigo distinto de cero si rompe un contrato critico.

Criterio de salida:

- Un agente puede validar un modulo sin recordar la lista de tests.

### Fase 3 — Selector de pruebas por cambio

**ID:** `MOD-F3-TEST-SELECTOR`

Entregables:

- Crear `scripts/select_quality_checks.py`.
- Mapear patrones de archivos a suites.
- Integrar en `scripts/hooks/pre-push`.

Ejemplo de reglas:

| Patron | Checks |
|---|---|
| `backend/api/evangelism*`, `frontend/src/app/plataforma/evangelism/**` | evangelism quality |
| `backend/api/projects.py`, `frontend/src/app/plataforma/projects/**`, `frontend/src/components/projects/**` | projects quality |
| `backend/api/crm*`, `frontend/src/app/plataforma/crm/**` | crm quality |
| `frontend/src/components/ui/TableView.tsx`, `frontend/next.config.mjs` | frontend build + CRM + projects + evangelism smoke |
| `backend/core/permissions.py`, `backend/models_auth.py` | platform + all critical module smoke |
| `alembic/versions/**` | migration chain + affected module smoke |

Criterio de salida:

- El pre-push corre pruebas proporcionales al cambio.
- Cambios documentales genéricos siguen usando smoke general rapido.
- Cambios en `ESTADO_*`, contratos API, matrices RBAC o checklists QA del owner disparan al menos el smoke canónico del modulo o de plataforma compartida.

### Fase 4 — Contratos API y RBAC

**ID:** `MOD-F4-CONTRACTS`

Entregables:

- Contrato API CRM.
- Contrato API Projects.
- Contrato API Academy.
- Contrato API CMS.
- Contrato RBAC plataforma.

Cada contrato debe incluir:

- endpoints
- metodos
- payload minimo
- response shape
- codigos esperados
- permisos por rol
- relaciones con `personas.id` y `sede_id`

Criterio de salida:

- Un cambio de endpoint no se aprueba si no actualiza contrato o conserva forma.

### Fase 5 — QA frontend por rutas criticas

**ID:** `MOD-F5-FRONTEND-QA`

Entregables:

- Playwright smoke de rutas criticas:
  - `/plataforma/crm/personas`
  - `/plataforma/projects`
  - `/plataforma/evangelism`
  - `/plataforma/academy`
  - `/plataforma/cms`
- Captura de consola: bloquear 401/403/404/500 no esperados.
- Validacion de assets `_next/static`.

Avance inicial `2026-07-16`:

- suite compartida `frontend/tests/e2e/platform-critical-routes.spec.ts` creada para las 5 rutas críticas canónicas
- usa login previo por `E2E_EMAIL`/`E2E_PASSWORD`
- falla por `console.error`, `pageerror`, respuestas API 4xx/5xx y assets `_next/static` rotos
- no cierra todavía los pendientes e2e dedicados de CRM o Academy; sí cierra la primera capa transversal del gate frontend
- suites profundas protegidas de Proyectos y Evangelismo ya usan `frontend/scripts/run-managed-playwright.mjs` para levantar `webServer` administrado y dejar de depender de arrancar Next manualmente

Criterio de salida:

- Un build que carga pero rompe consola no se considera sano.

### Fase 6 — CI/pre-push reforzado

**ID:** `MOD-F6-GATE`

Entregables:

- Pre-push con selector por modulo.
- Modo rapido local.
- Modo completo para release.
- Reporte claro de que modulo fallo y por que.

Criterio de salida:

- El hook deja de ser solo generalista.
- Los errores redundantes empiezan a bloquearse antes del push.
- Validacion y deploy no se ejecutan como si fueran el mismo acto.
- El smoke frontend modular agregado puede correrse con un solo comando y opcionalmente desde `pre-push` full.
- La misma bateria modular puede correrse por matriz de usuarios reales sin reescribir las suites.

## 8. Orden recomendado de ejecucion

1. CRM: crear documentacion canonica porque es el modulo con mas cruces.
2. Evangelismo: crear `scripts/test_evangelism_quality.py`.
3. Proyectos: separar contratos API y QA checklist.
4. Crear selector de pruebas por cambio.
5. Integrar selector al pre-push.
6. Crear Playwright smoke de rutas criticas.
7. Completar Academy/CMS/Agenda.

## 9. Politica de commits

- Un commit documental por modulo.
- Un commit por smoke script.
- Un commit por integracion de pre-push.
- No mezclar refactors de UI con contratos backend.
- No mezclar migraciones con cambios visuales.
- Si un commit toca plataforma compartida, el mensaje debe indicarlo.

## 10. Definicion de hecho

La arquitectura modular queda implementada cuando:

- Todos los modulos criticos tienen documentos canonicos.
- Los modulos criticos tienen smoke test ejecutable.
- El pre-push selecciona pruebas por area tocada.
- Las piezas compartidas disparan smoke de modulos dependientes.
- Los contratos API/RBAC existen para CRM, Projects, Evangelism, Academy y CMS.
- Las rutas frontend criticas tienen smoke con consola limpia.

## 11. Primer sprint propuesto

**Sprint 1 — Estabilizacion de proceso**

1. Crear `ESTADO_CRM.md`.
2. Crear `CRM_API_CONTRACTS.md`.
3. Crear `CRM_QA_CHECKLIST.md`.
4. Crear `scripts/test_evangelism_quality.py`.
5. Crear `scripts/test_crm_quality.py`.
6. Crear `scripts/select_quality_checks.py` sin integrarlo todavia al hook.
7. Validar selector con cambios simulados.

Resultado esperado:

- CRM y evangelismo quedan al nivel documental de proyectos.
- Ya existe base tecnica para gates por modulo.
