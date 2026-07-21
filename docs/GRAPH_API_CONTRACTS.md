# Contratos API — Módulo Graph

> **Objetivo:** fijar el contrato operativo real de `/api/graph` para frontend, tests y mantenimiento. Este documento describe los 2 endpoints del módulo después del fix de graceful degradation para `models.AssetItem` (2026-07-19, cierre de `DONE-GRAPH-ASSETITEM-GUARD-001`).
>
> **Fecha de verificación:** 2026-07-19
> **Fuente de verdad:** código en `backend/api/graph.py`, `backend/services/knowledge_graph.py`, `backend/core/permissions.py`
> **Cierra:** `PEND-GRAPH-003`

## 1. Reglas generales

- **Prefijo backend:** `/api/graph`
- **Prefijo frontend** (vía `apiFetch`): `/graph`
- **Tag OpenAPI:** `graph`
- **Módulo de sólo lectura**: no hay mutaciones.
- Toda identidad de persona en el grafo se resuelve contra `personas.id` (ver `Persona` en `backend/models_crm.py`).
- Toda query respeta `sede_id` del usuario autenticado (Axioma 3). Ver `docs/ESTADO_GRAPH.md` para el contrato global de aislamiento.
- Los nodos de `_family_nodes` y `_project_nodes` se materializan sin guard (modelos críticos).
- Los nodos de `_asset_nodes` y los edges `MAINTENANCE` están bajo `_has_model` graceful degradation (ver §4.6) y se omiten silenciosamente si el modelo no está registrado.
- Cualquier nodo/edge referenciado pero no presente en `seen` se omite silenciosamente (no se materializan nodos huérfanos).

## 2. Modelo de acceso

El módulo Graph **no usa `require_module_access`**. Todas las rutas usan `get_current_user` (autenticación básica) más el aislamiento por sede:

| Acción | Guard | Aislamiento adicional |
|---|---|---|
| leer snapshot | `get_current_user` | filtro por `user.sede_id` en cada resolver |
| ver conexiones de un nodo | `get_current_user` | filtro por `user.sede_id` al construir el snapshot interno |

**Roles equivalentes:** ADMINISTRADOR / GESTOR / LECTOR tienen el mismo acceso de lectura (ver `docs/GRAPH_RBAC_MATRIX.md` para justificación). El aislamiento es **per-sede, no per-rol**.

**Comportamiento de cross-sede:** un nodo de `sede_b` solicitado desde un usuario de `sede_a` retorna `404` con `detail="Node not found"` (no `403`). Coherente con el contrato uniforme de CRM/Projects (`docs/PROJECTS_API_CONTRACTS.md §10`).

**Comportamiento de `user.sede_id == None`:** si `get_user_sede_id(db, current_user.id)` retorna `None`, **ningún** resolver aplica filtro de sede y el snapshot devuelve vista global sin error y sin 403/401. Contrato abierto (ver `PEND-GRAPH-006`).

## 3. Router canónico

Archivo: `backend/api/graph.py`

```python
router = APIRouter(prefix="/graph", tags=["graph"])
```

| Método | Ruta | Guard |
|---|---|---|
| `GET` | `/graph/snapshot` | `get_current_user` |
| `GET` | `/graph/connections/{node_id}` | `get_current_user` |

> El router se monta en `backend/app.py` con el resto de routers de plataforma.

## 4. `GET /api/graph/snapshot`

Devuelve una vista ligera del grafo de conocimiento combinando academy, CRM, proyectos, fondos y (opcionalmente) assets.

### 4.1 Query params

| Param | Tipo | Default | Validación backend | Rango efectivo |
|---|---|---|---|---|
| `limit` | `int` | `50` | `safe_limit = max(1, min(limit, 500))` | `[1, 500]` |
| `offset` | `int` | `0` | `safe_offset = max(offset, 0)` | `[0, ∞)` |
| `types` | `string \| None` | `None` | `s.split(",")` → `strip()` → `[t for t if t]` | Lista CSV de tipos válidos (`course, person, asset, fund, family, project`) |

> ⚠️ **Clamping silencioso:** valores fuera de rango no producen 4xx; se ajustan al rango efectivo (e.g. `?limit=99999` → `limit=500`, `?offset=-1` → `offset=0`).
>
> ⚠️ **`types` inválidos se ignoran:** un `types="__invalid,persona"` filtra sólo los válidos y devuelve `404` indirecto si el set resultante queda vacío (no `400`).

