"""automation unification

Revision ID: 20260502_0003
Revises: 20260502_0002
Create Date: 2026-05-02 13:00:00
"""

from __future__ import annotations

import json

import sqlalchemy as sa

from alembic import op

revision = "20260502_0003"
down_revision = "20260502_0002"
branch_labels = None
depends_on = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(
        column["name"] == column_name for column in inspector.get_columns(table_name)
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("automation_rules"):
        with op.batch_alter_table("automation_rules") as batch_op:
            if not _has_column(inspector, "automation_rules", "action_type"):
                batch_op.add_column(
                    sa.Column("action_type", sa.String(length=50), nullable=True)
                )
            if not _has_column(inspector, "automation_rules", "action_payload"):
                batch_op.add_column(
                    sa.Column("action_payload", sa.JSON(), nullable=True)
                )

    inspector = sa.inspect(bind)
    if inspector.has_table("crm_automations") and inspector.has_table(
        "automation_rules"
    ):
        rows = bind.execute(
            sa.text(
                "SELECT id, name, trigger_event, action_type, action_payload, is_active "
                "FROM crm_automations"
            )
        ).mappings()
        for row in rows:
            exists = bind.execute(
                sa.text(
                    "SELECT id FROM automation_rules "
                    "WHERE name = :name AND trigger_type = :trigger_type "
                    "AND coalesce(action_type, '') = coalesce(:action_type, '')"
                ),
                {
                    "name": row["name"],
                    "trigger_type": row["trigger_event"],
                    "action_type": row["action_type"],
                },
            ).first()
            if exists:
                continue
            payload_value = row["action_payload"]
            if payload_value is not None and not isinstance(payload_value, str):
                payload_value = json.dumps(payload_value)
            bind.execute(
                sa.text(
                    "INSERT INTO automation_rules "
                    "(name, trigger_type, action_type, action_payload, is_active, last_run, config_json) "
                    "VALUES (:name, :trigger_type, :action_type, :action_payload, :is_active, NULL, :config_json)"
                ),
                {
                    "name": row["name"],
                    "trigger_type": row["trigger_event"],
                    "action_type": row["action_type"],
                    "action_payload": payload_value,
                    "is_active": row["is_active"],
                    "config_json": "{}",
                },
            )
        op.drop_table("crm_automations")

    inspector = sa.inspect(bind)
    if inspector.has_table("automation_rules"):
        existing_indexes = {
            index["name"] for index in inspector.get_indexes("automation_rules")
        }
        if "ix_automation_rules_action_type" not in existing_indexes:
            op.create_index(
                "ix_automation_rules_action_type",
                "automation_rules",
                ["action_type"],
                unique=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("crm_automations"):
        op.create_table(
            "crm_automations",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("trigger_event", sa.String(length=50), nullable=False),
            sa.Column("action_type", sa.String(length=50), nullable=False),
            sa.Column("action_payload", sa.JSON(), nullable=True),
            sa.Column(
                "is_active", sa.Boolean(), nullable=True, server_default=sa.true()
            ),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_crm_automations_id"), "crm_automations", ["id"], unique=False
        )

    inspector = sa.inspect(bind)
    if inspector.has_table("automation_rules") and _has_column(
        inspector, "automation_rules", "action_type"
    ):
        rows = bind.execute(
            sa.text(
                "SELECT id, name, trigger_type, action_type, action_payload, is_active "
                "FROM automation_rules WHERE action_type IS NOT NULL"
            )
        ).mappings()
        for row in rows:
            bind.execute(
                sa.text(
                    "INSERT INTO crm_automations (id, name, trigger_event, action_type, action_payload, is_active, created_at) "
                    "VALUES (:id, :name, :trigger_event, :action_type, :action_payload, :is_active, CURRENT_TIMESTAMP)"
                ),
                {
                    "id": row["id"],
                    "name": row["name"],
                    "trigger_event": row["trigger_type"],
                    "action_type": row["action_type"],
                    "action_payload": row["action_payload"],
                    "is_active": row["is_active"],
                },
            )
        with op.batch_alter_table("automation_rules") as batch_op:
            batch_op.drop_column("action_payload")
            batch_op.drop_column("action_type")
