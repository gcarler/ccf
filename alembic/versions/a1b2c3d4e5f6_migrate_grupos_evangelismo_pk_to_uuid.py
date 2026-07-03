"""Migrate grupos_evangelismo PK from Integer to UUID

Revision ID: a1b2c3d4e5f6
Revises: e47a67a4c954
Create Date: 2026-06-11 00:00:00.000000
"""

from alembic import op

revision = 'a1b2c3d4e5f6'
down_revision = '5ff8ddf9dce0'
branch_labels = None
depends_on = None


def upgrade():
    # ── Step 1: Add new UUID columns ──────────────────────────────────────────
    op.execute("ALTER TABLE grupos_evangelismo ADD COLUMN new_id UUID NOT NULL DEFAULT gen_random_uuid()")
    op.execute("ALTER TABLE sesiones_grupo ADD COLUMN new_grupo_id UUID")
    op.execute("ALTER TABLE grupo_participantes ADD COLUMN new_grupo_id UUID")
    op.execute("ALTER TABLE personas ADD COLUMN new_origen_grupo_id UUID")
    op.execute("ALTER TABLE grupos_evangelismo ADD COLUMN new_parent_group_id UUID")

    # ── Step 2: Populate UUID FKs from current integer join ──────────────────
    op.execute("""
        UPDATE sesiones_grupo sg
        SET new_grupo_id = ge.new_id
        FROM grupos_evangelismo ge
        WHERE sg.grupo_id = ge.id
    """)
    op.execute("""
        UPDATE grupo_participantes gp
        SET new_grupo_id = ge.new_id
        FROM grupos_evangelismo ge
        WHERE gp.grupo_id = ge.id
    """)
    op.execute("""
        UPDATE personas p
        SET new_origen_grupo_id = ge.new_id
        FROM grupos_evangelismo ge
        WHERE p.origen_grupo_id = ge.id
    """)
    op.execute("""
        UPDATE grupos_evangelismo child
        SET new_parent_group_id = parent.new_id
        FROM grupos_evangelismo parent
        WHERE child.parent_group_id = parent.id
    """)

    # ── Step 3: Drop indexes on old integer FK columns ────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_personas_origen_grupo_id")
    op.execute("DROP INDEX IF EXISTS ix_grupos_evangelismo_parent_group_id")
    op.execute("DROP INDEX IF EXISTS idx_participantes_grupo_id")
    op.execute("DROP INDEX IF EXISTS idx_sesiones_grupo_id")

    # ── Step 4: Drop old FK constraints ──────────────────────────────────────
    op.execute("ALTER TABLE sesiones_grupo DROP CONSTRAINT IF EXISTS sesiones_grupo_grupo_id_fkey")
    op.execute("ALTER TABLE grupo_participantes DROP CONSTRAINT IF EXISTS grupo_participantes_grupo_id_fkey")
    op.execute("ALTER TABLE personas DROP CONSTRAINT IF EXISTS personas_origen_grupo_id_fkey")
    op.execute("ALTER TABLE grupos_evangelismo DROP CONSTRAINT IF EXISTS grupos_evangelismo_parent_group_id_fkey")

    # ── Step 5: Drop old PK ───────────────────────────────────────────────────
    op.execute("ALTER TABLE grupos_evangelismo DROP CONSTRAINT IF EXISTS grupos_evangelismo_pkey")

    # ── Step 6: Drop old integer columns ─────────────────────────────────────
    op.execute("ALTER TABLE sesiones_grupo DROP COLUMN grupo_id")
    op.execute("ALTER TABLE grupo_participantes DROP COLUMN grupo_id")
    op.execute("ALTER TABLE personas DROP COLUMN origen_grupo_id")
    op.execute("ALTER TABLE grupos_evangelismo DROP COLUMN parent_group_id")
    op.execute("ALTER TABLE grupos_evangelismo DROP COLUMN id")

    # ── Step 7: Rename new columns to canonical names ─────────────────────────
    op.execute("ALTER TABLE grupos_evangelismo RENAME COLUMN new_id TO id")
    op.execute("ALTER TABLE sesiones_grupo RENAME COLUMN new_grupo_id TO grupo_id")
    op.execute("ALTER TABLE grupo_participantes RENAME COLUMN new_grupo_id TO grupo_id")
    op.execute("ALTER TABLE personas RENAME COLUMN new_origen_grupo_id TO origen_grupo_id")
    op.execute("ALTER TABLE grupos_evangelismo RENAME COLUMN new_parent_group_id TO parent_group_id")

    # ── Step 8: Re-add NOT NULL where required ────────────────────────────────
    op.execute("ALTER TABLE sesiones_grupo ALTER COLUMN grupo_id SET NOT NULL")
    op.execute("ALTER TABLE grupo_participantes ALTER COLUMN grupo_id SET NOT NULL")

    # ── Step 9: Restore PK ────────────────────────────────────────────────────
    op.execute("ALTER TABLE grupos_evangelismo ADD PRIMARY KEY (id)")

    # ── Step 10: Restore FK constraints ──────────────────────────────────────
    op.execute("""
        ALTER TABLE sesiones_grupo ADD CONSTRAINT sesiones_grupo_grupo_id_fkey
        FOREIGN KEY (grupo_id) REFERENCES grupos_evangelismo(id) ON DELETE CASCADE
    """)
    op.execute("""
        ALTER TABLE grupo_participantes ADD CONSTRAINT grupo_participantes_grupo_id_fkey
        FOREIGN KEY (grupo_id) REFERENCES grupos_evangelismo(id) ON DELETE CASCADE
    """)
    op.execute("""
        ALTER TABLE personas ADD CONSTRAINT personas_origen_grupo_id_fkey
        FOREIGN KEY (origen_grupo_id) REFERENCES grupos_evangelismo(id) ON DELETE SET NULL
    """)
    op.execute("""
        ALTER TABLE grupos_evangelismo ADD CONSTRAINT grupos_evangelismo_parent_group_id_fkey
        FOREIGN KEY (parent_group_id) REFERENCES grupos_evangelismo(id) ON DELETE SET NULL
    """)

    # ── Step 11: Restore indexes ──────────────────────────────────────────────
    op.execute("CREATE INDEX ix_personas_origen_grupo_id ON personas(origen_grupo_id)")
    op.execute("CREATE INDEX ix_grupos_evangelismo_parent_group_id ON grupos_evangelismo(parent_group_id)")
    op.execute("CREATE INDEX idx_participantes_grupo_id ON grupo_participantes(grupo_id)")
    op.execute("CREATE INDEX idx_sesiones_grupo_id ON sesiones_grupo(grupo_id)")

    # ── Step 12: Default for future inserts ───────────────────────────────────
    op.execute("ALTER TABLE grupos_evangelismo ALTER COLUMN id SET DEFAULT gen_random_uuid()")


def downgrade():
    # Downgrade not supported — integer PKs cannot be safely restored once dropped
    raise NotImplementedError("Downgrade not supported for UUID PK migration")
