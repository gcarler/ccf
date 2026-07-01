"""eradicate runtime legacy contracts

Revision ID: 20260701_0002_no_legacy
Revises: 20260701_0001_cms_sede
Create Date: 2026-06-30 19:30:00

This is the breaking cleanup after the v3.0.1 compatibility window:

* CMS user-generated content must have a persona owner and a sede.
* obsolete communication outcome and QR token values are normalized.
* project task labels are always a non-null JSON array.
* the public ``baptism_date`` contract becomes the physical Persona column.
* PostgreSQL objects that still target the retired ``members`` contract are
  removed, and the table itself is dropped only after every row is proven to
  exist in ``personas`` by normalized email.

Rows that cannot be attributed to a persona/sede are deleted deliberately.
Their ownership is unknowable, so retaining or publishing them would violate
tenant isolation.  The data cleanup is intentionally irreversible; downgrade
only restores column nullability for binary rollback.
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260701_0002_no_legacy"
down_revision: str | None = "20260701_0001_cms_sede"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table: str) -> bool:
    return table in set(_inspector().get_table_names())


def _has_column(table: str, column: str) -> bool:
    return _has_table(table) and column in {
        item["name"] for item in _inspector().get_columns(table)
    }


def _set_not_null(table: str, column: str) -> None:
    if not _has_column(table, column):
        return
    existing_type = next(
        item["type"]
        for item in _inspector().get_columns(table)
        if item["name"] == column
    )
    with op.batch_alter_table(table) as batch_op:
        batch_op.alter_column(
            column,
            existing_type=existing_type,
            nullable=False,
        )


def _set_nullable(table: str, column: str) -> None:
    if not _has_column(table, column):
        return
    existing_type = next(
        item["type"]
        for item in _inspector().get_columns(table)
        if item["name"] == column
    )
    with op.batch_alter_table(table) as batch_op:
        batch_op.alter_column(
            column,
            existing_type=existing_type,
            nullable=True,
        )


def _backfill_sede(table: str, persona_column: str) -> None:
    if not all(
        (
            _has_table("personas"),
            _has_column("personas", "sede_id"),
            _has_column(table, "sede_id"),
            _has_column(table, persona_column),
        )
    ):
        return
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        bind.execute(
            sa.text(
                f'UPDATE "{table}" AS target '
                "SET sede_id = persona.sede_id "
                "FROM personas AS persona "
                f'WHERE target."{persona_column}" = persona.id '
                "AND target.sede_id IS NULL "
                "AND persona.sede_id IS NOT NULL"
            )
        )
    else:
        bind.execute(
            sa.text(
                f'UPDATE "{table}" '
                "SET sede_id = (SELECT persona.sede_id FROM personas AS persona "
                f'WHERE CAST(persona.id AS TEXT) = CAST("{table}"."{persona_column}" AS TEXT)) '
                "WHERE sede_id IS NULL"
            )
        )


def _purge_unowned_cms_content() -> None:
    contracts = (
        ("cms_media_items", "created_by_persona_id"),
        ("announcements", "created_by_persona_id"),
        ("testimonials", "author_persona_id"),
    )
    bind = op.get_bind()
    for table, persona_column in contracts:
        if not (_has_column(table, "sede_id") and _has_column(table, persona_column)):
            continue
        _backfill_sede(table, persona_column)
        bind.execute(
            sa.text(
                f'DELETE FROM "{table}" '
                f'WHERE sede_id IS NULL OR "{persona_column}" IS NULL'
            )
        )
        _set_not_null(table, "sede_id")
        _set_not_null(table, persona_column)


def _normalize_runtime_values() -> None:
    bind = op.get_bind()
    if _has_column("communication_logs", "outcome"):
        bind.execute(
            sa.text(
                "UPDATE communication_logs SET outcome = 'sent_real' "
                "WHERE lower(outcome) = 'delivered'"
            )
        )
    if _has_column("personas", "qr_token"):
        if bind.dialect.name == "postgresql":
            bind.execute(
                sa.text(
                    "UPDATE personas "
                    "SET qr_token = upper(substr(md5(id::text || :salt), 1, 16)) "
                    "WHERE qr_token LIKE 'CCF-' || 'MBR-%%'"
                ).bindparams(salt=":persona")
            )
        else:
            bind.execute(
                sa.text(
                    "UPDATE personas SET qr_token = upper(substr(hex(id), 1, 16)) "
                    "WHERE qr_token LIKE 'CCF-' || 'MBR-%%'"
                )
            )
    if _has_column("project_tasks", "labels"):
        if bind.dialect.name == "postgresql":
            bind.execute(
                sa.text(
                    "UPDATE project_tasks SET labels = json_build_array(labels #>> '{}') "
                    "WHERE jsonb_typeof(labels::jsonb) = 'string'"
                )
            )
            bind.execute(
                sa.text("UPDATE project_tasks SET labels = '[]'::json WHERE labels IS NULL")
            )
        else:
            bind.execute(
                sa.text(
                    "UPDATE project_tasks SET labels = json_array(json_extract(labels, '$')) "
                    "WHERE json_type(labels) = 'text'"
                )
            )
            bind.execute(sa.text("UPDATE project_tasks SET labels = '[]' WHERE labels IS NULL"))
        _set_not_null("project_tasks", "labels")
    if _has_column("project_tasks", "priority"):
        bind.execute(
            sa.text(
                "UPDATE project_tasks SET priority = CASE lower(trim(priority)) "
                "WHEN 'baja' THEN 'low' WHEN 'bajo' THEN 'low' "
                "WHEN 'normal' THEN 'medium' "
                "WHEN 'alta' THEN 'high' WHEN 'altas' THEN 'high' "
                "WHEN 'alto' THEN 'high' WHEN 'urgente' THEN 'urgent' "
                "ELSE lower(trim(priority)) END WHERE priority IS NOT NULL"
            )
        )
        bind.execute(
            sa.text("UPDATE project_tasks SET priority = 'medium' WHERE priority IS NULL")
        )
        invalid_priorities = bind.execute(
            sa.text(
                "SELECT count(*) FROM project_tasks "
                "WHERE priority NOT IN ('low', 'medium', 'high', 'urgent')"
            )
        ).scalar_one()
        if invalid_priorities:
            raise RuntimeError(
                f"Cannot normalize project task priority: {invalid_priorities} invalid row(s)"
            )
        _set_not_null("project_tasks", "priority")


def _rename_persona_baptism_date() -> None:
    if not _has_column("personas", "fecha_bautismo"):
        return
    if _has_column("personas", "baptism_date"):
        raise RuntimeError("personas has both fecha_bautismo and baptism_date")
    existing_type = next(
        item["type"]
        for item in _inspector().get_columns("personas")
        if item["name"] == "fecha_bautismo"
    )
    with op.batch_alter_table("personas") as batch_op:
        batch_op.alter_column(
            "fecha_bautismo",
            new_column_name="baptism_date",
            existing_type=existing_type,
        )


def _drop_retired_member_objects() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for function_name in (
        "fn_generate_qr_token",
        "fn_upsert_member",
        "fn_search_members",
        "fn_member_engagement_score",
        "fn_track_member_ministry_changes",
    ):
        bind.execute(sa.text(f"DROP FUNCTION IF EXISTS {function_name} CASCADE"))
    bind.execute(sa.text("DROP MATERIALIZED VIEW IF EXISTS mv_member_engagement CASCADE"))

    if not _has_table("members"):
        return
    if not _has_table("personas"):
        raise RuntimeError("Cannot remove members without canonical personas table")
    unmatched = bind.execute(
        sa.text(
            "SELECT count(*) FROM members AS member "
            "WHERE member.email IS NULL OR NOT EXISTS ("
            "SELECT 1 FROM personas AS persona "
            "WHERE lower(persona.email) = lower(member.email))"
        )
    ).scalar_one()
    if unmatched:
        raise RuntimeError(
            f"Cannot remove members: {unmatched} row(s) are not present in personas"
        )
    bind.execute(sa.text("DROP TABLE members CASCADE"))


def upgrade() -> None:
    _purge_unowned_cms_content()
    _normalize_runtime_values()
    _rename_persona_baptism_date()
    _drop_retired_member_objects()


def downgrade() -> None:
    if _has_column("personas", "baptism_date") and not _has_column(
        "personas", "fecha_bautismo"
    ):
        existing_type = next(
            item["type"]
            for item in _inspector().get_columns("personas")
            if item["name"] == "baptism_date"
        )
        with op.batch_alter_table("personas") as batch_op:
            batch_op.alter_column(
                "baptism_date",
                new_column_name="fecha_bautismo",
                existing_type=existing_type,
            )
    _set_nullable("project_tasks", "labels")
    _set_nullable("project_tasks", "priority")
    for table, persona_column in (
        ("testimonials", "author_persona_id"),
        ("announcements", "created_by_persona_id"),
        ("cms_media_items", "created_by_persona_id"),
    ):
        _set_nullable(table, persona_column)
        _set_nullable(table, "sede_id")
