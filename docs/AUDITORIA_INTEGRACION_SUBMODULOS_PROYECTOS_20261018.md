# INFORME FORENSE — Conexión e Integración Real de Submódulos de Proyectos (CCF)

**Ticket:** TKT-PROJECTS-SUBMODULES-INTEGRATION-AUDIT-01 · **Auditor:** freebuff · **Revisor:** agy
**Fecha:** 2026-10-18 · **Worktree:** /root/ccf · **Rama:** main
**Alcance:** 6 frentes (TimeTracking, Suministros/Costos, Línea Base, Carga de Trabajo, Ruta Crítica CPM, Automatizaciones) en backend (modelos/CRUD/servicios/endpoints) y frontend (drawers/secciones del enunciado).

---

## 1. Resumen del dictamen

| # | Frente | Veredicto | Ruptura principal |
|---|--------|-----------|-------------------|
| 1 | TimeTracking → horas reales | 🟡 **PARCIAL** | `create_project_time_log` no escribe en `ProjectTask` y `ProjectTask.actual_hours` **no existe** como columna; el EVM recalcula horas dinámicamente, pero sin escritura ni recompute al nodo de la tarea |
| 2 | Suministros (TaskSupply) → costo AC | ❌ **DESCONECTADO** | `TaskSupply` no tiene precio unitario ni costo ni vínculo a `ProjectExpense` — suma a `project_budget_spent`/AC = **0** |
| 3 | Línea Base → variaciones EVM/Curva S | ❌ **DESCONECTADA** | Ni `project_evm_service.py` ni `generate_curve_s_data` leen `ProjectBaseline`; la Curva S usa interpolación de `start_date/target_date` del proyecto |
| 4 | Carga de Trabajo → horas/subtareas | 🟡 **PARCIAL** | Construida sobre conteo de tareas asignadas (`active_tasks`/`completed`) y `capacity_status`; no agrega `estimated_hours` de la EDT ni `ProjectTimeLog` |
| 5 | Ruta Crítica CPM → dependencias/EDT | 🟡 **PARCIAL** | Conectada a `ProjectTaskDependency` (FS) y duraciones (`crud/projects.py:2024-2105`) pero aislada de la jerarquía EDT (no distingue padres/subtareas ni horas) y no alimenta Gantt/EVM |
| 6 | Automatizaciones → triggers reales | ❌ **SEMIAUTOMÁTICAS** | `evaluate_project_automations` solo se invoca desde el endpoint manual `POST` (`api/projects.py:5757`); completar una tarea/aprobar un gasto NO dispara reglas (grep de `task_completed`/`expense_` en mutaciones = 0 coincidencias) |

**Conclusión:** el patrón detectado en KPIs (auto-cálculo EVM sano, pérdidas en el tramo hacia la entidad del submódulo) se repite: 2 desconexiones duras (Suministros, Línea Base), 1 semiautomática (Automatizaciones) y 3 parciales (TimeTracking, Workload, CPM). El motor EVM es el receptor sano; los submódulos son emisores mordidos en la entrega.

---

## 2. Evidencia exacta por frente

### Frente 1 — TimeTracking (🟡 Parcial)
- `backend/models_projects.py:474-490`: `ProjectTimeLog(task_id, persona_id, hours, date, is_billable,...)`. Sin columna `actual_hours` en `ProjectTask` (grep en todo el modelo = 0 resultados).
- `backend/api/projects.py:5443` (`create_project_time_log`): valida `_ensure_task_in_project`, inserta el log, `_log_project_activity`... y **jamás toca la tarea** (no recompute de avance, no escritura de horas).
- Puentes existentes: `backend/services/project_evm_service.py:797-815` (`calculate_task_rollup` suma `time_logs` de los descendientes → `actual_hours` reportable) y `:1010-1037` (`calculate_project_tasks_rollup` → `total_actual_hours`).
- Endpoint de solo-lectura: `backend/api/projects.py:5537` (`get_project_time_tracking_summary`).
- **Veredicto:** las horas registradas SÍ llegan al EVM vía servicios (roll-up dinámico), pero la tarea queda silente (sin avance físico ni campo materializado) — paralelo directo al caso KPI: "se registran horas pero no se notan en la tarea".

### Frente 2 — Suministros de tareas → costo AC (❌ Desconectado)
- `backend/models_projects.py:210-219`: `TaskSupply` == solo `item_name`, `quantity`, `status("pending")`, sin `unit_cost`/`total_cost` ni `expense_id`.
- `backend/crud/projects.py` y `backend/api/projects.py:304-313, 3811-3830`: CRUD de suministros puramente descriptivo; el AC de componente/proyecto (`calculate_component_evm`, líneas 380-436 del servicio; `calculate_project_evm`, líneas 255-262) solo suma `ProjectExpense.status ∈ (approved, paid)` y `project.budget_spent` → **ningún suministro puede incidir en el AC**.
- **Veredicto:** un "Almacén/Suministros" que no mueve dinero es un inventario sin contabilidad; desconexión igual de severa que la de KPIs.

