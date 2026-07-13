# Backend Audit 2026-07-13

## Scope

- Live PostgreSQL schema vs SQLAlchemy models.
- Active Alembic chain under `alembic/canonical_versions`.
- High-risk backend patterns related to serialization, weak API contracts and hard deletes.
- Focused regressions for projects, CRM resources and evangelism habilitation.

## Repairs Applied

- Added active canonical migration `20260713_0001_backend_schema_drift_repair`.
- Repaired blocking schema drift:
  - `crm_plantillas_mensaje.contenido_html`
  - `sesiones_grupo` report/novelty columns
  - `crm_casos` drag/reorder columns
  - `crm_automation_edges` node/cascade columns
  - `event_assignments.deleted_at`
  - `persona_church_roles.assigned_by_persona_id`
  - `project_whiteboards.deleted_at`
  - `public_contact_submissions`
- Added `scripts/audit_backend_schema.py` as a repeatable read-only drift check.
- Added `scripts/audit_backend_risk_patterns.py` as a repeatable read-only risk-pattern inventory.

## Current Schema Status

`schema_audit_2026-07-13_after_repair.json` reports:

- `missing_tables`: none.
- `blocking_table_diffs`: none.
- Remaining non-blocking extras:
  - extra live tables: `content_metrics`, `content_publications`, `media_assets`, `page_content_versions`, `page_contents`
  - extra live columns: `persona_ministries.created_at`, `sedes.created_at`, `sedes.updated_at`

These extras were not dropped because they may be historical production data.

## Risk Pattern Inventory

`risk_patterns_2026-07-13.json` reports:

- `response_model=dict`: 135
- `hard_delete`: 80
- `orm_all_return`: 6
- `raw_model_dict_mutation`: 4
- `schema_list_any`: 1
- `users_fk`: 0

The broad `response_model=dict` and hard-delete findings require module-by-module cleanup, not a single global refactor.

## Validation

- `python3 -m py_compile scripts/audit_backend_schema.py alembic/canonical_versions/20260713_0001_backend_schema_drift_repair.py`
- `python3 -m py_compile scripts/audit_backend_risk_patterns.py`
- `ENV_FILE=backend/.env alembic current` -> `20260713_0001 (head)`
- `ENV_FILE=backend/.env python scripts/audit_backend_schema.py` -> exit 0
- ORM probe:
  - `PlantillaMensaje` query OK with `contenido_html` mapped.
  - `ProjectAttachment` query OK.
- `pytest tests/test_projects_api.py -q --no-cov` -> 83 passed.
- `pytest tests/test_evangelism_habilitacion_regression.py tests/test_evangelism_crm_bridge.py -q --no-cov` -> 24 passed.
- `pytest tests/test_crm_resource_bank.py tests/test_crm_visual_adversarial.py::test_cross_sede_template_access_isolation_breach tests/test_crm_visual_stress.py::test_cross_sede_template_deletion -q --no-cov` -> 12 passed.
- `pytest tests/test_pastoral_coverage.py::TestAllOtherEndpoints::test_resources_plantillas tests/test_pastoral_deep.py::TestCRMResources::test_list_plantillas -q --no-cov` -> 2 passed.

## Operational Notes

- PM2 backend process is online.
- Recent logged 500s for projects and CRM plantillas are timestamped before the backend restart at `2026-07-13 09:07 UTC`.
- The `ccf-logo-small.png` 404 remains a CMS/static asset routing issue, separate from backend DB/schema drift.
