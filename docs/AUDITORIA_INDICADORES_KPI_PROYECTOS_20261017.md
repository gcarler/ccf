# INFORME FORENSE — KPIs e Indicadores del Módulo de Proyectos (CCF)

**Ticket:** TKT-PROJECTS-KPI-INDICATORS-AUDIT-01 · **Auditor:** freebuff · **Revisor:** agy
**Fecha:** 2026-10-17 · **Worktree:** /root/ccf · **Rama:** main
**Alcance:** backend/services/project_evm_service.py, backend/models_projects.py, backend/crud/projects.py, backend/api/projects.py, backend/services/automation_engine.py, frontend (drawers KPI/IDP/EVM, page indicators).

---

## 1. Resumen Ejecutivo (Dictamen)

**La respuesta directa a la pregunta del usuario es: los KPIs que se pueden crear en la UI de Proyectos NO están conectados a la ejecución real del proyecto.** Los indicadores EVM (tiempo × financiero) SÍ están implementados, funcionales y conectados a tareas y gastos, pero con una ruptura crítica de tributación en el tramo Componentes→Proyecto.

| Sistema | ¿Existe? | ¿Conectado a la ejecución? | Dato fuente |
|---|---|---|---|
| **ProjectKPI** (`project_kpis`, Drawer "Metas Operativas") | ✅ Sí | ❌ **NO — 100% manual** | Solo captura manual (+1/+10 en UI, PATCH del valor) |
| **ProjectIndicator (IDP/MGA + CREMA)** (`project_indicators`) | ✅ Sí | ⚠️ **SEMI** — SPI automático pero solo de mediciones manuales | `ProjectIndicatorRecord` reportado a mano |
| **EVM Fiat / Avanzado** (CPI, SPI, CR, ES, TCPI, 4 Cuadrantes) | ✅ Sí | ✅ **SÍ** — derivado de tareas + hitos + gastos reales | `ProjectTask`, `ProjectMilestone`, `ProjectExpense` |

Además coexisten **3 sistemas paralelos de indicadores** sin una fuente única de verdad (duplicación metodológica).

---

## 2. Verificación detallada por sistema

### 2.1 ProjectKPI — DESCONECTADO de la ejecución (F1)

Evidencia de código:

- `backend/models_projects.py:306-323`: el modelo `ProjectKPI` solo tiene `title`, `description`, `target_value`, `current_value`, `unit`, `category`, `due_date`. **No existe ninguna columna de vinculación** (`source_type`, `linked_task_id`, `linked_component_id`, fórmula, ni periodicidad).
- `backend/api/projects.py:4640-4700`: los endpoints solo listan/crean/actualizan manualmente. `current_value` se actualiza únicamente con `payload.current_value` enviado por el cliente.
- `backend/crud/projects.py:1034-1090`: CRUD plano sin lógica de recálculo.
- `frontend/src/components/projects/ProjectKpiDrawer.tsx`: la UI solo ofrece botones `-1 / +1 / +10` y formulario manual. Un humano avanza el KPI a dedo.

**Consecuencia:** el usuario puede crear KPIs que nunca reflejarán la ejecución (tareas, EDT, horas, gastos). Confirmado el síntoma reportado.

### 2.2 ProjectIndicator (IDP/MGA + CREMA) — SEMI-conectado (F2)

- `backend/models_projects.py:472+`: `ProjectIndicator` + `ProjectIndicatorRecord` (base, meta, `period_targets`, CREMA, SPI por medición).
- `backend/crud/projects.py:4355-4385`: al registrar una medición, el SPI se deriva del registro persistido (`actual/target`, nunca del cliente, bien hecho) y `current_value` toma el último valor reportado.
- **Pero el `actual_value` lo escribe una persona a mano** (Drawer IDP, pestaña "Reportar Medición SPI" → `／indicators/{id}/records`). No hay pipeline automático desde Actividades/EDT/horas logs/gastos hacia el indicador.
- El Asistente CREMA (`validate_crema_indicator`) califica la **calidad metodológica** del indicador (0-100), no su datos: buen complemento MGA, no fuente de ejecución.

### 2.3 EVM estándar + avanzado — CONECTADO, pero con ruptura de tributación (F3, F4)

Lo que SÍ existe y funciona en `backend/services/project_evm_service.py` (1,532 líneas):

