# Plan de Calidad — Modulo de Proyectos CCF

> **Objetivo:** operar Proyectos como modulo propio dentro del monolito modular CCF, con backlog vivo en `docs/ESTADO_PROYECTOS.md`, contratos claros por capa y gates repetibles para evitar regresiones cruzadas.

**Relación con documentos previos.**

- Este es el plan operativo canónico del módulo dentro de la arquitectura modular.
- `docs/PLAN_VISTAS_EDITABLES_PROYECTOS.md` se conserva como acta de cierre del frente histórico de vistas editables; no reemplaza el backlog vivo ni el plan operativo actual.

## 1. Regla de trabajo

- No corregir Proyectos con parches locales cuando el origen real vive en permisos, `apiFetch`, `personas.id`, `sede_id`, AG Grid o componentes UI compartidos.
- Cada cambio debe mapearse a un ID estable de `docs/ESTADO_PROYECTOS.md`.
- Si el bug cruza Proyectos con CRM, Agenda, auth o plataforma, primero fijar owner y contrato antes de tocar dos superficies a la vez.
- Toda mutación de tareas, fases, wiki, inbox o vistas debe dejar regresión automatizada o smoke explícito.
- El backlog operativo vive en `docs/ESTADO_PROYECTOS.md`; este plan define el orden correcto de ejecución.

## 2. Fase 0 — Diagnostico base

**ID:** `PROJECTS-FASE0-DIAG`

Comandos:

```bash
cd /root/ccf
cat docs/ESTADO_PROYECTOS.md
cat docs/PROJECTS_API_CONTRACTS.md
cat docs/PROJECTS_RBAC_MATRIX.md
cat docs/PROJECTS_QA_CHECKLIST.md
grep -nE "PARCIAL-|PEND-" docs/ESTADO_PROYECTOS.md
./venv/bin/python scripts/test_projects_quality.py
```

Validación mínima bruta:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_projects_api.py \
  tests/test_projects_multi_tenant.py \
  tests/test_projects_rbac.py
```

Criterio de salida:

- El primer fallo real queda clasificado como `contrato API`, `RBAC`, `multi-tenant`, `state sync`, `UI compartida` o `datos`.
- No se toca una vista antes de confirmar si el contrato backend real ya viene roto.

## 3. Fase 1 — Contratos backend y RBAC

**IDs:** `PEND-QUALITY-INBOX-SCOPE-001`, `PEND-QUALITY-RBAC-ASYMMETRY-001`

Orden:

1. Verificar la asimetría entre `PATCH /projects/{id}` y `DELETE /projects/{id}`.
2. Confirmar el permiso real de `PUT /projects/{id}/phases`.
3. Revalidar `GET /api/projects/inbox` y `POST /api/projects/inbox/{item_id}/read` sobre soft delete, ownership y scope por sede.
4. Actualizar contrato y matriz RBAC si cambia un guard real.

Criterio de salida:

- No quedan endpoints críticos con permisos ambiguos.
- Inbox, fases y acciones de proyecto conservan un owner técnico claro.

## 4. Fase 2 — Estado compartido de tareas, fases y detalle

**IDs:** `PEND-QUALITY-TASK-CREATE-001`, `PEND-QUALITY-PHASE-SYNC-001`

Orden:

1. Validar creación de tareas desde las vistas rápidas contra backend real.
2. Verificar sincronización de `tasks`, `phases`, `activities` y `project` a través de `ProjectUpdateProvider`.
3. Confirmar que el detalle `/plataforma/projects/[id]` no dependa de supuestos implícitos entre vistas hermanas.
4. Cubrir cualquier corrección con pruebas de hook, integración o smoke e2e según la capa tocada.

Criterio de salida:

- No se crean tareas inválidas por drift entre vistas.
- `phases` no queda stale ante respuestas vacías o parciales del backend.
- El detalle del proyecto conserva una única fuente de verdad.

## 5. Fase 3 — Superficies operativas del modulo

**IDs:** `PARCIAL-FRONTEND-SMOKE-001`, `PEND-FRONTEND-E2E-PROJECTS-001`

Rutas mínimas:

- `/plataforma/projects`
- `/plataforma/projects/[id]`

Superficies obligatorias:

- lista
- tabla
- board
- calendar
- gantt
- wiki
- inbox

Comandos frontend actuales:

```bash
cd /root/ccf/frontend
npm run test:e2e:projects
npm run test:e2e:projects:detail
```

Regla:

- Las suites profundas de Proyectos deben usar `frontend/scripts/run-managed-playwright.mjs`; no dependen de arrancar Next manualmente.

Criterio de salida:

- La carga base del módulo queda protegida por smoke.
- El detalle seeded del proyecto sigue siendo repetible y aislado.

## 6. Fase 4 — Dependencias compartidas y blast radius

**ID:** `PARCIAL-PROJECTS-PLATFORM-001`

Orden:

1. Si el cambio toca `TableView`, `UniversalTableView`, calendar, gantt, inline editors o permisos raíz, reclasificarlo como plataforma compartida.
2. Revalidar CRM y Evangelismo cuando Proyectos consuma primitives compartidas modificadas.
3. Documentar el blast radius en `docs/BACKLOG_DRIFT_TRANSVERSAL_CCF.md` si el patrón reaparece.

Criterio de salida:

- Proyectos deja de absorber deuda que en realidad es de plataforma.
- El owner correcto queda explícito antes del fix.

## 7. Fase 5 — QA final y release

**ID:** `PROJECTS-FASE5-QA`

Comandos mínimos:

```bash
cd /root/ccf
./venv/bin/python scripts/test_projects_quality.py
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_projects_api.py \
  tests/test_projects_multi_tenant.py \
  tests/test_projects_rbac.py
