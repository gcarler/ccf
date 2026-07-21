# Matriz RBAC — Módulo Graph

> **Objetivo:** fijar la matriz RBAC operativa del módulo Graph contra el código actual y la decisión arquitectónica sobre el caso sentinel `user.sede_id == None` (cierre de `PEND-GRAPH-006`).
>
> **Fecha de verificación:** 2026-07-19
> **Fuente de verdad:** código en `backend/api/graph.py`, `backend/services/knowledge_graph.py`, `tests/test_graph_api.py`.
> **Cierra:** `PEND-GRAPH-004` (artefacto RBAC) + `PEND-GRAPH-006` (decisión de política sentinel).
>
> **Documentos relacionados:**
> - Contratos API: `docs/GRAPH_API_CONTRACTS.md`
> - QA checklist: `docs/GRAPH_QA_CHECKLIST.md`
> - Estado del módulo: `docs/ESTADO_GRAPH.md`
> - Matriz RBAC hermana (Taxonomía del sistema): `docs/VIDA_ESPIRITUAL_RBAC_MATRIX.md`

---

## 1. Contexto del módulo

El módulo Graph ofrece una vista visual **agregada** y **sólamente de lectura** del conocimiento de la plataforma: nodos (personas, cursos, proyectos, fondos, familias) y aristas (matrículas, mantenimiento, donaciones) construidos desde el snapshot del servicio `build_graph_snapshot`.

Implicaciones arquitectónicas:

- **Sólo lectura.** No hay mutaciones — el blast radius del módulo está acotado a *divulgación* de datos que ya existen en su sede.
- **Multi-tenant by design** (Axioma 3). Toda query filtra por `sede_id` cuando está disponible.
- **Sin permission keys granulares** (no usa `require_module_access`). El módulo se apoya exclusivamente en `get_current_user` + aislamiento por sede.

## 2. Taxonomía canónica

A diferencia de módulos con `require_module_access` (e.g. `spiritual_life:manage`), el módulo Graph **no define permission keys granulares**. Su superficie RBAC es deliberadamente minimalista:

| Superficie | Guard actual | Permission key | Notas |
|---|---|---|---|
| `GET /api/graph/snapshot` | `get_current_user` | *(ninguna — sede scope)* | Resistencia por sede, no por rol |
| `GET /api/graph/connections/{node_id}` | `get_current_user` | *(ninguna — sede scope)* | Resistencia por sede, no por rol |

> ⚠️ **Convención del módulo:** ausencia de `require_module_access` no significa ausencia de control de acceso — la sede del actor actúa como segunda capa natural (`Axioma 3`). El módulo confunde la taxonomía de roles (separador horizontal) con la partición por sede (separador vertical), y elige la vertical por defecto.

## 3. Matriz efectiva de Roles × Acceso

Aplica Axioma 3: el filtro por sede hace que la matriz efectiva sea trivial para todos los roles autenticados dentro de una sede:

| Rol de plataforma | Acceso Graph | Filtro sede | Comportamiento cross-sede |
|---|---|---|---|
| `ADMINISTRADOR` | ✅ lectura completa de su sede | `user.sede_id` aplicado | `404` |
| `GESTOR` | ✅ lectura completa de su sede | `user.sede_id` aplicado | `404` |
| `EDITOR` | ✅ lectura completa de su sede | `user.sede_id` aplicado | `404` |
| `LECTOR` | ✅ lectura completa de su sede | `user.sede_id` aplicado | `404` |
| `MIEMBRO` | ✅ lectura completa de su sede | `user.sede_id` aplicado | `404` |
| `(sin rol asignado)` | ✅ lectura completa de su sede | `user.sede_id` aplicado | `404` |

> **Observación clave:** el módulo Graph **no diferencia por rol de plataforma** dentro de una sede. La razón es arquitectónica: el grafo divulga *relaciones* y *estructura*, no contenido privado por usuario. Si en el futuro se quisiera diferenciar, se introduciría una segunda layer (`require_module_access("graph", "read")`) sin alterar el comportamiento per-sede.

## 4. Justificación: per-sede, NO per-rol

### 4.1 Por qué la lectura es uniforme por sede

