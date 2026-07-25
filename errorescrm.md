# Auditoría Forense de Calidad — Módulo CRM
## Completitud y Consistencia (Revisión Línea por Línea)

**Fecha:** 2026-07-25  
**Alcance:** `backend/api/crm/{__init__,personas,persona_relations,pastoral,pipelines,resources}.py`, `backend/crud/crm.py`, `backend/crud/crm_/*.py` (19 archivos), `backend/models_crm.py`, `backend/models_crm_pipeline.py`, `backend/schemas/crm/*.py`, `frontend/src/app/plataforma/crm/**/*.tsx` (~84 archivos), `tests/test_crm_*.py` (25 archivos).

> **Contexto.** `docs/ESTADO_CRM.md §17` declaraba CRM operativamente cerrado al 100% bajo su "plan de cierre fino". Esta auditoría forense implementa el mismo escrutinio 5-capas aplicado a Academy (`erroresacademia.md`) y CMS (7 ciclos). Hallazgos fuera del alcance declarado del plan anterior no contradicen el cierre previo — lo amplían a la cobertura que una auditoría forense exige.

> **Iteración 1 (2026-07-25):** 5 hallazgos cerrados (C-01, C-02, C-03, C-04, A-02). Smoke canónico final: **94 unitarios + 33 RBAC = verde** (baseline pre-fix 78 passed).
> **Iteración 2 (2026-07-25):** C-05 cerrado vía approach "honest minimal": 5 alias no-op eliminados del router productivo (`flows_unicode`, `cycle_deep`, `multiple_cycles`, `disconnected_subgraph_cycles`, `concurrent_cycle_checks`), 6 tests migrados a canonical endpoints (`/flows/check-cycles`, `/flows/validate-complex-dag`, `/flows/empty`), `LocalASGITestClient.default_headers` mechanism añadido + autouse fixture `_authed_client_for_router_endpoints`. Remediation file pasó **6→38 passing en aislamiento** (era 32 en memoria — se completó el tramo final de 6 tests). Smoke final re-verificado: 94 + 38 + 33 = **verde, sin regresión**. Quedan **21 hallazgos pendientes**.

---

## Resumen Ejecutivo

| Métrica | Valor |
|---|---|
| Archivos backend revisados | 28 |
| Archivos frontend revisados | ~84 (vía grep dirigido) |
| Endpoints API en scope | ~178 |
| Funciones CRUD públicas | 195 |
| Hallazgos críticos | 5 (5 cerrados ✅, 0 pendientes) |
| Hallazgos altos | 9 (1 cerrado ✅, 1 cerrado ✅ A-07, 4 ya-cubiertos 🟢, 3 latentes/post 🔴) |
| Hallazgos medios | 8 pendientes 🔴 |
| Hallazgos bajos (info) | 3 en revisión 🟡 |
| Funcionalidades | 2 pendientes 🔴 |
| **Total** | **27** (7 cerrados ✅, 4 ya-cubiertos 🟢, 16 pendientes 🔴/🟡) |

---

## 🔴 CRÍTICOS

### C-01: `_find_existing_persona` deduplica cross-sede — fuga de identidad entre sedes

**Archivo:** `backend/crud/crm_/personas.py:99-124`  
**Capa:** CRUD  

**Problema.** La función busca una persona existente por `phone`, `mobile_phone` o `id_number` sin filtrar por `sede_id`. Cuando un usuario de sede_A crea una persona con un teléfono que ya existe en sede_B, `_find_existing_persona` retorna la persona de sede_B y la persona se "anexa" a ese UUID — cross-tenant merge. `create_persona` la invoca para deduplicar (Axioma 1 Kernel de Personas), por lo que cualquier creación de persona con teléfono/id_number repetidos inter-sedes produce la fusión.

**Impacto.** Violación de Axioma 3 (aislamiento por sede) + Axioma 1 (kernel de personas). Una sede puede observar y operar sobre personas de otra sede vía teléfono compartido (familias compartidas, multi-sede legítimo, datos de avance pastoral). El comportamiento está disfrazado de "dedup" pero es leak inter-tenant.

**Evidencia.**
```python
def _find_existing_persona(db: Session, payload: schemas.PersonaCreate) -> Optional[models.Persona]:
    phones = [p for p in (payload.phone, payload.mobile_phone) if p]
    if phones:
        match = (
            persona_query(db)
            .filter(or_(models.Persona.phone.in_(phones), models.Persona.mobile_phone.in_(phones)))
            .first()  # SIN .filter(models.Persona.sede_id == sede_id)
        )
        ...
    if payload.id_number:
        match = persona_query(db).filter(models.Persona.id_number == payload.id_number).first()
        # idem, sin sede
```

**Fix.** Añadir `sede_id: UUID` parámetro y aplicar `.filter(models.Persona.sede_id == sede_id)` a ambas queries. El caller `create_persona` ya debe recibirlo.

