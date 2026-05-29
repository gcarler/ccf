-- =====================================================================
-- MIGRACIÓN UUID: sedes.id INTEGER → UUID (Protocolo 2.F)
-- Afecta 15 tablas hijas
-- =====================================================================

-- PASO 1: Columna UUID temporal en PADRE
ALTER TABLE sedes ADD COLUMN IF NOT EXISTS uuid_id UUID DEFAULT gen_random_uuid();
UPDATE sedes SET uuid_id = gen_random_uuid() WHERE uuid_id IS NULL;

-- PASO 2: Columnas temporales en HIJAS
ALTER TABLE academy_courses ADD COLUMN IF NOT EXISTS sede_uuid UUID;
ALTER TABLE agenda_eventos ADD COLUMN IF NOT EXISTS sede_uuid UUID;
ALTER TABLE agenda_recursos ADD COLUMN IF NOT EXISTS sede_uuid UUID;
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS sede_uuid UUID;
ALTER TABLE crm_casos ADD COLUMN IF NOT EXISTS sede_uuid UUID;
ALTER TABLE crm_pipelines ADD COLUMN IF NOT EXISTS sede_uuid UUID;
ALTER TABLE grupos_evangelismo ADD COLUMN IF NOT EXISTS sede_uuid UUID;
ALTER TABLE personas ADD COLUMN IF NOT EXISTS sede_uuid UUID;
ALTER TABLE proyectos ADD COLUMN IF NOT EXISTS sede_uuid UUID;

-- PASO 3: MAPEO MOLECULAR — cruzar por PK entera activa
UPDATE academy_courses SET sede_uuid = sedes.uuid_id FROM sedes WHERE academy_courses.sede_id = sedes.id;
UPDATE agenda_eventos SET sede_uuid = sedes.uuid_id FROM sedes WHERE agenda_eventos.sede_id = sedes.id;
UPDATE agenda_recursos SET sede_uuid = sedes.uuid_id FROM sedes WHERE agenda_recursos.sede_id = sedes.id;
UPDATE auth_users SET sede_uuid = sedes.uuid_id FROM sedes WHERE auth_users.sede_id = sedes.id;
UPDATE crm_casos SET sede_uuid = sedes.uuid_id FROM sedes WHERE crm_casos.sede_id = sedes.id;
UPDATE crm_pipelines SET sede_uuid = sedes.uuid_id FROM sedes WHERE crm_pipelines.sede_id = sedes.id;
UPDATE grupos_evangelismo SET sede_uuid = sedes.uuid_id FROM sedes WHERE grupos_evangelismo.sede_id = sedes.id;
UPDATE personas SET sede_uuid = sedes.uuid_id FROM sedes WHERE personas.sede_id = sedes.id;
UPDATE proyectos SET sede_uuid = sedes.uuid_id FROM sedes WHERE proyectos.sede_id = sedes.id;

-- PASO 4: Validación
DO $$ DECLARE huerfano_count INTEGER; BEGIN
  SELECT count(*) INTO huerfano_count FROM academy_courses WHERE sede_uuid IS NULL;
  IF huerfano_count > 0 THEN RAISE EXCEPTION 'academy_courses: % huérfanos', huerfano_count; END IF;
END $$;

-- PASO 5: Remover constraints y columnas viejas
ALTER TABLE academy_courses DROP CONSTRAINT IF EXISTS academy_courses_sede_id_fkey;
ALTER TABLE agenda_eventos DROP CONSTRAINT IF EXISTS agenda_eventos_sede_id_fkey;
ALTER TABLE crm_casos DROP CONSTRAINT IF EXISTS crm_casos_sede_id_fkey;
ALTER TABLE crm_pipelines DROP CONSTRAINT IF EXISTS crm_pipelines_sede_id_fkey;
ALTER TABLE grupos_evangelismo DROP CONSTRAINT IF EXISTS grupos_evangelismo_sede_id_fkey;
ALTER TABLE personas DROP CONSTRAINT IF EXISTS personas_sede_id_fkey;
ALTER TABLE proyectos DROP CONSTRAINT IF EXISTS proyectos_sede_id_fkey;
ALTER TABLE sedes DROP CONSTRAINT IF EXISTS sedes_pkey CASCADE;

