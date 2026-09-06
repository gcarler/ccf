import json
import uuid

import psycopg2

DB_URI = "postgresql://ccf_admin:ccf_password_secret_123@localhost:5432/ccf_recovery_20260823"
SITE_ID = "9b2bf82b-6cc5-4aeb-ac64-30a2d2bbd4f1"

conn = psycopg2.connect(DB_URI)
cur = conn.cursor()

try:
    # 1. Obtener page_id de 'about'
    cur.execute("SELECT id FROM cms_pages WHERE slug = 'about' AND site_id = %s AND deleted_at IS NULL", (SITE_ID,))
    row = cur.fetchone()
    if not row:
        raise Exception("Página 'about' no encontrada")
    page_id = row[0]
    print(f"Page ID for about: {page_id}")

    # 2. Obtener props_json de la sección monolítica 'about' si existe
    cur.execute("SELECT props_json FROM cms_sections WHERE page_id = %s AND section_key = 'about' AND deleted_at IS NULL", (page_id,))
    mono_row = cur.fetchone()
    existing_props = mono_row[0] if mono_row and mono_row[0] else {}
    if isinstance(existing_props, str):
        existing_props = json.loads(existing_props)

    # 3. Definir las 6 secciones atómicas
    atomic_sections = [
        {
            "section_key": "stats",
            "type": "stats_counter",
            "sort_order": 1,
            "props_json": {
                "stats": existing_props.get("stats") or [
                    {"value": "+20", "label": "Años de ministerio"},
                    {"value": "+8", "label": "Pastores activos"},
                    {"value": "+500", "label": "Familias"},
                    {"value": "3", "label": "Sedes"}
                ]
            }
        },
        {
            "section_key": "vision_mision",
            "type": "vision_mision",
            "sort_order": 2,
            "props_json": {
                "vision_title": existing_props.get("vision_title") or "¿A dónde vamos?",
                "vision_text": existing_props.get("vision_text") or "Ser una comunidad de fe que <strong>transforma vidas, familias y ciudades</strong> a través del poder del Evangelio, levantando discípulos que reflejen el carácter de Cristo en cada esfera de la sociedad.",
                "mision_title": existing_props.get("mision_title") or "¿Por qué existimos?",
                "mision_text": existing_props.get("mision_text") or "Guiar, equipar y movilizar a cada persona de nuestra comunidad mediante la <strong>enseñanza bíblica profunda</strong>, el compañerismo genuino y el servicio desinteresado — llevando la luz de Cristo a donde haya oscuridad."
            }
        },
        {
            "section_key": "founders",
            "type": "founders_profile",
            "sort_order": 3,
            "props_json": {
                "founder_label": existing_props.get("founder_label") or "Nuestros Pastores Principales",
                "founder_title": existing_props.get("founder_title") or "Un llamado a construir",
                "founder_title_accent": existing_props.get("founder_title_accent") or "una familia de fe",
                "founder1_name": existing_props.get("founder1_name") or "Luis Ricardo Meza G.",
                "founder1_role": existing_props.get("founder1_role") or "Pastor Principal",
                "founder1_image": "/api/static/cms/pastores/luis_ricardo.jpg",
                "founder2_name": existing_props.get("founder2_name") or "Histar Ariza Herrera",
                "founder2_role": existing_props.get("founder2_role") or "Pastor Principal",
                "founder2_image": "/api/static/cms/pastores/histar_ariza.jpg",
                "founder_bio": existing_props.get("founder_bio") or "La Comunidad Cristiana CCF nació de un profundo encuentro con la paternidad de Dios. Nuestros pastores principales, <strong>Luis Ricardo Meza Gutiérrez</strong> e <strong>Histar Ariza Herrera</strong>, han dedicado más de dos décadas a construir una iglesia que sea verdaderamente una casa — un lugar donde cada persona sea vista, amada y formada.",
                "founder_bio2": existing_props.get("founder_bio2") or "Desde sus inicios, el ADN de CCF ha sido claro: <em>sana doctrina, corazón pastoral y vida en comunidad</em>. Una iglesia que no teme enseñar la Palabra en su profundidad y que, al mismo tiempo, envuelve a cada persona con la calidez del amor de Cristo.",
                "founder_cta_team": existing_props.get("founder_cta_team") or "Conoce al equipo",
                "founder_cta_visit": existing_props.get("founder_cta_visit") or "Visítanos"
            }
        },
        {
            "section_key": "values",
            "type": "values_grid",
            "sort_order": 4,
            "props_json": {
                "values_eyebrow": existing_props.get("values_eyebrow") or "Lo que nos define",
                "valores_title": existing_props.get("valores_title") or "Valores que nos Guían",
                "valores": existing_props.get("valores") or [
                    {"num": "01", "key": "palabra", "title": "Palabra", "desc": "La Escritura es nuestra brújula. Cada decisión, enseñanza y acción está fundamentada en la sana doctrina de la Biblia."},
                    {"num": "02", "key": "amor", "title": "Amor Radical", "desc": "Un compromiso inquebrantable de servir y acoger a todos, sin importar su historia, origen o camino recorrido."},
                    {"num": "03", "key": "comunidad", "title": "Comunidad", "desc": "Creemos en la vida en familia. El crecimiento espiritual genuino ocurre en relación auténtica con otros."},
                    {"num": "04", "key": "integridad", "title": "Integridad", "desc": "Vivir con coherencia entre lo que creemos y lo que hacemos, permitiendo que nuestra fe sea visible en cada área de la vida."},
                    {"num": "05", "key": "mision", "title": "Misión", "desc": "No existimos solo para nosotros mismos. Somos enviados a alcanzar a los que aún no conocen el amor de Cristo."},
                    {"num": "06", "key": "excelencia", "title": "Excelencia", "desc": "Damos lo mejor de nosotros en todo lo que hacemos, como un acto de adoración y respeto a quien nos llamó."}
                ]
            }
        },
        {
            "section_key": "quote",
            "type": "quote_callout",
            "sort_order": 5,
            "props_json": {
                "quote_text": existing_props.get("quote_text") or "La luz que encontramos en CCF no es para guardarla — es para guiar a otros que aún caminan en la oscuridad.",
                "quote_author": existing_props.get("quote_author") or "Pastor Histar Ariza Herrera",
                "quote_subtitle": existing_props.get("quote_subtitle") or "Comunidad Cristiana CCF"
            }
        },
        {
            "section_key": "cta",
            "type": "cta_banner",
            "sort_order": 6,
            "props_json": {
                "cta_title": existing_props.get("cta_title") or "¿Listo para ser parte?",
                "cta_desc": existing_props.get("cta_desc") or "Ven a conocernos. Tenemos puertas abiertas y un lugar reservado para ti y tu familia.",
                "cta_view_sedes": existing_props.get("cta_view_sedes") or "Ver sedes",
                "cta_view_events": existing_props.get("cta_view_events") or "Próximos eventos"
            }
        }
    ]

    # 4. Insertar o actualizar cada sección atómica de forma idempotente
    for sec in atomic_sections:
        cur.execute("""
            SELECT id FROM cms_sections
            WHERE page_id = %s AND section_key = %s AND deleted_at IS NULL
        """, (page_id, sec["section_key"]))
        existing = cur.fetchone()
        if existing:
            cur.execute("""
                UPDATE cms_sections
                SET type = %s, props_json = %s, sort_order = %s, status = 'published', is_visible = true, updated_at = NOW()
                WHERE id = %s
            """, (sec["type"], json.dumps(sec["props_json"]), sec["sort_order"], existing[0]))
            print(f"Actualizada sección '{sec['section_key']}' (ID {existing[0]})")
        else:
            new_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO cms_sections (id, page_id, section_key, type, props_json, sort_order, is_visible, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, true, 'published', NOW(), NOW())
            """, (new_id, page_id, sec["section_key"], sec["type"], json.dumps(sec["props_json"]), sec["sort_order"]))
            print(f"Insertada sección '{sec['section_key']}' (ID {new_id})")

    # 5. Archivar la sección monolítica 'about' para que no duplique en CMS ni rompa el reordenamiento
    cur.execute("""
        UPDATE cms_sections
        SET status = 'archived', is_visible = false, updated_at = NOW()
        WHERE page_id = %s AND section_key = 'about' AND deleted_at IS NULL
    """, (page_id,))
    print("Sección monolítica 'about' archivada.")

    # 6. Hero a sort_order 0
    cur.execute("""
        UPDATE cms_sections
        SET sort_order = 0, status = 'published', is_visible = true, updated_at = NOW()
        WHERE page_id = %s AND section_key = 'hero' AND deleted_at IS NULL
    """, (page_id,))
    print("Hero configurado en sort_order 0.")

    conn.commit()
    print("Migración completada exitosamente.")

except Exception as e:
    conn.rollback()
    print(f"Error en migración: {e}")
    raise e
finally:
    cur.close()
    conn.close()
