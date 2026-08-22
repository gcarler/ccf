# Handoff Report — Phase 6 Exploration (R1 - R5)

## 1. Observation
- **`backend/models_cms.py`**:
  - Uses `from backend.models_shared import *` and `_utcnow`.
  - All models inherit from `Base` (from `backend.core.database`).
  - Primary keys use `UUID(as_uuid=True)` with default `uuid.uuid4`.
  - Timestamps use `Column(DateTime(timezone=True), default=_utcnow)`.
  - Column types use `JSON` (not `JSONB`).
  - Contains existing models: `CmsSite`, `CmsPage`, `CmsPost`, `CmsPopup`, `CmsForm`, `CmsNewsletter`, `CmsSubscriber`, etc.
  - Missing models: `CmsAbTest`, `CmsAbTestEvent` (R3) and `CmsPostComment` (R4).

- **`backend/app.py` & `cms_v2`**:
  - Routers are registered in `ROUTER_REGISTRY` (`(cms_v2.router, "/api", None)`).
  - Main router `cms_v2` is defined in `backend/api/cms_v2/__init__.py` with prefix `"/cms/v2"`.
  - Sub-routers are mounted using `router.include_router(mod.router)` inside `backend/api/cms_v2/__init__.py`.
  - Sub-modules `presence.py`, `ab_testing.py`, `post_comments.py`, and `search.py` do not yet exist in `backend/api/cms_v2/`.

- **Alembic Migrations (`alembic/canonical_versions/`)**:
  - Configured location in `alembic.ini`: `version_locations = %(here)s/alembic/canonical_versions`.
  - Naming format: `YYYYMMDD_000X_<descriptive_slug>.py` (e.g. `20260730_0006_add_cms_newsletters_subscribers.py`).
  - Uses helper `_uuid_type()` and table existence checks `inspector.has_table()`.

- **R1 Builder Blocks**:
  - `constants.ts`: `SECTION_TYPES` (line 15), `SECTION_TYPE_COLORS` (lines 57-60), `SECTION_TYPE_LABEL` (lines 100-103), `SECTION_TEMPLATES` (lines 266-307) already include `animated_counter`, `video_embed`, `gallery_masonry`, `map_embed`.
  - `BuilderSectionInspector.tsx`: Inspector forms implemented on lines 1517–1742 for editing props of all 4 blocks.
  - `PublicSectionRenderer.tsx` & `sections/`: Section components (`AnimatedCounterSection.tsx`, `VideoEmbedSection.tsx`, `GalleryMasonrySection.tsx`, `MapEmbedSection.tsx`) implemented and wired into switch renderer.

- **`CmsModuleNav.tsx`**:
  - Defines `CMS_TABS` array for CMS admin navigation.
  - Missing nav tabs for `ab-testing` (R3) and `comments` (R4).

- **`search-admin/page.tsx` (R5)**:
  - Frontend admin page exists at `frontend/src/app/plataforma/cms/search-admin/page.tsx`.
  - Expects endpoints `POST /api/cms/v2/search`, `GET /api/cms/v2/search/promotions`, and `POST /api/cms/v2/search/promotions`.

- **`tests/test_structural_contracts.py`**:
  - Requires all routes under `/api/` (and `cms_v2` under `/api/cms/v2/`).
  - Mandates `UUID(as_uuid=True)` for PKs, `DateTime(timezone=True)`, `JSON` (not `JSONB`), soft deletes (`deleted_at`), and `apiFetch()` on frontend.

## 2. Logic Chain
1. **Observation**: R1 block components (`animated_counter`, `video_embed`, `gallery_masonry`, `map_embed`) are present in `constants.ts`, `BuilderSectionInspector.tsx`, `PublicSectionRenderer.tsx`, and `sections/`.
   **Inference**: Feature R1 frontend implementation is complete. Only backend section_types catalog validation needs checking.
2. **Observation**: `search-admin/page.tsx` makes `apiFetch` requests to `/cms/v2/search` and `/cms/v2/search/promotions`, but `backend/api/cms_v2/search.py` does not exist.
   **Inference**: R5 frontend is ready, but requires `backend/api/cms_v2/search.py` to handle search queries and promotion management.
3. **Observation**: `cms_v2` sub-modules are included via `router.include_router()` in `backend/api/cms_v2/__init__.py`.
   **Inference**: New endpoints for R2 (`presence.py`), R3 (`ab_testing.py`), R4 (`post_comments.py`), and R5 (`search.py`) should be created as sub-modules in `backend/api/cms_v2/` and mounted in `backend/api/cms_v2/__init__.py`.
4. **Observation**: R3 requires A/B test entity tracking and R4 requires post comments, but `models_cms.py` lacks `CmsAbTest`, `CmsAbTestEvent`, and `CmsPostComment`.
   **Inference**: Models must be added to `models_cms.py` following canonical patterns (`UUID`, `timezone=True`, `JSON`), and corresponding Alembic migrations created under `alembic/canonical_versions/`.

## 3. Caveats
- No caveats. Investigation covered all 8 items requested and examined existing source code directly.

## 4. Conclusion
- Exploration for Phase 6 is complete.
- Complete findings written to `/root/ccf/.agents/teamwork_preview_explorer_m0_1/analysis.md`.
- Implementation roadmap clear across backend ORM models, Alembic migrations, sub-router files in `backend/api/cms_v2/`, frontend navigation tabs, and component integrations.

## 5. Verification Method
- **Structural Contract Tests**: Run `pytest tests/test_structural_contracts.py` to ensure route naming, UUID types, and DB constraints pass.
- **CMS Test Suite**: Run `pytest tests/test_cms_*.py` to verify CMS functionality.
- **Inspect Analysis File**: Verify report at `/root/ccf/.agents/teamwork_preview_explorer_m0_1/analysis.md`.
