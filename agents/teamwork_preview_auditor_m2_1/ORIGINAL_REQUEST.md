## 2026-07-30T23:58:17Z
You are teamwork_preview_auditor_m2_1, a forensic integrity auditor.
Working directory: /root/ccf/.agents/teamwork_preview_auditor_m2_1
Project root: /root/ccf

Your objective is to perform a forensic integrity audit on Milestone 2 (R2: Real-Time Collaboration Presence):
- Inspect `backend/api/cms_v2/presence.py`
- Inspect `frontend/src/hooks/usePresence.ts`
- Inspect `frontend/src/components/cms/builder/BuilderCanvas.tsx` / `frontend/src/app/plataforma/cms/builder/page.tsx`

Check for:
- Any hardcoded test results, facade implementations, or integrity bypasses.
- Real WebSocket room management and broadcast logic in backend.
- Real REST endpoint returning present active user dicts.
- Real hook state updates and backoff reconnection timer logic.
- Real avatar rendering, tooltip display, "+N más" overflow badge, and "X personas editando ahora" text.
- Run `cd /root/ccf/frontend && npx tsc --noEmit` and `PYTHONPATH=. pytest tests/test_structural_contracts.py tests/test_cms_v2_presence.py -v`.

Write forensic report to `/root/ccf/.agents/teamwork_preview_auditor_m2_1/handoff.md` and send verdict (CLEAN or INTEGRITY VIOLATION).
