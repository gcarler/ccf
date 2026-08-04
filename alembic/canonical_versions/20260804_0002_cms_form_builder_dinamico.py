"""CmsForm builder dinámico + vinculación con CrmEvent.form_id (plan_de_form_builder).

Revision ID: 20260804_0002_cms_form_builder_dinamico
Revises: 20260804_0001_event_registration_features
Create Date: 2026-08-04

Contexto
========
Plan: ``docs/PLAN_FORM_BUILDER_DINAMICO.md``.

Habilita el render dinámico de ``CmsForm`` en el sitio público y la
preinscripción de eventos, ampliando el contrato del JSON ``fields`` de
``cms_forms`` con tipos avanzados, validación custom y lógica condicional, más
soporte de captcha (hCaptcha) y honeypot, y un FK opcional de
``crm_events.form_id`` a ``cms_forms.id`` para que cada evento pueda pedir
campos distintos sin tocar código.

Compatibilidad (REGLAS.md §9): backward-compatible.
    - Las columnas nuevas declaran un ``server_default`` FALSE / NULL / ``'{}'``
      de modo que los formularios y eventos existentes siguen funcionando.
    - El JSON ``fields`` de ``cms_forms`` no se altera — el nuevo contrato
      ``CmsFormFieldSpec`` (validado en el backend) es un superset del schema
      viejo (6 tipos básicos), por lo que los registros existentes siguen
      siendo válidos.
    - ``crm_events.form_id`` es NULL por defecto: si no está seteado, la
      preinscripción usa el form fijo actual (regresión: ningún cambio visible).

Columnas
--------
    crm_events:
        + form_id     UUID  NULL  REFERENCES cms_forms(id) ON DELETE SET NULL

    cms_forms:
        + settings_json        JSON     NOT NULL DEFAULT '{}'
        + captcha_enabled       BOOLEAN  NOT NULL DEFAULT FALSE
        + captcha_provider     VARCHAR(20) NOT NULL DEFAULT 'hcaptcha'
        + honeypot_enabled     BOOLEAN  NOT NULL DEFAULT TRUE

Axioma 3 (Multi-Tenant — REGLAS.md §4): ``crm_events.form_id`` apunta a un
``CmsForm`` del mismo site del evento. El contrato del API valida la
pertenencia (mismo ``site_id``) al vincular — no se añade ``site_id`` a
``cms_forms`` (ya existe) ni se relaja el scope.

Idempotencia
------------
La migración valida antes de alterar (``_has_column``) para ser segura frente
a entornos que ya la hayan aplicado manualmente.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260804_0002_cms_form_builder_dinamico"
down_revision: Union[str, None] = "20260804_0001_event_registration_features"
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


# ─────────────────────────────────────────────────────────────────────────────
# UPGRADE
# ─────────────────────────────────────────────────────────────────────────────


def upgrade() -> None:
    _upgrade_crm_events_form_id()
    _upgrade_cms_forms_columns()


def _upgrade_crm_events_form_id() -> None:
    if not _has_table("crm_events"):
        return
    if not _has_column("crm_events", "form_id"):
        with op.batch_alter_table("crm_events", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "form_id",
                    postgresql.UUID(as_uuid=True),
                    sa.ForeignKey("cms_forms.id", ondelete="SET NULL"),
                    nullable=True,
                )
            )


def _upgrade_cms_forms_columns() -> None:
    if not _has_table("cms_forms"):
        return
    columns_to_add = [
        ("settings_json", sa.Column("settings_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'"))),
        ("captcha_enabled", sa.Column("captcha_enabled", sa.Boolean(), nullable=False, server_default=sa.text("FALSE"))),
        ("captcha_provider", sa.Column("captcha_provider", sa.String(20), nullable=False, server_default=sa.text("'hcaptcha'"))),
        ("honeypot_enabled", sa.Column("honeypot_enabled", sa.Boolean(), nullable=False, server_default=sa.text("TRUE"))),
    ]
    with op.batch_alter_table("cms_forms", schema=None) as batch_op:
        for name, col in columns_to_add:
            if not _has_column("cms_forms", name):
                batch_op.add_column(col)


# ─────────────────────────────────────────────────────────────────────────────
# DOWNGRADE
# ─────────────────────────────────────────────────────────────────────────────


def downgrade() -> None:
    _downgrade_cms_forms_columns()
    _downgrade_crm_events_form_id()


def _downgrade_cms_forms_columns() -> None:
    if not _has_table("cms_forms"):
        return
    with op.batch_alter_table("cms_forms", schema=None) as batch_op:
        for name in ("honeypot_enabled", "captcha_provider", "captcha_enabled", "settings_json"):
            if _has_column("cms_forms", name):
                batch_op.drop_column(name)


def _downgrade_crm_events_form_id() -> None:
    if not _has_table("crm_events"):
        return
    if _has_column("crm_events", "form_id"):
        with op.batch_alter_table("crm_events", schema=None) as batch_op:
            batch_op.drop_column("form_id")