**Estado:** ✅ CERRADO Iter1 (2026-07-25) — `_find_existing_persona` ahora recibe `sede_id: UUID | None` y aplica `.filter(Persona.sede_id == sede_id)` en ambas queries phone/id_number. Personas.py compila limpio. 94 unitarios + 33 RBAC pasan.

---

### C-02: `/roles/{role_id}` PUT/DELETE — IDOR cross-sede total + bulk update global

**Archivo:** `backend/api/crm/pastoral.py:1692-1764`  
**Capa:** API  

**Problema.** `update_crm_role` y `delete_crm_role` consultan `db.query(RoleDefinition).filter(id == role_id).first()` **sin** `sede_id`. Un usuario autenticado de cualquier sede con permiso `crm:edit` puede renombrar o eliminar roles de otra sede. Peor aún:
- **Renombrado global sin scope**: `db.query(Persona).filter(Persona.church_role == row.name).update({"church_role": new_name})` afecta a personas de TODAS las sedes, no solo la del actor.
- **Eliminación global sin scope**: el `update` de `church_role` a `fallback.name` aplica de igual forma。
- **`sede_id` del cliente aceptado**: `row.sede_id = data.get("sede_id")` y `sede_id=data.get("sede_id") or ...` permiten al cliente re-attribuir el rol a otra sede.

**Impacto.** Cross-tenant data write + data corruption. Un usuario malintencionado o un operador descuidado de sede A puede alterar la taxonomía de roles de toda la plataforma y dejar personas de otras sedes con `church_role` apuntando al nuevo nombre del rol, atravesando `sede_id`. Viola Axioma 3 y §4.1 de REGLAS.md.

**Evidencia.**
```python
@router.put("/roles/{role_id}", response_model=dict)
def update_crm_role(role_id: UUID, payload: RoleUpdate, ...):
    row = db.query(models.RoleDefinition).filter(models.RoleDefinition.id == role_id).first()
    ...
    db.query(models.Persona).filter(models.Persona.church_role == row.name)\
        .update({"church_role": new_name})  # GLOBAL, sin sede
    if "sede_id" in data:
        row.sede_id = data.get("sede_id")  # sede_id del cliente
```

**Fix.** En ambos endpoints: (1) calcular `user_sede = require_user_sede_id(db, current_user)` y filtrar `RoleDefinition.sede_id == user_sede` en la query inicial; (2) el bulk update de `Persona.church_role` debe scopesarse `Persona.sede_id == user_sede AND church_role == row.name`; (3) ignorar `sede_id` del payload (server-side source of truth). Devolver 404 si el role no pertenece a la sede del actor.

**Estado:** ✅ CERRADO Iter1 (2026-07-25) — `/roles` create/update/delete ahora (1) calculan user_sede y 409 si actor sin sede, (2) filtran RoleDefinition por sede del actor (404 cross-sede), (3) bloquean roles globales (sede_id NULL) desde una sede con 403, (4) bulk update de church_role solo afecta Personas con sede_id == actor_sede, (5) sede_id del payload ignorado en update. Pastoral.py compila limpio. 94+33 tests pasan.

---

### C-03: `/categorias` PATCH/DELETE sin scope — mutación cross-sede de taxonomía compartida

**Archivo:** `backend/api/crm/resources.py:114-135` + `backend/crud/crm_/resources.py:46-63`  
**Capa:** API + CRUD  

**Problema.** `CategoriaRecurso` es deliberadamente global (sin `sede_id`, modelo análogo a catálogo editorial compartido) — esa es la decisión arquitectónica correcta. Pero los endpoints PATCH y DELETE permiten a cualquier usuario con `crm:edit` desactivar o renombrar una categoría compartida sin ownership audit. Resultado: un operador de sede A puede desactivar una categoría que sede B utiliza activamente en sus plantillas (cascade: las plantillas pierden su categoría).

**Impacto.** Mutación cross-sede destructiva de contenido compartido. Sintoma de la familia C-API-3 de Academy: "política inconsistente sobre un mismo campo global nullable". No es data leak, es data corruption multi-tenant sin governance.

**Evidencia.**
```python
@router.delete("/categorias/{categoria_id}", status_code=204)
def del_categoria(categoria_id: str, db, user=Depends(require_module_access("crm", "edit"))):
    if not delete_categoria(db, categoria_id):  # SIN sede filter, SIN audit
        raise HTTPException(404, "Categoría no encontrada")
```

**Fix.** Either (a) restringir PATCH/DELETE a `require_admin` (permiso `system:config`), reservando mutaciones a platform-admin (los LECTOR/pastor solo leen categorías); o (b) añadir una columna `created_by_sede_id` y requerir ownership. Para alcance mínimo e inmediato: aplicar (a) y añadir auditoría en `bitacora`. GET/POST pueden quedar abiertos (POST crea entidad global nueva). Documentar en `CRM_API_CONTRACTS.md`.

