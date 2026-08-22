# BRIEFING — 2026-07-30T18:32:00Z

## Mission
Fix ProjectCommentItem TS error in TaskCommentSection.tsx, verify next build, run structural contract tests, and ensure feat(cms): commit prefix with clean working tree.

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: /root/ccf/.agents/worker_final_build_commit_fix_gen2
- Original parent: 92b36264-1865-4585-935d-cbe1d12688ec
- Milestone: final_build_commit_fix

## 🔒 Key Constraints
- Fix ProjectCommentItem TS error in TaskCommentSection.tsx / projects.ts
- `cd /root/ccf/frontend && npx next build` -> exit code 0
- `cd /root/ccf && PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v` -> 43 passed
- Latest git commit message starts with `feat(cms):`
- Working tree clean (`git status` -> `nothing to commit, working tree clean`)
- **Reglas CCF obligatorias**: Leer y aplicar `/root/ccf/AGENTS_RULES_CCF.md` ANTES de implementar. Todo código nuevo debe cumplir: backend (datetime.now(timezone.utc), sede_id kwonly, actor UUID, UUID PKs, soft deletes, HTTPException semánticos), frontend (apiFetch, /plataforma/, drawers NO modals, tokens semánticos hsl(var(--*)), clsx, DS* components), DB (migraciones reversibles, no editar cerradas).
- **Drawers NO modals**: Flujos create/edit/view usan drawers (SidePanel, RightPanel, UniversalCreationDrawer), NO modals/AlertDialog. Excepción: confirmaciones de delete pueden usar AlertDialog.
- **Lint obligatorio**: Ejecutar `cd /root/ccf/frontend && npm run lint -- --max-warnings=0` antes de commit.
- **Venv para pytest**: Ejecutar `cd /root/ccf && ./venv/bin/python -m pytest` (no `python3` directo).
- **Sistema task**: Registrar T1 + sub-tareas en el sistema task ANTES de codear.

## Current Parent
- Conversation ID: 92b36264-1865-4585-935d-cbe1d12688ec
- Updated: 2026-07-30T18:32:00Z

## Task Summary
- **What to build**: Fix TS types in `projects.ts` and `TaskCommentSection.tsx` for `ProjectCommentItem`.
- **Success criteria**: Next.js build succeeds with zero TS/build errors, 43 structural contract tests pass, commit message amended to `feat(cms): ...`, clean git working tree.

## Change Tracker
- **Files modified**:
  - `frontend/src/types/projects.ts`: added `ProjectCommentAttachment` interface and updated `ProjectCommentItem.attachments` typing.
  - `frontend/src/components/projects/TaskCommentSection.tsx`: imported `ProjectCommentAttachment` and updated `Comment` interface attachment typing.
- **Build status**: Pass (0 errors)
- **Pending issues**: None

## Quality Status
- **Build/test result**: Pass (next build exit code 0; 43 structural contract tests passed; 3 TaskCommentSection unit tests passed)
- **Lint status**: Pass
- **Tests added/modified**: Verified existing test suite

## Loaded Skills
- **ccf-backend-guard**: Backend safety (FastAPI, SQLAlchemy, sede_id, soft deletes, datetime, UUID).
- **ccf-ui-guard**: Frontend safety (Next.js, apiFetch, /plataforma/, drawers, semantic tokens, DS 3-layer).
- **ccf-architecture-guard**: Cross-layer change planning and rollback safety.
- **ccf-cms-guard**: CMS and public-content safety.
