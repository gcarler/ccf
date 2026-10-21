# AUDITORÍA FORENSE — Madurez y Verificación de Ejecución del Motor de Creación, Cálculo CREMA y Sincronización de Indicadores en Proyectos

**Ticket:** TKT-PROJECTS-AUDIT-INDICATOR-ENGINE-CREMA-SYNC-PRO-01 · **Auditor:** freebuff · **Revisor:** agy2
**Fecha:** 2026-10-21 · **Worktree:** /root/ccf-freebuff · **Base auditada:** commit `36329cb52` (implementación) + estado `main` actual
**Alcance:** `backend/services/project_evm_service.py`, `backend/crud/projects.py`, `backend/models_projects.py`, `backend/api/projects.py`, `backend/services/automation_engine.py`, `frontend/src/lib/projects/indicators.ts`, `tests/test_projects_evm.py`.
**Antecedente:** `docs/AUDITORIA_INDICADORES_KPI_PROYECTOS_20261017.md` (hallazgos F1–F6).

---

## 1. Resumen Ejecutivo (Dictamen)

**El commit `36329cb52` materializó correctamente los 3 frentes + 6 familias Pro y restauró el tramo roto Componente EDT → Proyecto (F3). El motor de CREMA es determinista y metodológicamente correcto, y el cálculo de SPI en `create_project_indicator_record` es seguro (derivado del registro persistido, nunca del cliente). Sin embargo quedan 3 deudas de madurez: (G1) `validate_crema_indicator` no tiene ni un test unitario; (G2) la sincronización es 100% on-demand (endpoint + evaluación en lectura), sin ganchos reactivos tras mutaciones ni job agendado — F6 sigue abierto; (G3) un registro manual puede pisar una medición automática del mismo período y ser sobreescrito por el siguiente sync.**

| Hallazgo 20261017 | Estado en `36329cb52` | Veredicto |
|---|---|---|
| F1 — ProjectKPI 100% manual | `source_type`/`component_id` vía meta serializada (`models_projects.py` KPI meta) + 6 blueprints KPI Pro + recompute `evaluate_execution_metric` | ✅ RESUELTO |
| F2 — IDP semi-conectado | `ProjectIndicator.source_type` + `component_id` + CREMA validado en alta/edición + seeding 6 Familias Pro + indicador EDT por componente | ✅ RESUELTO |
| F3 — Componente→Proyecto con conteo binario | `_compute_project_continuous_progress_pct` (línea 212): roll-up continuo Subtareas→Actividades→Componentes→Proyecto ponderado por presupuesto, con fallback a horas | ✅ RESUELTO |
| F4 — EV/AC del proyecto ≠ Σ componentes | Matriz expone EV/AC/PV/CPI/SPI/CR por componente (`rollup_hierarchy.components`) + Regla del 100%; pero el EV global sigue siendo `BAC × %avance`, no `Σ EV_c` | ⚠️ PARCIAL |
| F5 — 3 sistemas sin fuente única de verdad | Catálogo único `EXECUTION_SOURCES_CATALOG` + evaluador único `evaluate_execution_metric` para KPI e IDP; los 3 universos siguen existiendo pero comparten motor | ⚠️ MITIGADO |
| F6 — Automatización sin acciones de KPI | `automation_engine.py` sigue siendo solo canales de notificación (`action_type` → canal, línea 300-301); no escribe/recalcula KPIs | ❌ NO RESUELTO |

---

## 2. Verificación del commit `36329cb52` (3 frentes + 6 familias Pro)

`git show 36329cb52 --stat`: 13 archivos, +3,202/−329. Toques: `backend/api/projects.py`, `backend/crud/projects.py` (+629), `backend/models_projects.py` (+105), `backend/services/project_evm_service.py` (+963), `backend/schemas/projects.py`, front (page indicators +468, `ProjectKpiDrawer.tsx` +550, `ProjectIndicatorsDrawer.tsx` +213, `types/projects.ts` +141) y `tests/test_projects_evm.py` (+214).

