## 2026-07-30T16:31:52Z
You are Worker 2 (Structural Contract Fixes & Build Verification). Your working directory is /root/ccf/.agents/teamwork_preview_worker_contract_fixes_1.
Your mission is to fix all structural contract test failures in `tests/test_structural_contracts.py` and verify Next.js clean build in /root/ccf:

1. Fix `test_platform_frontend_respects_ccf_ui_contracts`:
   - In `frontend/src/app/plataforma/mensajes/page.tsx`: replace forbidden `purple` color token usages (lines 42, 640) with allowed CCF design system tokens (e.g. `violet`, `indigo`, or standard platform UI theme classes).
   - In `frontend/src/components/BuilderSectionInspector.test.tsx` (or wherever line 857 is): replace forbidden mock role `'Miembro'` with an allowed CCF UI contract role.

2. Fix `test_active_code_does_not_reintroduce_old_architecture_labels`:
   - Inspect `backend/api/cms.py` (around lines 44, 247) and `frontend/src/lib/cms/v2.ts` (around line 1030).
   - Clean up comment lines containing the forbidden label word `legacy` (rephrase or remove obsolete comments) so the contract check passes.

3. Fix `test_frontend_no_direct_fetch_calls`:
   - In `frontend/src/app/plataforma/mensajes/page.tsx`: replace direct `fetch('/api/chat/upload-attachment')` (line 234) with standardized API client invocation (e.g. `apiClient.post` or custom API helper module).

4. Verify Build and Test Suite:
   - Run `pytest tests/test_structural_contracts.py` using run_command to verify 100% test pass (44/44 tests passed).
   - Run `npm run build` inside `frontend/` to verify clean Next.js build with 0 TypeScript errors.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

When finished, write your handoff report to /root/ccf/.agents/teamwork_preview_worker_contract_fixes_1/handoff.md and report back to the parent orchestrator with test output details.
