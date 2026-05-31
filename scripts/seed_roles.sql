-- =============================================
-- seed_roles.sql — Poblar platform_role_definitions
-- EJECUTAR PRIMERO:
--   psql -h <HOST> -U ccf_admin -d ccf_db -f scripts/seed_roles.sql
-- =============================================

INSERT INTO platform_role_definitions (role, permissions, description)
VALUES 
('ADMINISTRADOR', '{"*": ["create","read","update","delete","admin"]}', 'Acceso total a todos los módulos'),
('GESTOR', '{"crm": ["create","read","update"],"academy": ["create","read","update"],"projects": ["create","read","update"],"evangelism": ["create","read","update"],"cms": ["read","update"],"community": ["create","read","update"],"agenda": ["create","read","update"],"finances": ["read"]}', 'Gestión operativa de módulos principales'),
('EDITOR', '{"crm": ["read","update"],"academy": ["read"],"projects": ["read","update"],"evangelism": ["read","update"],"cms": ["read","update"],"community": ["create","read","update"],"agenda": ["read"]}', 'Edición limitada de contenidos'),
('LECTOR', '{"crm": ["read"],"academy": ["read"],"projects": ["read"],"evangelism": ["read"],"cms": ["read"],"community": ["read"],"agenda": ["read"]}', 'Solo lectura de todos los módulos')
ON CONFLICT (role) DO NOTHING;

-- Verificar
SELECT id, role, description FROM platform_role_definitions ORDER BY id;
