# BRIEFING — 2026-07-30T23:58:18Z

## Mission
Independently review Milestone 2 (R2: Real-Time Collaboration Presence) for correctness, edge cases, error handling, WebSocket lifecycle, exponential backoff reconnection, UI rendering, layout compliance, and integrity violations.

## 🔒 My Identity
- Archetype: reviewer / critic
- Roles: reviewer, critic
- Working directory: /root/ccf/.agents/teamwork_preview_reviewer_m2_1
- Original parent: fc6334ba-ffb9-4160-9578-53dfd4dae55e
- Milestone: Milestone 2 (R2: Real-Time Collaboration Presence)
- Instance: 1 of 1

## 🔒 Key Constraints
- Review-only — do NOT modify implementation code
- Perform adversarial checking for integrity violations, edge cases, and compliance
- Do not run external HTTP commands (CODE_ONLY network mode)
- **Reglas CCF obligatorias**: Leer y aplicar `/root/ccf/AGENTS_RULES_CCF.md`. Verificar TODO el checklist de la sección 6, no solo grep de features.
- **Lint obligatorio**: Ejecutar `cd /root/ccf/frontend && npm run lint -- --max-warnings=0` además de typecheck. Es criterio transversal CCF.
- **Venv para pytest**: Ejecutar `cd /root/ccf && ./venv/bin/python -m pytest` (no `python3` directo).

## Current Parent
- Conversation ID: fc6334ba-ffb9-4160-9578-53dfd4dae55e
- Updated: 2026-07-30T23:58:18Z

## Review Scope
- **Files to review**:
  - `backend/api/cms_v2/presence.py`
  - `backend/api/cms_v2/__init__.py`
  - `frontend/src/hooks/usePresence.ts`
  - `frontend/src/components/cms/builder/BuilderCanvas.tsx`
  - `frontend/src/app/plataforma/cms/builder/page.tsx`
- **Verification Commands**:
  - `cd /root/ccf/frontend && npx tsc --noEmit`
  - `cd /root/ccf && PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py tests/test_cms_v2_presence.py -v`

## Key Decisions Made
- Completed inspection of backend presence routes, sub-router mounting, frontend hook, and canvas UI components.
- Ran TypeScript typecheck (`npx tsc --noEmit` -> 0 errors).
- Ran Pytest suite (`pytest tests/test_structural_contracts.py tests/test_cms_v2_presence.py -v` -> 46 passed, 1 skipped).
- Issued review decision: APPROVE.

## Artifact Index
- `/root/ccf/.agents/teamwork_preview_reviewer_m2_1/ORIGINAL_REQUEST.md` — Original request log
- `/root/ccf/.agents/teamwork_preview_reviewer_m2_1/BRIEFING.md` — Working memory briefing
- `/root/ccf/.agents/teamwork_preview_reviewer_m2_1/progress.md` — Heartbeat progress log
- `/root/ccf/.agents/teamwork_preview_reviewer_m2_1/handoff.md` — Handoff and review report

## Review Checklist
- **Items reviewed**: `backend/api/cms_v2/presence.py`, `backend/api/cms_v2/__init__.py`, `frontend/src/hooks/usePresence.ts`, `frontend/src/components/cms/builder/BuilderCanvas.tsx`, `frontend/src/app/plataforma/cms/builder/page.tsx`
- **Verdict**: APPROVE
- **Unverified claims**: none

## Loaded Skills
- **ccf-backend-guard**: Backend safety (FastAPI, SQLAlchemy, sede_id, soft deletes, datetime, UUID).
- **ccf-ui-guard**: Frontend safety (Next.js, apiFetch, /plataforma/, drawers, semantic tokens, DS 3-layer).
- **ccf-architecture-guard**: Cross-layer change planning and rollback safety.

## Attack Surface
- **Hypotheses tested**: WebSocket lifecycle, stale socket cleanup, token parsing robustness, backoff timing logic, frontend rendering and unmount safety. All confirmed robust.
- **Vulnerabilities found**: none.
- **Untested angles**: Multi-node backend Redis pub/sub sync (out of scope for single process).
