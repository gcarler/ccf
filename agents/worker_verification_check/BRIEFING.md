# BRIEFING — 2026-07-30T22:41:56Z

## Mission
Run final verification checks for frontend type checking, structural contracts test suite, git commit prefix, and git working tree cleanliness.

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: /root/ccf/.agents/worker_verification_check
- Original parent: 92b36264-1865-4585-935d-cbe1d12688ec
- Milestone: final_verification_check

## 🔒 Key Constraints
- CODE_ONLY network mode
- Write agent metadata only to /root/ccf/.agents/worker_verification_check
- Follow 5-Component Handoff Report format in handoff.md
- **Reglas CCF obligatorias**: Leer y aplicar `/root/ccf/AGENTS_RULES_CCF.md` ANTES de implementar. Todo código nuevo debe cumplir: backend (datetime.now(timezone.utc), sede_id kwonly, actor UUID, UUID PKs, soft deletes, HTTPException semánticos), frontend (apiFetch, /plataforma/, drawers NO modals, tokens semánticos hsl(var(--*)), clsx, DS* components), DB (migraciones reversibles, no editar cerradas).
- **Drawers NO modals**: Flujos create/edit/view usan drawers (SidePanel, RightPanel, UniversalCreationDrawer), NO modals/AlertDialog. Excepción: confirmaciones de delete pueden usar AlertDialog.
- **Lint obligatorio**: Ejecutar `cd /root/ccf/frontend && npm run lint -- --max-warnings=0` antes de commit.
- **Venv para pytest**: Ejecutar `cd /root/ccf && ./venv/bin/python -m pytest` (no `python3` directo).
- **Sistema task**: Registrar T1 + sub-tareas en el sistema task ANTES de codear.

## Current Parent
- Conversation ID: 92b36264-1865-4585-935d-cbe1d12688ec
- Updated: 2026-07-30T22:41:56Z

## Task Summary
- **What to verify**:
  1. Frontend TypeScript compilation (`npx tsc --noEmit` in `/root/ccf/frontend`)
  2. Structural contracts pytest (`pytest tests/test_structural_contracts.py -v` in `/root/ccf`)
  3. Git log latest commit prefix check (`feat(cms):` in `/root/ccf`)
  4. Git status clean working tree check in `/root/ccf`
- **Success criteria**: All checks pass with zero errors, clean git status, matching commit prefix.

## Key Decisions Made
- Executing verification steps in order.

## Artifact Index
- /root/ccf/.agents/worker_verification_check/ORIGINAL_REQUEST.md — Initial user request
- /root/ccf/.agents/worker_verification_check/BRIEFING.md — Persistent context briefing
- /root/ccf/.agents/worker_verification_check/progress.md — Liveness heartbeat progress
- /root/ccf/.agents/worker_verification_check/handoff.md — Final handoff report

## Change Tracker
- **Files modified**: None (read-only verification checks)
- **Build status**: Pending
- **Pending issues**: None

## Quality Status
- **Build/test result**: Pending
- **Lint status**: Pending
- **Tests added/modified**: N/A

## Loaded Skills
- **ccf-backend-guard**: Backend safety (FastAPI, SQLAlchemy, sede_id, soft deletes, datetime, UUID).
- **ccf-ui-guard**: Frontend safety (Next.js, apiFetch, /plataforma/, drawers, semantic tokens, DS 3-layer).
- **ccf-architecture-guard**: Cross-layer change planning and rollback safety.
- **ccf-cms-guard**: CMS and public-content safety.
