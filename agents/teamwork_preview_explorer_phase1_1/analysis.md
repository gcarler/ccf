# Comprehensive Analysis Report: CMS Patterns & Structural Requirements

**Agent**: Explorer phase1_1  
**Date**: 2026-07-30  
**Target Repository**: `/root/ccf`

---

## 1. Executive Summary

This report documents the architectural patterns, database schemas, API route conventions, migration standards, frontend UI components, and test contracts governing the CMS system in the CCF platform. All findings are derived directly from source inspection of the codebase in `/root/ccf`.

---

## 2. Model Inheritance & Database Architecture (`backend/models_cms.py`)

### 2.1 Model Base & Common Imports
- **Base Class**: All CMS models inherit from `Base`, re-exported via `from backend.models_shared import *`.
- **SQLAlchemy Primitives**: `Column`, `UUID`, `String`, `Integer`, `Boolean`, `DateTime`, `Text`, `JSON`, `Date`, `ForeignKey`, `UniqueConstraint`, `relationship`, and `uuid` are imported from `backend.models_shared`.
- **Timestamp Helper**: `_utcnow` from `backend.models_shared` is used as default for timezone-aware DateTime fields.

### 2.2 Key Conventions
1. **Primary Keys**: Every CMS entity uses UUIDv4 primary keys:
   ```python
   id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
   ```
2. **Timezone Awareness**: All `DateTime` columns specify `timezone=True`:
   ```python
   created_at = Column(DateTime(timezone=True), default=_utcnow)
   updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
   ```
3. **Database JSON Type**: Uses standard `JSON` (never `JSONB`) to guarantee SQLite compatibility during test suite execution.
4. **Foreign Keys & Cascade Rules**:
   - `site_id` cascades on site deletion: `ForeignKey("cms_sites.id", ondelete="CASCADE")`.
   - `created_by_persona_id` / `updated_by_persona_id`: `ForeignKey("personas.id")`.
   - Multi-tenant isolation (Axioma 3): `sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=False, index=True)`.
5. **Relationships**:
   - Loaded using `lazy="joined"` or `lazy="selectin"`.
   - Disambiguated with explicit `foreign_keys=[...]` when multiple FKs reference the same target table.
6. **Unique Constraints**: Declared in `__table_args__`:
   ```python
   __table_args__ = (
       UniqueConstraint("site_id", "slug", name="uq_cms_page_site_slug"),
   )
   ```

### 2.3 Inventory of CMS Entities (19 Models)
1. `CmsMediaItem` (`cms_media_items`): Media files, with `url`, `dimensions`, `width`, `height`, `mime_type`, `file_size`, `section`, `tags`, `sede_id`, and `created_by_persona_id`.
2. `CmsSite` (`cms_sites`): Site metadata with `site_key`, `base_path`, `is_active`, and `sede_id`.
3. `CmsTheme` (`cms_themes`): Site themes with `tokens_json`, `is_active`, `version`.
4. `CmsMenu` (`cms_menus`): Menu container scoped by `site_id` and `menu_key`.
5. `CmsMenuItem` (`cms_menu_items`): Tree menu items with self-referencing `parent_id`, `href`, `target`, `sort_order`.
6. `CmsPage` (`cms_pages`): CMS pages with `slug`, `title`, `status`, `published_version_id`, `publish_at`, `expires_at`, `deleted_at`.
7. `CmsPageVersion` (`cms_page_versions`): Page version snapshots with `version_number`, `snapshot_json`, `notes`.
8. `CmsSection` (`cms_sections`): Modular page sections with `section_key`, `type`, `props_json`, `sort_order`, `is_global`, `global_key`, `deleted_at`.
9. `CmsSectionType` (`cms_section_types`): Catalog of available section types.
10. `CmsPublishLog` (`cms_publish_logs`): Audit trail of publishing events (`entity_type`, `action`, `from_status`, `to_status`).
11. `CmsPageView` (`cms_page_views`): Page view analytics tracking `ip_address`, `user_agent`, `referrer`.
12. `SavedView` (`saved_views`): User table views (`schema_json`, `filters_json`, `grouping_json`, `conditional_format_json`).
13. `CmsCategory` (`cms_categories`): Post categories with hierarchical `parent_id`.
14. `CmsTag` (`cms_tags`): Post tags.
15. `CmsPost` (`cms_posts`): Blog/news posts with `slug`, `title`, `excerpt`, `content`, `featured_image_url`, `status`, `published_at`, `expires_at`.
16. `CmsPostCategory` (`cms_post_categories`): Many-to-many junction table for posts and categories.
17. `CmsPostTag` (`cms_post_tags`): Many-to-many junction table for posts and tags.
18. `CmsSeoSnapshot` (`cms_seo_snapshots`): Daily site SEO score snapshots.
19. `CmsPopup` (`cms_popups`): Native popups with `name`, `content_html`, `trigger_type`, `trigger_value`, `is_active`, `show_on_pages`.

---

## 3. Backend API Route Architecture & Conventions