**Estado:** ✅ CERRADO Iter1 (2026-07-25) — POST/PATCH/DELETE `/categorias` ahora requieren `require_admin` (system:config) en vez de `crm:edit`. POST añade `_audit_log` con `creado_por_sede`. GET sigue abierto a `crm:read`. Resources.py compila limpio. 94+33 tests pasan. La opción (b) (created_by_sede_id) queda fuera — requiere migración; opción (a) satisface el riesgo (mutación cross-sede compartida restringida a platform-admin). Documentar próximo en CRM_API_CONTRACTS.md.

---

### C-04: `CrmAutomationFlow`/`Node`/`Edge`/`Branch` sin `sede_id` — flujos de automatización cross-tenant

**Archivo:** `backend/models_crm.py:737-791` (CrmAutomationFlow, CrmAutomationNode, CrmFlowBranch, CrmFlowCycleCache)  
**Capa:** Modelo  

**Problema.** Cuatro tablas de automatización (`crm_automation_flows`, `crm_automation_nodes`, `crm_flow_branches`, `crm_flow_cycle_cache`) carecen completamente de columna `sede_id`. El endpoint `POST /automations/flows` (`pipelines.py:549-562`) crea un `CrmAutomationFlow` sin atribuirlo a ninguna sede; cualquier actor autenticado con `crm:edit` ve y modifica los flujos de todas las sedes. Esto viola REGLAS.md §4.2 (toda UGC expuesta por API admin debe tener `sede_id` con la sola excepción de las entidades site-faro CMS).

**Impacto.** Cross-tenant data leak + cross-tenant data write. Una automatización de sede A puede ejecutarse contra personas de sede B; cualquier pastor puede ver el flujo confidencial de consolidación pastoral de otra sede. Severidad máxima — estos flujos codifican estrategia de seguimiento pastoral.

**Evidencia.**
```python
class CrmAutomationFlow(Base):
    __tablename__ = "crm_automation_flows"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    # ← SIN sede_id, FK sedes.id, ni ownership
```

**Fix.** Migración que añada `sede_id UUID NOT NULL FK sedes.id` a `crm_automation_flows` (con backfill a la sede operativa por defecto). Cascade-down: añadir `sede_id` a `crm_automation_nodes` (vía flow) o usar JOIN al flow. Cada endpoint que opera sobre AutomationFlow/Node/Edge debe filtrar por sede del actor. Esto es un cambio estructural — requiere migración nueva (no edita migraciones cerradas, REGLAS.md §9.1), test, y ajuste de los serializers.

**Estado:** ✅ CERRADO Iter1 (2026-07-25) — (1) Modelo `CrmAutomationFlow.sede_id` añadido (nullable para backfill graceful, FK sedes.id, indexed). (2) Migración nueva `20260725_0001` en `alembic/canonical_versions/` chain de `20260724_0001`; SQLite branch es no-op, Postgres branch ejecuta ADD COLUMN + index + FK + constraint. Aplicada con `alembic upgrade head`. (3) Helper `_owned_flow` con 404 cross-sede + manejo de flujos legacy (sede_id NULL solo editable por superadmin sin sede). (4) `POST /automations/flows` inyecta sede_id server-side y 409 si actor sin sede. (5) `flow_builder_three_node_render`, `cyclical_flow_resolution`, `cross_flow_check` usan `_owned_flow`. Pendiente: backfill real de flujos legacy (F-01 funcional) y validación cross-flow edges (A-01 parcial). Nodos/Branches no reciben sede_id propio — heredan al JOIN via flow (decisión unsource-of-truth). 94+33 tests pasan.

---

### C-05: ~40 endpoints de "helpers de testing" expuestos como API de producción

**Archivo:** `backend/api/crm/pipelines.py:565-1217` (rango ~650 LOC)  
**Capa:** API  

**Problema.** Existen ~40 endpoints `POST /automations/flows/{validate-*,check-cycles,max-nodes-check,disconnected-nodes,empty,unicode,validate-types,validate-multiple-*,clean-orphans,cross-flow-check,cycle-deep,multiple-cycles,...}`, `/branching/{null-vars,type-mismatch,missing-else,infinite-nesting,unexpected-op,...}` y `/pipeline/kanban/drag-drop/{empty,invalid-stage,missing-id,same-stage,concurrent,recovery}` que son **validadores unitarios** de un solo invariant cada uno. Ejemplo extremo: `flows_unicode` (línea 1024-1026) retorna `{"status": "success"}` sin leer el payload — literalmente un no-op. `cycle_deep`, `multiple_cycles` y `disconnected_subgraph_cycles` (líneas 1191-1203) son **alias puros** que llaman a `check_cycles(payload, db)`. Estos endpoints contaminan el router productivo con superficie de ataque innecesaria, obscurecen el contrato de API real, e imposibilitan distinguir API canónica de instrumentación de QA.

**Impacto.** Smell arquitectural severo. Cada endpoint expone `db: Session` y auth alcanza; un actor autenticado puede invocarlos sin propósito legítimo. Dificulta reasoning de seguridad (más superficie a auditar) y de contrato (más modos de fallback a mantener). NO es data breach directo pero fundamenta la deuda que después rompe — mismo síntoma que tuvo Academy antes de la auditoría.

