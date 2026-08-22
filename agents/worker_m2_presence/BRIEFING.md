# BRIEFING — 2026-07-30T23:57:10Z

## Mission
Implement Milestone 2: R2 Real-Time Collaboration Presence (Backend WebSocket + REST endpoints, Frontend `usePresence` hook, and Presence UI component in CMS Builder).

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: /root/ccf/.agents/worker_m2_presence
- Original parent: 92b36264-1865-4585-935d-cbe1d12688ec
- Milestone: Milestone 2: R2 Real-Time Collaboration Presence

## 🔒 Key Constraints
- Minimal change principle.
- No cheating, hardcoding, or dummy implementations.
- Zero TypeScript errors (`npm run typecheck`).
- Fully genuine implementation with test suite.
- **Reglas CCF obligatorias**: Leer y aplicar `/root/ccf/AGENTS_RULES_CCF.md` ANTES de implementar. Todo código nuevo debe cumplir: backend (datetime.now(timezone.utc), sede_id kwonly, actor UUID, UUID PKs, soft deletes, HTTPException semánticos), frontend (apiFetch, /plataforma/, drawers NO modals, tokens semánticos hsl(var(--*)), clsx, DS* components), DB (migraciones reversibles, no editar cerradas).
- **Drawers NO modals**: Flujos create/edit/view usan drawers (SidePanel, RightPanel, UniversalCreationDrawer), NO modals/AlertDialog. Excepción: confirmaciones de delete pueden usar AlertDialog.
- **Lint obligatorio**: Ejecutar `cd /root/ccf/frontend && npm run lint -- --max-warnings=0` antes de commit.
- **Venv para pytest**: Ejecutar `cd /root/ccf && ./venv/bin/python -m pytest` (no `python3` directo).
- **Sistema task**: Registrar T1 + sub-tareas en el sistema task ANTES de codear.

## Current Parent
- Conversation ID: 92b36264-1865-4585-935d-cbe1d12688ec
- Updated: 2026-07-30T23:57:10Z

## Task Summary
- **What to build**: Real-time collaboration presence system for CMS Builder.
  - Backend: WebSocket `/api/cms/v2/ws/presence/{site_key}/{slug}` + REST `GET /api/cms/v2/sites/{site_key}/pages/{slug}/presence`.
  - Frontend Hook: `usePresence.ts` (WebSocket connection with exponential backoff 1s, 2s, 4s, state management).
  - Frontend UI: Presence Avatar Bar in CMS Builder header (+N indicator, tooltips, "X personas editando ahora").
- **Success criteria**:
  - WebSocket & REST APIs functioning.
  - Real-time updates on join/leave/disconnect.
  - Automatic reconnection backoff.
  - 0 TS errors (`npm run typecheck`), all backend & frontend tests passing.
- **Interface contracts**: REST and WebSocket contracts described in prompt.

## Key Decisions Made
- Wired `_presence_mod.router` into `backend/api/cms_v2/__init__.py` and mounted under `/api/cms/v2`.
- Ensured WebSocket query token parsing supports JWT, JSON object tokens, and plain text IDs.
- Implemented `usePresence` hook with automatic backoff reconnection logic (1s, 2s, 4s delays).
- Added Presence UI header avatar bar in `BuilderCanvas.tsx` displaying initials, deterministic avatar background colors, full name tooltips, "+N más" overflow indicator, and active editor count label.
- Added comprehensive pytest test suite (`tests/test_cms_v2_presence.py`) and vitest unit tests (`usePresence.test.ts`, `PresenceUI.test.tsx`, `BuilderCanvas.test.tsx`).

## Artifact Index
- /root/ccf/.agents/worker_m2_presence/ORIGINAL_REQUEST.md — Initial user request
- /root/ccf/.agents/worker_m2_presence/progress.md — Progress heartbeat log
- /root/ccf/.agents/worker_m2_presence/handoff.md — Final handoff report

## Change Tracker
- **Files modified**:
  - `backend/api/cms_v2/presence.py` — Backend WebSocket and REST router for page presence.
  - `backend/api/cms_v2/__init__.py` — Router mounting for presence endpoints.
  - `backend/core/rate_limit.py` — Parameter default fix for rate_limiter dependency.
  - `frontend/src/hooks/usePresence.ts` — React hook for presence state & WS lifecycle.
  - `frontend/src/components/cms/builder/BuilderCanvas.tsx` — Presence avatar bar UI header element.
  - `tests/test_cms_v2_presence.py` — Pytest backend presence test suite.
  - `frontend/src/hooks/__tests__/usePresence.test.ts` — Vitest unit tests for usePresence hook.
  - `frontend/src/components/cms/builder/__tests__/PresenceUI.test.tsx` — Vitest unit tests for presence UI.
  - `frontend/src/components/cms/builder/BuilderCanvas.test.tsx` — Updated mock context for AuthContext.
- **Build status**: PASS (0 TypeScript errors, 21 frontend vitest tests PASS, 3 backend pytest tests PASS).
- **Pending issues**: None.

## Quality Status
- **Build/test result**: All tests passing (pytest: 3/3 PASS, vitest: 21/21 PASS).
- **Lint status**: 0 TypeScript errors (`npm run typecheck`).
- **Tests added/modified**: `tests/test_cms_v2_presence.py`, `usePresence.test.ts`, `PresenceUI.test.tsx`.

## Loaded Skills
None
