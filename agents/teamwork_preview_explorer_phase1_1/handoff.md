# Handoff Report: CMS Architectural & Structural Analysis

**Agent**: Explorer phase1_1  
**Date**: 2026-07-30  
**Working Directory**: `/root/ccf/.agents/teamwork_preview_explorer_phase1_1`

## 1. Observation
- **Backend Models (`backend/models_cms.py`)**:
  - Contains 19 SQLAlchemy model classes inheriting from `Base` (imported from `backend.models_shared` at line 1).
  - All models use UUIDv4 PKs (`id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)`).
  - Timestamps use timezone-aware DateTime with default `_utcnow` (e.g. line 32: `created_at = Column(DateTime(timezone=True), default=_utcnow)`).
  - Uses standard `JSON` column type (e.g. line 21, 79, 139, 170, 606).
  - Multi-tenant isolation (Axioma 3) implemented via `sede_id` columns (e.g. line 31 in `CmsMediaItem`, line 52 in `CmsSite`, line 554 in `CmsSeoSnapshot`).
  - Table unique constraints defined in `__table_args__` (e.g. line 109, 201, 238, 381, 421, 464, 574).
- **Backend API Routes (`backend/api/cms_v2/__init__.py`, `backend/api/cms_v2/popups.py`, `backend/api/cms.py`)**:
  - `cms_v2` orchestrator (`backend/api/cms_v2/__init__.py`:41-45) mounts sub-routers under `/cms/v2` with `rate_limiter(limit=600, window_seconds=60)`.
  - `popups.py` defines public endpoint `@router.get("/public/popups")` (line 38) and admin endpoints under `/sites/{site_key}/popups` (lines 63, 74, 90, 101, 115).
  - Scoping helper `_get_scoped_site_or_404(db, site_key, current_user)` used across admin CRUD endpoints (lines 70, 86, 97, 110, 124).
  - Authentication and module permissions enforced via `Depends(require_module_access("cms", "read" | "edit"))` and `_assert_role(current_user, CMS_EDITOR_ROLES)`.
  - `cms.py` handles media operations under `/cms/media`, enforcing multi-tenant scoping via `_scope_cms_media_by_user_sede` (line 67) and `_get_scoped_cms_media` (line 131).
- **Alembic Migrations (`alembic/canonical_versions/`)**:
  - Canonical versions directory contains 46 migration files.
  - Head migration: `20260730_0004_add_cms_popups.py` (Revision ID `20260730_0004_add_cms_popups`, Revises `20260730_0003_drop_legacy_announcements_table`).
  - Uses dialect helper `_uuid_type()` to handle PostgreSQL vs SQLite dialects (lines 19-23).
  - Implements table existence check before creation: `if sa.inspect(bind).has_table("cms_popups"): return` (line 28).
- **Frontend Navigation & Popups UI (`frontend/src/components/cms/CmsModuleNav.tsx`, `frontend/src/app/plataforma/cms/popups/page.tsx`)**:
  - `CmsModuleNav.tsx` defines 22 CMS navigation tabs (`Resumen`, `Paginas`, `Popups`, etc.) mapping to `/plataforma/cms/...` paths (lines 36-59).
  - Icons imported from `lucide-react`. Role checks via `canEditCms` and `canManageSites` from `@/lib/cms/permissions` (lines 71-72).
  - `popups/page.tsx` is a `"use client"` page utilizing `@/lib/cms/v2` helpers (`listCmsPopups`, `createCmsPopup`, `patchCmsPopup`, `deleteCmsPopup`, `listCmsSites`), `SidePanel`, `RichEditor`, `framer-motion`, and `sonner` toasts.
- **Frontend Media Detail View (`frontend/src/app/plataforma/cms/media/[id]/page.tsx`)**:
  - Dynamic page using `useParams()` (`const id = params?.id as string`) and `useRouter()`.
  - Data loaded via `apiFetch<MediaItemData>(`/cms/media/${id}`, { token })` (line 65).
  - Layout includes `WorkspaceToolbar` header with breadcrumbs and actions (Archive, Permanent Delete, Save Metadata), left column media viewer (`OptimizedImage`, `<video>`, `<audio>`), right column inputs for title/section and `DSCard` technical info / tags (`DSBadge`).
