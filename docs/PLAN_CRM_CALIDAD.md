# Plan de Calidad — Modulo de CRM CCF

> **Objetivo:** cerrar CRM como modulo de consolidacion con gates repetibles por capa, sin mezclar problemas de identidad, auth o UI compartida con fixes locales.

## 1. Regla de trabajo

- No corregir CRM con parches visuales si el origen real vive en `personas.id`, `sede_id`, permisos, `apiFetch` o componentes compartidos.
- Cada cambio debe mapearse a un ID estable de `docs/ESTADO_CRM.md`.
- Si un flujo cruza CRM y evangelismo, primero fijar el contrato del bridge antes de cambiar dos UIs a la vez.
- La paginación, filtros y dashboards deben resolverse por contrato backend real, no con carga masiva en frontend.
- Si se toca pipeline, reorder o automations, dejar regresión automatizada.

## 2. Fase 0 — Diagnostico base

**ID:** `CRM-FASE0-DIAG`

Comandos:

```bash
cd /root/ccf
cat docs/ESTADO_CRM.md
grep -nE "PARCIAL-|PEND-" docs/ESTADO_CRM.md
./venv/bin/python scripts/test_crm_quality.py
```

Validación mínima bruta:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_crm_domain.py \
  tests/test_crm_sede_isolation.py \
  tests/test_crm_runtime_security.py
```

Criterio de salida:

- El primer fallo real queda clasificado como `datos`, `contrato API`, `RBAC`, `sede isolation`, `pipeline`, `dashboard` o `frontend state`.
- No se toca UI antes de saber si falla el contrato backend.

## 3. Fase 1 — Personas e identidad base

**IDs:** `PARCIAL-PERSONAS-UI-001`, `PARCIAL-PERSONA-DETAIL-001`

Orden:

1. Validar `GET /api/crm/personas/page` como contrato canónico para volumen alto.
2. Verificar paginación real, orden, filtros y conteo total.
3. Verificar detalle `/personas/{id}` con `timeline`, `donations`, `mentor-candidates` y `mentorship`.
4. Confirmar `404` cross-sede en detalle y subrutas protegidas.
5. Verificar que la UI no dependa de cargar todo el directorio.

Criterio de salida:

- `/plataforma/crm/personas` funciona con dataset alto sin fetch masivo.
- El detalle de persona no rompe por ausencia de subdatos opcionales.
- La identidad canónica sigue siendo `personas.id`.

## 4. Fase 2 — Dashboard CRM

**ID:** `PEND-DASHBOARD-CONTRACT-001`

Orden:

1. Validar shape real de `GET /api/dashboard/crm`.
2. Alinear `cards`, `pipeline_funnel`, `growth_chart`, `conversion_rate`, `filters` y `last_updated` con el frontend.
3. Eliminar supuestos visuales que esperen campos inexistentes.
4. Añadir prueba de contrato si cambia la shape.

Criterio de salida:

- `CRMClient.tsx` consume únicamente campos documentados.
- El contrato del dashboard queda escrito en `docs/CRM_API_CONTRACTS.md`.

## 5. Fase 3 — Pipeline, kanban y automations

**IDs:** `PARCIAL-AUTOMATIONS-001`, `PEND-EXPAND-SMOKE-CRM-001`

Orden:

1. Validar CRUD de pipelines y stages.
2. Validar `PATCH /pipeline/casos/reorder` con atomicidad y scope por sede.
3. Validar kanban y drag-drop sin romper orden persistido.
4. Validar DAG y branching de automations.
5. Correr suites de concurrencia y automations.

Comandos:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_crm_automations_dag.py \
  tests/test_crm_concurrency_adversarial.py
```

Criterio de salida:

- No hay reorder cross-sede ni estados inválidos por concurrencia.
- Automations no aceptan grafos inconsistentes.

## 6. Fase 4 — Bridge CRM con evangelismo

**ID:** `PARCIAL-GROUPS-BRIDGE-001`

Orden:

