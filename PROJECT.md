# Project: CCF Enterprise CMS Phase 6

## Architecture
- **Frontend**: Next.js 14 App Router, TypeScript (`frontend/src/`)
  - Builder: `frontend/src/components/cms/builder/`
  - Public Sections: `frontend/src/components/public/cms/sections/`
  - Public Section Renderer: `frontend/src/components/public/cms/PublicSectionRenderer.tsx`
  - Navigation: `frontend/src/components/cms/CmsModuleNav.tsx`
- **Backend**: FastAPI + SQLAlchemy + PostgreSQL (`backend/`)
  - API Endpoints: `backend/api/cms_v2/`
  - Models: `backend/models_cms.py`
  - Router Registration: `backend/app.py`
- **Migrations**: Alembic in `alembic/canonical_versions/`

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | R1: 4 New Builder Blocks | `animated_counter`, `video_embed`, `gallery_masonry`, `map_embed` in `constants.ts`, `sections/`, `PublicSectionRenderer.tsx`, `BuilderSectionInspector.tsx` | None | DONE |
| 2 | R2: Real-Time Presence | `backend/api/cms_v2/presence.py` WS + REST, `usePresence.ts` hook, `BuilderCanvas.tsx` / `builder/page.tsx` avatar bar | None | DONE |
| 3 | R3: A/B Testing | Models in `models_cms.py`, migration, `backend/api/cms_v2/ab_testing.py`, `ab-testing/page.tsx`, `FlaskConical` in nav, `PublicSectionRenderer` variant split | None | PLANNED |
| 4 | R4: Post Comments | `CmsPostComment` model, migration, `backend/api/cms_v2/post_comments.py`, `comments/page.tsx`, `MessageCircle` in nav, `PostComments.tsx` public component | None | PLANNED |
| 5 | R5: Full-Text Search | `backend/api/cms_v2/search.py`, `search-admin/page.tsx`, `SearchBar.tsx` public component | None | PLANNED |
| 6 | Final: E2E Verification & Git Commit | Run `tsc --noEmit`, run `pytest tests/test_structural_contracts.py`, git commit `feat(cms): ...`, verify clean tree | M1, M2, M3, M4, M5 | PLANNED |

## Code Layout
- Backend Routers:
  - `backend/api/cms_v2/presence.py`
  - `backend/api/cms_v2/ab_testing.py`
  - `backend/api/cms_v2/post_comments.py`
  - `backend/api/cms_v2/search.py`
- Frontend Pages & Components:
  - `frontend/src/components/cms/builder/constants.ts`
  - `frontend/src/components/cms/builder/BuilderSectionInspector.tsx`
  - `frontend/src/components/public/cms/PublicSectionRenderer.tsx`
  - `frontend/src/hooks/usePresence.ts`
  - `frontend/src/app/plataforma/cms/ab-testing/page.tsx`
  - `frontend/src/app/plataforma/cms/comments/page.tsx`
  - `frontend/src/app/plataforma/cms/search-admin/page.tsx`
  - `frontend/src/components/public/cms/PostComments.tsx`
  - `frontend/src/components/public/cms/SearchBar.tsx`