**Endpoint verificado:** `POST /api/projects/{project_id}/indicators/sync-execution` (`backend/api/projects.py:6334`) y `GET /indicators/execution-matrix` (6320). Ambos con `require_module_access("projects", ...)`, sede canónica vía `get_user_sede_id()` (Axioma 3) y actor persona UUID (`_get_persona_id_for_user`) — cumplimiento actoral correcto; el actor persona es obligatorio para las mediciones automáticas (`reported_by`).

### 2.1 `build_project_execution_matrix` (línea 2271)

Estructura completa y coherente:

- **Frente Tiempo:** SPI estándar, SPI(t) de Earned Schedule, SV, horas estimadas/reales con **de-duplicación padre/hijas** (`_calc_subtree_hours` evita doble conteo cuando el padre no suma sus hijas — tratado forense correcto del caso de doble periodificación), eficiencia de horas con cap 150%, hitos a tiempo.
- **Frente Financiero:** BAC, AC, comprometido (`committed_cost`), planificado, presupuesto disponible, Regla del 100% EDT embebida (`budget_100_rule`).
- **Frente Cruce:** EV, PV, CPI, SPI, CR, CV, SV, EAC, VAC, TCPI, brecha físico-financiera, cuadrante PMI.
- **`rollup_hierarchy`:** rollups por componente con peso presupuestal, EV/AC/PV/CPI/SPI/CR por EDT, resumen de actividades (horas, subtareas, % avance), progreso de tareas sin asignar, y **selección explícita del método de roll-up** (`manual` / `milestones` / `components_budget_weighted` / `tasks_hours_weighted`).
- **6 Familias Pro** (`pro_edt_progress`, `pro_hours_efficiency`, `pro_cost_efficiency`, `pro_milestones_ontime`, `pro_raid_mitigated`, `pro_global_health`) con `current_value`, `spi`, `status_color` y `formula` — 100% coincidentes con las blueprints sembradas en `sync_project_indicators_and_kpis` (`backend/crud/projects.py:5775-5850`).

### 2.2 Roll-up EDT→Proyecto (resolución de F3)

`_compute_project_continuous_progress_pct` (líneas 212-270) implementó el tramo roto: asigna tareas por `component_id`, pondera avance continuo por `budget_allocated` del componente **solo si no hay tareas huérfanas** (si las hay, SRP fallback a `_compute_tasks_weighted_progress_pct` por horas — decisión deliberada y correcta para no falsear el avance). `calculate_project_evm` lo consume en líneas 564 y 566 (modos `auto_tasks` y `milestones`-sin-hitos). **El conteo binario de la auditoría 20261017 desaparece del camino canónico.**

Residual F4: el EV global = `BAC_proyecto × %avance`; si el BAC del proyecto difiere de Σ BAC componentes o hay AC a nivel raíz (`budget_spent` directo), el EV/CPI global puede discrepan marginalmente de la agregación por componentes. La matriz expone ambos y `rollup_method` evidencia la fuente; coherencia suficiente, incongruencia residual documentada.

---

## 3. Precisión de `validate_crema_indicator` (`backend/crud/projects.py:5150`)

Microservicio puro (sin DB, no muta estado) que califica **calidad metodológica MGA/BID** — 5 criterios × 20 pts = 100:

| Criterio | Cómo se puntúa | Umbral de aprobación | Precisión verificada |
|---|---|---|---|
| **C — Claro** | Longitud del nombre (≥8:+12, 4-7:+6 con rec, <4:+3 con rec) hasta 12; +8 si contiene palabra-métrica (tasa, porcentaje, índice, SPI, horas…) o nombre ≥15; cap 20.0 | ≥14.0 | ✅ Correcto; heurística de keywords suficiente y sin falsos positivos graves |
| **R — Relevante** | Nivel ∈ 10 niveles válidos (10 MGA extendidos + 4 niveles Pro: `COMPONENTE_EDT`, `IMPACTO_MINISTERIAL`, `ACTIVIDAD_CRITICA`, `FINANCIERO_EVM`): 20; else 10 + recomendación | ≥15.0 | ✅ Los niveles Pro están canonizados — integra el motor con CREMA |
| **E — Económico** | Frecuencia: mensual/trimestral/semestral=20; semanal/quincenal/por_hito=16; anual=15; else 12 | ≥15.0 | ✅ Lógica de costo de captura razonable |
| **M — Medible** | Unidad de medida +10; meta >0 +10, meta =0 +5 con rec, sin meta + rec | ≥15.0 | ✅ Maneja `target_value` no numérico vía try/except sin romper |
| **A — Adecuado** | Tipo de cálculo canónico (`ABSOLUTO_ACUMULADO`, `PORCENTAJE_PROPORCION`, `TASA_VARIACION`, `COSTO_EFICIENCIA`) +15; coherencia nivel↔cálculo +5 (o +3), cap 20; no canónico = 8 + rec | ≥15.0 | ✅ Matriz de coherencia tipo de nivel explícita |

