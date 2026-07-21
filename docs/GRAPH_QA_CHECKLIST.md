# QA Checklist — Módulo Graph

**Fecha:** 2026-07-19
**Estado de cobertura:** 2/6 artefactos canónicos (ESTADO_GRAPH ✅, este QA ✅). Faltan API_CONTRACTS, RBAC_MATRIX, smoke script propio, backlog estable.

> **Objetivo:** validar el módulo Graph (visualización de grafo de conocimiento) como unidad aislada antes de cerrar una tarea, commit o despliegue. Este checklist refleja el contrato actual del endpoint `/api/graph/snapshot` después del fix de graceful degradation para `models.AssetItem` (2026-07-19).

---

## Backend

### Endpoints

- [ ] `GET /api/graph/snapshot` — autenticado → 200 con `{nodes, edges, meta}`
- [ ] `GET /api/graph/snapshot?limit=N&offset=M` — paginación: `limit` clamped a [1, 500], `offset` ≥ 0
- [ ] **Cap anti-DoS `expanded_limit = 1500`** (aplicado por `graph.py` como `min(safe_limit + safe_offset, 1500)`): cota el input por resolver, NO el total de nodos. **Total real de nodos en snapshot ≈ 4260** (suma de las cuotas por resolver: person 1500 + course 750 + asset 750 + project 750 + family 500 + fund 10) cuando todos los resolvers están poblados; **≈ 3510** sin `AssetItem` (caso típico del test env tras el fix 2026-07-19, ver §Graceful degradation). El slice `nodes[safe_offset : safe_offset + safe_limit]` sólo queda vacío cuando `safe_offset >= total_nodes` real, NO cuando `safe_offset >= 1500`. El cap previene traversal extremo y DoS por offsets abusivos (e.g., `?limit=500&offset=100000` no degrada la query linealmente más allá de 1500 unidades de input).
- [ ] `GET /api/graph/snapshot?types=course,person` — filtro de tipos resuelto case-insensitive whitespace-trim
- [ ] `GET /api/graph/snapshot?types=__invalid` — types desconocidos se ignoran silenciosamente (no 4xx)
- [ ] `GET /api/graph/snapshot?limit=99999` — clamping real a 500, no error
- [ ] `GET /api/graph/snapshot?offset=-1` — clamping real a 0
- [ ] `GET /api/graph/connections/{node_id}` — nodo existente → 200 con `{node, incoming, outgoing, related_nodes, meta}`
- [ ] `GET /api/graph/connections/{unknown_id}` — 404 con `detail="Node not found"`
- [ ] `GET /api/graph/connections/{unknown_id}?limit=99999` — clamping a 500 incluso en 404

### Multi-tenant (Axioma 3)

- [ ] Snapshot del usuario autenticado **sólo incluye nodos de su `sede_id`**
- [ ] Nodos de otras sedes **no aparecen** ni siquiera como `{"id": "..."}`
- [ ] Edges cross-sede (Enrollment cross-sede) **filtrados** vía JOIN sobre Persona.sede_id
- [ ] Connections devuelve nodos related **sólo de la misma sede** que el nodo solicitado
- [ ] **Caso `user.sede_id == None` (asumido, riesgo pendiente)**: si `get_user_sede_id(db, current_user.id)` retorna `None`, **ninguna** query (`_course_nodes`, `_person_nodes`, `_family_nodes`, `_project_nodes`, `_asset_nodes`, etc.) aplica filtro de sede; el snapshot devuelve vista global sin error y **sin 403/401**. Este comportamiento existe hoy por diseño implícito (no hay else-branch explícito); documentar formalmente y decidir (ver `PEND-GRAPH-006`).

### Graceful degradation

> Contrato añadido en fix 2026-07-19 (`backend/services/knowledge_graph.py:_asset_nodes`). Cubierto por asserts en `tests/test_graph_api.py`.

- [ ] **Consolidado — efecto cascada al faltar `models.AssetItem`**: `_asset_nodes` retorna `[]` (no AttributeError), no se materializan nodos `type="asset"`; adicionalmente, el bloque edges `MAINTENANCE` usa el guard `if _has_model("MaintenanceLog") and _has_model("AssetItem")` (AND lógico, no OR), por lo que **tampoco** aparecen nodos `type="maintenance_log"` ni aristas `MAINTENANCE`. Verificación QA contra asserts en `tests/test_graph_api.py` (4 tests cubren este contrato).
- [ ] El log emite un único warning por modelo ausente por proceso (no spam) — `_warned_missing_models` cache
- [ ] Comportamiento idempotente: dos llamadas seguidas con el mismo modelo ausente producen un único warning en logs