1. Identificar qué vistas CRM consumen grupos o contratos nacidos en evangelismo.
2. Validar aliases y permisos del lado evangelismo antes de tocar CRM.
3. Confirmar que CRM no reimplemente contratos de grupos en paralelo.

Criterio de salida:

- El owner del bug queda claro.
- CRM solo consume contratos documentados de evangelismo.

## 7. Fase 5 — Smoke frontend CRM

**IDs:** `PARCIAL-FRONTEND-SMOKE-001`, `PEND-FRONTEND-E2E-CRM-001`

Rutas mínimas:

- `/plataforma/crm`
- `/plataforma/crm/personas`
- `/plataforma/crm/personas/[id]`
- `/plataforma/crm/pipeline`

Checks manuales obligatorios hasta tener e2e dedicado:

- consola limpia de `401`, `403`, `404`, `500`
- paginación de personas
- carga del dashboard
- drag/drop o al menos carga del tablero de pipeline

Comandos frontend actuales:

```bash
cd /root/ccf/frontend
npm run test:e2e:crm
npm run test:e2e:crm:deep
```

Regla:

- `test:e2e:crm:deep` usa `webServer` administrado y cubre el detalle de persona; cualquier expansión profunda nueva de CRM debe reutilizar ese patrón compartido.

Criterio de salida:

- Se crea smoke e2e dedicado o queda explícito el checklist manual temporal.

## 8. Fase 6 — QA final y release

**ID:** `CRM-FASE6-QA`

**Estado de ejecucion al 2026-07-18:** cerrado.

Resumen de cierre:

- `scripts/test_crm_quality.py` base: verde
- `scripts/test_crm_quality.py --backend-deep --pipeline --concurrency`: verde (`5/5` suites)
- `npm run test:e2e:crm`: verde (`14 passed`)
- `npm run test:e2e:crm:deep`: verde (`17 passed`)
- cierre estructural aplicado en contrato wiki compartido del pipeline CRM y en suites profundas alineadas al RBAC real

Comandos mínimos:

```bash
cd /root/ccf
./venv/bin/python scripts/test_crm_quality.py
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_crm_domain.py \
  tests/test_crm_sede_isolation.py \
  tests/test_crm_runtime_security.py
```

Si se toca pipeline, dashboard o automations:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_crm_persona_mentorship.py \
  tests/test_crm_resource_bank.py \
  tests/test_crm_automations_dag.py \
  tests/test_crm_concurrency_adversarial.py
