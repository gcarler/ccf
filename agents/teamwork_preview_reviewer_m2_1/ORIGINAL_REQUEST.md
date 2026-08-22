## 2026-07-30T23:58:17Z
You are teamwork_preview_reviewer_m2_1, a high-reliability code reviewer.
Working directory: /root/ccf/.agents/teamwork_preview_reviewer_m2_1
Project root: /root/ccf

Your objective is to independently review Milestone 2 (R2: Real-Time Collaboration Presence):
- Inspect `backend/api/cms_v2/presence.py` (WebSocket route `WS /api/cms/v2/ws/presence/{site_key}/{slug}` and REST route `GET /api/cms/v2/sites/{site_key}/pages/{slug}/presence`).
- Inspect `backend/api/cms_v2/__init__.py` router mounting.
- Inspect `frontend/src/hooks/usePresence.ts`.
- Inspect `frontend/src/components/cms/builder/BuilderCanvas.tsx` / `frontend/src/app/plataforma/cms/builder/page.tsx`.

Verify:
1. Correctness, edge cases, error handling, WebSocket lifecycle (connect, broadcast, disconnect), exponential backoff reconnection (1s, 2s, 4s), and UI rendering.
2. Run `cd /root/ccf/frontend && npx tsc --noEmit` -> 0 errors.
3. Run `cd /root/ccf && PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py tests/test_cms_v2_presence.py -v` -> all passed.

Write review report to `/root/ccf/.agents/teamwork_preview_reviewer_m2_1/handoff.md` and send review decision (APPROVE or REJECT).
