"""0034_kernel_identity_protocol

Revision ID: 20260526_0034_kernel_identity
Revises: 20260525_0035
Create Date: 2026-05-26

Kernel CCF — Protocolo de Identidad y Roles (3 dimensiones + estado vital).

Tablas nuevas:
- user_ministries: Dimensión A — Ministerios (Efesios 4:11)
- user_church_roles: Dimensión B — Rol en la iglesia (embudo)
- kernel_role_history: Historial de cambios de rol de iglesia
- platform_role_definitions: Dimensión C — Definiciones de roles plataforma
- user_platform_roles: Dimensión C — Asignación de roles plataforma a usuarios
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260526_0034_kernel_identity"
down_revision: Union[str, None] = "20260525_0035"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ──────────────────────────────────────────────
# ENUM TYPES (PostgreSQL)
# ──────────────────────────────────────────────

ACTIVITY_STATUS_VALUES = ("ACTIVO", "INACTIVO")
MINISTRY_OFFICE_VALUES = (
    "APOSTOL", "PROFETA", "EVANGELISTA", "PASTOR", "MAESTRO",
)
CHURCH_ROLE_VALUES = (
    "LIDER", "SERVIDOR", "MIEMBRO_BAUTIZADO", "SIMPATIZANTE",
    "VISITANTE_SERVICIO", "VISITANTE_EVANGELISMO", "VISITANTE_ONLINE",
)
PLATFORM_ROLE_VALUES = ("ADMINISTRADOR", "GESTOR", "EDITOR", "LECTOR")




def _drop_enums(bind):
    for name in [
        "activity_status", "ministry_office",
        "church_role", "platform_role",
    ]:
        sa.Enum(name=name, create_type=False).drop(bind, checkfirst=True)


def upgrade() -> None:
    bind = op.get_bind()

    # Create enums with IF NOT EXISTS (raw SQL to avoid duplicate)
    bind.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE activity_status AS ENUM ('ACTIVO', 'INACTIVO');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
        DO $$ BEGIN
            CREATE TYPE ministry_office AS ENUM ('APOSTOL', 'PROFETA', 'EVANGELISTA', 'PASTOR', 'MAESTRO');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
        DO $$ BEGIN
            CREATE TYPE church_role AS ENUM ('LIDER', 'SERVIDOR', 'MIEMBRO_BAUTIZADO', 'SIMPATIZANTE', 'VISITANTE_SERVICIO', 'VISITANTE_EVANGELISMO', 'VISITANTE_ONLINE');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
        DO $$ BEGIN
            CREATE TYPE platform_role AS ENUM ('ADMINISTRADOR', 'GESTOR', 'EDITOR', 'LECTOR');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """))

    # ── Tabla: user_ministries (Dimensión A) ──
    op.create_table(
        "user_ministries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column(
            "ministry",
            sa.Enum(*MINISTRY_OFFICE_VALUES, name="ministry_office", create_type=False),
            nullable=False, index=True,
        ),
        sa.Column("is_primary", sa.Boolean(), default=False),
        sa.Column("recognized_at", sa.DateTime(), nullable=True),
        sa.Column(
            "recognized_by", sa.Integer(),
            sa.ForeignKey("users.id"), nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.UniqueConstraint(
            "user_id", "ministry", name="uq_user_ministry",
        ),
        sa.Index("ix_user_ministries_lookup", "user_id", "ministry"),
    )

    # ── Tabla: user_church_roles (Dimensión B) ──
    op.create_table(
        "user_church_roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False, unique=True, index=True,
        ),
        sa.Column(
            "church_role",
            sa.Enum(*CHURCH_ROLE_VALUES, name="church_role", create_type=False),
            nullable=False, index=True,
        ),
        sa.Column("assigned_at", sa.DateTime(), nullable=True),
        sa.Column(
            "assigned_by", sa.Integer(),
            sa.ForeignKey("users.id"), nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
    )

    # ── Tabla: kernel_role_history (Historial Dimensión B) ──
    op.create_table(
        "kernel_role_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column(
            "from_role",
            sa.Enum(*CHURCH_ROLE_VALUES, name="church_role", create_type=False),
            nullable=True,
        ),
        sa.Column(
            "to_role",
            sa.Enum(*CHURCH_ROLE_VALUES, name="church_role", create_type=False),
            nullable=False,
        ),
        sa.Column("reason", sa.String(200), nullable=True),
        sa.Column(
            "changed_by", sa.Integer(),
            sa.ForeignKey("users.id"), nullable=True,
        ),
        sa.Column("changed_at", sa.DateTime(), nullable=True, index=True),
        sa.Index("ix_role_history_user", "user_id", "changed_at"),
    )

    # ── Tabla: platform_role_definitions (Dimensión C) ──
    op.create_table(
        "platform_role_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "role",
            sa.Enum(*PLATFORM_ROLE_VALUES, name="platform_role", create_type=False),
            unique=True, nullable=False, index=True,
        ),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    # ── Tabla: user_platform_roles (Dimensión C — asignaciones) ──
    op.create_table(
        "user_platform_roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column(
            "role_id", sa.Integer(),
            sa.ForeignKey("platform_role_definitions.id"),
            nullable=False, index=True,
        ),
        sa.Column("assigned_at", sa.DateTime(), nullable=True),
        sa.Column(
            "assigned_by", sa.Integer(),
            sa.ForeignKey("users.id"), nullable=True,
        ),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True, index=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.UniqueConstraint(
            "user_id", "role_id", name="uq_user_platform_role",
        ),
    )

    # ── Seed data: definiciones de roles de plataforma ──
    _seed_platform_roles()

    # ── Índices estratégicos ──
    op.create_index(
        "ix_user_ministries_user", "user_ministries", ["user_id"],
    )
    op.create_index(
        "ix_church_roles_user", "user_church_roles", ["user_id"],
    )
    op.create_index(
        "ix_platform_roles_user",
        "user_platform_roles", ["user_id", "is_active"],
    )


