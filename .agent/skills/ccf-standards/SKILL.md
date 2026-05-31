---
name: ccf-standards
description: >
  CCF Platform Development Standards — Enterprise-Grade, Anti-Data-Loss Enforced.
  Use this skill ALWAYS when working on the CCF (Comunidad Cristiana El Faro) codebase.
  This covers 3 Axioms, 6 Database standards, 5 Backend rules, 5 Frontend rules,
  the Safe Migration Protocol, Owner-Only authorization, and the 10-point Pre-Commit checklist.
  Triggers: ANY modification to backend/ Python files, frontend/ TSX/TS files, database
  migrations, SQL scripts, API schemas, or CRUD operations within the CCF repository.
---

# CCF Standards Skill

## 3 AXIOMS (violation = rejected code)

### 1. Person-Centric Kernel (Single Source of Truth)
Every human entity MUST point to `personas.id` (UUID). Never create parallel tables for
"students", "volunteers", "donors", or "leaders". Use FK to `personas.id`.

```python
persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"))  # ✅
user_id = Column(Integer, ForeignKey("users.id"))                  # ❌
```

### 2. Tridimensional Identity
A person has 3 independent role dimensions that coexist simultaneously:

| Dimension | Table | Examples |
|---|---|---|
| **A: Ministries** | `persona_ministries` | Pastor, Teacher |
| **B: Church Roles** | `persona_church_roles` / `persona_role_assignments` | Leader, Servant, Member |
| **C: Platform Permissions** | `auth_roles` / `auth_user_module_roles` | ADMIN, GESTOR, EDITOR, LECTOR |

Never conflate these dimensions. A person can be A=Maestro, B=Líder, C=EDITOR simultaneously.

### 3. Multi-Tenant Isolation (`sede_id`)
Every SELECT query MUST filter by `sede_id`. Extract it from JWT, NOT from frontend input.

```python
sede_id = get_user_sede_id(db, current_user.id)
personas = db.query(Persona).filter(Persona.sede_id == sede_id).all()  # ✅
personas = db.query(Persona).all()                                      # ❌
```

## 6 DATABASE STANDARDS

### A. UUID Primary Keys
**Obligatorio:** Prohibited: autoincremental Integer PKs for relational/transactional tables.
```python
id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
```
Exception: catalog tables with <100 rows and no FK to personas.

### B. Zero Redundancy (Normalized)
If a data attribute lives in a normalized table, don't duplicate it as a column in `personas`.
```python
class Persona(Base):
    church_role = Column(String(50))  # ❌ redundant
```

### C. Soft Deletes Only
**Prohibited:** `db.delete()` on personas or transactional tables.
```python
persona.estado_vital = "INACTIVO"  # ✅
db.delete(persona)                  # ❌
```

### D. Strict Timezone (`DateTime(timezone=True)`)
**Mandatory:** Every DateTime column uses `DateTime(timezone=True)`. Server stores UTC.
```python
created_at = Column(DateTime(timezone=True))  # ✅
created_at = Column(DateTime)                  # ❌
```

### E. GIST Exclusion Constraints
For resource reservations, apply exclusion constraints at DB level:
```sql
EXCLUDE USING gist (recurso_id WITH =, tsrange(bloqueo_inicio, bloqueo_fin) WITH &&)
```

### F. Safe Migration Protocol (6 Steps — Anti-Data-Loss)
When migrating PK/FK types (e.g. Integer→UUID), follow this strict protocol:
1. Add temp UUID column in PARENT (keep original PK)
2. Add temp UUID column in CHILD tables
3. **Cross-populate** child temp columns via active integer FK (THIS PREVENTS DATA LOSS)
4. Validate zero orphans + apply NOT NULL
5. Drop old constraints and columns
6. Rename temp columns + recreate PK/FKs

**⚠️ NEVER execute Step 5 before completing and verifying Step 3.**

## 5 BACKEND RULES

1. **Strict Typing**: `persona_id: str` in Pydantic schemas (not `int`)
2. **Context Injection**: `sede_id` extracted from JWT, not request body
3. **Owner-Only**: `LECTOR` role can only CRUD own resources
4. **No @property in SQL**: Never use Python `@property` in `.filter()` / `.order_by()`
5. **Module Registration**: New modules MUST be registered in `models.py`, `api/__init__.py`, and `app.py`

### Owner-Only Enforcement
```python
if usuario_autenticado.rol_global == "LECTOR" and recurso.persona_id != usuario_autenticado.id:
    raise HTTPException(status_code=403, detail="Operación no permitida sobre este recurso")
```