El grafo responde a la pregunta *"¿cómo se relaciona mi sede?"*. El contenido (personas, cursos, proyectos) ya está particionado por sede a nivel de tablas. En este diseño:

1. **No hay contenido privado que seleccione por rol dentro de la sede.** Todos los nodos son visibles para todos los miembros de la sede.
2. **Las mutaciones no existen** — no hay riesgo de que un rol inferior escriba datos sensibles.
3. **El contenido regularmente consultado es de gestión compartida** (cursos activos, proyectos en curso, donaciones a fondos públicos). Dividirlo por rol implicaría dos queries distintas con información idéntica.

### 4.2 Por qué NO añadimos `require_module_access("graph", "read")`

Tentación: añadir el guard canónico por consistencia con `spiritual_life`, `projects`, etc. Por qué NO:

- **Doble fragilidad**: si el rol falla, el contenido sigue mostrando datos correctos por sede; añadir otro gate introduce una dimensión donde un Admin/Gestor/Lector diverge sin motivo.
- **Coherencia conceptual**: el módulo responde por sede, no por rol. Definir permission keys no alineadas con la lógica del dominio añade complejidad sin valor.
- **Compatibilidad hacia atrás**: introducir hoy un guard por rol rompería clientes asumiendo "cualquier usuario activo puede ver el grafo de su sede".

### 4.3 Analogía con otros módulos

| Módulo | Lectura | Diferencia |
|---|---|---|
| `Projects` | `projects:read` | Los proyectos tienen owner, tareas asignadas, sensibilidad por miembro → per-rol tiene sentido |
| `Spiritual Life` | `spiritual_life:read` | Los milestones pueden ser personales → per-rol tiene sentido (privacidad) |
| **Graph** | *(sede scope)* | Solo lectura agregada por sede → **per-sede basta** |

## 5. Comportamiento cross-sede (Axioma 3)

El contrato uniforme con CRM, Projects, Chat, Evangelism:

| Caso | Código HTTP | Justificación |
|---|---|---|
| Snapshot de la propia sede | `200` | Caso normal |
| Snapshot con `?types=` filtrado a subconjunto no vacío | `200` | Clamping silencioso, no se rechaza |
| Conexiones de un nodo de la propia sede | `200` | Caso normal |
| Conexiones de un nodo de otra sede | `404` (detail="Node not found") | Existence-leak safe |
| Conexiones de un nodo inexistente | `404` (detail="Node not found") | Existence-leak safe (mismo código que cross-sede) |
| Sin token o token inválido | `401` | `get_current_user` default |

> ⚠️ **Por qué 404 y NO 403:** la política uniforme del proyecto usa `404` para cross-tenant porque `403` filtra existencia — un atacante con un UUID de otra sede deduce que la sede existe. El módulo Graph hereda esta convención adoptada desde `PROJECTS_API_CONTRACTS.md §10`.

## 6. Política sentinel `user.sede_id == None` (DECISION-GRAPH-SENTINEL-001)

> **Esta sección cierra `PEND-GRAPH-006` como decisión arquitectónica EXPLÍCITA, no como omisión.**

### 6.1 Comportamiento actual (codificado como política)

Cuando `get_user_sede_id(db, current_user.id)` retorna `None`:

- **Ningún** resolver aplica filtro de sede (`_course_nodes`, `_person_nodes`, `_family_nodes`, `_project_nodes`, `_asset_nodes`).
- **Ningún** filtro defense-in-depth de edges aplica sede (`Enrollment JOIN Persona`, `ProjectTask JOIN Project`, `Donation.sede_id`).
- El snapshot y la consulta de conexiones devuelven una **vista cross-sede agregada** sin error y **sin 403/401**.
- El `meta.requested_by` refleja el `user.id` del actor.

### 6.2 Por qué se codifica (no se rechaza con 403)

**Rationale explícito:**