### 3.1 Orchestrator Router (`backend/api/cms_v2/__init__.py`)
- Prefix: `/cms/v2`
- Tags: `["cms_v2"]`
- Rate Limiting: Default `rate_limiter(limit=600, window_seconds=60)` applied at router level.
- Sub-router Registration: Wires 10 domain modules via `router.include_router(...)`:
  - `section_types`, `global_blocks`, `sites`, `themes_menus`, `pages`, `public`, `pastoral`, `posts`, `analytics_ops`, `popups`.

### 3.2 Endpoint Patterns (`backend/api/cms_v2/popups.py`)
- **Router Tag**: `["cms_v2_popups"]`
- **Public Endpoints**:
  - `GET /public/popups?site_key=...&page_slug=...`: Public active popups listing with `PUBLIC_CMS_RATE_LIMIT`.
- **Admin CRUD Endpoints (URL Site-Key Parameter)**:
  - `GET /sites/{site_key}/popups` (List popups)
  - `POST /sites/{site_key}/popups` (Create popup, returns 201)
  - `GET /sites/{site_key}/popups/{id}` (Get popup detail)
  - `PATCH /sites/{site_key}/popups/{id}` (Update popup)
  - `DELETE /sites/{site_key}/popups/{id}` (Delete popup, returns 204)
- **Dependencies & Authorization**:
  - DB Session: `db: Session = Depends(get_db)`.
  - Auth Access: `current_user: models.User = Depends(require_module_access("cms", "read"))` for GET, `require_module_access("cms", "edit")` for write operations.
  - Role Check: `_assert_role(current_user, CMS_EDITOR_ROLES)`.
  - Tenant Scoping: `site = _get_scoped_site_or_404(db, site_key, current_user)`.

### 3.3 Media Router (`backend/api/cms.py`)
- Router Tag: `["cms"]`
- Paths: `/cms/media`, `/cms/media/upload`, `/cms/media/{item_id}`, `/cms/metrics`, `/cms/media/cleanup`.
- Multi-Tenant Scoping: Staff can only access media from their assigned `sede_id` via `_scope_cms_media_by_user_sede`.

---

## 4. Alembic Migration Conventions (`alembic/canonical_versions/`)

### 4.1 Chain & Revision History
- **Latest Head**: `20260730_0004_add_cms_popups`
- **Down Revision**: `20260730_0003_drop_legacy_announcements_table`
- **Merge Point**: `0461885be9c9_merge_heads.py` (merges `20260730_0001_drop_legacy_testimonials_table` and `20260730_0002_migrate_announcements_to_cms_posts`).

### 4.2 Standard Alembic Migration Skeleton
```python
"""add_cms_popups — table for native CMS popups (R3-BE)

Revision ID: 20260730_0004_add_cms_popups
Revises: 20260730_0003_drop_legacy_announcements_table
Create Date: 2026-07-30 17:30:00.000000
"""
from __future__ import annotations
import sqlalchemy as sa
from alembic import op

revision = "20260730_0004_add_cms_popups"
down_revision = "20260730_0003_drop_legacy_announcements_table"
branch_labels = None
depends_on = None

def _uuid_type() -> sa.types.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return sa.dialects.postgresql.UUID(as_uuid=True)
    return sa.String(length=36)

def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("cms_popups"):
        return

    uuid_t = _uuid_type()
    op.create_table(
        "cms_popups",
        sa.Column("id", uuid_t, primary_key=True),
        sa.Column("site_id", uuid_t, sa.ForeignKey("cms_sites.id", ondelete="CASCADE"), nullable=False),
        # Columns...
    )
    op.create_index("ix_cms_popups_site_id", "cms_popups", ["site_id"], unique=False)

def downgrade() -> None:
    op.drop_index("ix_cms_popups_site_id", table_name="cms_popups")
    op.drop_table("cms_popups")
```

### 4.3 Key Migration Standards
1. **Naming**: `YYYYMMDD_XXXX_description.py`.
2. **UUID Helper**: Use dialect check helper `_uuid_type()` for PostgreSQL (`UUID(as_uuid=True)`) vs SQLite (`String(36)`).
3. **Idempotency**: Always inspect database before creating table: `if sa.inspect(bind).has_table(...): return`.
4. **Explicit Indexes**: Explicitly create and drop indexes in `upgrade()` and `downgrade()`.

---

## 5. Frontend Navigation & Management Patterns

### 5.1 CMS Module Nav (`frontend/src/components/cms/CmsModuleNav.tsx`)
- Client Component (`"use client"`).
- Navigational Array (`CMS_TABS`): List of 22 sub-modules targeting `/plataforma/cms/...`.
- Icons: Lucide-react icon components (`LayoutDashboard`, `FileText`, `Layers`, `MessageCircle`, `ImageIcon`, etc.).
- Access Control: Filters tabs based on user roles (`canEditCms(user?.role)`, `canManageSites(user?.role)`).
- Stats Banner: Fetches counts for media, pages, testimonials, and posts via `apiFetch` using an `AbortController` signal.

