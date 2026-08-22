## 2026-07-30T23:50:07Z
You are a Worker subagent for Milestone M2 (R2: Colaboración en Tiempo Real / Presence).
Working Directory: /root/ccf/.agents/teamwork_preview_worker_m2_1/
Project root: /root/ccf

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your objective is to implement real-time presence collaboration for the CMS Page Builder:

1. **Backend (`backend/api/cms_v2/presence.py`)**:
   - Create `backend/api/cms_v2/presence.py`.
   - Implement WebSocket endpoint `WS /api/cms/v2/ws/presence/{site_key}/{slug}`:
     - Authenticate via query param `?token=X` (decode JWT / token or extract user payload `{user_id, name, avatar_initials, color}`).
     - Maintain an in-memory active connection manager / dictionary keyed by `(site_key, slug)`.
     - Upon connection: add user to the set/list, broadcast current list of present users to all clients connected to `(site_key, slug)`.
     - Upon disconnect: remove user from set/list, broadcast updated presence list.
   - Implement REST endpoint `GET /api/cms/v2/sites/{site_key}/pages/{slug}/presence`:
     - Returns `{presence_users: [{user_id, name, avatar_initials, color}, ...]}` for the specified page.
   - Mount/register `presence.router` in `backend/api/cms_v2/__init__.py` or `backend/app.py`.

2. **Frontend Hook (`frontend/src/hooks/usePresence.ts`)**:
   - Create `frontend/src/hooks/usePresence.ts`.
   - Export hook `usePresence({ siteKey, slug, token, user })`:
     - Establishes WebSocket connection to `ws(s)://.../api/cms/v2/ws/presence/${siteKey}/${slug}?token=${token}`.
     - Maintains state `presenceUsers: Array<{ id: string; name: string; color: string; initials: string }>` (or matching structure).
     - Handles incoming WS messages (presence state updates).
     - Features automatic reconnect with backoff (1s, 2s, 4s).
     - Proper cleanup on unmount.

3. **UI in Builder (`BuilderCanvas.tsx` / `builder/page.tsx`)**:
   - Integrate `usePresence` hook into `BuilderCanvas.tsx` or `builder/page.tsx`.
   - Render presence avatar bar in top-right area of canvas / builder header:
     - Avatar circles showing `initials` with `color` background.
     - Hover tooltip displaying user's full `name`.
     - If > 4 users, render first 4 avatars + `+N más` indicator badge.
     - Small text `"X personas editando ahora"` (or `"1 persona editando ahora"`) next to avatars.

4. **Verification**:
   - `cd /root/ccf/frontend && npx tsc --noEmit` (0 errors).
   - `PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v` (passed).

Report your changes in `/root/ccf/.agents/teamwork_preview_worker_m2_1/changes.md` and handoff report in `/root/ccf/.agents/teamwork_preview_worker_m2_1/handoff.md`.
Then send a message back to parent with a summary of work completed.
