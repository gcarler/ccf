# Context Tracking — CCF Enterprise CMS Phase 6

## Project Context
- **Project Root**: `/root/ccf`
- **Orchestrator Workdir**: `/root/ccf/.agents/orchestrator`
- **Original User Request**: `/root/ccf/.agents/ORIGINAL_REQUEST.md`

## Requirements Summary
1. **R1: 4 New Builder Blocks**
   - `animated_counter`, `video_embed`, `gallery_masonry`, `map_embed`
   - Files: `constants.ts`, `PublicSectionRenderer.tsx`, `sections/`, `BuilderSectionInspector.tsx`
2. **R2: Real-Time Collaboration Presence**
   - Backend: `backend/api/cms_v2/presence.py` (`WS /api/cms/v2/ws/presence/{site_key}/{slug}` + REST `GET /api/cms/v2/sites/{site_key}/pages/{slug}/presence`)
   - Router registration in `backend/app.py`
   - Frontend hook: `frontend/src/hooks/usePresence.ts`
   - UI: presence avatar bar in `BuilderCanvas.tsx` / `builder/page.tsx`
3. **R3: A/B Testing**
   - Models: `CmsAbTest` & `CmsAbTestEvent` in `backend/models_cms.py`
   - Alembic migration in `alembic/canonical_versions/` or `alembic/versions/`
   - Router: `backend/api/cms_v2/ab_testing.py`
   - Admin UI: `frontend/src/app/plataforma/cms/ab-testing/page.tsx`
   - Nav: `FlaskConical` icon in `CmsModuleNav.tsx`
   - Public: A/B variant switching in `PublicSectionRenderer.tsx` using `ab_visitor_id` cookie
4. **R4: Blog Post Comments**
   - Model: `CmsPostComment` in `backend/models_cms.py`
   - Alembic migration in `alembic/canonical_versions/` or `alembic/versions/`
   - Router: `backend/api/cms_v2/post_comments.py`
   - Admin UI: `frontend/src/app/plataforma/cms/comments/page.tsx` (moderation tabs, `MessageCircle` nav icon)
   - Public Component: `frontend/src/components/public/cms/PostComments.tsx`
5. **R5: Full-Text Search**
   - Backend: `backend/api/cms_v2/search.py` (`GET /api/cms/v2/search`)
   - Admin UI: `frontend/src/app/plataforma/cms/search-admin/page.tsx`
   - Public Component: `frontend/src/components/public/cms/SearchBar.tsx`
6. **Acceptance Criteria & Verification**
   - `npx tsc --noEmit` -> 0 errors
   - `pytest tests/test_structural_contracts.py` -> pass
   - `git commit` prefix `feat(cms):`
   - `git status` clean working tree

## CCF Platform Rules
- All agents MUST follow `/root/ccf/AGENTS_RULES_CCF.md`
- Victory audit MUST verify CCF architectural rules, not just grep acceptance criteria
- Lint (`npm run lint -- --max-warnings=0`) is MANDATORY for all milestones
- Venv activation required: `cd /root/ccf && ./venv/bin/python -m pytest`