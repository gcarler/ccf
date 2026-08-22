## 2026-07-30T17:32:52Z

You are teamwork_preview_challenger for Milestone 3 (Native Popups Backend R3-BE).
Your metadata working directory is `.agents/teamwork_preview_challenger_m3_1/`. Create this directory for your briefing and handoff files if needed.

Your objective:
Adversarially challenge and stress-test the backend Popups implementation (`backend/api/cms_v2/popups.py`, `CmsPopup` model, schemas, and migrations).

Verification focus areas:
1. Multi-tenant isolation: Verify site_key scoping prevents cross-site popup data leaks.
2. Permission enforcement: Verify unauthorized users receive 403 on admin endpoints.
3. Edge case filtering: Verify `GET /public/popups?site_key=X&page_slug=Y` correctly filters by `show_on_pages` (handling empty list `[]` as all pages vs explicit slug lists).
4. Schema validation: Verify invalid `trigger_type` strings, negative `trigger_value` numbers, or missing required fields return 422.
5. Migration integrity: Run `PYTHONPATH=. python3 -m alembic heads` to ensure revision chain is continuous.

Run tests and produce empirical evidence:
- `cd /root/ccf && PYTHONPATH=. python3 -m pytest tests/test_cms_v2_popups.py -v`
- Run any stress/boundary scripts if needed.

Deliverable:
Write your challenge report to `.agents/teamwork_preview_challenger_m3_1/handoff.md` with findings and empirical evidence. Send a message to orchestrator when completed.