### Frente 3 — Línea Base → variaciones EVM y Curva S (❌ Desconectada)
- `backend/models_projects.py`: `ProjectBaseline` con snapshot (nombre/descripción + defecto JSON de métricas; ver crud). CRUD completo: `backend/crud/projects.py:2191-2245` (`create_project_baseline`, `get_project_latest_baseline`, `list_project_baselines`) y endpoints `backend/api/projects.py:5344,5378,5395`.
- Consumo: `grep ProjectBaseline|baseline backend/services/project_evm_service.py` = **0 coincidencias**. `generate_curve_s_data` (servicio, líneas 396-408) construye PV con `project.start_date/target_date/budget_allocated`, no con el snapshot.
- **Veredicto:** la Línea Base es decorativa: "crear" una LB no congela ninguna métrica que luego se compare en EVM/Curva S/Gantt. Las variaciones (SV/CV/EAC) se miden contra interpolación, no contra el plan autentificado.

### Frente 4 — Carga de Trabajo (🟡 Parcial)
- `backend/api/projects.py:1705` (`workload_summary` por sede) y `:5234-5250` (`/{project_id}/workload` Super-PRO) → ambos delegan en `crud.get_project_workload` (`backend/crud/projects.py:1792-1990`).
- Interno: `tasks_by_assignee`, `active_tasks` (≠completed), `completed`, y `capacity_status` (líneas 1930/1971: saturación derivada de **conteo de tareas**, no de horas).
- No consulta `estimated_hours` de la EDT ni `ProjectTimeLog`; el Axioma 1 se respeta (persona_id vía asignaciones), pero la saturación "por conteo" falsea el balance cuando las tareas tienen pesos de horas muy distintos.
- **Veredicto:** conectada a asignaciones (mitad de la cadena), desconectada de horas (la otra mitad).

