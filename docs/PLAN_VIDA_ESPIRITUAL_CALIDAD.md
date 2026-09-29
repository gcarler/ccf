# Plan de Calidad — Módulo de Vida Espiritual y Discipulado CCF

**Actualizado:** 2026-09-06 (Auditoría Forense Integral — Certificación 100/100 A+)  
**Estado:** CERRADO Y CERTIFICADO (100/100 A+) — ([`docs/AUDITORIA_FORENSE_VIDA_ESPIRITUAL_2026-09-06.md`](./AUDITORIA_FORENSE_VIDA_ESPIRITUAL_2026-09-06.md))

> **Objetivo:** operar Vida Espiritual y Discipulado como un módulo propio dentro del monolito modular CCF, con backlog vivo en `docs/ESTADO_VIDA_ESPIRITUAL.md`, contratos claros por capa y gates repetibles para evitar regresiones.

## 1. Regla de trabajo

- No corregir Vida Espiritual con parches locales cuando el origen real vive en permisos, `apiFetch`, `personas.id`, `sede_id` o componentes UI compartidos.
- Cada cambio debe mapearse a un ID estable de `docs/ESTADO_VIDA_ESPIRITUAL.md`.
- Si el bug cruza con CRM, Agenda, Academia o Plataforma, primero fijar owner y contrato antes de tocar dos superficies a la vez.
- Toda mutación de hitos espirituales debe dejar regresión automatizada o smoke explícito.
- El backlog operativo vive en `docs/ESTADO_VIDA_ESPIRITUAL.md`; este plan define el orden correcto de ejecución.

---

## 2. Fase 0 — Diagnóstico base ✅ CERRADO

**ID:** `SPIRITUAL-FASE0-DIAG`

Suite canónica (para diagnóstico continuo o verificación de regresiones):

```bash
cd /root/ccf
./venv/bin/python scripts/test_spiritual_life_quality.py
```

Criterio de salida (cumplido al 100%):

- [x] Suite canónica (`scripts/test_spiritual_life_quality.py`) pasa al 100% — **41/41 tests aprobados**.
- [x] Todos los hallazgos clasificados y documentados en `AUDITORIA_FORENSE_VIDA_ESPIRITUAL_2026-09-06.md`.

---

## 3. Fase 1 — Contratos backend y RBAC ✅ CERRADO

**IDs:** `SPIRITUAL-RBAC-001`, `SPIRITUAL-API-001`

Criterio de salida (cumplido al 100%):

- [x] Guard de `POST /spiritual-life/milestones` usa `spiritual_life:manage`.
- [x] Guard de `GET /spiritual-life/milestones/{persona_id}` usa `spiritual_life:read`.
- [x] Endpoints completos: `GET /milestones`, `GET /milestones/{persona_id}`, `POST /milestones`, `GET /milestone/{id}`, `PATCH /milestone/{id}`, `DELETE /milestone/{id}`.
- [x] Axioma 3 (sede isolation) validado en todos los endpoints — BOLA mitigado con HTTP 404 neutro.
- [x] Contrato y matriz RBAC actualizados.

---

## 4. Fase 2 — Normalización de tipos y catálogo ✅ CERRADO

**ID:** `SPIRITUAL-API-003`

Criterio de salida (cumplido al 100%):

- [x] Catálogo canónico definido: `Decision_Fe`, `Bautismo_Aguas`, `Bautismo_Espiritu`, `Persona_Oficial`, `Liderazgo`.
- [x] Validación Pydantic `Field(pattern=...)` en `MilestoneCreate` y `MilestoneUpdate`.
- [x] Frontend y backend comparten el mismo catálogo. Tipos inválidos retornan HTTP 422.

---

## 5. Fase 3 — Frontend y consola administrativa ✅ CERRADO

**IDs:** `SPIRITUAL-FRONT-001`, `SPIRITUAL-FRONT-002`, `SPIRITUAL-FRONT-003`

Criterio de salida (cumplido al 100%):

