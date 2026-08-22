## 2026-07-30T23:58:42Z
<USER_REQUEST>
You are a Forensic Auditor subagent for Milestone M2 (R2: Real-Time Presence Collaboration).
Working Directory: /root/ccf/.agents/teamwork_preview_auditor_m2_2/
Project root: /root/ccf

Your task is to conduct an independent integrity audit of the code implemented for Milestone M2:
- `backend/api/cms_v2/presence.py`
- `backend/core/rate_limit.py`
- `frontend/src/hooks/usePresence.ts`
- `frontend/src/components/cms/builder/BuilderCanvas.tsx`
- `tests/test_cms_v2_presence.py`

Audit requirements:
1. Run `PYTHONPATH=. python3 -m pytest tests/test_cms_v2_presence.py tests/test_structural_contracts.py -v` and confirm 100% pass (46 passed, 1 skipped).
2. Run `cd /root/ccf/frontend && npx tsc --noEmit` and confirm 0 errors.
3. Verify genuine implementation (no hardcoded test results, facade logic, or cheating).
4. Verify WebSocket handling, token parsing, auto-reconnect, and UI presence avatars.

Write your audit report to `/root/ccf/.agents/teamwork_preview_auditor_m2_2/audit.md` and handoff report to `/root/ccf/.agents/teamwork_preview_auditor_m2_2/handoff.md`.
Send a message back with your verdict: CLEAN or INTEGRITY VIOLATION, along with detailed evidence.
</USER_REQUEST>
