# Milestone 2 (R2: Real-Time Collaboration Presence) Review Report

**Verdict**: APPROVE

---

## 1. Observation

- **Backend Presence Module (`backend/api/cms_v2/presence.py`)**:
  - Contains WebSocket endpoint `WS /api/cms/v2/ws/presence/{site_key}/{slug}` (lines 208–234) and REST endpoint `GET /api/cms/v2/sites/{site_key}/pages/{slug}/presence` (lines 236–240).
  - Implements `PresenceManager` (lines 133–203) with in-memory room mapping `(site_key, slug) -> {WebSocket: user_dict}`.
  - Features real-time connection management, user token parsing via JWT / JSON / string fallbacks (`_parse_user_from_token`, lines 56–130), stale socket cleanup during broadcasts (lines 191–202), ping/pong heartbeats, and unique presence user deduplication (lines 161–176).

- **Sub-router Mounting (`backend/api/cms_v2/__init__.py`)**:
  - Mounted presence sub-router at line 130–132 (`from backend.api.cms_v2 import presence as _presence_mod; router.include_router(_presence_mod.router)`), under the main `/cms/v2` router prefix.

- **Frontend Hook (`frontend/src/hooks/usePresence.ts`)**:
  - Implements `usePresence({ siteKey, slug, token, user })` hook.
  - Constructs WebSocket connection URL (`/api/cms/v2/ws/presence/${encodedSiteKey}/${encodedSlug}`) with token query param.
  - Full connection lifecycle management (`onopen`, `onmessage`, `onerror`, `onclose`) with unmount cleanup (`isMountedRef`, `clearTimeout`, `socket.close()`).
  - Implements exponential backoff reconnection schedule: `RECONNECT_DELAYS = [1000, 2000, 4000]` (lines 32, 153–163).

- **Frontend UI Rendering (`frontend/src/components/cms/builder/BuilderCanvas.tsx` & `page.tsx`)**:
  - Integrated `usePresence` in `BuilderCanvas.tsx` (lines 410–415).
  - Renders live user avatar stack with custom background colors, initials, hover tooltips showing user full name, overflow counter (`+N más`), and real-time active editor counter (lines 449–477).

- **Verification Command 1 (TypeScript Typecheck)**:
  - Executed `cd /root/ccf/frontend && npx tsc --noEmit`
  - Output: Exit code 0, 0 errors.

- **Verification Command 2 (Pytest Suite)**:
  - Executed `cd /root/ccf && PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py tests/test_cms_v2_presence.py -v`
  - Output: 46 passed, 1 skipped (docker-compose test skipped as expected) in 16.82s. All tests in `test_cms_v2_presence.py` (`test_token_parsing_helper`, `test_rest_presence_empty`, `test_websocket_presence_flow`) and structural contract tests passed cleanly.

---

## 2. Logic Chain

1. **Verification of Backend WebSocket & REST Contracts**:
   - The REST route `GET /api/cms/v2/sites/{site_key}/pages/{slug}/presence` and WS route `WS /api/cms/v2/ws/presence/{site_key}/{slug}` match the specified paths and API prefix rules.
   - User token decoding supports JWT authentication as well as fallback JSON/string tokens, computing initials and deterministic hex avatar colors reliably.
   - When a WebSocket disconnects or throws an error, `PresenceManager.disconnect` removes the socket and broadcasts the updated presence list to all remaining subscribers in that room.
   - Stale socket cleanup in `broadcast_presence` prevents memory leaks or broken pipe exceptions when clients drop ungracefully.

2. **Verification of Frontend Hook & Reconnection**:
   - The `usePresence` hook properly cleans up active WebSockets and timeout timers when page parameters change or components unmount.
   - Backoff retry delay accurately uses the `[1000, 2000, 4000]` sequence and caps at 4s for subsequent retry attempts, resetting to 0 upon successful reconnection (`onopen`).

3. **Verification of Frontend UI**:
   - The presence avatar bar in `BuilderCanvas.tsx` correctly visualizes presence users, truncates stack to 4 avatars with `+N` badge for larger numbers, and dynamically displays count messages.

4. **Integrity & Code Quality Verification**:
   - Verified that no hardcoded outputs, fake implementations, or architectural contract violations exist.
   - TypeScript type checking and Python unit tests both pass without warnings or errors.

---

## 3. Caveats

- In-memory presence management (`PresenceManager`) operates per backend process instance. In a multi-node load-balanced backend cluster, cross-node socket broadcasting would require a Redis pub/sub broker; for single-instance / current process deployment, in-memory state is complete and correct.

---

## 4. Conclusion

Milestone 2 (R2: Real-Time Collaboration Presence) is fully compliant, robust, and verified against all required functional, structural, type, and testing criteria.

**Final Recommendation**: APPROVE.

---

## 5. Verification Method

To independently verify this review:

1. **TypeScript Typecheck**:
   ```bash
   cd /root/ccf/frontend && npx tsc --noEmit
   ```
2. **Pytest Presence & Structural Suite**:
   ```bash
   cd /root/ccf && PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py tests/test_cms_v2_presence.py -v
   ```