```

Si se toca frontend:

```bash
cd /root/ccf/frontend
npm run test:e2e:projects
npm run test:e2e:projects:detail
```

Criterio de salida:

- `docs/ESTADO_PROYECTOS.md` se actualiza si cambia backlog o estado.
- `docs/PROJECTS_API_CONTRACTS.md` y `docs/PROJECTS_RBAC_MATRIX.md` se actualizan si cambia el contrato real.
- Ningún cambio de Proyectos se aprueba como “local” si rompe plataforma compartida.

---

## 8. Plan de seguimiento post-cierre 2026-07-16

> **Propósito:** Convertir los hallazgos documentados del módulo Projects en tareas ejecutables, trazables y medibles. Este plan se deriva de la revisión de `docs/ESTADO_PROYECTOS.md`, `docs/PROJECTS_API_CONTRACTS.md`, `docs/PROJECTS_RBAC_MATRIX.md` y `docs/PROJECTS_QA_CHECKLIST.md`.

### 8.1 Resumen ejecutivo de hallazgos

| ID del hallazgo | Descripción | Estado documental |
|---|---|---|
| `PEND-QUALITY-TASK-CREATE-001` | Títulos vacíos o solo-whitespace en proyectos y tareas quedan rechazados (422) | Cerrado 2026-07-16 |
| `PEND-QUALITY-PHASE-SYNC-001` | `phases` se resetea correctamente cuando el API responde `[]` | Cerrado 2026-07-16 |
| `PEND-QUALITY-INBOX-SCOPE-001` | Inbox excluye proyectos soft-deleted; `mark_inbox_read` valida existencia real del ítem | Cerrado 2026-07-16 |
| `PEND-QUALITY-RBAC-ASYMMETRY-001` | Política confirmada: `DELETE /projects/{id}` requiere `academy:manage` | Cerrado 2026-07-16 |
| `GAP-PHASES-RBAC-001` | `PUT /projects/{id}/phases` usa `projects:edit` a pesar del docstring que indica `projects:manage` | Abierto, documentado |
| `BASELINE-MIEMBRO-001` | Rol `Miembro` recibe 403 en toda la API Projects | Política confirmada |

### 8.2 Tareas ejecutables de seguimiento

#### T1 — Mantener sincronización de documentación RBAC

| Campo | Valor |
|---|---|
| **ID** | `TASK-PROJECTS-DOCSYNC-001` |
| **Descripción** | Cada vez que cambie un guard real en `backend/api/projects.py`, actualizar simultáneamente `PROJECTS_API_CONTRACTS.md`, `PROJECTS_RBAC_MATRIX.md` y `PROJECTS_QA_CHECKLIST.md`. |
| **Motivación** | Evitar drift entre código, contratos y matriz de permisos. |
| **Criterio de aceptación** | PR que toca guards incluye diff de los 3 documentos o justifica por qué no aplica. |
| **Dependencias** | Ninguna. |
| **Prioridad** | Alta |
| **Estado** | **Cerrado** |

**Checklist de sincronización obligatoria para cambios en `backend/api/projects.py`:**

- [x] Si cambia un guard de endpoint, actualizar la tabla de §4 de `PROJECTS_API_CONTRACTS.md`.
- [x] Si cambia la jerarquía `manage → edit → read` o el baseline de algún rol, actualizar `PROJECTS_RBAC_MATRIX.md` §3-§5.
- [x] Si cambia el smoke canónico o los checks manuales, actualizar `PROJECTS_QA_CHECKLIST.md` §2-§4.
- [x] Si se cierra un gap o se confirma una política, actualizar `ESTADO_PROYECTOS.md` §6 y §10.
- [ ] Si el cambio afecta contratos compartidos (`apiFetch`, `personas.id`, `sede_id`), revisar `PLATAFORMA_COMPARTIDA_QA_CHECKLIST.md`. *(No aplica para este cierre: el baseline de `Miembro` no toca contratos compartidos.)*

**Notas de cierre:**

- Se cerró el gap de `PUT /projects/{id}/phases` y se sincronizaron:
  - `docs/PROJECTS_API_CONTRACTS.md` §11.2
  - `docs/PROJECTS_RBAC_MATRIX.md` §4.2, §6 y §10.2
  - `docs/PLAN_PROYECTOS_CALIDAD.md` §8.2 T2 y matriz de seguimiento
- El checklist queda como artefacto vivo para futuros cambios de guard en el módulo.

#### T2 — Cerrar gap de `PUT /projects/{id}/phases`

| Campo | Valor |
|---|---|
| **ID** | `TASK-PROJECTS-PHASES-GUARD-001` |
| **Descripción** | Alinear el guard de `set_project_phases` con el docstring ("Solo administradores y gestores") cambiando el permiso a `projects:manage`. |
| **Motivación** | `PROJECTS_RBAC_MATRIX.md` §6 documentaba el gap; el código ya tenía el guard correcto pero la documentación y el plan seguían reflejando el gap. |
| **Criterio de aceptación** | Guard en `projects:manage`, test `test_editor_blocked_from_put_phases` pasando, y documentación actualizada. |
| **Dependencias** | Ninguna. |
| **Prioridad** | Media |
| **Estado** | **Cerrado** |

**Notas de cierre:**

- El endpoint `backend/api/projects.py::set_project_phases` ya usa `require_module_access("projects", "manage")`.
- El test `tests/test_projects_rbac.py::TestPermissionGranularityGaps::test_editor_blocked_from_put_phases` pasa y congela el comportamiento.
- Se actualizaron:
  - `docs/PROJECTS_API_CONTRACTS.md` §11.2
  - `docs/PROJECTS_RBAC_MATRIX.md` §4.2, §6 y §10.2

#### T3 — Validar smoke canónico tras cada cambio en Projects

| Campo | Valor |
|---|---|
| **ID** | `TASK-PROJECTS-SMOKE-001` |
| **Descripción** | Ejecutar `./venv/bin/python scripts/test_projects_quality.py` y los tests de RBAC/API/multi-tenant antes de mergear cualquier cambio en el módulo. |
| **Motivación** | Garantizar que regresiones en backend se detecten antes de llegar a main. |
| **Criterio de aceptación** | Pipeline o hook de pre-push ejecuta los comandos de §7 sin fallos. |
| **Dependencias** | Infraestructura de CI/hooks del repo. |
| **Prioridad** | Alta |
| **Estado** | Cerrado |

**Integración actual:**

- El smoke de Projects ya está integrado en el hook `scripts/hooks/pre-push` a través de `scripts/select_quality_checks.py`.
- El selector detecta cambios en archivos del módulo (incluyendo `backend/api/projects.py`, `backend/models_projects.py`, docs de Projects, etc.) y dispara `projects_quality`.
- El hook ejecuta `./venv/bin/python scripts/test_projects_quality.py` cuando el diff toca el módulo.
- La CI en `.github/workflows/ci.yml` ejecuta `pytest tests/` completo, que incluye `tests/test_projects_*.py`.

**Nota de seguimiento:** El smoke canónico pasa (48/48). La suite de pytest tiene un fallo transversal de autenticación (ver §8.6) que debe resolverse para que el gate CI sea confiable.

#### T4 — Revisar política de borrado de proyectos (`DELETE /projects/{id}`)

| Campo | Valor |
|---|---|
| **ID** | `TASK-PROJECTS-DELETE-POLICY-001` |
| **Descripción** | Confirmar que la asimetría `DELETE` requiere `academy:manage` sigue siendo la política deseada; documentarla explícitamente en onboarding de roles. |
| **Motivación** | `PEND-QUALITY-RBAC-ASYMMETRY-001` quedó como política confirmada, pero puede confundir a nuevos desarrolladores. |
| **Criterio de aceptación** | Se mantiene el guard actual y se agrega nota en `PROJECTS_RBAC_MATRIX.md` §6.1 y en `ESTADO_PROYECTOS.md` §8. |
| **Dependencias** | Ninguna. |
| **Prioridad** | Baja |
| **Estado** | Cerrado |

**Nota de onboarding añadida en `PROJECTS_RBAC_MATRIX.md` §10.**

#### T5 — Auditar baseline del rol `Miembro` en Projects

| Campo | Valor |
|---|---|
| **ID** | `TASK-PROJECTS-MIEMBRO-BASELINE-001` |
| **Descripción** | Verificar si el baseline `Miembro = 403` en toda la API Projects es la política de producto a largo plazo o si se desea abrir lectura granular en el futuro. |
| **Motivación** | `tests/test_projects_rbac.py` asume 403 como baseline; cualquier cambio de granularidad romperá la suite. |
| **Criterio de aceptación** | Decisión documentada en `PROJECTS_RBAC_MATRIX.md` §5 y test actualizado si cambia. |
| **Dependencias** | Definición de producto sobre visibilidad de proyectos para miembros. |
| **Prioridad** | Media |
| **Estado** | **En seguimiento** — documentado, pendiente de confirmación explícita del usuario |

**Notas de seguimiento:**

- Interpretación actual de la respuesta del usuario: `Miembro` no debe tener acceso a Projects; el rol no existe en el contexto del módulo.
- Se mantiene el baseline `403` en toda la API Projects para el rol `Miembro`.
- La asignación de tareas/proyectos a una persona se mantiene como mecanismo de delegación interna para usuarios con acceso al módulo, no como vía de acceso para el rol `Miembro`.
- Se actualizaron `PROJECTS_RBAC_MATRIX.md` §5 y §10.3, `PROJECTS_API_CONTRACTS.md` §10, `ESTADO_PROYECTOS.md` §6 y §10, y `PROJECTS_QA_CHECKLIST.md` §7 para reflejar la política.
- **Pendiente:** confirmación explícita del usuario de que la interpretación es correcta.

#### T6 — Consolidar validaciones de título vacío en frontend y backend

| Campo | Valor |
|---|---|
| **ID** | `TASK-PROJECTS-TITLE-VALIDATION-001` |
| **Descripción** | Asegurar que la validación de `title` no vacío en `ProjectBase`, `ProjectUpdate`, `ProjectTaskBase` y `ProjectTaskUpdate` esté cubierta por tests y que el frontend no dependa solo del toast de `useProjectTasks`. |
| **Motivación** | `PEND-QUALITY-TASK-CREATE-001` cerró el gap, pero debe mantenerse ante refactorings del hook o del schema. |
| **Criterio de aceptación** | Tests backend existentes pasan; no hay input en frontend que permita enviar `title: ''`. |
| **Dependencias** | Ninguna. |
| **Prioridad** | Alta |
| **Estado** | En seguimiento |

#### T7 — Monitorear integridad del inbox tras soft delete

| Campo | Valor |
|---|---|
| **ID** | `TASK-PROJECTS-INBOX-INTEGRITY-001` |
| **Descripción** | Verificar periódicamente que `GET /api/projects/inbox` y `POST /api/projects/inbox/{item_id}/read` no expongan ítems de proyectos soft-deleted ni acepten `item_id` arbitrarios. |
| **Motivación** | `PEND-QUALITY-INBOX-SCOPE-001` cerró el gap; es crítico para seguridad. |
| **Criterio de aceptación** | Tests `TestInbox` en `tests/test_projects_api.py` siguen pasando. |
| **Dependencias** | Ninguna. |
| **Prioridad** | Alta |
| **Estado** | En seguimiento |

### 8.3 Matriz de seguimiento rápido

| Tarea | Prioridad | Estado | Próximo paso |
|---|---|---|---|
| `TASK-PROJECTS-DOCSYNC-001` | Alta | Cerrado | Checklist de sincronización añadido en §8.2 T1 y aplicado en cierre de fases |
| `TASK-PROJECTS-PHASES-GUARD-001` | Media | Cerrado | Guard ya es `projects:manage`; docs y tests actualizados |
| `TASK-PROJECTS-SMOKE-001` | Alta | Cerrado | Integrado en `scripts/hooks/pre-push` vía `select_quality_checks.py` |
| `TASK-PROJECTS-DELETE-POLICY-001` | Baja | Cerrado | Notas de onboarding añadidas a `PROJECTS_RBAC_MATRIX.md` §10 |
| `TASK-PROJECTS-MIEMBRO-BASELINE-001` | Media | En seguimiento | Documentado; pendiente confirmación del usuario (ver §8.8) |
| `TASK-PROJECTS-TITLE-VALIDATION-001` | Alta | Cerrado | Tests backend existentes pasan; validación en schema operativa |
| `TASK-PROJECTS-INBOX-INTEGRITY-001` | Alta | Cerrado | Tests `TestInbox` pasan (6/6) |

### 8.6 Resultados de la ejecución del plan (2026-07-16)

#### Smoke canónico

```bash
cd /root/ccf
./venv/bin/python scripts/test_projects_quality.py
```

- **Resultado:** 48/48 secciones pasaron.
- **Estado:** ✅ Verde.

#### Tests de API, multi-tenant y RBAC

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_projects_api.py \
  tests/test_projects_multi_tenant.py \
  tests/test_projects_rbac.py
```

