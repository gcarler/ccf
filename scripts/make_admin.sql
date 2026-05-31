-- =============================================
-- make_admin.sql — Crea gscarlosernesto@gmail.com
-- como ADMINISTRADOR en PostgreSQL (CCF)
-- =============================================
-- USO:
--   1. Primero poblar roles:
--      psql -h <HOST> -U ccf_admin -d ccf_db -c "
--        INSERT INTO platform_role_definitions (role, permissions)
--        VALUES ('ADMINISTRADOR', '{\"*\": [\"create\",\"read\",\"update\",\"delete\",\"admin\"]}')
--        ON CONFLICT (role) DO NOTHING;
--        INSERT INTO platform_role_definitions (role, permissions)
--        VALUES ('GESTOR', '{\"crm\": [\"create\",\"read\",\"update\"],\"academy\": [\"create\",\"read\",\"update\"],\"projects\": [\"create\",\"read\",\"update\"],\"evangelism\": [\"create\",\"read\",\"update\"],\"cms\": [\"read\",\"update\"],\"community\": [\"create\",\"read\",\"update\"],\"agenda\": [\"create\",\"read\",\"update\"],\"finances\": [\"read\"]}')
--        ON CONFLICT (role) DO NOTHING;
--        INSERT INTO platform_role_definitions (role, permissions)
--        VALUES ('EDITOR', '{\"crm\": [\"read\",\"update\"],\"academy\": [\"read\"],\"projects\": [\"read\",\"update\"],\"evangelism\": [\"read\",\"update\"],\"cms\": [\"read\",\"update\"],\"community\": [\"create\",\"read\",\"update\"],\"agenda\": [\"read\"]}')
--        ON CONFLICT (role) DO NOTHING;
--        INSERT INTO platform_role_definitions (role, permissions)
--        VALUES ('LECTOR', '{\"crm\": [\"read\"],\"academy\": [\"read\"],\"projects\": [\"read\"],\"evangelism\": [\"read\"],\"cms\": [\"read\"],\"community\": [\"read\"],\"agenda\": [\"read\"]}')
--        ON CONFLICT (role) DO NOTHING;
--      "
--   2. Luego ejecutar este script:
--      psql -h <HOST> -U ccf_admin -d ccf_db -f scripts/make_admin.sql
-- =============================================

-- Verificar que existe la sede por defecto (sede_id = 1)
INSERT INTO sedes (id, name)
SELECT 1, 'Sede Principal'
WHERE NOT EXISTS (SELECT 1 FROM sedes WHERE id = 1);

-- 1. Crear persona si no existe
INSERT INTO personas (id, first_name, last_name, email, sede_id, church_role, estado_vital, created_at)
SELECT 
    gen_random_uuid(), 
    'Carlos Ernesto', 
    'Sánchez', 
    'gscarlosernesto@gmail.com', 
    1,
    'ADMINISTRADOR', 
    'ACTIVO', 
    NOW()
WHERE NOT EXISTS (SELECT 1 FROM personas WHERE email = 'gscarlosernesto@gmail.com');

-- 2. Crear usuario admin en auth_users (FK a persona, platform_role_id = 1 = ADMINISTRADOR)
INSERT INTO auth_users (id, sede_id, username, email, password_hash, platform_role_id, is_active, is_email_verified, failed_login_attempts, is_mfa_enabled, mfa_backup_codes, xp, created_at, updated_at)
SELECT 
    p.id,
    p.sede_id,
    'gscarlosernesto',
    'gscarlosernesto@gmail.com',
    NULL,  -- sin password hash aún (se asigna luego vía reset password)
    (SELECT id FROM platform_role_definitions WHERE role = 'ADMINISTRADOR' LIMIT 1),
    true,
    true,
    0,
    false,
    '[]',
    0,
    NOW(),
    NOW()
FROM personas p
WHERE p.email = 'gscarlosernesto@gmail.com'
  AND NOT EXISTS (SELECT 1 FROM auth_users WHERE email = 'gscarlosernesto@gmail.com');

-- 3. Si ya existe, asegurar que tenga el rol ADMINISTRADOR
UPDATE auth_users
SET platform_role_id = (SELECT id FROM platform_role_definitions WHERE role = 'ADMINISTRADOR' LIMIT 1),
    is_active = true,
    is_email_verified = true
WHERE email = 'gscarlosernesto@gmail.com'
  AND platform_role_id IS DISTINCT FROM (SELECT id FROM platform_role_definitions WHERE role = 'ADMINISTRADOR' LIMIT 1);

-- 4. Verificación final
\x on
SELECT 
    'USUARIO ADMIN' as "",
    u.email, 
    u.username, 
    u.is_active, 
    u.is_email_verified,
    prd.role as platform_role,
    CONCAT(p.first_name, ' ', p.last_name) as nombre_completo,
    p.sede_id
FROM auth_users u
JOIN personas p ON p.id = u.id
LEFT JOIN platform_role_definitions prd ON prd.id = u.platform_role_id
WHERE u.email = 'gscarlosernesto@gmail.com';
\x off