**Frente Tiempo:** SPI (`EV/PV`), Earned Schedule (ES, interpolación Lipke sigmoidea `3t² − 2t³`), SPI(t), `ProjectTimeLog` → horas reales en `calculate_project_tasks_rollup` y `calculate_task_rollup`.

**Frente Financiero:** BAC (`budget_allocated`), AC (gastos con estado `approved|paid` vía `ProjectExpense` + `budget_spent`), CPI (`EV/AC`), EAC (`BAC/CPI`), VAC, TCPI(BAC/EAC) con niveles de dificultad, Regla del 100% EDT (`validate_project_budget_100_rule`), brecha físico-financiera.

**Frente Híbrido Tiempo×Financiero:** EV = BAC×%avance, PV por vencimiento de tareas/interpolación, CR = CPI×SPI, Matriz de 4 Cuadrantes (`calculate_cpi_spi_quadrant`: Óptima / Riesgo-Aceleración / Crítica / Atención-Falso Ahorro), Regla del 15% PMI con alertas tempranas (early warnings), modelos de pronóstico EAC, curva S (`generate_curve_s_data`), árbol WBS con codificación automática (`build_project_wbs_tree`).

**Endpoints frontend verificados:** `/kpis`, `/advanced-indicators` (+`/records`, `/validate-crema`), `/evm`, `/evm-advanced`, desglose EDT (`get_project_components_breakdown`, línea 2830), roll-up (línea 3796), curve-S. Todos consumidos vía `apiFetch` con api y Drawers (cumplen frontend rules).

---

## 3. Matriz de tributación Subtareas → Actividades → Componentes (EDT) → Proyecto

| Tramo | Estado | Evidencia |
|---|---|---|
| Subtarea → Tarea (paquete) | ✅ **RESUELTO** | `calculate_task_rollup` (3 dimensiones, recursivo) + `sync_parent_task_rollup` en cascada al `physical_progress_pct` del padre, disparado en CRUD de tareas (`crud/projects.py:483,535,551`, `api/projects.py:3744`) |
| Tarea → Componente EDT | ✅ **RESUELTO** (con matiz) | `calculate_component_evm` usa avance continuo ponderado por horas (`physical_progress_pct` de tareas directas), AC de gastos directos o de sus tareas, PV por due-date. La cascada de `sync_parent_task_rollup` hace llegar el avance continuo de las subtareas al padre |
| Componente → Proyecto (físico) | ❌ **ROTO** | `calculate_project_evm` (línea 122) NO agrega componentes: usa simple conteo `completed_tasks / total_tasks` (o milestone count o manual). Es la línea de código line ~137-165 |
| Componente → Proyecto (financiero) | ⚠️ Parcial | La Regla del 100% valida que Σ(componentes) ≤ BAC, pero el EV/AC del proyecto se calcula aparte, no como suma de los EV/AC de componentes |
| Roll-up horas-ponderado a nivel proyecto | ✅ Existe pero **NO se consume** en el EVM | `calculate_project_tasks_rollup` (línea ~870) calcula el avance global ponderado por horas estimadas; solo se expone en un endpoint (`api/projects.py:3796`); ni `calculate_project_evm` ni `calculate_project_evm_advanced` (línea 1303) lo usan |

**Conclusión de la hilaridad:** la cadena está resuelta hasta el Componente. El tramo **Componente→Proyecto está gobernado por un conteo binario** en vez de la agregación ponderada continua. En proyectos con subtareas parcialmente avanzadas el SPI/CPI del proyecto subestima el avance real y se desincroniza con lo que muestra el desglose EDT (hotel de indicadores incoherente entre niveles).

---

## 4. Otras observaciones

- **F5 — Duplicación sin fuente única de verdad:** `ProjectKPI`, la matriz virtual de indicadores EVM (`current_value` = cpi/spi/spi_t/cr/gap/tcpi en `project_evm_service.py:1197-1273`) y `ProjectIndicator` son 3 universos sin interconexión, con 2 UIs manuales distintas (KPI Drawer vs IDP Drawer).
- **F6 — Motor de automatización sin acciones de KPI:** `ProjectAutomationRule` + `automation_engine.py` existen y funcionan (canales de notificación), pero no tienen `action_type` que escriba/recalcule un KPI o indicador al ocurrir eventos de ejecución (tarea completada, gasto aprobado, log de horas).
- Cumplimiento de reglas verificable en los drawers: apiFetch, tokens semánticos, ConfirmActionDrawer (no modals), EmptyState/Skeleton/sonner. Sin hallazgos de frontend rules.

