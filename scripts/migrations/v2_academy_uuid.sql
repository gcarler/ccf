-- ============================================================
-- Migración: Academy Integer PKs → UUID
-- Copia datos de tablas compat (courses, lessons, etc.)
-- a las nuevas tablas v2 (academy_courses, academy_lessons, etc.)
-- ============================================================
-- Ejecutar solo después de verificar que las tablas v2 existen
-- y que no hay colisiones de datos.
-- ============================================================

BEGIN;

-- 1. Migrar cursos
INSERT INTO academy_courses (id, sede_id, code, title, description, modality, 
                             otorga_rol_iglesia, is_published, is_self_paced, 
                             duration_hours, xp_per_lesson, image_url, created_at, updated_at)
SELECT 
    gen_random_uuid(),  -- Nuevo UUID
    NULL,               -- sede_id (requiere mapeo manual si aplica)
    c.code,
    c.title,
    c.description,
    'PRESENCIAL',       -- modality por defecto
    NULL,               -- otorga_rol_iglesia
    c.is_published,
    FALSE,              -- is_self_paced
    COALESCE(c.duration_hours, 0),
    COALESCE(c.xp_per_lesson, 10),
    NULL,               -- image_url
    c.created_at,
    c.updated_at
FROM courses c
ON CONFLICT (code) DO NOTHING;

-- 2. Migrar lecciones
INSERT INTO academy_lessons (id, curso_id, title, content, content_type, 
                             order_index, duration_minutes, is_published, 
                             xp_reward, created_at, updated_at)
SELECT 
    gen_random_uuid(),
    ac.id,              -- Nuevo UUID del curso en academy_courses
    l.title,
    l.content,
    'VIDEO',            -- content_type por defecto
    l.order_index,
    COALESCE(l.duration_minutes, 0),
    TRUE,               -- is_published
    COALESCE(ac.xp_per_lesson, 10),
    l.created_at,
    l.updated_at
FROM lessons l
JOIN courses c ON c.id = l.course_id
JOIN academy_courses ac ON ac.code = c.code;

-- 3. Migrar matrículas
INSERT INTO academy_enrollments (id, persona_id, curso_id, status, 
                                 enrolled_at, completed_at, xp_earned)
SELECT 
    gen_random_uuid(),
    e.persona_id,
    ac.id,
    CASE 
        WHEN e.completed_at IS NOT NULL THEN 'COMPLETED'
        ELSE 'ACTIVE'
    END,
    e.enrolled_at,
    e.completed_at,
    COALESCE(e.xp_earned, 0)
FROM enrollments e
JOIN courses c ON c.id = e.course_id
JOIN academy_courses ac ON ac.code = c.code;

COMMIT;
