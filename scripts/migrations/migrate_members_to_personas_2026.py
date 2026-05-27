#!/usr/bin/env python3
"""
Migration: members (Integer PK) → personas (UUID PK).

Crea la tabla personas, migra todos los datos desde members,
y actualiza todas las FK de child tables para referenciar personas.id.

Uso:
    cd /root/ccf && ./venv/bin/python scripts/migrations/migrate_members_to_personas_2026.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../..")

from sqlalchemy import text
from backend.core.database import engine, SessionLocal


def table_exists(table: str) -> bool:
    with engine.connect() as conn:
        r = conn.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_name = :t"),
            {"t": table},
        )
        return r.first() is not None


def column_exists(table: str, column: str) -> bool:
    with engine.connect() as conn:
        r = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = :t AND column_name = :c"
            ),
            {"t": table, "c": column},
        )
        return r.first() is not None


def fk_exists(table: str, column: str) -> bool:
    """Check if a FK constraint exists on a given column."""
    with engine.connect() as conn:
        r = conn.execute(
            text(
                "SELECT 1 FROM information_schema.key_column_usage "
                "WHERE table_name = :t AND column_name = :c "
                "AND constraint_name LIKE '%fkey'"
            ),
            {"t": table, "c": column},
        )
        return r.first() is not None


def drop_fk_if_exists(table: str, column: str):
    """Drop FK constraint on column if it exists."""
    with engine.connect() as conn:
        r = conn.execute(
            text(
                "SELECT constraint_name FROM information_schema.key_column_usage "
                "WHERE table_name = :t AND column_name = :c "
                "AND constraint_name LIKE '%fkey'"
            ),
            {"t": table, "c": column},
        )
        row = r.first()
        if row:
            fk_name = row[0]
            conn.execute(text(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {fk_name}"))


def migrate_fk_column(
    db,
    table: str,
    old_col: str,
    new_col: str,
    *,
    nullable: bool = False,
    on_delete: str = "CASCADE",
):
    """Migrate a child table FK from member_id (Integer) to persona_id (UUID)."""
    if not column_exists(table, old_col):
        print(f"    → {table}.{old_col} doesn't exist, skipping...")
        return

    if column_exists(table, new_col):
        print(f"    → {table}.{new_col} already exists, skipping...")
        return

    print(f"    → Migrating {table}.{old_col} → {new_col}")

    # Add new UUID column
    nullable_sql = "" if not nullable else ""
    db.execute(text(f"ALTER TABLE {table} ADD COLUMN {new_col} UUID"))

    # Update from mapping
    db.execute(text(f"""
        UPDATE {table} t
        SET {new_col} = m.new_persona_id
        FROM member_to_persona_mapping m
        WHERE t.{old_col} = m.old_member_id
    """))

    # Drop old FK if exists
    drop_fk_if_exists(table, old_col)

    # Drop old column
    db.execute(text(f"ALTER TABLE {table} DROP COLUMN {old_col}"))

    # Add FK constraint
    if not nullable:
        db.execute(text(f"ALTER TABLE {table} ALTER COLUMN {new_col} SET NOT NULL"))
    db.execute(text(
        f"ALTER TABLE {table} ADD FOREIGN KEY ({new_col}) REFERENCES personas(id) ON DELETE {on_delete}"
    ))
    db.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{table}_{new_col} ON {table}({new_col})"))


def run():
    db = SessionLocal()
    total_steps = 30
    step = 0

    # ── Step 1: Create mapping table (old member_id -> new persona UUID) ──
    step += 1
    if not table_exists("personas"):
        print(f"[{step}/{total_steps}] Creating member_to_persona_mapping...")
        db.execute(text("""
            CREATE TEMP TABLE member_to_persona_mapping AS
            SELECT id AS old_member_id, gen_random_uuid() AS new_persona_id
            FROM members
        """))
        count = db.execute(text("SELECT COUNT(*) FROM member_to_persona_mapping")).scalar()
        print(f"    → Mapped {count} members")
    else:
        print(f"[{step}/{total_steps}] personas table already exists, skipping mapping...")

    # ── Step 2: Create personas table ──
    step += 1
    if not table_exists("personas"):
        print(f"[{step}/{total_steps}] Creating personas table...")
        db.execute(text("""
            CREATE TABLE personas (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id INTEGER REFERENCES users(id) ON DELETE SET NULL UNIQUE,
                family_id INTEGER REFERENCES families(id) ON DELETE SET NULL,
                nombre_completo VARCHAR(300) NOT NULL,
                email VARCHAR(200),
                telefono VARCHAR(50),
                church_role VARCHAR(100) DEFAULT 'Miembro',
                estado_vital VARCHAR(20) DEFAULT 'ACTIVO',
                datos_extra JSONB DEFAULT '{}'::jsonb,
                tags JSON DEFAULT '[]'::json,
                origen_estrategia_id INTEGER REFERENCES evangelism_strategies(id) ON DELETE SET NULL,
                origen_grupo_id INTEGER REFERENCES glory_houses(id) ON DELETE SET NULL,
                origen_fecha TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """))
        db.execute(text("CREATE INDEX idx_personas_email ON personas(email)"))
        db.execute(text("CREATE INDEX idx_personas_telefono ON personas(telefono)"))
        db.execute(text("CREATE INDEX idx_personas_estado_vital ON personas(estado_vital)"))
    else:
        print(f"[{step}/{total_steps}] personas table already exists, skipping...")

    # ── Step 3: Migrate data from members to personas ──
    step += 1
    existing = db.execute(text("SELECT COUNT(*) FROM personas")).scalar()
    if existing == 0:
        print(f"[{step}/{total_steps}] Migrating member data to personas...")
        db.execute(text("""
            INSERT INTO personas (
                id, user_id, family_id,
                nombre_completo, email, telefono, church_role,
                estado_vital, datos_extra,
                tags, origen_estrategia_id, origen_grupo_id, origen_fecha,
                created_at, updated_at
            )
            SELECT
                m2p.new_persona_id,
                m.user_id, m.family_id,
                CONCAT(m.first_name, ' ', COALESCE(m.last_name, '')),
                m.email, COALESCE(m.phone, m.mobile_phone, m.other_phone), m.church_role,
                CASE
                    WHEN m.unregistration_date IS NOT NULL THEN 'INACTIVO'
                    ELSE 'ACTIVO'
                END,
                jsonb_build_object(
                    'first_name', m.first_name,
                    'last_name', m.last_name,
                    'second_name', m.second_name,
                    'second_last_name', m.second_last_name,
                    'id_type', m.id_type,
                    'id_number', m.id_number,
                    'marital_status', m.marital_status,
                    'birth_country', m.birth_country,
                    'landline_phone', m.landline_phone,
                    'other_phone', m.other_phone,
                    'mobile_phone', m.mobile_phone,
                    'address', m.address,
                    'housing_type', m.housing_type,
                    'education_level', m.education_level,
                    'education_status', m.education_status,
                    'profession', m.profession,
                    'economic_sector', m.economic_sector,
                    'blood_type', m.blood_type,
                    'medical_notes', m.medical_notes,
                    'optional_info', m.optional_info,
                    'registration_reason', m.registration_reason,
                    'unregistration_reason', m.unregistration_reason,
                    'registration_date', m.registration_date::text,
                    'unregistration_date', m.unregistration_date::text,
                    'responsible_adult_name', m.responsible_adult_name,
                    'responsible_adult_contact', m.responsible_adult_contact,
                    'guardian_name', m.guardian_name,
                    'guardian_contact', m.guardian_contact,
                    'sex', m.sex,
                    'is_baptized', m.is_baptized,
                    'spiritual_status', m.spiritual_status,
                    'last_group_attendance', m.last_group_attendance::text,
                    'last_meeting_attendance', m.last_meeting_attendance::text,
                    'membership_type', m.membership_type,
                    'attendance_type', m.attendance_type,
                    'group_name', m.group_name,
                    'campus', m.campus,
                    'church_join_date', m.church_join_date::text,
                    'colombian_department_id', m.colombian_department_id,
                    'city', m.city,
                    'qr_token', m.qr_token,
                    'birthday', m.birthday::text,
                    'role_in_family', m.role_in_family,
                    'talents', m.talents,
                    'spiritual_gifts', m.spiritual_gifts,
                    'pastoral_notes', m.pastoral_notes
                ),
                m.tags,
                m.origen_estrategia_id, m.origen_grupo_id, m.origen_fecha,
                m.created_at, m.updated_at
            FROM members m
            JOIN member_to_persona_mapping m2p ON m.id = m2p.old_member_id
        """))
        count = db.execute(text("SELECT COUNT(*) FROM personas")).scalar()
        print(f"    → {count} personas created")
    else:
        print(f"[{step}/{total_steps}] personas already has data ({existing} rows), skipping...")

    # ── Step 4-19: Migrate FK columns in child tables ──
    fk_migrations = [
        # (table, old_column, new_column, nullable?, on_delete)
        ("event_assignments", "member_id", "persona_id", False, "CASCADE"),
        ("event_attendances", "member_id", "persona_id", False, "CASCADE"),
        ("counseling_tickets", "member_id", "persona_id", False, "NO ACTION"),
        ("member_positions", "member_id", "persona_id", False, "CASCADE"),
        # Consolidation tables — new column names per kernel schema:
        ("consolidation_cases", "member_id", "persona_id", False, "CASCADE"),
        ("consolidation_assignments", "assigned_by_member_id", "assigned_by_id", False, "CASCADE"),
        ("consolidation_assignments", "assigned_to_member_id", "assigned_to_id", False, "CASCADE"),
        ("consolidation_interactions", "performed_by_member_id", "performed_by_id", False, "CASCADE"),
        ("donations", "member_id", "persona_id", True, "NO ACTION"),
        ("crm_tasks", "member_id", "persona_id", True, "NO ACTION"),
        ("volunteer_shifts", "member_id", "persona_id", False, "NO ACTION"),
        ("communication_logs", "member_id", "persona_id", False, "CASCADE"),
        ("member_roles", "member_id", "persona_id", False, "CASCADE"),
        ("member_ministries", "member_id", "persona_id", False, "CASCADE"),
        ("ministries", "leader_id", "leader_persona_id", True, "NO ACTION"),
        ("glory_houses", "leader_id", "leader_persona_id", True, "SET NULL"),
        ("glory_houses", "assistant_id", "assistant_persona_id", True, "SET NULL"),
        ("glory_houses", "host_id", "host_persona_id", True, "SET NULL"),
        ("glory_house_members", "member_id", "persona_id", False, "CASCADE"),
        ("glory_house_sessions", "reported_by_member_id", "reported_by_persona_id", True, "SET NULL"),
        ("glory_house_attendance", "member_id", "persona_id", False, "CASCADE"),
        ("registros_seguimiento", "realizado_por_member_id", "realizado_por_persona_id", True, "SET NULL"),
        ("historial_embudo", "persona_id", "persona_uuid", False, "CASCADE"),
    ]

    for table, old_col, new_col, nullable, on_delete in fk_migrations:
        step += 1
        if not table_exists(table):
            print(f"[{step}/{total_steps}] {table} doesn't exist, skipping...")
            continue
        print(f"[{step}/{total_steps}] Migrating {table}.{old_col} → {new_col}...")
        migrate_fk_column(db, table, old_col, new_col, nullable=nullable, on_delete=on_delete)

    # ── Special case: consolidation_cases.assigned_pastor_id (same name, new type) ──
    step += 1
    if table_exists("consolidation_cases") and column_exists("consolidation_cases", "assigned_pastor_id"):
        col_type = db.execute(text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'consolidation_cases' AND column_name = 'assigned_pastor_id'"
        )).scalar()
        if col_type == "integer":
            print(f"[{step}/{total_steps}] Replacing consolidation_cases.assigned_pastor_id (int→UUID)...")
            db.execute(text("ALTER TABLE consolidation_cases DROP COLUMN IF EXISTS assigned_pastor_id"))
            db.execute(text("ALTER TABLE consolidation_cases ADD COLUMN assigned_pastor_id UUID REFERENCES personas(id) ON DELETE SET NULL"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_consolidation_cases_assigned_pastor_id ON consolidation_cases(assigned_pastor_id)"))
        else:
            print(f"[{step}/{total_steps}] consolidation_cases.assigned_pastor_id already UUID, skipping...")
    else:
        print(f"[{step}/{total_steps}] consolidation_cases.assigned_pastor_id doesn't exist, skipping...")

    # ── Special case: consolidation_cases.assigned_leader_id (same name, new type) ──
    step += 1
    if table_exists("consolidation_cases") and column_exists("consolidation_cases", "assigned_leader_id"):
        col_type = db.execute(text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'consolidation_cases' AND column_name = 'assigned_leader_id'"
        )).scalar()
        if col_type == "integer":
            print(f"[{step}/{total_steps}] Replacing consolidation_cases.assigned_leader_id (int→UUID)...")
            db.execute(text("ALTER TABLE consolidation_cases DROP COLUMN IF EXISTS assigned_leader_id"))
            db.execute(text("ALTER TABLE consolidation_cases ADD COLUMN assigned_leader_id UUID REFERENCES personas(id) ON DELETE SET NULL"))
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_consolidation_cases_assigned_leader_id ON consolidation_cases(assigned_leader_id)"))
        else:
            print(f"[{step}/{total_steps}] consolidation_cases.assigned_leader_id already UUID, skipping...")
    else:
        print(f"[{step}/{total_steps}] consolidation_cases.assigned_leader_id doesn't exist, skipping...")

    # ── Special case: consolidation_cases.id int→UUID, source_campaign ──
    step += 1
    if table_exists("consolidation_cases") and column_exists("consolidation_cases", "id"):
        col_type = db.execute(text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'consolidation_cases' AND column_name = 'id'"
        )).scalar()
        if col_type == "integer":
            print(f"[{step}/{total_steps}] Migrating consolidation_cases.id (int→UUID) + adding source_campaign...")
            # Drop PK constraint so we can change column type
            db.execute(text("ALTER TABLE consolidation_cases DROP CONSTRAINT IF EXISTS consolidation_cases_pkey CASCADE"))
            # Drop all FK constraints referencing this table
            fk_names = db.execute(text("""
                SELECT conname FROM pg_constraint WHERE confrelid = 'consolidation_cases'::regclass
                AND contype = 'f'
            """)).scalars().all()
            for fk in fk_names:
                db.execute(text(f"ALTER TABLE consolidation_cases DROP CONSTRAINT IF EXISTS {fk} CASCADE"))
            # Change id to UUID (table is empty, so no data conversion needed)
            db.execute(text("ALTER TABLE consolidation_cases ALTER COLUMN id TYPE UUID USING gen_random_uuid()"))
            db.execute(text("ALTER TABLE consolidation_cases ALTER COLUMN id SET DEFAULT gen_random_uuid()"))
            db.execute(text("ALTER TABLE consolidation_cases ADD PRIMARY KEY (id)"))
            # Add source_campaign
            if not column_exists("consolidation_cases", "source_campaign"):
                db.execute(text("ALTER TABLE consolidation_cases ADD COLUMN source_campaign VARCHAR(200)"))
        else:
            print(f"[{step}/{total_steps}] consolidation_cases.id already UUID, skipping...")
    else:
        print(f"[{step}/{total_steps}] consolidation_cases doesn't exist, skipping...")

    # ── Final step: Verify ──
    step += 1
    print(f"[{step}/{total_steps}] Verifying migration...")
    persona_count = db.execute(text("SELECT COUNT(*) FROM personas")).scalar()
    print(f"    → Personas: {persona_count}")

    # Keep members table as fallback (don't drop yet)
    print("    → members table preserved as fallback (not dropped)")

    db.commit()
    print("\nMigration complete!")
    print("NOTE: members table is preserved. Drop it manually after verification:")
    print("  DROP TABLE members CASCADE;")


if __name__ == "__main__":
    run()