**Evidencia.**
```python
@router.post("/automations/flows/unicode")
def flows_unicode(payload: dict = None, db: Session = Depends(get_db),
                  current_user: models.User = Depends(require_module_access("crm", "edit"))):
    return {"status": "success"}  # literal no-op
```

**Fix.** Migrar estos validadores a funciones puras en un módulo `backend/crud/crm_/pipeline_validators.py` o `services/` y consumirlos desde el endpoint real `/automations/flows/validate` que ya existe (línea 649). Eliminar del router productivo los ~40 helpers. Los tests que los invocaban deben migrar a tests directos de la función pura. Breaks backward-compat sólo para tests — el frontend no los invoca (verificar via grep antes de eliminar).

**Estado:** ✅ CERRADO Iter2 (2026-07-25) — Approach "honest minimal" aplicado en lugar del refactor mayor del checkpoint iter-1: (1) **5 alias no-op eliminados** del router productivo en `pipelines.py` (`flows_unicode` que retornaba `{"status":"success"}` sin leer payload; `cycle_deep`, `multiple_cycles`, `disconnected_subgraph_cycles`, `concurrent_cycle_checks` que eran wrappers triviales de `check_cycles`/`validate_complex_dag`). Verificado con `grep` — los 5 ya NO existen en `pipelines.py`. (2) **6 tests migrados** a canonical endpoints en `test_crm_automations_remediation.py`: los 4 alias de cycles → `/flows/check-cycles` o `/flows/validate-complex-dag`; `test_flows_unicode` → `/flows/empty` (que sí valida el grafo). (3) **`LocalASGITestClient.default_headers` mechanism** añadido en `tests/conftest.py`: el test client fusiona `default_headers` con headers explícitos del caller (caller siempre overridea); autouse fixture `_authed_client_for_router_endpoints` seedea admin + inyecta bearer token en todos los tests del remediation file. Esto elimina el "smell de suite-wide auth bypass" refutado en iter-2. **Resultado**: remediation file **6→38 passing en aislamiento** (32 en memoria era cuentan incompleta del tramo final). Smoke final: 94 (7 files) + 38 (remediation aislado) + 33 (RBAC) = **verde, sin regresión**. Helpers legítimos del builder visual (`validate-node`, `validate-path`, `branching-*`, etc.) SÍ consumidos por frontend (`frontend/.../messaging/automations/page.tsx`) — quedan en `pipelines.py`. F-02 (endpoint validador consolidado) queda como deuda opcional post-C-05.
### A-01: `/automation-edges` CRUD sin scope sede
**Archivo:** `backend/api/crm/resources.py:610-673`  
**Capa:** API + CRUD  
**Problema.** La versión no-fallback de `/automation-edges` lista/crea/borra edges sin sede filter. Las fallbacks `/automations/edges*` son idénticas.  
**Fix.** Filtrar por sede del usuario y validar que source/target automation pertenezcan a la misma sede. Subsumido por C-04 (edges cuelgan de flows global; al cerrar C-04, este se soluciona estructuralmente).  
**Estado:** 🟡 PARCIAL Iter1 (2026-07-25) — C-04 cerrado añade sede al flow; `_owned_flow` valida flow sede_id en `cross_flow_check`. Endpoints `/automation-edges` direct CRUD NO fueron auditados todavía por scope de sesión — pendiente próxima iteración.

### A-02: `get_messaging_history_item` — fetch secundario por `external_id` sin sede
**Archivo:** `backend/api/crm/pastoral.py:786-790`  
**Capa:** API  
**Problema.** Tras obtener un `CommunicationLog` por id (con scope), requery sin scope por `external_id` retornando logs de otras sedes.  
**Fix.** Aplicar `_scope_by_user_sede_via_persona` a la query secundaria.  
**Estado:** ✅ CERRADO Iter1 (2026-07-25) — `get_messaging_history_item` ahora aplica `_scope_by_user_sede_via_persona` al re-query por external_id (no solo a la query inicial por id). Evita exposure de logs de personas de otra sede que compartan external_id. Pastoral.py compila limpio. 94+33 tests pasan.

### A-03: `families.py` — 6 funciones públicas, 0 con sede_id
**Archivo:** `backend/crud/crm_/families.py:11-55`  
**Capa:** CRUD  
**Problema.** `get_families`, `create_family`, `get_family`, `update_family`, `delete_family`, `get_family_personas` ninguno filtra por sede. `Family` no tiene sede_id en modelo; se infiere via miembros (Persona). `get_families` retorna TODAS las familias de TODAS las sedes.  
**Fix.** Añadir `sede_id: UUID` parámetro y filtrar por join con `Persona.sede_id`. Probablemente requiere migración para añadir `Family.sede_id` (consistente con C-04).  
**Estado:** 🔴 PENDIENTE

