## 2026-07-30T18:10:03Z
You are a Worker subagent assigned to remediate comments and TaskCommentSection build issues in Milestone 5.
Your working directory is: /root/ccf/.agents/worker_fix_comments_build_gen2

Objective:
1. Fix Frontend TS Error in `TaskCommentSection.tsx`:
   - Inspect `frontend/src/components/TaskCommentSection.tsx` or related components for attachments type errors.
   - Fix the TypeScript error so `npx next build` passes cleanly.

2. Fix Backend Import Error in `backend/api/comments.py`:
   - Inspect `backend/api/comments.py` for any missing or broken imports.
   - Fix the import error so `PYTHONPATH=. pytest tests/test_structural_contracts.py -v` passes cleanly.

3. Verify Next.js Build:
   - Run `cd /root/ccf/frontend && npx next build`
   - Verify exit code 0 and 0 TypeScript/build errors.

4. Verify Structural Contract Tests:
   - Run `cd /root/ccf && PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v`
   - Verify all tests pass cleanly.

5. Stage, Commit & Clean Working Tree:
   - Stage changes: `cd /root/ccf && git add .`
   - Commit changes: `cd /root/ccf && git commit -m "feat(cms): implement tip-tap media library, full-screen post editor, and native popups module"` (or `git commit --amend --no-edit` if amending recent commit).
   - Check status: `cd /root/ccf && git status` (must say "nothing to commit, working tree clean").

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Upon completion, write a detailed handoff report to `/root/ccf/.agents/worker_fix_comments_build_gen2/handoff.md`.
