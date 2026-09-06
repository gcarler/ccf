## 2026-09-06T03:06:47Z

Modularizar atómicamente las secciones de la página Home en la base de datos de CCF (Comunidad Cristiana El Faro) y habilitar controles de reordenamiento interactivo en tiempo real desde el CMS con renderizado dinámico en el sitio público.

Working directory: /root/ccf-cms-main-final
Integrity mode: development

## Requirements

### R1. Atomic Database Modularization (PostgreSQL)
Decouple the monolithic `feed` section in `cms_sections` into discrete atomic sections with distinct `section_key`s (`welcome` / `feed` for Bento cards, `activities` for upcoming events, `newsletter` for the subscription form) while preserving `hero` and `discover_cta`. Must execute under an idempotent, atomic transaction with zero data loss.

### R2. Interactive Reordering Controls in CMS Builder
Provide intuitive visual reordering controls (Move Up / Move Down buttons) on every section card within `PublicContentEditor`. Trigger optimistic UI updates and persist changes immediately via the existing `reorderCmsSections` API (`POST /api/cms/v2/sites/{site_key}/pages/{slug}/sections/reorder`) with error rollback and notification.

### R3. Dynamic Section Rendering in Public Home Page
Refactor `PublicHomePage.tsx` from static JSX ordering to dynamically render sections based on `sort_order`. Maintain 100% backward compatibility with legacy combined schemas so no component breaks if fallback props are present.

### R4. Real-time Cache Invalidation & Verification
Verify that Redis cache invalidation triggers instantly upon reordering, test the end-to-end flow with automated tests, and ensure zero TypeScript errors (`tsc --noEmit`) and successful build deployment.

## Acceptance Criteria

### Database Integrity
- [ ] Idempotent migration script executes without errors and separates `feed` into atomic sections without losing existing card, activity, or newsletter props.
- [ ] `cms_sections` reflects valid distinct `sort_order` integer sequences.

### CMS Builder
- [ ] `PublicContentEditor` displays Up/Down action buttons on each section header with appropriate disabled states for top/bottom items.
- [ ] Clicking Up/Down sends `items: [{id, sort_order}]` to `/sections/reorder` and updates the layout immediately.
- [ ] Network errors trigger an automatic state rollback and user-facing error toast.

### Public Site
- [ ] `PublicHomePage` renders all sections respecting the exact order defined in `cms_sections.sort_order`.
- [ ] Moving Newsletter above Bienvenidos a Casa in CMS immediately reflects in `http://localhost:3000/` without delay.
- [ ] Fallback support guarantees zero regressions if a section contains legacy combined fields.

### Verification & Quality
- [ ] `npx tsc --noEmit -p frontend/tsconfig.json` passes cleanly with 0 type errors.
- [ ] Deployment script `bash scripts/deploy_frontend.sh` executes with HTTP 200 verification.
