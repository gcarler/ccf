-- ============================================================
-- UUID MIGRATION: personas.id Integer → UUID
-- Ejecutar en producción ANTES del deploy de código.
-- 
-- PRECAUCIÓN: Este script modifica 26 FK constraints.
-- Hacer respaldo completo antes de ejecutar:
--   pg_dump ccf_db > backup_$(date +%Y%m%d_%H%M).sql
-- ============================================================

BEGIN;

-- 1. Extensión UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Tabla temporal de mapeo (integer → UUID)
CREATE TEMP TABLE persona_id_map (
    old_id INTEGER PRIMARY KEY,
    new_id UUID DEFAULT uuid_generate_v4()
);

INSERT INTO persona_id_map (old_id)
SELECT id FROM personas;

-- 3. Dropear TODAS las FKs que referencian personas.id
-- (generado dinámicamente desde pg_constraint)
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT conrelid::regclass AS tbl, conname
        FROM pg_constraint
        WHERE confrelid = 'personas'::regclass AND contype = 'f'
    LOOP
        EXECUTE format('ALTER TABLE %s DROP CONSTRAINT %I', r.tbl, r.conname);
    END LOOP;
END $$;

-- 4. Convertir personas.id a UUID
ALTER TABLE personas ALTER COLUMN id DROP DEFAULT;
ALTER TABLE personas ALTER COLUMN id TYPE UUID USING persona_id_map.new_id;
ALTER TABLE personas ALTER COLUMN id SET DEFAULT uuid_generate_v4();

-- 5. Migrar TODAS las columnas FK en cascada
-- (ejecutar manualmente para cada tabla afectada)
-- NOTA: El script intenta migrar automáticamente todas las columnas
-- de tipo integer que referencian personas.id

DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT kcu.table_name, kcu.column_name
        FROM information_schema.key_column_usage kcu
        JOIN information_schema.table_constraints tc
            ON kcu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND kcu.table_schema = 'public'
    LOOP
        -- Intentar convertir si es integer y tiene datos que mapean
        BEGIN
            EXECUTE format(
                'ALTER TABLE %I ALTER COLUMN %I TYPE UUID USING persona_id_map.new_id FROM persona_id_map WHERE %I = persona_id_map.old_id',
                r.table_name, r.column_name, r.column_name
            );
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'No se pudo migrar %.%: %', r.table_name, r.column_name, SQLERRM;
        END;
    END LOOP;
END $$;

