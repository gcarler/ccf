## 2026-07-30T18:07:57Z
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

You are teamwork_preview_worker for Fix Comments API & TaskCommentSection Build.
Your metadata working directory is `.agents/teamwork_preview_worker_fix_comments_build/`. Create this directory for your briefing and handoff files if needed.

Your task:
Fix the `backend/api/comments.py` import error and `frontend/src/components/projects/TaskCommentSection.tsx` type error so `pytest` and `npx next build` both pass cleanly with 0 errors, and ensure `git status` is clean under a commit prefixed with `feat(cms):`.

Detailed Steps:
1. Backend Fix (`backend/api/comments.py`):
   - Inspect `git diff backend/api/comments.py` or inspect line 61 (`response_model=List[schemas.CommentItem]`).
   - Fix the schema import in `backend/api/comments.py` (e.g., replace `schemas.CommentItem` with `schemas.CommentRead` or the correct schema declared in `backend/schemas/`), or revert uncommitted syntax breaks if invalid.
   - Run `cd /root/ccf && PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v` to ensure all tests pass (0 collection errors).
2. Frontend Fix (`frontend/src/components/projects/TaskCommentSection.tsx`):
   - Inspect line 40 of `frontend/src/components/projects/TaskCommentSection.tsx`.
   - Add `attachments: []` to the initial state objects or adjust the `Comment` interface / mock objects so property `attachments` is satisfied.
   - Run `cd /root/ccf/frontend && npx next build` to ensure 0 TypeScript / build errors (`cd /root/ccf/frontend && npx next build 2>&1 | grep -c "error TS"` returns 0).
3. Stage and Commit:
   - Run `cd /root/ccf && git add .`
   - Run `cd /root/ccf && git commit -m "feat(cms): TipTap media library, full-screen post editor, and native popups module"` (or amend).
   - Verify `cd /root/ccf && git log --oneline -1` shows top commit prefix `feat(cms):`.
   - Verify `cd /root/ccf && git status` shows "nothing to commit, working tree clean".
4. Document all outputs in `.agents/teamwork_preview_worker_fix_comments_build/handoff.md` and send a message to orchestrator when completed.
