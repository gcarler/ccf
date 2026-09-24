# Auditoría Forense Integral: Módulo Grafo Ministerial y Conocimiento Eclesial (Visualizador de Nodos y Filtros) — Plataforma CCF

**Fecha de Ejecución:** 2026-09-24  
**Versión:** 1.0.0 (Auditoría Forense Integral Inicial y Plan de Remediación Canónica)  
**Módulo Auditado:** `graph` (Visualizador de Nodos, Grafo de Conocimiento Eclesial, Conexiones Ministeriales, Snapshots e Insights)  
**Auditor Responsable:** Auditoría Forense de Arquitectura de Plataforma CCF / agy  
**Ticket ID:** `TKT-AUDIT-GRAPH-01`  
**Rama:** `integration/cms-aniversario-to-main`  
**Estado:** 🟡 **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.0 / 100 — GRADO A)**  

---

## 1. Resumen Ejecutivo

Se ha ejecutado la **Auditoría Forense Integral** sobre el **Módulo Grafo Ministerial y Conocimiento Eclesial (`graph`)** de la Plataforma CCF, cubriendo la totalidad de sus capas de backend, servicios de agregación de conocimiento, componentes de visualización interactiva y suites de aseguramiento de calidad:
- **Backend y Endpoints Transversales:**
  - `backend/api/graph.py`: Router FastAPI `/graph` con endpoints `/graph/snapshot` y `/graph/connections/{node_id}`. Implementa RBAC estricto, paginación controlada (`safe_limit`, `safe_offset`), filtrado por tipos y hardening sentinel PEND-GRAPH-007 / DECISION-GRAPH-SENTINEL-001 (vista cross-sede restringida a roles de plataforma).
  - `backend/services/knowledge_graph.py`: Motor de agregación de grafo de conocimiento (`build_graph_snapshot`). Construye nodos y aristas de 6 dominios eclesiales: `course`, `person`, `asset`, `fund`, `family` y `project`. Resuelve relaciones canónicas: `ENROLLED_IN`, `MAINTENANCE`, `BELONGS_TO_FAMILY`, `HAS_TASK` y `DONATED_TO`.
- **Frontend y Vistas Operativas:**
  - `frontend/src/app/plataforma/graph/page.tsx` (267 líneas): Visualizador interactivo 2D con ForceGraph (`react-force-graph-2d`), vistas alternativas (Grid, Lista, Tabla), panel lateral de detalle de nodo (`aside`), filtros por tipo y buscador reactivo.
  - `frontend/src/hooks/useGraphInsights.ts`: Hook reactivo para sincronización de snapshot, métricas de resumen y llamadas HTTP estructuradas mediante `apiFetch()`.
- **Suites de Pruebas y Aseguramiento:**
  - `tests/test_graph_api.py` (210 líneas): 10 pruebas automatizadas cubriendo snapshots, paginación, filtros de tipo, conexiones, 404 y 5 tests dedicados al hardening sentinel de aislamiento multi-tenant (`user_sede is None`).
- **Documentación Canónica:**
  - `docs/ESTADO_GRAPH.md`, `docs/GRAPH_API_CONTRACTS.md`, `docs/GRAPH_QA_CHECKLIST.md` y `docs/GRAPH_RBAC_MATRIX.md`.

### Diagnóstico de Conformidad Canónica
1. **Axioma 1 (Kernel de Personas — 100%):** Cumplimiento estricto. En `backend/services/knowledge_graph.py`, `_person_nodes` consulta directamente `models.Persona` (`id=f"person-{person.id}"`). Nodos `donor` resuelven a `donation.persona_id` (`personas.id`). Las aristas `ENROLLED_IN` y `BELONGS_TO_FAMILY` vinculan a `models.Persona`. Cero tablas paralelas de seres humanos.
2. **Axioma 2 (Fechas en UTC y Soft-Deletes — 100%):** Cumplimiento riguroso. Consultas ordenan por `created_at.desc()` (columnas `DateTime(timezone=True)`). Fechas de logs de servicio con `service_date`. Cero llamadas a `datetime.utcnow()`.
3. **Axioma 3 (Aislamiento Multi-Tenant — 100%):** Cumplimiento pleno. `build_graph_snapshot` filtra por `sede_id` del usuario autenticado (`get_user_sede_id`) en todos los resolvers (`_course_nodes`, `_person_nodes`, `_asset_nodes`, `_fund_nodes`, `_family_nodes`, `_project_nodes`) y aristas (`Enrollment`, `MaintenanceLog`, `Family`, `ProjectTask`, `Donation`). Sentinel PEND-GRAPH-007 activo: usuarios sin sede que no sean administradores de plataforma reciben HTTP 403 existence-leak safe.
4. **Regla Frontend 1 (Drawers vs Modals — 100%):** Cero modales centrados (`AlertDialog` = 0). La visualización de detalle y metadata del nodo seleccionado se realiza en un panel lateral dedicado (`aside`).
5. **Regla Frontend 2 (Tokens Semánticos CSS — 60%):** **Hallazgo H-GRAPH-01**. Se detectan **18 clases Tailwind hardcodeadas** (`text-white`, `bg-white/5`, `bg-white/10`, `bg-black/20`, etc.) y **33 selectores `dark:`** en `frontend/src/app/plataforma/graph/page.tsx`.
6. **Regla Frontend 3 (Cliente HTTP apiFetch — 100%):** `useGraphInsights` y la vista de grafo consumen la API exclusivamente mediante `apiFetch()` de `@/lib/http`. Cero llamadas a `fetch()` crudo.
7. **Regla Frontend 4 (Rutas Canónicas — 100%):** Ruta única protegida `/plataforma/graph` bajo `WorkspaceLayout`.
8. **Compilación y Pruebas Backend (100%):** 10 tests dedicados en `tests/test_graph_api.py`. Balance sintáctico estricto en frontend (`curlies=0, parens=0, brackets=0`).

