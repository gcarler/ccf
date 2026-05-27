"""0037_evangelismo_super_pro

Revision ID: 20260527_0037
Revises: 20260527_0036_member_tags_origen
Create Date: 2026-05-27

Modelo de Evangelismo Super Pro:
- sedes (multi-tenant)
- categorias_estrategia
- logs_auditoria (JSONB)
- estrategias_evangelismo_super (con sede_id + categoria_id)
- grupos_evangelismo_super (con geolocalización)
- historial_embudo (velocidad ministerial)
- Vistas materializadas OLAP
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision: str = "20260527_0037"
down_revision: Union[str, None] = "20260527_0036_member_tags_origen"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── sedes ──
    op.create_table(
        "sedes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("ciudad", sa.String(100), nullable=False),
        sa.Column("es_activa", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    # ── categorias_estrategia ──
    op.create_table(
        "categorias_estrategia",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nombre", sa.String(100), nullable=False, unique=True),
        sa.Column("descripcion", sa.String(255), nullable=True),
        sa.Column("es_del_sistema", sa.Boolean(), server_default="false"),
        sa.Column("activa", sa.Boolean(), server_default="true"),
        sa.Index("ix_cat_estrategia_activa", "activa"),
    )

    # ── logs_auditoria (con JSONB de PostgreSQL) ──
    op.create_table(
        "logs_auditoria",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tabla_afectada", sa.String(50), nullable=False),
        sa.Column("registro_id", sa.String(50), nullable=False),
        sa.Column("accion", sa.String(20), nullable=False),
        sa.Column("detalles_cambio", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("usuario_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("fecha_accion", sa.DateTime(), nullable=True),
        sa.Index("ix_auditoria_tabla", "tabla_afectada"),
        sa.Index("ix_auditoria_fecha", "fecha_accion"),
        sa.Index("ix_auditoria_usuario", "usuario_id"),
    )

    # ── estrategias_evangelismo_super ──
    op.create_table(
        "estrategias_evangelismo_super",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("categoria_id", sa.Integer(), sa.ForeignKey("categorias_estrategia.id"), nullable=False),
        sa.Column("sede_id", sa.Integer(), sa.ForeignKey("sedes.id"), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=True),
        sa.Column("frecuencia", sa.String(20), nullable=True),
        sa.Column("fecha_inicio", sa.DateTime(), nullable=True),
        sa.Column("fecha_fin", sa.DateTime(), nullable=True),
        sa.Column("activa", sa.Boolean(), server_default="true"),
        sa.Index("ix_ee_super_categoria", "categoria_id"),
        sa.Index("ix_ee_super_sede", "sede_id"),
        sa.Index("ix_ee_super_activa", "activa"),
    )

    # ── grupos_evangelismo_super (con geolocalización) ──
    op.create_table(
        "grupos_evangelismo_super",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("estrategia_id", sa.String(20), sa.ForeignKey("estrategias_evangelismo_super.id"), nullable=False),
        sa.Column("sede_id", sa.Integer(), sa.ForeignKey("sedes.id"), nullable=False),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("ubicacion", sa.String(255), nullable=True),
        sa.Column("latitud", sa.Float(), nullable=True),
        sa.Column("longitud", sa.Float(), nullable=True),
        sa.Column("dia_reunion", sa.String(20), nullable=True),
        sa.Column("hora_reunion", sa.String(10), nullable=True),
        sa.Column("activo", sa.Boolean(), server_default="true"),
        sa.Index("ix_grupo_super_estrategia", "estrategia_id"),
        sa.Index("ix_grupo_super_sede", "sede_id"),
        sa.Index("ix_grupo_super_activo", "activo"),
    )

    # ── historial_embudo (velocidad ministerial) ──
    op.create_table(
        "historial_embudo",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("persona_id", sa.Integer(), sa.ForeignKey("members.id"), nullable=False),
        sa.Column("rol_anterior", sa.String(50), nullable=True),
        sa.Column("rol_nuevo", sa.String(50), nullable=False),
        sa.Column("fecha_cambio", sa.DateTime(), nullable=True),
        sa.Column("dias_en_estado_anterior", sa.Integer(), nullable=True),
        sa.Index("ix_embudo_persona", "persona_id"),
        sa.Index("ix_embudo_fecha", "fecha_cambio"),
    )

    # ── F2: Extender tablas existentes ──
    # Agregar sede_id a evangelism_strategies (nullable para compatibilidad)
    op.add_column(
        "evangelism_strategies",
        sa.Column("sede_id", sa.Integer(), sa.ForeignKey("sedes.id"), nullable=True),
    )
    op.create_index("ix_evangelism_strategies_sede", "evangelism_strategies", ["sede_id"])

    # Agregar categoria_id a evangelism_strategies
    op.add_column(
        "evangelism_strategies",
        sa.Column("categoria_id", sa.Integer(), sa.ForeignKey("categorias_estrategia.id"), nullable=True),
    )
    op.create_index("ix_evangelism_strategies_categoria", "evangelism_strategies", ["categoria_id"])

    # Agregar sede_id a glory_houses (nullable para compatibilidad)
    op.add_column(
        "glory_houses",
        sa.Column("sede_id", sa.Integer(), sa.ForeignKey("sedes.id"), nullable=True),
    )
    op.create_index("ix_glory_houses_sede", "glory_houses", ["sede_id"])

    # Asignar todas las estrategias existentes a Sede Principal (id=1)
    op.execute("""
        UPDATE evangelism_strategies
        SET sede_id = (SELECT id FROM sedes WHERE nombre = 'Sede Principal' LIMIT 1)
        WHERE sede_id IS NULL
    """)

    # Asignar todas las glory_houses existentes a Sede Principal
    op.execute("""
        UPDATE glory_houses
        SET sede_id = (SELECT id FROM sedes WHERE nombre = 'Sede Principal' LIMIT 1)
        WHERE sede_id IS NULL
    """)

    # Asignar categoría "Faro en Casa" a estrategias existentes de tipo relacional
    op.execute("""
        UPDATE evangelism_strategies
        SET categoria_id = (SELECT id FROM categorias_estrategia WHERE nombre = 'Faro en Casa' LIMIT 1)
        WHERE categoria_id IS NULL AND strategy_type = 'Relacional'
    """)

    # Seed Data ──
    _seed_data()

    # ── Vistas materializadas OLAP ──
    _create_materialized_views()


def _seed_data():
    """Seed data para sedes, categorías y motivos de excusa."""
    # Sedes
    op.execute(
        "INSERT INTO sedes (nombre, ciudad, es_activa, created_at) VALUES "
        "('Sede Principal', 'Bogotá', true, NOW()), "
        "('Sede Norte', 'Bogotá', true, NOW()), "
        "('Sede Sur', 'Bogotá', true, NOW())"
    )

    # Categorías de estrategia
    op.execute(
        "INSERT INTO categorias_estrategia (nombre, descripcion, es_del_sistema, activa) VALUES "
        "('Faro en Casa', 'Grupos pequeños en hogares para evangelismo relacional', true, true), "
        "('Evento Masivo', 'Eventos de gran escala para alcance masivo', true, true), "
        "('Sectorial', 'Estrategias enfocadas en nichos o sectores específicos', true, true)"
    )


def _create_materialized_views():
    """Crea vistas materializadas para dashboards rápidos."""
    # Vista de resumen de asistencia
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_resumen_asistencia AS
        SELECT 
            g.evangelism_strategy_id as estrategia_id,
            DATE_TRUNC('month', ghss.session_date) as mes,
            COUNT(gha.id) FILTER (WHERE gha.attended = TRUE) as total_asistencias,
            COUNT(gha.id) FILTER (WHERE gha.attended = FALSE) as total_faltas,
            COUNT(gha.id) FILTER (WHERE gha.status = 'first_time' OR gha.es_primera_vez = TRUE) as total_nuevos
        FROM glory_house_sessions ghss
        JOIN glory_house_attendance gha ON ghss.id = gha.session_id
        JOIN glory_houses g ON ghss.glory_house_id = g.id
        GROUP BY g.evangelism_strategy_id, DATE_TRUNC('month', ghss.session_date)
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_resumen_asistencia 
        ON mv_resumen_asistencia(estrategia_id, mes)
    """)

    # Vista de velocidad del embudo
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_velocidad_embudo AS
        SELECT 
            he.persona_id,
            he.rol_anterior,
            he.rol_nuevo,
            he.dias_en_estado_anterior,
            he.fecha_cambio
        FROM historial_embudo he
        WHERE he.dias_en_estado_anterior IS NOT NULL
        ORDER BY he.fecha_cambio DESC
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_mv_velocidad_persona 
        ON mv_velocidad_embudo(persona_id)
    """)


def downgrade() -> None:
    # Remove views
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_velocidad_embudo")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_resumen_asistencia")

    # Drop new tables
    op.drop_table("historial_embudo")
    op.drop_table("grupos_evangelismo_super")
    op.drop_table("estrategias_evangelismo_super")
    op.drop_table("logs_auditoria")

    # Remove extended columns from existing tables
    op.drop_index("ix_glory_houses_sede", table_name="glory_houses")
    op.drop_column("glory_houses", "sede_id")

    op.drop_index("ix_evangelism_strategies_categoria", table_name="evangelism_strategies")
    op.drop_column("evangelism_strategies", "categoria_id")

    op.drop_index("ix_evangelism_strategies_sede", table_name="evangelism_strategies")
    op.drop_column("evangelism_strategies", "sede_id")

    op.drop_table("categorias_estrategia")
    op.drop_table("sedes")
