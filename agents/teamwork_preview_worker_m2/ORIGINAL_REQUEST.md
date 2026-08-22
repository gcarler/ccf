## 2026-07-30T23:55:08Z

<USER_REQUEST>
You are teamwork_preview_worker_m2, a software engineering worker.
Working directory: /root/ccf/.agents/teamwork_preview_worker_m2
Project root: /root/ccf

Your task is Milestone 2 (R2: Real-Time Collaboration Presence):

1. **Backend** (`backend/api/cms_v2/presence.py`):
   - Create WebSocket endpoint: `WS /api/cms/v2/ws/presence/{site_key}/{slug}`
   - Accept connection, authenticate/extract user info via query param `?token=X` (or decode token / fallback user info).
   - Maintain an in-memory presence registry per `{site_key}/{slug}` containing dict of connected users: `{id, name, avatar_initials, color}`. Assign a consistent color (e.g. from a vibrant palette) and initial letters.
   - On connection: register user, broadcast full active presence user list to all connected WebSocket clients on that `{site_key}/{slug}`.
   - On disconnect: unregister user, broadcast updated active presence user list.
   - Create REST endpoint: `GET /api/cms/v2/sites/{site_key}/pages/{slug}/presence` returning active users list.
   - Mount router in `backend/api/cms_v2/__init__.py`.

2. **Frontend Hook** (`frontend/src/hooks/usePresence.ts`):
   - Create hook accepting `{siteKey, slug, token, user}`.
   - Establishes WebSocket connection to `ws(s)://${window.location.host}/api/cms/v2/ws/presence/${siteKey}/${slug}?token=${token}` (or equivalent backend URL).
   - Manages state `presenceUsers`: list of `{id, name, color, initials}`.
   - Reconnection logic with backoff (1s, 2s, 4s) on unexpected disconnect.
   - Proper WebSocket close on component unmount.

3. **UI in Builder** (`frontend/src/components/cms/builder/BuilderCanvas.tsx` or `frontend/src/app/plataforma/cms/builder/page.tsx`):
   - Include presence bar in top right corner of builder canvas/page.
   - Displays circles with background color + initials for present users.
   - Tooltip on hover showing full name.
   - Displays `+N más` if more than 4 users are present.
   - Displays small text `"X personas editando ahora"` beside avatars (e.g. "1 persona editando ahora" or "X personas editando ahora").

4. **Verification**:
   - Run `cd /root/ccf/frontend && npx tsc --noEmit` -> 0 errors.
   - Run `cd /root/ccf && PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v` -> passed.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Write report to `/root/ccf/.agents/teamwork_preview_worker_m2/handoff.md` and notify orchestrator when done.
</USER_REQUEST>
