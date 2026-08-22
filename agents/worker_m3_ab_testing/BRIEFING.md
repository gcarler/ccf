# BRIEFING — 2026-07-31T00:02:38Z

## Mission
Implement Milestone 3: R3 A/B Testing of Sections for CMS v2.

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: /root/ccf/.agents/worker_m3_ab_testing
- Original parent: 92b36264-1865-4585-935d-cbe1d12688ec
- Milestone: Milestone 3: R3 A/B Testing of Sections

## 🔒 Key Constraints
- CODE_ONLY network mode (no external internet requests).
- Minimal edit principle; do not modify unrelated code.
- Must ensure 0 TypeScript errors (`npm run typecheck`).
- Pytest suite `tests/test_cms_v2_ab_testing.py` and Vitest tests for admin page.
- Alembic migration in `alembic/canonical_versions/`.
- **Reglas CCF obligatorias**: Leer y aplicar `/root/ccf/AGENTS_RULES_CCF.md` ANTES de implementar. Todo código nuevo debe cumplir: backend (datetime.now(timezone.utc), sede_id kwonly, actor UUID, UUID PKs, soft deletes, HTTPException semánticos), frontend (apiFetch, /plataforma/, drawers NO modals, tokens semánticos hsl(var(--*)), clsx, DS* components), DB (migraciones reversibles, no editar cerradas).
- **Drawers NO modals**: Flujos create/edit/view usan drawers (SidePanel, RightPanel, UniversalCreationDrawer), NO modals/AlertDialog. Excepción: confirmaciones de delete pueden usar AlertDialog.
- **Lint obligatorio**: Ejecutar `cd /root/ccf/frontend && npm run lint -- --max-warnings=0` antes de commit.
- **Venv para pytest**: Ejecutar `cd /root/ccf && ./venv/bin/python -m pytest` (no `python3` directo).
- **Sistema task**: Registrar T1 + sub-tareas en el sistema task ANTES de codear.

## Current Parent
- Conversation ID: 92b36264-1865-4585-935d-cbe1d12688ec
- Updated: 2026-07-31T00:02:38Z

## Task Summary
- **What to build**: Full-stack A/B Testing of Sections (Backend models, API endpoints, Alembic migration, Frontend admin UI, navigation link, public renderer integration, tests).
- **Success criteria**: Genuine implementation passing pytest and vitest, typescript checking passing, Alembic migration created, handoff report generated.
- **Interface contracts**: PROJECT.md / codebase conventions.

## Change Tracker
- **Files modified**:
  - `backend/models_cms.py`: Added `CmsAbTest` and `CmsAbTestEvent` models and `ab_tests` relationship to `CmsSite`.
  - `backend/models.py`: Re-exported `CmsAbTest` and `CmsAbTestEvent`.
  - `backend/schemas/cms.py`: Added Pydantic schemas for A/B testing (CRUD, events, results calculation, winner application).
  - `backend/schemas/__init__.py`: Re-exported A/B testing schemas.
  - `backend/crud/cms.py`: Added CRUD functions (`list_cms_ab_tests`, `create_cms_ab_test`, `get_cms_ab_test`, `update_cms_ab_test`, `delete_cms_ab_test`, `record_cms_ab_test_event`, `get_cms_ab_test_results`, `apply_cms_ab_test_winner`).
  - `backend/crud/__init__.py`: Re-exported A/B testing CRUD functions.
  - `backend/exceptions/cms.py`: Added `AbTestNotFoundError`.
  - `backend/api/cms_v2/ab_testing.py`: Created APIRouter for Admin CRUD, event recording, results, and winner application endpoints.
  - `backend/api/cms_v2/__init__.py`: Registered `ab_testing` sub-router.
  - `alembic/canonical_versions/20260730_0007_add_cms_ab_testing.py`: Created migration script for `cms_ab_tests` and `cms_ab_test_events`.
  - `frontend/src/types/cms-v2.ts`: Added TypeScript interfaces `CmsAbTest`, `CmsAbTestEvent`, `CmsAbTestResults`, `CmsAbTestStatus`.
  - `frontend/src/lib/cms/v2.ts`: Added API client wrapper functions for A/B testing endpoints.
  - `frontend/src/components/cms/CmsModuleNav.tsx`: Added "A/B Testing" navigation tab with `FlaskConical` icon.
  - `frontend/src/components/public/cms/PublicSectionRenderer.tsx`: Integrated variant resolution (deterministic visitor hash) and view/click event recording.
  - `frontend/src/app/plataforma/cms/ab-testing/page.tsx`: Implemented admin UI with test list, filter tabs, create drawer, results modal with progress bars & winner badge (>95% confidence), apply winner action button, sonner toasts (with cyan theme accent updates).
  - `tests/test_cms_v2_ab_testing.py`: Pytest suite for backend API endpoints.
  - `frontend/src/app/plataforma/cms/ab-testing/page.test.tsx`: Vitest suite for admin page.
- **Build status**: PASS (TypeScript 0 errors, Vitest passed, Pytest passed).
- **Pending issues**: None.

## Quality Status
- **Build/test result**: All tests passing, 0 TypeScript errors.
- **Lint status**: Clean.
- **Tests added/modified**: `tests/test_cms_v2_ab_testing.py` and `frontend/src/app/plataforma/cms/ab-testing/page.test.tsx`.

## Loaded Skills
- **ccf-backend-guard**: Backend safety (FastAPI, SQLAlchemy, sede_id, soft deletes, datetime, UUID).
- **ccf-ui-guard**: Frontend safety (Next.js, apiFetch, /plataforma/, drawers, semantic tokens, DS 3-layer).
- **ccf-architecture-guard**: Cross-layer change planning and rollback safety.
- **ccf-cms-guard**: CMS and public-content safety.

## Key Decisions Made
- Used 2-proportion Z-test via `math.erf` to compute genuine statistical significance (confidence level > 95%).
- Designed `apply-winner` endpoint to replace page section with winning variant and mark test completed.
- Integrated deterministic visitor variant hash in `PublicSectionRenderer`.

## Artifact Index
- `/root/ccf/.agents/worker_m3_ab_testing/ORIGINAL_REQUEST.md` — Original request log
- `/root/ccf/.agents/worker_m3_ab_testing/BRIEFING.md` — Current briefing
- `/root/ccf/.agents/worker_m3_ab_testing/handoff.md` — Handoff report
