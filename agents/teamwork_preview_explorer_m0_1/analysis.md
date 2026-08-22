# Comprehensive Phase 6 Architectural and Codebase Exploration Report

## Overview
This report provides a detailed analysis of the existing codebase for Phase 6 of the CCF Enterprise CMS project, covering features R1 through R5.

---

## 1. `backend/models_cms.py` Analysis
- **Imports & Base**:
  - `from backend.models_shared import *` (re-exports SQLAlchemy types, `Base`, `_utcnow`, `UUID`, etc.)
  - `Base` originates from `backend.core.database.Base`.
  - Timestamp helper `_utcnow` returns timezone-aware UTC `datetime.datetime.now(dt.timezone.utc)`.
- **Primary Keys & Types**:
  - `id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)`
  - Foreign keys explicitly declare `UUID(as_uuid=True)` and target SQL tablenames (e.g. `cms_sites.id`, `cms_pages.id`, `cms_posts.id`).
- **Timestamps**:
  - `created_at = Column(DateTime(timezone=True), default=_utcnow)`
  - `updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)`
  - All `DateTime` columns explicitly set `timezone=True`.
- **JSON Storage**:
  - Uses `JSON` column type from `sqlalchemy` (never `JSONB` to ensure SQLite test compatibility).
- **Existing Models in File**:
  - `CmsMediaItem`, `CmsSite`, `CmsTheme`, `CmsMenu`, `CmsMenuItem`, `CmsPage`, `CmsPageVersion`, `CmsSection`, `CmsSectionType`, `CmsPublishLog`, `CmsPageView`, `SavedView`, `CmsCategory`, `CmsTag`, `CmsPost`, `CmsPostCategory`, `CmsPostTag`, `CmsSeoSnapshot`, `CmsPopup`, `CmsForm`, `CmsFormSubmission`, `CmsNewsletter`, `CmsSubscriber`.
- **Required Model Additions for Phase 6**:
  - **R3 (A/B Testing)**:
    - `CmsAbTest`: `id` (UUID), `site_id` (FK `cms_sites.id`, ondelete CASCADE), `page_id` (FK `cms_pages.id`, ondelete CASCADE, optional/nullable), `name` (String(255)), `status` (String(30), default "draft"), `variant_a_props` (JSON), `variant_b_props` (JSON), `traffic_split` (Integer/Float, default 50), `created_at`, `updated_at`.
    - `CmsAbTestEvent`: `id` (UUID), `ab_test_id` (FK `cms_ab_tests.id`, ondelete CASCADE), `variant` (String(10), e.g. "a"/"b"), `event_type` (String(30), e.g. "impression"/"conversion"), `created_at`.
    - Relationship on `CmsSite`: `ab_tests = relationship("CmsAbTest", back_populates="site", lazy="selectin", cascade="all, delete-orphan")`.
  - **R4 (Blog Post Comments)**:
    - `CmsPostComment`: `id` (UUID), `post_id` (FK `cms_posts.id`, ondelete CASCADE), `author_name` (String(120)), `author_email` (String(255)), `content` (Text), `status` (String(20), default "pending"), `created_at`, `updated_at`.
    - Relationship on `CmsPost`: `comments = relationship("CmsPostComment", back_populates="post", lazy="selectin", cascade="all, delete-orphan")`.
  - **R5 (Search Promotions if persistent model is desired)**:
    - `CmsSearchPromotion`: `id` (UUID), `site_id` (FK `cms_sites.id`, ondelete CASCADE), `query_text` (String(255)), `entity_type` (String(50)), `entity_id` (String(120)), `title` (String(255), nullable), `boost_score` (Integer, default 100), `is_active` (Boolean, default True), `created_at`, `updated_at`.

---

## 2. Router Registration in `backend/app.py` & `cms_v2`
- **FastAPI Router Architecture**:
  - `backend/app.py` imports sub-routers and registers them in `ROUTER_REGISTRY` (lines 62-97).
  - `(cms_v2.router, "/api", None)` registers the main `cms_v2` router.
  - `cms_v2.router` is defined in `backend/api/cms_v2/__init__.py` with `prefix="/cms/v2"` and tag `["cms_v2"]`.