### 5.2 Popups Management Page (`frontend/src/app/plataforma/cms/popups/page.tsx`)
- Page Structure: Client component with site selector dropdown, search input, skeleton loading grid, empty state, and popup cards.
- API Client Integration: Uses functions from `@/lib/cms/v2` (`listCmsPopups`, `createCmsPopup`, `patchCmsPopup`, `deleteCmsPopup`, `listCmsSites`).
- State Management: Optimistic updates for popup toggles, drawer form state (`SidePanel`), rich text editor (`RichEditor`), delete confirmation modal.
- Notifications: `toast.success()` and `toast.error()` from `sonner`.

---

## 6. Frontend Media Detail Page Analysis (`frontend/src/app/plataforma/cms/media/[id]/page.tsx`)

### 6.1 Routing & Props
- App Router dynamic parameters: `const params = useParams(); const id = params?.id as string;`.
- Programmatic navigation via `useRouter()`.

### 6.2 Data Fetching & Normalization
- Calls `apiFetch<MediaItemData>(`/cms/media/${id}`, { token })`.
- Normalizes server response (falls back `alt_text` to `filename`, `section` to `'general'`, `tags` to `[]`, `mime_type`, `file_size`, `status`).

### 6.3 UI Structure & Components
- **Top Header**: `WorkspaceToolbar` displaying breadcrumbs (`CMS` -> `Media` -> `filename`) and quick action buttons (Archive/Restore, Delete Permanent, Save Metadata).
- **Two-Column Main Grid**:
  - **Left Column**: Media asset viewer (`OptimizedImage` for image types, `<video>` for video, `<audio>` for audio), zoom overlay, Download Original button (`window.open`), Copy URL button (`navigator.clipboard.writeText`).
  - **Right Column**: Title/Alt Text input, Section input, `DSCard` for technical details (Filename, MIME type, Size via `formatBytes`, Upload date), `DSCard` for tag management (`DSBadge` list).
- **Delete Modal**: Modal popup for permanent delete action calling `DELETE /cms/media/{id}?permanent=true`.

---

## 7. Structural Contract Test Analysis (`tests/test_structural_contracts.py`)

### 7.1 Backend API & Database Contracts
1. `test_all_application_routes_stay_under_api_tree_or_explicit_exceptions`: All FastAPI routes must start with `/api/` (except OpenAPI/docs/healthz). Deprecated routes like `/api/announcements` or `/api/testimonials` are strictly forbidden.
2. `test_domain_modules_expose_only_expected_canonical_prefixes`: Routes in `backend.api.cms_v2` MUST start with `/api/cms/v2/`.
3. `test_backend_no_jsonb_columns`: Models must use `JSON` instead of `JSONB` to maintain SQLite compatibility.
4. `test_backend_datetime_columns_always_have_timezone`: `Column(DateTime)` must have `timezone=True`.
5. `test_backend_no_hard_deletes_in_transactional_apis`: `db.delete()` is forbidden in transactional endpoints (must use soft delete / status flag), with strict allowlist exceptions (`backend/crud/cms.py` for static files, etc.).
6. `test_all_runtime_primary_keys_are_uuid`: All database entity primary keys MUST be UUIDs.
7. `test_internal_id_contracts_do_not_use_integer_annotations`: Exposed ID fields in backend schemas must be UUIDs, not integers.

### 7.2 Frontend Contract Rules
1. `test_platform_frontend_respects_ccf_ui_contracts`:
   - Forbidden Tailwind colors: `indigo`, `violet`, `purple`.
   - Forbidden direct imports: `@radix-ui/react-dialog`, `<Dialog`.
   - Forbidden display terms in user copy: `Miembro`, `membresía`.
2. `test_frontend_no_direct_fetch_calls`: Must use `apiFetch()` from `@/lib/http` instead of raw `fetch()` (except binary blob downloads and FormData uploads).
3. `test_frontend_no_legacy_cms_ui_routes`: Frontend UI links and navigation MUST use `/plataforma/cms/...` canonical paths (never legacy `/cms/...`).

---

## 8. Summary Table of Architecture Standards

| Domain | Standard / Requirement | Reference |
|---|---|---|
| Models | UUIDv4 PK, `timezone=True`, `JSON` type (no JSONB) | `backend/models_cms.py`, `tests/test_structural_contracts.py` |
| API Routes | `/cms/v2` prefix, `/sites/{site_key}/...` path params, `require_module_access("cms", ...)` | `backend/api/cms_v2/__init__.py`, `backend/api/cms_v2/popups.py` |
| Migrations | `YYYYMMDD_XXXX_description.py`, dialect UUID helper, `has_table` check | `alembic/canonical_versions/` |
| Frontend Nav | `/plataforma/cms/...` links, Lucide icons, role check, `CmsModuleNav` | `frontend/src/components/cms/CmsModuleNav.tsx` |
| Frontend Detail | `WorkspaceToolbar`, `apiFetch`, `DSCard`, `DSBadge`, `sonner` toast | `frontend/src/app/plataforma/cms/media/[id]/page.tsx` |
| Contracts | `apiFetch` mandatory, soft deletes, no integer PKs/IDs | `tests/test_structural_contracts.py` |