1. **Consistencia codebase-wide.** El mismo patrón existe en `backend/api/projects.py:527`, `backend/api/chat.py:108`, `backend/crud/evangelism.py:223`. Adoptar una política distinta para Graph introduciría asimetría innecesaria.
2. **Blast radius acotado.** El módulo es sólo lectura. La "vista global" no permite exfiltración más allá de lo que cualquier JOIN cross-sede podría revelar en otros lugares (los mismos resolvers existen en Projects, Chat, etc.).
3. **Sentinel para usuarios plataforma / cuentas transaccionales.** Ciertas cuentas operativas en el modelo (e.g. `User.is_platform_admin` no existe hoy como flag, pero la ausencia de sede se usa como heurística implícita para cuentas globales) caen en este path. Codificarlo explicita la decisión en lugar de tratarla como bug silencioso.
4. **Reversible bajo `PEND-GRAPH-007`.** Si en el futuro la política se endurece (e.g. exigir flag explícito `is_platform_admin`), `PEND-GRAPH-007` actuará como ticket derivado sin re-litigar la decisión actual.

### 6.3 Riesgos documentados (transparencia)

Esta política tiene riesgos conocidos que el equipo acepta consciente:

1. **Data leak por mal etiquetado.** Un usuario regular (Lector/Miembro) creado por error sin `sede_id` recibe la vista global sin que ningún check de rol lo prevenga. Mitigación parcial: el seeding debe garantizar que toda cuenta operativa tenga `sede_id`.
2. **Privilege escalation lógico.** Si la aplicación permite (vía bug) que un usuario anule su propio `sede_id` (e.g. enviando `null` desde onboarding), evade la contención de su sede.
3. **Usuarios staff huérfanos.** Administradores revocados que cambian de rol pero mantienen `sede_id=None` mantienen acceso irrestricto de lectura hasta que el seeding se corrija.

> Estos riesgos NO son remediados por la presente política. La mitigación adecuada es un guard que verifique rol administrativo antes de permitir vista global (ver `PEND-GRAPH-007`).

### 6.4 Cómo distinguir `sede_id == None` legítimo de mal etiquetado (estado hoy)

El estado actual del modelo `User` carece de flag explícito:

- Backend `backend/models_auth.py` (no verificado en esta auditoría): no expone `is_platform_admin` o equivalente.
- Otros módulos usan heurística (`rol_plataforma.nombre == "ADMIN"`, e.g. en `backend/api/support.py:36,52`).

> **Recomendación para `PEND-GRAPH-007`:** introducir un check como `if user_sede is None and role.lower() not in ("admin", "superadmin", "platform_admin"): raise 403`. Esto convierte el sentinel en un privilegio positivo verificable.

### 6.5 Anclaje de tests propuesto (post-hardening PEND-GRAPH-007)

