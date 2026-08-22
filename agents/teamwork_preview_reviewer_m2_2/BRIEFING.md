# BRIEFING — 2026-07-30T23:56:05Z

## Mission
Re-review M2: Real-Time Presence Collaboration implementation, verify WebSocket rate limiting fixes, run tests, and assess integrity/quality.

## 🔒 My Identity
- Archetype: Reviewer / Critic
- Roles: reviewer, critic
- Working directory: /root/ccf/.agents/teamwork_preview_reviewer_m2_2
- Original parent: 29fb24b8-3c58-4e56-9cb8-c98e4a775f50
- Milestone: M2 (Re-review of R2)
- Instance: 1 of 1

## 🔒 Key Constraints
- Review-only — do NOT modify implementation code
- Perform required check items 1-6
- Inspect for integrity violations (hardcoded tests, dummy facades, shortcuts, self-certifying work)
- Produce review.md and handoff.md in working directory
- Send verdict to parent agent via send_message
- **Reglas CCF obligatorias**: Leer y aplicar `/root/ccf/AGENTS_RULES_CCF.md`. Verificar TODO el checklist de la sección 6, no solo grep de features.
- **Lint obligatorio**: Ejecutar `cd /root/ccf/frontend && npm run lint -- --max-warnings=0` además de typecheck. Es criterio transversal CCF.
- **Venv para pytest**: Ejecutar `cd /root/ccf && ./venv/bin/python -m pytest` (no `python3` directo).

## Current Parent
- Conversation ID: 29fb24b8-3c58-4e56-9cb8-c98e4a775f50
- Updated: 2026-07-30T23:56:05Z

## Review Scope
- **Files to review**: `backend/api/cms_v2/presence.py`, `frontend/src/hooks/usePresence.ts`, `frontend/src/components/cms/builder/BuilderCanvas.tsx`, `frontend/src/app/plataforma/cms/builder/page.tsx`, `tests/test_cms_v2_presence.py`, `tests/test_structural_contracts.py`
- **Interface contracts**: PROJECT.md / SCOPE.md
- **Review criteria**: Correctness, completeness, TypeScript compile without errors, Pytest pass all 46 tests, anti-cheat / integrity check

## Key Decisions Made
- Initializing review pipeline

## Loaded Skills
- **ccf-backend-guard**: Backend safety (FastAPI, SQLAlchemy, sede_id, soft deletes, datetime, UUID).
- **ccf-ui-guard**: Frontend safety (Next.js, apiFetch, /plataforma/, drawers, semantic tokens, DS 3-layer).
- **ccf-architecture-guard**: Cross-layer change planning and rollback safety.

## Artifact Index
- `/root/ccf/.agents/teamwork_preview_reviewer_m2_2/ORIGINAL_REQUEST.md` — User request log
- `/root/ccf/.agents/teamwork_preview_reviewer_m2_2/BRIEFING.md` — Briefing document