### 4.2 Hardening anti-DoS (`expanded_limit`)

El backend aplica un cap interno **por-resolver** antes de invocar el servicio:

```python
expanded_limit = min(safe_limit + safe_offset, 1500)
snapshot = build_graph_snapshot(db, limit=expanded_limit, types=type_list, sede_id=user_sede)
```

- Cota el **input** pasado a cada resolver (`1500` max). Esto previene DoS por paginación con offsets abusivos (e.g. `?limit=500&offset=100000` no degrada la query linealmente más allá de 1500).
- **No cota el total acumulado de nodos**, porque los resolvers no comparten cuota: cada uno consume su propio slice. Suma teórica con todos los resolvers poblados: `~4260` (person 1500 + course 750 + asset 750 + project 750 + family 500 + fund 10); `~3510` sin `AssetItem` (caso típico del test env tras el fix 2026-07-19).
- El slice `nodes[safe_offset : safe_offset + safe_limit]` sólo queda vacío cuando `safe_offset >= total_nodes` real, **no** cuando `safe_offset >= 1500`. Pedir `?offset=1500&limit=500` puede todavía devolver datos si el grafo está poblado.

### 4.3 Response shape (200)

```jsonc
{
  "nodes": [
    {
      "id": "person-<uuid>",
      "type": "person",
      "label": "Nombre Apellido",
      "detail": "email@example.com",
      "meta": {
        "status": "<spiritual_status>",
        "gender": "<gender>"
      }
    }
    // ...
  ],
  "edges": [
    {
      "from": "person-<uuid>",
      "to": "course-<uuid>",
      "relation": "ENROLLED_IN"
    }
    // ...
  ],
  "meta": {
    "counts": {
      "nodes": 0,        // len(nodes)
      "edges": 0,        // len(edges)
      "courses": 0,      // nodes con type == "course"
      "people": 0,       // nodes con type in {"person", "donor"}
      "assets": 0        // nodes con type == "asset" — 0 si AssetItem no registrado
    },
    "pagination": {
      "limit": 50,
      "offset": 0,
      "total_nodes": 0,  // len(nodes) ANTES del slicing
      "returned_nodes": 0 // len(nodes) DESPUÉS del slicing (= safe_limit)
    },
    "requested_by": "<str(user.id)>"
  }
}
```

> ⚠️ Las claves `meta.counts.assets` y `meta.counts.people/donor` reflejan **el estado del grafo post-resolver**, no un conteo de modelo base. Cuando `models.AssetItem` falta ⇒ `assets = 0` aunque la tabla exista (graceful degradation, ver §4.6).

### 4.4 Multi-tenant (Axioma 3)

```python
user_sede = get_user_sede_id(db, current_user.id)
```

- Si `user_sede is not None`: todas las queries internas filtran por sede (`Course.sede_id`, `Persona.sede_id`, `Project.sede_id`, `Donation.sede_id`, etc.).
- Si `user_sede is None`: vista global sin filtro (contrato abierto, `PEND-GRAPH-006`).
- Los edges `ENROLLED_IN` filtran adicionalmente con `JOIN Persona ON Enrollment.persona_id == Persona.id WHERE Persona.sede_id == user_sede` (defense-in-depth: evita aristas cross-sede aunque los nodos estén correctamente filtrados).
- Cross-sede no se valida con `403`: usa `404` (coherente con `PROJECTS_API_CONTRACTS §10`).

### 4.5 Resolvers y cuotas

| Tipo | Modelo SQLAlchemy | Cuota cuando `expanded_limit=1500` | Multi-tenant filter |
|---|---|---|---|
| `course` | `models.Course` | `limit // 2 = 750` | `Course.sede_id == user_sede` |
| `person` | `models.Persona` | `limit = 1500` | `Persona.sede_id == user_sede` |
| `asset` | `models.AssetItem` | `limit // 2 = 750` (o `[]` si modelo ausente) | `AssetItem.sede_id == user_sede` |
| `fund` | `models.Fund` | `limit = 10` (hardcoded) | `Fund.sede_id == user_sede` |
| `family` | `models.Family` | `limit // 3 = 500` | JOIN con `Persona.sede_id == user_sede` |
| `project` | `models.Project` | `limit // 2 = 750` | `Project.sede_id == user_sede` |

