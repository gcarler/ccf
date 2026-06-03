"""Nuevo schema canónico de evangelismo.

Elimina tablas legacy (evangelism_strategies, grupos_evangelismo, grupo_*).
Crea: sedes, categorias_estrategia, motivos_excusa, logs_auditoria,
      estrategias_evangelismo, estrategia_roles_personalizados,
      grupos_evangelismo, personas, grupo_participantes,
      sesiones_grupo, asistencias, registros_seguimiento, historial_embudo.
Actualiza members: origen_estrategia_id Integer→VARCHAR(50), nuevas FKs.

Revision ID: 20260527_0037_evangelism_new_schema
Revises: 20260527_0036_member_tags_origen
Create Date: 2026-05-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260527_0037"
down_revision = "20260527_0036_member_tags_origen"
branch_labels = None
depends_on = None


def upgrade():
    # ── 1. Soltar FKs viejas de members ──────────────────────────────────────
    op.drop_constraint("fk_members_origen_estrategia", "members", type_="foreignkey")
    op.drop_constraint("fk_members_origen_grupo", "members", type_="foreignkey")
    op.drop_index("ix_members_origen_estrategia_id", table_name="members")
    op.drop_index("ix_members_origen_grupo_id", table_name="members")

    # ── 2. Eliminar tablas legacy (CASCADE elimina sus FKs dependientes) ──────
    op.execute("DROP TABLE IF EXISTS asistencias CASCADE")
    op.execute("DROP TABLE IF EXISTS grupo_participantes CASCADE")
    op.execute("DROP TABLE IF EXISTS sesiones_grupo CASCADE")
    op.execute("DROP TABLE IF EXISTS grupos_evangelismo CASCADE")
    op.execute("DROP TABLE IF EXISTS evangelism_strategies CASCADE")
    # Tablas intermedias que no se migraron y quedan obsoletas
    op.execute("DROP TABLE IF EXISTS roles_personalizados_estrategia CASCADE")
    op.execute("DROP TABLE IF EXISTS registros_seguimiento CASCADE")

    # ── 3. Crear tablas nuevas ─────────────────────────────────────────────────

    # sedes
    op.create_table(
        "sedes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column("ciudad", sa.String(100), nullable=False),
        sa.Column("es_activa", sa.Boolean(), server_default="true"),
    )
    # Sede principal por defecto
    op.execute("INSERT INTO sedes (nombre, ciudad, es_activa) VALUES ('Sede Principal', 'Bogotá', true)")

    # categorias_estrategia
    op.create_table(
        "categorias_estrategia",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nombre", sa.String(100), nullable=False, unique=True),
        sa.Column("descripcion", sa.String(255), nullable=True),
        sa.Column("es_del_sistema", sa.Boolean(), server_default="false"),
        sa.Column("activa", sa.Boolean(), server_default="true"),
    )

    # motivos_excusa
    op.create_table(
        "motivos_excusa",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("descripcion", sa.String(200), nullable=False, unique=True),
        sa.Column("es_del_sistema", sa.Boolean(), server_default="false"),
        sa.Column("activo", sa.Boolean(), server_default="true"),
    )

    # estrategias_evangelismo (PK es String)
    op.create_table(
        "estrategias_evangelismo",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("categoria_id", sa.Integer(), sa.ForeignKey("categorias_estrategia.id"), nullable=False),
        sa.Column("sede_id", sa.Integer(), sa.ForeignKey("sedes.id"), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column("frecuencia", sa.String(20), nullable=True),
        sa.Column("fecha_inicio", sa.DateTime(), nullable=True),
        sa.Column("fecha_fin", sa.DateTime(), nullable=True),
        sa.Column("activa", sa.Boolean(), server_default="true"),
    )

    # estrategia_roles_personalizados
    op.create_table(
        "estrategia_roles_personalizados",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("estrategia_id", sa.String(50), sa.ForeignKey("estrategias_evangelismo.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nombre_rol", sa.String(100), nullable=False),
        sa.Column("descripcion", sa.String(255), nullable=True),
    )

    # grupos_evangelismo
    op.create_table(
        "grupos_evangelismo",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("estrategia_id", sa.String(50), sa.ForeignKey("estrategias_evangelismo.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sede_id", sa.Integer(), sa.ForeignKey("sedes.id"), nullable=False),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column("ubicacion", sa.String(255), nullable=True),
        sa.Column("latitud", sa.Float(), nullable=True),
        sa.Column("longitud", sa.Float(), nullable=True),
        sa.Column("dia_reunion", sa.String(20), nullable=True),
        sa.Column("hora_reunion", sa.String(10), nullable=True),
        sa.Column("activo", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )

    # personas
    op.create_table(
        "personas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, unique=True),
        sa.Column("family_id", sa.Integer(), sa.ForeignKey("families.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sede_id", sa.Integer(), sa.ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("nombre_completo", sa.String(300), nullable=False),
        sa.Column("email", sa.String(200), nullable=True),
        sa.Column("telefono", sa.String(50), nullable=True),
        sa.Column("church_role", sa.String(100), nullable=True),
        sa.Column("estado_vital", sa.String(20), server_default="ACTIVO"),
        sa.Column("ministerio", sa.String(100), nullable=True),
        sa.Column("rol_iglesia", sa.String(100), nullable=True),
        sa.Column("permiso_plataforma", sa.String(50), nullable=True),
        sa.Column("datos_extra", postgresql.JSONB(), nullable=True),
        sa.Column("tags_sistema", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("origen_estrategia_id", sa.String(50), sa.ForeignKey("estrategias_evangelismo.id", ondelete="SET NULL"), nullable=True),
        sa.Column("origen_grupo_id", sa.Integer(), sa.ForeignKey("grupos_evangelismo.id", ondelete="SET NULL"), nullable=True),
        sa.Column("origen_fecha", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_personas_nombre_completo", "personas", ["nombre_completo"])
    op.create_index("ix_personas_email", "personas", ["email"])
    op.create_index("ix_personas_estado_vital", "personas", ["estado_vital"])

    # logs_auditoria (después de personas)
    op.create_table(
        "logs_auditoria",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tabla_afectada", sa.String(100), nullable=False),
        sa.Column("registro_id", sa.String(100), nullable=False),
        sa.Column("accion", sa.String(20), nullable=False),
        sa.Column("detalles_cambio", postgresql.JSONB(), nullable=True),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("fecha_accion", sa.DateTime(), server_default=sa.text("NOW()")),
    )

    # grupo_participantes
    op.create_table(
        "grupo_participantes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("grupo_id", sa.Integer(), sa.ForeignKey("grupos_evangelismo.id", ondelete="CASCADE"), nullable=False),
        sa.Column("persona_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rol_base", sa.String(20), nullable=False),
        sa.Column("rol_personalizado_id", sa.Integer(), sa.ForeignKey("estrategia_roles_personalizados.id", ondelete="SET NULL"), nullable=True),
        sa.Column("fecha_ingreso", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column("activo", sa.Boolean(), server_default="true"),
    )

    # sesiones_grupo
    op.create_table(
        "sesiones_grupo",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("grupo_id", sa.Integer(), sa.ForeignKey("grupos_evangelismo.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fecha_sesion", sa.DateTime(), nullable=False),
        sa.Column("estado", sa.String(20), server_default="PENDIENTE", nullable=False),
        sa.Column("motivo_cancelacion", sa.String(255), nullable=True),
        sa.Column("tema_estudio", sa.String(200), nullable=True),
        sa.Column("notas_lider", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )

    # asistencias
    op.create_table(
        "asistencias",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sesion_id", sa.Integer(), sa.ForeignKey("sesiones_grupo.id", ondelete="CASCADE"), nullable=False),
        sa.Column("persona_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("motivo_excusa_id", sa.Integer(), sa.ForeignKey("motivos_excusa.id", ondelete="SET NULL"), nullable=True),
        sa.Column("detalle_excusa", sa.String(255), nullable=True),
        sa.Column("es_primera_vez", sa.Boolean(), server_default="false"),
        sa.Column("requiere_seguimiento", sa.Boolean(), server_default="false"),
    )

    # registros_seguimiento
    op.create_table(
        "registros_seguimiento",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("asistencia_id", sa.Integer(), sa.ForeignKey("asistencias.id", ondelete="CASCADE"), nullable=False),
        sa.Column("responsable_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("fecha_seguimiento", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("estado_completado", sa.Boolean(), server_default="true"),
    )

    # historial_embudo
    op.create_table(
        "historial_embudo",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("persona_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rol_anterior", sa.String(100), nullable=True),
        sa.Column("rol_nuevo", sa.String(100), nullable=False),
        sa.Column("fecha_cambio", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column("dias_en_estado_anterior", sa.Integer(), nullable=True),
    )

    # ── 4. Actualizar members: origen_estrategia_id Integer → VARCHAR(50) ─────
    op.alter_column(
        "members",
        "origen_estrategia_id",
        type_=sa.String(50),
        postgresql_using="NULL",
        existing_type=sa.Integer(),
        existing_nullable=True,
    )
    # Limpiar datos (los integers no son IDs válidos del nuevo esquema)
    op.execute("UPDATE members SET origen_estrategia_id = NULL, origen_grupo_id = NULL")

    op.create_foreign_key(
        "fk_members_origen_estrategia",
        "members", "estrategias_evangelismo",
        ["origen_estrategia_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_members_origen_grupo",
        "members", "grupos_evangelismo",
        ["origen_grupo_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_members_origen_estrategia_id", "members", ["origen_estrategia_id"])
    op.create_index("ix_members_origen_grupo_id", "members", ["origen_grupo_id"])

    # ── 5. Vista materializada OLAP ───────────────────────────────────────────
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_resumen_asistencia AS
        SELECT
            g.sede_id,
            g.estrategia_id,
            DATE_TRUNC('month', sg.fecha_sesion) AS mes,
            COUNT(a.id) FILTER (WHERE a.estado = 'ASISTIO') AS total_asistencias,
            COUNT(a.id) FILTER (WHERE a.estado = 'FALTO')   AS total_faltas,
            COUNT(a.id) FILTER (WHERE a.es_primera_vez = TRUE) AS total_nuevos
        FROM sesiones_grupo sg
        JOIN asistencias a ON sg.id = a.sesion_id
        JOIN grupos_evangelismo g ON sg.grupo_id = g.id
        GROUP BY g.sede_id, g.estrategia_id, DATE_TRUNC('month', sg.fecha_sesion)
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_resumen_asistencia
        ON mv_resumen_asistencia(sede_id, estrategia_id, mes)
    """)