### Resolvers (orden lexicográfico)

| Tipo | Modelo SQLAlchemy | Comportamiento cuando falta |
|---|---|---|
| `course` | `models.Course` | Crash (no tiene guard — modelo crítico) |
| `person` | `models.Persona` | Crash (no tiene guard — modelo crítico) |
| `asset` | `models.AssetItem` | **Graceful** ✅ |
| `fund` | `models.Fund` | Crash (no tiene guard) |
| `family` | `models.Family` | Crash (no tiene guard) |
| `project` | `models.Project` | Crash (no tiene guard) |

> ⚠️ **Nota para QA:** sólo `asset` está hoy con graceful degradation. Cualquier fallo de import en los otros modelos crashea el snapshot. Antes de añadir más guards, confirmar con `docs/ESTADO_GRAPH.md` que el modelo en cuestión es opcional.

### Edge types

| Edge | Source → Target | Filtro por sede |
|---|---|---|
| `ENROLLED_IN` | `person-*` → `course-*` | JOIN sobre Persona.sede_id |
| `MAINTENANCE` | `asset-*` → `maintenance-*` | JOIN sobre AssetItem.sede_id (omitido si AssetItem falta) |
| `BELONGS_TO_FAMILY` | `person-*` → `family-*` | Filtro Persona.sede_id |
| `HAS_TASK` | `project-*` → `task-*` | JOIN sobre Project.sede_id |
| `DONATED_TO` | `person-*` o `fund-untracked` → `fund-*` | Filtro Donation.sede_id |

- [ ] Edges sólo se materializan si **ambos endpoints** están en `seen` (no crean nodos huérfanos nuevos por aristas)
- [ ] `seen` deduplica por `id` exacto — un nodo referenciado por dos resolvers no se duplica

### Permisos

- [ ] Sin token → 401 (FastAPI default `get_current_user`)
- [ ] Con token de cualquier usuario activo → 200, filtrado por su sede
- [ ] Cross-sede no se valida con 403: usa 404 (contrato uniforme con CRM/Projects)

### Meta payload

- [ ] `meta.counts.nodes`, `meta.counts.edges`, `meta.counts.courses`, `meta.counts.people`, `meta.counts.assets` siempre presentes
- [ ] `meta.counts.assets == 0` cuando `models.AssetItem` no está registrado (verificación directa del contrato)
- [ ] `meta.pagination.limit`, `meta.pagination.offset`, `meta.pagination.total_nodes`, `meta.pagination.returned_nodes` siempre presentes en snapshot
- [ ] `meta.requested_by` siempre presente = `str(user.id)`
- [ ] `meta.limit` siempre presente en connections

---

## Frontend

> Vista actual: `frontend/src/app/plataforma/graph/`

- [ ] Página `/plataforma/graph` carga sin errores de consola
- [ ] Visualización se actualiza al cambiar filtros (`types`, `limit`, `offset`)
- [ ] Sin errores 401/403/500 al cargar
- [ ] Estados vacíos manejados (snapshot sin nodos, connections sin aristas)
- [ ] Hover/click en nodo no rompe con type desconocido

---

## Tests

### Suite dedicada (2026-07-19)

```bash
./venv/bin/python -m pytest tests/test_graph_api.py -v --no-cov
```

Esperado: **5/5 PASSED**

- [ ] `test_graph_snapshot` → 200 + shape `{nodes, edges, meta}` + sin nodos `type="asset"` (cuando AssetItem no registrado)
- [ ] `test_graph_snapshot_with_pagination` → `meta.pagination.limit == 5`
- [ ] `test_graph_snapshot_with_types` → 200 con filter `types=persona`
- [ ] `test_graph_connections` → primer nodo tiene edge analysis funcional O rama 404 con dummy-id
- [ ] `test_graph_connections_404` → `detail == "Node not found"`

### Contrato graceful degradation (asserts nuevos)

- [ ] `assert all(n["type"] != "asset" for n in data["nodes"])` presente en **4 de 5 tests** (snapshot, snapshot_with_pagination, snapshot_with_types, connections)
- [ ] Si un futuro PR reintroduce hard-import de `models.AssetItem` en `_asset_nodes` ⇒ los 4 tests fallan loudly con `AssertionError` específico

### Smoke heredado

```bash
./venv/bin/python scripts/test_fase3_quality.py
```

