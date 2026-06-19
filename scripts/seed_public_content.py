#!/usr/bin/env python3
"""
Seed page_contents con el contenido real de todas las páginas públicas.
Hace UPSERT: si ya existe el registro lo actualiza, si no lo crea.

Uso:
    cd /root/ccf && source venv/bin/activate && python scripts/seed_public_content.py
"""
import json
import sys
import os

sys.path.insert(0, "/root/ccf")
os.environ.setdefault("DATABASE_URL", "")

from sqlalchemy import text
from backend.core.database import engine

# ── Contenido de cada bloque ────────────────────────────────────────────────

BLOCKS = {

    # ── HOME ────────────────────────────────────────────────────────────────
    "faro_events_feed": {
        "title": "Contenido — Eventos",
        "content": {
            "empty_title": "Esperando agenda desde el CMS",
            "empty_description": "Cuando haya eventos reales publicados, apareceran aqui sin contenido simulado.",
            "no_events_title": "Sin eventos publicados",
            "no_events_description": "Cuando el CMS publique eventos, apareceran aqui sin tarjetas inventadas.",
            "calendar_title": "Explora nuestro Calendario",
            "calendar_description": "Organiza tu tiempo con nuestras actividades comunitarias.",
            "today_label": "HOY",
            "upcoming_label": "Proximo en 48 horas",
            "featured_badge": "Destacado",
            "reserve_cta": "Reservar lugar",
            "filters": ["Todos", "Conferencias", "Grupos de Conexión", "Cursos & Talleres", "Especiales"],
            "featured_empty_title": "Evento destacado",
            "featured_empty_description": "Contenido real desde el CMS",
            "channel_link_label": "Ver canal",
        },
    },
    "faro_sermons_feed": {
        "title": "Contenido — Prédicas",
        "content": {
            "hero_eyebrow": "Ministerios Faro Oficial",
            "hero_title_lead": "Prédicas &",
            "hero_title_accent": "Mensajes",
            "hero_description": "Alimento para el alma — explora los mensajes más recientes de nuestro canal de YouTube.",
            "featured_label": "Último mensaje",
            "grid_label": "Más mensajes",
            "results_label": "Resultados",
            "empty_title": "No se pudieron cargar los videos",
            "empty_description": "Verifica tu conexión o intenta nuevamente.",
            "search_placeholder": "Buscar por título o predicador…",
            "clear_search_label": "Limpiar búsqueda",
            "watched_label": "Visto",
            "more_videos_label": "videos",
            "channel_link_label": "Ver canal",
            "cta_label": "Ver todos en YouTube",
            "no_results_prefix": "Sin resultados para",
            "no_results_description": "Intenta con otro término.",
        },
    },
    "faro_testimonials_hero": {
        "title": "Hero — Testimonios",
        "content": {
            "eyebrow": "Impacto Real",
            "title_lead": "Historias de",
            "title_accent": "Transformación",
            "description": "Descubre cómo la fe y la comunidad han iluminado el camino de personas reales.",
        },
    },
    "faro_testimonials_feed": {
        "title": "Contenido — Testimonios",
        "content": {
            "search_placeholder": "Buscar por tema, nombre o palabra clave",
            "loading_label": "Cargando...",
            "empty_title": "Todavía no hay testimonios publicados",
            "empty_description": "Cuando el CMS publique testimonios, aparecerán aquí.",
            "cta_label": "Compartir mi historia",
            "hero_badge": "Impacto Real",
            "hero_title_lead": "Historias de",
            "hero_title_accent": "Transformación",
            "hero_description": "Descubre cómo la fe y la comunidad han iluminado el camino de personas reales.",
        },
    },
    "faro_boletin_hero": {
        "title": "Hero — Boletín",
        "content": {
            "subtitle": "Boletín Semanal FARO",
            "title": "Recibe nuestra palabra de aliento",
            "description": "Cada semana te enviamos una reflexión bíblica, un versículo de ánimo y consejos prácticos para fortalecer tu fe.",
            "cta_text": "Suscribirme ahora",
        },
    },
    "faro_pastores_index": {
        "title": "Contenido — Pastores",
        "content": {
            "hero_badge": "Conoce a nuestro equipo pastoral",
            "hero_title": "Liderazgo Pastoral",
            "hero_description": "Hombres y mujeres llamados por Dios para servir, guiar y amar a esta casa.",
            "loading_label": "Cargando...",
            "empty_title": "No hay líderes pastorales registrados aún.",
            "card_cta": "Conocer más",
            "principal_label": "Pastor Principal",
        },
    },
    "faro_home_hero": {
        "title": "Hero — Inicio",
        "content": {
            "eyebrow": "UNA COMUNIDAD QUE ILUMINA",
            "title_lead": "FARO:",
            "title_accent": "Tu Guía,",
            "title_tail": "Su Luz",
            "description": "Navegando juntos hacia la verdad. Un espacio de encuentro, fe y transformación en el corazón de nuestra comunidad.",
            "primary_cta": "Empezar mi viaje",
            "secondary_cta": "Ver Prédicas",
            "bg_image": "https://images.unsplash.com/photo-1504051771394-dd2e66b2e08f?auto=format&fit=crop&w=1800&q=80",
        },
    },
    "faro_events_hero": {
        "title": "Hero — Eventos",
        "content": {
            "eyebrow": "Calendario de Comunidad",
            "title": "Nuestra Agenda",
            "description": "Espacios diseñados para el crecimiento, la conexión y la guía espiritual.",
        },
    },
    "faro_testimonios_hero": {
        "title": "Hero — Testimonios",
        "content": {
            "eyebrow": "Impacto Real",
            "title_lead": "Historias de",
            "title_accent": "Transformación",
            "description": "Descubre cómo la fe y la comunidad han iluminado el camino de personas reales.",
        },
    },
    "faro_sermons_hero": {
        "title": "Hero — Prédicas",
        "content": {
            "eyebrow": "Mensaje Destacado",
            "title_lead": "Alimento para el",
            "title_accent": "Alma",
            "description": "Explora nuestra biblioteca de mensajes que iluminan el camino.",
        },
    },
    "faro_courses_hero": {
        "title": "Hero — Cursos",
        "content": {
            "eyebrow": "Formación y Sabiduría",
            "title_lead": "El Camino",
            "title_accent": "del Faro",
            "description": "Explora cursos y recursos para profundizar tu fe.",
        },
    },
    "faro_courses_feed": {
        "title": "Contenido — Cursos",
        "content": {
            "hero_image_url": "https://picsum.photos/seed/1481627834876-b7833e8f5570/1920/1080",
            "featured_fallback_image_url": "https://picsum.photos/seed/1524178232363-1fb2b075b655/800/600",
            "cta_images": [
                {"src": "https://picsum.photos/seed/academia1/800/800", "alt": "Estudio"},
                {"src": "https://picsum.photos/seed/academia2/800/800", "alt": "Librería"},
            ],
            "library_title": "Nuestra Librería",
            "library_description": "Una curaduría de obras que han transformado generaciones.",
            "empty_books_message": "Próximamente tendremos libros disponibles.",
            "courses_title": "Cursos & Academia",
            "courses_description": "Programas estructurados para líderes, estudiantes y buscadores de la verdad.",
        },
    },
    "faro_discover_hero": {
        "title": "Hero — Conocer a Jesús",
        "content": {
            "eyebrow": "Inicia Tu Camino",
            "title_lead": "La Luz que",
            "title_accent": "Guía",
            "title_tail": "Tu Vida.",
            "description": "El comienzo de una relación que transforma tu historia.",
            "cta": "Quiero conocer a Jesús",
            "bg_image": "https://picsum.photos/seed/1518623489648-a173ef7824f3/800/600",
        },
    },
    "faro_discover_feed": {
        "title": "Contenido — Conocer a Jesús",
        "content": {
            "intro_title": "Un Encuentro Personal",
            "intro_paragraph_1": "En FARO, creemos que cada historia es única. No importa dónde hayas estado o qué hayas hecho, la invitación es la misma: Ven y ve.",
            "intro_paragraph_2": "Descubre un espacio donde las preguntas son bienvenidas y la gracia es el lenguaje principal.",
            "testimonials_title": "Historias que iluminan",
            "testimonials_empty_title": "Próximamente compartiremos historias de transformación.",
            "contact_title": "Hablemos de Tu Caminar",
            "contact_description": "¿Tienes dudas? ¿Quieres orar por algo específico? Nuestro equipo está aquí para acompañarte sin juicios.",
            "name_label": "Nombre completo",
            "name_placeholder": "Tu nombre",
            "phone_label": "WhatsApp",
            "phone_placeholder": "+57 300...",
            "message_label": "¿En qué podemos ayudarte?",
            "message_placeholder": "Cuéntanos un poco sobre ti o tu petición de oración...",
            "submit_label": "Enviar mensaje y conectar",
            "benefits": [
                {"icon": "Heart", "title": "Gracia sin condenas", "desc": "Eres bienvenido tal como eres."},
                {"icon": "Star", "title": "Propósito real", "desc": "Descubre para qué fuiste creado."},
                {"icon": "Shield", "title": "Comunidad que cuida", "desc": "No estarás solo en este camino."},
                {"icon": "ArrowRight", "title": "Primer paso simple", "desc": "Escríbenos y conectamos."},
            ],
            "contact_info": [
                {"icon": "Clock", "text": "Respuesta en menos de 24 horas"},
                {"icon": "Mail", "text": "soporte@ccf.la"},
            ],
        },
    },
    "faro_home_feed": {
        "title": "Contenido — Inicio",
        "content": {
            "eyebrow": "Nuestra esencia",
            "section_title": "Bienvenidos a Casa",
            "section_description": "Rutas públicas para conocer la comunidad, profundizar en la fe y encontrar dónde dar el siguiente paso.",
            "featured_card": {
                "title": "Conocer a Jesús",
                "desc": "Descubre la base de nuestra fe a través de un viaje personal y transformador. En FARO, te acompañamos en cada paso.",
                "href": "/conocer-a-jesus",
                "cta": "Empezar el camino",
                "img": "https://images.unsplash.com/photo-1519671482749-fd09be7ccebf?w=900&q=80",
                "alt": "Reunión de personas en comunidad",
            },
            "cards": [
                {
                    "title": "Librería",
                    "desc": "Recursos para profundizar en tu estudio bíblico.",
                    "href": "/cursos",
                    "img": "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=600&q=80",
                    "alt": "Libros y estudio",
                },
                {
                    "title": "Horarios",
                    "desc": "Reuniones presenciales y online cada semana.",
                    "href": "/eventos",
                    "img": "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?w=600&q=80",
                    "alt": "Conferencia y reunión",
                },
                {
                    "title": "Sedes",
                    "desc": "Encuéntranos en tu ciudad.",
                    "href": "/sedes",
                    "img": "https://images.unsplash.com/photo-1438032005730-c779502df39b?w=600&q=80",
                    "alt": "Lugar de reunión",
                },
            ],
        },
    },

    # ── NOSOTROS ────────────────────────────────────────────────────────────
    "faro_about_hero": {
        "title": "Hero — Quiénes Somos",
        "content": {
            "eyebrow": "Nuestra Identidad",
            "title_lead": "Iluminando el",
            "title_accent": "camino juntos.",
            "description": "Somos la <strong>Comunidad Cristiana El Faro</strong>, una iglesia viva y en crecimiento que existe para conectar corazones con Dios y entre sí, fundamentada en la Palabra y movida por el amor.",
        },
    },
    "faro_about_feed": {
        "title": "Contenido — Quiénes Somos",
        "content": {
            "stats": [
                {"value": "+20", "label": "Años de ministerio"},
                {"value": "+8",  "label": "Pastores activos"},
                {"value": "+500","label": "Familias"},
                {"value": "3",   "label": "Sedes"},
            ],
            "vision_title": "¿A dónde vamos?",
            "vision_text": "Ser una comunidad de fe que <strong>transforma vidas, familias y ciudades</strong> a través del poder del Evangelio, levantando discípulos que reflejen el carácter de Cristo en cada esfera de la sociedad.",
            "mision_title": "¿Por qué existimos?",
            "mision_text": "Guiar, equipar y movilizar a cada persona de nuestra comunidad mediante la <strong>enseñanza bíblica profunda</strong>, el compañerismo genuino y el servicio desinteresado — llevando la luz de Cristo a donde haya oscuridad.",
            "founder_label": "Nuestros Pastores Principales",
            "founder_title": "Un llamado a construir",
            "founder_title_accent": "una familia de fe",
            "founder1_name": "Luis Ricardo Meza G.",
            "founder1_role": "Pastor Principal",
            "founder1_image": "/images/pastores/luis_ricardo_meza.webp",
            "founder2_name": "Histar Ariza Herrera",
            "founder2_role": "Pastor Principal",
            "founder2_image": "/images/pastores/histar_ariza.webp",
            "founder_bio": "La Comunidad Cristiana El Faro nació de un profundo encuentro con la paternidad de Dios. Nuestros pastores principales, <strong>Luis Ricardo Meza Gutiérrez</strong> e <strong>Histar Ariza Herrera</strong>, han dedicado más de dos décadas a construir una iglesia que sea verdaderamente una casa — un lugar donde cada persona sea vista, amada y formada.",
            "founder_bio2": "Desde sus inicios, el ADN de El Faro ha sido claro: <em>sana doctrina, corazón pastoral y vida en comunidad</em>. Una iglesia que no teme enseñar la Palabra en su profundidad y que, al mismo tiempo, envuelve a cada persona con la calidez del amor de Cristo.",
            "valores_title": "Valores que nos Guían",
            "valores": [
                {"num": "01", "key": "palabra",    "title": "Palabra",       "desc": "La Escritura es nuestra brújula. Cada decisión, enseñanza y acción está fundamentada en la sana doctrina de la Biblia."},
                {"num": "02", "key": "amor",       "title": "Amor Radical",  "desc": "Un compromiso inquebrantable de servir y acoger a todos, sin importar su historia, origen o camino recorrido."},
                {"num": "03", "key": "comunidad",  "title": "Comunidad",     "desc": "Creemos en la vida en familia. El crecimiento espiritual genuino ocurre en relación auténtica con otros."},
                {"num": "04", "key": "integridad", "title": "Integridad",    "desc": "Vivir con coherencia entre lo que creemos y lo que hacemos, permitiendo que nuestra fe sea visible en cada área de la vida."},
                {"num": "05", "key": "mision",     "title": "Misión",        "desc": "No existimos solo para nosotros mismos. Somos enviados a alcanzar a los que aún no conocen el amor de Cristo."},
                {"num": "06", "key": "excelencia", "title": "Excelencia",    "desc": "Damos lo mejor de nosotros en todo lo que hacemos, como un acto de adoración y respeto a quien nos llamó."},
            ],
            "quote_text": "La luz que encontramos en El Faro no es para guardarla — es para guiar a otros que aún caminan en la oscuridad.",
            "quote_author": "Pastor Histar Ariza Herrera",
            "quote_subtitle": "Comunidad Cristiana El Faro",
            "cta_title": "¿Listo para ser parte?",
            "cta_desc": "Ven a conocernos. Tenemos puertas abiertas y un lugar reservado para ti y tu familia.",
        },
    },

    # ── PASTORES ────────────────────────────────────────────────────────────
    "faro_pastores_hero": {
        "title": "Hero — Pastores",
        "content": {
            "title": "Liderazgo Pastoral",
            "description": "Hombres y mujeres llamados por Dios para servir, guiar y amar a esta casa.",
        },
    },
    "faro_pastores_feed": {
        "title": "Grid — Pastores",
        "content": {
            "pastors": [
                {
                    "slug": "luis-ricardo-meza",
                    "name": "Luis Ricardo Meza Gutiérrez",
                    "role": "Pastor Principal",
                    "image": "/images/pastores/luis_ricardo_meza.webp",
                    "isMain": True,
                    "story": "Un testimonio de transformación profunda y pasión inagotable por la enseñanza de la Palabra.",
                    "quote": "La Palabra de Dios, correctamente dividida, es el alimento que da vida a la Iglesia.",
                    "verse": "Esdras 7:10",
                },
                {
                    "slug": "histar-ariza",
                    "name": "Histar Ariza Herrera",
                    "role": "Pastor Principal",
                    "image": "/images/pastores/histar_ariza.webp",
                    "isMain": True,
                    "story": "El llamado pastoral, la visión de expansión y el corazón de paternidad espiritual que guía a nuestra congregación.",
                    "quote": "Nuestra mayor recompensa es ver corazones transformados por el amor del Padre.",
                    "verse": "Jeremías 3:15",
                },
                {
                    "slug": "alex-y-elvia",
                    "name": "Alex y Elvia",
                    "role": "Pastores de Familias",
                    "image": "/images/pastores/alex_elvia.webp",
                    "story": "Un testimonio vivo de gracia enfocado en la restauración matrimonial y el ministerio familiar.",
                },
                {
                    "slug": "alba-arias",
                    "name": "Alba Arias",
                    "role": "Pastora",
                    "image": "/images/pastores/camilo_alba.webp",
                    "quote": "Mi mayor gozo no está en una posición o en un título, sino en pertenecer a la obra de Dios y ser útil en sus manos.",
                    "verse": "Juan 3:16",
                    "story": "<p>Antes de llegar a la Comunidad Cristiana El Faro, la Pastora Alba Arias no había tenido acercamientos a ninguna iglesia ni una relación personal con Dios. Fue en este lugar donde experimentó la presencia del Espíritu Santo por primera vez, un encuentro que transformó su carácter, sanó su corazón y le dio una profunda identidad como hija amada. Esta revelación de la bondad del Padre la impulsó a compartir su amor con otros.</p><blockquote>\"Elijo Juan 3:16 porque nos muestra la esencia misma de lo que Él es y lo que quiere con cada uno de nosotros.\"</blockquote><p>Lo que más le apasiona es enseñar, una vocación que también constituye su profesión. Alba cree firmemente que la educación transforma vidas y que, a través de ella, Dios le concede el privilegio de sembrar conocimiento y valores eternos en el corazón de cada estudiante.</p><p><strong>Perfil Ministerial:</strong> A lo largo de su servicio en la casa de Dios, Alba ha apoyado en múltiples áreas. Comenzó colaborando en la limpieza del templo y en diversas tareas logísticas; posteriormente se integró al equipo de bienvenida para recibir con amor a todos los que llegaban. Más adelante sirvió en el ministerio infantil (sala cuna y escuela dominical), sembrando principios bíblicos en la niñez. Actualmente se desempeña en el ministerio pastoral, apoyando a los pastores principales en las áreas administrativa y financiera.</p><p><strong>Perfil Familiar:</strong> Está casada con el Pastor Camilo Pájaro, a quien conoció en su etapa escolar. Juntos comenzaron asistiendo a los servicios de madrugón. Aunque en los inicios de su relación vivieron altibajos que los llevaron a separarse durante un año —período en el que Alba se alejó temporalmente de la iglesia—, el Señor restauró su lazo amoroso y ella regresó a El Faro. En 2014 se bautizaron y se casaron. En doce años de matrimonio, el Padre los ha sustentado y hecho crecer ministerialmente. Hoy en día, tienen dos hermosas hijas, Sara Valentina y Shaddai Antonella, y su historia es un testimonio de la fidelidad y provisión divina.</p>",
                },
                {
                    "slug": "camilo-pajaro",
                    "name": "Camilo Pájaro",
                    "role": "Pastor",
                    "image": "/images/pastores/camilo_alba.webp",
                    "quote": "He entendido que si es Él quien me guía y me dirige, en mi vida todo terminará ayudando para bien.",
                    "verse": "Salmo 23:1",
                    "story": "<p>Antes de conocer al Señor, Camilo Pájaro vivía una vida volcada al baile, la música secular y su mayor prioridad: el béisbol, deporte en el cual se formaba activamente. Sin embargo, Dios intervino de forma providencial, llamándolo a abandonar lo que creía que era su propósito terrenal para alinear su vida con su propósito eterno. Llegó a los pies del Señor con inseguridades y maldiciones generacionales, de las cuales fue totalmente libertado por el amor y la misericordia divina.</p><blockquote>\"He entendido que si es Él quien me guía y me dirige, en mi vida todo terminará ayudando para bien.\"</blockquote><p>A Camilo le apasiona habitar en la presencia de Dios, cultivar una relación cercana con el Padre y agradarle en todo. Asimismo, tiene un pfofundo celo por las almas perdidas, sintiendo el llamado de apoyar a quienes andan sin rumbo y guiarlos de vuelta a la senda de Cristo.</p><p><strong>Perfil Ministerial:</strong> Su caminar en el servicio comenzó desde las tareas más sencillas, limpiando y colaborando con el aseo del templo. A medida que crecía espiritualmente, Dios abrió puertas en su liderazgo: se desempeñó como maestro de la Academia de Formación Ministerial, ministro de alabanza y miembro destacado de la agrupación musical Sonido de Gloria, y hoy en día sirve en el ministerio pastoral.</p><p><strong>Perfil Familiar:</strong> Está casado con la Pastora Alba Arias, con quien comparte su vida y ministerio. Se conocieron en el colegio y dieron sus primeros pasos espirituales asistiendo a los madrugones de la iglesia. Tras superar una separación de un año, se bautizaron y casaron en el 2014. Hoy, junto a sus hijas Sara Valentina y Shaddai Antonella, testifican que el Señor ha sido su sustento inquebrantable durante doce años de matrimonio.</p>",
                },
                {
                    "slug": "fernando-y-monica",
                    "name": "Fernando y Mónica",
                    "role": "Pastores de Discipulado",
                    "image": "/images/pastores/fernando_monica.webp",
                    "story": "La historia de la fidelidad, el servicio incondicional y el acompañamiento constante.",
                },
                {
                    "slug": "nehemias-morales",
                    "name": "Nehemías Morales",
                    "role": "Pastor de Consolidación",
                    "image": "/images/pastores/nehemias_morales.webp",
                    "story": "Enfocado en la resiliencia, la construcción de comunidad y la fe inquebrantable.",
                },
                {
                    "slug": "yair-macea",
                    "name": "Yair Macea",
                    "role": "Pastor Evangelístico",
                    "image": "/images/pastores/yair_macea.webp",
                    "story": "Un relato de gracia abrumadora, superación personal y un fuego evangelístico inextinguible.",
                },
                {
                    "slug": "yanedith-wilches",
                    "name": "Yanedith Wilches",
                    "role": "Pastora de Intercesión",
                    "image": "/images/pastores/yanedith_wilches.webp",
                    "story": "La fuerza inquebrantable de una mujer virtuosa, la intercesión y la compasión por los vulnerables.",
                },
            ]
        },
    },

    # ── SEDES ───────────────────────────────────────────────────────────────
    "faro_locations_hero": {
        "title": "Hero — Sedes",
        "content": {
            "eyebrow": "Nuestra Presencia",
            "title": "Nuestras Sedes",
            "search_placeholder": "Buscar ciudad o dirección...",
            "map_embed_url": "https://www.google.com/maps/d/embed?mid=1VDNpplw_9z1tcEhx25wEFRR5gQmnHgM&ehbc=2E312F",
        },
    },
    "faro_locations_feed": {
        "title": "Listado — Sedes",
        "content": [
            {
                "id": 1,
                "name": "Sede Central — El Faro",
                "address": "Barranquilla, Colombia",
                "phone": "+57 300 000 0000",
                "schedule": "Domingos 9 AM y 11 AM",
                "midweek": "Lunes 7 PM — Reunión de Célula",
                "isMain": True,
                "services": ["Domingos 9 AM", "Domingos 11 AM", "Lunes 7 PM"],
            },
            {
                "id": 2,
                "name": "Campus Norte",
                "address": "Norte de Barranquilla, Colombia",
                "phone": "+57 310 111 2222",
                "schedule": "Domingos 10 AM",
                "midweek": "Sábados 6 PM",
                "isMain": False,
                "services": ["Domingos 10 AM", "Sábados 6 PM"],
            },
            {
                "id": 3,
                "name": "Campus Sur",
                "address": "Sur de Barranquilla, Colombia",
                "phone": "+57 320 222 3333",
                "schedule": "Domingos 10 AM",
                "midweek": "Miércoles 7 PM",
                "isMain": False,
                "services": ["Domingos 10 AM", "Miércoles 7 PM"],
            },
        ],
    },
    "faro_footer": {
        "title": "Footer público FARO",
        "content": {
            "description": (
                "Iluminando el camino hacia una conexión profunda con lo divino "
                "a través de la comunidad y la guía espiritual. "
                "Una casa de fe abierta para toda la familia."
            ),
            "nav_links": [
                {"href": "/", "label": "Inicio"},
                {"href": "/nosotros", "label": "Sobre Nosotros"},
                {"href": "/pastores", "label": "Pastores"},
                {"href": "/eventos", "label": "Eventos"},
                {"href": "/predicas", "label": "Prédicas"},
                {"href": "/cursos", "label": "Cursos"},
            ],
            "resource_links": [
                {"href": "/conocer-a-jesus", "label": "Conocer a Jesús"},
                {"href": "/testimonios", "label": "Testimonios"},
                {"href": "/sedes", "label": "Sedes"},
                {"href": "/boletin", "label": "Boletín"},
            ],
            "social_links": [
                {"href": "https://facebook.com/comunidadfaro", "label": "Facebook", "kind": "facebook"},
                {"href": "https://instagram.com/comunidadfaro", "label": "Instagram", "kind": "instagram"},
                {"href": "https://youtube.com/comunidadfaro", "label": "YouTube", "kind": "youtube"},
            ],
            "location_label": "Cartagena, Colombia",
            "newsletter_label": "Boletín semanal",
        },
    },
    "faro_mobile_nav": {
        "title": "Navegación móvil FARO",
        "content": {
            "items": [
                {"href": "/", "label": "Inicio", "icon": "home"},
                {"href": "/eventos", "label": "Eventos", "icon": "calendar"},
                {"href": "/predicas", "label": "Prédicas", "icon": "play"},
                {"href": "/sedes", "label": "Sedes", "icon": "map-pin"},
                {"href": "/conocer-a-jesus", "label": "Conectar", "icon": "menu"},
            ]
        },
    },

    # ── BIENVENIDA / PRIVACIDAD ─────────────────────────────────────────────
    "faro_welcome": {
        "title": "Bienvenida pública FARO",
        "content": {
            "eyebrow": "Bienvenida",
            "title_template": "Hola, {name}.",
            "description": "No encontramos una cuenta registrada todavía, pero no te dejamos en una pantalla vacía.",
            "primary_cta": {"href": "/cursos", "label": "Discipulado Básico"},
            "secondary_cta": {"href": "/conocer-a-jesus", "label": "Una nueva vida con Cristo"},
            "highlights": [
                {
                    "title": "Discipulado Básico",
                    "description": "Empieza por la ruta de fundamentos para crecer con orden y acompañamiento.",
                    "href": "/cursos",
                    "cta": "Ver academia",
                    "icon": "book",
                },
                {
                    "title": "Una nueva vida con Cristo",
                    "description": "Conoce el mensaje central del evangelio en una ruta pública y clara.",
                    "href": "/conocer-a-jesus",
                    "cta": "Abrir ruta",
                    "icon": "heart",
                },
            ],
        },
    },
    "faro_privacy": {
        "title": "Política de privacidad FARO",
        "content": {
            "last_update": "12 de junio de 2026",
            "summary": "Esta política describe cómo PLES SAS y la Comunidad Cristiana El Faro recopilan, usan, almacenan y protegen tus datos personales.",
            "sections": [
                {"id": "responsables", "title": "1. Responsables del tratamiento"},
                {"id": "datos-recopilados", "title": "2. Datos que recopilamos"},
                {"id": "finalidades", "title": "3. Finalidades del tratamiento"},
                {"id": "bases-legales", "title": "4. Bases legales"},
                {"id": "derechos", "title": "5. Derechos del titular"},
                {"id": "procedimiento", "title": "6. Procedimiento para ejercer derechos"},
                {"id": "terceros", "title": "7. Transferencia y transmisión a terceros"},
                {"id": "cookies", "title": "8. Cookies y tecnologías similares"},
                {"id": "menores", "title": "9. Menores de edad"},
                {"id": "seguridad", "title": "10. Seguridad de la información"},
                {"id": "conservacion", "title": "11. Conservación de datos"},
                {"id": "cambios", "title": "12. Cambios a esta política"},
                {"id": "contacto", "title": "13. Canal de atención"},
            ],
        },
    },

    # ── NAV GLOBAL ──────────────────────────────────────────────────────────
    "faro_nav_items": {
        "title": "Menú de Navegación",
        "content": {
            "items": [
                {"label": "Inicio",          "href": "/"},
                {"label": "Quiénes Somos",   "href": "/nosotros"},
                {"label": "Pastores",         "href": "/pastores"},
                {"label": "Eventos",          "href": "/eventos"},
                {"label": "Prédicas",         "href": "/predicas"},
                {"label": "Cursos",           "href": "/cursos"},
                {"label": "Sedes",            "href": "/sedes"},
                {"label": "Conocer a Jesús",  "href": "/conocer-a-jesus"},
            ]
        },
    },
}


