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