- [ ] Smoke ejecuta sin importar el módulo `AssetItem`
- [ ] No errors ni warnings deprecation nuevos

### Smoke canónico propio

> **Pendiente (PEND-GRAPH-001):** crear `scripts/test_graph_quality.py` para evitar la dependencia heredada de Fase 3.

---

## Roles mínimos

| Rol | Esperado |
|---|---|
| ADMINISTRADOR | snapshot completo de su sede |
| GESTOR | snapshot completo de su sede |
| LECTOR | snapshot completo de su sede (lectura, no mutación) |

> El módulo Graph es **sólo lectura**. No hay gate por rol más allá de autenticación básica (`get_current_user`); el aislamiento es por sede, no por rol.

---

## Network/API

Para cada endpoint tocado:

- [ ] request sale por `/api/graph`
- [ ] Bearer token presente
- [ ] respuesta contiene `meta.requested_by == str(user.id)`
- [ ] sin errores 4xx no explicados en consola del navegador
- [ ] latencia aceptable: snapshot con 1500 nodos < 2s en CI

---

## Consola del navegador

No cerrar tarea si aparece:

- `401 Unauthorized` no explicado
- `403 Forbidden` (no aplica: el módulo no usa 403; sólo 401 y 404)
- `404` en `_next/static`
- `500 Internal Server Error`
- errores de hidratación React
- `TypeError` por shape inesperada (especialmente `data.meta.pagination` undefined)

---

## Criterio de cierre

Una tarea de Graph queda cerrada cuando:

1. ✅ `pytest tests/test_graph_api.py` → 5/5 PASSED con `--no-cov`; con cobertura global, el comportamiento individual es correcto aunque el gate global pueda estar rojo por deuda no relacionada (ver §Pendientes).
2. ✅ Smoke heredado (`scripts/test_fase3_quality.py`) corre sin nuevos warnings.
3. ✅ Si cambia el contrato de `/api/graph/snapshot` o `/api/graph/connections`, `ESTADO_GRAPH.md` y este checklist se actualizan.
4. ✅ Si se añade/quita un resolver o un edge type, los 4 asserts de `assert all(... != "asset")` se replican para el nuevo tipo o se mantienen si no aplica.
5. ✅ Si se añade graceful degradation para otro modelo, `_has_model("NuevoModelo") is False` queda anclado en `tests/test_services_final_push.py` (PEND-GRAPH-002).
6. ✅ El commit incluye solo cambios del módulo Graph (no混入 a CRM, Academy, etc.).

---

## Pendientes QA / backlog

- `PEND-GRAPH-001` Crear `scripts/test_graph_quality.py` (smoke canónico propio, sustituye dependencia de Fase 3).
- `PEND-GRAPH-002` Añadir `test_has_model_asset_item_missing` en `tests/test_services_final_push.py` (anclar `_has_model("AssetItem") is False` en el fixture actual; detecta si la semántica del helper cambia en futuro).
- `PEND-GRAPH-003` Crear `docs/GRAPH_API_CONTRACTS.md` (documentar formalmente los 2 endpoints, query params, respuestas, multi-tenant, graceful degradation).
- `PEND-GRAPH-004` Crear `docs/GRAPH_RBAC_MATRIX.md` (justificar scope per-sede, no per-rol; comportamiento cross-sede).
- `PEND-GRAPH-005a` Definir política arquitectónica: ¿graceful degradation universelle (todos los modelos opcionales) vs guard explícito por modelo crítico? Decisión que requiere input de plataforma compartida (afecta a otros servicios que importan `models`).
- `PEND-GRAPH-005b` (bloqueado por `PEND-GRAPH-005a`) Una vez decidida la política, documentar formalmente qué modelos son críticos vs opcionales para Graph (matriz de criticidad por dominio).
- `PEND-GRAPH-006` Investigar y decidir el comportamiento correcto del módulo cuando `user.sede_id == None` (vista global sin filtro vs 401/403). Hoy es comportamiento implícito sin contrato documentado; ver §Multi-tenant arriba.

## Cerrado recientemente

- `DONE-GRAPH-ASSETITEM-GUARD-001` cerrado el 2026-07-19 con guardia `_has_model("AssetItem")` en `_asset_nodes`, removidos 5 `@pytest.mark.xfail` en `tests/test_graph_api.py` y añadidos 4 asserts `assert all(n["type"] != "asset" ...)` para lock-in del contrato. **5/5 tests PASSED**.