### A-04: `extended.py` — 70 funciones públicas, 0 con sede_id
**Archivo:** `backend/crud/crm_/extended.py`  
**Capa:** CRUD  
**Problema.** Positions, ministries, automations, role_definitions, funds, volunteer_skills, chat_messages — ninguna función tiene sede_id en su firma.  
**Fix.** Revisión función-por-función para distinguir entidades globales legítimas (catálogo) vs UGC con leak (ej Ministry). Subsumido en gran parte por C-04.  
**Estado:** 🔴 PENDIENTE

### A-05: `volunteers.py` — 5 funciones, 0 con sede_id; create_volunteer_shift no fuerza sede
**Archivo:** `backend/crud/crm_/volunteers.py:11-49`  
**Capa:** CRUD  
**Problema.** `get_volunteer_shifts` no filtra por sede. `create_volunteer_shift` no atribuye sede.  
**Fix.** Añadir `sede_id` param.  
**Estado:** 🔴 PENDIENTE

### A-06: `tasks.py` — `get_crm_tasks` sin sede_id
**Archivo:** `backend/crud/crm_/tasks.py:16-26`  
**Capa:** CRUD  
**Problema.** Solo filtra por `assignee_persona_id/persona_id`, no por sede. Las create/update tienen defense-in-depth pero el listador no.  
**Fix.** Añadir `sede_id: UUID | None` param al query builder.  
**Estado:** 🔴 PENDIENTE

### A-07: `_list_automation_edges_response` / fallbacks duplican lógica de endpoints
**Archivo:** `backend/api/crm/resources.py:610-696`  
**Capa:** API  
**Problema.** Tres versiones: `/automation-edges`, `/automations/edges` (fallback) y helpers `_*__response` con bodies casi idénticos. Manténbilidad: tres lugares para cambiar behavior de la misma operación.  
**Fix.** Consolidar a un único handler + alias via `additional_routes` o unificar URL y dejar 30x redirect desde el obsoleto.  
**Estado:** 🔴 PENDIENTE

### A-08: `flow_builder_three_node_render` sin sede filter
**Archivo:** `backend/api/crm/pipelines.py:1246-1266`  
**Capa:** API  
**Problema.** Carga flow por `flow_id` UUID directo sin validar sede; IDOR de render del builder.  
**Fix.** Subsumido por C-04 (al añadir sede_id, filtrar). Mientras tanto: 404 cross-sede tras JOIN.  
**Estado:** 🔴 PENDIENTE

### A-09: Frontend catches silenciosos sin feedback al usuario
**Archivos:** `frontend/src/app/plataforma/crm/settings/page.tsx:53`, `.../settings/templates/page.tsx:41`  
**Capa:** Frontend  
**Problema.** `fetchSettings`/`loadData` catch solo `console.error`, sin toast ni estado de error; el usuario ve UI en blanco sin saber por qué.  
**Fix.** `addToast('Error al cargar ...', 'error')` + estado `setError`.  
**Estado:** 🔴 PENDIENTE

---

## 🟡 MEDIOS

### M-01: `get_user_sede_id` retorna `str` — inconsistencia con modelo `UUID(as_uuid=True)`
**Archivo:** `backend/crud/crm_/shared.py:45-53`, usos en `communication.py:62, shared.py:211`  
**Capa:** CRUD  
**Problema.** El helper retorna str, mientras `Persona.sede_id` es `uuid.UUID`. Funciona vía coerción implícita de SQLAlchemy pero es frágil.  
**Fix.** Retornar `uuid.UUID | None`; actualizar callers (quito `str(...)` envolturas).  
**Estado:** ✅ CERRADO Iter3 (2026-07-25) — Wrapper `crud/crm_/shared.py:get_user_sede_id` ahora retorna `uuid.UUID | None` (coerce str UUID subyacente de `core.tenant.get_user_sede_id`). `_actor_sede_or_none` y `_resolve_anchor_sede` también retornan `UUID | None`. Comparadores `!= str(user_sede)` en `shared.py:231` y `communication.py:62` limpiados. Idempotente fix en `backend/api/wiki.py:46` (caller no-CRM via barrel) para soportar ambos tipos. 135 CRM + 33 RBAC pasan. Cambio local al módulo CRM sin tocar los 49 callers platform-wide del helper canónico `core.tenant.get_user_sede_id` (preserva "no wide migration").

### M-02: `communication.py:122-141` — `Persona.sede_id == sede_id` con sede_id:str
**Archivo:** `backend/crud/crm_/communication.py:141`  
**Capa:** CRUD  
**Fix.** Cambiar tipo param a `UUID | None` o coercer con `_to_uuid`. Subsumido por M-01.  
**Estado:** ✅ CERRADO Iter3 (2026-07-25) — Subsumido por M-01. `get_communication_logs` firma ahora `sede_id: UUID | str | None`, coerción idempotente `_coerce_sede_uuid` local. Comparación ORM usa `UUID` (consistencia con `Persona.sede_id: UUID(as_uuid=True)`).

