# Forensic Audit Report — Milestone M2 (R2: Real-Time Presence Collaboration)

**Work Product**:
- `backend/api/cms_v2/presence.py`
- `frontend/src/hooks/usePresence.ts`
- `frontend/src/components/cms/builder/BuilderCanvas.tsx`

**Profile**: General Project / Integrity Forensics
**Verdict**: INTEGRITY VIOLATION

---

## Executive Summary

An independent forensic audit was conducted on Milestone M2 (Real-Time Presence Collaboration). While the source code in `presence.py`, `usePresence.ts`, and `BuilderCanvas.tsx` does NOT contain hardcoded test results, facades, or cheating, **behavioral verification failed**. Specifically, WebSocket connections to `/api/cms/v2/ws/presence/...` crash at runtime due to an incompatibility with the parent `cms_v2` router's `rate_limiter` dependency. As a result, the automated backend test `test_websocket_presence_flow` in `tests/test_cms_v2_presence.py` fails with a `TypeError`. Additionally, a reconnect loop bug was identified in `usePresence.ts`.

Per Forensic Audit rules ("a project that doesn't build or whose tests don't run is automatically flagged"), the verdict is **INTEGRITY VIOLATION**.

---

## Phase Results

| # | Check Name | Status | Details |
|---|------------|--------|---------|
| 1 | Hardcoded output & Facade detection | **PASS** | Source code analysis confirmed genuine logic in `PresenceManager`, `usePresence`, and `BuilderCanvas`. No dummy return values or hardcoded test strings. |
| 2 | REST Endpoint Implementation | **PASS** | `GET /api/cms/v2/sites/{site_key}/pages/{slug}/presence` is implemented and verified. Returns active users tracked by `PresenceManager`. |
| 3 | UI Presence Components | **PASS** | `BuilderCanvas.tsx` correctly renders user avatars with initials, assigned colors, hover tooltips with names, `+N más` indicator for >4 users, and `"X personas editando ahora"` text. |
| 4 | React Hook `usePresence.ts` | **FAIL** | Implements backoff `[1000, 2000, 4000]` and WebSocket event handling, but contains a bug where calling `socketRef.current.close()` inside `connectWebSocket()` triggers `onclose` without clearing handlers, causing cascading reconnect timers. |
| 5 | Behavioral Test Suite Execution | **FAIL** | `pytest tests/test_cms_v2_presence.py` failed during `test_websocket_presence_flow`. FastAPI dependency resolution crashes on WebSocket routes mounted under `cms_v2` router. |

---

## Forensic Investigation Findings

### Finding 1: Runtime Crash on WebSocket Connection (Backend Integration Issue)
- **Location**: `backend/api/cms_v2/__init__.py` & `backend/api/cms_v2/presence.py`
- **Issue**: `cms_v2.router` defines global dependencies: `dependencies=[Depends(rate_limiter(limit=600, window_seconds=60))]`. The `rate_limiter` dependency in `backend/core/rate_limit.py` expects a FastAPI `Request` object (`async def dependency(request: Request = None)`).
- **Impact**: When a WebSocket connection request arrives at `@router.websocket("/ws/presence/{site_key}/{slug}")`, FastAPI attempts to inject `Request` into `rate_limiter`. Because WebSocket connections pass a `WebSocket` scope instead of `Request`, FastAPI raises:
  `TypeError: rate_limiter.<locals>.dependency() missing 1 required positional argument: 'request'`
- **Evidence**: `test_websocket_presence_flow` in `tests/test_cms_v2_presence.py` fails on connection context entry.

### Finding 2: Cascading Reconnect Timers (Frontend Hook Issue)
- **Location**: `frontend/src/hooks/usePresence.ts`
- **Issue**: In `connectWebSocket()`, existing socket `socketRef.current` is closed via `socketRef.current.close()`. However, `socketRef.current.onclose` handler is not set to `null` prior to closing.
- **Impact**: Closing the old socket triggers its `onclose` callback, which schedules another reconnect timer via `setTimeout` and increments `retryCountRef.current`. This creates duplicate parallel reconnect loops upon socket reset or unmount.

---

## Raw Empirical Evidence

### 1. Pytest Failure Log (`tests/test_cms_v2_presence.py`)

```
=================================== FAILURES ===================================
_________________________ test_websocket_presence_flow _________________________

    def test_websocket_presence_flow():
        """Test WebSocket connection, presence broadcast, and disconnection."""
        client = TestClient(app)
        token_user1 = json.dumps({"user_id": "usr-1", "name": "Carlos Gomez", "color": "#10B981", "avatar_initials": "CG"})
        token_user2 = json.dumps({"user_id": "usr-2", "name": "Elena Diaz", "color": "#EF4444", "avatar_initials": "ED"})

        # Client 1 connects
>       with client.websocket_connect(f"/api/cms/v2/ws/presence/main/home?token={token_user1}") as ws1:

tests/test_cms_v2_presence.py:57:
...
/usr/local/lib/python3.12/dist-packages/fastapi/dependencies/utils.py:678:
E   TypeError: rate_limiter.<locals>.dependency() missing 1 required positional argument: 'request'
```

### 2. Vitest Test Log (`BuilderCanvas.test.tsx`)

```
 RUN  v1.6.1 /root/ccf/frontend

 · src/components/cms/builder/BuilderCanvas.test.tsx (13)
   ✓ renders the canvas toolbar and empty state
   ✓ renders sections and marks the active one
   ✓ toggles canvas mode and preview device
   ✓ calls addSection when clicking Añadir
   ✓ disables add section when canEdit is false
   ✓ calls moveSection with up/down direction
   ✓ renders the scroll heatmap overlay when enabled
   ✓ renders the clicks heatmap overlay when enabled
   ✓ renders the attention heatmap overlay when enabled
   ✓ switches to render preview when canvasMode is render
   ✓ reloads theme when the reload button is clicked
   ✓ updates newSectionType when selecting a section type
   ✓ disables move up for the first section and move down for the last section

 Test Files  1 passed (1)
      Tests  13 passed (13)
```

---

## Recommended Remediation (For Implementer Team)

1. **Fix Backend Rate Limiter for WebSockets**:
   In `backend/core/rate_limit.py`, update `rate_limiter` dependency signature to accept `Request | WebSocket`:
   `async def dependency(request: Request | WebSocket = None) -> None:`
   Or declare `presence.py` router independently without inheriting the `cms_v2` HTTP rate_limiter dependency.

2. **Fix `usePresence.ts` Socket Cleanup**:
   In `frontend/src/hooks/usePresence.ts`, nullify `onclose` before closing sockets:
   ```ts
   if (socketRef.current) {
     socketRef.current.onclose = null;
     socketRef.current.close();
     socketRef.current = null;
   }
   ```
