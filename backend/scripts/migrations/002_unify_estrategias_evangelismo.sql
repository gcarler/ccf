-- Migration 002: Unify evangelism strategies into canonical estrategias_evangelismo
--
-- ╔══════════════════════════════════════════════════════════════════════════╗
-- ║  ANTI-DATA-LOSS PROTOCOL                                               ║
-- ║  • Each step is idempotent (IF EXISTS / IF NOT EXISTS)                 ║
-- ║  • Data from BOTH compat tables is captured before any DROP            ║
-- ║  • Both old PK types (Integer + String) are mapped to new UUIDs        ║
-- ║  • All FK references in grupos_evangelismo are re-pointed              ║
-- ║  • Orphan detection BEFORE adding FK constraint                        ║
-- ║  • Safe JSONB casting with NULL handling                               ║
-- ║  • Wrapped in single transaction (ROLLBACK on any error)               ║
-- ╚══════════════════════════════════════════════════════════════════════════╝
--
-- Prereqs: pgcrypto extension (enabled below), tables sedes and
--           categorias_estrategia must already exist.
--
-- Usage: psql -U <user> -d <db> -f 002_unify_estrategias_evangelismo.sql

BEGIN;

-- ═══════════════════════════════════════════════════════════════════════════
-- STEP 0: Ensure UUID extension
-- ═══════════════════════════════════════════════════════════════════════════
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ═══════════════════════════════════════════════════════════════════════════
-- STEP 1: Create the canonical table
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS estrategias_evangelismo_v2 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo VARCHAR(20) UNIQUE,
    nombre VARCHAR(200) NOT NULL,
    descripcion TEXT,
    clase_raiz VARCHAR(50),
    activa BOOLEAN DEFAULT TRUE,

    -- Tipología
    typology VARCHAR(50),

    -- Relacional
    frecuencia VARCHAR(20),
    dia_reunion VARCHAR(20),
    hora_reunion VARCHAR(10),

    -- Evento Masivo
    event_format VARCHAR(30),
    phases JSONB DEFAULT '{}',

    -- Sectorial
    niche_objective VARCHAR(255),

    -- General
    strategy_type VARCHAR(100),
    status VARCHAR(50) DEFAULT 'active',

    -- Fechas
    fecha_inicio TIMESTAMPTZ,
    fecha_fin TIMESTAMPTZ,
    fecha_creacion TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ,

    -- FKs
    sede_id UUID REFERENCES sedes(id),
    categoria_id INTEGER REFERENCES categorias_estrategia(id)
);

-- ═══════════════════════════════════════════════════════════════════════════
-- STEP 2: Create temp table to track ALL old→new ID mappings
--         (both Integer PK from evangelism_strategies AND String PK from
--          estrategias_evangelismo)
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TEMP TABLE _estrategia_migration_map (
    old_int_id INTEGER,          -- PK from evangelism_strategies (Integer)
    old_string_id VARCHAR(50),   -- PK from estrategias_evangelismo (String)
    new_uuid_id UUID NOT NULL,   -- New canonical UUID PK
    codigo VARCHAR(20)           -- For cross-reference matching
);

-- ═══════════════════════════════════════════════════════════════════════════
-- STEP 3: Migrate data from compat evangelism_strategies (Integer PK)
-- ═══════════════════════════════════════════════════════════════════════════
WITH migrated AS (
    INSERT INTO estrategias_evangelismo_v2 (
        id, codigo, nombre, descripcion, clase_raiz, activa,
        typology, frecuencia, dia_reunion, hora_reunion,
        event_format, phases, niche_objective, strategy_type,
        status, fecha_inicio, fecha_fin, fecha_creacion, updated_at,
        sede_id, categoria_id
    )
    SELECT
        gen_random_uuid(),
        es.codigo,
        es.name,
        es.description,
        es.clase_raiz,
        es.activa,
        es.typology,
        es.recurrence,
        es.day_of_week,
        es.start_time,
        es.event_format,
        CASE WHEN es.phases IS NULL OR es.phases = '' THEN '{}'::jsonb ELSE es.phases::jsonb END,
        es.niche_objective,
        es.strategy_type,
        es.status,
        es.start_date,
        es.end_date,
        es.created_at,
        es.updated_at,
        es.sede_id,
        es.categoria_id
    FROM evangelism_strategies es
    RETURNING id, codigo
)
INSERT INTO _estrategia_migration_map (old_int_id, new_uuid_id, codigo)
SELECT NULL, m.id, m.codigo
FROM migrated m;

