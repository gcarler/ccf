# Project: CCF Enterprise CMS

## Architecture
- Enterprise CMS built with Next.js 15.5, React 18, Tailwind CSS, TypeScript, Sonner, TipTap.
- Automated structural contract testing via pytest (`tests/test_structural_contracts.py`).
- Design system modals via `DSModal` / `AnimatePresence` confirmation modals (raw Radix UI Dialog prohibited by contracts).

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Exploration & Architecture Assessment | Full codebase, UI components, structural test suite analysis | None | DONE |
| 2 | R1 & R2 CMS Gaps | Verify TipTap R1; fix R2 Testimonials missing modal UI block | M1 | IN_PROGRESS |
| 3 | R3 Feedback Toasts Gaps | Add Sonner toast.success to Menus item visibility toggle & TestimonialForm CRUD | M1 | PLANNED |
| 4 | R4 & R6 Announcements & Redirects Polish | Remove line 326 picsum image in Announcements; verify Redirects/Webhooks components | M1 | PLANNED |
| 5 | R5 Dashboard CMS Audit | Verify animate-pulse skeletons, 4-button Quick Actions, recent audit log activity | M1 | PLANNED |
| 6 | R7 Structural Contracts Fixes | Fix purple tokens, legacy comment labels, and direct fetch calls for 100% pytest pass | M1-M5 | PLANNED |
| 7 | R7 Build, Test Verification & Git Delivery | Run Next.js build (0 TS errors), full pytest verification, pre-push, git commit feat(cms)/fix(cms) and git push to main | M6 | PLANNED |

## Interface Contracts
- Toasts: Must use `sonner` (`toast.success`, `toast.error`).
- Modals: Must use native `DSModal` or `AnimatePresence` confirm dialogs (no raw `<Dialog>` imports).
- Editor: Must use TipTap (`RichEditor`).
- Structural Contracts: Must strictly conform to `tests/test_structural_contracts.py` rules (no direct `fetch`, no forbidden color tokens, no `legacy` comments in active code).

## Code Layout
- Frontend: `/root/ccf/frontend`
  - CMS Pages: `/root/ccf/frontend/src/app/plataforma/cms`
    - Posts: `posts/page.tsx`
    - Testimonials: `testimonials/page.tsx`
    - Menus: `menus/page.tsx`
    - Webhooks: `webhooks/page.tsx`
    - Redirects: `redirects/page.tsx`
    - Announcements: `announcements/page.tsx`
    - Dashboard: `/root/ccf/frontend/src/app/plataforma/cms/page.tsx`
  - Components: `/root/ccf/frontend/src/components`
  - Design System: `/root/ccf/frontend/src/design`
- Backend: `/root/ccf/backend`
- Structural Tests: `/root/ccf/tests/test_structural_contracts.py`