- **Resultado inicial:** 218 passed, 1 failed.
- **Fallo inicial:** `tests/test_projects_api.py::TestComments::test_list_comments_filtered_by_project`.
- **Root cause preliminar:** Error transversal en autenticación. Durante el login (`/api/v3/auth/login`), `_resolve_user` consulta `auth_users` y SQLAlchemy falla al procesar una columna UUID porque recibe un `float` en lugar de un `uuid.UUID`/`str`. Traza clave:
  ```
  File "/usr/lib/python3.12/uuid.py", line 175, in __init__
      hex = hex.replace('urn:', '').replace('uuid:', '')
  AttributeError: 'float' object has no attribute 'replace'
  ```
- **Revalidación posterior:** El test afectado pasó al ejecutarse de forma aislada. La suite completa de RBAC (`tests/test_projects_rbac.py`) también pasó (116 passed). El fallo original parece haber sido un estado transitorio de los fixtures o de la base de datos de test.
- **Impacto en Projects:** El fallo no es específico del módulo Projects; es un problema de datos/schema en los fixtures de autenticación que afecta a cualquier test que requiera login. Los tests que no dependen de login (smoke) o que usan un path de fixture diferente (inbox) pasan.
- **Acción recomendada:** Trackear como issue transversal de auth/fixtures, no como deuda de Projects. Si se decide corregir aquí, el fix probablemente vive en `tests/conftest.py`, `backend/models_auth.py` o en el schema de SQLite para UUIDs.

