-- ============================================================================
-- SCRIPT DE INICIALIZACIÓN PARA POSTGRESQL — Plataforma CCF
-- ============================================================================
-- Ejecutar: psql -U ccf_admin -d ccf_db -f scripts/init_postgresql.sql
-- Compatible con: PostgreSQL 14+
--
-- Este script crea TODO el schema necesario para CCF:
--   - Extensiones (UUID, pg_trgm para búsqueda)
--   - ENUMs del kernel
--   - Tablas del kernel (personas, sedes, roles)
--   - Tablas de autenticación v3 (auth_*)
--   - Tablas de módulos (evangelism, crm, academy, agenda, proyectos)
--   - Tablas legacy con NOTA de deprecación
--   - Índices y constraints
--   - Seed data mínima
-- ============================================================================

BEGIN;

-- ============================================================================
-- EXTENSIONES
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gist";

-- ============================================================================
-- ENUMS DEL KERNEL
-- ============================================================================
DO $$ BEGIN
    CREATE TYPE activity_status AS ENUM ('ACTIVO', 'INACTIVO');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE ministry_office AS ENUM ('APOSTOL', 'PROFETA', 'EVANGELISTA', 'PASTOR', 'MAESTRO');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE church_role AS ENUM (
        'LIDER', 'SERVIDOR', 'MIEMBRO_BAUTIZADO', 'SIMPATIZANTE',
        'VISITANTE_SERVICIO', 'VISITANTE_EVANGELISMO', 'VISITANTE_ONLINE'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE platform_role AS ENUM ('ADMINISTRADOR', 'GESTOR', 'EDITOR', 'LECTOR');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================================
-- TABLA: sedes (multi-tenant)
-- ============================================================================
CREATE TABLE IF NOT EXISTS sedes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre VARCHAR(150) NOT NULL,
    ciudad VARCHAR(100) NOT NULL,
    es_activa BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- TABLA: personas (Kernel — Single Source of Truth)
-- ============================================================================
CREATE TABLE IF NOT EXISTS personas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sede_id UUID REFERENCES sedes(id) ON DELETE SET NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    second_name VARCHAR(100),
    second_last_name VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(20),
    mobile_phone VARCHAR(20),
    church_role VARCHAR(50) DEFAULT 'Miembro',
    is_baptized BOOLEAN DEFAULT FALSE,
    fecha_bautismo DATE,
    spiritual_status VARCHAR(50) DEFAULT 'Nuevo',
    estado_vital VARCHAR(50) DEFAULT 'ACTIVO',
    ministerio VARCHAR(100),
    id_type VARCHAR(50),
    id_number VARCHAR(50),
    marital_status VARCHAR(50),
    birth_country VARCHAR(100),
    address TEXT,
    birthday DATE,
    sex VARCHAR(1),
    tags JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_personas_sede ON personas(sede_id);
CREATE INDEX IF NOT EXISTS idx_personas_email ON personas(email);
CREATE INDEX IF NOT EXISTS idx_personas_nombre ON personas(first_name, last_name);

-- ============================================================================
-- TABLAS DEL KERNEL (3 Dimensiones de Identidad)
-- ============================================================================

-- Dimensión A: Ministerios
CREATE TABLE IF NOT EXISTS persona_ministries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    persona_id UUID NOT NULL REFERENCES personas(id) ON DELETE CASCADE,
    ministry ministry_office NOT NULL,
    recognition_date DATE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pers_min_pers ON persona_ministries(persona_id);

-- Dimensión B: Roles de Iglesia
CREATE TABLE IF NOT EXISTS persona_church_roles (
    id SERIAL PRIMARY KEY,
    persona_id UUID NOT NULL REFERENCES personas(id) ON DELETE CASCADE UNIQUE,
    church_role church_role NOT NULL DEFAULT 'VISITANTE_ONLINE',
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_pers_church_role ON persona_church_roles(persona_id);

CREATE TABLE IF NOT EXISTS persona_role_history (
    id SERIAL PRIMARY KEY,
    persona_id UUID NOT NULL REFERENCES personas(id) ON DELETE CASCADE,
    church_role_old church_role,
    church_role_new church_role NOT NULL,
    changed_at TIMESTAMPTZ DEFAULT NOW(),
    changed_by INTEGER,
    notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_pers_role_hist ON persona_role_history(persona_id);

-- Dimensión C: Roles de Plataforma (definiciones)
CREATE TABLE IF NOT EXISTS platform_role_definitions (
    id SERIAL PRIMARY KEY,
    role platform_role NOT NULL UNIQUE,
    permissions JSONB NOT NULL DEFAULT '{}',
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS persona_platform_roles (
    id SERIAL PRIMARY KEY,
    persona_id UUID NOT NULL REFERENCES personas(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES platform_role_definitions(id),
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_pers_plat_role ON persona_platform_roles(persona_id);

-- ============================================================================
-- TABLAS DE AUTENTICACIÓN v3 (UUID-based)
-- ============================================================================

CREATE TABLE IF NOT EXISTS auth_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre VARCHAR(100) NOT NULL UNIQUE,
    permisos JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS auth_levels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(100) NOT NULL,
    min_xp INTEGER NOT NULL UNIQUE,
    icon_key VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS auth_users (
    id UUID PRIMARY KEY REFERENCES personas(id) ON DELETE CASCADE,
    sede_id UUID NOT NULL REFERENCES sedes(id),
    username VARCHAR(150) NOT NULL UNIQUE,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255),
    rol_plataforma_id UUID REFERENCES auth_roles(id),
    platform_role_id INTEGER REFERENCES platform_role_definitions(id),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_email_verified BOOLEAN DEFAULT FALSE NOT NULL,
    failed_login_attempts INTEGER DEFAULT 0 NOT NULL,
    locked_until TIMESTAMPTZ,
    mfa_secret VARCHAR(100),
    is_mfa_enabled BOOLEAN DEFAULT FALSE,
    mfa_backup_codes JSONB DEFAULT '[]',
    xp INTEGER DEFAULT 0 NOT NULL,
    current_level_id UUID REFERENCES auth_levels(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_auth_users_email ON auth_users(email);
CREATE INDEX IF NOT EXISTS idx_auth_users_sede ON auth_users(sede_id);

CREATE TABLE IF NOT EXISTS auth_user_module_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    modulo VARCHAR(50) NOT NULL,
    rol_id UUID NOT NULL REFERENCES auth_roles(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS auth_refresh_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    token VARCHAR(500) NOT NULL UNIQUE,
    revoked BOOLEAN DEFAULT FALSE,
    ip_address VARCHAR(50),
    user_agent TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    last_active TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_refresh_token ON auth_refresh_tokens(token);

CREATE TABLE IF NOT EXISTS auth_security_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth_users(id) ON DELETE CASCADE,
    evento VARCHAR(100) NOT NULL,
    ip_address VARCHAR(50),
    user_agent TEXT,
    detalles JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS auth_password_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS auth_reset_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS auth_verification_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS auth_badges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    icon_key VARCHAR(50),
    xp_reward INTEGER DEFAULT 50
);

CREATE TABLE IF NOT EXISTS auth_user_badges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    badge_id UUID NOT NULL REFERENCES auth_badges(id) ON DELETE CASCADE,
    earned_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS auth_user_ui_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE UNIQUE,
    settings JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS auth_notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS auth_user_reminders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    remind_at TIMESTAMPTZ NOT NULL,
    priority VARCHAR(20) DEFAULT 'MEDIA',
    is_dismissed BOOLEAN DEFAULT FALSE,
    related_type VARCHAR(50),
    related_id VARCHAR(100)
);

-- ============================================================================
-- SEED DATA — SEDES
-- ============================================================================
INSERT INTO sedes (id, nombre, ciudad, es_activa) VALUES
    (uuid_generate_v4(), 'Sede Norte - Matriz', 'Monterrey', TRUE),
    (uuid_generate_v4(), 'Sede Sur', 'Monterrey', TRUE),
    (uuid_generate_v4(), 'Sede Online', 'Virtual', TRUE)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- SEED DATA — ROLES DE PLATAFORMA
-- ============================================================================
INSERT INTO platform_role_definitions (id, role, description, permissions) VALUES
    (1, 'ADMINISTRADOR', 'Acceso total al sistema',
     '{"system:config":["admin"],"crm":["create","read","update","delete"],"academy":["create","read","update","delete"],"projects":["create","read","update","delete"],"evangelism":["create","read","update","delete"],"community":["create","read","update","delete"],"cms":["create","read","update","delete"],"agenda":["create","read","update","delete"],"finances":["create","read","update","delete"],"messaging":["create","read","update","delete"]}')
ON CONFLICT (id) DO NOTHING;

INSERT INTO platform_role_definitions (id, role, description, permissions) VALUES
    (2, 'GESTOR', 'Gestiona módulos asignados',
     '{"crm":["create","read","update"],"academy":["create","read","update"],"projects":["create","read","update"],"evangelism":["create","read","update"],"community":["create","read","update"],"agenda":["create","read"]}')
ON CONFLICT (id) DO NOTHING;

INSERT INTO platform_role_definitions (id, role, description, permissions) VALUES
    (3, 'EDITOR', 'Crea y edita contenido',
     '{"crm":["read","update"],"academy":["read"],"projects":["read","update"],"evangelism":["read","update"],"cms":["read","update"],"community":["create","read","update"]}')
ON CONFLICT (id) DO NOTHING;

INSERT INTO platform_role_definitions (id, role, description, permissions) VALUES
    (4, 'LECTOR', 'Solo lectura en todos los módulos',
     '{"crm":["read"],"academy":["read"],"projects":["read"],"evangelism":["read"],"community":["read"],"agenda":["read"],"cms":["read"]}')
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- SEED DATA — AUTH ROLES (v2 legacy)
-- ============================================================================
INSERT INTO auth_roles (id, nombre, permisos) VALUES
    (uuid_generate_v4(), 'ADMINISTRADOR', '{"system:config":"allow","crm:manage":"allow","academy:manage":"allow","projects:manage":"allow","evangelism:manage":"allow","community:manage":"allow","cms:manage":"allow","agenda:manage":"allow","finances:manage":"allow","messaging:edit":"allow","profile:manage":"allow"}'),
    (uuid_generate_v4(), 'GESTOR', '{"crm:manage":"allow","academy:manage":"allow","projects:manage":"allow","evangelism:edit":"allow","community:edit":"allow","messaging:edit":"allow","profile:manage":"allow"}'),
    (uuid_generate_v4(), 'EDITOR', '{"crm:edit":"allow","academy:edit":"allow","projects:edit":"allow","evangelism:edit":"allow","community:edit":"allow","cms:edit":"allow","messaging:edit":"allow","profile:manage":"allow"}'),
    (uuid_generate_v4(), 'LECTOR', '{"crm:read":"allow","academy:read":"allow","projects:read":"allow","evangelism:read":"allow","community:read":"allow","cms:read":"allow","messaging:read":"allow","profile:manage":"allow"}')
ON CONFLICT (nombre) DO NOTHING;

-- ============================================================================
-- SEED DATA — NIVELES DE GAMIFICACIÓN
-- ============================================================================
INSERT INTO auth_levels (id, title, min_xp, icon_key) VALUES
    (uuid_generate_v4(), 'Semilla', 0, 'seed'),
    (uuid_generate_v4(), 'Retoño', 100, 'sprout'),
    (uuid_generate_v4(), 'Árbol', 500, 'tree'),
    (uuid_generate_v4(), 'Roble', 2000, 'oak'),
    (uuid_generate_v4(), 'Monte', 10000, 'mountain')
ON CONFLICT (min_xp) DO NOTHING;

-- ============================================================================
-- SEED DATA — MEDALLAS
-- ============================================================================
INSERT INTO auth_badges (id, name, description, icon_key, xp_reward) VALUES
    (uuid_generate_v4(), 'Primer Inicio', 'Iniciaste sesión por primera vez', 'login', 10),
    (uuid_generate_v4(), 'Consistente', 'Asististe a 5 sesiones de grupo', 'calendar-check', 50),
    (uuid_generate_v4(), 'Evangelista', 'Invitaste a 3 personas a un grupo', 'users', 100),
    (uuid_generate_v4(), 'Discípulo', 'Completaste un curso de Academia', 'graduation-cap', 200),
    (uuid_generate_v4(), 'Líder', 'Lideraste un grupo por 6 meses', 'crown', 500)
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- NOTA: Las tablas legacy no se crean aquí.
-- Las migraciones de Alembic las manejan (y eliminan progresivamente).
-- ============================================================================

COMMIT;

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================
SELECT '✅ Schema CCF instalado correctamente' AS status;
SELECT COUNT(*) AS total_sedes FROM sedes;
SELECT COUNT(*) AS total_platform_roles FROM platform_role_definitions;
SELECT COUNT(*) AS total_auth_roles FROM auth_roles;
SELECT COUNT(*) AS total_levels FROM auth_levels;
SELECT COUNT(*) AS total_badges FROM auth_badges;
