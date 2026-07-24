# Bitácora de Cierre — Fase 2 Descomposición de Estrategia (Evangelismo)

> **Creada:** 2026-07-24
> **Sesión superior:** `ses_06be8d107ffeg35tuwvjtFFq3c`
> **Plan de referencia:** `docs/PLAN_EVANGELISMO_CALIDAD.md` §5 Fase 2 (`PARCIAL-STRATEGY-PAGE-001`, `PEND-STRATEGY-DECOMPOSE-001`)
> **IDs estables afectados:** `PARCIAL-STRATEGY-PAGE-001`, `PEND-STRATEGY-DECOMPOSE-001`
> **Estado previo (entrada):** `strategies/[id]/page.tsx` con 2580 LOC monolítico + panel-extraction pendiente + drift de tipos `strategyDetailShared.ts` ↔ `types.ts`.
> **Estado final (salida):** `page.tsx` 2005 LOC; 5 paneles extraídos con commit atómico por panel; drift de tipos eliminado; smoke + suite 226/226 + tsc clean.

---

## 1. Contexto de retoma

La Fase 1 (RBAC radical + eliminación del wrapper legacy) se cerró el 2026-07-21 con commit `339539e9` y bitácora propia `CIERRA_FASE1_RBAC_2026-07-21.md`. Quedaba pendiente la **Fase 2 — descomposición de `strategies/[id]/page.tsx`** por ser el monolito más sensible del módulo: 2580 LOC que concentraban fetches, mutations, búsqueda remota, estados de attendance y rendering.

La memoria inter-sesión (`MEMORY-evangelism-rbac.md` ses_075c59c7) ya había cerrado **panel-extraction física** entre el 2026-07-22 con 5 commits atómicos, pero la bitácora de cierre nunca se escribió. Este documento rellena ese hueco documental y captura el último eslabón pendiente — limpieza del drift de tipos entre `strategyDetailShared.ts` y `types.ts` (`51c2a0a0`).

## 2. Hallazgos operacionales

1. **Reducción de monolito:** `strategies/[id]/page.tsx` pasó de 2580 LOC a 2005 LOC (-22.3%) mediante extracción de paneles en orden de menor-riesgo-primero.
2. **Disciplina de paneles:** cada panel es _controlled presentational_ — recibe props + callbacks desde `page.tsx`. State y fetches permanecen en la página. La única excepción documentada es el `AttendanceDrawer`, donde el `useRemotePersonaSearch` auto-contenido vive dentro del drawer (propiedad drawer-internal lifecycle).
3. **Drift de tipos identificado:** `strategyDetailShared.ts` duplicaba 4 interfaces (`Strategy`, `StrategyGroup`, `SessionRow`, `HabilitacionEstado`) drifted con sus homónimas en `types.ts`. Mapeo de consumo:
   - `types.ts` era canónica y usada por todos los paneles + el hook `useStrategyDetail.ts`.
   - `strategyDetailShared.ts` seguía re-declarandolas haunted pero **ningún consumidor las importaba desde ahí** — eran dead drift.
   - Los únicos símbolos vivos en `strategyDetailShared.ts` eran `CustomRole`, `FollowUpRecord`, `AttendancePersona`, `SearchablePersona`, `AttendanceSaveResult`, `TabId`, las 7 constants y las 5 funciones utilitarias — todos únicos (no present en `types.ts`).

## 3. Acciones tomadas (baseline verde pre + validación post)

### Baseline previo (2026-07-24)

```
./venv/bin/python scripts/test_evangelism_quality.py
RESUMEN: 2 passed, 0 failed, 2 total suites
(19+1xfailed + 18+1xfailed = 37 passed)

./venv/bin/python -m pytest -q -o addopts= --no-cov tests/test_evangelism_module_coverage.py
226 passed in 157.88s

npx tsc --noEmit (filtrado evangelism/) → 0 errores
```

### Commits atómicos por panel (sesión previa ses_075c59c7)

| Commit | Archivo extraído | LOC movido |
|---|---|---:|
| `470b5d73` | `panels/StrategyOverviewForm.tsx` | 17 props (L1414-1514) |
| `26dc07d7` | `panels/StrategyHeader.tsx` | 5 props (L988-1020) |
| `fa547d18` | `panels/CustomRolesPanel.tsx` | L→panel |
| `9a89fd06` | `panels/GroupCreationDrawer.tsx` | (incluye `RoleSearchPersona` type) |
| `96c28863` | `panels/AttendanceDrawer.tsx` | (mayor — `useRemotePersonaSearch` movido dentro) |

### Commit de cierre de drift de tipos (2026-07-24, sesión actual)

| Commit | Archivo | Cambio |
|---|---|---:|
| `51c2a0a0` | `strategyDetailShared.ts` | -46 / +2 LOC (24% red, 185→141) |

