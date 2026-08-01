# Project: Puck Editor Visual Integration & Platform Migration

## Architecture
- **Framework**: Next.js 14+ (App Router, Tailwind CSS, TypeScript)
- **Editor Engine**: `@puckeditor/core` (`<Puck ... />`) with `iframe={{ enabled: false }}` for direct DOM style & theme variable inheritance.
- **Theme System**: Site theme fetched from `/cms/v2/public/sites/${siteKey}/theme` mapped to CSS custom properties (`--site-background`, `--site-primary`, etc.) on container `<main style={themeStyles}>`. Fonts: `Outfit` and `Inter` via `next/font/google`.
- **Media System**: `MediaPicker` component (`src/components/cms/builder/MediaPicker.tsx`) connected via callback coordinator (`mediaPickerTrigger`) to custom image field renderers in Puck (`bg_image`, `image_url`, `url`). Storage backed by SeaweedFS (`/cms/media`).
- **AI Text Assistant**: `AiTextInput` inline/standalone component invoking POST `/system/ai/generate` for auto-generating titles, descriptions, and body content.
- **Persistence Layer**: CMS V2 REST API (`/cms/v2/sites/${siteKey}/pages/${pageSlug}/sections`). Dual-mode persistence: debounced automatic background save (`onChange`) + immediate synchronous manual save (`onPublish` / header button).
- **E2E Test Suite**: Playwright specs under `tests/e2e/cms/builder-puck-flow.spec.ts` mocking auth and CMS APIs, validating block editing, MediaPicker, AI text generation, auto-save, and DB persistence.
- **Primary Routes**:
  - Puck Editor Source Component: `src/app/plataforma/cms/builder-puck/page.tsx`
  - Main CMS Builder Route (Migration Target): `src/app/plataforma/cms/builder/page.tsx`

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Outfit & Inter Fonts | Import `Outfit` from `next/font/google` in `src/app/layout.tsx`, pass variable to `<html>`, map in `tailwind.config.ts` | M1 | R1 |
| 2 | Puck iframe & Theme Sync | Verify `<Puck iframe={{ enabled: false }}>`, ensure `--site-*` variables and `var(--site-background)` styling cascade to Puck canvas | M1 | R1 |
| 3 | MediaPicker Integration | Connect `MediaPicker` drawer for image selection in Puck fields (Hero `bg_image`, Cards `image_url`, Gallery `url`) | M2 | R2 |
| 4 | AI Writing Assistant | Integrate `AiTextInput` on Puck inputs/textareas calling `/system/ai/generate` for Hero, Rich Text, CTA Banner | M3 | R3 |
| 5 | Complex Blocks Catalog | Verify & refine `gallery` and `cards` blocks with array fields (dynamic add, reorder, delete sub-elements) | M4 | R4 |
| 6 | Auto-Save & Save Button | Implement 2-5s debounced auto-save on Puck `onChange` + header manual Publish/Save button for instant DB sync | M5 | R5 |
| 7 | Playwright E2E Suite | Create and execute green Playwright test `tests/e2e/cms/builder-puck-flow.spec.ts` | M6 | R6 |
| 8 | Main Route Migration | Replace `src/app/plataforma/cms/builder/page.tsx` with Puck editor implementation | M6 | R6 |
| 9 | Quality Verification | `npm run typecheck` (0 errors), `npm run lint` (0 errors/warnings) | M6 | Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | R1 Theme & CSS Sync | `layout.tsx`, `tailwind.config.ts`, `builder-puck/page.tsx` | none | DONE |
| M2 | R2 MediaPicker Integration | `builder-puck/page.tsx`, `MediaPicker.tsx` | M1 | DONE |
| M3 | R3 AI Writing Assistant | `builder-puck/page.tsx`, `AiTextInput` | M1 | DONE |
| M4 | R4 Complex Blocks Catalog | `builder-puck/page.tsx` (`gallery`, `cards` array fields) | M2, M3 | DONE |
| M5 | R5 Auto-save & Save Button | `builder-puck/page.tsx` (debounced `onChange` + header button) | M4 | DONE |
| M6 | R6 E2E Suite & Migration | `builder-puck-flow.spec.ts`, `src/app/plataforma/cms/builder/page.tsx` | M5 | IN_PROGRESS |



## Interface Contracts
### MediaPicker Integration
- Interface: `MediaPickerProps` (`open`, `token`, `selectedUrl`, `onClose`, `onSelect: (item: CmsMediaItem) => void`)
- Signal: `mediaPickerTrigger(onChange: (url: string) => void, currentValue: string)`

### AI Generation Assistant
- Endpoint: `POST /system/ai/generate`
- Request: `{ prompt: string, context?: string }`
- Response: `{ response: string }`

### CMS Section API Persistence
- Batch Section CRUD: `GET/POST/PATCH/DELETE /cms/v2/sites/${siteKey}/pages/${pageSlug}/sections`

## Code Layout
- `src/app/layout.tsx` — Global Next.js layout, font declarations (`Outfit`, `Inter`).
- `tailwind.config.ts` — Tailwind font & color mappings.
- `src/components/cms/builder/MediaPicker.tsx` — Media library selection drawer component.
- `src/app/plataforma/cms/builder-puck/page.tsx` — Complete Puck Editor implementation.
- `src/app/plataforma/cms/builder/page.tsx` — Main CMS builder route (to be updated to export Puck editor).
- `tests/e2e/cms/builder-puck-flow.spec.ts` — Playwright E2E spec for Puck flow verification.
