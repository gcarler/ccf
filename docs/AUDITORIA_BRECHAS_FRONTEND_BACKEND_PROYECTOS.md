# Auditoría de brechas Frontend ↔ Backend — Módulo de Proyectos

> **Estado**: v2, corregida por agy el 2026-10-28. Reemplaza la v1 de freebuff, cuyas afirmaciones se contrastaron una a una contra el código; 8 resultaron falsas o exageradas y se eliminan o se corrigen aquí.
> **Método**: lectura estática (`git grep`, lectura de archivos) sobre la rama `integration/projects-tools-and-governance-20261026`. **No** se ejecutó la aplicación ni `scripts/audit_projects_api_contracts.py`, y no se hicieron peticiones HTTP.
> **Alcance**: `frontend/src/components/projects/`, `frontend/src/app/plataforma/projects/`, `frontend/src/lib/projects/`, `frontend/src/types/projects.ts` y `backend/api/projects.py`, `backend/schemas/projects.py`.

---

## 1. Resumen

| Métrica | Valor verificado |
|---|---|
| Rutas en `backend/api/projects.py` | **161** (74 GET, 46 POST, 22 DELETE, 17 PATCH, 2 PUT), conteo por regex sobre `@router.<verbo>(` |
| `fetch()` crudo en el cliente de proyectos | 0 en lo revisado (se usa `apiFetch`) |
| Endpoints llamados por la UI que no existen en backend | Ninguno detectado en las rutas contrastadas |
| Endpoints de backend sin consumidor en la UI | **1 confirmado**: `GET /projects/{id}/tasks-rollup`; 2 más son redundantes (ver §3) |

No se publica un porcentaje de paridad global: la v1 daba "91 %" sin fórmula reproducible.

**Veredicto**: el módulo está en buena paridad funcional. Las brechas reales son pocas y pequeñas: un tipo TypeScript incompleto, tipos genéricos y manejo de errores silencioso.

---

## 2. Brechas Frontend → Backend

### 2.1 Llamadas a endpoints inexistentes
Ninguna detectada. Esta conclusión es de lectura estática, no de ejecución.

### 2.2 Errores silenciosos en el cliente (confirmado)
| Archivo | Líneas | Detalle |
|---|---|---|
| `ProjectMasterView.tsx` | 151-181 | 4 `catch { // fallback silencioso }` en las cargas de KPIs, presupuesto, riesgos, carga de trabajo y tiempo. Si falla una, la tarjeta queda en blanco sin aviso al usuario. AGENTS §2 exige estados de carga, vacío y notificación. |
| `ProjectWorkflowView.tsx` | ~147 | `loadComponents` con fallback silencioso (no re-verificado línea a línea en v2). |
| `ProjectDriveDrawer.tsx` | 123 | Comentario "endpoint mockeado" desactualizado; el endpoint real existe. Solo limpieza. |

### 2.3 Formularios cuyos campos el backend descarta
Ninguno confirmado. **Retirado de la v1**: el supuesto riesgo `name` vs `title` en la edición de KPI. `ProjectKpiDrawer.tsx:397-400` envía solo `{ current_value }`.

### 2.4 Datos simulados en el cliente
Ninguno de negocio detectado. Los `*.stories.tsx` son fixtures de Storybook.

---

## 3. Brechas Backend → Frontend

| # | Endpoint | Estado verificado | Acción |
|---|---|---|---|
| 1 | `GET /{id}/tasks-rollup` | **Sin consumidor** en `frontend/src` (fuera de tests). | Evaluar su uso en el WBS, **solo si** se confirma que la UI hace N llamadas a `/tasks/{id}/dimensions` (no verificado). |
| 2 | `GET /{id}/indicators/execution-matrix` | La UI no lo llama, pero obtiene la misma matriz embebida en `GET /projects/{id}` (`indicators/page.tsx:76-87`) y en la respuesta de `sync-execution` (`:128`). | Redundante, no es brecha de negocio. Decidir si se deprecia. |
| 3 | `GET /{id}/components/budget-100-rule` | La UI no lo llama, pero `ProjectComponentDrawer.tsx:109` usa el `budget_rule` calculado por backend que viene dentro de `components-breakdown`, y lo muestra. | Redundante, no es brecha de negocio. |
| 4 | `GET /projects/summary` y `GET /projects/workload` (sin paginar) | Según v1, la UI usa solo `summary-page` y `/{id}/workload`. **No re-verificado en v2.** | Decidir oficial o deprecar. |

