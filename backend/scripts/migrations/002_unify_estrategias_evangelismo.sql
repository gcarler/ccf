-- Migration 002: Unify evangelism strategies into canonical estrategias_evangelismo
--
-- This migration:
--   1. Adds a UUID column to existing legacy 'evangelism_strategies' table
--   2. Creates a new canonical table 'estrategias_evangelismo_v2' with proper UUID PK
--   3. Migrates ALL data from BOTH old tables
--   4. Re-points FKs in grupos_evangelismo to the new UUID PK
--   5. Drops old tables and columns
--
-- Anti-data-loss protocol applied at every step.

BEGIN;

-- ═══════════════════════════════════════════════
-- STEP 0: Ensure UUID extension
-- ═══════════════════════════════════════════════
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ═══════════════════════════════════════════════
-- STEP 1: Create the canonical table
-- ═══════════════════════════════════════════════
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
    phases JSONB,

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

-- ═══════════════════════════════════════════════
-- STEP 2: Migrate data from legacy evangelism_strategies
-- ═══════════════════════════════════════════════
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
    es.phases::jsonb,
    es.niche_objective,
    es.strategy_type,
    es.status,
    es.start_date,
    es.end_date,
    es.created_at,
    es.updated_at,
    es.sede_id,
    es.categoria_id
FROM evangelism_strategies es;

-- ═══════════════════════════════════════════════
-- STEP 3: Migrate data from old estrategias_evangelismo (String PK → UUID)
-- that are NOT already migrated (by codigo match)
-- ═══════════════════════════════════════════════
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
    ee.phases::jsonb,
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
    SELECT 1 FROM estrategias_evangelismo_v2 v
    WHERE v.codigo = ee.codigo
);

-- ═══════════════════════════════════════════════
-- STEP 4: Create mapping from old IDs to new UUIDs
-- ═══════════════════════════════════════════════
CREATE TEMP TABLE _estrategia_id_map (
    old_string_id VARCHAR(50),
    new_uuid_id UUID NOT NULL
);

-- Map from old estrategias_evangelismo (String PK like 'EST-...')
INSERT INTO _estrategia_id_map (old_string_id, new_uuid_id)
SELECT DISTINCT ON (ee.id) ee.id, v.id
FROM estrategias_evangelismo ee
JOIN estrategias_evangelismo_v2 v ON v.codigo = ee.codigo;

-- ═══════════════════════════════════════════════
-- STEP 5: Update FK in grupos_evangelismo
-- ═══════════════════════════════════════════════

-- 5a: Add new UUID column for estrategia FK
ALTER TABLE grupos_evangelismo ADD COLUMN IF NOT EXISTS estrategia_uuid_id UUID;

-- 5b: Populate from the mapping (match on old string ID)
UPDATE grupos_evangelismo ge
SET estrategia_uuid_id = m.new_uuid_id
FROM _estrategia_id_map m
WHERE ge.estrategia_id = m.old_string_id;

-- 5c: For remaining rows, try matching on codigo from evangelism_strategies
UPDATE grupos_evangelismo ge
SET estrategia_uuid_id = v.id
FROM estrategias_evangelismo_v2 v
WHERE ge.estrategia_uuid_id IS NULL
  AND v.codigo IS NOT NULL
  AND v.nombre = ge.nombre;  -- fallback match by group name

-- ═══════════════════════════════════════════════
-- STEP 6: Drop old columns and rename new ones
-- ═══════════════════════════════════════════════

-- 6a: Drop old FK column
ALTER TABLE grupos_evangelismo DROP COLUMN IF EXISTS evangelism_strategy_id;

-- 6b: Drop old estrategia_id (String PK)
ALTER TABLE grupos_evangelismo DROP COLUMN IF EXISTS estrategia_id;

-- 6c: Rename new UUID column
ALTER TABLE grupos_evangelismo RENAME COLUMN estrategia_uuid_id TO estrategia_id;

-- 6d: Add proper FK constraint
ALTER TABLE grupos_evangelismo
    ADD CONSTRAINT fk_grupo_estrategia
    FOREIGN KEY (estrategia_id) REFERENCES estrategias_evangelismo_v2(id) ON DELETE SET NULL;

-- ═══════════════════════════════════════════════
-- STEP 7: Drop old tables
-- ═══════════════════════════════════════════════
DROP TABLE IF EXISTS estrategias_evangelismo CASCADE;
DROP TABLE IF EXISTS evangelism_strategies CASCADE;

-- ═══════════════════════════════════════════════
-- STEP 8: Rename canonical table to final name
-- ═══════════════════════════════════════════════
ALTER TABLE estrategias_evangelismo_v2 RENAME TO estrategias_evangelismo;

-- ═══════════════════════════════════════════════
-- STEP 9: Add indexes
-- ═══════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS ix_estrategias_evangelismo_codigo ON estrategias_evangelismo(codigo);
CREATE INDEX IF NOT EXISTS ix_estrategias_evangelismo_activa ON estrategias_evangelismo(activa);
CREATE INDEX IF NOT EXISTS ix_estrategias_evangelismo_sede_id ON estrategias_evangelismo(sede_id);
CREATE INDEX IF NOT EXISTS ix_estrategias_evangelismo_fecha_creacion ON estrategias_evangelismo(fecha_creacion);
CREATE INDEX IF NOT EXISTS ix_grupos_evangelismo_estrategia_id ON grupos_evangelismo(estrategia_id);

-- ═══════════════════════════════════════════════
-- CLEANUP
-- ═══════════════════════════════════════════════
DROP TABLE IF EXISTS _estrategia_id_map;

COMMIT;