- **Sub-Router Inclusion Pattern**:
  - `backend/api/cms_v2/__init__.py` imports domain modules (e.g. `pages.py`, `posts.py`, `popups.py`, `forms.py`, `newsletter.py`) and mounts them via `router.include_router(module.router)`.
  - Endpoints in sub-modules use relative routes (e.g. `@router.get("/sites/{site_key}/posts")`), resulting in canonical paths like `/api/cms/v2/sites/{site_key}/posts`.
- **Mount Points for Phase 6 Sub-routers**:
  - R2 Presence: `backend/api/cms_v2/presence.py` (WS / REST routes) -> mounted in `backend/api/cms_v2/__init__.py`.
  - R3 A/B Testing: `backend/api/cms_v2/ab_testing.py` -> mounted in `backend/api/cms_v2/__init__.py`.
  - R4 Comments: `backend/api/cms_v2/post_comments.py` -> mounted in `backend/api/cms_v2/__init__.py`.
  - R5 Search: `backend/api/cms_v2/search.py` -> mounted in `backend/api/cms_v2/__init__.py`.

---

## 3. Migration Naming and Formatting (`alembic/canonical_versions/`)
- **Alembic Configuration**:
  - Specified in `alembic.ini`: `version_locations = %(here)s/alembic/canonical_versions`.
- **Naming Pattern**:
  - File format: `YYYYMMDD_000X_<descriptive_slug>.py`
  - Examples:
    - `20260730_0004_add_cms_popups.py`
    - `20260730_0005_add_cms_forms.py`
    - `20260730_0006_add_cms_newsletters_subscribers.py`
- **Migration File Structure**:
  ```python
  """<description>

  Revision ID: <revision_str>
  Revises: <down_revision_str>
  Create Date: YYYY-MM-DD HH:MM:SS.000000
  """
  from __future__ import annotations
  import sqlalchemy as sa
  from alembic import op

  revision = "<revision_str>"
  down_revision = "<down_revision_str>"
  branch_labels = None
  depends_on = None

  def _uuid_type() -> sa.types.TypeEngine:
      bind = op.get_bind()
      if bind.dialect.name == "postgresql":
          return sa.dialects.postgresql.UUID(as_uuid=True)
      return sa.String(length=36)

  def upgrade() -> None:
      bind = op.get_bind()
      inspector = sa.inspect(bind)
      uuid_t = _uuid_type()
      if not inspector.has_table("my_table"):
          op.create_table(...)

  def downgrade() -> None:
      ...
  ```
- **Next Revisions for Phase 6**:
  - `20260730_0007_add_cms_ab_testing.py` (down_revision: `20260730_0006_add_cms_newsletters_subscribers`)
  - `20260730_0008_add_cms_post_comments.py`
  - `20260730_0009_add_cms_search_promotions.py`

---

## 4. Frontend Builder Components (`constants.ts` & `BuilderSectionInspector.tsx`)
- **`constants.ts` (`frontend/src/components/cms/builder/constants.ts`)**:
  - `SECTION_TYPES` (lines 3-16): Array of const strings including `animated_counter`, `video_embed`, `gallery_masonry`, `map_embed`.
  - `SECTION_TYPE_COLORS` (lines 57-60): Hex/HSL background color badges mapped for all 4 block types.
  - `SECTION_TYPE_LABEL` (lines 100-103): User-facing Spanish label strings ("Contador Animado", "Video Embed", "Galería Masonry", "Mapa Embed").
  - `SECTION_TEMPLATES` (lines 266-307): Default JSON props template structures pre-configured for each block type.
- **`BuilderSectionInspector.tsx` (`frontend/src/components/cms/builder/BuilderSectionInspector.tsx`)**:
  - Prop editing controls already present:
    - `animated_counter` (lines 1517-1578): Form for counter items array (label, value, duration_ms, prefix, suffix, archive/restore).
    - `video_embed` (lines 1581-1618): Form for video_url, caption, autoplay checkbox.
    - `gallery_masonry` (lines 1621-1675): Form for columns selector (2/3/4) and images array (url, alt, caption).
    - `map_embed` (lines 1678-1742): Form for address, lat, lng, zoom (1-20), height_px.

---

## 5. Public Section Renderer (`PublicSectionRenderer.tsx` & `sections/`)
- **Dispatch Component (`PublicSectionRenderer.tsx`)**:
  - Imports individual section components from `./sections`.
  - Switch statement maps `section.type`:
    - `"animated_counter"` -> `<AnimatedCounterSection section={asTyped<"animated_counter">(section)} />`
    - `"video_embed"` -> `<VideoEmbedSection section={asTyped<"video_embed">(section)} />`
    - `"gallery_masonry"` -> `<GalleryMasonrySection section={asTyped<"gallery_masonry">(section)} />`
    - `"map_embed"` -> `<MapEmbedSection section={asTyped<"map_embed">(section)} />`
