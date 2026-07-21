# Plan de Calidad — Módulo de Vida Espiritual CCF

> **Objetivo:** operar Vida Espiritual como un módulo propio dentro del monolito modular CCF, con backlog vivo en `docs/ESTADO_VIDA_ESPIRITUAL.md`, contratos claros por capa y gates repetibles para evitar regresiones.

## 1. Regla de trabajo

- No corregir Vida Espiritual con parches locales cuando el origen real vive en permisos, `apiFetch`, `personas.id`, `sede_id` o componentes UI compartidos.
- Cada cambio debe mapearse a un ID estable de `docs/ESTADO_VIDA_ESPIRITUAL.md`.
- Si el bug cruza con CRM, Agenda, Academia o Plataforma, primero fijar owner y contrato antes de tocar dos superficies a la vez.
- Toda mutación de hitos espirituales debe dejar regresión automatizada o smoke explícito.
- El backlog operativo vive en `docs/ESTADO_VIDA_ESPIRITUAL.md`; este plan define el orden correcto de ejecución.

## 2. Fase 0 — Diagnóstico base

**ID:** `SPIRITUAL-FASE0-DIAG`

Comandos:

```bash
cd /root/ccf
cat docs/ESTADO_VIDA_ESPIRITUAL.md
cat docs/VIDA_ESPIRITUAL_API_CONTRACTS.md
cat docs/VIDA_ESPIRITUAL_RBAC_MATRIX.md
grep -nE "SPIRITUAL-" docs/ESTADO_VIDA_ESPIRITUAL.md
./venv/bin/python -m pytest -q -o addopts='' tests/test_api_comprehensive.py::TestSpiritualLifeEndpoints tests/test_api_integration.py::TestSpiritualLifeAPI
```

Criterio de salida:

- El primer fallo real queda clasificado como `contrato API`, `RBAC`, `multi-tenant`, `state sync`, `UI compartida` o `datos`.
- No se toca una vista antes de confirmar si el contrato backend real ya viene roto.

## 3. Fase 1 — Contratos backend y RBAC

**IDs:** `SPIRITUAL-RBAC-001`, `SPIRITUAL-API-001`

Orden:

1. Cambiar guard de `POST /spiritual-life/milestones` de `require_admin` a `spiritual_life:manage`.
2. Agregar guard `spiritual_life:read` al `GET /spiritual-life/milestones/{persona_id}`.
3. Implementar endpoints faltantes: listado, detalle, PATCH, DELETE.
4. Validar Axioma 3 (sede isolation) en todos los endpoints.
5. Actualizar contrato y matriz RBAC si cambia un guard real.

Criterio de salida:

- No quedan endpoints críticos con permisos ambiguos.
- La creación de hitos queda bajo `spiritual_life:manage`.
- La lectura queda bajo `spiritual_life:read`.

## 4. Fase 2 — Normalización de tipos y catálogo

**ID:** `SPIRITUAL-API-003`

Orden:

1. Definir catálogo canónico de tipos de hitos.
2. Implementar validación en schema Pydantic (`MilestoneCreate`, `MilestoneUpdate`).
3. Actualizar frontend para usar el mismo catálogo.
4. Migrar datos legacy si es necesario.

Criterio de salida:

- No se crean hitos con tipos arbitrarios.
- Frontend y backend comparten el mismo catálogo.

## 5. Fase 3 — Frontend y consola administrativa

**IDs:** `SPIRITUAL-FRONT-001`, `SPIRITUAL-FRONT-002`, `SPIRITUAL-FRONT-003`

Orden:

1. Conectar dashboard de Vida Espiritual a datos reales (`/spiritual-life/milestones/{persona_id}`).
2. Corregir rutas internas (`/plataforma/spiritual-life/*`).
3. Implementar creación/edición/eliminación de hitos en consola admin.
4. Conectar consola admin a `/spiritual-life/milestones`.
5. Implementar acciones reales de botones (registrar hito, descargar PDF, validar código).

Criterio de salida:

- El dashboard muestra hitos reales.
- La consola admin permite gestionar hitos.
- No hay datos demo en producción.

## 6. Fase 4 — Tests y calidad

**IDs:** `SPIRITUAL-TEST-001`, `SPIRITUAL-TEST-002`

Comandos mínimos:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' tests/test_spiritual_life_api.py
./venv/bin/python -m pytest -q -o addopts='' tests/test_spiritual_life_rbac.py
```

Tests a crear:

- CRUD completo de milestones.
- RBAC por rol (Admin/Gestor/Editor/Lector/Miembro).
- Axioma 3 (cross-sede devuelve 404).
- Validación de tipos canónicos.
- Integración con timeline y health score.

Smoke frontend:

```bash
cd /root/ccf/frontend
npm run test:e2e:spiritual-life
```

## 7. Fase 5 — QA final y release

**ID:** `SPIRITUAL-FASE5-QA`

Comandos mínimos:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' tests/test_spiritual_life_api.py tests/test_spiritual_life_rbac.py
./venv/bin/python -m pytest -q -o addopts='' tests/test_api_comprehensive.py::TestSpiritualLifeEndpoints tests/test_api_integration.py::TestSpiritualLifeAPI
```

Si se toca frontend:

```bash
cd /root/ccf/frontend
npm run test:e2e:spiritual-life
```

Criterio de salida:

- `docs/ESTADO_VIDA_ESPIRITUAL.md` se actualiza si cambia backlog o estado.
- `docs/VIDA_ESPIRITUAL_API_CONTRACTS.md` y `docs/VIDA_ESPIRITUAL_RBAC_MATRIX.md` se actualizan si cambia el contrato real.
- Ningún cambio de Vida Espiritual se aprueba como “local” si rompe plataforma compartida.

## 8. Backlog ejecutable

| ID | Prioridad | Descripción | Criterio de aceptación |
|---|---|---|---|
| `SPIRITUAL-RBAC-001` | P0 | Cambiar guard de POST a `spiritual_life:manage` | Test de RBAC pasa; Admin/Gestor crean, Editor no |
| `SPIRITUAL-API-001` | P0 | Exponer PUT/PATCH/DELETE de milestones | CRUD completo testeado |
| `SPIRITUAL-API-002` | P0 | Crear endpoint administrativo de listado | Consola admin lista milestones reales |
| `SPIRITUAL-API-003` | P0 | Normalizar `type` a enum/catálogo | Solo tipos canónicos aceptados |
| `SPIRITUAL-FRONT-001` | P1 | Conectar dashboard a datos reales | Dashboard muestra hitos reales del usuario |
| `SPIRITUAL-FRONT-002` | P1 | Implementar CRUD en consola admin | Crear/editar/eliminar hitos desde UI |
| `SPIRITUAL-FRONT-003` | P1 | Corregir rutas internas | Links usan `/plataforma/spiritual-life/*` |
| `SPIRITUAL-TEST-001` | P1 | Crear suite de tests backend | Cobertura de CRUD + RBAC + Axioma 3 |
| `SPIRITUAL-TEST-002` | P2 | Crear tests E2E de frontend | Smoke de navegación y CRUD básico |
| `SPIRITUAL-DOCS-001` | Transversal | Mantener docs sincronizadas | Cada PR toca docs si cambia contrato |
