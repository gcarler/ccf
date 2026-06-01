-- ============================================================
-- Migración: Eliminar columna redundante church_role de Persona
-- ============================================================
-- Requisito: Todos los consumidores deben usar church_role_effective
-- (que resuelve desde persona_church_roles vía Kernel)
-- 
-- Ejecutar SOLO después de:
-- 1. Verificar que todas las personas tienen registro en persona_church_roles
-- 2. Actualizar todo el código que referencia Persona.church_role
-- ============================================================

BEGIN;

-- 1. Backfill: crear registros en persona_church_roles para quienes no tengan
INSERT INTO persona_church_roles (persona_id, church_role, assigned_at)
SELECT p.id, p.church_role, NOW()
FROM personas p
WHERE p.church_role IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM persona_church_roles pcr 
    WHERE pcr.persona_id = p.id
  );

-- 2. Verificar que no haya personas sin registro en persona_church_roles
-- (deben tener al menos el rol por defecto "Miembro")
INSERT INTO persona_church_roles (persona_id, church_role, assigned_at)
SELECT p.id, COALESCE(p.church_role, 'Miembro'), NOW()
FROM personas p
WHERE NOT EXISTS (
    SELECT 1 FROM persona_church_roles pcr 
    WHERE pcr.persona_id = p.id
);

-- 3. Eliminar la columna física (SOLO cuando estés seguro)
-- ALTER TABLE personas DROP COLUMN church_role;

COMMIT;