- **Structural Contract Tests (`tests/test_structural_contracts.py`)**:
  - `test_all_application_routes_stay_under_api_tree_or_explicit_exceptions` (lines 28-65): All routes must be under `/api/` or allowed exceptions. Deprecated `/api/announcements`, `/api/testimonials`, `/api/content/...` are forbidden.
  - `test_domain_modules_expose_only_expected_canonical_prefixes` (lines 147-175): `backend.api.cms_v2` routes must start with `/api/cms/v2/`.
  - `test_backend_no_jsonb_columns` (lines 545-556): Enforces `JSON` over `JSONB` for SQLite compatibility.
  - `test_backend_datetime_columns_always_have_timezone` (lines 558-572): `Column(DateTime)` must specify `timezone=True`.
  - `test_backend_no_hard_deletes_in_transactional_apis` (lines 574-601): Forbids `db.delete()` in transactional endpoints.
  - `test_all_runtime_primary_keys_are_uuid` (lines 643-654): Enforces UUID PKs across all models.
  - `test_platform_frontend_respects_ccf_ui_contracts` (lines 391-426): Forbids `indigo`, `violet`, `purple`, direct `@radix-ui/react-dialog`, and forbidden prose words.
  - `test_frontend_no_direct_fetch_calls` (lines 857-900): Mandatory `apiFetch()` usage.
  - `test_frontend_no_legacy_cms_ui_routes` (lines 902-940): Mandatory `/plataforma/cms/...` UI paths.

## 2. Logic Chain
1. **Observation 1 (Models & Schema)** shows that all 19 CMS entities inherit from `Base`, use `UUID(as_uuid=True)` PKs, `timezone=True` for DateTime columns, and `JSON` instead of `JSONB`.
2. **Observation 6 (Contract Tests)** shows that `test_all_runtime_primary_keys_are_uuid`, `test_backend_datetime_columns_always_have_timezone`, and `test_backend_no_jsonb_columns` strictly enforce these exact model choices. Breaking any of these breaks `pytest tests/test_structural_contracts.py`.
3. **Observation 2 (API Routes)** shows that CMS v2 endpoints are mounted under `/cms/v2`, use `{site_key}` as URL path parameters for site-scoped entities, require `require_module_access("cms", ...)`, and assert user roles with `_assert_role`.
4. **Observation 3 (Migrations)** shows that new database tables follow the `YYYYMMDD_XXXX_description.py` naming standard, use `_uuid_type()` helper for dialect portability, and include idempotency guards (`has_table`).
5. **Observation 4 & 5 (Frontend Components)** show that CMS UI components reside under `/plataforma/cms/...`, use `apiFetch()` for HTTP requests, utilize `WorkspaceToolbar`, `SidePanel`, `DSCard`, `DSBadge`, `sonner` toasts, and `lucide-react` icons, with role checks via `@/lib/cms/permissions`.
6. Therefore, any future CMS model or route development must conform strictly to these 6 architectural dimensions to remain compliant with CCF project standards and pass automated contract verification.

## 3. Caveats
- No caveats. All 6 requested areas were directly inspected in full in the codebase.

## 4. Conclusion
The CMS architecture in `/root/ccf` is highly consistent and rigidly guarded by structural contract tests. Key standards include:
- Backend: `Base` inheritance, UUID PKs, `DateTime(timezone=True)`, `JSON` column types, multi-tenant `sede_id` columns (Axioma 3), soft-delete rules.
- API: Router prefix `/cms/v2`, sub-resource scoping via `/sites/{site_key}/...`, `get_db` session dependency, `require_module_access` and `_assert_role` auth.
- Migrations: Dated files under `alembic/canonical_versions/`, `_uuid_type()` helper, `has_table` idempotency check.
- Frontend: Canonical paths `/plataforma/cms/...`, `apiFetch` from `@/lib/http`, `CmsModuleNav`, `WorkspaceToolbar`, `DSCard`/`DSBadge` design system primitives, `sonner` toasts, `lucide-react` icons.
- Contracts: Enforced by `pytest tests/test_structural_contracts.py`.

## 5. Verification Method
To independently verify these findings:
1. Run structural contract tests:
   ```bash
   pytest tests/test_structural_contracts.py
   ```
2. Inspect the analysis document:
   ```bash
   cat /root/ccf/.agents/teamwork_preview_explorer_phase1_1/analysis.md
   ```
3. Inspect model definitions:
   ```bash
   view_file /root/ccf/backend/models_cms.py
   ```
4. Invalidation conditions: If any test in `test_structural_contracts.py` fails or if model definitions diverge from the UUID/JSON/timezone standards, this analysis is invalidated.