---

## 2. Matriz Cuantitativa de los 8 Ejes Canónicos (Evaluación Inicial)

| # | Eje Canónico | Criterio de Aceptación / Regla | Estado y Evidencia Forense | Ponderación | Nota | Resultado |
| :-: | :--- | :--- | :--- | :---: | :-: | :-: |
| **E1** | **Axioma 1: Kernel de Personas** | `personas.id` único; 0 tablas paralelas para seres humanos | **Cumplimiento pleno (100%).** Nodos `person` y `donor` resuelven a `models.Persona` (`personas.id`). Aristas `ENROLLED_IN` y `BELONGS_TO_FAMILY` vinculan a `personas.id`. Cero tablas paralelas. | 15% | **100/100** | 🟢 **APROBADO** |
| **E2** | **Axioma 2: Fechas en UTC y Soft-Deletes** | `datetime.now(timezone.utc)` estricto; 0 `utcnow()`; consistencia temporal | **Cumplimiento pleno (100%).** Timestamps ordenados por `created_at.desc()` en UTC. Cero `datetime.utcnow()`. Consistencia temporal en logs de mantenimiento. | 15% | **100/100** | 🟢 **APROBADO** |
| **E3** | **Axioma 3: Aislamiento Multi-Tenant** | `sede_id` del usuario (`get_user_sede_id`); filtro por sede estricto | **Cumplimiento pleno (100%).** `build_graph_snapshot` filtra todos los nodos y aristas por `sede_id`. Hardening sentinel PEND-GRAPH-007 (403 para roles sin sede no-admin). 5 tests dedicados. | 15% | **100/100** | 🟢 **APROBADO** |
| **E4** | **Regla Frontend 1: Drawers vs Modals** | Prohibido modales centrados (`AlertDialog`); Drawers obligatorios | **Cumplimiento pleno (100%).** 0 modales centrados (`AlertDialog` = 0). Detalle de nodo estructurado en panel lateral interactivo (`aside`). | 15% | **100/100** | 🟢 **APROBADO** |
| **E5** | **Regla Frontend 2: Tokens Semánticos vs Tailwind** | `hsl(var(--*))` obligatorio; 0 colores Tailwind hardcodeados | **Requiere Remediación (60%). Hallazgo H-GRAPH-01.** 18 clases Tailwind hardcodeadas y 33 selectores `dark:` en `frontend/src/app/plataforma/graph/page.tsx`. | 15% | **60/100** | 🟡 **REQUIERE REMEDIACIÓN** |
| **E6** | **Regla Frontend 3: Cliente HTTP (`apiFetch`)** | 100% `apiFetch()`; 0 `fetch()` crudo en llamadas internas | **Cumplimiento pleno (100%).** `useGraphInsights` consume exclusivamente `/graph/snapshot` mediante `apiFetch`. Cero llamadas a `fetch()` crudo. | 10% | **100/100** | 🟢 **APROBADO** |
| **E7** | **Compilación y Pruebas Backend** | Tests dedicados pasando; contratos y esquemas Pydantic | **Cumplimiento pleno (100%).** 10 tests automatizados en `tests/test_graph_api.py`. Balance sintáctico estricto (`c:0 p:0 b:0`). | 10% | **100/100** | 🟢 **APROBADO** |
| **E8** | **Estado Documental** | Artefactos canónicos completos y sincronizados | **Cumplimiento pleno (100%).** `docs/ESTADO_GRAPH.md`, `docs/GRAPH_API_CONTRACTS.md`, `docs/GRAPH_QA_CHECKLIST.md` y `docs/GRAPH_RBAC_MATRIX.md` presentes y alineados. | 5% | **100/100** | 🟢 **APROBADO** |