> **Total teórico con todos los resolvers = ~4260 nodos.** Ver §4.2 para el cap anti-DoS.

### 4.6 Graceful degradation (`_asset_nodes`)

Contrato introducido en `DONE-GRAPH-ASSETITEM-GUARD-001` (2026-07-19):

```python
# backend/services/knowledge_graph.py:_asset_nodes
if not _has_model("AssetItem"):
    return []
```

**Efecto cascada al faltar `models.AssetItem`:**

- `_asset_nodes` retorna `[]` (no `AttributeError`).
- No se materializan nodos `type="asset"`.
- El bloque edges `MAINTENANCE` (más abajo en el archivo) usa el guard `if _has_model("MaintenanceLog") and _has_model("AssetItem")` (**AND lógico**, no OR), por lo que tampoco aparecen nodos `type="maintenance_log"` ni aristas `MAINTENANCE`.
- `meta.counts.assets == 0` (lock directo del contrato).
- El log emite **un único warning** por modelo ausente por proceso (`_warned_missing_models` cache en `knowledge_graph.py`); dos llamadas seguidas con el mismo modelo ausente producen un único warning — no spam en producción.

**Cobertura:** los 4 asserts añadidos en `tests/test_graph_api.py` (`assert all(n["type"] != "asset" for n in data["nodes"])`) lock-in este contrato contra futuras regresiones.

### 4.7 Códigos esperados (snapshot)

| Código | Cuándo |
|---|---|
| `200` | Respuesta normal (incluyendo snapshot vacío) |
| `401` | Sin token o token inválido (`get_current_user`) |
| `500` | Crash en un resolver crítico (`Course`, `Persona`, `Fund`, `Family`, `Project`) — ver §5 |

### 4.8 Edge types materializados

| Edge | Source → Target | Filtro multi-tenant | Dependencia |
|---|---|---|---|
| `ENROLLED_IN` | `person-*` → `course-*` | JOIN sobre `Persona.sede_id` | `Enrollment` + `Course` + `Persona` |
| `MAINTENANCE` | `asset-*` → `maintenance-*` | JOIN sobre `AssetItem.sede_id` | `MaintenanceLog` + `AssetItem` (graceful) |
| `BELONGS_TO_FAMILY` | `person-*` → `family-*` | Filtro `Persona.sede_id` | `Family` + `Persona` |
| `HAS_TASK` | `project-*` → `task-*` | JOIN sobre `Project.sede_id` | `ProjectTask` + `Project` |
| `DONATED_TO` | `person-*` o `fund-untracked` → `fund-*` | Filtro `Donation.sede_id` | `Donation` + `Fund` (con `persona_id` opcional) |

> Una arista sólo se materializa si **ambos endpoints** están ya en `seen` (no se crean nodos huérfanos nuevos por aristas). Excepción: `DONATED_TO` puede crear nodo `type="donor"` para la persona donante si no estaba en el grafo (incrementa `meta.counts.people`).

## 5. `GET /api/graph/connections/{node_id}`

Devuelve el nodo solicitado + aristas entrantes/salientes + nodos relacionados, todo del snapshot subyacente (filtrado por sede).

### 5.1 Path params

| Param | Tipo | Validación |
|---|---|---|
| `node_id` | `string` | Comparado con `node.get("id")` en el snapshot; 404 si no se encuentra |

> ⚠️ El endpoint **no** valida que `node_id` siga un patrón específico (`person-<uuid>`, `course-<uuid>`, etc.). Cualquier string que aparezca como `id` en el snapshot puede ser consultado.

### 5.2 Query params

| Param | Tipo | Default | Validación | Rango efectivo |
|---|---|---|---|---|
| `limit` | `int` | `100` | `safe_limit = max(1, min(limit, 500))` | `[1, 500]` |

### 5.3 Hardening interno

```python
snapshot = build_graph_snapshot(db, limit=1500, sede_id=user_sede)
```

- `limit=1500` es fijo (no tomado del query param); permite resolver el nodo pedido más sus aristas sin cap por resolver.
- Las aristas y nodos relacionados se extraen en memoria (no hay segunda query).
- Multi-tenant idéntico a snapshot (§4.4).