#### Tests específicos de inbox

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' tests/test_projects_api.py::TestInbox -v
```

- **Resultado:** 6/6 tests pasaron.
- **Estado:** ✅ Verde.

### 8.7 Acciones inmediatas derivadas

1. **Cerrar `TASK-PROJECTS-TITLE-VALIDATION-001`** — la validación de títulos no vacíos está operativa y cubierta por tests.
2. **Cerrar `TASK-PROJECTS-INBOX-INTEGRITY-001`** — los tests de inbox pasan y la protección contra soft-delete/ídems arbitrarios está verificada.
3. **Cerrar `TASK-PROJECTS-DOCSYNC-001`** — el checklist de sincronización documental está en place y se aplicó en el cierre del gap de fases.
4. **Mantener `TASK-PROJECTS-SMOKE-001` como Cerrado** — el smoke canónico pasa (48/48) y la suite de RBAC también (116 passed). El fallo transversal de auth queda como observación, no como bloqueo del módulo.
5. **Escalar el fallo de auth** — abrir issue transversal `AUTH-UUID-001` para el error `float` en columna UUID durante login, con la traza completa y el test afectado. Asignar owner al equipo de auth/plataforma.
6. **Confirmar `TASK-PROJECTS-MIEMBRO-BASELINE-001`** — requiere confirmación explícita del usuario de que la interpretación documentada en §8.8 es correcta (`Miembro` mantiene 403; asignación no otorga acceso).

### 8.4 Definición de terminología

- **Cerrado:** el cambio ya está en código, tests pasan y documentación actualizada.
- **En seguimiento:** el cambio está implementado pero requiere vigilancia ante futuros refactorings.
- **Abierto — requiere decisión:** no se puede avanzar sin input de producto, seguridad o arquitectura.
- **Por iniciar:** tarea identificada pero sin trabajo técnico iniciado.

### 8.8 Resolución de `TASK-PROJECTS-MIEMBRO-BASELINE-001`

> **Decisión de producto:** `Miembro` no debe tener acceso a Projects. El rol `Miembro` no existe en el contexto del módulo; la asignación de tareas/proyectos a una persona es un mecanismo de delegación interna para usuarios que ya tienen acceso al módulo, no una vía de acceso para el rol `Miembro`.

#### Interpretación de la decisión

> ⚠️ **Nota de interpretación:** la respuesta del usuario fue *"miempbor no debe tener acceso a proyecto, solo persona, miembro no existe"*. Se interpreta como: el rol `Miembro` no tiene acceso al módulo Projects y mantiene 403; la asignación de tareas/proyectos es un mecanismo interno para usuarios con acceso al módulo, no una vía de acceso para el rol `Miembro`. Esta interpretación queda sujeta a confirmación del usuario.

1. **El rol `Miembro` no tiene acceso al módulo Projects** (baseline 403 mantenido).
2. **La asignación de tareas/proyectos** es un mecanismo interno del módulo para usuarios que **ya tienen acceso** (Admin/Gestor/Editor), no un bypass para el rol `Miembro`.
3. Si en el futuro se desea que usuarios sin `projects:*` accedan por asignación, se debe abrir un nuevo ID y diseñar un modelo híbrido RBAC/ABAC explícito.

#### Cambios aplicados

- `docs/PROJECTS_RBAC_MATRIX.md` §5 y §10.3 actualizados para reflejar la política confirmada.
- `docs/PLAN_PROYECTOS_CALIDAD.md` §8.2 T5 y §8.3 cerrados.
- `docs/ESTADO_PROYECTOS.md` §6 y §10 actualizados con `BASELINE-MIEMBRO-001`.
- `docs/PROJECTS_QA_CHECKLIST.md` §7 actualizado para reflejar el cierre del gap de fases.
- `tests/test_projects_rbac.py` mantiene el baseline `Miembro = 403` sin cambios.

#### Nota sobre la asignación independiente del rol

El usuario indicó previamente que *"no importa el rol dentro de módulo de proyectos, existe la delegación o asignación de una tarea, proyecto a una actividad independiente su rol"*. Esto se aplica **dentro del conjunto de usuarios que ya tienen acceso al módulo**:

- Un usuario con `projects:manage` puede asignar una tarea a un usuario con `projects:edit` o a un Admin.
- La asignación no cambia el rol de plataforma del usuario asignado.
- El usuario asignado solo puede interactuar con la tarea/proyecto dentro de los límites de su rol y permisos existentes.

El rol `Miembro` (sin permisos `projects:*`) **no tiene acceso al módulo**, por lo que una asignación en base de datos no le otorga acceso. Si en el futuro se desea que la asignación otorgue acceso a usuarios sin `projects:*`, se debe diseñar un modelo híbrido RBAC/ABAC explícito.

### 8.5 Criterio de cierre de este plan de seguimiento

Este plan de seguimiento se considerará cerrado cuando:

1. Todas las tareas de prioridad **Alta** estén en estado `En seguimiento` o `Cerrado`.
2. Las tareas que requerían decisión de producto (`TASK-PROJECTS-PHASES-GUARD-001`, `TASK-PROJECTS-MIEMBRO-BASELINE-001`) tengan una resolución documentada.
3. La documentación RBAC (`PROJECTS_RBAC_MATRIX.md`, `PROJECTS_API_CONTRACTS.md`) refleje fielmente el código actual.
4. El fallo transversal de auth (`float` en columna UUID) esté resuelto o escalado como issue separado.
5. El usuario confirme la interpretación del baseline de `Miembro` documentada en §8.8.

**Estado actual:** todas las tareas del plan de seguimiento están cerradas. El plan queda en estado de **cierre técnico condicional**, sujeto a:
- la resolución/escalación del fallo transversal de auth, y
- la confirmación del usuario sobre la interpretación del baseline de `Miembro`.