def downgrade():
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_resumen_asistencia CASCADE")
    op.drop_constraint("fk_members_origen_estrategia", "members", type_="foreignkey")
    op.drop_constraint("fk_members_origen_grupo", "members", type_="foreignkey")
    op.drop_index("ix_members_origen_estrategia_id", table_name="members")
    op.drop_index("ix_members_origen_grupo_id", table_name="members")
    op.alter_column("members", "origen_estrategia_id", type_=sa.Integer(), existing_type=sa.String(50), existing_nullable=True)

    op.execute("DROP TABLE IF EXISTS historial_embudo CASCADE")
    op.execute("DROP TABLE IF EXISTS registros_seguimiento CASCADE")
    op.execute("DROP TABLE IF EXISTS asistencias CASCADE")
    op.execute("DROP TABLE IF EXISTS sesiones_grupo CASCADE")
    op.execute("DROP TABLE IF EXISTS grupo_participantes CASCADE")
    op.execute("DROP TABLE IF EXISTS logs_auditoria CASCADE")
    op.execute("DROP TABLE IF EXISTS personas CASCADE")
    op.execute("DROP TABLE IF EXISTS grupos_evangelismo CASCADE")
    op.execute("DROP TABLE IF EXISTS estrategia_roles_personalizados CASCADE")
    op.execute("DROP TABLE IF EXISTS estrategias_evangelismo CASCADE")
    op.execute("DROP TABLE IF EXISTS motivos_excusa CASCADE")
    op.execute("DROP TABLE IF EXISTS categorias_estrategia CASCADE")
    op.execute("DROP TABLE IF EXISTS sedes CASCADE")
