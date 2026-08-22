# Review Report — Milestone M2 (R2: Real-Time Presence Collaboration)

## Executive Summary
**Verdict**: REQUEST_CHANGES (FAIL)

The implementation of Milestone M2 (Real-Time Presence Collaboration) **FAILS** Acceptance Criterion #6 due to a test failure in `tests/test_cms_v2_presence.py::test_websocket_presence_flow`.

When attempting a WebSocket connection to `/api/cms/v2/ws/presence/...`, FastAPI fails to resolve the router-level `rate_limiter` dependency (`Depends(rate_limiter(limit=600, window_seconds=60))` in `backend/api/cms_v2/__init__.py`), raising:
`TypeError: rate_limiter.<locals>.dependency() missing 1 required positional argument: 'request'`

---

## Acceptance Criteria Checklist

| # | Criterion | Verification Method / Command | Status |
|---|---|---|---|
| 1 | `backend/api/cms_v2/presence.py` exists | `ls -la backend/api/cms_v2/presence.py` | PASS |
| 2 | WebSocket references in `presence.py` | `grep 'WebSocket\|websocket' backend/api/cms_v2/presence.py` (18 matches) | PASS |
| 3 | `frontend/src/hooks/usePresence.ts` exists | `ls -la frontend/src/hooks/usePresence.ts` | PASS |
| 4 | Presence references in Canvas UI | `grep -i 'presence\|presenceUsers\|editando' BuilderCanvas.tsx page.tsx` (13 matches) | PASS |
| 5 | TypeScript Compilation | `cd /root/ccf/frontend && npx tsc --noEmit` (0 errors) | PASS |
| 6 | Pytest Test Suite | `PYTHONPATH=. python3 -m pytest tests/test_cms_v2_presence.py tests/test_structural_contracts.py -v` | **FAIL** (1 failed: `test_websocket_presence_flow`) |

---

## Findings

### [Critical] Finding 1: WebSocket Connection Handshake Crash due to Router-Level Rate Limiter Dependency (`test_websocket_presence_flow` FAILED)

- **What**: Executing `PYTHONPATH=. python3 -m pytest tests/test_cms_v2_presence.py -v` fails on `test_websocket_presence_flow`.
- **Where**:
  - `backend/api/cms_v2/__init__.py` line 44: `router = APIRouter(prefix="/cms/v2", tags=["cms_v2"], dependencies=[Depends(rate_limiter(limit=600, window_seconds=60))])`
  - `backend/core/rate_limit.py` line 39: `async def dependency(request: Request = None) -> None:`
  - `tests/test_cms_v2_presence.py` line 57: `with client.websocket_connect(f"/api/cms/v2/ws/presence/main/home?token={token_user1}") as ws1:`
- **Why**: The top-level `APIRouter` in `backend/api/cms_v2/__init__.py` attaches `rate_limiter` as a default dependency to all sub-routers, including `presence.py`. `rate_limiter`'s inner `dependency` function specifies `request: Request = None`. When FastAPI processes a WebSocket connection (`@router.websocket`), the incoming connection object is a `WebSocket` instance (not a `Request` instance). FastAPI fails to match the `Request` type annotation for WebSockets and passes an empty keyword argument dictionary `call(**{})` to `dependency()`, resulting in:
  `TypeError: rate_limiter.<locals>.dependency() missing 1 required positional argument: 'request'`
- **Impact**: Any WebSocket connection attempt to `/api/cms/v2/ws/presence/...` crashes at connection handshake time in production and test environments.
- **Suggested Fix Direction**:
  Option 1: Update `rate_limiter` in `backend/core/rate_limit.py` to accept `HTTPConnection` or `Request | WebSocket | None`:
  ```python
  from starlette.requests import HTTPConnection

  def rate_limiter(limit: int = 5, window_seconds: int = 60):
      async def dependency(request: HTTPConnection | None = None) -> None:
          if request is None or not hasattr(request, "client"):
              return
          ...
  ```
  Option 2: Exclude WebSocket routes from router-level HTTP rate limiting (e.g. mounting presence WebSocket sub-router without router-level HTTP dependencies).

---

## Verified Claims & Verification Matrix

- `backend/api/cms_v2/presence.py` exists → verified via `ls` → PASS
- WebSocket endpoint definitions → verified via `grep` → PASS
- `frontend/src/hooks/usePresence.ts` exists → verified via `ls` → PASS
- BuilderCanvas & Page presence integration → verified via `grep` → PASS
- TypeScript check (`npx tsc --noEmit`) → 0 errors → PASS
- Pytest suite (`tests/test_cms_v2_presence.py`) → 1 failed (`test_websocket_presence_flow`) → **FAIL**

---

## Review Verdict
**REQUEST_CHANGES**
