"""create surveys core tables

Revision ID: 20260930_0001_create_surveys_tables
Revises: 20260929_0001_cms_seed_cartagena_locations
Create Date: 2026-09-30 00:30:00.000000

"""
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = '20260930_0001_create_surveys_tables'
down_revision = '20260929_0001_cms_seed_cartagena_locations'
branch_labels = None
depends_on = None


def upgrade():
    # 1. encuesta_formularios
    op.create_table(
        'encuesta_formularios',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('sede_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sedes.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('titulo', sa.String(length=255), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('slug', sa.String(length=255), nullable=True, index=True),
        sa.Column('es_publico', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('requiere_autenticacion', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('limitar_una_respuesta', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('permitir_editar_respuesta', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('mostrar_barra_progreso', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('mensaje_confirmacion', sa.Text(), nullable=True),
        sa.Column('redirigir_url', sa.String(length=500), nullable=True),
        sa.Column('fecha_apertura', sa.DateTime(timezone=True), nullable=True),
        sa.Column('fecha_cierre', sa.DateTime(timezone=True), nullable=True),
        sa.Column('max_respuestas', sa.Integer(), nullable=True),
        sa.Column('total_respuestas', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('estado', sa.String(length=50), nullable=False, server_default='BORRADOR'),
        sa.Column('config_visual', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('ajustes', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('creado_por_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('personas.id', ondelete='SET NULL'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

    # 2. encuesta_preguntas
    op.create_table(
        'encuesta_preguntas',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('formulario_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('encuesta_formularios.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('titulo', sa.Text(), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('tipo_pregunta', sa.String(length=50), nullable=False),
        sa.Column('orden', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('es_requerida', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('opciones', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('filas', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('columnas', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('escala_min', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('escala_max', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('escala_min_etiqueta', sa.String(length=100), nullable=True),
        sa.Column('escala_max_etiqueta', sa.String(length=100), nullable=True),
        sa.Column('archivo_tipos_permitidos', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('archivo_max_mb', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('archivo_max_archivos', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('configuracion', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # 3. encuesta_respuestas_envios
    op.create_table(
        'encuesta_respuestas_envios',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('formulario_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('encuesta_formularios.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('persona_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('personas.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('usuario_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('auth_users.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('ip_hash', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('email_respondente', sa.String(length=255), nullable=True, index=True),
        sa.Column('nombre_respondente', sa.String(length=255), nullable=True),
        sa.Column('metadatos', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # 4. encuesta_respuestas_detalles
    op.create_table(
        'encuesta_respuestas_detalles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('envio_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('encuesta_respuestas_envios.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('pregunta_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('encuesta_preguntas.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('valor_texto', sa.Text(), nullable=True),
        sa.Column('valor_numero', sa.Float(), nullable=True),
        sa.Column('valor_fecha', sa.Date(), nullable=True),
        sa.Column('valor_hora', sa.String(length=10), nullable=True),
        sa.Column('valor_json', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )


def downgrade():
    op.drop_table('encuesta_respuestas_detalles')
    op.drop_table('encuesta_respuestas_envios')
    op.drop_table('encuesta_preguntas')
    op.drop_table('encuesta_formularios')
