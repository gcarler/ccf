# Plan de Calidad — Módulo de Evangelismo CCF

> **Objetivo:** mantener evangelismo como módulo aislado, con validación repetible y backlog realista.
>
> **Actualizado:** 2026-07-21
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
- `NUEVO-FOLLOWUP-PENDING-FIXES` (cola de calidad): 7 brechas menores pendientes identificadas en auditoria follow-up que requieren migracion DB o cambio con masaje (ver `notes.md` ses_06be8d107ffe): #4 default `estado_completado=True→False`, #5 enum CHECK en `tipo`, #6 indices FK, #7 `extra="forbid"` en `RegistroSeguimientoResponse`, #10 UI scoping por estrategia del panel de seguimiento, #12 tests cross-sede/update-sobre-soft-deleted, #3 endpoint DELETE via API. No forman backlog activo — ejecutar en proxima sesión con migración agrupada.

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