def _seed_platform_roles():
    """Inserta las 4 definiciones de roles de plataforma."""
    gestor_perms = (
        '{"crm": ["create", "read", "update"], '
        '"academy": ["create", "read", "update"], '
        '"projects": ["create", "read", "update"], '
        '"evangelism": ["create", "read", "update"], '
        '"cms": ["read", "update"], '
        '"community": ["create", "read", "update"], '
        '"agenda": ["create", "read", "update"], '
        '"finances": ["read"]}'
    )
    editor_perms = (
        '{"crm": ["read", "update"], '
        '"academy": ["read"], '
        '"projects": ["read", "update"], '
        '"evangelism": ["read", "update"], '
        '"cms": ["read", "update"], '
        '"community": ["create", "read", "update"], '
        '"agenda": ["read"]}'
    )
    lector_perms = (
        '{"crm": ["read"], "academy": ["read"], '
        '"projects": ["read"], "evangelism": ["read"], '
        '"cms": ["read"], "community": ["read"], '
        '"agenda": ["read"]}'
    )

    op.execute(
        "INSERT INTO platform_role_definitions "
        "(role, permissions, description, created_at) VALUES "
        "('ADMINISTRADOR', "
        "'{\"*\": [\"create\", \"read\", \"update\", "
        "\"delete\", \"admin\"]}', "
        "'Control total del sistema, configuraciones globales', NOW()), "
        "('GESTOR', "
        "'" + gestor_perms + "', "
        "'Control sobre módulos asignados', NOW()), "
        "('EDITOR', "
        "'" + editor_perms + "', "
        "'Modificar contenido, reportar asistencias, mover tareas N2', "
        "NOW()), "
        "('LECTOR', "
        "'" + lector_perms + "', "
        "'Solo visualización de dashboards y contenido', NOW())"
    )


def downgrade() -> None:
    op.drop_index("ix_platform_roles_user", table_name="user_platform_roles")
    op.drop_index("ix_church_roles_user", table_name="user_church_roles")
    op.drop_index(
        "ix_user_ministries_user", table_name="user_ministries",
    )

    op.drop_table("user_platform_roles")
    op.drop_table("platform_role_definitions")
    op.drop_table("kernel_role_history")
    op.drop_table("user_church_roles")
    op.drop_table("user_ministries")

    bind = op.get_bind()
    _drop_enums(bind)