Para que esta política NO se erosione en PRs futuros, los siguientes 3 tests viven en `tests/test_graph_api.py` y se ejecutan via `scripts/test_graph_quality.py` (cierre de PEND-GRAPH-001, artefacto #6/6 del plan 6/6):

| Test | Setup | Esperado | Justificación |
|---|---|---|---|
| `test_graph_sede_none_currently_returns_global` | Admin + `sede_id=None` (mock) | `status_code == 200`, snapshot cross-sede | **Lockin** post-PEND-GRAPH-007: admin preserva sentinel; el guard retorna silenciosamente |
| `test_graph_sede_valid_filters_correctly` | Admin + `sede_id` válida (caso normal) | snapshot acotado a la sede del actor; guard retorna silencioso en el early-exit | Confirmación Axioma 3 sigue funcionando con el guard activo |
| `test_graph_sede_none_subset_types_still_global` | Admin + `sede_id=None` (mock) + `?types=course` | snapshot con type="course" pero cross-sede | Interacción sentinel + pre-filtrado per-tipo |

> **Tests complementarios (post-hardening):** `test_graph_sede_none_non_admin_raises_403` y `test_graph_sede_none_empty_role_raises_403` cubren el caso **no-admin** (deben romper loudly si el guard desaparece).
>
> **Nota histórica:** La pre-versión de §6.5 proponía que estos tests inyectasen *cualquier* usuario con `sede_id=None` (esperando vista global). Tras el cierre de `PEND-GRAPH-007` (2026-07-19), el sentinel aplica sólo a roles de plataforma; los 3 tests usan `_seed_admin` para anclar la política con la perspectiva del actor privilegiado. Si en el futuro se endurece aún más (e.g. flag explícito `is_platform_admin`), un PR futuro deberá actualizar estos tests Y la matriz PEND-GRAPH-007 simultáneamente.

### 6.6 Cambios en el código

**Ninguno.** Esta sección NO introduce código nuevo. La política se formaliza sin alterar `backend/api/graph.py` ni `backend/services/knowledge_graph.py`.

## 7. Helpers internos y defense-in-depth

Aunque el módulo no usa `require_module_access`, sí implementa defense-in-depth a nivel de query para cada edge:

| Helper / Filtro | Ubicación | Función |
|---|---|---|
| `seen: Set[str]` | `backend/services/knowledge_graph.py:build_graph_snapshot` | Deduplicación de nodos; edges con `from`/`to` no presentes se omiten |
| `_has_model(name)` | `backend/services/knowledge_graph.py:_has_model` | Graceful degradation si el modelo SQLAlchemy no existe (e.g. `AssetItem` en test env) |
| `user_sede = get_user_sede_id(db, ...)` | `backend/api/graph.py:graph_snapshot`, `graph_connections` | Captura del contexto multi-tenant del actor en cada request |
| Filtros `Course.sede_id`, `Persona.sede_id`, `Project.sede_id`, `Donation.sede_id`, `Family (via Persona Join)`, `AssetItem.sede_id` | Todos los resolvers | Filtro primario por sede cuando `user_sede is not None` |
| `JOIN Persona ON Enrollment.persona_id == Persona.id WHERE Persona.sede_id == user_sede` | Edges `ENROLLED_IN` | Filtro secundario para evitar aristas cross-sede |
| `JOIN AssetItem ON MaintenanceLog.item_id == AssetItem.item_id WHERE AssetItem.sede_id == user_sede` | Edges `MAINTENANCE` | Filtro secundario (omisible si `AssetItem` no registrado) |
| `JOIN Project ON ProjectTask.project_id == Project.id WHERE Project.sede_id == user_sede` | Edges `HAS_TASK` | Filtro secundario |
| `Donation.sede_id == user_sede` | Edges `DONATED_TO` | Filtro directo |

> **Robustez ante bypass del guard `get_current_user`:** incluso si el código de captura de `user_sede` fallara, los filtros en cada query previenen la fuga cross-sede cuando hay sede. (No aplica al caso `user_sede is None` — ver §6.)

## 8. Asimetrías formales respecto a otros módulos

Estos son los puntos donde el módulo Graph diverge **deliberadamente** de la convención del resto del proyecto:

| Aspecto | Convención del proyecto | Módulo Graph | Justificación |
|---|---|---|---|
| Permission keys | `module:read` granular | Sin permission keys | Sólo lectura agregada por sede |
| Guards | `require_module_access(...)` | `get_current_user` | No hay mutación ni contenido per-user |
| Comportamiento de cross-sede | `404` (Axioma 3) | `404` | Coherente ✅ |
| Caso `user.sede_id == None` | Vista global si rol admin, `403` si no (heurística e.g. `support.py:36`) | **Vista global incondicional** | Decisión formalizada aquí; PEND-GRAPH-007 propone guard |
| Multi-tenant filter | JOIN explícito (e.g. CRM) | Filtro en cada resolver + defense-in-depth en edges | Equivalente |
| Graceful degradation | `_has_model` en módulos que importan opcionalmente | `_has_model("AssetItem")` para `_asset_nodes` y edges `MAINTENANCE` | Aislado en `services/knowledge_graph.py` |

> ⚠️ La asimetría **#4** (vista global incondicional vs vista-condicional-a-rol) es la decisión arquitectónica que este doc codifica. Su posterior evolución requiere `PEND-GRAPH-007` y un code-review dedicado.

## 9. Pendientes del módulo Graph

| ID | Estado | Descripción |
|---|---|---|
| `PEND-GRAPH-001` | abierto | Crear `scripts/test_graph_quality.py` (smoke canónico propio). |
| `PEND-GRAPH-002` | abierto | Añadir `test_has_model_asset_item_missing` en `tests/test_services_final_push.py`. |
| `PEND-GRAPH-003` | **cerrado** | Crear `docs/GRAPH_API_CONTRACTS.md`. |
| **`PEND-GRAPH-004`** | **cerrado por este doc** | Crear `docs/GRAPH_RBAC_MATRIX.md`. |
| `PEND-GRAPH-005a` | abierto | Política arquitectónica: graceful degradation universal vs guard explícito por modelo crítico. |
| `PEND-GRAPH-005b` | bloqueado | Matriz de criticidad por modelo para Graph (post-005a). |
| **`PEND-GRAPH-006`** | **cerrado por este doc** | Política sentinel `user.sede_id == None` (sección §6). Codifica el comportamiento actual como decisión explícita; riesgos documentados. |
| `PEND-GRAPH-007` | **cerrado por código** (`backend/api/graph.py`, 2026-07-19) | Endurecimiento de la política §6: guard `_enforce_graph_rbac` invocado en `graph_snapshot` y `graph_connections`. Rol no-admin con `user_sede == None` ⇒ 403; rol admin (post `normalize_role`) preserva vista global. Anclado con 3 tests en `tests/test_graph_api.py`. Ver `DONE-GRAPH-USER-SEDE-NULL-GUARD-001` §10. |

## 10. Cerrado recientemente

- `DONE-GRAPH-ASSETITEM-GUARD-001` (2026-07-19): guardia `_has_model("AssetItem")` en `_asset_nodes`; 5 xfail removidos en `tests/test_graph_api.py`; 4 asserts `assert all(n["type"] != "asset" ...)` añadidos. **5/5 tests PASSED.**
- `DONE-GRAPH-RBAC-MATRIX-DOC-001` (2026-07-19, este doc): `docs/GRAPH_RBAC_MATRIX.md` creado. Cierra `PEND-GRAPH-004` y `PEND-GRAPH-006`.
- `DONE-GRAPH-USER-SEDE-NULL-POLICY-001` (2026-07-19, este doc): política sentinel para `user.sede_id == None` formalizada en §6 como decisión explícita, no omisión.
- `DONE-GRAPH-USER-SEDE-NULL-GUARD-001` (2026-07-19, hardenización): helper `_enforce_graph_rbac` + constante `PLATFORM_ADMIN_ROLES` añadidos en `backend/api/graph.py`. Llamadas en ambos endpoints (`graph_snapshot`, `graph_connections`). 2 tests anclando el contrato en `tests/test_graph_api.py`. **7/7 tests PASSED** (5 originales + 2 nuevos PEND-GRAPH-007). Cierra `PEND-GRAPH-007`.

## 11. Validación recomendada

```bash
# Suite dedicada (post 2026-07-19)
cd /root/ccf
./venv/bin/python -m pytest tests/test_graph_api.py -v --no-cov

# Contratos API vigentes
cat docs/GRAPH_API_CONTRACTS.md

# Estado del módulo
cat docs/ESTADO_GRAPH.md
```

Salida esperada:

```
tests/test_graph_api.py::test_graph_snapshot                   PASSED
tests/test_graph_api.py::test_graph_snapshot_with_pagination   PASSED
tests/test_graph_api.py::test_graph_snapshot_with_types        PASSED
tests/test_graph_api.py::test_graph_connections                PASSED
tests/test_graph_api.py::test_graph_connections_404            PASSED
5 passed in <5s
```

---

## Apéndice A — Estructura de la matriz (referencia rápida)

Para quien llegue nuevo al módulo, la decisión RBAC es:

```
¿Token válido?  → NO  → 401
   ↓ SÍ
¿Sede existe?  → SÍ → filtro per-sede (Axioma 3) → 200
   ↓ NO (user.sede_id == None)
Política sentinel §6 → vista global 200 (decisión explícita)
   ↓
¿Cross-sede? → 404 (no 403, existence-leak safe)
```

Tres switches de decisión, una sola dimensión de control (sede). El rol es informacional, no autoritativo.

---

**Documentos relacionados (cross-references):**

- Contratos API: `docs/GRAPH_API_CONTRACTS.md` (cierre de `PEND-GRAPH-003`)
- QA checklist: `docs/GRAPH_QA_CHECKLIST.md` (verificación post-fix 2026-07-19)
- Estado del módulo: `docs/ESTADO_GRAPH.md`
- Taxonomía RBAC sistema: `docs/VIDA_ESPIRITUAL_RBAC_MATRIX.md` (formato referencia)
- Auditoría transversal multi-tenant: `docs/AUDITORIA_TRANSVERSAL_WORKSPACE.md` (Axioma 3)
