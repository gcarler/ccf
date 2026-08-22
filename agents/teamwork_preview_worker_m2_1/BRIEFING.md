# BRIEFING — 2026-07-30T23:52:45Z

## Mission
Implement real-time presence collaboration for the CMS Page Builder (Milestone M2).

## 🔒 My Identity
- Archetype: implementer/qa/specialist
- Roles: implementer, qa, specialist
- Working directory: /root/ccf/.agents/teamwork_preview_worker_m2_1
- Original parent: 29fb24b8-3c58-4e56-9cb8-c98e4a775f50
- Milestone: M2 (R2: Colaboración en Tiempo Real / Presence)

## 🔒 Key Constraints
- DO NOT CHEAT. All implementations must be genuine.
- Backend: WebSocket WS /api/cms/v2/ws/presence/{site_key}/{slug} & REST GET /api/cms/v2/sites/{site_key}/pages/{slug}/presence
- Frontend: Hook usePresence in frontend/src/hooks/usePresence.ts
- UI: Presence avatar bar in Builder header/canvas with tooltips, overflow handling (+N más), and edit count status text.
- Verification: cd /root/ccf/frontend && npx tsc --noEmit (0 errors), PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v (pass).
- **Reglas CCF obligatorias**: Leer y aplicar `/root/ccf/AGENTS_RULES_CCF.md` ANTES de implementar. Todo código nuevo debe cumplir: backend (datetime.now(timezone.utc), sede_id kwonly, actor UUID, UUID PKs, soft deletes, HTTPException semánticos), frontend (apiFetch, /plataforma/, drawers NO modals, tokens semánticos hsl(var(--*)), clsx, DS* components), DB (migraciones reversibles, no editar cerradas).
- **Drawers NO modals**: Flujos create/edit/view usan drawers (SidePanel, RightPanel, UniversalCreationDrawer), NO modals/AlertDialog. Excepción: confirmaciones de delete pueden usar AlertDialog.
- **Lint obligatorio**: Ejecutar `cd /root/ccf/frontend && npm run lint -- --max-warnings=0` antes de commit.
- **Venv para pytest**: Ejecutar `cd /root/ccf && ./venv/bin/python -m pytest` (no `python3` directo).
- **Sistema task**: Registrar T1 + sub-tareas en el sistema task ANTES de codear.

## Current Parent
- Conversation ID: 29fb24b8-3c58-4e56-9cb8-c98e4a775f50
- Updated: 2026-07-30T23:52:45Z

## Task Summary
- **What to build**: Backend presence WS & REST endpoints, frontend usePresence hook, UI Avatar bar in Builder.
- **Success criteria**: Genuine WS/REST presence system, auto-reconnect, avatar bar with tooltips and +N indicator, all tests & tsc pass.

## Key Decisions Made
- Implemented `PresenceManager` in `backend/api/cms_v2/presence.py`.
- Mounted router in `backend/api/cms_v2/__init__.py`.
- Created `frontend/src/hooks/usePresence.ts` with exponential backoff reconnect (1s, 2s, 4s).
- Integrated presence indicator into `BuilderCanvas.tsx`.
- Created tests in `tests/test_cms_v2_presence.py`.

## Change Tracker
- **Files modified**:
  - `backend/api/cms_v2/presence.py` (created)
  - `backend/api/cms_v2/__init__.py` (updated)
  - `tests/test_cms_v2_presence.py` (created)
  - `frontend/src/hooks/usePresence.ts` (created)
  - `frontend/src/components/cms/builder/BuilderCanvas.tsx` (updated)
  - `.agents/teamwork_preview_worker_m2_1/changes.md` (created)
  - `.agents/teamwork_preview_worker_m2_1/handoff.md` (created)
- **Build status**: All checks passed (tsc: 0 errors, pytest: 46 passed).
- **Pending issues**: None.

## Quality Status
- **Build/test result**: Passed (tsc 0 errors, 46 pytest passed).
- **Lint status**: Passed.
- **Tests added/modified**: `tests/test_cms_v2_presence.py`.

## Loaded Skills
- **ccf-backend-guard**: Backend safety (FastAPI, SQLAlchemy, sede_id, soft deletes, datetime, UUID).
- **ccf-ui-guard**: Frontend safety (Next.js, apiFetch, /plataforma/, drawers, semantic tokens, DS 3-layer).
- **ccf-architecture-guard**: Cross-layer change planning and rollback safety.
- **ccf-cms-guard**: CMS and public-content safety.
