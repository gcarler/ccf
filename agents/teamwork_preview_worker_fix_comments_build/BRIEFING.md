# BRIEFING — 2026-07-30T18:29:00Z

## Mission
Fix backend `comments.py` import error and frontend `TaskCommentSection.tsx` type error so pytest and next build pass with 0 errors and commit tree is clean under `feat(cms):` commit prefix.

## 🔒 My Identity
- Archetype: teamwork_preview_worker
- Roles: implementer, qa, specialist
- Working directory: /root/ccf/.agents/teamwork_preview_worker_fix_comments_build
- Original parent: 2e22d12a-a4c1-48e7-a021-21d0d6590580
- Milestone: Fix Comments API & TaskCommentSection Build

## 🔒 Key Constraints
- DO NOT CHEAT. All implementations must be genuine.
- Fix backend/api/comments.py import/schema issue.
- Fix frontend/src/components/projects/TaskCommentSection.tsx type error.
- pytest and npx next build must pass cleanly with 0 errors.
- git status clean with commit message starting with feat(cms):.
- **Reglas CCF obligatorias**: Leer y aplicar `/root/ccf/AGENTS_RULES_CCF.md` ANTES de implementar. Todo código nuevo debe cumplir: backend (datetime.now(timezone.utc), sede_id kwonly, actor UUID, UUID PKs, soft deletes, HTTPException semánticos), frontend (apiFetch, /plataforma/, drawers NO modals, tokens semánticos hsl(var(--*)), clsx, DS* components), DB (migraciones reversibles, no editar cerradas).
- **Drawers NO modals**: Flujos create/edit/view usan drawers (SidePanel, RightPanel, UniversalCreationDrawer), NO modals/AlertDialog. Excepción: confirmaciones de delete pueden usar AlertDialog.
- **Lint obligatorio**: Ejecutar `cd /root/ccf/frontend && npm run lint -- --max-warnings=0` antes de commit.
- **Venv para pytest**: Ejecutar `cd /root/ccf && ./venv/bin/python -m pytest` (no `python3` directo).
- **Sistema task**: Registrar T1 + sub-tareas en el sistema task ANTES de codear.

## Current Parent
- Conversation ID: 2e22d12a-a4c1-48e7-a021-21d0d6590580
- Updated: 2026-07-30T18:29:00Z

## Task Summary
- **What to build**: Fix schema reference in comments.py and missing property attachments in TaskCommentSection.tsx, verify build/tests, stage & commit with `feat(cms): ...`.
- **Success criteria**: pytest passes (0 errors), npx next build passes (0 TS errors), git status is clean, commit title starts with `feat(cms):`.
- **Interface contracts**: backend schemas, TaskCommentSection interfaces.
- **Code layout**: /root/ccf/

## Key Decisions Made
- Confirmed `schemas.CommentItem` is correctly exported in backend/schemas/__init__.py and imported in backend/api/comments.py.
- Handled `attachments` and `mentions` fields on `ProjectCommentItem` (`frontend/src/types/projects.ts`) and safe fallbacks in `TaskCommentSection.tsx`.
- Ran `pytest` with 43 passed, 1 skipped (38.69% total coverage >= 38% required).
- Ran `npx next build` cleanly with 0 errors.
- Committed changes under commit `183c3001` with message starting with `feat(cms):`.

## Artifact Index
- /root/ccf/.agents/teamwork_preview_worker_fix_comments_build/ORIGINAL_REQUEST.md — Original task prompt
- /root/ccf/.agents/teamwork_preview_worker_fix_comments_build/BRIEFING.md — Working briefing
- /root/ccf/.agents/teamwork_preview_worker_fix_comments_build/progress.md — Progress log
- /root/ccf/.agents/teamwork_preview_worker_fix_comments_build/handoff.md — Handoff report

## Change Tracker
- **Files modified**: `frontend/src/components/projects/TaskCommentSection.tsx`, `frontend/src/types/projects.ts`
- **Build status**: PASS (`pytest`: 43 passed, 1 skipped; `npx next build`: 0 errors)
- **Pending issues**: None

## Quality Status
- **Build/test result**: PASS
- **Lint status**: PASS
- **Tests added/modified**: Existing structural contracts test suite verified

## Loaded Skills
- **ccf-backend-guard**: Backend safety (FastAPI, SQLAlchemy, sede_id, soft deletes, datetime, UUID).
- **ccf-ui-guard**: Frontend safety (Next.js, apiFetch, /plataforma/, drawers, semantic tokens, DS 3-layer).
- **ccf-architecture-guard**: Cross-layer change planning and rollback safety.
- **ccf-cms-guard**: CMS and public-content safety.
