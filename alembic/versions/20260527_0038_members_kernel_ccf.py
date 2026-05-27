"""0038_members_kernel_ccf

Revision ID: 20260527_0038
Revises: 20260527_0037
Create Date: 2026-05-27

Members Super Pro — Identidad Única Multiagente:
- Agrega columnas a members (sede_id, estado_vital, ministerio, etc.)
- Crea historial_ministerial (máquina del tiempo)
- Crea trigger automático para historial_ministerial
- Crea índices estratégicos (B-Tree)
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260527_0038"
down_revision: Union[str, None] = "20260527_0037"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # MULTI-TENANT
    if not _column_exists("members", "sede_id"):
        op.add_column(
            "members",
            sa.Column(
                "sede_id", sa.Integer(),
                sa.ForeignKey("sedes.id"), nullable=True,
            ),
        )
        op.create_index("ix_members_sede", "members", ["sede_id"])

    # PERFIL TRIDIMENSIONAL
    for col, typ, default in [
        ("estado_vital", sa.String(20), "ACTIVO"),
        ("ministerio", sa.String(50), None),
        ("permiso_plataforma", sa.String(50), None),
        ("fecha_bautismo", sa.DateTime(), None),
        ("latitud", sa.Float(), None),
        ("longitud", sa.Float(), None),
    ]:
        if not _column_exists("members", col):
            kwargs = {"nullable": True}
            if default:
                kwargs["server_default"] = default
                kwargs["nullable"] = False
            op.add_column(
                "members",
                sa.Column(col, typ, **kwargs),
            )

    # ÍNDICES ESTRATÉGICOS
    for idx, cols in [
        ("ix_members_rol_iglesia", ["church_role"]),
        ("ix_members_fecha_registro", ["created_at"]),
        ("ix_members_estado_vital", ["estado_vital"]),
        ("ix_members_ministerio", ["ministerio"]),
    ]:
        if not _index_exists(idx):
            op.create_index(idx, "members", cols)

    # HISTORIAL MINISTERIAL
    if not _table_exists("historial_ministerial"):
        op.create_table(
            "historial_ministerial",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "miembro_id", sa.Integer(),
                sa.ForeignKey("members.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("tipo_cambio", sa.String(50), nullable=False),
            sa.Column("valor_anterior", sa.String(100), nullable=True),
            sa.Column("valor_nuevo", sa.String(100), nullable=False),
            sa.Column(
                "fecha_cambio", sa.DateTime(),
                server_default=sa.func.now(),
            ),
            sa.Column("dias_transcurridos", sa.Integer(), nullable=True),
            sa.Index("ix_hist_min_miembro", "miembro_id"),
            sa.Index("ix_hist_min_tipo", "tipo_cambio"),
            sa.Index("ix_hist_min_fecha", "fecha_cambio"),
        )

    # TRIGGER AUTOMÁTICO
    _create_trigger()


def _create_trigger():
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_track_member_ministry_changes()
        RETURNS TRIGGER AS $$
        BEGIN
            IF OLD.estado_vital IS DISTINCT FROM NEW.estado_vital THEN
                INSERT INTO historial_ministerial
                    (miembro_id, tipo_cambio, valor_anterior, valor_nuevo)
                VALUES (NEW.id, 'ESTADO_VITAL', OLD.estado_vital, NEW.estado_vital);
            END IF;
            IF OLD.ministerio IS DISTINCT FROM NEW.ministerio THEN
                INSERT INTO historial_ministerial
                    (miembro_id, tipo_cambio, valor_anterior, valor_nuevo)
                VALUES (NEW.id, 'MINISTERIO', OLD.ministerio, NEW.ministerio);
            END IF;
            IF OLD.church_role IS DISTINCT FROM NEW.church_role THEN
                INSERT INTO historial_ministerial
                    (miembro_id, tipo_cambio, valor_anterior, valor_nuevo)
                VALUES (NEW.id, 'ROL_IGLESIA', OLD.church_role, NEW.church_role);
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        DROP TRIGGER IF EXISTS trg_track_ministry ON members;
        CREATE TRIGGER trg_track_ministry
            AFTER UPDATE ON members FOR EACH ROW
            EXECUTE FUNCTION fn_track_member_ministry_changes();
    """)


def _column_exists(table, column):
    conn = op.get_bind()
    r = conn.execute(sa.text(
        "SELECT count(*) FROM information_schema.columns "
        "WHERE table_name=:t AND column_name=:c"
    ), {"t": table, "c": column})
    return r.scalar() > 0


def _index_exists(name):
    conn = op.get_bind()
    r = conn.execute(sa.text(
        "SELECT count(*) FROM pg_indexes WHERE indexname=:n"
    ), {"n": name})
    return r.scalar() > 0


def _table_exists(name):
    conn = op.get_bind()
    r = conn.execute(sa.text(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_name=:n"
    ), {"n": name})
    return r.scalar() > 0


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_track_ministry ON members")
    op.execute("DROP FUNCTION IF EXISTS fn_track_member_ministry_changes()")
    op.drop_table("historial_ministerial")
    for idx in ["ix_members_estado_vital", "ix_members_ministerio",
                 "ix_members_fecha_registro", "ix_members_rol_iglesia",
                 "ix_members_sede"]:
        op.drop_index(idx, table_name="members")
    for col in ["longitud", "latitud", "fecha_bautismo",
                 "permiso_plataforma", "ministerio", "estado_vital", "sede_id"]:
        op.drop_column("members", col)
