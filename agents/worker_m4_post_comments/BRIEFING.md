# BRIEFING — 2026-07-31T00:06:00Z

## Mission
Implement Milestone 4: R4 Blog Post Comments for CCF, including backend model, API endpoints, Alembic migration, admin UI, public UI component, navigation badge, unit tests, and typechecks.

## 🔒 My Identity
- Archetype: implementer/qa/specialist
- Roles: implementer, qa, specialist
- Working directory: /root/ccf/.agents/worker_m4_post_comments
- Original parent: 92b36264-1865-4585-935d-cbe1d12688ec
- Milestone: Milestone 4 - R4 Blog Post Comments

## 🔒 Key Constraints
- CODE_ONLY network mode: no external HTTP requests.
- No cheating or hardcoding test results / dummy implementations.
- Minimal edits and full verification.
- 0 TypeScript errors on `npm run typecheck`.
- **Reglas CCF obligatorias**: Leer y aplicar `/root/ccf/AGENTS_RULES_CCF.md` ANTES de implementar. Todo código nuevo debe cumplir: backend (datetime.now(timezone.utc), sede_id kwonly, actor UUID, UUID PKs, soft deletes, HTTPException semánticos), frontend (apiFetch, /plataforma/, drawers NO modals, tokens semánticos hsl(var(--*)), clsx, DS* components), DB (migraciones reversibles, no editar cerradas).
- **Drawers NO modals**: Flujos create/edit/view usan drawers (SidePanel, RightPanel, UniversalCreationDrawer), NO modals/AlertDialog. Excepción: confirmaciones de delete pueden usar AlertDialog.
- **Lint obligatorio**: Ejecutar `cd /root/ccf/frontend && npm run lint -- --max-warnings=0` antes de commit.
- **Venv para pytest**: Ejecutar `cd /root/ccf && ./venv/bin/python -m pytest` (no `python3` directo).
- **Sistema task**: Registrar T1 + sub-tareas en el sistema task ANTES de codear.

## Current Parent
- Conversation ID: 92b36264-1865-4585-935d-cbe1d12688ec
- Updated: 2026-07-31T00:06:00Z

## Task Summary
- **What to build**: 
  1. Backend Model `CmsPostComment` in `backend/models_cms.py` and re-exported in `backend/models.py`
  2. Alembic Migration `20260731_0008_add_cms_post_comments.py` in `alembic/canonical_versions/`
  3. Pydantic schemas in `backend/schemas/cms.py` and re-exports in `backend/schemas/__init__.py`
  4. Backend Endpoints in `backend/api/cms_v2/post_comments.py` and router registration in `backend/api/cms_v2/__init__.py`
  5. Frontend Types in `frontend/src/types/cms-v2.ts` and API helpers in `frontend/src/lib/cms/v2.ts`
  6. Navigation update in `frontend/src/components/cms/CmsModuleNav.tsx`
  7. Frontend Admin Page `frontend/src/app/plataforma/cms/comments/page.tsx`
  8. Frontend Public Component `frontend/src/components/public/cms/PostComments.tsx`
  9. Pytest backend unit tests `tests/test_cms_v2_post_comments.py`
  10. Vitest frontend tests `frontend/src/components/public/cms/__tests__/PostComments.test.tsx` and `frontend/src/app/plataforma/cms/comments/__tests__/page.test.tsx`
- **Success criteria**: 0 TS errors, all 7 backend pytest tests passing, all 5 vitest frontend tests passing.

## Change Tracker
- **Files modified**:
  - `backend/models_cms.py`: Defined `CmsPostComment` model and added `comments` relationship to `CmsPost`.
  - `backend/models.py`: Re-exported `CmsPostComment`.
  - `backend/schemas/cms.py`: Added comment schemas (`CmsPostCommentCreate`, `CmsPostCommentStatusUpdate`, `CmsPostCommentRead`, `CmsPostCommentPublicRead`, `CmsPostCommentListResponse`).
  - `backend/schemas/__init__.py`: Re-exported comment schemas.
  - `backend/api/cms_v2/__init__.py`: Included `post_comments` router.
  - `frontend/src/types/cms-v2.ts`: Added comment TypeScript interfaces.
  - `frontend/src/lib/cms/v2.ts`: Added API fetch helper functions for comments.
  - `frontend/src/components/cms/CmsModuleNav.tsx`: Added "Comentarios" tab and pending count badge.
- **Files created**:
  - `alembic/canonical_versions/20260731_0008_add_cms_post_comments.py`
  - `backend/api/cms_v2/post_comments.py`
  - `tests/test_cms_v2_post_comments.py`
  - `frontend/src/app/plataforma/cms/comments/page.tsx`
  - `frontend/src/components/public/cms/PostComments.tsx`
  - `frontend/src/components/public/cms/__tests__/PostComments.test.tsx`
  - `frontend/src/app/plataforma/cms/comments/__tests__/page.test.tsx`
- **Build status**: PASS (Pytest 7/7 passed, Vitest 5/5 passed, tsc typecheck 0 errors)
- **Pending issues**: None

## Quality Status
- **Build/test result**: PASS (7 backend pytest tests, 5 vitest tests)
- **Lint status**: Clean (0 TS errors)
- **Tests added/modified**: `test_cms_v2_post_comments.py`, `PostComments.test.tsx`, `page.test.tsx`

## Loaded Skills
- **ccf-backend-guard**: Backend safety (FastAPI, SQLAlchemy, sede_id, soft deletes, datetime, UUID).
- **ccf-ui-guard**: Frontend safety (Next.js, apiFetch, /plataforma/, drawers, semantic tokens, DS 3-layer).
- **ccf-architecture-guard**: Cross-layer change planning and rollback safety.
- **ccf-cms-guard**: CMS and public-content safety.

## Key Decisions Made
- `CmsPostComment` status defaults to 'pending'.
- Public comments endpoint returns approved comments only, with 1-level nested replies.
- Admin comments list returns `pending_count` metadata for tab badge display.

## Artifact Index
- `/root/ccf/.agents/worker_m4_post_comments/ORIGINAL_REQUEST.md` — Original request log
- `/root/ccf/.agents/worker_m4_post_comments/progress.md` — Progress tracker and liveness heartbeat
- `/root/ccf/.agents/worker_m4_post_comments/handoff.md` — Final handoff report
