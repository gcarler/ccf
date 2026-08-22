## 2026-07-30T18:30:03Z

<USER_REQUEST>
You are a Worker subagent assigned to fix the ProjectCommentItem TS error in TaskCommentSection.tsx and verify the feat(cms): commit prefix and clean working tree.
Your working directory is: /root/ccf/.agents/worker_final_build_commit_fix_gen2

Tasks to complete:
1. Fix ProjectCommentItem TS error in TaskCommentSection.tsx:
   - Check `frontend/src/components/projects/TaskCommentSection.tsx` and `frontend/src/types/projects.ts`.
   - Ensure `attachments` property on `ProjectCommentItem` is correctly typed (e.g. `attachments?: { url: string; type: string; name: string; size: number }[]` or aligned with backend/frontend comment types).
   - Run `cd /root/ccf/frontend && npx next build` and verify exit code 0 (0 TS/build errors).

2. Structural Contracts Verification:
   - Run `cd /root/ccf && PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v`
   - Verify exit code 0 (43 passed).

3. Git Commit Prefix & Working Tree Verification:
   - Stage all changes: `cd /root/ccf && git add .`
   - Ensure the latest commit has message starting with `feat(cms):`:
     `cd /root/ccf && git commit --amend -m "feat(cms): implement tip-tap media library, full-screen post editor, and native popups module"`
   - Verify `cd /root/ccf && git log -1 --oneline` starts with `feat(cms):`.
   - Verify `cd /root/ccf && git status` outputs `nothing to commit, working tree clean`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Upon completion, write a detailed handoff report to `/root/ccf/.agents/worker_final_build_commit_fix_gen2/handoff.md`.
</USER_REQUEST>
