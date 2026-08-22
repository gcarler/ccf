## 2026-07-31T00:02:38Z
You are a Worker subagent for Milestone M3 (R3: A/B Testing of Sections).
Working Directory: /root/ccf/.agents/teamwork_preview_worker_m3_1/
Project root: /root/ccf

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your objective is to implement Section A/B Testing across Backend, Alembic migration, Admin UI, Navigation, and Public Renderer:

1. **Backend Models (`backend/models_cms.py`)**:
   Add models:
   - `CmsAbTest`:
     - id (UUID PK)
     - site_id (UUID FK `cms_sites.id`)
     - page_id (UUID FK `cms_pages.id`)
     - name (String)
     - section_a_id (UUID FK `cms_sections.id`)
     - section_b_id (UUID FK `cms_sections.id`)
     - traffic_split (Float, default 0.5)
     - status (String: 'active'|'paused'|'completed')
     - winner_section_id (UUID FK `cms_sections.id`, nullable)
     - created_at, started_at, ended_at (DateTime with timezone=True)
   - `CmsAbTestEvent`:
     - id (UUID PK)
     - test_id (UUID FK `cms_ab_tests.id`)
     - variant (String: 'a'|'b')
     - event_type (String: 'view'|'click'|'conversion')
     - visitor_id (String)
     - created_at (DateTime with timezone=True)

   Ensure all DB rules from structural contracts are met:
   - Use `sa.JSON` if JSON fields used
   - Use `DateTime(timezone=True)`
   - UUID PKs with `_uuid_type()`

2. **Alembic Migration (`alembic/canonical_versions/`)**:
   Create idempotent migration file creating `cms_ab_tests` and `cms_ab_test_events` tables with `has_table()` guards.

3. **Backend API (`backend/api/cms_v2/ab_testing.py`)**:
   Create router mounted under `/api/cms/v2/sites/{site_key}/ab-tests`:
   - CRUD endpoints for A/B tests (list, create, detail, update, delete).
   - `POST /ab-tests/{id}/record-event`: Body `{variant: 'a'|'b', event_type: 'view'|'click'|'conversion', visitor_id: str}`. Records event into `CmsAbTestEvent`.
   - `GET /ab-tests/{id}/results`: Calculates and returns `views_a`, `views_b`, `clicks_a`, `clicks_b`, `conversions_a`, `conversions_b`, `conversion_rate_a`, `conversion_rate_b`, `statistical_significance` (z-test / chi-squared calculation or standard two-proportion z-score formula, returning >0.95 when significant), and suggested winner.
   - `POST /ab-tests/{id}/apply-winner`: Sets `winner_section_id`, updates test status to `'completed'`, and updates page sections if requested.
   Register router in `backend/api/cms_v2/__init__.py` or `backend/app.py`.

4. **Frontend Admin UI (`frontend/src/app/plataforma/cms/ab-testing/page.tsx`)**:
   - Create admin page for A/B testing.
   - Lists active/paused/completed tests with status badges.
   - Form to create test: select page, select section A, select section B, name, traffic split slider/input.
   - Test results view: metrics cards and progress bars for views/clicks/conversions of variant A vs B, statistical significance badge (>95%).
   - "Aplicar ganador" button that calls the backend endpoint.

5. **Navigation (`frontend/src/components/cms/CmsModuleNav.tsx`)**:
   - Add A/B Testing entry to `CMS_TABS` using `FlaskConical` icon from `lucide-react`, href `/plataforma/cms/ab-testing`, label `"A/B Testing"`.

6. **Public Renderer (`frontend/src/components/public/cms/PublicSectionRenderer.tsx`)**:
   - Integrate variant determination logic for active A/B tests. Check `ab_visitor_id` cookie (generate UUID if not set). If a section is part of an active test, render section A or section B based on visitor hash % traffic split, and trigger view event recording.

7. **Verification**:
   - `cd /root/ccf/frontend && npx tsc --noEmit` (0 errors)
   - `PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v` (passed)

Report your changes in `/root/ccf/.agents/teamwork_preview_worker_m3_1/changes.md` and handoff report in `/root/ccf/.agents/teamwork_preview_worker_m3_1/handoff.md`.
Send a message back to parent when completed.
