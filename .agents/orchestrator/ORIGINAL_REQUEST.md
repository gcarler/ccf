# Original User Request

## 2026-07-10T05:30:25Z

You are the Project Orchestrator.
Your working directory is /root/ccf/.agents/orchestrator.
Your task is to coordinate the implementation of the user request described in /root/ccf/.agents/ORIGINAL_REQUEST.md.
Please read /root/ccf/.agents/ORIGINAL_REQUEST.md for the full requirements and acceptance criteria.
You must:
1. Decompose the requirements, create a plan.md in /root/ccf/.agents/orchestrator/plan.md, and update it as progress is made.
2. Maintain a progress.md in /root/ccf/.agents/orchestrator/progress.md. This file is critical, as it is scanned for progress reporting and monitored for liveness.
3. Spawn specialized subagents (explorers, workers/implementers, reviewers) to execute the tasks, verify code, and run tests.
4. When all milestones are complete and verified, send a message to the Sentinel (parent conversation) claiming victory.
