# BRIEFING — 2026-07-10T05:30:25Z

## Mission
Coordinate the implementation of the "Super Pro" evolution of CCF's CRM integrating Pastoral Health Score, AI Copilot for Counseling, and Omnichannel Inbox.

## 🔒 My Identity
- Archetype: teamwork_preview_orchestrator
- Roles: orchestrator, user_liaison, human_reporter, successor
- Working directory: /root/ccf/.agents/orchestrator
- Original parent: parent
- Original parent conversation ID: 6d53c929-9ee0-4039-a7d7-1df44e6acb98

## 🔒 My Workflow
- **Pattern**: Project Pattern
- **Scope document**: /root/ccf/PROJECT.md
1. **Decompose**: Decompose the project into milestones (M1: Pastoral Health Score, M2: AI Copilot for Counseling, M3: Omnichannel Inbox, M4: E2E Integration and Adversarial Testing).
2. **Dispatch & Execute** (pick ONE):
   - **Delegate (sub-orchestrator)**: Spawn a sub-orchestrator for each milestone.
3. **On failure** (in this order):
   - Retry: nudge stuck agent or re-send task
   - Replace: spawn fresh agent with partial progress
   - Skip: proceed without (only if non-critical)
   - Redistribute: split stuck agent's remaining work
   - Redesign: re-partition decomposition
   - Escalate: report to parent (sub-orchestrators only, last resort)
4. **Succession**: Self-succeed at 16 spawns, write handoff.md, spawn successor.
- **Work items**:
  - M1: Pastoral Health Score [done]
  - M2: AI Copilot for Pastoral Counseling [done]
  - M3: Omnichannel Inbox [done]
  - M4: E2E Integration & Adversarial Testing [done]
- **Current phase**: Completed
- **Current focus**: Project closure

## 🔒 Key Constraints
- NEVER write, modify, or create source code files directly.
- NEVER run build/test commands yourself — require workers to do so.
- You MAY use file-editing tools ONLY for metadata/state files (.md) in your .agents/ folder.
- Never reuse a subagent after it has delivered its handoff — always spawn fresh

## Current Parent
- Conversation ID: 6d53c929-9ee0-4039-a7d7-1df44e6acb98
- Updated: not yet

## Key Decisions Made
- Initial plan formulated, choosing to decompose into backend, AI copilot, and frontend milestones.

## Team Roster
| Agent | Type | Work Item | Status | Conv ID |
|-------|------|-----------|--------|---------|
| explorer_initial | teamwork_preview_explorer | Codebase exploration and mapping | completed | c9dd4d0f-350d-49f5-bf81-4ef126738817 |
| e2e_testing_orch | self | E2E Testing Track Orchestrator | completed | c7cd5c31-82de-4e34-9435-dc26fbf96d98 |
| implementation_orch | self | Implementation Track Orchestrator | completed | 8a3c398b-1012-4828-8bfa-4aa754c3d601 |
| implementation_orch_succ | self | Implementation Track Successor | completed | 5db48e85-cc03-4ae2-94c4-14cbf69923b9 |

## Succession Status
- Succession required: no
- Spawn count: 3 / 16
- Pending subagents: none
- Predecessor: none
- Successor: not yet spawned

## Active Timers
- Heartbeat cron: none
- Safety timer: none
- On succession: kill all timers before spawning successor
- On context truncation: run manage_task(Action="list") — re-create if missing

## Artifact Index
- /root/ccf/.agents/orchestrator/BRIEFING.md — My persistent working memory
- /root/ccf/.agents/orchestrator/progress.md — Liveness heartbeat and recovery state
- /root/ccf/.agents/orchestrator/plan.md — Step-by-step plan
- /root/ccf/PROJECT.md — Global project index and milestone details
