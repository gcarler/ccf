# BRIEFING — 2026-07-30T19:14:30Z

## Mission
Implement Milestone 3: R3 Image Editor in Media Library (frontend HTML5 canvas image editor modal + non-destructive backend edit endpoint + vitest/pytest tests).

## 🔒 My Identity
- Archetype: implementer/qa/specialist
- Roles: implementer, qa, specialist
- Working directory: /root/ccf/.agents/worker_m3_image_editor
- Original parent: 92b36264-1865-4585-935d-cbe1d12688ec
- Milestone: Milestone 3 - R3 Image Editor in Media Library

## 🔒 Key Constraints
- CODE_ONLY network mode: No external internet access.
- Minimal change principle: follow existing code patterns and styles.
- Non-destructive image edit: save copy with `_edited` suffix.
- 0 TypeScript errors on `npm run typecheck`.
- Genuine tests and implementation (no hardcoding, facade, or dummy outputs).
- **Reglas CCF obligatorias**: Leer y aplicar `/root/ccf/AGENTS_RULES_CCF.md` ANTES de implementar. Todo código nuevo debe cumplir: backend (datetime.now(timezone.utc), sede_id kwonly, actor UUID, UUID PKs, soft deletes, HTTPException semánticos), frontend (apiFetch, /plataforma/, drawers NO modals, tokens semánticos hsl(var(--*)), clsx, DS* components), DB (migraciones reversibles, no editar cerradas).
- **Drawers NO modals**: Flujos create/edit/view usan drawers (SidePanel, RightPanel, UniversalCreationDrawer), NO modals/AlertDialog. Excepción: confirmaciones de delete pueden usar AlertDialog.
- **Lint obligatorio**: Ejecutar `cd /root/ccf/frontend && npm run lint -- --max-warnings=0` antes de commit.
- **Venv para pytest**: Ejecutar `cd /root/ccf && ./venv/bin/python -m pytest` (no `python3` directo).
- **Sistema task**: Registrar T1 + sub-tareas en el sistema task ANTES de codear.

## Current Parent
- Conversation ID: 92b36264-1865-4585-935d-cbe1d12688ec
- Updated: 2026-07-30T19:14:30Z

## Task Summary
- **What to build**:
  1. Frontend image editor modal `CmsImageEditorModal` integrated in `frontend/src/app/plataforma/cms/media/[id]/page.tsx` with HTML5 `<canvas>` and native Web API editing controls (Crop with handle overlay, Rotation ±90°, Brightness/Contrast sliders, Flip H/V, Save changes).
  2. Backend non-destructive edit endpoint `POST /cms/media/{id}/edit` in `backend/api/cms.py` saving a new `CmsMediaItem` record/file with `_edited` suffix.
  3. Pytest backend test `tests/test_cms_media_editor.py` & Vitest frontend test `src/app/plataforma/cms/media/__tests__/CmsImageEditorModal.test.tsx`.
- **Success criteria**:
  - `npm run typecheck` passes with 0 errors.
  - Vitest test passes (3/3 tests passed).
  - Pytest test passes (2/2 tests passed).
  - Image editing modal works as described.

## Change Tracker
- **Files modified**:
  - `backend/api/cms.py`: added `POST /cms/media/{item_id}/edit` endpoint.
  - `tests/test_cms_media_editor.py`: added backend pytest tests for image editing endpoint.
  - `frontend/src/components/cms/CmsImageEditorModal.tsx`: created full-screen HTML5 canvas image editor modal.
  - `frontend/src/app/plataforma/cms/media/[id]/page.tsx`: added "Editar imagen" buttons and modal integration.
  - `frontend/src/app/plataforma/cms/media/__tests__/CmsImageEditorModal.test.tsx`: created frontend vitest unit tests.
- **Build status**: PASS
- **Pending issues**: None

## Quality Status
- **Build/test result**: All tests passed (pytest 2/2, vitest 3/3, typecheck 0 errors)
- **Lint status**: Clean
- **Tests added/modified**: 2 backend pytest tests, 3 frontend vitest tests

## Loaded Skills
- **ccf-backend-guard**: Backend safety (FastAPI, SQLAlchemy, sede_id, soft deletes, datetime, UUID).
- **ccf-ui-guard**: Frontend safety (Next.js, apiFetch, /plataforma/, drawers, semantic tokens, DS 3-layer).
- **ccf-architecture-guard**: Cross-layer change planning and rollback safety.
- **ccf-cms-guard**: CMS and public-content safety.
