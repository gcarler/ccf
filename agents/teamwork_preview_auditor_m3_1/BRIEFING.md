# BRIEFING — 2026-07-31T00:05:03Z

## Mission
Conduct an independent forensic integrity audit of Milestone M3 (Section A/B Testing).

## 🔒 My Identity
- Archetype: forensic_auditor
- Roles: critic, specialist, auditor
- Working directory: /root/ccf/.agents/teamwork_preview_auditor_m3_1/
- Original parent: 29fb24b8-3c58-4e56-9cb8-c98e4a775f50
- Target: Milestone M3 (R3: Section A/B Testing)

## 🔒 Key Constraints
- Audit-only — do NOT modify implementation code
- Trust NOTHING — verify everything independently
- Check pytest, tsc, genuine implementation, statistical z-test / erf, Alembic guards & _uuid_type()
- **Reglas CCF obligatorias**: Leer y aplicar `/root/ccf/AGENTS_RULES_CCF.md`. Verificar TODO el checklist de la sección 6, no solo grep de features.
- **Lint obligatorio**: Ejecutar `cd /root/ccf/frontend && npm run lint -- --max-warnings=0` además de typecheck. Es criterio transversal CCF.
- **Venv para pytest**: Ejecutar `cd /root/ccf && ./venv/bin/python -m pytest` (no `python3` directo).

## Current Parent
- Conversation ID: 29fb24b8-3c58-4e56-9cb8-c98e4a775f50
- Updated: 2026-07-31T00:05:03Z

## Audit Scope
- Work product: Milestone M3 files
- Profile loaded: General Project
- Audit type: forensic integrity check

## Audit Progress
- Phase: investigating
- Checks completed: none
- Checks remaining: pytest, tsc, genuine implementation, z-test / erf logic, alembic migration guards
- Findings so far: TBD

## Key Decisions Made
- Initiated audit workflow

## Loaded Skills
- **ccf-backend-guard**: Backend safety (FastAPI, SQLAlchemy, sede_id, soft deletes, datetime, UUID).
- **ccf-ui-guard**: Frontend safety (Next.js, apiFetch, /plataforma/, drawers, semantic tokens, DS 3-layer).
- **ccf-architecture-guard**: Cross-layer change planning and rollback safety.
- **ccf-cms-guard**: CMS and public-content safety.

## Artifact Index
- ORIGINAL_REQUEST.md — Original task prompt