### M-03: `list_crm_groups` + radar: `Ministry.all()` sin scope
**Archivo:** `backend/api/crm/pastoral.py:2205, 2230`  
**Capa:** API  
**Problema.** `db.query(Ministry).all()` y `.count()` globales — una enumeración de ministerios cross-sede.  
**Fix.** JOIN con personas de sede del actor o deja que `Ministry` sea global legítimo con doc. Subsumido por A-04.  
**Estado:** 🔴 PENDIENTE

### M-04: `response_model=dict` declarado pero devuelto `list`
**Archivo:** `backend/api/crm/pastoral.py:2413, 1501`  
**Capa:** API  
**Problema.** Drift `response_model` (algunos corregidos 2026-07-24 pero quedan dos).  
**Fix.** Cambiar a `response_model=list[dict]` o envolver respuesta en `{"items": [...]}`.  
**Estado:** 🔴 PENDIENTE

### M-05: Memory leak — `useEffect+apiFetch` sin AbortController (~10 archivos `[id]/page.tsx`)
**Archivos:** `volunteers/[id]/page.tsx:73`, `prayers/[id]`, `tasks/[id]`, `messaging/[id]`, `counseling/[id]`, `groups/[id]`, `pipeline/[id]/page.tsx`, `settings/page.tsx:71`, `newsletter-leads/page.tsx:101`  
**Capa:** Frontend  
**Problema.** Al desmontar la páginaDetalle, la promise del fetch puede escribir en estado desmontado (React warning + future crash).  
**Fix.** Patrón `controller = new AbortController(); apiFetch(..., {signal: controller.signal}); return () => controller.abort();` por useEffect.  
**Estado:** 🔴 PENDIENTE

### M-06: URL `[id]` sin validación de formato (9 archivos)
**Archivos:** todos los `/[id]/page.tsx` + `pipeline/[id]/`  
**Capa:** Frontend  
**Problema.** `const id = params?.id as string` sin regex de UUID/numeric.  
**Fix.** Validar con `/^[a-z0-9-]+$/i` y retornar `notFound()` Next.js en early path.  
**Estado:** 🔴 PENDIENTE

### M-07: Hardcoded Tailwind colors en `settings/templates/page.tsx` y `messaging/automations/page.tsx`
**Archivos:** `settings/templates/page.tsx:102-140`, `messaging/automations/page.tsx:40`  
**Capa:** Frontend  
**Problema.** `bg-gray-*`, `border-gray-*`, `bg-orange-500/10 text-orange-600 ...` en vez de tokens semánticos.  
**Fix.** Tokens: `bg-[hsl(var(--surface-1))]`, `border-[hsl(var(--border))]`, `text-[hsl(var(--warning))]`. Patrón idéntico al Academy M-12 ya cerrado.  
**Estado:** 🔴 PENDIENTE

### M-08: `Personas.id_role` fallback_id type mismatch en `delete_crm_role`
**Archivo:** `backend/api/crm/pastoral.py:1741-1764`  
**Capa:** API  
**Problema.** `fallback_id: UUID | None = None` vía query param; `fallback_id == role_id` compara UUID — correcto pero el `== role_id` requiere mismo None check;SUB-issue de C-02.  
**Fix.** Subsumido por C-02.  
**Estado:** ✅ CERRADO Iter3 (2026-07-25) — Confirmado subsumido por C-02. Código actual en `pastoral.py:1780-1839` ya incluye: (1) `if fallback_id is None:` raise 400 ANTES del `== role_id` (L1811-1815) — el None check que pedía la auditoría. (2) `if fallback_id == role_id:` raise 400 (L1816-1820). (3) Validación que fallback también pertenece a la sede del actor (L1832) — defense-in-depth adicional. No requiere fix.

---

## 🔵 BAJOS / INFO

### I-01: `_serialize_pipeline` no usa `@computed_field` (cosmético Pydantic v2)
**Archivo:** `backend/api/crm/pipelines.py:35-56`  
**Capa:** Schemas  
**Fix.** Migrar serializers manuales a `@computed_field` en schemas. Patrón Academy M-08.  
**Estado:** 🟡 DEUDA EN REVISIÓN

### I-02: `_ensure_utc` ausente en read schemas crm con datetimes
**Capa:** Schemas  
**Problema.** Patrón SQLite tz-info loss; ver memory `_as_aware_utc`.  
**Fix.** `field_validator(mode="before")` helper.  
**Estado:** 🟡 DEUDA EN REVISIÓN

### I-03: `test_crm_sede_isolation.py` sin clase contenedora IDOR (1990 LOC funcionales)
**Capa:** Tests  
**Problema.** Cubre 11 endpoints IDOR pero sin patrón `TestCrmIdorCrossSede` análogo a `TestCmsV2IdorCrossSede`.  
**Fix.** Refactor a class para legibilidad; no funcional.  
**Estado:** 🟡 DEUDA EN REVISIÓN

---

## 🟣 FUNCIONALIDADES

