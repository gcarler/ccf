## 2026-07-30T23:53:03Z
<USER_REQUEST>
You are a Worker subagent assigned to implement Milestone 2: R2 Real-Time Collaboration Presence.
Your working directory is: /root/ccf/.agents/worker_m2_presence

Detailed Requirements:
1. Backend Router (`backend/api/cms_v2/presence.py`):
   - WebSocket endpoint: `WS /api/cms/v2/ws/presence/{site_key}/{slug}`
     - Authenticates user token from query param `?token=X`.
     - Maintains in-memory active connection manager tracking present users `{user_id, name, avatar_initials, color}` grouped by `(site_key, slug)`.
     - Broadcasts active user list to all connected clients on join, leave, or disconnect.
   - REST endpoint: `GET /api/cms/v2/sites/{site_key}/pages/{slug}/presence`
     - Returns JSON list of currently active users on the page `[{id, name, avatar_initials, color}]`.
   - Register router in `backend/app.py` or `backend/api/cms_v2/__init__.py`.

2. Frontend Hook (`frontend/src/hooks/usePresence.ts`):
   - Accepts `{ siteKey, slug, token, user }`.
   - Establishes WebSocket connection to `ws(s)://${location.host}/api/cms/v2/ws/presence/${siteKey}/${slug}?token=${token}`.
   - Maintains state `presenceUsers: Array<{ id: string; name: string; color: string; initials: string }>`.
   - Reconnects automatically with backoff (1s, 2s, 4s) on connection drop.
   - Cleans up WebSocket connection on unmount.

3. Frontend UI (`frontend/src/components/cms/builder/BuilderCanvas.tsx` or `frontend/src/app/plataforma/cms/builder/page.tsx`):
   - Renders avatar presence bar in top right corner of builder canvas header.
   - Shows colored avatar circles with user initials and hover tooltip displaying full name.
   - Renders `+N más` indicator if >4 active users.
   - Displays label `"X personas editando ahora"` (or `"X persona editando ahora"` if 1).

4. Testing & Typecheck:
   - Run `cd /root/ccf/frontend && npm run typecheck` to ensure 0 TypeScript errors.
   - Write backend tests in `tests/test_cms_v2_presence.py` and frontend vitest tests for `usePresence.ts` / presence UI.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Upon completion, write a detailed handoff report to `/root/ccf/.agents/worker_m2_presence/handoff.md`.
</USER_REQUEST>
