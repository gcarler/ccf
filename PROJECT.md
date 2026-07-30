# Project: CCF Enterprise CMS

## Architecture
- Enterprise CMS built with Next.js, React, Tailwind CSS, TypeScript, Sonner, TipTap.
- Automated testing harness via pytest (`tests/test_structural_contracts.py`).

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Architecture & Contract Exploration | Inspect codebase layout, existing components, tests, and current implementations | None | IN_PROGRESS |
| 2 | R1: TipTap RichEditor Integration | Integrate TipTap RichEditor in Posts and Testimonials | M1 | PLANNED |
| 3 | R2: Destructive Confirmation Modals | Implement native confirmation modals on destructive actions across media, categories, tags, themes, branding, announcements, pages, testimonials | M1 | PLANNED |
| 4 | R3: Feedback Toasts (Sonner) | Add Sonner toast.success and toast.error on CRUD operations in menus, testimonials, webhooks, redirects | M1 | PLANNED |
| 5 | R4: Webhooks & Redirects Redesign | Fix misplaced imports bug in redirects/page.tsx, implement UI components, badges, filters, skeletons, empty states | M1 | PLANNED |
| 6 | R5: Dashboard CMS Enhancements | Add animate-pulse skeletons, Quick Actions card with 4 buttons, recent activity card backed by audit logs | M1 | PLANNED |
| 7 | R6: Announcements Enhancements | Remove mock picsum images, add CSS gradient background, search field, state filters | M1 | PLANNED |
| 8 | R7: Clean Build, Test & Git Delivery | Next.js build (0 TS errors), pytest tests/test_structural_contracts.py, pre-push verification, git commit feat(cms)/fix(cms), git push to main | M2-M7 | PLANNED |

## Interface Contracts
- To be refined post-exploration.

## Code Layout
- To be mapped post-exploration.
