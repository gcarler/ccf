"""Persistent event communication deliveries and public identity challenges."""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260807_0001_event_followup_identity"
down_revision: Union[str, None] = "20260806_0001_event_contextual_roles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "event_registrations" not in tables or "event_campaigns" not in tables:
        raise RuntimeError("Las tablas de pre-registro deben existir antes de aplicar esta migración")

    campaign_columns = {c["name"] for c in inspector.get_columns("event_campaigns")}
    if "communication_type" not in campaign_columns:
        with op.batch_alter_table("event_campaigns") as batch:
            batch.add_column(sa.Column("communication_type", sa.String(20), nullable=False, server_default="ROUTINE"))

    if "event_communication_deliveries" not in tables:
        op.create_table(
            "event_communication_deliveries",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("registration_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("event_registrations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("event_campaigns.id", ondelete="CASCADE"), nullable=False),
            sa.Column("event_update_id", sa.String(100), nullable=True),
            sa.Column("communication_key", sa.String(180), nullable=False),
            sa.Column("channel", sa.String(20), nullable=False),
            sa.Column("recipient_masked", sa.String(255), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="QUEUED"),
            sa.Column("skip_reason", sa.String(80), nullable=True),
            sa.Column("consent_rule_applied", sa.String(40), nullable=True),
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("provider_message_id", sa.String(180), nullable=True),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("payload_version", sa.String(40), nullable=True),
            sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.UniqueConstraint("registration_id", "campaign_id", "communication_key", name="uq_event_communication_delivery_key"),
        )
        op.create_index("ix_event_delivery_registration", "event_communication_deliveries", ["registration_id"])
        op.create_index("ix_event_delivery_campaign", "event_communication_deliveries", ["campaign_id"])
        op.create_index("ix_event_delivery_status_next_attempt", "event_communication_deliveries", ["status", "next_attempt_at"])
        op.create_index("ix_event_delivery_event_update", "event_communication_deliveries", ["event_update_id"])

    # Prefer explicit communication preferences on the registration snapshot;
    # this preserves the consent decision used for each event.
    registration_columns = {c["name"] for c in sa.inspect(bind).get_columns("event_registrations")}
    with op.batch_alter_table("event_registrations") as batch:
        if "communication_consent" not in registration_columns:
            batch.add_column(sa.Column("communication_consent", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")))
        if "consent_source" not in registration_columns:
            batch.add_column(sa.Column("consent_source", sa.String(40), nullable=True))
        if "consent_at" not in registration_columns:
            batch.add_column(sa.Column("consent_at", sa.DateTime(timezone=True), nullable=True))
        if "consent_policy_version" not in registration_columns:
            batch.add_column(sa.Column("consent_policy_version", sa.String(40), nullable=True))
        if "preferred_channels" not in registration_columns:
            batch.add_column(sa.Column("preferred_channels", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
        if "transactional_notifications_enabled" not in registration_columns:
            batch.add_column(sa.Column("transactional_notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")))
        if "marketing_opt_out_at" not in registration_columns:
            batch.add_column(sa.Column("marketing_opt_out_at", sa.DateTime(timezone=True), nullable=True))

    tables = set(sa.inspect(bind).get_table_names())
    if "event_identity_challenges" not in tables:
        op.create_table(
            "event_identity_challenges",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("crm_events.id", ondelete="CASCADE"), nullable=False),
            sa.Column("identifier_type", sa.String(20), nullable=False),
            sa.Column("identifier_hash", sa.String(128), nullable=False),
            sa.Column("challenge_hash", sa.String(128), nullable=False),
            sa.Column("verified_identity_token_hash", sa.String(128), nullable=True),
            sa.Column("persona_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="SET NULL"), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
        op.create_index("ix_event_identity_challenge_lookup", "event_identity_challenges", ["event_id", "identifier_hash"])
        op.create_index("ix_event_identity_challenge_token", "event_identity_challenges", ["verified_identity_token_hash"])


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "event_campaigns" in tables and "communication_type" in {c["name"] for c in sa.inspect(bind).get_columns("event_campaigns")}:
        with op.batch_alter_table("event_campaigns") as batch:
            batch.drop_column("communication_type")
    if "event_identity_challenges" in tables:
        op.drop_index("ix_event_identity_challenge_token", table_name="event_identity_challenges")
        op.drop_index("ix_event_identity_challenge_lookup", table_name="event_identity_challenges")
        op.drop_table("event_identity_challenges")
    if "event_registrations" in tables:
        columns = {c["name"] for c in sa.inspect(bind).get_columns("event_registrations")}
        with op.batch_alter_table("event_registrations") as batch:
            for column in (
                "marketing_opt_out_at", "transactional_notifications_enabled", "preferred_channels",
                "consent_policy_version", "consent_at", "consent_source", "communication_consent",
            ):
                if column in columns:
                    batch.drop_column(column)
    if "event_communication_deliveries" in tables:
        op.drop_index("ix_event_delivery_event_update", table_name="event_communication_deliveries")
        op.drop_index("ix_event_delivery_status_next_attempt", table_name="event_communication_deliveries")
        op.drop_index("ix_event_delivery_campaign", table_name="event_communication_deliveries")
        op.drop_index("ix_event_delivery_registration", table_name="event_communication_deliveries")
        op.drop_table("event_communication_deliveries")