ALTER TABLE academy_courses DROP COLUMN sede_id;
ALTER TABLE agenda_eventos DROP COLUMN sede_id;
ALTER TABLE agenda_recursos DROP COLUMN sede_id;
ALTER TABLE auth_users DROP COLUMN sede_id;
ALTER TABLE crm_casos DROP COLUMN sede_id;
ALTER TABLE crm_pipelines DROP COLUMN sede_id;
ALTER TABLE grupos_evangelismo DROP COLUMN sede_id;
ALTER TABLE personas DROP COLUMN sede_id;
ALTER TABLE proyectos DROP COLUMN sede_id;
ALTER TABLE sedes DROP COLUMN id;

-- PASO 6: Renombrar y recrear PK/FKs
ALTER TABLE sedes RENAME COLUMN uuid_id TO id;
ALTER TABLE sedes ADD CONSTRAINT sedes_pkey PRIMARY KEY (id);

ALTER TABLE academy_courses RENAME COLUMN sede_uuid TO sede_id;
ALTER TABLE academy_courses ADD CONSTRAINT academy_courses_sede_id_fkey FOREIGN KEY (sede_id) REFERENCES sedes(id) ON DELETE CASCADE;

ALTER TABLE agenda_eventos RENAME COLUMN sede_uuid TO sede_id;
ALTER TABLE agenda_eventos ADD CONSTRAINT agenda_eventos_sede_id_fkey FOREIGN KEY (sede_id) REFERENCES sedes(id) ON DELETE CASCADE;

ALTER TABLE agenda_recursos RENAME COLUMN sede_uuid TO sede_id;
ALTER TABLE agenda_recursos ADD CONSTRAINT agenda_recursos_sede_id_fkey FOREIGN KEY (sede_id) REFERENCES sedes(id) ON DELETE CASCADE;

ALTER TABLE auth_users RENAME COLUMN sede_uuid TO sede_id;
ALTER TABLE auth_users ADD CONSTRAINT auth_users_sede_id_fkey FOREIGN KEY (sede_id) REFERENCES sedes(id) ON DELETE CASCADE;

ALTER TABLE crm_casos RENAME COLUMN sede_uuid TO sede_id;
ALTER TABLE crm_casos ADD CONSTRAINT crm_casos_sede_id_fkey FOREIGN KEY (sede_id) REFERENCES sedes(id) ON DELETE CASCADE;

ALTER TABLE crm_pipelines RENAME COLUMN sede_uuid TO sede_id;
ALTER TABLE crm_pipelines ADD CONSTRAINT crm_pipelines_sede_id_fkey FOREIGN KEY (sede_id) REFERENCES sedes(id) ON DELETE CASCADE;

ALTER TABLE grupos_evangelismo RENAME COLUMN sede_uuid TO sede_id;
ALTER TABLE grupos_evangelismo ADD CONSTRAINT grupos_evangelismo_sede_id_fkey FOREIGN KEY (sede_id) REFERENCES sedes(id) ON DELETE CASCADE;

ALTER TABLE personas RENAME COLUMN sede_uuid TO sede_id;
ALTER TABLE personas ADD CONSTRAINT personas_sede_id_fkey FOREIGN KEY (sede_id) REFERENCES sedes(id) ON DELETE CASCADE;

ALTER TABLE proyectos RENAME COLUMN sede_uuid TO sede_id;
ALTER TABLE proyectos ADD CONSTRAINT proyectos_sede_id_fkey FOREIGN KEY (sede_id) REFERENCES sedes(id) ON DELETE CASCADE;