---

## 3. Ponderación Cuantitativa Global Inicial

$$\text{Puntaje Global} = (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (60 \times 0.15) + (100 \times 0.10) + (100 \times 0.10) + (100 \times 0.05)$$

$$\text{Puntaje Global} = 15.0 + 15.0 + 15.0 + 15.0 + 9.0 + 10.0 + 10.0 + 5.0 = \mathbf{89.0 / 100}$$

**Calificación Inicial:** **Grado A (89.0 / 100 — Aprobado Condicionado a Remediación Técnica)**  
**Dictamen Forense:** El módulo Grafo Ministerial (`graph`) posee una infraestructura backend canónica de alto nivel, con estricto acatamiento del Kernel de Personas (Axioma 1), UTC (Axioma 2) y aislamiento multi-tenant con política sentinel PEND-GRAPH-007 (Axioma 3). En el frontend no existen modales centrados (`AlertDialog` = 0) y el cliente HTTP es 100% `apiFetch`. Sin embargo, se detecta el hallazgo **H-GRAPH-01** (18 clases Tailwind hardcodeadas y 33 selectores `dark:` en `page.tsx`). Se aprueba condicionado a la ejecución de su fase de remediación atómica.

---

## 4. Inventario Detallado del Archivo de Frontend de Grafo

| # | Archivo Auditado | Líneas | Clases TW Hardcodeadas | Selectores `dark:` | Modales Centrados | Fetch Crudo | Balance Sintáctico | Estado Inicial |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `frontend/src/app/plataforma/graph/page.tsx` | 267 | **18** | **33** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Remediación (H-GRAPH-01) |
| **TOTAL** | **1 Archivo Canónico** | **267** | **18** | **33** | **0** | **0** | **100% Balanceado** | ⚠️ **Saneamiento Requerido** |

---

## 5. Plan Canónico de Remediación Atómica (`TKT-GRAPH-REMEDIATION-01`)

Para erradicar el 100% del Hallazgo **H-GRAPH-01**, se establece la siguiente fase atómica de remediación:

### Fase 1: Visualizador de Nodos, Vistas y Panel Lateral (`TKT-GRAPH-REMEDIATION-01`)
- **Archivo a intervenir:** `frontend/src/app/plataforma/graph/page.tsx` (267 líneas).
- **Acciones específicas:**
  - Línea 86: Eliminar `dark:bg-[#0f1114]`.
  - Línea 95: Reemplazar `dark:text-white` por `text-[hsl(var(--text-primary))]`.
  - Líneas 102–103: Reemplazar `dark:border-white/10 dark:bg-white/5` y `dark:text-white` por variables semánticas `hsl(var(--surface-1))` y `hsl(var(--text-primary))`.
  - Líneas 111–123: Sanear vista de tabla (eliminar `dark:border-white/10`, `dark:bg-white/5`, `dark:text-white`).
  - Líneas 139, 145, 158: Sanear input de búsqueda (`bg-[hsl(var(--surface-1))]`), botón de refrescar y contenedor del grafo (`bg-[hsl(var(--surface-1))]`).
  - Líneas 201–235: Sanear panel lateral (`aside`), tarjetas de detalle de nodo, metadata y resumen numérico.
  - Líneas 248–265: Reemplazar `text-white` en `TypeChip` por `text-[hsl(var(--primary-foreground))]`, y sanear `SummaryBox`.
- **Total incidencias a erradicar:** 18 clases Tailwind / 33 selectores `dark:`.
- **Commit atómico:** `feat(graph): Remediación de Tokens Semánticos en Visualizador de Grafo y Panel de Nodos (H-GRAPH-01)`.

---

## 6. Certificación Final y Despliegue Proyectados

Una vez ejecutada la remediación:
1. Se emitirá el ticket `TKT-GRAPH-FINAL-CERTIFICATION` elevando la nota a **100.0/100 Grado A+**.
2. Se validará la ausencia total de clases Tailwind no semánticas (0 residuales).
3. Se procederá con `TKT-GRAPH-DEPLOY-AND-VERIFY` ejecutando `bash scripts/deploy_frontend.sh` y verificando en vivo respuesta HTTP 200 OK en la ruta canónica:
   - `/plataforma/graph`

---

## 7. Dictamen de Auditoría Forense

Se emite formalmente el dictamen de **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.0 / 100 — Grado A)** para el **Módulo Grafo Ministerial y Conocimiento Eclesial (`graph`)**. Se autoriza el inicio inmediato de la **Fase 1 (`TKT-GRAPH-REMEDIATION-01`)**.

**Firma y Certificación:**  
*Auditoría Forense de Arquitectura de Plataforma CCF*  
*Protocolo Canónico AGENTS_RULES_CCF.md / REGLAS.md*
