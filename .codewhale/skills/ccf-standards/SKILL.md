# CCF Standards Skill

name: ccf-standards
description: |
  Load the CCF platform development standards for this session. 
  Use this skill when working on ANY CCF codebase file (backend, frontend, database, or API).
  This skill enforces the 3 Axioms, 8 database rules, and 5 backend/frontend standards
  that prevent the most common mistakes made by AI agents and human developers.

instructions: |
  ## CCF Platform Development Standards — Active

  You are working on the CCF (Comunidad Cristiana El Faro) platform. EVERY change you make
  MUST comply with these non-negotiable rules:

  ### 3 AXIOMS (violation = rejected code)

  1. **Person-Centric Kernel**: Every human entity MUST be represented by `personas.id` (UUID).
     Never create separate tables for "students", "volunteers", "donors", or "leaders".
     Use `persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"))`.

  2. **Tridimensional Identity**: A person has 3 independent role dimensions:
     - A: Ministries (pastor, teacher)
     - B: Church Roles (leader, servant, member — via `persona_role_assignments`)
     - C: Platform Permissions (admin, editor, lector — via `auth_roles`)
     Never conflate these dimensions.

  3. **Multi-Tenant Isolation**: Every SELECT query MUST filter by `sede_id`.
     Extract it from the JWT token, NOT from frontend input.
     `sede_id = get_user_sede_id(db, current_user.id)`

  ### 8 DATABASE RULES (violation = runtime crash or data corruption)

  1. **UUID PKs**: Use `UUID(as_uuid=True)` for any table with FK to `personas.id`
  2. **No Redundancy**: Don't duplicate columns that live in normalized tables
  3. **Soft Deletes**: Never `db.delete()` on transactional tables. Use `deleted_at` or `estado_vital='INACTIVO'`
  4. **Timezone**: ALWAYS `DateTime(timezone=True)`. Never bare `DateTime`.
  5. **Exclusion Constraints**: Use GIST for resource reservations to prevent race conditions
  6. **FKs to personas.id**: Use UUID. Never `Integer` FK to `personas.id`
  7. **JSON not JSONB**: Use `Column(JSON)` for SQLite compatibility
  8. **Never reference legacy tables**: `consolidation_cases`, `cell_groups`, `cell_group_sessions`, `courses`, `enrollments`, `projects`, `project_tasks` are DROPPED. Use `crm_casos`, `grupos_evangelismo`, `sesiones_grupo`, `academy_courses`, `academy_enrollments`, `proyectos`, `tareas_proyecto`.

  ### 5 BACKEND RULES

  1. **Strict Typing**: `persona_id: str` in schemas (not `int`)
  2. **Context Injection**: `sede_id` comes from JWT, not request body
  3. **Owner-Only**: `LECTOR` role can only access own resources
  4. **No @property in SQL**: Never use `@property` attributes in `.filter()` or `.order_by()`
  5. **Module Registration**: New modules must be added to `models.py`, `api/__init__.py`, and `app.py`

  ### 5 FRONTEND RULES

  1. **No Modals**: Use Drawers (side panels), never blocking dialogs
  2. **Semantic Tokens**: `bg-sistema-panel`, not `bg-white`
  3. **Lazy Loading**: Separate API calls per tab, not one massive fetch
  4. **Route Convention**: `/plataforma/{module}[/{id}]`
  5. **API prefix**: Always use `apiFetch('/endpoint')` — the `/api` prefix is added by `apiUrl()`

  ### BEFORE EVERY COMMIT — 10-point checklist

  Run this mental checklist before writing any code:
  1. Does this query filter by `sede_id`?
  2. Are all `persona_id` fields `str` (not `int`)?
  3. Are all `DateTime` columns using `timezone=True`?
  4. Is `db.delete()` absent (using soft delete instead)?
  5. Are FKs to personas using `UUID` type?
  6. Am I using `JSON` (not `JSONB`)?
  7. Am I referencing actual table names (not legacy ones)?
  8. Am I using real Column names (not `@property` attributes)?
  9. Is the new module registered in `models.py` + `api/__init__.py` + `app.py`?
  10. Have I verified syntax with `python -c "import ast; ast.parse(...)"`?

  ### COMMON MISTAKES TO AVOID

  | Mistake | Wrong | Right |
  |---|---|---|
  | @property in SQL | `SesionGrupo.session_date` | `SesionGrupo.fecha_sesion` |
  | persona_id type | `persona_id: int` | `persona_id: str` |
  | Hard delete | `db.delete(persona)` | `persona.estado_vital = 'INACTIVO'` |
  | Missing sede_id | `db.query(Persona).all()` | `db.query(Persona).filter(Persona.sede_id == sede_id).all()` |
  | Legacy table | `ConsolidationCase` | `CasoCRM` |
  | Bare DateTime | `Column(DateTime)` | `Column(DateTime(timezone=True))` |
  | FK to users.id | `ForeignKey("users.id")` | `ForeignKey("personas.id")` |
  | JSONB | `Column(JSONB)` | `Column(JSON)` |

  ### FILE NAMING CONVENTIONS

  - Models: `models_{module}.py` → `models_crm_core.py`
  - Schemas: `schemas/{module}.py` → `schemas/crm_core.py`
  - CRUD: `crud/{module}.py` → `crud/crm_core.py`
  - API router: `api/{module}.py` → `api/crm_core.py`
  - Services: `services/{name}.py` → `services/xp_engine.py`
  - Migrations: `scripts/migrations/{name}.sql`

  ### MODULE REGISTRATION PATTERN

  When creating a new module:
  1. Add to `backend/models.py`: `from backend.models_{module} import *`
  2. Add to `backend/api/__init__.py`: import router and add to list
  3. In `backend/app.py`: only if special initialization is needed

  Full documentation: `ccf/docs/ESTANDARES_DESARROLLO.md`
