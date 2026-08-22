# BRIEFING — 2026-07-30T17:42:15Z

## Mission
Adversarially challenge and stress-test frontend Popups implementation (`frontend/src/app/plataforma/cms/popups/page.tsx` and `frontend/src/components/cms/PopupManager.tsx`).

## 🔒 My Identity
- Archetype: empirical_challenger
- Roles: critic, specialist
- Working directory: /root/ccf/.agents/teamwork_preview_challenger_m4_1
- Original parent: 2e22d12a-a4c1-48e7-a021-21d0d6590580
- Milestone: Native Popups Frontend R3-FE (Milestone 4)
- Instance: 1 of 1

## 🔒 Key Constraints
- Review-only — do NOT modify implementation code (write unit/integration test harnesses or scripts for empirical verification if needed, but do not touch main application source code unless fixing or creating test scripts outside source).
- Verification must be empirical: execute tests / scripts and analyze outputs.
- **Reglas CCF obligatorias**: Leer y aplicar `/root/ccf/AGENTS_RULES_CCF.md`. Verificar TODO el checklist de la sección 6, no solo grep de features.
- **Lint obligatorio**: Ejecutar `cd /root/ccf/frontend && npm run lint -- --max-warnings=0` además de typecheck. Es criterio transversal CCF.
- **Venv para pytest**: Ejecutar `cd /root/ccf && ./venv/bin/python -m pytest` (no `python3` directo).

## Current Parent
- Conversation ID: 2e22d12a-a4c1-48e7-a021-21d0d6590580
- Updated: 2026-07-30T17:42:15Z

## Review Scope
- **Files to review**: `frontend/src/app/plataforma/cms/popups/page.tsx`, `frontend/src/components/cms/PopupManager.tsx`
- **Verification focus**: Trigger engine evaluation, session storage suppression, path matching logic, Admin UI robustness, Next.js production build (`npx next build`).

## Key Decisions Made
- Created empirical stress test suite `frontend/src/components/cms/PopupManagerAdversarial.test.tsx` containing 14 unit and integration tests covering all triggers (`on_load`, `time_delay`, `scroll_percent`, `exit_intent`), path matching rules, session storage suppression, admin UI modal flows, and edge cases.
- Executed `npm test` across the full frontend test suite (107 test files, 760 tests passed).
- Executed `PopupManagerAdversarial.test.tsx` (14/14 tests passed).
- Triggered Next.js production build (`npx next build`).

## Artifact Index
- `.agents/teamwork_preview_challenger_m4_1/ORIGINAL_REQUEST.md` — Original request
- `.agents/teamwork_preview_challenger_m4_1/BRIEFING.md` — Briefing document
- `.agents/teamwork_preview_challenger_m4_1/progress.md` — Progress log
- `.agents/teamwork_preview_challenger_m4_1/handoff.md` — Final challenge report
- `frontend/src/components/cms/PopupManagerAdversarial.test.tsx` — Empirical adversarial test harness

## Loaded Skills
- **ccf-backend-guard**: Backend safety (FastAPI, SQLAlchemy, sede_id, soft deletes, datetime, UUID).
- **ccf-ui-guard**: Frontend safety (Next.js, apiFetch, /plataforma/, drawers, semantic tokens, DS 3-layer).
- **ccf-architecture-guard**: Cross-layer change planning and rollback safety.

## Attack Surface
- **Hypotheses tested**:
  1. `on_load` triggers immediately and sets `sessionStorage` flag. (CONFIRMED)
  2. `time_delay` triggers after specified delay and clears timer on route change / unmount. (CONFIRMED)
  3. `time_delay` with `trigger_value = 0` falls back to `5s` default due to `trigger_value > 0` check. (VULNERABILITY / EDGE CASE IDENTIFIED)
  4. `scroll_percent` calculates `(scrollTop / scrollHeight) * 100` and cleans up scroll listener upon firing. (CONFIRMED)
  5. `scroll_percent` on short pages (`scrollHeight <= clientHeight`) gracefully suppresses trigger without error. (CONFIRMED)
  6. `exit_intent` triggers on `mouseleave` with `clientY < 10`. (CONFIRMED)
  7. Path matching handles wildcard `*`, exact matches, and prefix wildcards like `/cursos/*`. (CONFIRMED)
  8. Session storage suppression prevents re-showing popups already marked `popup_shown_${id} = "1"`. (CONFIRMED)
  9. Admin UI supports optimistic toggle of `is_active`, modal confirmation for popup deletion, and drawer form validation. (CONFIRMED)
  10. When creating `on_load` or `exit_intent` popups, `formTriggerValue` sends `5` instead of `null`. (MINOR DISCREPANCY IDENTIFIED)
- **Vulnerabilities found**:
  - `trigger_value = 0` fallback to default `5s` (time_delay) / `50%` (scroll_percent).
  - Unhandled `sessionStorage` exceptions in private browsing or disabled cookie environments (no `try / catch` around `sessionStorage.getItem` / `setItem`).
  - Payload for `on_load` and `exit_intent` in `page.tsx` sends `trigger_value: 5` instead of `null`.
- **Untested angles**:
  - Real browser multi-tab synchronization of `sessionStorage` (since `sessionStorage` is per tab session by browser design).
