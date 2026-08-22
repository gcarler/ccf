# BRIEFING — 2026-07-30T19:03:50Z

## Mission
Implement Milestone 1: R1 Contact Forms Module (Backend models, API endpoints, Alembic migration, Frontend forms page, navigation update, unit/integration tests, and typecheck verification).

## 🔒 My Identity
- Archetype: implementer/qa/specialist
- Roles: implementer, qa, specialist
- Working directory: /root/ccf/.agents/worker_m1_forms_module
- Original parent: 92b36264-1865-4585-935d-cbe1d12688ec
- Milestone: Milestone 1 - R1 Contact Forms Module

## 🔒 Key Constraints
- CODE_ONLY network mode.
- Do not cheat; genuine implementation required.
- Minimal change principle.
- Absolute paths for tool calls.
- Self-contained handoff report at `/root/ccf/.agents/worker_m1_forms_module/handoff.md`.
- **Reglas CCF obligatorias**: Leer y aplicar `/root/ccf/AGENTS_RULES_CCF.md` ANTES de implementar. Todo código nuevo debe cumplir: backend (datetime.now(timezone.utc), sede_id kwonly, actor UUID, UUID PKs, soft deletes, HTTPException semánticos), frontend (apiFetch, /plataforma/, drawers NO modals, tokens semánticos hsl(var(--*)), clsx, DS* components), DB (migraciones reversibles, no editar cerradas).
- **Drawers NO modals**: Flujos create/edit/view usan drawers (SidePanel, RightPanel, UniversalCreationDrawer), NO modals/AlertDialog. Excepción: confirmaciones de delete pueden usar AlertDialog.
- **Lint obligatorio**: Ejecutar `cd /root/ccf/frontend && npm run lint -- --max-warnings=0` antes de commit.
- **Venv para pytest**: Ejecutar `cd /root/ccf && ./venv/bin/python -m pytest` (no `python3` directo).
- **Sistema task**: Registrar T1 + sub-tareas en el sistema task ANTES de codear.

## Current Parent
- Conversation ID: 92b36264-1865-4585-935d-cbe1d12688ec
- Updated: 2026-07-30T19:03:50Z

## Task Summary
- **What to build**: 
  1. Backend Models in `backend/models_cms.py` (`CmsForm`, `CmsFormSubmission`).
  2. Backend Endpoints in `backend/api/cms_v2/forms.py` and router registration in `backend/api/cms_v2/__init__.py`.
  3. Alembic migration script in `alembic/canonical_versions/20260730_0005_add_cms_forms.py`.
  4. Frontend Page in `frontend/src/app/plataforma/cms/forms/page.tsx` with Form builder, tabs ("Formularios" & "Respuestas"), skeletons, empty states, modals.
  5. Navigation update in `frontend/src/components/cms/CmsModuleNav.tsx`.
  6. Backend (`tests/test_cms_v2_forms.py`) and frontend (`frontend/src/app/plataforma/cms/forms/page.test.tsx`) tests.
  7. Frontend typecheck (`npm run typecheck` / `npx tsc --noEmit`).

## Change Tracker
- **Files modified**:
  - `backend/models_cms.py`: Updated `CmsForm.success_message` default to "¡Gracias por tu mensaje!".
  - `backend/schemas/cms.py`: Updated default `success_message` to "¡Gracias por tu mensaje!".
  - `alembic/canonical_versions/20260730_0005_add_cms_forms.py`: Updated default `success_message` to "¡Gracias por tu mensaje!".
  - `backend/api/cms_v2/forms.py`: Added `@router.patch` decorator alongside `@router.put`.
  - `frontend/src/lib/cms/v2.ts`: Exported `patchCmsForm`.
  - `frontend/src/app/plataforma/cms/forms/page.tsx`: Implemented complete CMS Forms page with tabs ("Formularios", "Respuestas"), drawer, builder, chips, skeletons, empty states, delete modal.
  - `tests/test_cms_v2_forms.py`: Created backend pytest suite (9 tests passing).
  - `frontend/src/app/plataforma/cms/forms/page.test.tsx`: Created frontend vitest suite (2 tests passing).
- **Build status**: PASSING
- **Pending issues**: None

## Quality Status
- **Build/test result**: 9/9 pytest passed, 2/2 vitest passed, 0 TypeScript errors.
- **Lint status**: Clean.
- **Tests added/modified**: `tests/test_cms_v2_forms.py`, `frontend/src/app/plataforma/cms/forms/page.test.tsx`.

## Loaded Skills
- **ccf-backend-guard**: Backend safety (FastAPI, SQLAlchemy, sede_id, soft deletes, datetime, UUID).
- **ccf-ui-guard**: Frontend safety (Next.js, apiFetch, /plataforma/, drawers, semantic tokens, DS 3-layer).
- **ccf-architecture-guard**: Cross-layer change planning and rollback safety.
- **ccf-cms-guard**: CMS and public-content safety.