```

Criterio de salida:

- `docs/ESTADO_CRM.md` se actualiza si cambia backlog o estado.
- El fix queda en la capa propietaria.
- No se aprueba cambio CRM que rompa plataforma compartida sin documentarlo.

## 9. Fase 7 — Auditoría forense de seguridad y hardening residual (cerrada 2026-07-25)

**ID:** `CRM-FASE7-FORENSE`

**Estado:** cerrado al **100%** el 2026-07-25. Documentado en `errorescrm.md` (raíz del repo, ledger canónico), `docs/ESTADO_CRM.md` §18 y project MEMORY.md.

Resumen de cierre:

- **27 hallazgos** auditados: 18 ✅ CERRADOS + 9 🟢 ya-cubiertos/subsumidos/deferidos + 0 🔴 pendientes.
- **Críticos C-01..C-05** — data breach / mutación cross-tenant — bloqueante, todos cerrados en commit `30037749` (consolidado por fusión física en archivos compartidos) + migración `alembic/canonical_versions/20260725_0001_crm_automation_flows_sede_id.py` para C-04 (sede_id en CrmAutomationFlow). Backfill de flows legacy NULL resultó no-op tras probe directo de prod DB: `SELECT COUNT(*) FROM crm_automation_flows WHERE sede_id IS NULL` = 0 — no hay datos pre-migración.
- **Altos A-01..A-09** — subsumidos por C-04/C-05 en mayoría. A-09 (frontend catches silenciosos) ✅ cerrado commit `136b01ca`. A-01 (`/automation-edges` direct CRUD) 🟢 YA-CUBIERTO: verificado que GET/POST/DELETE scopen via sede del actor en `backend/api/crm/resources.py:644/670/700`, con 3 tests cross-sede de cobertura en `tests/test_crm_sede_isolation.py:667/708/747`.
- **Medios M-01..M-08** — frontend hygiene + tipado CRUD. TODOS cerrados: M-01/M-02 commit `963b8a76` (helpers CRUD retornan UUID), M-03 commit `09249f76` (list_crm_groups scope via membership), M-04 commit `30037749` (response_model drift), M-05 commit `6e84e17d` (AbortController en 13 useEffects / 11 componentes), M-06 commit `b0dd39ac` (validación UUID/slug URL `[id]` 9 componentes), M-07 commit `258b8bcc` (Tailwind hardcoded colors → tokens), M-08 subsumido por C-02 commit `83b1e1da`.
- **Bajos I-01/I-02/I-03** — cosmética/datetime hydratación. I-01 (subsumido: `_serialize_pipeline` patrón dict válido) e I-03 (subsumido: 20 tests IDOR cross-sede existen ya) 🟢. **I-02 widening CERRADO COMPLETO** commits `b9097d5e` + `7033aa97`: 70 campos `datetime` migrados a `AwareDateTime = Annotated[datetime, BeforeValidator(_ensure_utc)]` en `backend/schemas/crm/base.py` (66 campos) + `backend/schemas/crm/resources.py` (3 campos). Cierra el SQLite tz-info loss invariant defense.
- **Funcionalidades F-01/F-02** — log auditoría + endpoint consolidado. F-01 ✅ cerrado commit `8142bf5b` (`patch_categoria`/`del_categoria` audit log bitácora). F-02 🟢 DEFERIDO: verificación de cero callers SDK/CMS para consolidation (no hay demanda actual).

Verificación post-cierre (datos vivos):

```
cd /root/ccf && source venv/bin/activate
python -m pytest -q -o addopts='' \
  tests/test_crm_sede_isolation.py tests/test_crm_rbac_http.py \
  tests/test_crm_domain.py tests/test_crm_runtime_security.py \
  tests/test_crm_automations_dag.py tests/test_crm_persona_mentorship.py \
  tests/test_crm_resource_bank.py tests/test_crm_automations_remediation.py
# → 138 passed

python scripts/test_crm_quality.py
# → RESUMEN 2 passed 0 failed (smoke + RBAC HTTP 33 passed)
```

Criterio de salida:

- ✅ Cero hallazgos 🔴 pendientes en `errorescrm.md`.
- ✅ Cero deuda residual (la única que existía, I-02 widening, fue completada).
- ✅ Smoke CRM canónico `138 passed` + RBAC HTTP `33 passed`.
- ✅ Baseline stash-pop comparison confirma cero regresiones introducidas por I-02 widening.
- ✅ Migración `20260725_0001` aplicada en prod, columna presente, 0 rows legacy NULL.

## 10. Regla de plan formal (regla durable viva desde 2026-07-25)

Toda sesión que labore en módulos CCF debe registrar el plan en el sistema `task` (T1 root + sub-tareas T1.1, T1.2, …) ANTES de codear. Sub-tareas individuales (C-01, M-04, F-01, etc.) son la unidad atómica de seguimiento y deben marcarse `start` antes de trabajarlas y `done` inmediatamente tras cerrarlas. Rationale: ante caída/suspensión de sesión o internet, el próximo agente retoma por donde quedó sin reconstruir contexto desde cero ni pisar trabajo ya hecho. Promovida a project `MEMORY.md` ## Rules como `PLAN DE TRABAJO FORMAL OBLIGATORIO`.

CRM es uno de los **módulos más sensibles de la plataforma CCF** (junto con Evangelismo) por identidad, sede isolation, automations y cruces con evangelismo. Cualquier cambio futuro en CRM debe pasar smoke canónico 138 + RBAC 33 verdes antes de commitear. Esta sensibilidad operativa está documentada en MEMORY.md y §18.4 de ESTADO_CRM.md.
