## 2026-07-31T00:53:19Z
You are Worker 2 for Milestone 2 (Fase 4: Backend Refactor & Query Optimization).

Working Directory: /root/ccf
Your Metadata Directory: /root/ccf/.agents/worker_m2

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Task Description:
1. Read `/root/ccf/.agents/ORIGINAL_REQUEST.md`, `/root/ccf/.agents/explorer_survey_1/handoff.md`, and `/root/ccf/.agents/challenger_m1_1/handoff.md`.
2. Refactor `backend/api/cms_v2.py` / `backend/api/cms_v2/` into 10 specialized submodules in `backend/api/cms/`:
   - `backend/api/cms/admin/pages.py`
   - `backend/api/cms/admin/menus.py`
   - `backend/api/cms/admin/themes.py`
   - `backend/api/cms/admin/sites.py`
   - `backend/api/cms/public/pages.py`
   - `backend/api/cms/public/menus.py`
   - `backend/api/cms/public/posts.py`
   - `backend/api/cms/seo.py`
   - `backend/api/cms/workflow.py`
   - `backend/api/cms/section_types.py`
3. Ensure `backend/api/cms_v2.py` (and/or top-level CMS router entry point) has < 100 lines (only imports and router mounts).
4. Export custom domain exceptions in `backend/exceptions/cms.py`:
   - `CmsNotFound` (mapped to 404, alias or class for `CmsNotFoundError`)
   - `CmsPermissionDenied` (mapped to 403, alias or class for `CmsPermissionError`)
   - `CmsConflict` (mapped to 409, alias or class for `CmsConflictError`)
5. Fix N+1 Query Issues in `public/posts.py` and `public/pages.py`:
   - In `public/posts.py` (`_enrich_public_posts` / `public_posts_list`): Avoid Pydantic ORM validation touching `post.site` (which triggers 11 selectin queries per post). Build `CmsPublicPostRead` without triggering lazy-loading of `post.site` for every post in the list, ensuring `public_posts_list` executes in ~5 queries total.
   - In `public/pages.py` (`_build_section_defaults` / `public_page`): Ensure dynamic section defaults do not execute unnecessary N+1 queries.
6. Update `docs/cms_query_metrics.md` so that the metrics table and details accurately reflect real empirical query counts.
7. Run all backend pytest tests (`PYTHONPATH=. python3 -m pytest tests/ -v`).
8. Write your handoff report at `/root/ccf/.agents/worker_m2/handoff.md`.
- Aplicar `/root/ccf/AGENTS_RULES_CCF.md` — cumplir TODAS las reglas CCF (backend: datetime.now(timezone.utc), sede_id, actor UUID, UUID PKs, soft deletes; frontend: apiFetch, /plataforma/, drawers-no-modals, tokens semánticos, clsx, DS components; DB: migraciones reversibles; transversal: lint, venv pytest, no 'legacy' substring). Ejecutar `cd /root/ccf/frontend && npm run lint -- --max-warnings=0` y `cd /root/ccf && ./venv/bin/python -m pytest` con venv.
9. Send a message to parent (id: f5e54e23-3be1-4361-aea7-d995971998bd) when handoff is complete.