- [x] Dashboard `spiritual-life/page.tsx` muestra hitos reales vía `apiFetch`.
- [x] **Ruta de Discipulado (`DISCIPULADO_STEPS`) conectada dinámicamente** a los hitos reales del usuario autenticado — 0 datos demo.
- [x] `SpiritualTimelinePanel.tsx` soporta claves UUID (`id`) y `milestone_id` de forma robusta.
- [x] Rutas internas corregidas a `/plataforma/spiritual-life/*`.
- [x] Consola admin `/plataforma/admin/spiritual-life/milestones` conectada a `/admin/milestones`.
- [x] `tsc --noEmit`: 0 errores. ESLint `--max-warnings 0`: 0 warnings. 0 clases Tailwind vetadas. 0 modales prohibidos. 100% `apiFetch`.

---

## 6. Fase 4 — Tests y calidad ✅ CERRADO

**IDs:** `SPIRITUAL-TEST-001`, `SPIRITUAL-TEST-002`

Suite canónica de calidad (gate de regresión):

```bash
cd /root/ccf
./venv/bin/python scripts/test_spiritual_life_quality.py
```

O ejecución directa:

```bash
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_spiritual_life_api.py \
  tests/test_spiritual_life_extended.py \
  tests/test_spiritual_life_gap.py \
  tests/test_admin_milestones_uuid.py
```

Criterio de salida (cumplido al 100%):

- [x] **41 tests de backend aprobados al 100%** en 4 suites canónicas.
  - `test_spiritual_life_api.py`: CRUD, RBAC, catálogo, cross-sede.
  - `test_spiritual_life_extended.py`: helpers unitarios y endpoints extendidos.
  - `test_spiritual_life_gap.py`: gaps de cobertura y casos borde.
  - `test_admin_milestones_uuid.py`: contrato UUID de otorgamiento admin.
- [x] 51 tests de control de acceso frontend (`workspaceAccess.test.ts`) aprobados.

---

## 7. Fase 5 — QA final y Certificación ✅ CERRADO

**ID:** `SPIRITUAL-FASE5-QA`

Gate de calidad continua (regresiones futuras):

```bash
cd /root/ccf
./venv/bin/python scripts/test_spiritual_life_quality.py
cd frontend && npx tsc --noEmit
cd frontend && npx eslint src/app/plataforma/spiritual-life src/components/spiritual --max-warnings 0
```

Criterio de salida (cumplido al 100%):

- [x] `docs/ESTADO_VIDA_ESPIRITUAL.md` actualizado con métricas y veredicto definitivo.
- [x] `docs/VIDA_ESPIRITUAL_API_CONTRACTS.md` y `docs/VIDA_ESPIRITUAL_RBAC_MATRIX.md` actualizados.
- [x] Auditoría forense adversarial independiente emitida — **VICTORY CONFIRMED (100/100 A+)**.
- [x] Dictamen publicado en `docs/AUDITORIA_FORENSE_VIDA_ESPIRITUAL_2026-09-06.md` (616 líneas).

---

## 8. Backlog ejecutable

| ID | Prioridad | Descripción | Estado |
|---|---|---|---|
| `SPIRITUAL-RBAC-001` | P0 | Guard de POST a `spiritual_life:manage` | ✅ Cerrado |
| `SPIRITUAL-API-001` | P0 | Exponer PATCH/DELETE de milestones | ✅ Cerrado |
| `SPIRITUAL-API-002` | P0 | Endpoint admin de listado de milestones | ✅ Cerrado |
| `SPIRITUAL-API-003` | P0 | Normalizar `type` a catálogo canónico | ✅ Cerrado |
| `SPIRITUAL-FRONT-001` | P1 | Dashboard conectado a datos reales | ✅ Cerrado |
| `SPIRITUAL-FRONT-002` | P1 | Ruta de Discipulado dinámica (0 datos demo) | ✅ Cerrado |
| `SPIRITUAL-FRONT-003` | P1 | Rutas internas `/plataforma/spiritual-life/*` | ✅ Cerrado |
| `SPIRITUAL-TEST-001` | P1 | Suite de tests backend (41 tests en 4 archivos) | ✅ Cerrado |
| `SPIRITUAL-TEST-002` | P1 | Tests de control de acceso frontend (51 tests) | ✅ Cerrado |
| `SPIRITUAL-DOCS-001` | Transversal | Certificación forense documental 100/100 A+ | ✅ Cerrado |
