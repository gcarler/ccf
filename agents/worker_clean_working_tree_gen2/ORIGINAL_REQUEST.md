## 2026-07-30T18:00:02Z
You are a Worker subagent assigned to ensure a completely clean working tree and finalize git commits.
Your working directory is: /root/ccf/.agents/worker_clean_working_tree_gen2

Tasks to complete:
1. Check Git Status:
   - Run `cd /root/ccf && git status`
2. Stage and Commit any Remaining Unstaged Changes:
   - Run `cd /root/ccf && git add .`
   - If there are staged changes to commit, run `cd /root/ccf && git commit --amend --no-edit` (or `cd /root/ccf && git commit -m "feat(cms): implement tip-tap media library, full-screen post editor, and native popups module"` if amending is not applicable).
3. Verify Working Tree Cleanliness:
   - Run `cd /root/ccf && git status`
   - Verify output explicitly states: `nothing to commit, working tree clean`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Upon completion, write a detailed handoff report to `/root/ccf/.agents/worker_clean_working_tree_gen2/handoff.md`.