---

## 5. Propuesta: 6 familias de indicadores Pro autovinculados a la ejecución

Diseño transversal: nueva columna `source_type` + `source_ref` (o `formula` con `metric_key`) en `ProjectKPI`/`ProjectIndicator`, y un servicio único `project_indicator_service.py` con `recompute_project_indicators(db, project_id, actor)` llamado: (a) tras cada mutación de tarea/hito/gasto/TimeLog (ya hay ganchos: `sync_parent_task_rollup`, CRUD de expenses, engine de eventos), (b) en un job agendado (persist apscheduler/celery ya presentes en el stack), y (c) en lecturas de endpoints KPI. Sin consultas manuales del usuario.

1. **Familia Ejecución Física (Habilidad EDT):** Avance físico ponderado por horas (`calculate_project_tasks_rollup` – ya existe el cálculo, conectar como fuente automática); % subtareas en riesgo (vencidas + sin avance); índice de hitos cumplidos a tiempo (`ProjectMilestone.is_completed` vs `due` antes de vencer); % de entregables de EDT aprobados.
2. **Familia Financiera de Control:** Quema de presupuesto vs avance (burn rate semanal = Δbudget_spent/Δdías), Costo por unidad de producto (`AC` / unidades IDP), `% ejecución financiera` vs plan de fases, días/poza de fondos librados (`ProjectExpense.status = planned → approved`).
3. **Familia EA de Tiempo (Cronograma):** SPI(t) del Earned Schedule ya existente; variación del cronograma (SV_Días = ES − AT); índice de retraso de ruta crítica (fracasa de dependencias `ProjectTaskDependency` FS cruzadas); densidad de cargas/horas (`ProjectTimeLog`/`estimated_hours` por EDT en riesgo de sobrecarga).
4. **Familia Híbrida EVM Pro (ya operativa, connecting):** CPI, SPI, CR, TCPI, puntuación de Cuadrante (4C mapping), cuenta de early warnings activos (Regla 15%),.coordinates de proyección a la conclusión (EAC/VAC) — solo falta aporte del roll-up ponderado correcto y exponerlo como indicadores auditables en la matriz IDP.
5. **Familia Calidad y Riesgo:** score de CREMA promedio (ya persistido); severidad ponderada de riesgos del proyecto (Σ `impact×probabilidad` de `ProjectRisk` activos), % riesgos con plan de mitigación, ratio cierre de riesgos por fase.
6. **Familia Participación y Máximo Input (Academia al Proyecto):** conecta el Kernel de Personas: personas asignadas activas vs comprometidas (miembros), productividad de tareas por responsable (% asignadas completadas, por `assignee`), avance per-componente por dueño (necesario para gobernanza ministerial), y (#menciones conversaciones)/◫ de actividad del equipo como velocidad indirecta.

**Implementación recomendada (orden):**
- TKT-A: Rutas de recálculo en el tramo rótura — `calculate_project_evm` debe aceptar fuente de avance: preferent `calculate_project_tasks_rollup.overall_physical_progress_pct` (ponderado), fallback conteo. Al concurrente, EV/CPI/SPI del proyecto = Σ componentes (EV_c, AC_c) para coherencia EDT↔Proyecto.
- TKT-B: Auto-vinculación de KPIs/IDP: `source_type ∈ {ejecucion_fisica, financiera, evm, cronograma, calidad_riesgo, equipo}` + recompute on event + botón "Sincronizar ahora" en los drawers.
- TKT-C: Consolidación de UI: un solo identador de Indicadores con secciones (MGA/CREMA manual + EVM automático + KPIs vinculados).

---

## 6. Criterios de aceptación cubiertos

- [x] Informe forense completo en `docs/AUDITORIA_INDICADORES_KPI_PROYECTOS_20261017.md`
- [x] Verificación real de código backend (`project_evm_service.py` 1532 líneas, modelos, CRUD, api) y frontend (3 drawers + page indicators)
- [x] Diagnóstico de desconexión: **ProjectKPI manual=100%; IDP semi; EVM conectado**
- [x] Verificación de roll-up: resuelto hasta Componente; **roto en Componente→Proyecto** (conteo binario vs roll-up ponderado no consumido)
- [x] 6 familias Pro propuestas con mecanismo de vinculación automática y plan de 3 tickets
