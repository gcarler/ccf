## 2026-07-31T22:00:13Z
You are Worker for Milestone 6 (R6 E2E Test Suite & Main Route Migration).
Working directory: /root/ccf/frontend/.agents/worker_m6_1

MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your task:
1. Read /root/ccf/frontend/.agents/explorer_m6_1/handoff.md, /root/ccf/frontend/.agents/explorer_m6_2/handoff.md, and /root/ccf/frontend/.agents/explorer_m6_3/handoff.md.
2. Implement Milestone 6 in /root/ccf/frontend:
   - Create Playwright E2E spec `tests/e2e/cms/builder-puck-flow.spec.ts` using `installMockPlatformSession` and route mocks (`GET /api/cms/v2/sites/ccf/pages/home/sections`, `GET /api/cms/v2/public/sites/ccf/theme`, `GET /api/cms/media`, `POST /api/system/ai/generate`, `PATCH/POST /api/cms/v2/sites/ccf/pages/home/sections/*`). Test loading `/plataforma/cms/builder-puck?site=ccf&page=home` and `/plataforma/cms/builder?site=ccf&page=home`, Hero section editing, MediaPicker image selection, AI text generation, auto-save status badge, and DB persistence.
   - Migrate main route `src/app/plataforma/cms/builder/page.tsx`: Move full Puck implementation to `src/app/plataforma/cms/builder/page.tsx`. Re-export from `src/app/plataforma/cms/builder-puck/page.tsx` (`export { default, type SaveStatus } from "../builder/page";`).
   - Update `src/app/plataforma/cms/builder/page.test.tsx` to assert Puck editor rendering (`aria-label="Editor visual Puck"`).
   - Fix the 1 linter warning in `src/app/plataforma/crm/messaging/[id]/page.tsx:76:8` so `npm run lint` finishes with 0 errors and 0 warnings.
3. Run verification commands in /root/ccf/frontend:
   - `npm run typecheck`
   - `npm run lint`
   - `npx playwright test tests/e2e/cms/builder-puck-flow.spec.ts`
4. Write your implementation report and test logs to /root/ccf/frontend/.agents/worker_m6_1/handoff.md. Send a completion message.
