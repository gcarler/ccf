## 2026-07-31T23:56:12Z
<USER_REQUEST>
You are Worker for Milestone 6 (R6 Audit Remediation & Final Quality Verification).
Working directory: /root/ccf/frontend/.agents/worker_m6_remediate

MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your task:
1. Inspect `src/app/plataforma/cms/builder/RouteHandlingEdgeCases.test.tsx` and run `npx eslint src/app/plataforma/cms/builder/RouteHandlingEdgeCases.test.tsx`.
2. Fix any unused imports/variables or ESLint rule violations in `RouteHandlingEdgeCases.test.tsx` so that `npm run lint` passes cleanly with exit code 0 and 0 errors across the entire codebase.
3. Run verification commands in /root/ccf/frontend:
   - `npm run typecheck`
   - `npm run lint`
   - `node scripts/run-managed-playwright.mjs tests/e2e/cms/builder-puck-flow.spec.ts`
4. Write your implementation report to /root/ccf/frontend/.agents/worker_m6_remediate/handoff.md. Send a completion message.
</USER_REQUEST>
