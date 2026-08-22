## 2026-07-30T19:09:32Z
You are a Worker subagent assigned to implement Milestone 3: R3 Image Editor in Media Library.
Your working directory is: /root/ccf/.agents/worker_m3_image_editor

Detailed Requirements:
1. Frontend Image Editor (`frontend/src/app/plataforma/cms/media/[id]/page.tsx`):
   - When viewing an item whose `mime_type` contains 'image', provide an "Editar imagen" button/panel.
   - Implement a full-screen modal/dialog with the image rendered on an HTML5 `<canvas>` in the center and editing controls in the right sidebar.
   - Editing controls (built using native Web API Canvas without external image editing libraries):
     - **Recorte (Crop)**: interactive selection overlay with handle points. Crop preview box and "Aplicar recorte" button.
     - **Rotación**: -90° and +90° buttons with real-time canvas transformation.
     - **Brillo/Contraste**: Range sliders from -100 to +100 with real-time canvas filter / CSS preview.
     - **Voltear (Flip)**: Horizontal and Vertical flip buttons.
     - **Guardar cambios**: Converts the edited canvas to Blob and posts to `POST /cms/media/{id}/edit` (or `/api/cms/v2/sites/{site_key}/media/{id}/edit` / `/api/cms/media/{id}/edit`) using `FormData` with field `file`.
   - **Non-destructive**: Ensures the backend saves a new copy of the image with `_edited` suffix added to filename rather than overwriting original.

2. Backend Endpoint:
   - Implement `POST /cms/media/{id}/edit` (or `/api/cms/v2/sites/{site_key}/media/{id}/edit` / `/api/cms/media/{id}/edit` / `/api/cms/v2/media/{id}/edit` as appropriate) in backend media router (`backend/api/cms_v2/media.py` or `backend/api/cms.py`).
   - Receives uploaded file blob, generates filename with `_edited` suffix, creates new database record in `CmsMediaItem` or uploads file to media storage, and returns the new media item.

3. Testing & Typecheck:
   - Run `cd /root/ccf/frontend && npm run typecheck` to ensure 0 TypeScript errors.
   - Write pytest test in backend for media edit endpoint and vitest test in frontend for image editor page.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Upon completion, write a detailed handoff report to `/root/ccf/.agents/worker_m3_image_editor/handoff.md`.
