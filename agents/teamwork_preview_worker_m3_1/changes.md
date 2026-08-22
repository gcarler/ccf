# Summary of Changes — Milestone M3 (R3: Section A/B Testing)

## Core Implementations

1. **Backend Models (`backend/models_cms.py` & `backend/models.py`)**:
   - `CmsAbTest`:
     - Schema: `id` (UUID PK), `site_id` (UUID FK `cms_sites.id`), `page_id` (UUID FK `cms_pages.id`), `name` (String), `section_a_id` (UUID FK `cms_sections.id`), `section_b_id` (UUID FK `cms_sections.id`), `traffic_split` (Float, default 0.5), `status` (String: 'active'|'paused'|'completed'|'deleted'), `winner_section_id` (UUID FK `cms_sections.id`, nullable), `created_at`, `started_at`, `ended_at`, `deleted_at` (`DateTime(timezone=True)`).
     - Standard relationships with `CmsSite`, `CmsPage`, `CmsSection` (a/b/winner), and `CmsAbTestEvent`.
   - `CmsAbTestEvent`:
     - Schema: `id` (UUID PK), `test_id` (UUID FK `cms_ab_tests.id`), `variant` (String: 'a'|'b'), `event_type` (String: 'view'|'click'|'conversion'), `visitor_id` (String), `created_at` (`DateTime(timezone=True)`).
   - Re-exported in `backend/models.py`.

2. **Alembic Migration (`alembic/canonical_versions/20260731_0007_add_cms_ab_tests.py`)**:
   - Canonical, fully idempotent Alembic migration creating `cms_ab_tests` and `cms_ab_test_events` with `has_table()` guards, `_uuid_type()` helper, `DateTime(timezone=True)`, indexes, and safe downgrade callbacks.

3. **Backend CRUD & API Endpoints (`backend/crud/cms.py` & `backend/api/cms_v2/ab_testing.py`)**:
   - CRUD functions: `list_cms_ab_tests`, `get_cms_ab_test`, `create_cms_ab_test`, `update_cms_ab_test`, `delete_cms_ab_test`.
   - Event recording: `record_cms_ab_test_event` (`POST /api/cms/v2/sites/{site_key}/ab-tests/{id}/record-event`).
   - Statistical calculation: `get_cms_ab_test_results` (`GET /api/cms/v2/sites/{site_key}/ab-tests/{id}/results`). Calculates views, clicks, conversions, conversion rates for variants A and B, calculates two-proportion z-test statistical significance (returning >0.95 when significant), and recommends a winner.
   - Apply winner: `apply_cms_ab_test_winner` (`POST /api/cms/v2/sites/{site_key}/ab-tests/{id}/apply-winner`). Marks winning section visible, hides losing section, sets `winner_section_id`, and updates status to `'completed'`.
   - Router mounted under `/cms/v2` in `backend/api/cms_v2/__init__.py`.
   - Fixed schemas re-export in `backend/schemas/__init__.py` for `CmsPostCommentRead` and `CmsAbTest` schemas.

4. **Frontend Admin UI (`frontend/src/app/plataforma/cms/ab-testing/page.tsx`)**:
   - Full A/B testing admin management interface with tabs, search, status filtering.
   - Test drawer to create experiments selecting page, variant sections A and B, and traffic split.
   - Results modal with cards, progress bars for views/clicks/conversions, statistical significance badge (>95%), and "Aplicar ganador" button calling `/apply-winner`.

5. **Navigation (`frontend/src/components/cms/CmsModuleNav.tsx`)**:
   - Registered A/B Testing entry in `CMS_TABS` using `FlaskConical` icon from `lucide-react`, href `/plataforma/cms/ab-testing`, label `"A/B Testing"`.

6. **Public Renderer (`frontend/src/components/public/cms/PublicSectionRenderer.tsx`)**:
   - Client-side variant determination logic reading/setting `ab_visitor_id` cookie & local storage.
   - Hash-based deterministic variant resolution (`visitor_id + abTest.id % 100` vs `traffic_split`).
   - Triggers `recordCmsAbTestEvent` for view events on mount and click events on section click.

## Verification Results

- `cd /root/ccf/frontend && npx tsc --noEmit`: PASS (0 errors)
- `PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v`: PASS (43 passed, 1 skipped)
- `PYTHONPATH=. python3 -m pytest tests/test_cms_v2_ab_testing.py -v`: PASS (7 passed)
