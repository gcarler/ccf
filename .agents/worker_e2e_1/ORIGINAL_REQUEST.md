## 2026-07-10T05:34:28Z

You are a worker with role "E2E Test Writer".
Your working directory is `/root/ccf/.agents/worker_e2e_1`.
You must:
1. Create `TEST_INFRA.md` at the project root `/root/ccf/TEST_INFRA.md` following the requirements in the project.
2. Implement 38 E2E tests in `/root/ccf/tests/test_crm_super_pro.py` based on the CRM Super Pro requirements (Pastoral Health Score, AI Copilot, Omnichannel Inbox) defined in `/root/ccf/.agents/ORIGINAL_REQUEST.md`.
The tests must follow the 4-tier E2E testing methodology defined in the project:
- Tier 1: Feature Coverage (>= 5 cases per feature) -> 15 cases min.
- Tier 2: Boundary & Corner Cases (>= 5 cases per feature) -> 15 cases min.
- Tier 3: Cross-Feature Combinations (pairwise) -> 3 cases min.
- Tier 4: Real-world Application Scenarios -> 5 cases min.
Total cases should be at least 38.
Use pytest syntax, standard client fixtures, and database sessions.
The tests should be written defensively so that they run, but fail on the baseline project (as the features are not yet implemented).
Specifically:
- Check for the existence of `health_score` and `health_status` columns on the `Persona` model.
- Try calling the scoring engine (e.g. from `backend.services.pastoral_health` or `backend.crud.crm`).
- Make API requests to `/api/crm/counseling/{id}/copilot-draft` (expecting a draft response) and mock the OpenAI client.
- Make API requests to `/api/crm/personas/{persona_id}/timeline` and assert that WhatsApp, SMS, Email, and SpiritualMilestone events are unified and returned chronologically.
3. Run the test suite via `pytest --no-cov tests/test_crm_super_pro.py` to verify that they collect and run correctly, and that they fail on the baseline as expected. Document these failures in your handoff.
4. Create `TEST_READY.md` at the project root `/root/ccf/TEST_READY.md` specifying how to run the test suite, the coverage summary, and a feature checklist.
5. Write your handoff report to `/root/ccf/.agents/worker_e2e_1/handoff.md` and update `/root/ccf/.agents/worker_e2e_1/progress.md` with your status.

MANDATORY INTEGRITY WARNING:
> DO NOT CHEAT. All implementations must be genuine. DO NOT
> hardcode test results, create dummy/facade implementations, or
> circumvent the intended task. A Forensic Auditor will independently
> verify your work. Integrity violations WILL be detected and your
> work WILL be rejected.
