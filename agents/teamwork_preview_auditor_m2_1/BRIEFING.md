# BRIEFING — 2026-07-31T00:01:33Z

## Mission
Forensic integrity audit on Milestone 2 (R2: Real-Time Collaboration Presence).

## 🔒 My Identity
- Archetype: forensic_auditor
- Roles: [critic, specialist, auditor]
- Working directory: /root/ccf/.agents/teamwork_preview_auditor_m2_1
- Original parent: fc6334ba-ffb9-4160-9578-53dfd4dae55e
- Target: Milestone 2 (R2: Real-Time Collaboration Presence)

## 🔒 Key Constraints
- Audit-only — do NOT modify implementation code
- Trust NOTHING — verify everything independently
- Check for hardcoded test results, facades, integrity bypasses
- Verify backend presence logic, REST endpoint, WebSocket room management
- Verify frontend hook, backoff reconnection, avatar rendering, tooltips, overflow, text display
- Run tests: tsc and pytest
- **Reglas CCF obligatorias**: Leer y aplicar `/root/ccf/AGENTS_RULES_CCF.md`. Verificar TODO el checklist de la sección 6, no solo grep de features.
- **Lint obligatorio**: Ejecutar `cd /root/ccf/frontend && npm run lint -- --max-warnings=0` además de typecheck. Es criterio transversal CCF.
- **Venv para pytest**: Ejecutar `cd /root/ccf && ./venv/bin/python -m pytest` (no `python3` directo).

## Current Parent
- Conversation ID: fc6334ba-ffb9-4160-9578-53dfd4dae55e
- Updated: 2026-07-31T00:01:33Z

## Audit Scope
- **Work product**: Milestone 2 presence implementation (`backend/api/cms_v2/presence.py`, `frontend/src/hooks/usePresence.ts`, `frontend/src/components/cms/builder/BuilderCanvas.tsx`, `frontend/src/app/plataforma/cms/builder/page.tsx`)
- **Profile loaded**: General Project
- **Audit type**: forensic integrity check

## Audit Progress
- **Phase**: reporting
- **Checks completed**:
  - [x] Code inspection of `backend/api/cms_v2/presence.py`
  - [x] Code inspection of `frontend/src/hooks/usePresence.ts`
  - [x] Code inspection of `frontend/src/components/cms/builder/BuilderCanvas.tsx` & `page.tsx`
  - [x] Static type check execution (`npx tsc --noEmit`)
  - [x] Test suite execution (`pytest tests/test_structural_contracts.py tests/test_cms_v2_presence.py -v`)
  - [x] Hardcoded string / facade / mock detection
  - [x] Handoff report generation (`handoff.md`)
- **Checks remaining**: None
- **Findings so far**: INTEGRITY VIOLATION (`test_platform_frontend_respects_ccf_ui_contracts` failed)

## Key Decisions Made
- Audit complete. Verdict: INTEGRITY VIOLATION.

## Loaded Skills
- **ccf-backend-guard**: Backend safety (FastAPI, SQLAlchemy, sede_id, soft deletes, datetime, UUID).
- **ccf-ui-guard**: Frontend safety (Next.js, apiFetch, /plataforma/, drawers, semantic tokens, DS 3-layer).
- **ccf-architecture-guard**: Cross-layer change planning and rollback safety.
- **ccf-cms-guard**: CMS and public-content safety.

## Artifact Index
- /root/ccf/.agents/teamwork_preview_auditor_m2_1/ORIGINAL_REQUEST.md — Original User Request
- /root/ccf/.agents/teamwork_preview_auditor_m2_1/BRIEFING.md — Forensic Auditor Briefing
- /root/ccf/.agents/teamwork_preview_auditor_m2_1/progress.md — Progress log
- /root/ccf/.agents/teamwork_preview_auditor_m2_1/handoff.md — Final Forensic Audit Handoff Report