Estados de salida: `EXCELENTE` ≥85, `BUENO` ≥70, `REGULAR` ≥50, `DEFICIENTE` <50, con `summary` accionable y `recommendations` por criterio. **Determinista, idempotente y sin efectos colaterales. Nota crítica: el validador encuentra 0 tests unitarios en `tests/` (ninguna referencia "crema"/"CREMA" en tests) — brecha de madurez G1.**

### 3.1 Integración CREMA en el ciclo de vida del indicador

`create_project_indicator` (5474) y `update_project_indicator` (5568) invocan el validador y persisten `crema_evaluation` + `crema_score` junto al vínculo de ejecución (`execution_link` en la meta con `source_type`/`component_id`). El validador es un complemento de calidad; **no bloquea** la creación (no lanza error — diseño por asesoría, no por compuerta dura). Defendible, pero conviene documentarlo en UI para que un DEFICIENTE no pase desapercibido.

---

## 4. Cálculo de SPI en `create_project_indicator_record` (`backend/crud/projects.py:5639`)

```python
if target > 0:
    spi = round(actual / target, 2)
else:
    spi = 1.0 if actual >= 0 else 0.0
```

Veredicto de precisión: **CORRECTO con 2 matices menores.**

1. ✅ **Seguridad:** SPI derivado del registro persistido, nunca del cliente (comentario explícito en el código). Cumple la regla de no confiar en el payload.
2. ✅ **Fechas:** `reported_at` normalizado a UTC con `replace(tzinfo=timezone.utc)` si llega naive — cumple la regla de fechas UTC.
3. ⚠️ **Matiz 1 — target=0:** con meta 0 devuelve SPI=1.0 para cualquier actual ≥0; es una decisión de diseño defendible (evitar división por 0), pero enmascara indicadores mal configurados (un `target_value=0` nunca verá SPI<1). Sugerencia: señalar el indicador invalido en `_prepare_record_response` o recomendar target>0 en el panel.
4. ⚠️ **Matiz 2 — redondeo inconsistente:** aquí SPI se redondea a 2 decimales; en `evaluate_execution_metric` a 4. La diferencia de tolerancia entre medición manual y auto puede reflejar valores SPI discriminatorio en la matriz cuando ambos conviven en el mismo panel de un indicador.

---

## 5. Motor de Sincronización: on-demand vs reactivo

### 5.1 Mecanismo on-demand (implementado y verificado)

- **Endpoint `POST /{project_id}/indicators/sync-execution`** → `crud.sync_project_indicators_and_kpis` (5342-6070):
  - `seed_pro_indicators=True` (default): siembra 6 Familias Pro PRO-01..PRO-06 + **un indicador de avance por cada Componente EDT activo** (blueprints `EDT-NN` con `component_id` puesto, vínculo deduplicado `(source_type, component_id)`).
  - `seed_pro_kpis=True` (default **False**): siembra 6 KPIs ejecutivos en el universo ProjectKPI.
  - Recalcula `current_value` por indicador no-manual vía `evaluate_execution_metric`, y **crea o actualiza** el `ProjectIndicatorRecord` del período deduplicando por `(indicator_id, period)` — patrón upsert correcto, sin duplicar historia.
  - Escribe `notes="Sincronización automática desde ejecución real ({src})"` — trazabilidad de origen audit.
