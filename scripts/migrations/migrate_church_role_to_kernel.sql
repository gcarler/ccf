-- Migración: church_role (String legacy) → PersonaRoleAssignment (Kernel)
-- Ejecutar: PGPASSWORD=... psql -h localhost -U ccf_admin -d ccf_db -f este_script.sql

-- 1. Verificar que la tabla existe
SELECT 'persona_role_assignments exists: ' || count(*)::text FROM information_schema.tables 
WHERE table_schema='public' AND table_name='persona_role_assignments';

-- 2. Insertar church_roles existentes al Kernel (solo si no hay duplicado)
INSERT INTO persona_role_assignments (id, persona_id, role_type, role_name, assigned_by, is_active, created_at)
SELECT 
    gen_random_uuid(),
    p.id,
    'church_role',
    p.church_role,
    'system_migration',
    true,
    NOW()
FROM personas p
WHERE p.church_role IS NOT NULL 
  AND p.church_role != ''
  AND NOT EXISTS (
    SELECT 1 FROM persona_role_assignments pra 
    WHERE pra.persona_id = p.id AND pra.role_type = 'church_role'
  );

-- 3. Verificar resultado
SELECT 'Migrated: ' || count(*)::text || ' church_roles' FROM persona_role_assignments WHERE role_type = 'church_role';