Acciones específicas del commit `51c2a0a0`:
- Elimina 4 interfaces drifted: `Strategy`, `StrategyGroup`, `SessionRow`, `HabilitacionEstado`.
- Reemplaza tipo hackish `typeof Users` por `LucideIcon` idiomático en la constante `TABS`.
- Fusiona el import `type { Users } from 'lucide-react'` con el bloque principal (ya no se necesita un import aparte).

### Validación post-cierre

```
npx tsc --noEmit  → 16 errores globales (todos en design/*.test.tsx y
                          ThemeToggle.test.tsx — ajenos a evangelismo);
                          0 errores en evangelismo/
git diff --check   → clean
```

Smoke + suite amplia ya verificados en baseline previo y sin tocar backend: no se re-corren (sin cambio de runtime).

## 4. Estado final con métricas antes/después

| Métrica | Antes (entrada Fase 2) | Después (cierre Fase 2) |
|---|---:|---:|
| `strategies/[id]/page.tsx` LOC | 2580 | 2005 |
| Paneles extraídos | 0 | 5 |
| Archivos en `strategies/[id]/` | 4 | 9 (page, useStrategyDetail, strategyDetailShared, types + 5 panels) |
| `strategyDetailShared.ts` LOC | 185 | 141 |
| Drift interfaces Strategy/StrategyGroup/SessionRow | ✗ | ✓ eliminado |
| Smoke base 2/2 | ✓ | ✓ |
| Suite amplia 226/226 | ✓ | ✓ |
| `npx tsc --noEmit` (evangelism) | 0 errores | 0 errores |

## 5. Actualización documental

- `docs/ESTADO_EVANGELISMO.md` §11: mover `PARCIAL-STRATEGY-PAGE-001` y `PEND-STRATEGY-DECOMPOSE-001` de "disciplina operativa continua" (§8 del plan) → "Cerrado y no reabrir salvo nueva evidencia", combinados en una sola entrada de cierre Fase 2 con fecha 2026-07-24.
- `docs/PLAN_EVANGELISMO_CALIDAD.md` §5 Fase 2 y §8 Backlog vivo: marcar Fase 2 como **CERRADA** (2026-07-24) y limpiar las dos entradas de disciplina operativa. El backlog activo sigue vacío.
- Esta bitácora queda como rastro atómico de cierre.

## 6. Plan operativo de la próxima fase

Con la Fase 1 (RBAC) y Fase 2 (descomposición) cerradas, los próximos frentes abiertos del módulo son puramente disciplinarios:

- **Fase 3 (validación canónica)** — `PARCIAL-SMOKE-EVANGELISM-001`, `PEND-EXPAND-SMOKE-EVANGELISM-001`: ya cerrados infrastructuralmente el 2026-07-16; vigilar que el script canónico `scripts/test_evangelism_quality.py` permanezca como la entrada oficial. Regla: el script raíz es la única puertas; no inventar suites ad-hoc.

- **Fase 4 (cierre por unidad)** — disciplina: cada cambio futuro debe usar el checklist de `EVANGELISMO_QA_CHECKLIST.md`.

- **Deuda técnica residual opcional:** la page sigue en 2005 LOC; hay duplicación hooks-`page` (el hook `useCustomRoles` / `useAttendanceDrawer` están extraídos pero `page.tsx` mantiene implementaciones inline equivalentes). Ahora que los 5 paneles están aislados y los tipos consolidados, un Fase 3-opcional podría adoptar los hooks y eliminar los duplicados inline sin tocar contratos de panel. No se planifica como backlog activo — solo se ejecuta si la page vuelve a crecer.

Comandos de validación para futuras sesiones:

```bash
cd /root/ccf
./venv/bin/python scripts/test_evangelism_quality.py
./venv/bin/python -m pytest -q -o addopts= --no-cov tests/test_evangelism_module_coverage.py
cd frontend && npx tsc --noEmit 2>&1 | grep evangelism/ | wc -l   # debe ser 0
```

## 7. Notas para el siguiente agente

- **No revertir ni mezclar el commit `51c2a0a0`.** Es atomic y surgical, contiene solo `strategyDetailShared.ts`. Otros archivos modified en el tree (`academy.py`, `test_academy_quality.py`) son trabajo ajeno en curso — NO tocar.
- **ESTADO_EVANGELISMO.md §11** ya dice "100% del plan maestro" desde antes de este cierre; actualizar en consecuencia para reflejar el cierre formal de Fase 2 (no dejarlo como "disciplina operativa").
- **`types.ts` es la fuente canónica de tipos.** Cualquier nuevo tipo de dominio evangelismo vive ahí. `strategyDetailShared.ts` queda relegado a UI constants + helpers + interfaces puramente presentacionales (`AttendancePersona`, `SearchablePersona`, `CustomRole`, `FollowUpRecord`, `AttendanceSaveResult`, `TabId`).
- **`File:Glass`**ával de unit tests frontend e2e cubre `strategies/[id]/`: las suites `frontend/tests/e2e/evangelism/` siguen válidas para detectar regresiones visuales.
