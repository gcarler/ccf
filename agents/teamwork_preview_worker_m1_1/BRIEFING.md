# BRIEFING — 2026-07-30T23:44:29Z

## Mission
Implement 4 new section types in the CMS Builder and Public Renderer: `animated_counter`, `video_embed`, `gallery_masonry`, `map_embed`.

## 🔒 My Identity
- Archetype: implementer
- Roles: implementer, qa, specialist
- Working directory: /root/ccf/.agents/teamwork_preview_worker_m1_1
- Original parent: 29fb24b8-3c58-4e56-9cb8-c98e4a775f50
- Milestone: Milestone M1 (R1: Bloques nuevos en el Builder)

## 🔒 Key Constraints
- CODE_ONLY network mode: no external HTTP/curl/wget access.
- Minimal change principle: implement exact 4 new section types in constants, public section components, PublicSectionRenderer, and BuilderSectionInspector.
- DO NOT CHEAT: real implementation only, no hardcoded or facade results.
- **Reglas CCF obligatorias**: Leer y aplicar `/root/ccf/AGENTS_RULES_CCF.md` ANTES de implementar. Todo código nuevo debe cumplir: backend (datetime.now(timezone.utc), sede_id kwonly, actor UUID, UUID PKs, soft deletes, HTTPException semánticos), frontend (apiFetch, /plataforma/, drawers NO modals, tokens semánticos hsl(var(--*)), clsx, DS* components), DB (migraciones reversibles, no editar cerradas).
- **Drawers NO modals**: Flujos create/edit/view usan drawers (SidePanel, RightPanel, UniversalCreationDrawer), NO modals/AlertDialog. Excepción: confirmaciones de delete pueden usar AlertDialog.
- **Lint obligatorio**: Ejecutar `cd /root/ccf/frontend && npm run lint -- --max-warnings=0` antes de commit.
- **Venv para pytest**: Ejecutar `cd /root/ccf && ./venv/bin/python -m pytest` (no `python3` directo).
- **Sistema task**: Registrar T1 + sub-tareas en el sistema task ANTES de codear.

## Current Parent
- Conversation ID: 29fb24b8-3c58-4e56-9cb8-c98e4a775f50
- Updated: 2026-07-30T23:44:29Z

## Task Summary
- **What to build**:
  1. Update `SECTION_TYPES`, `SECTION_TYPE_COLORS`, `SECTION_TYPE_LABEL`, and templates in `frontend/src/components/cms/builder/constants.ts`.
  2. Implement 4 section components in `frontend/src/components/public/cms/sections/`: `AnimatedCounterSection.tsx`, `VideoEmbedSection.tsx`, `GalleryMasonrySection.tsx`, `MapEmbedSection.tsx`.
  3. Register 4 components in `frontend/src/components/public/cms/PublicSectionRenderer.tsx`.
  4. Add editor controls for 4 new section types in `frontend/src/components/cms/builder/BuilderSectionInspector.tsx`.
  5. Verify TypeScript compilation (`cd /root/ccf/frontend && npx tsc --noEmit`).
- **Success criteria**: 0 TypeScript compilation errors, full functionality of 4 section types in public renderer and inspector.

## Change Tracker
- **Files modified**: TBD
- **Build status**: TBD
- **Pending issues**: none

## Quality Status
- **Build/test result**: TBD
- **Lint status**: TBD
- **Tests added/modified**: TBD

## Loaded Skills
- **ccf-backend-guard**: Backend safety (FastAPI, SQLAlchemy, sede_id, soft deletes, datetime, UUID).
- **ccf-ui-guard**: Frontend safety (Next.js, apiFetch, /plataforma/, drawers, semantic tokens, DS 3-layer).
- **ccf-architecture-guard**: Cross-layer change planning and rollback safety.
- **ccf-cms-guard**: CMS and public-content safety.

## Key Decisions Made
- TBD

## Artifact Index
- `/root/ccf/.agents/teamwork_preview_worker_m1_1/ORIGINAL_REQUEST.md` — User request copy
- `/root/ccf/.agents/teamwork_preview_worker_m1_1/progress.md` — Liveness heartbeat
- `/root/ccf/.agents/teamwork_preview_worker_m1_1/BRIEFING.md` — Working briefing
- `/root/ccf/.agents/teamwork_preview_worker_m1_1/changes.md` — Detailed changes and verification output
- `/root/ccf/.agents/teamwork_preview_worker_m1_1/handoff.md` — 5-component handoff report
