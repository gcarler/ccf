## 2026-07-31T00:35:58Z
You are the Project Orchestrator for the CCF platform CMS v2 improvement plan.

Your task is to orchestrate and execute all 5 pending phases specified in the user request recorded at `/root/ccf/.agents/ORIGINAL_REQUEST.md` (see the section `## Follow-up — 2026-07-31T00:35:14Z`).

Working Directory: `/root/ccf`
Agent Working Directory: `/root/ccf/.agents/orchestrator`

Summary of Requirements:
1. Fase 3 — Document SQL query reduction with query logging in `docs/cms_query_metrics.md` (table showing before/after for `public_page`, `public_post`, `public_menu`, `public_theme`, `public_posts_list`).
2. Fase 4 — Refactor `backend/api/cms_v2.py` into 10 specialized submodules in `backend/api/cms/`:
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
   `backend/api/cms_v2.py` must have < 100 lines. Define custom domain exceptions: `CmsNotFound` (404), `CmsPermissionDenied` (403), `CmsConflict` (409). Maintain 0 breaking changes to frontend API contracts and pass all existing pytest tests.
3. Fase 5 — Complete Playwright E2E suite (`npm run test:e2e:cms`) with 4 critical flows:
   - Main flow: Login -> create page -> add section -> publish -> verify on public site.
   - Menu flow: Edit menu & verify changes in navbar of public site.
   - Media flow: Upload image, verify alt text in media library & public site.
   - Tenant isolation flow: Verify Sede A user cannot access/modify Sede B content.
4. Fase 6 — Accessibility & SEO:
   - Ensure non-empty explicit `alt` for functional CMS images.
   - Add `aria-hidden="true"` for decorative images.
   - Dynamic XML sitemap endpoint or file with published CMS pages.
   - Align `canonical_url` with Next.js/Vite config.
   - Ensure Lighthouse a11y >= 90 and SEO >= 90 on public CMS main page (measure and document).
5. Fase 7 — Documentation & Closure:
   - `docs/cms_architecture.md` (or similar) with Mermaid architecture diagram.
   - API contracts documentation with request/response examples for `public_page`, `public_posts_list`, `patch_section`, `transition_cms_page_status`.
   - `docs/cms_runbook.md` with deploy, rollback, troubleshooting.
   - Update `CHANGELOG.md` with entries for all phases.
6. Transversal criteria:
   - `cd frontend && npm run lint -- --max-warnings=0` passes.
   - `cd frontend && npx tsc --noEmit` = 0 errors.
   - `PYTHONPATH=. python3 -m pytest tests/ -v` all tests pass.
   - Clean `git status` with final commit prefix `feat(cms):` or `docs(cms):`.

7. **Reglas CCF obligatorias**: Todo código producido debe cumplir `/root/ccf/AGENTS_RULES_CCF.md`. Verificar antes de claim victory: backend (datetime.now(timezone.utc) no utcnow, sede_id kwonly, actor UUID 401/409, UUID PKs, soft deletes), frontend (apiFetch no fetch crudo, /plataforma/ prefix, drawers no modals, tokens semánticos hsl(var(--*)), clsx, DS components), DB (migraciones reversibles, no editar cerradas), transversal (lint --max-warnings=0, venv pytest, no 'legacy' substring, coverage 70% o documentar 38% como aceptado). Un victory claim que viole reglas CCF arquitecturales DEBE ser rechazado.
Follow Teamwork principles: create and update `.agents/orchestrator/BRIEFING.md` and `.agents/orchestrator/progress.md`. Dispatch specialist subagents as needed.

When all requirements and acceptance criteria are met, send a completion report claiming victory to the Sentinel.