# ── Runner ───────────────────────────────────────────────────────────────────

def upsert_block(conn, page_key: str, title: str, content: dict | list):
    content_str = json.dumps(content, ensure_ascii=False)
    
    # Query existing row
    row = conn.execute(
        text("SELECT page_key, title, content FROM page_contents WHERE page_key = :page_key"),
        {"page_key": page_key}
    ).fetchone()
    
    if row:
        # Save previous version
        conn.execute(
            text("""
                INSERT INTO page_content_versions (page_key, title, content, created_at)
                VALUES (:page_key, :title, :content, NOW())
            """),
            {"page_key": row[0], "title": row[1], "content": row[2]}
        )
        # Update current row
        conn.execute(
            text("""
                UPDATE page_contents
                SET title = :title, content = :content, updated_at = NOW()
                WHERE page_key = :page_key
            """),
            {"title": title, "content": content_str, "page_key": page_key}
        )
        action = "updated"
    else:
        # Insert current row
        conn.execute(
            text("""
                INSERT INTO page_contents (page_key, title, content, created_at, updated_at)
                VALUES (:page_key, :title, :content, NOW(), NOW())
            """),
            {"page_key": page_key, "title": title, "content": content_str}
        )
        action = "created"
    
    return action


def run():
    conn = engine.connect()
    trans = conn.begin()
    try:
        print(f"\n{'='*60}")
        print("  Seed — Contenido público CMS (Raw SQL Mode)")
        print(f"{'='*60}\n")
        ok = err = 0
        for key, data in BLOCKS.items():
            try:
                action = upsert_block(conn, key, data["title"], data["content"])
                print(f"  ✓  [{action:7}]  {key}")
                ok += 1
            except Exception as e:
                print(f"  ✗  [error  ]  {key}: {e}")
                trans.rollback()
                trans = conn.begin()
                err += 1
        trans.commit()
        print(f"\n  Total: {ok} OK, {err} errores\n")
    finally:
        conn.close()


if __name__ == "__main__":
    run()