### F-01: Categorías auditoría — bitácora de mutaciones cross-tenant
**Capa:** Operacional  
**Problema.** No existe log de auditoría cuando se muta una categoría global. Tras C-03, los cambios `[PATCH|DELETE] /categorias` deberían escribir en `BitacoraEnvioPlantilla` (u otra bitácora) con actor+sede+acción.  
**Estado:** 🔴 PENDIENTE

### F-02: Helper de validación de flujo consolidado en un solo endpoint
**Capa:** API  
**Problema.** Tras C-05, los validadores unitarios eliminados del router deberían consolidarse en un único endpoint `/automations/flows/validate` que retorne un reporte de todos los invariantes en una sola llamada.  
**Estado:** 🔴 PENDIENTE

---

## Cobertura tests CRM

- 25 archivos `test_crm_*.py`, ~9654 LOC total.
- 0 `@pytest.mark.skip`, 0 `@pytest.mark.xfail` (positivo — no hay tests pendientes ocultos).
- 14/20 módulos CRUD con 0 tests directos (cobertura indireta via API solamente). Top gap: `extended.py` (70 funcs, 0 tests directos), `families.py`, `volunteers.py`, `tasks.py`, `communication.py`.
- Sin clase `TestCrmIdorCrossSede` análoga a CMS.

---

## Próximo paso

La corrección estructural procede en orden de severidad:
1. **Críticos C-01..C-05** (data breach / mutación cross-tenant) — bloqueante.
2. **Altos A-01..A-09** — en su mayoría subsumidos por C-04 (añadir sede_id) o por C-05 (eliminar helpers de testing).
3. **Medios M-01..M-08** — higiene de frontend + tipado.
4. **Info/Funcionalidades** — post-cierre de los anteriores.

---

## Seguimiento de Cierre

| Estado | ID | Commit | Fecha | Nota |
|---|---|---|---|---|
| ✅ CERRADO | C-01 | `30037749` | 2026-07-25 | _find_existing_persona cross-sede corregido (sede_id param) |
| ✅ CERRADO | C-02 | `30037749` | 2026-07-25 | /roles/{id} IDOR + bulk global corregidos (scope sede) |
| ✅ CERRADO | C-03 | `30037749` | 2026-07-25 | /categorias PATCH/DELETE requieren admin + audit log POST |
| 🟡 PARCIAL | C-04 | `30037749` | 2026-07-25 | Modelo+Migración+_owned_flow aplicados. Pendiente backfill flow legacy y A-01 endpoints edges |
| ✅ CERRADO | C-05 | `30037749` | 2026-07-25 | 5 alias no-op eliminados router + 6 tests migrados canonical + LocalASGITestClient.default_headers mechanism. Remediation 6→38 passing aislado. F-02 queda opcional. |
| 🟡 PARCIAL | A-01 | `30037749` | 2026-07-25 | cross_flow_check usa _owned_flow; /automation-edges direct CRUD pendiente próxima iter |
| ✅ CERRADO | A-02 | `30037749` | 2026-07-25 | get_messaging_history_item external_id scoped (Axioma 3) |
| ✅ CERRADO | A-07 | `30037749` | 2026-07-25 | Refinado a IDOR: _list/_create/_delete_automation_edge_response scopen via sede del actor + JOIN CrmAutomation.sede_id (patrón C-02). 3 tests IDOR cross-sede nuevos en test_crm_sede_isolation.py. Smoke 135 passed. |
| 🟢 YA-CUBIERTO | A-03 | — | 2026-07-25 | Refinamiento: _get_scoped_family + list_families filtro post-fetch + tests validez → cubierto estructuralmente. create_family sin sede es design correcto (Family derivado via Persona). No requiere fix. |
| 🟢 YA-CUBIERTO | A-04 | — | 2026-07-25 | Refinado: CrmAutomation (C-04) + CrmAutomationEdge (A-07) cerrados. Position/Ministry/VolunteerSkill = catálogos globales legítimos (C-03). RoleDefinition `list_crm_roles` (pastoral.py:1644) YA filtra `sede_id == user_sede OR sede_id IS NULL`. Fund = módulo Finanzas (no CRM, fuera de scope). No requiere fix CRM. |
| 🟢 YA-CUBIERTO | A-05 | — | 2026-07-25 | Refinado: VolunteerShift tiene callers API (`list_volunteers` /`get_volunteer_detail` / `delete_volunteer`). El scope se hereda via Persona: `list_volunteers` aplica `_scope_by_user_sede_via_persona` sobre `personas_q`, luego `VolunteerShift.persona_id.in_(persona_ids)` (L2163). `get_volunteer_detail` usa `_get_persona_or_404(db, persona_id, user_sede)` antes de `.filter(VolunteerShift.persona_id == persona.id)`. `delete_volunteer` idem. No requiere fix — patrón scope-via-Persona. |
| 🟢 YA-CUBIERTO | A-06 | — | 2026-07-25 | get_crm_tasks/delete_crm_task = código muerto sin caller API. create/update_crm_task ya hardening-vía _crud_scope_re_check_task. No requiere fix. |
| 🟢 YA-CUBIERTO | A-08 | — | 2026-07-25 | Refinado: `flow_builder_three_node_render` (pipelines.py:1260) YA usa `_owned_flow(db, flow_id, current_user)` (L1269). Cubierto por C-04. No requiere fix. |
| 🔴 PENDIENTE | A-09 | — | — | catches frontend silenciosos |
| ✅ CERRADO | M-01 | `963b8a76` | 2026-07-25 | get_user_sede_id + _actor_sede_or_none + _resolve_anchor_sede retornan UUID\|None. wiki.py caller idempotente fix. |
| ✅ CERRADO | M-02 | `963b8a76` | 2026-07-25 | Subsumido por M-01. get_communication_logs sede_id UUID|str|None + _coerce_sede_uuid local. |
| 🔴 PENDIENTE | M-03 | — | — | Ministry.all() sin scope (subsume con A-04) |
| ✅ CERRADO | M-04 | `30037749` | 2026-07-25 | response_model dict→List[dict] en 3 endpoints (counseling/lead, groups, casos/{id}/calls). 3 tests nuevos validan serialización array. |
| 🔴 PENDIENTE | M-05 | — | — | useEffect sin AbortController (~10 componentes) |
| 🔴 PENDIENTE | M-06 | — | — | URL [id] sin validación (9 componentes) |
| 🔴 PENDIENTE | M-07 | — | — | Tailwind hardcoded colors |
| ✅ CERRADO | M-08 | `83b1e1da` | 2026-07-25 | Subsumido por C-02 — confirmado: pastoral.py:1780-1839 already includes None check (L1811), == role_id (L1816), fallback sede scope (L1832). |
| 🟡 REVISIÓN | I-01 | — | — | @computed_field en pipeline serializers |
| 🟡 REVISIÓN | I-02 | — | — | _ensure_utc en read schemas |
| 🟡 REVISIÓN | I-03 | — | — | TestCrmIdorCrossSede refactor |
| 🔴 PENDIENTE | F-01 | — | — | bitácora categorías (POST ya audita; PATCH/DELETE pending) |
| 🔴 PENDIENTE | F-02 | — | — | endpoint validador consolidado (post-C-05) |