- **Section Implementations (`frontend/src/components/public/cms/sections/`)**:
  - `AnimatedCounterSection.tsx`: IntersectionObserver trigger with requestAnimationFrame cubic ease-out counter animation.
  - `VideoEmbedSection.tsx`: Responsive video container supporting YouTube/Vimeo embed parsing and autoplay.
  - `GalleryMasonrySection.tsx`: CSS column masonry layout based on `columns` prop.
  - `MapEmbedSection.tsx`: OpenStreetMap/Google Maps iframe renderer based on lat/lng or address.
  - Re-exported cleanly in `sections/index.ts`.

---

## 6. CMS Navigation Bar (`CmsModuleNav.tsx`)
- **Location**: `frontend/src/components/cms/CmsModuleNav.tsx`
- **Existing Tabs (`CMS_TABS`)**:
  - Array of tab objects `{ id, label, href, icon }`.
- **Required New Tabs for Phase 6**:
  - **R3 A/B Testing**: `{ id: "ab-testing", label: "A/B Testing", href: "/plataforma/cms/ab-testing", icon: Split }` (or `GitBranch` / `FlaskConical`).
  - **R4 Comments**: `{ id: "comments", label: "Comentarios", href: "/plataforma/cms/comments", icon: MessageSquare }`.

---

## 7. Search Admin Page (`search-admin/page.tsx`)
- **Location**: `frontend/src/app/plataforma/cms/search-admin/page.tsx`
- **Current State**: Implemented on the frontend, awaiting backend REST endpoints.
- **Backend API Endpoints Called**:
  - `POST /api/cms/v2/search`: Body `{ site_key, query }`, Returns `{ results: SearchResult[], promoted: Promotion[] }`.
  - `GET /api/cms/v2/search/promotions?site_key={SITE_KEY}`: Returns list of active search promotions `Promotion[]`.
  - `POST /api/cms/v2/search/promotions`: Body `{ site_key, query_text, entity_type, entity_id, title, boost_score }`, Creates promotion rule.

---

## 8. Structural Contract Expectations (`test_structural_contracts.py`)
- **Route Namespace**: All API routes must start with `/api/`. Module `backend.api.cms_v2` routes must be under `/api/cms/v2/`.
- **Database Model Rules**:
  - Column types: Use `JSON` (never `JSONB`).
  - Timestamps: All `DateTime` columns must use `timezone=True`.
  - Primary Keys: All tables must use `UUID(as_uuid=True)` as primary key.
  - Soft Delete: Hard `db.delete()` is forbidden in transactional API endpoints; soft deletion via `deleted_at` or status field is required.
- **Frontend Rules**:
  - Network calls: Use `apiFetch()` from `@/lib/http` instead of raw `fetch()`.
  - UI Navigation: Use canonical paths under `/plataforma/cms/...`.

---

## Summary of Findings & Next Steps for Implementation
1. **R1 (Builder Blocks)**: Complete frontend implementation exists (constants, inspector, public renderer, section components). Backend `cms_section_types` registry support should be verified.
2. **R2 (Presence)**: Requires `backend/api/cms_v2/presence.py` WebSocket/REST endpoint, `usePresence.ts` hook, and integration in `BuilderCanvas.tsx` / `builder/page.tsx`.
3. **R3 (A/B Testing)**: Requires ORM models (`CmsAbTest`, `CmsAbTestEvent`), Alembic migration, `backend/api/cms_v2/ab_testing.py` API, `/plataforma/cms/ab-testing/page.tsx` frontend page, and nav tab in `CmsModuleNav.tsx`.
4. **R4 (Blog Post Comments)**: Requires ORM model (`CmsPostComment`), Alembic migration, `backend/api/cms_v2/post_comments.py` API, `/plataforma/cms/comments/page.tsx` moderation page, nav tab in `CmsModuleNav.tsx`, and `PostComments.tsx` public view.
5. **R5 (Search)**: Requires `backend/api/cms_v2/search.py` backend implementation providing `POST /api/cms/v2/search` and promotions CRUD to pair with existing `search-admin/page.tsx` and public `SearchBar.tsx`.