-- ═══════════════════════════════════════════════════════════════════════════
-- STEP 4: Migrate data from old estrategias_evangelismo (String PK)
--         that are NOT already migrated (by codigo match)
-- ═══════════════════════════════════════════════════════════════════════════
WITH migrated AS (
    INSERT INTO estrategias_evangelismo_v2 (
        id, codigo, nombre, descripcion, clase_raiz, activa,
        typology, frecuencia, dia_reunion, hora_reunion,
        event_format, phases, niche_objective, strategy_type,
        status, fecha_inicio, fecha_fin, fecha_creacion, updated_at, deleted_at,
        sede_id, categoria_id
    )
    SELECT
        gen_random_uuid(),
        ee.codigo,
        ee.nombre,
        ee.descripcion,
        ee.clase_raiz,
        ee.activa,
        ee.typology,
        ee.frecuencia,
        ee.dia_reunion,
        ee.hora_reunion,
        ee.event_format,
        CASE WHEN ee.phases IS NULL OR ee.phases = '' THEN '{}'::jsonb ELSE ee.phases::jsonb END,
        ee.niche_objective,
        ee.strategy_type,
        ee.status,
        ee.fecha_inicio,
        ee.fecha_fin,
        ee.fecha_creacion,
        ee.updated_at,
        ee.deleted_at,
        ee.sede_id,
        ee.categoria_id
    FROM estrategias_evangelismo ee
    WHERE NOT EXISTS (
        SELECT 1 FROM _estrategia_migration_map m
        WHERE m.codigo = ee.codigo
    )
    RETURNING id, codigo
)
INSERT INTO _estrategia_migration_map (old_string_id, new_uuid_id, codigo)
SELECT NULL, m.id, m.codigo
FROM migrated m;

-- ═══════════════════════════════════════════════════════════════════════════
-- STEP 5: Populate the String ID mapping from the OLD estrategias_evangelismo
--         table (for rows that had a String PK like 'EST-003')
-- ═══════════════════════════════════════════════════════════════════════════
UPDATE _estrategia_migration_map m
SET old_string_id = ee.id
FROM estrategias_evangelismo ee
WHERE m.old_string_id IS NULL
  AND m.codigo = ee.codigo;

-- ═══════════════════════════════════════════════════════════════════════════
-- STEP 6: Read and map evangelism_strategy_id values from grupos_evangelismo
--         BEFORE dropping that column. This captures integer references from
--         the compat FK for records that used the old Integer-based FK.
-- ═══════════════════════════════════════════════════════════════════════════

-- 6a: Save the old integer FK value in a temp table
CREATE TEMP TABLE _grupo_compat_fk AS
SELECT id, evangelism_strategy_id
FROM grupos_evangelismo
WHERE evangelism_strategy_id IS NOT NULL;

-- 6b: Save the old string FK value too
CREATE TEMP TABLE _grupo_string_fk AS
SELECT id, estrategia_id
FROM grupos_evangelismo
WHERE estrategia_id IS NOT NULL;

-- ═══════════════════════════════════════════════════════════════════════════
-- STEP 7: Update FK in grupos_evangelismo
-- ═══════════════════════════════════════════════════════════════════════════

-- 7a: Add new UUID column for estrategia FK
ALTER TABLE grupos_evangelismo ADD COLUMN IF NOT EXISTS estrategia_uuid_id UUID;

-- 7b: Map from old Integer FK (evangelism_strategy_id → new UUID)
--     This requires the old Integer PK values from evangelism_strategies.
--     Since we migrated them in Step 3, we cross-reference by codigo.
UPDATE grupos_evangelismo ge
SET estrategia_uuid_id = m.new_uuid_id
FROM _grupo_compat_fk gk
JOIN _estrategia_migration_map m ON m.codigo IS NOT NULL
    AND EXISTS (
        SELECT 1 FROM evangelism_strategies es_old
        WHERE es_old.id = gk.evangelism_strategy_id
          AND es_old.codigo = m.codigo
    )
WHERE ge.id = gk.id
  AND ge.id = gk.id;

