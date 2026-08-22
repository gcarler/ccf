## 2026-07-31T00:06:24Z
You are a Worker subagent assigned to implement Milestone 5: R5 Full-Text Search.
Your working directory is: /root/ccf/.agents/worker_m5_search

Detailed Requirements:
1. Backend Endpoint (`backend/api/cms_v2/search.py`):
   - `GET /api/cms/v2/search?q=texto&site_key=X&types=pages,posts,announcements,sections&limit=20`:
     - Searches across `CmsPage` (title, meta_description), `CmsPost` (title, content, excerpt), `CmsSection` (props_json), and `CmsAnnouncement` (title, content).
     - Employs PostgreSQL `ILIKE` or `to_tsvector/to_tsquery` to match query string `q`.
     - Orders results by relevance (exact matches first, then partial matches).
     - Returns unified array: `[{type: 'page'|'post'|'announcement'|'section', id: string, title: string, excerpt: string, url: string, site_key: string, updated_at: string}]`.
   - Register router in `backend/api/cms_v2/__init__.py`.

2. Frontend Admin Page (`frontend/src/app/plataforma/cms/search-admin/page.tsx`):
   - Search input with 300ms debounce.
   - Filter chips for types (Todas, Páginas, Publicaciones, Secciones, Anuncios).
   - Results list displaying title, type badge, content excerpt snippet, updated timestamp, and direct edit link.
   - Empty state, loading skeleton, and error toast handling.

3. Frontend Public Component (`frontend/src/components/public/cms/SearchBar.tsx`):
   - Public search bar component with input + floating dropdown.
   - Triggers search when input length >= 3 characters with 300ms debounce.
   - Floating dropdown displaying title, type badge, and excerpt.
   - Keydown listener for `Escape` to close dropdown.
   - Click outside listener to dismiss dropdown.

4. Testing & Typecheck:
   - Run `cd /root/ccf/frontend && npm run typecheck` to ensure 0 TypeScript errors.
   - Write backend tests in `tests/test_cms_v2_search.py` and frontend vitest tests for `SearchBar.tsx` and search-admin page.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Upon completion, write a detailed handoff report to `/root/ccf/.agents/worker_m5_search/handoff.md`.
