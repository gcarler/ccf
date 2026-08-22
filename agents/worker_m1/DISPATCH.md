## 2026-07-31T00:41:03Z

You are Worker 1 for Milestone 1 (Fase 3: Query Metrics Documentation).

Working Directory: /root/ccf
Your Metadata Directory: /root/ccf/.agents/worker_m1

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Task Description:
1. Read `/root/ccf/.agents/ORIGINAL_REQUEST.md` and `/root/ccf/.agents/explorer_survey_1/handoff.md`.
2. Ensure `docs/cms_query_metrics.md` exists and contains a complete, accurate table showing pre-optimization vs post-optimization SQL query counts for the 5 public endpoints:
   - `public_page` (`GET /api/cms/v2/public/sites/{site_key}/pages/{slug}`)
   - `public_post` (`GET /api/cms/v2/public/sites/{site_key}/posts/{slug}`)
   - `public_menu` (`GET /api/cms/v2/public/sites/{site_key}/menus/{menu_key}`)
   - `public_theme` (`GET /api/cms/v2/public/sites/{site_key}/theme`)
   - `public_posts_list` (`GET /api/cms/v2/public/sites/{site_key}/posts`)
3. Run backend tests to verify endpoints respond cleanly (`PYTHONPATH=. python3 -m pytest tests/ -v`).
4. Write your handoff report at `/root/ccf/.agents/worker_m1/handoff.md` detailing changes, test commands and results.
- Aplicar `/root/ccf/AGENTS_RULES_CCF.md` — cumplir TODAS las reglas CCF (backend: datetime.now(timezone.utc), sede_id, actor UUID, UUID PKs, soft deletes; frontend: apiFetch, /plataforma/, drawers-no-modals, tokens semánticos, clsx, DS components; DB: migraciones reversibles; transversal: lint, venv pytest, no 'legacy' substring). Ejecutar `cd /root/ccf/frontend && npm run lint -- --max-warnings=0` y `cd /root/ccf && ./venv/bin/python -m pytest` con venv.
5. Send a message to parent (id: f5e54e23-3be1-4361-aea7-d995971998bd) when handoff is complete.
