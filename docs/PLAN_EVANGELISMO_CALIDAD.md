# Plan de Calidad — Módulo de Evangelismo CCF

> **Objetivo:** mantener evangelismo como módulo aislado, con validación repetible y backlog realista.
>
> **Actualizado:** 2026-08-02
> **Complementa:** `docs/ESTADO_EVANGELISMO.md`

## 1. Estado operativo actual

Evangelismo ya tiene cerrados los frentes que dominaron la estabilización inicial:

- contratos backend de eventos
- contratos backend de sesiones
- follow-up
- multiplicación
- smoke canónico backend
- smoke frontend
- cobertura profunda frontend
- búsqueda remota de personas
- migración principal de RBAC a `evangelism:*`

La calidad actual del módulo ya no depende de descubrir qué probar; depende de sostener:

- consistencia de permisos por rol
- deuda estructural de la pantalla de estrategia
- alineación documental continua con el código

## 2. Regla de trabajo

- No mezclar fixes de evangelismo con CRM, proyectos, calendario o CMS salvo contrato cruzado real.
- Toda tarea debe mapearse a una superficie concreta:
  - estrategias
  - grupos
  - sesiones
  - asistencia/follow-up
  - eventos
  - multiplicación
  - reportes/rankings/analytics
  - scanner
- Si se toca backend y frontend en la misma unidad, documentar el contrato que une ambas capas.
- Si cambia permiso real, actualizar primero docs de RBAC y contratos.

## 3. Fase 0 — Diagnóstico base

**ID:** `EVANG-FASE0-DIAG`

Meta: confirmar que el módulo sigue sano antes de abrir una nueva unidad.

Comandos:

```bash
cd /root/ccf
cat docs/ESTADO_EVANGELISMO.md
cat docs/EVANGELISMO_API_CONTRACTS.md
cat docs/EVANGELISMO_RBAC_MATRIX.md
cat docs/EVANGELISMO_QA_CHECKLIST.md
./venv/bin/python scripts/test_evangelism_quality.py
```

Criterio de salida:

- estado canónico leído
- contratos leídos
- matriz RBAC leída
- smoke base en verde o primer fallo real identificado

## 4. Fase 1 — QA runtime de permisos

**ID:** `PARCIAL-RUNTIME-AUTH-001` → cerrada el 2026-07-21

Estado vigente:

- el backend migro toda la superficie administrativa a `evangelism:read/edit/manage`
- las rutas contextuales (`mine`, asistencia por grupo) usan `get_current_user` + ownership/liderazgo, lo cual es intencional
- el wrapper legacy `require_pastor_or_admin_with_sede` (unico rastro `crm:manage`-coincidence en evangelism) fue eliminado el 2026-07-21 al borrar el paquete muerto `backend/api/_evangelism_helpers/`
- la UI alineo su fetch Por Rol con el guard real (ver `EVANGELISMO_RBAC_MATRIX.md` seccion 10)

Cierre formal (2026-07-21):

1. Verificado `docs/EVANGELISMO_RBAC_MATRIX.md` — matriz actualizada a fecha 2026-07-21
2. Smoke + suite amplia verde (smoke 2/2, suite 226/226) — evidencia fresca
3. Grep confirmado: 0 hits de `require_pastor_or_admin` en `backend/api/evangelism*`
4. Documentado cierre del wrapper legacy en seccion 10 de la matriz RBAC
5. Bug secundario corregido: tests usaban campo obsoleto `nombre` en PUT/POST `/grupos` cuando el schema exige `name`

Criterio de salida alcanzado:

- ningún `401/403` estructural inesperado
- toda restricción queda explicada por el guard real
- la UI no dispara requests prohibidas para ese rol/superficie
- modulo evangelism 100% libre del guard historico `crm:manage`-coincidence

## 5. Fase 2 — Descomposición de estrategia

**IDs:** `PARCIAL-STRATEGY-PAGE-001`, `PEND-STRATEGY-DECOMPOSE-001`

