## 2026-07-31T00:44:10Z
<USER_REQUEST>
You are Forensic Auditor for Milestone 1 (Fase 3: Query Metrics Documentation).

Working Directory: /root/ccf
Metadata Directory: /root/ccf/.agents/auditor_m1

Task Description:
1. Read `/root/ccf/.agents/ORIGINAL_REQUEST.md` and `/root/ccf/docs/cms_query_metrics.md`.
2. Conduct forensic integrity checks on `docs/cms_query_metrics.md` and backend code:
   - Check if metrics or test outputs were fabricated or hardcoded.
   - Verify that actual query batching logic exists in code and is genuinely tested.
3. Write your handoff report at `/root/ccf/.agents/auditor_m1/handoff.md` concluding with an explicit verdict: CLEAN or INTEGRITY VIOLATION.
6. Aplicar el checklist de auditoría CCF de `/root/ccf/AGENTS_RULES_CCF.md` sección 6 — verificar backend (datetime.now(timezone.utc), sede_id, actor UUID, UUID PKs, soft deletes, HTTPException semánticos), frontend (apiFetch, /plataforma/, drawers-no-modals, tokens semánticos, clsx, DS components), DB (migraciones reversibles, no edición de cerradas), y transversal (lint --max-warnings=0, venv pytest, no 'legacy' substring).
7. Ejecutar `cd /root/ccf/frontend && npm run lint -- --max-warnings=0` — debe pasar limpio.
8. Ejecutar pytest con venv: `cd /root/ccf && ./venv/bin/python -m pytest tests/test_cms* -v`.
4. Send a message to parent (id: f5e54e23-3be1-4361-aea7-d995971998bd) when handoff is complete.
</USER_REQUEST>