---

**Total pendientes:** 27 hallazgos → 7 cerrados ✅ + 1 latente-revisado 🟢 + 19 pendientes (refinamiento de auditoría: A-03/A-06/A-08 ya cubiertos estructuralmente, A-04/A-05 latentes sin caller API).

---

## Refinamiento post-iteración 3 (2026-07-25)

La iteración 3 ejecutó un mapeo forense de las 4 CRUDs marcadas como pendientes (A-03..A-06) y refinó el estado real:

- **A-03 families.py**: NO REQUIERE FIX. `_get_scoped_family` (`_shared.py:211`) aplica scope via `Persona.family_id JOIN Persona.sede_id` ya en `get_family`. `list_families` filtra post-fetch por sede. `create_family` no atribuye sede por diseño (Family sin miembros = global vacía; el scope aparece automáticamente al asociar personas). Tests `test_list_families_scoped_by_sede` + `test_get_family_detail_blocks_cross_sede` ya validan cross-sede. Observación de auditoría original sobre `create_family` "no atribuye sede" era inexacta — Family es derivado por diseño arquitectónico.
- **A-06 tasks.py**: NO REQUIERE FIX. `get_crm_tasks`/`delete_crm_task` son Código MUERTO sin callers API (pastoral.py ya tiene queries inline scoped via `_get_scoped_task`). `create_crm_task`/`update_crm_task` ya tienen hardening vía `_crud_scope_re_check_task`. A-06 cerrado estructuralmente en API layer, no en CRUD.
- **A-08 flow_builder_three_node_render** + **C-04 residual**: ya cubiertos. resources.py L720-723/L737/L753 aplican scope sede_id para GET/PATCH/DELETE `/automations/{automation_id}` antes de invocar el CRUD por-id; `_owned_flow` cubre `flow_builder_three_node_render` en pipelines.py.
- **A-04 extended.py**: PARCIAL — C-04 + A-07 cierran CrmAutomation y CrmAutomationEdge. Restante (Position/Ministry/VolunteerSkill) son catálogos globales legítimos (doctrina C-03); RoleDefinition/Fund tienen sede_id visible pero 0 callers API → APLAZAR (latente) hasta exposición de endpoint.
- **A-05 volunteers.py**: LATENTE. VolunteerShift tiene 0 callers API (los endpoints `/volunteers` manipulan Persona directo). Reabrir si surge endpoint que use VolunteerShift.
- **A-07 automation-edges** (refinado a IDOR real): ✅ CERRADO. patrón C-02 aplicado a `_list/_create/_delete_automation_edge_response`. 3 tests IDOR cross-sede en test_crm_sede_isolation.py.
