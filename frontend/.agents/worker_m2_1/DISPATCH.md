## 2026-07-31T20:51:20Z

You are Worker 1 for Milestone 2 (M2: R2 MediaPicker Integration).
Your working directory is: /root/ccf/frontend/.agents/worker_m2_1
Your identity is: worker_m2_1

Read the following context files before starting work:
1. /root/ccf/frontend/.agents/ORIGINAL_REQUEST.md
2. /root/ccf/frontend/.agents/orchestrator/PROJECT.md
3. /root/ccf/frontend/.agents/explorer_m2_1/handoff.md
4. /root/ccf/frontend/.agents/explorer_m2_2/handoff.md
5. /root/ccf/frontend/.agents/explorer_m2_3/handoff.md

Your task:
Implement and refine the `MediaPicker` integration in Puck custom field renderers in `src/app/plataforma/cms/builder-puck/page.tsx` (and `MediaPicker.tsx` if needed).
1. Connect `MediaPicker` drawer for all image fields in Puck block schemas:
   - Hero `bg_image`
   - Cards `items[].image_url`
   - Gallery `items[].url`
2. Create/refine a clean `MediaPickerField` custom field component in `builder-puck/page.tsx` featuring:
   - "Seleccionar Imagen" / "Cambiar Imagen" button calling `mediaPickerTrigger`
   - Image preview thumbnail when an image URL is present
   - "Quitar" (clear) button to reset image URL to empty string `""`
3. Ensure the `MediaPicker` drawer mounts, fetches authenticated media items via `token`, uploads images to SeaweedFS (`/cms/media/upload`), highlights selected items, closes on selection/cancel, and updates Puck block state via `onChange(url)`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Verification steps required before submitting handoff:
- Run `npm run typecheck` (must pass with 0 compilation errors)
- Run `npm run lint` (must pass with 0 errors)
- Run `npx vitest run src/components/cms/builder/MediaPicker.test.tsx` (must pass)

Deliver a handoff report at `/root/ccf/frontend/.agents/worker_m2_1/handoff.md` detailing all files modified, logic implemented, build/test outputs, and verification status. Update progress.md regularly. Send a message to parent when complete.
