# Plan: Puck Editor Visual Integration & Migration (R1-R6)

## Overview
This plan orchestrates the full Puck editor integration into `/root/ccf/frontend`, implementing R1-R5 features, building Playwright E2E tests, and migrating `/plataforma/cms/builder` to Puck (R6).

## Milestones & Strategy
1. **Phase 0: Survey & Codebase Investigation**
   - Spawn 3 parallel Explorers (`teamwork_preview_explorer`) to inspect existing Puck configuration, MediaPicker, AI generation endpoints, existing builder routes, and Playwright test setup.
   - Build `PROJECT.md` Feature Inventory & Architecture.

2. **Milestone 1 (M1): Theme and CSS Style Synchronization (R1)**
   - Disable Puck iframe isolation (`iframe={{ enabled: false }}`).
   - Pass site theme variables (`--site-*`) and typography (`Outfit`, `Inter`) to Puck canvas.

3. **Milestone 2 (M2): MediaPicker Integration (R2)**
   - Integrate `MediaPicker` component into Puck fields: Hero (`bg_image`), Cards (`image_url`), Gallery (`url`).
   - Drawer selection updates field value with SeaweedFS image URL.

4. **Milestone 3 (M3): AI Writing Assistant Integration (R3)**
   - Integrate `AiTextInput` on Puck inputs/textareas (Hero title/body, Rich Text, CTA Banner).
   - Hook to `/system/ai/generate` endpoint for text generation.

5. **Milestone 4 (M4): Complex Blocks Catalog (R4)**
   - Register `gallery` and `cards` blocks with array fields (dynamic add, reorder, delete sub-elements).

6. **Milestone 5 (M5): Auto-Save & Manual Save Button (R5)**
   - Debounced auto-save (2-5s) in background.
   - Header manual Publish/Save button for synchronous immediate DB sync.

7. **Milestone 6 (M6): Playwright E2E Test Suite & Route Migration (R6)**
   - Create E2E test `tests/e2e/cms/builder-puck-flow.spec.ts`.
   - Replace `/plataforma/cms/builder/page.tsx` with Puck editor.
   - Verify `npm run typecheck`, `npm run lint`, and E2E test pass in green.

8. **Final Victory Audit & Handover**
   - Perform full verification and report completion to Sentinel.
