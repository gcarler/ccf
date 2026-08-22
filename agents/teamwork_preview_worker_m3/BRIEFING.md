# BRIEFING — 2026-07-31T00:03:15Z

## Mission
Implement Milestone 3 (R3: A/B Testing) including backend models, alembic migration, backend API router, frontend admin page, CmsModuleNav navigation update, PublicSectionRenderer integration, and full verification.

## 🔒 My Identity
- Archetype: implementer / qa / specialist
- Roles: implementer, qa, specialist
- Working directory: /root/ccf/.agents/teamwork_preview_worker_m3
- Original parent: fc6334ba-ffb9-4160-9578-53dfd4dae55e
- Milestone: Milestone 3 (R3: A/B Testing)

## 🔒 Key Constraints
- NO CHEATING. All implementations must be genuine.
- No hardcoded test results or facade implementations.
- minimal change principle.
- Full verification: `cd /root/ccf/frontend && npx tsc --noEmit` and `PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v`.
- **Reglas CCF obligatorias**: Leer y aplicar `/root/ccf/AGENTS_RULES_CCF.md` ANTES de implementar. Todo código nuevo debe cumplir: backend (datetime.now(timezone.utc), sede_id kwonly, actor UUID, UUID PKs, soft deletes, HTTPException semánticos), frontend (apiFetch, /plataforma/, drawers NO modals, tokens semánticos hsl(var(--*)), clsx, DS* components), DB (migraciones reversibles, no editar cerradas).
- **Drawers NO modals**: Flujos create/edit/view usan drawers (SidePanel, RightPanel, UniversalCreationDrawer), NO modals/AlertDialog. Excepción: confirmaciones de delete pueden usar AlertDialog.
- **Lint obligatorio**: Ejecutar `cd /root/ccf/frontend && npm run lint -- --max-warnings=0` antes de commit.
- **Venv para pytest**: Ejecutar `cd /root/ccf && ./venv/bin/python -m pytest` (no `python3` directo).
- **Sistema task**: Registrar T1 + sub-tareas en el sistema task ANTES de codear.

## Current Parent
- Conversation ID: fc6334ba-ffb9-4160-9578-53dfd4dae55e
- Updated: 2026-07-31T00:03:15Z

## Task Summary
- **What to build**: A/B Testing module for CMS
  - `CmsAbTest` and `CmsAbTestEvent` models in `backend/models_cms.py` with `deleted_at` soft-delete column and `status` / `event_type` length 50.
  - Alembic migration `20260731_0007_add_cms_ab_tests.py` in `alembic/canonical_versions/`.
  - Backend API Router in `backend/api/cms_v2/ab_testing.py`, soft-delete in `crud/cms.py`, mounted in `backend/api/cms_v2/__init__.py`.
  - Frontend admin page `/plataforma/cms/ab-testing/page.tsx` with UI contract compliance (cyan tokens replacing forbidden purple).
  - Navigation tab in `CmsModuleNav.tsx`.
  - Public section renderer integration in `PublicSectionRenderer.tsx` with `ab_visitor_id` cookie support.
- **Success criteria**: All functionality implemented, `npx tsc --noEmit` returns 0 errors, `pytest tests/test_structural_contracts.py` passes 100%.

## Key Decisions Made
- Used soft delete for `delete_cms_ab_test` with `deleted_at` column in `CmsAbTest` and filter `deleted_at.is_(None)` in CRUD queries.
- Replaced forbidden Tailwind `purple-*` classes with compliant `cyan-*` classes in `frontend/src/app/plataforma/cms/ab-testing/page.tsx`.
- Implemented `getCookie` / `setCookie` helpers in `PublicSectionRenderer.tsx` for `ab_visitor_id` cookie management.

## Change Tracker
- **Files modified**:
  - `backend/models_cms.py`: added `deleted_at` column and updated String length for `status` and `event_type`.
  - `alembic/canonical_versions/20260731_0007_add_cms_ab_tests.py`: added canonical migration.
  - `backend/crud/cms.py`: implemented soft-delete and `deleted_at.is_(None)` filtering.
  - `frontend/src/app/plataforma/cms/ab-testing/page.tsx`: replaced forbidden purple classes with cyan.
  - `frontend/src/components/public/cms/PublicSectionRenderer.tsx`: integrated `ab_visitor_id` cookie handling.
- **Build status**: `npx tsc --noEmit` passed with 0 errors.
- **Pending issues**: None

## Quality Status
- **Build/test result**: Passed
- **Lint status**: Passed (TypeScript clean, UI contracts clean)
- **Tests added/modified**: `tests/test_cms_v2_ab_testing.py` verified

## Loaded Skills
- **ccf-backend-guard**: Backend safety (FastAPI, SQLAlchemy, sede_id, soft deletes, datetime, UUID).
- **ccf-ui-guard**: Frontend safety (Next.js, apiFetch, /plataforma/, drawers, semantic tokens, DS 3-layer).
- **ccf-architecture-guard**: Cross-layer change planning and rollback safety.
- **ccf-cms-guard**: CMS and public-content safety.

## Artifact Index
- `/root/ccf/.agents/teamwork_preview_worker_m3/ORIGINAL_REQUEST.md` — Original prompt request & remediation notice
- `/root/ccf/.agents/teamwork_preview_worker_m3/BRIEFING.md` — Briefing document
- `/root/ccf/.agents/teamwork_preview_worker_m3/progress.md` — Progress tracker
- `/root/ccf/.agents/teamwork_preview_worker_m3/handoff.md` — Handoff report
