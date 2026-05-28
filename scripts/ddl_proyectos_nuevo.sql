-- ==========================================
-- DDL: NUEVO MÓDULO DE PROYECTOS (CCF)
-- ==========================================
-- Este script crea las tablas del nuevo sistema de proyectos
-- con soporte para WBS, equipo multiagente, ruta crítica, y
-- gestor documental con SeaweedFS.
--
-- Las tablas viejas (projects, project_tasks, etc.) NO se tocan.
-- ==========================================

BEGIN;

-- 1. ENUMS
CREATE TYPE estado_proyecto AS ENUM (
    'PLANIFICACION',
    'EN_PROGRESO',
    'PAUSADO',
    'COMPLETADO',
    'CANCELADO'
);

CREATE TYPE estado_tarea AS ENUM (
    'POR_HACER',
    'EN_PROGRESO',
    'EN_REVISION',
    'COMPLETADO',
    'BLOQUEADO'
);

CREATE TYPE prioridad_tarea AS ENUM (
    'BAJA',
    'MEDIA',
    'ALTA',
    'URGENTE'
);

CREATE TYPE tipo_dependencia AS ENUM (
    'FIN_A_INICIO',
    'INICIO_A_INICIO',
    'FIN_A_FIN'
);

-- 2. TABLAS

-- 2.1 Proyectos (entidad autorreferencial para nesting)
CREATE TABLE proyectos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proyecto_padre_id UUID REFERENCES proyectos(id),
    codigo_wbs VARCHAR(50) NOT NULL UNIQUE,
    sede_id INTEGER NOT NULL REFERENCES sedes(id),
    nombre VARCHAR(150) NOT NULL,
    descripcion TEXT,
    estado estado_proyecto DEFAULT 'PLANIFICACION',
    fecha_inicio DATE NOT NULL,
    fecha_fin_est DATE NOT NULL,
    fecha_fin_real DATE,
    presupuesto_est NUMERIC(12, 2),
    creado_por_id INTEGER NOT NULL REFERENCES personas(id),
    fecha_creacion TIMESTAMP DEFAULT NOW()
);

-- 2.2 Equipo del proyecto (Persona → Rol en el proyecto)
CREATE TABLE equipo_proyecto (
    id SERIAL PRIMARY KEY,
    proyecto_id UUID NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
    persona_id INTEGER NOT NULL REFERENCES personas(id),
    rol_proyecto VARCHAR(50) NOT NULL,
    permiso_edicion BOOLEAN DEFAULT FALSE,
    fecha_asignacion TIMESTAMP DEFAULT NOW(),
    es_historico BOOLEAN DEFAULT FALSE
);

-- 2.3 Tareas (entidad autorreferencial para subtareas)
CREATE TABLE tareas_proyecto (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proyecto_id UUID NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
    tarea_padre_id UUID REFERENCES tareas_proyecto(id),
    codigo_wbs VARCHAR(50) NOT NULL,
    titulo VARCHAR(200) NOT NULL,
    descripcion TEXT,
    estado estado_tarea DEFAULT 'POR_HACER',
    prioridad prioridad_tarea DEFAULT 'MEDIA',
    asignado_a_id INTEGER REFERENCES personas(id),
    creado_por_id INTEGER NOT NULL REFERENCES personas(id),
    fecha_vencimiento TIMESTAMP NOT NULL,
    fecha_completado TIMESTAMP
);

-- 2.4 Dependencias entre tareas (ruta crítica)
CREATE TABLE dependencias_tareas (
    tarea_bloqueante_id UUID NOT NULL REFERENCES tareas_proyecto(id) ON DELETE CASCADE,
    tarea_bloqueada_id UUID NOT NULL REFERENCES tareas_proyecto(id) ON DELETE CASCADE,
    tipo_dependencia tipo_dependencia DEFAULT 'FIN_A_INICIO',
    PRIMARY KEY (tarea_bloqueante_id, tarea_bloqueada_id)
);

-- 2.5 Comentarios en tareas
CREATE TABLE comentarios_tarea (
    id SERIAL PRIMARY KEY,
    tarea_id UUID NOT NULL REFERENCES tareas_proyecto(id) ON DELETE CASCADE,
    persona_id INTEGER NOT NULL REFERENCES personas(id),
    comentario TEXT NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT NOW()
);

-- 2.6 Gestor documental (SeaweedFS)
CREATE TABLE documentos_proyecto (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proyecto_id UUID NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
    tarea_id UUID REFERENCES tareas_proyecto(id) ON DELETE SET NULL,
    seaweed_fid VARCHAR(100) NOT NULL UNIQUE,
    url_acceso TEXT,
    nombre_archivo VARCHAR(255) NOT NULL,
    extension VARCHAR(20) NOT NULL,
    peso_bytes INTEGER NOT NULL,
    subido_por_id INTEGER NOT NULL REFERENCES personas(id),
    fecha_subida TIMESTAMP DEFAULT NOW(),
    activo BOOLEAN DEFAULT TRUE
);

-- 3. TRIGGER: Hoja de Vida Ministerial
-- Cuando un proyecto se marca como COMPLETADO, se:
--   1. Marca a todo el equipo como histórico
--   2. Inyecta en historial_ministerial la participación

CREATE OR REPLACE FUNCTION inyectar_historial_proyecto()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.estado = 'COMPLETADO' AND OLD.estado != 'COMPLETADO' THEN
        UPDATE equipo_proyecto SET es_historico = TRUE WHERE proyecto_id = NEW.id;

        INSERT INTO historial_ministerial (
            miembro_id, tipo_cambio, valor_anterior, valor_nuevo,
            dias_transcurridos, fecha_cambio
        )
        SELECT
            persona_id,
            'PARTICIPACION_PROYECTO',
            'N/A',
            rol_proyecto || ' - ' || NEW.nombre || ' (' || NEW.codigo_wbs || ')',
            CURRENT_DATE - NEW.fecha_inicio,
            CURRENT_TIMESTAMP
        FROM equipo_proyecto
        WHERE proyecto_id = NEW.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_cierre_proyecto
AFTER UPDATE OF estado ON proyectos
FOR EACH ROW
EXECUTE FUNCTION inyectar_historial_proyecto();

-- 4. ÍNDICES

CREATE INDEX idx_proyectos_sede ON proyectos(sede_id);
CREATE INDEX idx_proyectos_padre ON proyectos(proyecto_padre_id);
CREATE INDEX idx_equipo_proyecto ON equipo_proyecto(proyecto_id);
CREATE INDEX idx_equipo_persona ON equipo_proyecto(persona_id);
CREATE INDEX idx_tareas_proyecto ON tareas_proyecto(proyecto_id);
CREATE INDEX idx_tareas_asignado ON tareas_proyecto(asignado_a_id);
CREATE INDEX idx_tareas_padre ON tareas_proyecto(tarea_padre_id);
CREATE INDEX idx_dependencias_bloqueada ON dependencias_tareas(tarea_bloqueada_id);
CREATE INDEX idx_comentarios_tarea ON comentarios_tarea(tarea_id);
CREATE INDEX idx_docs_proyecto ON documentos_proyecto(proyecto_id);
CREATE INDEX idx_docs_tarea ON documentos_proyecto(tarea_id);

COMMIT;