### 5.4 Response shape (200)

```jsonc
{
  "node": {
    "id": "person-<uuid>",
    "type": "person",
    "label": "Nombre Apellido",
    "detail": "email@example.com",
    "meta": { /* ... */ }
  },
  "incoming": [
    {
      "from": "person-<uuid>",
      "to": "<this-node-id>",
      "relation": "ENROLLED_IN"
    }
    // máximo safe_limit items
  ],
  "outgoing": [
    {
      "from": "<this-node-id>",
      "to": "course-<uuid>",
      "relation": "ENROLLED_IN"
    }
    // máximo safe_limit items
  ],
  "related_nodes": [
    // nodos cuyos id aparecen en incoming.from ∪ outgoing.to
    // cardinalidad máxima: |related_nodes| ≤ 2 * safe_limit
    // (unión de to's + from's; cada related_node tiene ≥1 edge visible)
  ],
  "meta": {
    "requested_by": "<str(user.id)>",
    "limit": 100
  }
}
```

> **Asimetría de cardinalidad:** `incoming` y `outgoing` se truncan individualmente a `safe_limit` cada uno, pero `related_nodes` se computa por la **unión** de los `to`/`from` de ambos, así que `|related_nodes| ≤ 2 * safe_limit`. No hay divergencia de visibilidad: cada related_node está anclado a ≥1 edge presente en `incoming` u `outgoing` (por construcción, los ids vienen de los campos `to`/`from` de los edges ya truncados).

### 5.5 Response shape (404)

```jsonc
{
  "detail": "Node not found"
}
```

### 5.6 Códigos esperados (connections)

| Código | Cuándo |
|---|---|
| `200` | Nodo encontrado en snapshot del actor |
| `401` | Sin token o token inválido |
| `404` | `node_id` no aparece en el snapshot (existe en otra sede, no existe, o fue filtrado por tipo) |
| `500` | Crash en un resolver crítico durante la construcción del snapshot interno |

## 6. Ejemplos de uso

### 6.1 Snapshot básico

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8001/api/graph/snapshot"
```

Devuelve hasta 50 nodos (default) y sus aristas dentro de la sede del actor.

### 6.2 Snapshot paginado y filtrado por tipo

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8001/api/graph/snapshot?types=course,person&limit=100&offset=50"
```

- `types=course,person` → sólo nodos de esos dos resolvers.
- `limit=100` → safe_limit=100; `offset=50` → safe_offset=50.
- `expanded_limit = min(150, 1500) = 150`.
- Cuota resultante: courses 75 + persons 150 + 0 en resto = **225 nodos teóricos** antes del slicing.

### 6.3 Conexiones de un nodo

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8001/api/graph/connections/person-7f8e9c18-86aa-4eaf-a458-62ea0ab3a76b"
```

Devuelve el nodo + aristas entrantes/salientes + nodos relacionados (cohorte de la sede).

## 7. Hardening cruzado (helpers de Axioma 3)

Más allá de los guards documentados en §2, el servicio `build_graph_snapshot` aplica varias defensas adicionales **dentro** del snapshot:

### 7.1 `seen` deduplication

```python
seen: Set[str] = set()
for resolver in resolvers.values():
    for node in resolver():
        if node["id"] not in seen:
            nodes.append(node)
            seen.add(node["id"])
