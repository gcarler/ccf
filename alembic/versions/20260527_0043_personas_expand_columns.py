"""0043_personas_expand_columns

Revision ID: 20260527_0043
Revises: 20260527_0042
Create Date: 2026-05-27

Expande la tabla personas con todos los campos del perfil CRM
(migración desde members). La tabla fue creada en 0037 con un esquema
mínimo para evangelismo; aquí añadimos el perfil completo.

También:
- Actualiza stored procedures a personas (reemplaza member SPs)
- Crea mv_persona_engagement
- Crea persona_ministries, persona_church_roles, persona_role_history,
  persona_platform_roles (Kernel Identidad — Dimensión C)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260527_0043"
down_revision: Union[str, None] = "20260527_0042"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _col_exists(table: str, col: str) -> bool:
    conn = op.get_bind()
    r = conn.execute(sa.text(
        "SELECT count(*) FROM information_schema.columns "
        "WHERE table_name=:t AND column_name=:c"
    ), {"t": table, "c": col})
    return r.scalar() > 0


def _table_exists(name: str) -> bool:
    conn = op.get_bind()
    r = conn.execute(sa.text(
        "SELECT count(*) FROM information_schema.tables WHERE table_name=:n"
    ), {"n": name})
    return r.scalar() > 0


def _index_exists(name: str) -> bool:
    conn = op.get_bind()
    r = conn.execute(sa.text(
        "SELECT count(*) FROM pg_indexes WHERE indexname=:n"
    ), {"n": name})
    return r.scalar() > 0


# ──────────────────────────────────────────────────────────────────────────────
# UPGRADE
# ──────────────────────────────────────────────────────────────────────────────

def upgrade() -> None:
    _expand_personas_columns()
    _migrate_legacy_nombre_completo()
    _add_persona_id_to_historial()
    _update_stored_procedures()
    _create_persona_engagement_view()
    _create_kernel_identity_tables()
    _migrate_kernel_data_to_persona()


def _expand_personas_columns() -> None:
    """Agrega columnas de perfil completo a personas."""
    columns = [
        ("first_name",              sa.String(100),     True),
        ("last_name",               sa.String(100),     True),
        ("second_name",             sa.String(100),     True),
        ("second_last_name",        sa.String(100),     True),
        ("phone",                   sa.String(20),      True),
        ("mobile_phone",            sa.String(20),      True),
        ("landline_phone",          sa.String(20),      True),
        ("other_phone",             sa.String(20),      True),
        ("is_baptized",             sa.Boolean(),       True),
        ("fecha_bautismo",          sa.Date(),          True),
        ("spiritual_status",        sa.String(50),      True),
        ("id_type",                 sa.String(50),      True),
        ("id_number",               sa.String(50),      True),
        ("marital_status",          sa.String(50),      True),
        ("birth_country",           sa.String(100),     True),
        ("address",                 sa.Text(),          True),
        ("housing_type",            sa.String(50),      True),
        ("education_level",         sa.String(100),     True),
        ("education_status",        sa.String(50),      True),
        ("profession",              sa.String(100),     True),
        ("economic_sector",         sa.String(100),     True),
        ("blood_type",              sa.String(10),      True),
        ("medical_notes",           sa.Text(),          True),
        ("optional_info",           sa.Text(),          True),
        ("registration_reason",     sa.String(100),     True),
        ("unregistration_reason",   sa.String(100),     True),
        ("registration_date",       sa.Date(),          True),
        ("unregistration_date",     sa.Date(),          True),
        ("responsible_adult_name",  sa.String(200),     True),
        ("responsible_adult_contact", sa.String(100),   True),
        ("guardian_name",           sa.String(200),     True),
        ("guardian_contact",        sa.String(100),     True),
        ("sex",                     sa.String(1),       True),
        ("last_group_attendance",   sa.Date(),          True),
        ("last_meeting_attendance", sa.Date(),          True),
        ("membership_type",         sa.String(50),      True),
        ("attendance_type",         sa.String(50),      True),
        ("group_name",              sa.String(100),     True),
        ("campus",                  sa.String(100),     True),
        ("church_join_date",        sa.Date(),          True),
        ("city",                    sa.String(100),     True),
        ("latitud",                 sa.Float(),         True),
        ("longitud",                sa.Float(),         True),
        ("qr_token",                sa.String(100),     True),
        ("birthday",                sa.DateTime(),      True),
        ("role_in_family",          sa.String(50),      True),
        ("talents",                 sa.Text(),          True),
        ("spiritual_gifts",         sa.Text(),          True),
        ("pastoral_notes",          sa.Text(),          True),
        ("colombian_department_id", sa.Integer(),       True),
    ]

    for col_name, col_type, nullable in columns:
        if not _col_exists("personas", col_name):
            op.add_column("personas", sa.Column(col_name, col_type, nullable=nullable))

    # FK para colombian_department_id
    if _col_exists("personas", "colombian_department_id") and _table_exists("colombian_departments"):
        try:
            op.create_foreign_key(
                "fk_personas_colombian_dept",
                "personas", "colombian_departments",
                ["colombian_department_id"], ["id"],
                ondelete="SET NULL",
            )
        except Exception:
            pass  # Ya existe

    # Renombrar datos_extra → metadata si aplica
    if _col_exists("personas", "datos_extra") and not _col_exists("personas", "metadata"):
        op.alter_column("personas", "datos_extra", new_column_name="metadata")

    # Renombrar tags_sistema → tags si aplica
    if _col_exists("personas", "tags_sistema") and not _col_exists("personas", "tags"):
        op.alter_column("personas", "tags_sistema", new_column_name="tags")

    # Índices
    for idx, cols in [
        ("ix_personas_first_name",  ["first_name"]),
        ("ix_personas_last_name",   ["last_name"]),
        ("ix_personas_phone",       ["phone"]),
        ("ix_personas_qr_token",    ["qr_token"]),
    ]:
        if not _index_exists(idx):
            op.create_index(idx, "personas", cols)


def _migrate_legacy_nombre_completo() -> None:
    """Puebla first_name/last_name desde nombre_completo y phone desde telefono.
    Solo aplica si las columnas legacy existen (migration 0037 style).
    """
    if _col_exists("personas", "nombre_completo"):
        op.execute(sa.text("""
            UPDATE personas SET
                first_name = CASE
                    WHEN nombre_completo IS NOT NULL AND TRIM(nombre_completo) <> ''
                    THEN SPLIT_PART(TRIM(nombre_completo), ' ', 1)
                    ELSE 'Sin'
                END,
                last_name = CASE
                    WHEN nombre_completo IS NOT NULL AND POSITION(' ' IN TRIM(nombre_completo)) > 0
                    THEN SUBSTRING(TRIM(nombre_completo) FROM POSITION(' ' IN TRIM(nombre_completo)) + 1)
                    ELSE 'Nombre'
                END
            WHERE first_name IS NULL
        """))

    if _col_exists("personas", "telefono"):
        op.execute(sa.text("""
            UPDATE personas SET phone = telefono
            WHERE phone IS NULL AND telefono IS NOT NULL
        """))


def _personas_id_type() -> str:
    """Devuelve el tipo de datos de personas.id en la BD actual."""
    conn = op.get_bind()
    r = conn.execute(sa.text(
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_name='personas' AND column_name='id'"
    ))
    row = r.fetchone()
    return (row[0] if row else "integer").lower()


def _add_persona_id_to_historial() -> None:
    """Agrega persona_id a historial_ministerial con el mismo tipo que personas.id."""
    if not _col_exists("historial_ministerial", "persona_id"):
        pk_type = _personas_id_type()
        col_type = postgresql.UUID(as_uuid=True) if "uuid" in pk_type else sa.Integer()
        op.add_column(
            "historial_ministerial",
            sa.Column(
                "persona_id",
                col_type,
                sa.ForeignKey("personas.id", ondelete="CASCADE"),
                nullable=True,
                index=True,
            ),
        )
        # Poblar persona_id: JOIN directo por miembro_id = personas.id (misma tabla)
        if not _table_exists("members"):
            op.execute(sa.text("""
                UPDATE historial_ministerial hm
                SET persona_id = hm.miembro_id
                WHERE hm.miembro_id IS NOT NULL
            """))


def _update_stored_procedures() -> None:
    """Reemplaza SPs legacy de members con versiones para personas."""

    # Eliminar SPs legacy
    for sp in [
        "fn_search_members",
        "fn_member_engagement_score",
        "fn_upsert_member",
        "fn_generate_qr_token",
        "fn_track_member_ministry_changes",
    ]:
        op.execute(sa.text(f"DROP FUNCTION IF EXISTS {sp} CASCADE"))

    pk_type = _personas_id_type()
    id_sql_type = "UUID" if "uuid" in pk_type else "INTEGER"

    # fn_buscar_personas
    op.execute(sa.text(f"""
        CREATE OR REPLACE FUNCTION fn_buscar_personas(
            p_query TEXT,
            p_limit INT DEFAULT 20
        )
        RETURNS TABLE (
            id {id_sql_type},
            nombre_completo TEXT,
            email VARCHAR,
            telefono VARCHAR,
            church_role VARCHAR,
            estado_vital VARCHAR
        ) AS $$
        BEGIN
            RETURN QUERY
            SELECT
                p.id,
                TRIM(COALESCE(p.first_name,'') || ' ' || COALESCE(p.last_name,'')) AS nombre_completo,
                p.email,
                COALESCE(p.phone, p.mobile_phone) AS telefono,
                p.church_role,
                p.estado_vital
            FROM personas p
            WHERE
                LOWER(p.first_name) ILIKE '%' || LOWER(p_query) || '%'
                OR LOWER(p.last_name) ILIKE '%' || LOWER(p_query) || '%'
                OR LOWER(p.email) ILIKE '%' || LOWER(p_query) || '%'
                OR LOWER(COALESCE(p.phone,'')) ILIKE '%' || LOWER(p_query) || '%'
            ORDER BY p.first_name, p.last_name
            LIMIT p_limit;
        END;
        $$ LANGUAGE plpgsql;
    """))

    # fn_engagement_persona
    op.execute(sa.text(f"""
        CREATE OR REPLACE FUNCTION fn_engagement_persona(p_persona_id {id_sql_type})
        RETURNS JSONB AS $$
        DECLARE
            v_result JSONB;
        BEGIN
            SELECT jsonb_build_object(
                'persona_id',       p.id,
                'nombre_completo',  TRIM(COALESCE(p.first_name,'') || ' ' || COALESCE(p.last_name,'')),
                'estado_vital',     p.estado_vital,
                'asistencias_totales', COALESCE(a_count.total, 0),
                'seguimientos',     COALESCE(s_count.total, 0)
            ) INTO v_result
            FROM personas p
            LEFT JOIN (
                SELECT persona_id, COUNT(*) AS total
                FROM asistencias WHERE persona_id = p_persona_id GROUP BY persona_id
            ) a_count ON TRUE
            LEFT JOIN (
                SELECT responsable_id, COUNT(*) AS total
                FROM registros_seguimiento WHERE responsable_id = p_persona_id GROUP BY responsable_id
            ) s_count ON TRUE
            WHERE p.id = p_persona_id;

            RETURN v_result;
        END;
        $$ LANGUAGE plpgsql;
    """))

    # Trigger historial_ministerial en personas
    op.execute(sa.text("""
        CREATE OR REPLACE FUNCTION fn_track_persona_ministry_changes()
        RETURNS TRIGGER AS $$
        BEGIN
            IF OLD.estado_vital IS DISTINCT FROM NEW.estado_vital THEN
                INSERT INTO historial_ministerial (persona_id, tipo_cambio, valor_anterior, valor_nuevo)
                VALUES (NEW.id, 'ESTADO_VITAL', OLD.estado_vital, NEW.estado_vital);
            END IF;
            IF OLD.ministerio IS DISTINCT FROM NEW.ministerio THEN
                INSERT INTO historial_ministerial (persona_id, tipo_cambio, valor_anterior, valor_nuevo)
                VALUES (NEW.id, 'MINISTERIO', OLD.ministerio, NEW.ministerio);
            END IF;
            IF OLD.church_role IS DISTINCT FROM NEW.church_role THEN
                INSERT INTO historial_ministerial (persona_id, tipo_cambio, valor_anterior, valor_nuevo)
                VALUES (NEW.id, 'ROL_IGLESIA', OLD.church_role, NEW.church_role);
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """))
    op.execute(sa.text("""
        DROP TRIGGER IF EXISTS trg_track_ministry_persona ON personas;
        CREATE TRIGGER trg_track_ministry_persona
            AFTER UPDATE ON personas FOR EACH ROW
            EXECUTE FUNCTION fn_track_persona_ministry_changes();
    """))


def _create_persona_engagement_view() -> None:
    op.execute(sa.text("DROP MATERIALIZED VIEW IF EXISTS mv_persona_engagement CASCADE"))
    # Si personas.id es UUID y asistencias.persona_id también es UUID: JOIN directo.
    # Si tipos difieren (persona INT, asistencias UUID en transición): vista sin JOIN a asistencias.
    pk_type = _personas_id_type()
    conn = op.get_bind()
    r = conn.execute(sa.text(
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_name='asistencias' AND column_name='persona_id'"
    ))
    asist_type = (r.fetchone() or ("integer",))[0].lower()
    types_match = ("uuid" in pk_type) == ("uuid" in asist_type)

    if types_match:
        join_clause = "LEFT JOIN asistencias a ON a.persona_id = p.id"
        count_asist = "COUNT(DISTINCT a.id)"
        extra_group = ""
    else:
        join_clause = ""
        count_asist = "0"
        extra_group = ""

    op.execute(sa.text(f"""
        CREATE MATERIALIZED VIEW mv_persona_engagement AS
        SELECT
            p.id AS persona_id,
            TRIM(COALESCE(p.first_name,'') || ' ' || COALESCE(p.last_name,'')) AS nombre_completo,
            p.email,
            COALESCE(p.phone, p.mobile_phone) AS telefono,
            p.church_role,
            p.estado_vital,
            {count_asist} AS asistencias_totales,
            0 AS seguimientos_totales
        FROM personas p
        {join_clause}
        GROUP BY p.id, p.first_name, p.last_name, p.email, p.phone, p.mobile_phone,
                 p.church_role, p.estado_vital
        WITH DATA;
    """))
    op.execute(sa.text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_mv_persona_engagement_id "
        "ON mv_persona_engagement (persona_id)"
    ))


def _create_kernel_identity_tables() -> None:
    """Crea las tablas del Kernel de Identidad."""

    if not _table_exists("persona_ministries"):
        op.create_table(
            "persona_ministries",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("persona_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("personas.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("ministry", sa.String(100), nullable=False),
            sa.Column("is_primary", sa.Boolean(), server_default="false"),
            sa.Column("recognized_at", sa.DateTime(), server_default=sa.text("NOW()")),
            sa.Column("recognized_by_id", sa.Integer(),
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.UniqueConstraint("persona_id", "ministry", name="uq_persona_ministry"),
        )

    if not _table_exists("persona_church_roles"):
        op.create_table(
            "persona_church_roles",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("persona_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("personas.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("church_role", sa.String(100), nullable=False),
            sa.Column("assigned_at", sa.DateTime(), server_default=sa.text("NOW()")),
            sa.Column("changed_by_id", sa.Integer(),
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.UniqueConstraint("persona_id", name="uq_persona_church_role"),
        )

    if not _table_exists("persona_role_history"):
        op.create_table(
            "persona_role_history",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("persona_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("personas.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("previous_role", sa.String(100), nullable=True),
            sa.Column("new_role", sa.String(100), nullable=False),
            sa.Column("changed_at", sa.DateTime(), server_default=sa.text("NOW()")),
            sa.Column("changed_by_id", sa.Integer(),
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
        )

    if not _table_exists("platform_role_definitions"):
        op.create_table(
            "platform_role_definitions",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(100), nullable=False, unique=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("permissions", postgresql.JSONB(), nullable=True, server_default="'{}'"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
        )
        # Seed default platform roles
        op.execute(sa.text("""
            INSERT INTO platform_role_definitions (name, description) VALUES
            ('ADMINISTRADOR', 'Acceso completo al sistema'),
            ('GESTOR',        'Gestión de módulos operativos'),
            ('EDITOR',        'Edición de contenido y registros'),
            ('LECTOR',        'Solo lectura')
            ON CONFLICT (name) DO NOTHING
        """))

    if not _table_exists("persona_platform_roles"):
        op.create_table(
            "persona_platform_roles",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("persona_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("personas.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("platform_role", sa.String(100), nullable=False),
            sa.Column("assigned_at", sa.DateTime(), server_default=sa.text("NOW()")),
            sa.Column("assigned_by_id", sa.Integer(),
                      sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default="true"),
            sa.UniqueConstraint("persona_id", "platform_role", name="uq_persona_platform_role"),
        )


def _migrate_kernel_data_to_persona() -> None:
    """Migra datos desde user_* kernel tables a persona_* si existen."""
    conn = op.get_bind()

    # user_ministries → persona_ministries
    if _table_exists("user_ministries"):
        conn.execute(sa.text("""
            INSERT INTO persona_ministries (persona_id, ministry, is_primary, recognized_at, recognized_by, notes)
            SELECT p.id, um.ministry, um.is_primary, um.recognized_at, um.recognized_by, um.notes
            FROM user_ministries um
            JOIN personas p ON p.user_id = um.user_id
            ON CONFLICT (persona_id, ministry) DO NOTHING
        """))

    # user_church_roles → persona_church_roles
    if _table_exists("user_church_roles"):
        conn.execute(sa.text("""
            INSERT INTO persona_church_roles (persona_id, church_role, assigned_at, assigned_by, notes)
            SELECT p.id, ur.church_role, ur.assigned_at, ur.assigned_by, ur.notes
            FROM user_church_roles ur
            JOIN personas p ON p.user_id = ur.user_id
            ON CONFLICT (persona_id) DO NOTHING
        """))

    # user_role_history → persona_role_history
    if _table_exists("user_role_history"):
        conn.execute(sa.text("""
            INSERT INTO persona_role_history (persona_id, from_role, to_role, changed_at, changed_by, reason)
            SELECT p.id, rh.from_role, rh.to_role, rh.changed_at, rh.changed_by, rh.reason
            FROM user_role_history rh
            JOIN personas p ON p.user_id = rh.user_id
        """))

    # user_platform_roles → persona_platform_roles
    if _table_exists("user_platform_roles"):
        conn.execute(sa.text("""
            INSERT INTO persona_platform_roles (persona_id, role_id, assigned_at, assigned_by, expires_at, notes, is_active)
            SELECT p.id, upr.role_id, upr.assigned_at, upr.assigned_by, upr.expires_at, upr.notes, upr.is_active
            FROM user_platform_roles upr
            JOIN personas p ON p.user_id = upr.user_id
            ON CONFLICT (persona_id, role_id) DO NOTHING
        """))

    # Sincronizar estado_vital desde users.is_active para personas con user_id
    conn.execute(sa.text("""
        UPDATE personas p
        SET estado_vital = CASE WHEN u.is_active THEN 'ACTIVO' ELSE 'INACTIVO' END
        FROM users u
        WHERE p.user_id = u.id AND p.estado_vital IS NULL
    """))
    # Personas sin user_id → ACTIVO por defecto
    conn.execute(sa.text("""
        UPDATE personas SET estado_vital = 'ACTIVO' WHERE estado_vital IS NULL
    """))


# ──────────────────────────────────────────────────────────────────────────────
# DOWNGRADE (no-op — destructivo por diseño)
# ──────────────────────────────────────────────────────────────────────────────

def downgrade() -> None:
    pass
