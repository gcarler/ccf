-- ============================================================================
-- Migration: Modularize CCF Home Sections (Monolithic feed -> atomic sections)
-- Description: Decouples feed into welcome, activities, and newsletter while
--              preserving hero (sort_order=0) and discover_cta (sort_order=4).
-- Engine: PostgreSQL 16+
-- Transaction: Atomic (BEGIN ... COMMIT) & Idempotent
-- ============================================================================

BEGIN;

DO $$
DECLARE
    v_site_id UUID;
    v_page_id UUID;
    v_feed_id UUID;
    v_welcome_id UUID;
    v_activities_id UUID;
    v_newsletter_id UUID;
    v_feed_props JSONB;
    v_welcome_props JSONB;
    v_activities_props JSONB;
    v_newsletter_props JSONB;
    v_status VARCHAR(20) := 'published';
    v_is_visible BOOLEAN := TRUE;
BEGIN
    -- 1. Locate site and page
    SELECT id INTO v_site_id FROM cms_sites WHERE site_key = 'ccf' LIMIT 1;
    IF v_site_id IS NULL THEN
        RAISE NOTICE 'Site ccf not found, skipping.';
        RETURN;
    END IF;

    SELECT id INTO v_page_id FROM cms_pages WHERE site_id = v_site_id AND slug = 'home' AND deleted_at IS NULL LIMIT 1;
    IF v_page_id IS NULL THEN
        RAISE NOTICE 'Page home not found for site ccf, skipping.';
        RETURN;
    END IF;

    -- 2. Check existing sections
    SELECT id INTO v_welcome_id FROM cms_sections WHERE page_id = v_page_id AND section_key = 'welcome' AND deleted_at IS NULL LIMIT 1;
    SELECT id INTO v_activities_id FROM cms_sections WHERE page_id = v_page_id AND section_key = 'activities' AND deleted_at IS NULL LIMIT 1;
    SELECT id INTO v_newsletter_id FROM cms_sections WHERE page_id = v_page_id AND section_key = 'newsletter' AND deleted_at IS NULL LIMIT 1;
    SELECT id, props_json::jsonb, status, is_visible INTO v_feed_id, v_feed_props, v_status, v_is_visible 
    FROM cms_sections WHERE page_id = v_page_id AND section_key = 'feed' AND deleted_at IS NULL LIMIT 1;

    -- 3. Mutate feed into welcome if welcome does not yet exist
    IF v_welcome_id IS NULL AND v_feed_id IS NOT NULL THEN
        v_welcome_props := (v_feed_props 
            - 'activities_eyebrow' - 'activities_title' - 'activities_view_all' - 'activities_view_all_href' - 'activities_empty'
            - 'newsletter_eyebrow' - 'newsletter_title' - 'newsletter_description' - 'newsletter_placeholder'
            - 'newsletter_submit' - 'newsletter_sending_label' - 'newsletter_success_title' - 'newsletter_success_desc'
            - 'newsletter_success_toast' - 'newsletter_error_toast')
            || jsonb_build_object(
                'title', COALESCE(v_feed_props->>'title', v_feed_props->>'section_title', 'Bienvenidos a Casa'),
                'description', COALESCE(v_feed_props->>'description', v_feed_props->>'section_description', '')
            );

        UPDATE cms_sections
        SET section_key = 'welcome',
            type = 'feed',
            sort_order = 1,
            props_json = v_welcome_props,
            updated_at = NOW()
        WHERE id = v_feed_id;
        v_welcome_id := v_feed_id;
        RAISE NOTICE 'Converted feed section (%) into welcome', v_feed_id;
    ELSIF v_welcome_id IS NOT NULL THEN
        UPDATE cms_sections SET sort_order = 1 WHERE id = v_welcome_id;
    END IF;

    -- 4. Ensure activities section exists
    IF v_activities_id IS NULL THEN
        v_activities_props := jsonb_build_object(
            'eyebrow', COALESCE(v_feed_props->>'activities_eyebrow', 'Actualidad'),
            'activities_eyebrow', COALESCE(v_feed_props->>'activities_eyebrow', 'Actualidad'),
            'title', COALESCE(v_feed_props->>'activities_title', 'Actividades Recientes'),
            'activities_title', COALESCE(v_feed_props->>'activities_title', 'Actividades Recientes'),
            'view_all', COALESCE(v_feed_props->>'activities_view_all', 'Ver calendario →'),
            'activities_view_all', COALESCE(v_feed_props->>'activities_view_all', 'Ver calendario →'),
            'view_all_href', COALESCE(v_feed_props->>'activities_view_all_href', '/eventos'),
            'activities_view_all_href', COALESCE(v_feed_props->>'activities_view_all_href', '/eventos'),
            'empty', COALESCE(v_feed_props->>'activities_empty', 'Próximamente encontrarás aquí nuestras actividades. Mientras tanto, síguenos en redes sociales.'),
            'activities_empty', COALESCE(v_feed_props->>'activities_empty', 'Próximamente encontrarás aquí nuestras actividades. Mientras tanto, síguenos en redes sociales.')
        );

        INSERT INTO cms_sections (
            id, page_id, section_key, type, props_json, sort_order, is_visible, status, is_global, locale, created_at, updated_at
        ) VALUES (
            gen_random_uuid(), v_page_id, 'activities', 'events_calendar', v_activities_props, 2, v_is_visible, v_status, FALSE, 'es', NOW(), NOW()
        );
        RAISE NOTICE 'Inserted atomic activities section';
    ELSE
        UPDATE cms_sections SET sort_order = 2 WHERE id = v_activities_id;
    END IF;

    -- 5. Ensure newsletter section exists
    IF v_newsletter_id IS NULL THEN
        v_newsletter_props := jsonb_build_object(
            'eyebrow', COALESCE(v_feed_props->>'newsletter_eyebrow', 'Boletín semanal'),
            'newsletter_eyebrow', COALESCE(v_feed_props->>'newsletter_eyebrow', 'Boletín semanal'),
            'title', COALESCE(v_feed_props->>'newsletter_title', '¿Quieres recibir nuestras novedades?'),
            'newsletter_title', COALESCE(v_feed_props->>'newsletter_title', '¿Quieres recibir nuestras novedades?'),
            'description', COALESCE(v_feed_props->>'newsletter_description', E'Meditaciones semanales, eventos exclusivos y más.\nDirecto a tu correo.'),
            'newsletter_description', COALESCE(v_feed_props->>'newsletter_description', E'Meditaciones semanales, eventos exclusivos y más.\nDirecto a tu correo.'),
            'placeholder', COALESCE(v_feed_props->>'newsletter_placeholder', 'Tu correo electrónico'),
            'newsletter_placeholder', COALESCE(v_feed_props->>'newsletter_placeholder', 'Tu correo electrónico'),
            'submit', COALESCE(v_feed_props->>'newsletter_submit', 'Suscribirme'),
            'newsletter_submit', COALESCE(v_feed_props->>'newsletter_submit', 'Suscribirme'),
            'sending_label', COALESCE(v_feed_props->>'newsletter_sending_label', 'Enviando...'),
            'newsletter_sending_label', COALESCE(v_feed_props->>'newsletter_sending_label', 'Enviando...'),
            'success_title', COALESCE(v_feed_props->>'newsletter_success_title', '¡Gracias por suscribirte!'),
            'newsletter_success_title', COALESCE(v_feed_props->>'newsletter_success_title', '¡Gracias por suscribirte!'),
            'success_desc', COALESCE(v_feed_props->>'newsletter_success_desc', 'Recibirás meditaciones y novedades semanales.'),
            'newsletter_success_desc', COALESCE(v_feed_props->>'newsletter_success_desc', 'Recibirás meditaciones y novedades semanales.'),
            'success_toast', COALESCE(v_feed_props->>'newsletter_success_toast', '¡Suscrito al boletín de El Faro!'),
            'newsletter_success_toast', COALESCE(v_feed_props->>'newsletter_success_toast', '¡Suscrito al boletín de El Faro!'),
            'error_toast', COALESCE(v_feed_props->>'newsletter_error_toast', 'No se pudo suscribir. Intenta de nuevo.'),
            'newsletter_error_toast', COALESCE(v_feed_props->>'newsletter_error_toast', 'No se pudo suscribir. Intenta de nuevo.')
        );

        INSERT INTO cms_sections (
            id, page_id, section_key, type, props_json, sort_order, is_visible, status, is_global, locale, created_at, updated_at
        ) VALUES (
            gen_random_uuid(), v_page_id, 'newsletter', 'newsletter', v_newsletter_props, 3, v_is_visible, v_status, FALSE, 'es', NOW(), NOW()
        );
        RAISE NOTICE 'Inserted atomic newsletter section';
    ELSE
        UPDATE cms_sections SET sort_order = 3 WHERE id = v_newsletter_id;
    END IF;

    -- 6. Ensure hero sort_order is 0
    UPDATE cms_sections SET sort_order = 0 WHERE page_id = v_page_id AND section_key = 'hero' AND deleted_at IS NULL;

    -- 7. Ensure discover_cta sort_order is 4
    UPDATE cms_sections SET sort_order = 4 WHERE page_id = v_page_id AND section_key = 'discover_cta' AND deleted_at IS NULL;

    -- 8. Archive any obsolete feed row if distinct from welcome
    IF v_welcome_id IS NOT NULL AND v_feed_id IS NOT NULL AND v_welcome_id <> v_feed_id THEN
        UPDATE cms_sections SET deleted_at = NOW() WHERE id = v_feed_id;
        RAISE NOTICE 'Soft-deleted redundant feed section %', v_feed_id;
    END IF;

    RAISE NOTICE 'Modularization SQL completed successfully.';
END $$;

COMMIT;