```

- Un nodo referenciado por dos resolvers no se duplica.
- Una arista con `from` o `to` no presente en `seen` se omite silenciosamente.

### 7.2 Filtros defense-in-depth

Cada query de edges aplica un segundo filtro de sede incluso cuando el resolver ya filtró:

| Query | Filtro principal | Filtro secundario |
|---|---|---|
| `Enrollment` | (nodos visibles) | `JOIN Persona.sede_id` |
| `ProjectTask` | `Project.sede_id` (resolvers) | `JOIN Project.sede_id` (edges) |
| `Donation` | (nodos visibles) | `Donation.sede_id` directo |
| `MaintenanceLog` | `AssetItem.sede_id` (graceful) | (mismo) |

### 7.3 `_has_model` cache de warnings

`_warned_missing_models: Set[str]` evita spam en logs cuando un modelo falta en runtime. Ver `DONE-GRAPH-ASSETITEM-GUARD-001`.

## 8. Asimetrías y políticas formalizadas

1. **Cobertura de graceful degradation: sólo `asset`** (post 2026-07-19). Otros resolvers (`course`, `person`, `fund`, `family`, `project`) **crashean** si su modelo falta, porque son críticos para el dominio. Esto es deliberado y consistente con cómo `ESTADO_GRAPH.md` define criticidad por modelo.
2. **`types` no produce `400`** en input inválido: se filtra silenciosamente.
3. **`limit` y `offset` clampean silenciosamente** sin `4xx`. Coherente con el resto del módulo `pagination` del backend.
4. **`meta.counts.assets == 0`** es el contrato observable de graceful degradation, no un bug (ver §4.6).
5. **`expanded_limit` no es un cap de nodos totales** (§4.2). Confundir el cap con el total es un error de interpretación.
6. **Tamaño del snapshot sin cap real** — los nodos contadores `{courses, people, assets}` suman `nodes` pero pueden divergir por `donor` (ver §4.8 nota sobre `DONATED_TO`). `nodes` es la fuente de verdad.

## 9. Códigos de error consolidados

| Código | Endpoint | Causa |
|---|---|---|
| `200` | ambos | respuesta exitosa (incluyendo snapshot vacío) |
| `401` | ambos | sin token o token inválido |
| `404` | `/connections/{node_id}` | nodo no encontrado en snapshot (cross-sede, filtrado por tipo, o inexistente) |
| `500` | ambos | crash en resolver crítico (revisar logs) |

> El módulo **no usa `403`** — coherente con el contrato `PROJECTS_API_CONTRACTS §10`.

## 10. Pendientes / artefactos relacionados

| ID | Estado | Descripción |
|---|---|---|
| `PEND-GRAPH-001` | abierto | Crear `scripts/test_graph_quality.py` (smoke canónico propio). |
| `PEND-GRAPH-002` | abierto | Añadir `test_has_model_asset_item_missing` en `tests/test_services_final_push.py`. |
| **`PEND-GRAPH-003`** | **cerrado por este doc** | Crear `docs/GRAPH_API_CONTRACTS.md`. |
| `PEND-GRAPH-004` | abierto | Crear `docs/GRAPH_RBAC_MATRIX.md` (justificar scope per-sede, no per-rol). |
| `PEND-GRAPH-005a` | abierto | Política arquitectónica: graceful degradation universal vs guard explícito por modelo crítico. |
| `PEND-GRAPH-005b` | bloqueado | Matriz de criticidad por modelo para Graph (post-005a). |
| `PEND-GRAPH-006` | abierto | Decidir comportamiento correcto cuando `user.sede_id == None`. |

## 11. Cerrado recientemente

- `DONE-GRAPH-ASSETITEM-GUARD-001` (2026-07-19): guardia `_has_model("AssetItem")` en `_asset_nodes`, 5 `@pytest.mark.xfail` removidos de `tests/test_graph_api.py`, 4 asserts `assert all(n["type"] != "asset" ...)` añadidos para lock-in del contrato. **5/5 tests PASSED**.

## 12. Validación recomendada

```bash
# Suite dedicada
cd /root/ccf
./venv/bin/python -m pytest tests/test_graph_api.py -v --no-cov

# Smoke heredado (a sustituir por PEND-GRAPH-001)
./venv/bin/python scripts/test_fase3_quality.py
```

Salida esperada post-fix:

```
tests/test_graph_api.py::test_graph_snapshot                   PASSED
tests/test_graph_api.py::test_graph_snapshot_with_pagination   PASSED
tests/test_graph_api.py::test_graph_snapshot_with_types        PASSED
tests/test_graph_api.py::test_graph_connections                PASSED
tests/test_graph_api.py::test_graph_connections_404            PASSED
5 passed in <5s
```

---

**Documentos relacionados:**

- Estado del módulo: `docs/ESTADO_GRAPH.md`
- QA checklist: `docs/GRAPH_QA_CHECKLIST.md`
- RBAC matrix (pendiente): `docs/GRAPH_RBAC_MATRIX.md`
- Multi-tenant global: `docs/ESTADO_GRAPH.md §Multi-tenant`
