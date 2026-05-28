-- ==========================================
-- DDL: NUEVO MÓDULO DE AUTENTICACIÓN (CCF)
-- ==========================================
-- Reemplaza las tablas legacy: users, roles, refresh_tokens, etc.
-- Las tablas viejas NO se tocan — conviven hasta migrar datos.
--
-- Principios:
--   - 100% UUID en PKs y FKs (excepto campos de valor)
--   - FK directa auth_users.id → personas.id (integración Kernel)
--   - Timezone-aware (DateTime with timezone)
--   - RBAC con roles modulares granulares (auth_user_module_roles)
--   - Forense: security_logs, password_history
--   - MFA/TOTP nativo
-- ==========================================

BEGIN;

-- ==========================================
-- 1. CATÁLOGOS Y ROLES DE ACCESO (RBAC)
-- ==========================================

CREATE TABLE auth_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre VARCHAR(100) NOT NULL UNIQUE,
    permisos JSON NOT NULL DEFAULT '{}'
);

CREATE TABLE auth_levels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(100) NOT NULL,
    min_xp INTEGER NOT NULL UNIQUE,
    icon_key VARCHAR(50)
);

-- ==========================================
-- 2. TABLA PRINCIPAL DE CREDENCIALES
-- ==========================================

CREATE TABLE auth_users (
    id UUID PRIMARY KEY REFERENCES personas(id) ON DELETE CASCADE,
    sede_id INTEGER NOT NULL REFERENCES sedes(id),
    username CITEXT NOT NULL UNIQUE,
    email CITEXT NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    rol_plataforma_id UUID NOT NULL REFERENCES auth_roles(id),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_email_verified BOOLEAN DEFAULT FALSE NOT NULL,
    failed_login_attempts INTEGER DEFAULT 0 NOT NULL,
    locked_until TIMESTAMPTZ,
    mfa_secret VARCHAR(100),
    is_mfa_enabled BOOLEAN DEFAULT FALSE NOT NULL,
    mfa_backup_codes JSON DEFAULT '[]',
    xp INTEGER DEFAULT 0 NOT NULL,
    current_level_id UUID REFERENCES auth_levels(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==========================================
-- 3. ROLES MODULARES GRANULARES
-- ==========================================

CREATE TABLE auth_user_module_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    modulo VARCHAR(50) NOT NULL,
    rol_id UUID NOT NULL REFERENCES auth_roles(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==========================================
-- 4. CONTROL DE SESIONES Y SEGURIDAD
-- ==========================================

CREATE TABLE auth_refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    token VARCHAR(500) NOT NULL UNIQUE,
    revoked BOOLEAN DEFAULT FALSE NOT NULL,
    ip_address VARCHAR(50),
    user_agent TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    last_active TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE auth_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE auth_verification_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE auth_security_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    evento VARCHAR(100) NOT NULL,
    ip_address VARCHAR(50),
    user_agent TEXT,
    detalles JSON,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE auth_password_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==========================================
-- 5. PREFERENCIAS, NOTIFICACIONES, RECORDATORIOS
-- ==========================================

CREATE TABLE auth_user_ui_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    settings JSON NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE auth_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE auth_user_reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    remind_at TIMESTAMPTZ NOT NULL,
    priority VARCHAR(20) DEFAULT 'MEDIA',
    is_dismissed BOOLEAN DEFAULT FALSE NOT NULL,
    related_type VARCHAR(50),
    related_id VARCHAR(100)
);

-- ==========================================
-- 6. GAMIFICACIÓN
-- ==========================================

CREATE TABLE auth_badges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    icon_key VARCHAR(50),
    xp_reward INTEGER DEFAULT 50 NOT NULL
);

CREATE TABLE auth_user_badges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    badge_id UUID NOT NULL REFERENCES auth_badges(id) ON DELETE CASCADE,
    earned_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==========================================
-- 7. ÍNDICES
-- ==========================================

CREATE INDEX idx_auth_users_email ON auth_users(email);
CREATE INDEX idx_auth_users_username ON auth_users(username);
CREATE INDEX idx_auth_users_sede ON auth_users(sede_id);
CREATE INDEX idx_auth_users_rol ON auth_users(rol_plataforma_id);

CREATE INDEX idx_auth_module_roles_user ON auth_user_module_roles(user_id);
CREATE INDEX idx_auth_module_roles_modulo ON auth_user_module_roles(modulo);

CREATE INDEX idx_auth_refresh_user ON auth_refresh_tokens(user_id);
CREATE INDEX idx_auth_refresh_token ON auth_refresh_tokens(token);
CREATE INDEX idx_auth_refresh_expires ON auth_refresh_tokens(expires_at);

CREATE INDEX idx_auth_reset_user ON auth_reset_tokens(user_id);
CREATE INDEX idx_auth_reset_token ON auth_reset_tokens(token);

CREATE INDEX idx_auth_verify_user ON auth_verification_tokens(user_id);
CREATE INDEX idx_auth_verify_token ON auth_verification_tokens(token);

CREATE INDEX idx_auth_security_user ON auth_security_logs(user_id);
CREATE INDEX idx_auth_security_evento ON auth_security_logs(evento);

CREATE INDEX idx_auth_password_user ON auth_password_history(user_id);

CREATE INDEX idx_auth_notifications_user ON auth_notifications(user_id);
CREATE INDEX idx_auth_notifications_read ON auth_notifications(user_id, is_read);

CREATE INDEX idx_auth_reminders_user ON auth_user_reminders(user_id);
CREATE INDEX idx_auth_reminders_time ON auth_user_reminders(remind_at);

CREATE INDEX idx_auth_user_badges_user ON auth_user_badges(user_id);

-- ==========================================
-- 8. TRIGGER: updated_at automático
-- ==========================================

CREATE OR REPLACE FUNCTION auth_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_auth_users_updated
BEFORE UPDATE ON auth_users
FOR EACH ROW EXECUTE FUNCTION auth_set_updated_at();

CREATE TRIGGER tr_auth_module_roles_updated
BEFORE UPDATE ON auth_user_module_roles
FOR EACH ROW EXECUTE FUNCTION auth_set_updated_at();

CREATE TRIGGER tr_auth_ui_prefs_updated
BEFORE UPDATE ON auth_user_ui_preferences
FOR EACH ROW EXECUTE FUNCTION auth_set_updated_at();

COMMIT;
