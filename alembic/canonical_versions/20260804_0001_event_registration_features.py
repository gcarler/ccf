"""Add event pre-registration features (CrmEvent columns + event_registrations + event_campaigns).

Revision ID: 20260804_0001_event_registration_features
Revises: 20260803_0005_academy_normalize_privado_to_persona
Create Date: 2026-08-04

Contexto
========

Plan: ``docs/PLAN_PREREGISTRO_EVENTOS_MASIVOS.md`` (plan_de_preregistro).

Habilita el flujo de pre-inscripción a eventos masivos (conciertos,
conferencias, eventos con boleta) con QR por inscrito, verificación de email
opcional, aforo + lista de espera, y campaña de mensajería ligada al evento.

Compatibilidad (REGLAS.md §9): backward-compatible.
    - Todas las columnas nuevas en ``crm_events`` declaran un ``server_default``
      FALSE / NULL / ``'PER_REGISTRANT'`` / ``'{}'``, de modo que los eventos
      existentes siguen funcionando como hoy: ``requires_registration=False``
      significa "evento abierto sin pre-inscripción", idéntico al flujo
      legacy (``/public/register`` y ``events_checkin.fast_checkin_visitor``).
    - Las tablas hijas (``event_registrations``, ``event_campaigns``) son
      puramente aditivas: si el flag no está activado, ningún endpoint las
      consulta.

Tablas
------
    crm_events:
        + requires_registration        BOOLEAN  NOT NULL DEFAULT FALSE
        + requires_email_verification  BOOLEAN  NOT NULL DEFAULT FALSE
        + registration_opens_at        TIMESTAMPTZ NULL
        + registration_closes_at       TIMESTAMPTZ NULL
        + capacity_max                 INTEGER  NULL
        + waiting_list_enabled         BOOLEAN  NOT NULL DEFAULT FALSE
        + qr_mode                      VARCHAR(20) NOT NULL DEFAULT 'PER_REGISTRANT'
        + contact_person               VARCHAR(255) NULL
        + settings_json                JSON     NOT NULL DEFAULT '{}'

    event_registrations (NEW):
        Ciclo de vida de pre-inscripción PENDING → CONFIRMED → CHECKED_IN |
        ABSENT | CANCELLED, con QR opcional y tracking de reminders.

    event_campaigns (NEW):
        Campaña de mensajería ligada a un evento, con plantilla CRM
        (PlantillaMensaje), canal (WHATSAPP/EMAIL/SMS), trigger
        (MANUAL/RELATIVE_TO_EVENT/RELATIVE_TO_REGISTRATION) y audiencia
        por estado de inscripción (target_status JSON).

Axioma 3 (Multi-Tenant — REGLAS.md §4): las nuevas tablas no añaden
``sede_id`` propio — el scope por sede se hereda vía JOIN:
    event_registrations.event_id → crm_events.sede_id
    event_campaigns.event_id    → crm_events.sede_id
El contrato del API exige filtrar por la sede del actor en toda
lectura/escritura, reusando el helper ``require_event_access`` de
``backend/api/evangelism_events/_shared.py``.

Idempotencia
------------
La migración valida antes de alterar/crear (``_has_column`` /
``_has_table`` / ``_has_index``) para ser segura frente a entornos que ya
la hayan aplicado manualmente — no falla si la columna o tabla ya existen.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260804_0001_event_registration_features"
down_revision: Union[str, None] = "20260803_0005_academy_normalize_privado_to_persona"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table: str) -> bool:
    return table in set(_inspector().get_table_names())


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return any(col.get("name") == column for col in _inspector().get_columns(table))


def _has_index(table: str, index_name: str) -> bool:
    if not _has_table(table):
        return False
    return any(idx.get("name") == index_name for idx in _inspector().get_indexes(table))


# ─────────────────────────────────────────────────────────────────────────────
# UPGRADE
# ─────────────────────────────────────────────────────────────────────────────


def upgrade() -> None:
    _upgrade_crm_events_columns()
    _upgrade_create_event_registrations()
    _upgrade_create_event_campaigns()


def _upgrade_crm_events_columns() -> None:
    if not _has_table("crm_events"):
        return

    columns_to_add = [
        ("requires_registration", sa.Column("requires_registration", sa.Boolean(), nullable=False, server_default=sa.text("FALSE"))),
        ("requires_email_verification", sa.Column("requires_email_verification", sa.Boolean(), nullable=False, server_default=sa.text("FALSE"))),
        ("registration_opens_at", sa.Column("registration_opens_at", sa.DateTime(timezone=True), nullable=True)),
        ("registration_closes_at", sa.Column("registration_closes_at", sa.DateTime(timezone=True), nullable=True)),
        ("capacity_max", sa.Column("capacity_max", sa.Integer(), nullable=True)),
        ("waiting_list_enabled", sa.Column("waiting_list_enabled", sa.Boolean(), nullable=False, server_default=sa.text("FALSE"))),
        ("qr_mode", sa.Column("qr_mode", sa.String(20), nullable=False, server_default=sa.text("'PER_REGISTRANT'"))),
        ("contact_person", sa.Column("contact_person", sa.String(255), nullable=True)),
        ("settings_json", sa.Column("settings_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'"))),
    ]
    with op.batch_alter_table("crm_events", schema=None) as batch_op:
        for name, col in columns_to_add:
            if not _has_column("crm_events", name):
                batch_op.add_column(col)


def _upgrade_create_event_registrations() -> None:
    if _has_table("event_registrations"):
        return

    op.create_table(
        "event_registrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("crm_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("persona_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("registration_status", sa.String(20), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("qr_token", sa.String(128), nullable=True),
        sa.Column("qr_token_hash", sa.String(128), nullable=True),
        sa.Column("qr_generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("check_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("check_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checked_in_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source", sa.String(30), nullable=False, server_default=sa.text("'public_form'")),
        sa.Column("extras", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("waiting_list_position", sa.Integer(), nullable=True),
        sa.Column("reminder_sent_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("event_id", "persona_id", name="uq_event_reg_persona"),
    )
    if not _has_index("event_registrations", "ix_reg_event_status"):
        op.create_index("ix_reg_event_status", "event_registrations", ["event_id", "registration_status"], unique=False)
    if not _has_index("event_registrations", "ix_reg_qr"):
        op.create_index("ix_reg_qr", "event_registrations", ["qr_token_hash"], unique=False)
    if not _has_index("event_registrations", "ix_reg_deleted_at"):
        op.create_index("ix_reg_deleted_at", "event_registrations", ["deleted_at"], unique=False)
    if not _has_index("event_registrations", "uq_event_reg_qr_token"):
        op.create_index(
            "uq_event_reg_qr_token",
            "event_registrations",
            ["qr_token"],
            unique=True,
        )


def _upgrade_create_event_campaigns() -> None:
    if _has_table("event_campaigns"):
        return

    op.create_table(
        "event_campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("crm_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("plantilla_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("crm_plantillas_mensaje.id", ondelete="SET NULL"), nullable=True),
        sa.Column("canal", sa.String(20), nullable=False, server_default=sa.text("'EMAIL'")),
        sa.Column("trigger_type", sa.String(50), nullable=False, server_default=sa.text("'MANUAL'")),
        sa.Column("trigger_offset_minutes", sa.Integer(), nullable=True),
        sa.Column("target_status", sa.JSON(), nullable=False, server_default=sa.text("'[\"CONFIRMED\"]'")),
        sa.Column("sent_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    if not _has_index("event_campaigns", "ix_campaign_event"):
        op.create_index("ix_campaign_event", "event_campaigns", ["event_id"], unique=False)
    if not _has_index("event_campaigns", "ix_campaign_active"):
        op.create_index("ix_campaign_active", "event_campaigns", ["is_active"], unique=False)
    if not _has_index("event_campaigns", "ix_campaign_deleted_at"):
        op.create_index("ix_campaign_deleted_at", "event_campaigns", ["deleted_at"], unique=False)


# ─────────────────────────────────────────────────────────────────────────────
# DOWNGRADE
# ─────────────────────────────────────────────────────────────────────────────


def downgrade() -> None:
    _downgrade_drop_event_campaigns()
    _downgrade_drop_event_registrations()
    _downgrade_crm_events_columns()


def _downgrade_drop_event_campaigns() -> None:
    if not _has_table("event_campaigns"):
        return
    if _has_index("event_campaigns", "ix_campaign_deleted_at"):
        op.drop_index("ix_campaign_deleted_at", table_name="event_campaigns")
    if _has_index("event_campaigns", "ix_campaign_active"):
        op.drop_index("ix_campaign_active", table_name="event_campaigns")
    if _has_index("event_campaigns", "ix_campaign_event"):
        op.drop_index("ix_campaign_event", table_name="event_campaigns")
    op.drop_table("event_campaigns")


def _downgrade_drop_event_registrations() -> None:
    if not _has_table("event_registrations"):
        return
    if _has_index("event_registrations", "uq_event_reg_qr_token"):
        op.drop_index("uq_event_reg_qr_token", table_name="event_registrations")
    if _has_index("event_registrations", "ix_reg_deleted_at"):
        op.drop_index("ix_reg_deleted_at", table_name="event_registrations")
    if _has_index("event_registrations", "ix_reg_qr"):
        op.drop_index("ix_reg_qr", table_name="event_registrations")
    if _has_index("event_registrations", "ix_reg_event_status"):
        op.drop_index("ix_reg_event_status", table_name="event_registrations")
    op.drop_table("event_registrations")


def _downgrade_crm_events_columns() -> None:
    if not _has_table("crm_events"):
        return
    columns_to_drop = [
        "settings_json",
        "contact_person",
        "qr_mode",
        "waiting_list_enabled",
        "capacity_max",
        "registration_closes_at",
        "registration_opens_at",
        "requires_email_verification",
        "requires_registration",
    ]
    with op.batch_alter_table("crm_events", schema=None) as batch_op:
        for name in columns_to_drop:
            if _has_column("crm_events", name):
                batch_op.drop_column(name)
