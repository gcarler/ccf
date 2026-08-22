## 2026-07-30T18:26:53Z
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

You are teamwork_preview_worker for TaskCommentSection TS Fix & feat(cms): Commit Prefix.
Your metadata working directory is `.agents/teamwork_preview_worker_final_build_commit_fix/`. Create this directory for your briefing and handoff files if needed.

Your task:
Fix the `ProjectCommentItem` type mismatch in `frontend/src/components/projects/TaskCommentSection.tsx` so `npx next build` passes cleanly with 0 TypeScript errors, and ensure the top git commit message is prefixed with `feat(cms):` with a clean working tree.

Detailed Steps:
1. Fix `frontend/src/components/projects/TaskCommentSection.tsx`:
   - Inspect line 47 (`attachments: c.attachments || []`). `ProjectCommentItem` interface (in `TaskCommentSection.tsx` or imported type) lacks `attachments`.
   - Update `ProjectCommentItem` interface definition to include `attachments?: any[]` (or `attachments?: Attachment[]`), OR cast `(c as any).attachments || []`.
   - Run `cd /root/ccf/frontend && npx next build` to verify **0 TypeScript / compilation errors** (`cd /root/ccf/frontend && npx next build 2>&1 | grep -c "error TS"` returns 0).
2. Run Pytest suite:
   - Run `cd /root/ccf && PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v` to ensure all structural contract tests pass.
3. Fix Git Commit Prefix & Working Tree:
   - Run `cd /root/ccf && git add .`
   - Run `cd /root/ccf && git commit -m "feat(cms): TipTap media library, full-screen post editor, and native popups module"` (or amend so the latest commit message prefix is explicitly `feat(cms):`).
   - Run `cd /root/ccf && git log --oneline -1` and verify the commit message starts with `feat(cms):`.
   - Run `cd /root/ccf && git status` and verify output displays "nothing to commit, working tree clean".
4. Document all command outputs in `.agents/teamwork_preview_worker_final_build_commit_fix/handoff.md` and send a message to orchestrator when completed.
