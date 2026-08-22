## 2026-07-31T00:00:37Z
You are teamwork_preview_worker_m3, a software engineering worker.
Working directory: /root/ccf/.agents/teamwork_preview_worker_m3
Project root: /root/ccf

Your task is Milestone 3 (R3: A/B Testing):

1. **Backend Models** (`backend/models_cms.py`):
   - `CmsAbTest`: id (UUID(as_uuid=True), default uuid4), site_id (UUID FK cms_sites), page_id (UUID FK cms_pages), name (String(255)), section_a_id (UUID FK cms_sections), section_b_id (UUID FK cms_sections), traffic_split (Float, default 0.5), status (String(50), default 'active'), winner_section_id (UUID FK cms_sections, nullable), created_at, started_at, ended_at, deleted_at.
   - `CmsAbTestEvent`: id (UUID(as_uuid=True)), test_id (UUID FK cms_ab_tests), variant (String(10) 'a'|'b'), event_type (String(50) 'view'|'click'|'conversion'), visitor_id (String(255)), created_at.

2. **Alembic Migration** (`alembic/canonical_versions/`):
   - Create migration `20260731_0007_add_cms_ab_tests.py` adding `cms_ab_tests` and `cms_ab_test_events` tables with proper FKs and indexes.

3. **Backend API Router** (`backend/api/cms_v2/ab_testing.py`):
   - Endpoints under `/api/cms/v2/sites/{site_key}/ab-tests`:
     - CRUD: List, Create, Get, Update, Delete
     - `POST /ab-tests/{id}/record-event`: Record event payload {variant, event_type, visitor_id}
     - `GET /ab-tests/{id}/results`: Return metrics: {views_a, views_b, clicks_a, clicks_b, conversion_rate_a, conversion_rate_b, statistical_significance}
   - Mount router in `backend/api/cms_v2/__init__.py`.

4. **Frontend Admin Page** (`frontend/src/app/plataforma/cms/ab-testing/page.tsx`):
   - Admin view listing active, paused, and completed tests.
   - Create test form: select page, section A, section B, split %, test name.
   - Results view: progress bars comparing views/clicks/conversions variant A vs B, winner badge if statistical_significance > 95%.
   - "Aplicar ganador" button: updates page layout to set winning section as primary.

5. **Navigation** (`frontend/src/components/cms/CmsModuleNav.tsx`):
   - Add tab for A/B Testing (`/plataforma/cms/ab-testing`) with `FlaskConical` icon from `lucide-react`.

6. **Public Section Renderer Integration** (`frontend/src/components/public/cms/PublicSectionRenderer.tsx`):
   - Check if section has active A/B test, determine variant A vs B based on `ab_visitor_id` cookie, render appropriate variant section.

7. **Verification**:
   - Run `cd /root/ccf/frontend && npx tsc --noEmit` -> 0 errors.
   - Run `cd /root/ccf && PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v` -> passed.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Write report to `/root/ccf/.agents/teamwork_preview_worker_m3/handoff.md` and notify orchestrator when done.

## 2026-07-31T00:01:46Z
Sender: fc6334ba-ffb9-4160-9578-53dfd4dae55e
Content: **Context**: Remediation required for UI contract violation in `frontend/src/app/plataforma/cms/ab-testing/page.tsx`.
**Content**: Forensic Auditor flagged an integrity violation because `tests/test_structural_contracts.py::test_platform_frontend_respects_ccf_ui_contracts` failed due to raw forbidden Tailwind color token `purple` (`bg-purple-500`, `text-purple-600`, `text-purple-400`, `accent-purple-600`, etc.) in `frontend/src/app/plataforma/cms/ab-testing/page.tsx`.
**Action**: In your M3 implementation of `frontend/src/app/plataforma/cms/ab-testing/page.tsx`, ensure NO `purple-*` Tailwind color classes are used. Replace all `purple-*` references with compliant tokens (e.g. `primary`, `indigo`, `blue`, `emerald`, `slate`, `zinc`, etc.) so `pytest tests/test_structural_contracts.py` passes 100% cleanly!
Note: `indigo`, `violet`, `purple` are ALL in `_raw_forbidden` of `test_structural_contracts.py`. Must use `blue`, `emerald`, `amber`, `sky`, `slate`, `zinc`, `cyan`, `primary`, etc.!