-- 6. Re-crear FKs
ALTER TABLE cell_groups
    ADD CONSTRAINT fk_cell_groups_leader FOREIGN KEY (leader_persona_id) REFERENCES personas(id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_cell_groups_assistant FOREIGN KEY (assistant_persona_id) REFERENCES personas(id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_cell_groups_host FOREIGN KEY (host_persona_id) REFERENCES personas(id) ON DELETE SET NULL;

ALTER TABLE cell_group_members
    ADD CONSTRAINT fk_cell_group_members_persona FOREIGN KEY (persona_id) REFERENCES personas(id) ON DELETE CASCADE;

ALTER TABLE cell_group_sessions
    ADD CONSTRAINT fk_cell_group_sessions_reported FOREIGN KEY (reported_by_persona_id) REFERENCES personas(id) ON DELETE SET NULL;

ALTER TABLE cell_group_attendance
    ADD CONSTRAINT fk_cell_group_attendance_persona FOREIGN KEY (persona_id) REFERENCES personas(id) ON DELETE CASCADE;

ALTER TABLE grupo_participantes
    ADD CONSTRAINT fk_grupo_participantes_persona FOREIGN KEY (persona_id) REFERENCES personas(id) ON DELETE CASCADE;

ALTER TABLE asistencias
    ADD CONSTRAINT fk_asistencias_persona FOREIGN KEY (persona_id) REFERENCES personas(id) ON DELETE CASCADE;

ALTER TABLE historial_embudo
    ADD CONSTRAINT fk_historial_embudo_persona FOREIGN KEY (persona_id) REFERENCES personas(id) ON DELETE CASCADE;

ALTER TABLE registros_seguimiento
    ADD CONSTRAINT fk_registros_seguimiento_responsable FOREIGN KEY (responsable_id) REFERENCES personas(id) ON DELETE SET NULL;

ALTER TABLE logs_auditoria
    ADD CONSTRAINT fk_logs_auditoria_usuario FOREIGN KEY (usuario_id) REFERENCES personas(id) ON DELETE SET NULL;

ALTER TABLE grupos_evangelismo
    ADD CONSTRAINT fk_grupos_lider FOREIGN KEY (lider_persona_id) REFERENCES personas(id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_grupos_asistente FOREIGN KEY (asistente_persona_id) REFERENCES personas(id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_grupos_anfitrion FOREIGN KEY (anfitrion_persona_id) REFERENCES personas(id) ON DELETE SET NULL;

ALTER TABLE proyectos
    ADD CONSTRAINT fk_proyectos_creador FOREIGN KEY (creado_por_id) REFERENCES personas(id);

ALTER TABLE equipo_proyecto
    ADD CONSTRAINT fk_equipo_proyecto_persona FOREIGN KEY (persona_id) REFERENCES personas(id);

ALTER TABLE tareas_proyecto
    ADD CONSTRAINT fk_tareas_asignado FOREIGN KEY (asignado_a_id) REFERENCES personas(id),
    ADD CONSTRAINT fk_tareas_creador FOREIGN KEY (creado_por_id) REFERENCES personas(id);

ALTER TABLE comentarios_tarea
    ADD CONSTRAINT fk_comentarios_tarea_persona FOREIGN KEY (persona_id) REFERENCES personas(id);

ALTER TABLE documentos_proyecto
    ADD CONSTRAINT fk_documentos_proyecto_subidor FOREIGN KEY (subido_por_id) REFERENCES personas(id);

ALTER TABLE crm_casos
    ADD CONSTRAINT fk_crm_casos_persona FOREIGN KEY (persona_id) REFERENCES personas(id),
    ADD CONSTRAINT fk_crm_casos_asignado FOREIGN KEY (asignado_a_id) REFERENCES personas(id);

ALTER TABLE crm_interacciones
    ADD CONSTRAINT fk_crm_interacciones_realizador FOREIGN KEY (realizado_por_id) REFERENCES personas(id);

ALTER TABLE crm_tareas
    ADD CONSTRAINT fk_crm_tareas_asignado FOREIGN KEY (asignado_a_id) REFERENCES personas(id);

ALTER TABLE crm_plantillas_mensaje
    ADD CONSTRAINT fk_crm_plantillas_creador FOREIGN KEY (creado_por_id) REFERENCES personas(id);

ALTER TABLE academy_enrollments
    ADD CONSTRAINT fk_academy_enrollments_persona FOREIGN KEY (persona_id) REFERENCES personas(id);

ALTER TABLE academy_lesson_progress
    ADD CONSTRAINT fk_academy_lesson_progress_persona FOREIGN KEY (persona_id) REFERENCES personas(id);

ALTER TABLE academy_course_attendance
    ADD CONSTRAINT fk_academy_course_attendance_recorder FOREIGN KEY (recorded_by_persona_id) REFERENCES personas(id);

ALTER TABLE academy_formal_actas
    ADD CONSTRAINT fk_academy_actas_closer FOREIGN KEY (closed_by_persona_id) REFERENCES personas(id);

ALTER TABLE academy_forum_threads
    ADD CONSTRAINT fk_academy_forum_threads_author FOREIGN KEY (author_persona_id) REFERENCES personas(id);

ALTER TABLE academy_forum_comments
    ADD CONSTRAINT fk_academy_forum_comments_author FOREIGN KEY (author_persona_id) REFERENCES personas(id);

ALTER TABLE agenda_eventos
    ADD CONSTRAINT fk_agenda_eventos_organizador FOREIGN KEY (organizador_persona_id) REFERENCES personas(id);

ALTER TABLE agenda_participantes
    ADD CONSTRAINT fk_agenda_participantes_persona FOREIGN KEY (persona_id) REFERENCES personas(id) ON DELETE CASCADE;

-- 7. Verificar integridad
SELECT 'personas' AS tabla, count(*) AS registros FROM personas
UNION ALL
SELECT 'FKs activas', count(*)::text FROM pg_constraint WHERE confrelid = 'personas'::regclass AND contype = 'f';

COMMIT;