### Frente 5 — Ruta Crítica CPM (🟡 Parcial)
- Implementación: `backend/crud/projects.py:2024-2105` (`calculate_critical_path`): duraciones por tarea + adyacencia desde `ProjectTaskDependency` (líneas ~2068-2078: `predecessor_id/successor_id, deleted_at IS NONE`) — bien para la capa de tareas.
- Endpoint: `backend/api/projects.py:5333` (CPM expuesto).
- Rupturas: (a) no distingue jerarquía EDT — un padre y sus subtareas compiten en el mismo grafo; (b) duraciones sin recurso/horas (no usa `estimated_hours` — (c) no hay acoplamiento con Gantt/EVM: un cambio de dependencia no re-etiqueta la fase ni el SPI. (d) `ProjectTaskDependency.lag_days` existe pero el flujo FS puro dominó.
- **Veredicto:** el CPM "calcula" pero en una isla: sin integración con la EDT ni con el plan cronológico usado por PV/SPI(t).

### Frente 6 — Automatizaciones (❌ Semiautomáticas / Triggers declarativos)
- Modelo `ProjectAutomationRule` (`backend/models_projects.py:449-470`) con `trigger_event` (default `task_completed`), `action_type`, `condition_data/action_data`, `execution_count`, `last_triggered_at`.
- CRUD completo + endpoint manual: `backend/api/projects.py:5555-5712` (reglas) y `:5745-5770` (`evaluate_project_automations` con `dry_run`).
- Executor real: `backend/crud/projects.py:~3380-3520` — acciones implementadas: `set_priority`, `create_followup_task`, y registro de `execution_count/last_triggered_at` (líneas 3487-3488).
- **La brecha:** grep de `evaluate_project_automations` en todo el backend = 2 únicas referencias (definición + endpoint manual). Ningún endpoint de mutación de tareas/fases/gastos dispara el evaluador → el trigger `task_completed` declarado **nunca se dispara solo**; son reglas "a mano" (declarativas).
- Motor genérico ajeno: `backend/services/automation_engine.py` (notificaciones multi-canal) no conoce reglas de Proyectos.

---

## 3. Matriz de conexión vs impacto en ejecución real

| Flujo esperado | Estado | Impacto en el usuario |
|---|---|---|
| Registro de horas → avance/horas visibles en la tarea | 🟡 Solo vía reports EVM, no en la tarea | "Registré 4h y en la tarea no se nota nada" |
| Horas → horas regulares del Frente 1 (ES/SPI(t)) | ✅ vía roll-up dinámico | OK en pantalla ejecutiva |
| Suministro creado/aprobado → costo AC (componente/proyecto) | ❌ | "Los suministros no mueven el presupuesto" |
| Gasto aprobado → AC del componente y del proyecto | ✅ (confirmado en audit KPI anterior) | OK |
| Línea Base creada → comparación base vs real en EVM/Curva S | ❌ | "Creamos la línea base pero las variaciones no la usan" |
| Carga de trabajo = f(assignmentes) | ✅ | OK |
| Carga de trabajo = f(horas estimadas/registradas) | ❌ | Saturación engañosa con tareas de pesos distintos |
| CPM en dependencias FS | ✅ | OK |
| CPM integrado a EDT/Gantt/EVM | ❌ | Ruta crítica "callejera" |
| trigger `task_completed` al completar tarea | ❌ | "Las automatizaciones no se ejecutan solas" |
| Acciones `set_priority`/`create_followup_task` via endpoint manual | ✅ | Funciona si el usuario pulsa "Ejecutar/Evaluar" |

---

## 4. Plan de implementación priorizado para AGY2

**TKT-SM-01 (P0) — Automatizaciones con triggers reales:**
- Llamar a `crud.evaluate_project_automations(db, project_id, trigger_event=..., actor_persona_id=current_user.id, user_sede_id=..., dry_run=False)` dentro de los endpoints de mutación de tareas (`task_completed` al pasar a `completed/done` en `api/projects.py` ~3740 y `crud` update), `expense_approved/paid` y `milestone_completed` (ya existen los hooks de `sync_parent_task_rollup` en las mismas rutas — reutilizar puntos de anclaje). Auditor-safe: envolver en try/except, log `automation_triggered`, y retornar sin romper la mutación. Docs `trigger_event` disponibles en schema (`schemas/projects.py:1249`).

**TKT-SM-02 (P0) — Suministros con costo:**
- Migración reversible (upgrade+downgrade): columnas `unit_cost Float`, `total_cost Float (persisted)`, `expense_id UUID FK → project_expenses.id NULL`.

- En los fluxos CRUD de suministros: al crear/editar/eliminar con costo, emitir/construir la `ProjectExpense` vinculada (status `planned`→`approved` configurable) para que el AC existente la recoja sin tocar el motor EVM. Frontend: `TaskSupplySection` + `ProjectBudgetDrawer` (mostrar origen del gasto "suministro").

**TKT-SM-03 (P0) — Línea Base funcional:**
- En `create_project_baseline` sincronizar snapshot real (BAC, fechas, avance, EVM calculado con `calculate_project_evm`).
- En `generate_curve_s_data` / `calculate_project_evm`: si existe `get_project_latest_baseline`, usar sus fechas/métricas como plan de referencia (baseline) y añadir en la respuesta los campos `planned_*` y `variance_*` (CPI_b, SPI_b). Frontend: Cursor S y Gantt leen el par `"baseline"` existente.

**TKT-SM-04 (P1) — TimeTracking materializado:**
- Petición de log de tiempo → tras `db.commit()`, recompute del roll-up de la tarea (`sync... con parent_id chain) ya implementado para tareas; ampliar a recompute del `progress_pct` por horas ("earned hours") solo si `progress_mode` lo permite, y **log de actividades** reportando el delta de avance. Considerar columna opcional `ProjectTask.actual_hours` (materializada por servicio de roll-up) o normalizar que la UI siempre lea el `TimeTrackingSummary` (coherencia de Data Source).

**TKT-SM-05 (P1) — Workload ponderado por horas:**
- Incluir por persona: Σ `estimated_hours` de tareas activas (solo hojas EDT, para no doble contar) y Σ horas reales de `ProjectTimeLog` del mes; `capacity_status` derivado de una `capacity_hours` configurable por persona, con fallback al conteo actual. Frontend: `ProjectWorkloadDrawer` ya consume el schema — solo añadir campos nuevos.

**TKT-SM-06 (P2) — Ruta Crítica integrada a la EDT:**
- Calcular el CPM sobre tareas hoja de la EDT (excluir padres end `build_task_node`), sumando `lag_days` de las dependencias, y exponer `critical_path` + `slack` en el endpoint del Gantt para pintar la cadena crítica. Marcar las tareas críticas en el roll-up EVM (flag `is_critical`).

---

## 5. Criterios de aceptación cubiertos

- [x] Informe estructurado en `docs/AUDITORIA_INTEGRACION_SUBMODULOS_PROYECTOS_20261018.md` con archivos y líneas exactas en backend (y referencias de drawers para frontend) para los 6 frentes.
- [x] Matriz Conectado/Desconectado/Parcial con impacto en ejecución real (Secciones 1 y 3).
- [x] Plan priorizado P0/P1/P2 accionable para AGY2 (Sección 4).
- [x] Commit convencional `docs(cms):` + submit por el puente a agy.