**Estado:** ✅ CERRADA el 2026-07-24. Bitácora: `docs/CIERRA_FASE2_EVANGELISMO_2026-07-24.md`.

Cierre formal tras:

- 5 commits atómicos por panel (ses_075c59c7): `470b5d73` `26dc07d7` `fa547d18` `9a89fd06` `96c28863` — `page.tsx` 2580→2005 LOC, paneles en `strategies/[id]/panels/`.
- Cierre de drift de tipos (`51c2a0a0`): `strategyDetailShared.ts` 185→141 LOC, eliminadas 4 interfaces drifted que ninguna caller importaba.
- Cierre de auditoria follow-up (`b346586e`, `09192539`): sede-isolation CRUD/handlers, soft-delete filter en `update_seguimiento`, test falso remediado, badge `tipo` case-insensitive.

Criterio de salida alcanzado:

- menos lógica de negocio embebida en `strategies/[id]/page.tsx` ✓
- fetches centralizados y cancelables ✓
- cero regresiones de layout, permisos o rutas ✓ (smoke 2/2 + suite 226/226 + tsc clean)

## 6. Fase 3 — Validación canónica

**IDs:** `PARCIAL-SMOKE-EVANGELISM-001`, `PEND-EXPAND-SMOKE-EVANGELISM-001`

Estado: cerrado como problema de infraestructura, vigente como disciplina operativa.

Punto de entrada canónico:

```bash
cd /root/ccf
./venv/bin/python scripts/test_evangelism_quality.py
./venv/bin/python scripts/test_evangelism_quality.py --backend-deep
./venv/bin/python scripts/test_evangelism_quality.py --frontend-smoke
./venv/bin/python scripts/test_evangelism_quality.py --frontend-deep
./venv/bin/python scripts/test_evangelism_quality.py --expanded
```

Regla:

- el script raíz es la entrada oficial del módulo
- no depender de memoria operativa para elegir suites

## 7. Fase 4 — Cierre por unidad

**ID:** `EVANG-FASE4-CIERRE`

Antes de cerrar una unidad:

1. correr el smoke relevante
2. verificar rutas impactadas
3. confirmar que la consola no tenga errores nuevos
4. actualizar docs si cambió:
   - backlog
   - contrato
   - guard real
   - lectura por rol

Criterio de salida:

- cambio validado en la capa tocada
- documentación alineada con el código real
- commit coherente por unidad

## 8. Backlog vivo

### Activo

- (vacío tras cierre de Fase 2 el 2026-07-24 — todas las fases del plan están cerradas o son disciplina operativa)

### Disciplina operativa continua (no reactivar como backlog)

- Vigilancia de pobreza estructural en `strategies/[id]/page.tsx`: si vuelve a crecer sobre 2005 LOC o re-concentra fetches, extraer hooks/paneles adicionales. La lectura por rol queda alineada al guard real (ver RBAC_MATRIX seccion 3).

### Cerrado — `NUEVO-FOLLOWUP-PENDING-FIXES` (7 brechas, 2026-07-24 a 2026-07-29)

Las 7 brechas de calidad follow-up que requerian migracion DB agrupada estan **cerradas en commits**. No reabrir salvo nueva evidencia.

- **#3 endpoint DELETE via API (soft-delete)** — cerrada `b1f32287` "feat(evangelism): endpoint DELETE /follow-up/{id} (soft-delete) (Axioma 3)". Endpoint `DELETE /follow-up/{seguimiento_id}` con `require_evangelism_manage`, retorna `{"ok": True}`.
- **#4 default `estado_completado=True→False`** — cerrada `75ce8544` "fix(evangelism): seguimiento integrity (default pendiente, CHECK enum, indices FK)". Migration `alembic/canonical_versions/20260724_0001_seguimiento_integrity.py`.
- **#5 enum CHECK en `tipo`** — cerrada `75ce8544` (misma migracion). `TipoSeguimientoEnum` con CHECK constraint.
- **#6 indices FK en seguimiento** — cerrada `75ce8544` (misma migracion). Indices en FKs `asistencia_id`/`lider_id` aceleran joins `seguimiento → asistencia → sesion → grupo → sede`.
- **#7 `extra="forbid"` en `RegistroSeguimientoResponse`** — cerrada `c7458733` "fix(evangelism): RegistroSeguimientoResponse con extra=forbid".
- **#10 UI scoping del panel de seguimientos por estrategia** — cerrada `530d6892` "fix(evangelism): scoping UI del panel de seguimientos por estrategia (brecha #10)". Panel en `strategies/[id]/page.tsx` ahora filtra seguimientos por estrategia.
- **#12 tests cross-sede + update-sobre-soft-deleted** — cerrada `1c26c739` "test(evangelism): regression tests cross-sede + soft-deleted follow-up". 6 tests en `tests/test_evangelism_followup_sede_regression.py`.