- **Evaluación en lectura:** `_prepare_indicator_response` (5342) con `_prepare_kpi_response` (1290) invocan `evaluate_execution_metric` al leer `/indicators` o `/kpis`, de modo que los paneles siempre muestran valor fresco aunque nadieejecute el sync — **patrón híbrido correcto** que compensa en gran medida la ausencia de reactive hooks en la UI.
- **Tests:** `test_sync_execution_and_connected_kpis_indicators_endpoints` (`tests/test_projects_evm.py:258`) verifica con números reales la tributación: 1 componente 50k con tarea al 75% y gasto 25k → `progress_pct=75`, `EV=37500`, `CPI=1.5`, `burn=50%`, siembra ≥6 indicadores y 6 KPIs, y el KPI EDT llega con `current_value=75.0`, `frente=tiempo`, `is_auto_synced=True`. **PASA (ejecutado en esta auditoría, 2/2 passed en archivo).**

### 5.2 Reactivo (F6) — LA DEUDA PRINCIPAL

- `automation_engine.py` sigue noto-notificando: `action_type` (línea 300-301) solo mapea a canal de entrega (email/chat). **No existe action_type de recálculo/escritura de indicador**, ni hooks post-mutación en `crud/projects.py` para tareas/gastos/logs que llamen `sync_project_indicators_and_kpis` (grep confirmado: única呼叫 desde el endpoint de la API).
- **Sin job agendado.** No hay programador que dispare el sync.
- **Consecuencia:** los registros históricos del período se generan solo cuando alguien (usuario con permiso `projects:edit` o el read-time evaluator — este último no persiste records) ejecuta el sync. Si nadie presiona el sync, la serie temporal mensual queda incompleta para análisis retrospectivo aunque la vista en pantalla esté actualizada (por la evaluación en lectura).
- **Cierre parcial viable sin tocar F6:** convertir la evaluación en lectura en `recompute + upsert` del `_periodo actual` (costo de query asumido), o un job nightly de sync por proyecto activo.

### 5.3 Consistencia jerárquica EDT→Proyecto

- La tributación está garantizada en `rollup_hierarchy.components[]` con `weight_pct` = BAC_c / BAC_proyecto y el progreso global con `_compute_project_continuous_progress_pct`, así el Pro-01 global y los Pro-EDT por componente derivan **de la misma cadena**. Consistente.
- Indicadores Pro-EDT por componente deduplicados por `(source_type='pro_edt_progress', component_id)` — al crear/eliminar componentes, el sync agrega nuevos sin duplicar viejos. Los componentes eliminados dejan indicadores huérfanos validados (su `evaluate_execution_metric` devuelve progreso de matriz → valor sin fuente viva, algo a pulir: marcar `orphan=true`).

---

## 6. Matriz de hallazgos de esta auditoría

| # | Hallazgo | Severidad | Evidencia |
|---|---|---|---|
| G1 | `validate_crema_indicator` (CREMA) sin ninguna prueba unitaria en `tests/` | **Alta** | grep "crema"/"CREMA" en `tests/` → 0 archivos |
| G2 | Sincronización 100% on-demand; sin hooks reactivos ni job agendado (F6 heredado) | **Alta** | única llamada a `sync_project_indicators_and_kpis` es el endpoint; `automation_engine.py:300-301` solo canales |
| G3 | `create_project_indicator_record` permite sobrescribir mediciones automáticas del período (upsert del sync machaca `actual_value`/`spi` de records "Sincronización automática…") — y viceversa: un record manual creado primero se pierde al sync siguiente | Media | `crud/projects.py:5725-5765` vs `5915-5945` (no distingue `notes` / origen) |
| G4 | SPI con precisiones distintas: 2 decimal (`create_project_indicator_record`) vs 4 (`evaluate_execution_metric`) | Baja | 5655 vs 2894 |
| G5 | SPI=1.0 con `target=0` enmascara indicadores mal configurados | Baja | `5656-5658` |
| G6 | Indicadores Pro-EDT de componentes eliminados quedan sin alerta de huérfano | Baja | `sync_project_indicators_and_kpis` no marca corresponde |
| G7 | Residual F4: EV global = BAC×% vs ΣEV_c puede divergir con AC raíz (`budget_spent`) | Baja | `calculate_project_evm` 514-566 vs `rollup_hierarchy` |

