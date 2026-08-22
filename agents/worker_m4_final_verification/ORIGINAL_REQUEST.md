## 2026-07-30T19:17:40Z
<USER_REQUEST>
You are a Worker subagent assigned to Milestone 4: Final Integration Verification, Build & Git Commit.
Your working directory is: /root/ccf/.agents/worker_m4_final_verification

Tasks to complete:
1. TypeScript Validation:
   - Run `cd /root/ccf/frontend && npx tsc --noEmit`
   - Verify 0 TypeScript errors.

2. Structural Contracts Verification:
   - Run `cd /root/ccf && PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v`
   - Verify all tests pass cleanly (exit code 0).

3. Git Commit & Working Tree Verification:
   - Stage all changes: `cd /root/ccf && git add .`
   - Commit with required commit message prefix `feat(cms):`:
     `cd /root/ccf && git commit -m "feat(cms): implement contact forms, newsletter email marketing, and media library image editor"`
   - Verify `cd /root/ccf && git log -1 --oneline` starts with `feat(cms):`.
   - Verify `cd /root/ccf && git status` outputs `nothing to commit, working tree clean`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Upon completion, write a detailed handoff report to `/root/ccf/.agents/worker_m4_final_verification/handoff.md`.
</USER_REQUEST>