### @property Anti-Pattern
```python
db.query(SesionGrupo).filter(SesionGrupo.session_date >= cutoff)      # ❌ @property no existe en DB
db.query(SesionGrupo).filter(SesionGrupo.fecha_sesion >= cutoff)       # ✅
```

## 5 FRONTEND RULES

1. **No Modals**: Use Drawers (side panels). Implement drawer stacking for nested info.
   ```tsx
   <Drawer open={true} onClose={handleClose}>  {/* ✅ */}
   <Dialog open={true} onClose={handleClose}>  {/* ❌ */}
   ```
2. **Semantic Tokens**: `bg-sistema-panel`, `border-sistema-linea` — never `bg-white` or `border-gray-200`
3. **Lazy Loading**: Separate API calls per tab, not one massive `/full-profile` fetch
4. **Route Convention**: `/plataforma/{module}[/{id}]`
5. **API Prefix**: Use `apiFetch('/endpoint')` — the `/api` prefix is added automatically

## NEW REQUIREMENT DECISION TREE (3 Levels)

```
1. ¿Representa a un ser humano?
   → YES: Nivel 1 — Ficha Molecular. Apunta a personas.id con tags dinámicos.
   → NO: Go to 2.

2. ¿Exige capturar datos muy variables?
   → YES: Nivel 2 — Extensión JSONB. Guardar atributos dinámicos en JSONB satélite.
   → NO: Go to 3.

3. ¿Requiere conectar flujos con agenda/calendarios?
   → YES: Nivel 3 — Bus de Eventos. Usar enlace polimórfico (modulo_origen + entidad_origen_id).
   → NO: Re-evaluar si es necesario o si ya existe en la plataforma.
```

## 10-POINT PRE-COMMIT CHECKLIST

Antes de cada commit:
- [ ] 1. ¿Toda query filtra por `sede_id`?
- [ ] 2. ¿Todos los `persona_id` son `str` en schemas?
- [ ] 3. ¿Todos los `DateTime` usan `timezone=True`?
- [ ] 4. ¿Sin `db.delete()` en tablas transaccionales?
- [ ] 5. ¿FKs a personas con UUID type?
- [ ] 6. ¿`JSON` (no `JSONB`)?
- [ ] 7. ¿Tablas reales v2 (no legacy)?
- [ ] 8. ¿Columnas reales (no `@property`)?
- [ ] 9. ¿Módulo registrado en models.py + api/__init__.py + app.py?
- [ ] 10. ¿Documentado en formato matricial?

## COMMON MISTAKES TABLE

| Mistake | Wrong | Right |
|---|---|---|
| @property in SQL | `SesionGrupo.session_date` | `SesionGrupo.fecha_sesion` |
| persona_id type | `persona_id: int` | `persona_id: str` |
| Hard delete | `db.delete(persona)` | `persona.estado_vital = 'INACTIVO'` |
| Missing sede_id | `db.query(Persona).all()` | `.filter(Persona.sede_id == sede_id)` |
| Legacy table | `ConsolidationCase` | `CasoCRM` |
| Bare DateTime | `Column(DateTime)` | `Column(DateTime(timezone=True))` |
| FK to users.id | `ForeignKey("users.id")` | `ForeignKey("personas.id")` |
| JSONB | `Column(JSONB)` | `Column(JSON)` |
| Modals | `<Dialog>` | `<Drawer>` |
| Hardcoded colors | `bg-white` | `bg-sistema-panel` |

## LEGACY TABLE MAPPING (NO USAR)

| ❌ Eliminada | ✅ Reemplazo |
|---|---|
| `consolidation_cases` | `crm_casos` |
| `cell_groups` | `grupos_evangelismo` |
| `cell_group_sessions` | `sesiones_grupo` |
| `courses` | `academy_courses` |
| `enrollments` | `academy_enrollments` |
| `projects` | `proyectos` |
| `project_tasks` | `tareas_proyecto` |

## FILE NAMING CONVENTIONS

- Models: `models_{module}.py` → `models_crm_core.py`
- Schemas: `schemas/{module}.py` → `schemas/crm_core.py`
- CRUD: `crud/{module}.py` → `crud/crm_core.py`
- API router: `api/{module}.py` → `api/crm_core.py`
- Services: `services/{name}.py` → `services/xp_engine.py`
- Migrations: `scripts/migrations/{name}.sql`

## CODE AUDIT FORMAT

```json
{
  "auditoria_ccf": {
    "capa_evaluada": "DB / BACKEND / FRONTEND",
    "archivo_o_endpoint": "nombre_archivo.py",
    "estado": "PASS",
    "violacion_axioma": "Ninguna",
    "hallazgo_tecnico": "Descripción",
    "correccion_super_pro": "Bloque de código"
  }
}
```