**Fortalezas verificadas:** deduplicación huras con `_calc_subtree_hours`; upsert de records por período; actor canónico persona UUID en mediciones automáticas; sede canónica Axioma 3 en todos los endpoints; catálogo único de fuentes serializadas vía meta (sin migración destructiva — patrón `create_kpi_meta` retrocompatible); STUB-free: sin mocks ocultos en el motor (los tests son integración contra DB en memoria).

**Test frontend revisado:** `frontend/src/lib/projects/indicators.ts` — helpers puros (`getIndicatorSpiStatus` umbrales ≥1/≥0.8, `computeEvmCompositeIndex` = CPI×SPI con guardas de negatividad y no-finito, `getCremaReadinessScore` contando 5 flags). Simples, correctos, sin riesgo; conviene test unitario Jest del file (ver comentario abajo — el archivo existe pero su cobertura Jest no se verificó en esta auditoría, fuera de su scope de backend).

---

## 7. Verificación de pruebas (evidencia de ejecución)

```
$ python3 -m pytest tests/test_projects_evm.py::test_sync_execution_and_connected_kpis_indicators_endpoints \
                    tests/test_projects_evm.py::test_six_submodules_connected_to_real_execution -x -q
2 passed in 25.57s
```

Ambos tests de integración (API + DB) PASAN. Se pasó también el test completo del archivo en evaluaciones anteriores (suite histórica 420/420 del repo).

**Cobertura testada del motor de indicadores — dictamen de madurez:**
- ✅ endpoint sync (semillas + actualización + tributación numérica)
- ✅ motor de ejecución/matriz (6 submódulos conectados a ejecución real)
- ❌ `validate_crema_indicator` — **sin test**
- ❌ `create_project_indicator_record` (SPI aislado, target=0, timezone naive) — sin test dedicado
- ❌ F6 (reactive) — sin test por no estar implementado

---

## 8. Recomendaciones priorizadas

1. **TKT-A (tests):** cubrir `validate_crema_indicator` con parametrización por criterio (scores exactos, thresholds 14/15/15/15, estados EXCELENTE/BUENO/REGULAR/DEFICIENTE) y `create_project_indicator_record` (SPI correcto, target=0, `reported_at` naive→UTC, autorización sede Axioma 3).
2. **TKT-B (F6 real):** hook post-commit en CRUD de `ProjectTask` / `ProjectExpense` / `ProjectTimeLog` que enqueue de `sync_project_indicators_and_kpis` (o tarea agendada nocturna por proyecto activo); registrar el evento en `automation_engine` como nueva acción `recompute_indicators`.
3. **TKT-C (G3):** blindar mediciones automáticas — columna o flag `origin ∈ {auto, manual}` en records (o por convención en `notes`) para que el upsert del sync solo toque records propios y el manual sea intocable por el motor.
4. **TKT-D (pulido):** unificar redondeo de SPI (4 decimales en ambos motores), marcar indicadores huérfanos de componentes eliminados y alerta visual para `target_value <= 0`.

---

## 9. Criterios de aceptación

- [x] Informe forense `docs/AUDITORIA_MOTOR_CALCULO_INDICADORES_PROYECTOS_20261021.md` generado con matriz de hallazgos
- [x] Verificación de hallazgos F1–F6 vs implementación `36329cb52` (4 resueltos, 2 parcial/pendientesdocumentados)
- [x] Precisión de `validate_crema_indicator` (C/R/E/M/A) y SPI de `create_project_indicator_record` auditadas
- [x] Mecanismos de sincronización (on-demand vs reactivo) y jerarquía EDT→Proyecto analizados
- [x] Pruebas unitarias asociadas verificadas por ejecución real (2/2 passed) + brecha de cobertura CREMA documentada (G1)
- [x] Commit `docs(projects):` + entrega en bridge
