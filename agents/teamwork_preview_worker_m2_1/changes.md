# Summary of Changes — Milestone M2 (Real-Time Presence Collaboration)

## 1. Backend Implementation (`backend/api/cms_v2/presence.py`)
- Created `backend/api/cms_v2/presence.py`.
- Implemented `PresenceManager` in-memory connection manager mapping `(site_key, slug)` to active WebSocket clients.
- Implemented WebSocket endpoint `WS /api/cms/v2/ws/presence/{site_key}/{slug}` with `?token=X` query param authentication (decodes JWT, JSON payload, or plain ID token to produce standard user presence dict containing `user_id`, `id`, `name`, `avatar_initials`, `initials`, `color`).
- Implemented automatic presence broadcasting upon client connect and disconnect.
- Implemented REST endpoint `GET /api/cms/v2/sites/{site_key}/pages/{slug}/presence` returning `{presence_users: [...]}`.
- Mounted `presence.router` in `backend/api/cms_v2/__init__.py`.

## 2. Backend Automated Tests (`tests/test_cms_v2_presence.py`)
- Created `tests/test_cms_v2_presence.py` testing token decoding, empty presence REST response, WebSocket connections, real-time presence broadcasts, and multi-user connect/disconnect lifecycle.

## 3. Frontend Custom Hook (`frontend/src/hooks/usePresence.ts`)
- Created `frontend/src/hooks/usePresence.ts`.
- Exported `usePresence({ siteKey, slug, token, user })` hook.
- Connects to `ws(s)://.../api/cms/v2/ws/presence/${siteKey}/${slug}?token=${token}`.
- Maintains `presenceUsers` state list normalized with user attributes.
- Implemented automatic reconnect with exponential backoff (1s, 2s, 4s).
- Implemented strict cleanup on unmount to close active sockets and cancel pending timers.

## 4. CMS Builder UI Integration (`frontend/src/components/cms/builder/BuilderCanvas.tsx`)
- Integrated `usePresence` hook into `BuilderCanvas.tsx`.
- Added presence avatar bar in top header area of canvas:
  - Avatar circles showing initials with color background.
  - Hover tooltips displaying full user name.
  - Overflow indicator badge `+N más` when > 4 present users.
  - Status text `"1 persona editando ahora"` / `"X personas editando ahora"`.

## 5. Verification Results
- `cd /root/ccf/frontend && npx tsc --noEmit`: PASSED (0 errors).
- `PYTHONPATH=. python3 -m pytest tests/test_cms_v2_presence.py tests/test_structural_contracts.py -v`: PASSED (46 passed, 1 skipped).