### Afirmaciones de la v1 que resultaron falsas (no son brechas)
| Afirmación v1 | Realidad |
|---|---|
| `convert-and-publish` no se usa | Se usa en `ProjectAnyDocDrawer.tsx:124`. |
| No existe vista global de pizarras | `plataforma/whiteboard/page.tsx:46` llama a `GET /projects/whiteboards` mediante `fetchProjectWhiteboards`. |
| La UI no muestra el desglose de reservas PMI | `ProjectBudgetDrawer.tsx:291-296` y `ProjectEVMDrawer.tsx:906-923` muestran paquetes de trabajo, contingencia y reserva de gestión. |
| La UI recompone la matriz de ejecución con un POST | El POST `sync-execution` es la acción del botón "Sincronizar Pro"; la matriz se lee del GET del proyecto. |

---

## 4. Desalineaciones de contrato y tipos

| Ámbito | Backend | Frontend (TS) | Estado |
|---|---|---|---|
| **`ProjectExpense.status`** | `Literal["planned","committed","approved","paid"]` (`schemas/projects.py:488`) | `'planned' \| 'committed' \| 'paid'` (`types/projects.ts:88`) | **Desalineación real**: el TS omite `approved`. Un gasto aprobado queda mal tipado. No se revisó qué muestra hoy la UI para ese estado. |
| `ProjectKPI.progress_percent` | `progress_percent: int` (`schemas/projects.py:440`) | Ausente en `ProjectKPI` (`types/projects.ts:45-65`) | Falta. Los campos `frente`, `is_orphaned`, `target_value_valid`, `component_name` y `last_spi` **ya existen** en TS. |
| `TaskSupplyRecord.status` | `Literal["pending","ready","unavailable","received","approved","purchased","paid"]` (`schemas/projects.py:52`) | `status: string` (`types/projects.ts:~400`) | Tipo más débil que el backend. Riesgo bajo. |
| `dependency_type` | `Literal["FS","SS","FF","SF"]` | `'FS' \| 'SS' \| 'FF' \| 'SF'` (`types/projects.ts:72`) | **Alineado.** La v1 decía lo contrario. |
| `ProjectStatus`, prioridad, `development_approach`, `pmo_type`, `charter_status` | Literales | Uniones equivalentes | Alineados (según v1; no re-verificados uno a uno en v2). |

### Duplicación de umbral
`ProjectEVMForecastSimulator.tsx:58` fija `progress >= 15` para la regla de estabilidad del CPI, y el backend calcula `cpi_stability_rule` con la misma regla. El simulador evalúa una **hipótesis** del usuario, no el CPI actual, así que no puede leer el valor del backend tal cual. Lo que corresponde es extraer la constante a un único lugar. Prioridad baja.

---

## 5. Plan de acción corregido

| Prioridad | Tipo | Ítem | Esfuerzo |
|---|---|---|---|
| **Alta** | Contrato | Agregar `'approved'` a `ProjectExpense.status` en `types/projects.ts` y revisar badges, filtros y formularios de gastos para ese estado. | S |
| **Media** | Robustez | Sustituir los 4 `catch` silenciosos de `ProjectMasterView.tsx:151-181` por un estado de error parcial visible (norma AGENTS §2). | S |
| **Media** | Contrato | Tipar `TaskSupplyRecord.status` con la unión del backend y agregar `progress_percent` a `ProjectKPI`. | S |
| **Baja** | B→F | Usar `tasks-rollup` en el WBS, **solo si** primero se confirma el problema de N llamadas a `/dimensions`. | M |
| **Baja** | Limpieza | Quitar el comentario "mockeado" de `ProjectDriveDrawer.tsx:123`; extraer la constante 15 del simulador; ejecutar `python3 scripts/audit_projects_api_contracts.py --check` y regenerar `docs/PROJECTS_API_ROUTE_INVENTORY.md` si hay diferencias. | S |
| **Baja** | Decisión | Decidir si se deprecian `execution-matrix`, `budget-100-rule`, `/projects/summary` y `/projects/workload` (redundantes). | S |

### Descartado respecto de la v1
Exponer `execution-matrix` y `budget-100-rule` en la UI, corregir el payload de edición de KPI, mostrar las reservas PMI, crear una vista global de pizarras y migrar a `convert-and-publish`. Todo eso ya está resuelto o nunca fue una brecha.

---

## 6. Límites de esta auditoría
1. Análisis estático; no se ejecutó la aplicación ni se hicieron peticiones HTTP.
2. Una llamada con ruta armada en tiempo de ejecución podría escapar a un `git grep`.
3. Los puntos marcados "no re-verificado" provienen de la v1 y no se contrastaron en la v2.
4. No se evaluó el impacto en la UI del estado `approved` de gastos ni la existencia real del problema de N llamadas a `/dimensions`.
