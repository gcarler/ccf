## 2026-07-31T00:36:26Z
You are Explorer 1 (Backend & Query Metrics Survey) for the CCF CMS v2 improvement project.

Working Directory: /root/ccf
Your Metadata Directory: /root/ccf/.agents/explorer_survey_1

Task Description:
1. Read `/root/ccf/.agents/ORIGINAL_REQUEST.md` (specifically the section `## Follow-up — 2026-07-31T00:35:14Z`).
2. Investigate the backend structure:
   - Read `backend/api/cms_v2.py`, count total lines, identify all endpoints, dependencies, exceptions, database queries, and submodules to be refactored in Fase 4 into 10 submodules under `backend/api/cms/`:
     - `admin/pages.py`
     - `admin/menus.py`
     - `admin/themes.py`
     - `admin/sites.py`
     - `public/pages.py`
     - `public/menus.py`
     - `public/posts.py`
     - `seo.py`
     - `workflow.py`
     - `section_types.py`
   - Check custom exception needs: `CmsNotFound` (404), `CmsPermissionDenied` (403), `CmsConflict` (409).
   - Inspect existing pytest suite `tests/` (`PYTHONPATH=. python3 -m pytest tests/ -v`).
3. Investigate SQL Query Logging & Metrics (Fase 3):
   - Check how queries are executed for `public_page`, `public_post`, `public_menu`, `public_theme`, `public_posts_list`.
   - Determine how to log/count SQL queries in development environment to produce `docs/cms_query_metrics.md`.
4. Create your progress log at `/root/ccf/.agents/explorer_survey_1/progress.md` with liveness timestamp.
5. Write your comprehensive handoff report at `/root/ccf/.agents/explorer_survey_1/handoff.md`.
- Reportar cualquier violación de las reglas CCF (`/root/ccf/AGENTS_RULES_CCF.md`) encontrada durante la investigación: utcnow(), fetch() crudo, bg-blue-500, modals en vez de drawers, sede_id hardcodeado, migraciones editadas, etc.
6. Send a message to parent (id: f5e54e23-3be1-4361-aea7-d995971998bd) when handoff is complete.
