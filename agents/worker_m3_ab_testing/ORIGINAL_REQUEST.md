## 2026-07-30T23:57:24Z
You are a Worker subagent assigned to implement Milestone 3: R3 A/B Testing of Sections.
Your working directory is: /root/ccf/.agents/worker_m3_ab_testing

Detailed Requirements:
1. Backend Models (`backend/models_cms.py`):
   - `CmsAbTest`: id (UUID PK), site_id (FK cms_sites.id), page_id (FK cms_pages.id), name (str), section_a_id (FK cms_sections.id), section_b_id (FK cms_sections.id), traffic_split (float default 0.5), status (str default 'active': 'active'|'paused'|'completed'), winner_section_id (FK cms_sections.id nullable), created_at, started_at, ended_at.
   - `CmsAbTestEvent`: id (UUID PK), test_id (FK cms_ab_tests.id), variant (str: 'a'|'b'), event_type (str: 'view'|'click'|'conversion'), visitor_id (str), created_at.

2. Backend Endpoints (`backend/api/cms_v2/ab_testing.py`):
   - Admin CRUD under `/api/cms/v2/sites/{site_key}/ab-tests`: GET list, POST create, GET /{id}, PATCH /{id}, DELETE /{id}.
   - Event recording: `POST /api/cms/v2/sites/{site_key}/ab-tests/{id}/record-event` (records view, click, conversion).
   - Results calculation: `GET /api/cms/v2/sites/{site_key}/ab-tests/{id}/results` (computes views_a, views_b, clicks_a, clicks_b, conversion_rate_a, conversion_rate_b, statistical_significance).
   - Winner application endpoint: `POST /api/cms/v2/sites/{site_key}/ab-tests/{id}/apply-winner` (replaces page section with winning variant and marks test completed).
   - Register router in `backend/api/cms_v2/__init__.py`.

3. Alembic Migration:
   - Create migration script in `alembic/canonical_versions/` for `cms_ab_tests` and `cms_ab_test_events` tables.

4. Frontend Admin Page (`frontend/src/app/plataforma/cms/ab-testing/page.tsx`):
   - Active / Paused / Completed tests list.
   - Create test drawer/modal: page selector, section A & B selectors, split slider/input, name.
   - Results view with progress bars for A vs B (views, clicks, conversion rate) and winner badge (>95% confidence).
   - "Aplicar ganador" action button.
   - Use `apiFetch`, `useAuth`, `sonner` toasts, skeleton loaders.

5. Navigation (`frontend/src/components/cms/CmsModuleNav.tsx`):
   - Add "A/B Testing" navigation item linking to `/plataforma/cms/ab-testing` with icon `FlaskConical` from `lucide-react`.

6. Public Section Renderer (`frontend/src/components/public/cms/PublicSectionRenderer.tsx`):
   - Supports A/B test variant resolution and event tracking for active tests.

7. Testing & Typecheck:
   - Run `cd /root/ccf/frontend && npm run typecheck` to ensure 0 TypeScript errors.
   - Write pytest test suite `tests/test_cms_v2_ab_testing.py` and vitest tests for A/B testing admin page.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Upon completion, write a detailed handoff report to `/root/ccf/.agents/worker_m3_ab_testing/handoff.md`.