**Suite evangelismo end-to-end re-ejecutada 2026-08-02:** `1177 passed, 0 failed, 2 xfailed, 1 xpassed` en 12:33 (1180 colectados). Backlog activo del modulo: vacio.

### Adeuda tecnica eliminada (sesion `ses_0442c5c6effeUqcqRILFB1Augx`, commit `f75753c7`)

- 5 funciones helper muertas duplicadas eliminadas de `evangelism_shared.py` (~128 LOC): `_channel_label`, `_persona_matches_segment`, `_resolve_campaign_personas`, `_serialize_message_group`, `_serialize_crm_task` — copias canonicas en `crm/_shared.py` y `evangelism_main/main_utils.py`.
- `backend/services/evangelism_projection.py` eliminado (21 LOC, wrapper muerto re-exportando `calcular_sesiones`, 0% cobertura, sin importadores).
- 117 tests nuevos en `tests/test_evangelism_coverage_gaps.py`: `events_main.py` 76→95%, `main_estrategias.py` 83→90%, `grupos_main.py` 87→93%.
- 13 artefactos `*,cover` eliminados de subdirectorios evangelism. 2 directorios backup no trackeados eliminados.

### Cerrado y no reabrir salvo nueva evidencia

- `PARCIAL-RUNTIME-AUTH-001` — cerrado el 2026-07-21 (Fase 1 RBAC radical + wrapper legacy eliminado)
- `PARCIAL-STRATEGY-PAGE-001` — cerrado el 2026-07-24 (Fase 2: paneles extraídos + drift eliminado)
- `PEND-STRATEGY-DECOMPOSE-001` — cerrado el 2026-07-24 (Fase 2: page consume hooks canonicos)
- `NUEVO-DRIFT-TYPES-001` — cerrado el 2026-07-24 (`51c2a0a0`)
- `NUEVO-FOLLOWUP-SEDE-001` — cerrado el 2026-07-24 (`b346586e`)
- `NUEVO-FOLLOWUP-TEST-BADGE-001` — cerrado el 2026-07-24 (`09192539`)
- `PEND-PERSONAS-SEARCH-001`
- `PEND-RBAC-EVANGELISM-001`
- `PARCIAL-EVENTS-001`
- `PARCIAL-MULTIPLICATION-001`
- `PARCIAL-FOLLOWUP-001`
- `PEND-EVENTS-CONTRACT-001`
- `PEND-SESSIONS-CONTRACT-001`
- `PEND-FRONTEND-E2E-EVANGELISM-001`
- `PEND-FRONTEND-E2E-EVANGELISM-EVENTS-SCANNER-001`
- `PARCIAL-SMOKE-EVANGELISM-001`
- `PEND-EXPAND-SMOKE-EVANGELISM-001`

## 9. Relación con otros documentos

Usar en este orden:

1. `docs/ESTADO_EVANGELISMO.md`
2. `docs/PLAN_DE_TRABAJO_EVANGELISMO.md`
3. `docs/EVANGELISMO_RBAC_MATRIX.md`
4. `docs/EVANGELISMO_API_CONTRACTS.md`
5. `docs/EVANGELISMO_QA_CHECKLIST.md`

Este archivo no reemplaza el estado canónico. Lo traduce a plan de ejecución y control de calidad.