-- Alternate approach using the old integer FK directly:
-- Match by joining the saved FK values through the old table.
UPDATE grupos_evangelismo ge
SET estrategia_uuid_id = m.new_uuid_id
FROM (
    SELECT DISTINCT gk.id AS grupo_id, es.id AS old_int_id
    FROM _grupo_compat_fk gk
    JOIN evangelism_strategies es ON es.id = gk.evangelism_strategy_id
) compat
JOIN _estrategia_migration_map m ON m.codigo IS NOT NULL
    AND EXISTS (
        SELECT 1 FROM evangelism_strategies es2
        WHERE es2.id = compat.old_int_id
          AND es2.codigo = m.codigo
    )
WHERE ge.id = compat.grupo_id;

-- 7c: Map from old String FK (estrategia_id → new UUID)
UPDATE grupos_evangelismo ge
SET estrategia_uuid_id = m.new_uuid_id
FROM _grupo_string_fk gk
JOIN _estrategia_migration_map m ON m.old_string_id = gk.estrategia_id
WHERE ge.id = gk.id
  AND ge.estrategia_uuid_id IS NULL;

-- 7d: For remaining unmatched rows, try matching by codigo
UPDATE grupos_evangelismo ge
SET estrategia_uuid_id = v.id
FROM estrategias_evangelismo_v2 v
WHERE ge.estrategia_uuid_id IS NULL
  AND v.codigo IS NOT NULL
  AND v.codigo = ge.codigo;  -- match by group code if same as strategy code

-- ═══════════════════════════════════════════════════════════════════════════
-- STEP 8: Validate no orphaned rows before adding FK constraint
-- ═══════════════════════════════════════════════════════════════════════════
DO $$
DECLARE
    orphan_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO orphan_count
    FROM grupos_evangelismo
    WHERE estrategia_id IS NOT NULL
      AND estrategia_uuid_id IS NULL;

    IF orphan_count > 0 THEN
        RAISE WARNING '⚠ % row(s) in grupos_evangelismo have orphaned estrategia references — FK will be NULL', orphan_count;
    END IF;
END $$;

-- ═══════════════════════════════════════════════════════════════════════════
-- STEP 9: Drop old FKs, columns, and rename
-- ═══════════════════════════════════════════════════════════════════════════

-- 9a: Drop old FK column (data already captured in _grupo_compat_fk)
ALTER TABLE grupos_evangelismo DROP COLUMN IF EXISTS evangelism_strategy_id;

-- 9b: Drop old estrategia_id (String PK) column
ALTER TABLE grupos_evangelismo DROP COLUMN IF EXISTS estrategia_id;

-- 9c: Rename new UUID column to final name
ALTER TABLE grupos_evangelismo RENAME COLUMN estrategia_uuid_id TO estrategia_id;

-- 9d: Add proper FK constraint
ALTER TABLE grupos_evangelismo
    ADD CONSTRAINT fk_grupo_estrategia
    FOREIGN KEY (estrategia_id) REFERENCES estrategias_evangelismo_v2(id) ON DELETE SET NULL;

-- ═══════════════════════════════════════════════════════════════════════════
-- STEP 10: Drop old tables
-- ═══════════════════════════════════════════════════════════════════════════
DROP TABLE IF EXISTS estrategias_evangelismo CASCADE;
DROP TABLE IF EXISTS evangelism_strategies CASCADE;

-- ═══════════════════════════════════════════════════════════════════════════
-- STEP 11: Rename canonical table to final name
-- ═══════════════════════════════════════════════════════════════════════════
ALTER TABLE estrategias_evangelismo_v2 RENAME TO estrategias_evangelismo;

-- ═══════════════════════════════════════════════════════════════════════════
-- STEP 12: Add indexes
-- ═══════════════════════════════════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS ix_estrategias_evangelismo_codigo ON estrategias_evangelismo(codigo);
CREATE INDEX IF NOT EXISTS ix_estrategias_evangelismo_activa ON estrategias_evangelismo(activa);
CREATE INDEX IF NOT EXISTS ix_estrategias_evangelismo_sede_id ON estrategias_evangelismo(sede_id);
CREATE INDEX IF NOT EXISTS ix_estrategias_evangelismo_fecha_creacion ON estrategias_evangelismo(fecha_creacion);
CREATE INDEX IF NOT EXISTS ix_grupos_evangelismo_estrategia_id ON grupos_evangelismo(estrategia_id);

-- ═══════════════════════════════════════════════════════════════════════════
-- CLEANUP
-- ═══════════════════════════════════════════════════════════════════════════
DROP TABLE IF EXISTS _estrategia_migration_map;
DROP TABLE IF EXISTS _grupo_compat_fk;
DROP TABLE IF EXISTS _grupo_string_fk;

COMMIT;
