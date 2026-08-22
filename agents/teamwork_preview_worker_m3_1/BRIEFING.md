# BRIEFING — 2026-07-31T00:04:55Z

## Mission
Implement Section A/B Testing feature (Backend models, Alembic migration, API endpoints, Admin UI, Navigation tab, and Public Renderer variant resolution).

## 🔒 My Identity
- Archetype: implementer, qa, specialist
- Roles: implementer, qa, specialist
- Working directory: /root/ccf/.agents/teamwork_preview_worker_m3_1
- Original parent: 29fb24b8-3c58-4e56-9cb8-c98e4a775f50
- Milestone: M3 (R3: A/B Testing of Sections)

## 🔒 Key Constraints
- CODE_ONLY network mode: no external requests.
- Strict DB rules from structural contracts: sa.JSON if JSON fields, DateTime(timezone=True), UUID PKs with _uuid_type().
- Idempotent Alembic migration with has_table() guards.
- Admin UI in frontend/src/app/plataforma/cms/ab-testing/page.tsx.
- Nav tab in frontend/src/components/cms/CmsModuleNav.tsx.
- Public section renderer integration in frontend/src/components/public/cms/PublicSectionRenderer.tsx.
- Verification: `npx tsc --noEmit` (0 errors), `pytest tests/test_structural_contracts.py -v` (passed).
- **Reglas CCF obligatorias**: Leer y aplicar `/root/ccf/AGENTS_RULES_CCF.md` ANTES de implementar. Todo código nuevo debe cumplir: backend (datetime.now(timezone.utc), sede_id kwonly, actor UUID, UUID PKs, soft deletes, HTTPException semánticos), frontend (apiFetch, /plataforma/, drawers NO modals, tokens semánticos hsl(var(--*)), clsx, DS* components), DB (migraciones reversibles, no editar cerradas).
- **Drawers NO modals**: Flujos create/edit/view usan drawers (SidePanel, RightPanel, UniversalCreationDrawer), NO modals/AlertDialog. Excepción: confirmaciones de delete pueden usar AlertDialog.
- **Lint obligatorio**: Ejecutar `cd /root/ccf/frontend && npm run lint -- --max-warnings=0` antes de commit.
- **Venv para pytest**: Ejecutar `cd /root/ccf && ./venv/bin/python -m pytest` (no `python3` directo).
- **Sistema task**: Registrar T1 + sub-tareas en el sistema task ANTES de codear.

## Current Parent
- Conversation ID: 29fb24b8-3c58-4e56-9cb8-c98e4a775f50
- Updated: 2026-07-31T00:04:55Z

## Task Summary
- **What to build**: Section A/B testing backend & frontend integration.
- **Success criteria**: All models, migrations, endpoints, admin UI, navigation tab, and public section renderer logic working and passing verification without cheating.

## Change Tracker
- **Files modified**:
  - `backend/models_cms.py`: `CmsAbTest` & `CmsAbTestEvent` models
  - `backend/models.py`: Model exports
  - `alembic/canonical_versions/20260731_0007_add_cms_ab_tests.py`: Migration
  - `backend/api/cms_v2/ab_testing.py`: API endpoints
  - `backend/api/cms_v2/__init__.py`: Sub-router registration
  - `backend/crud/cms.py`: CRUD & Z-score results calculation logic
  - `backend/schemas/cms.py` & `backend/schemas/__init__.py`: Schemas export fix
  - `frontend/src/app/plataforma/cms/ab-testing/page.tsx`: Admin UI
  - `frontend/src/components/cms/CmsModuleNav.tsx`: Navigation entry with `FlaskConical`
  - `frontend/src/components/public/cms/PublicSectionRenderer.tsx`: Visitor variant hashing & event recording
- **Build status**: PASS
- **Pending issues**: None

## Quality Status
- **Build/test result**: PASS (`npx tsc --noEmit`: 0 errors; `test_structural_contracts.py`: 43 passed; `test_cms_v2_ab_testing.py`: 7 passed)
- **Lint status**: Clean
- **Tests added/modified**: `tests/test_cms_v2_ab_testing.py` verified

## Loaded Skills
- **ccf-backend-guard**: Backend safety (FastAPI, SQLAlchemy, sede_id, soft deletes, datetime, UUID).
- **ccf-ui-guard**: Frontend safety (Next.js, apiFetch, /plataforma/, drawers, semantic tokens, DS 3-layer).
- **ccf-architecture-guard**: Cross-layer change planning and rollback safety.
- **ccf-cms-guard**: CMS and public-content safety.
