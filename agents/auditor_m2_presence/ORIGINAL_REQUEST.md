## 2026-07-30T23:57:21Z
<USER_REQUEST>
You are the Forensic Integrity Auditor subagent assigned to perform a comprehensive audit of Milestone 2 (R2 Real-Time Collaboration Presence).
Your working directory is: /root/ccf/.agents/auditor_m2_presence

Objective:
Perform forensic integrity verification of Milestone 2 implementation and test suite.

Verification Steps:
1. Static Analysis & Code Integrity:
   - Check `backend/api/cms_v2/presence.py`: verify WebSocket endpoint `WS /api/cms/v2/ws/presence/{site_key}/{slug}` and REST endpoint `GET /api/cms/v2/sites/{site_key}/pages/{slug}/presence`.
   - Check `frontend/src/hooks/usePresence.ts`: verify WebSocket lifecycle, auto-reconnect, and presence state management.
   - Check `frontend/src/components/cms/builder/BuilderCanvas.tsx`: verify presence avatar bar, tooltip, `+N más`, and `"personas editando ahora"` label.
   - Verify no dummy/facade implementations or hardcoded test returns.

2. Build & Typecheck Verification:
   - Run `cd /root/ccf/frontend && npm run typecheck`. Verify exit code 0 and EXACTLY 0 TypeScript errors.

3. Test Execution Verification:
   - Run `pytest tests/test_cms_v2_presence.py -v`. Verify all 3 tests pass cleanly.
   - Run `cd /root/ccf/frontend && npx vitest run src/hooks/__tests__/usePresence.test.ts src/components/cms/builder/__tests__/PresenceUI.test.tsx`. Verify all tests pass cleanly.

4. Audit Verdict:
   - Determine whether the implementation is CLEAN or has an INTEGRITY VIOLATION.
   - Write your complete audit report to `/root/ccf/.agents/auditor_m2_presence/handoff.md`.
   - Send a message to the orchestrator with your verdict (CLEAN / INTEGRITY VIOLATION) and summary.
</USER_REQUEST>
