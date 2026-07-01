"""Default copy and configuration for public CMS blocks."""

from __future__ import annotations

PAGE_CONTENT_DEFAULTS = {
    "navbar_items": {
        "content": {
            "items": [
                {"label": "Inicio", "href": "/"},
                {"label": "Academia", "href": "/academy"},
                {"label": "Pr??dicas", "href": "/sermons"},
                {"label": "Libros", "href": "/books"},
                {"label": "Eventos", "href": "/events"},
                {"label": "Donaciones", "href": "/donate"},
            ]
        }
    },
    "home_hero": {
        "title": "Una iglesia en movimiento",
        "image_url": "https://images.unsplash.com/photo-1504051771394-dd2e66b2e08f?auto=format&fit=crop&w=1800&q=80",
        "content": {
            "subtitle": "Somos una comunidad digital y presencial que discipula, sirve y ama a la ciudad.",
            "cta_primary": "Explorar la Academia",
            "cta_secondary": "Ver Pr??dicas Recientes",
        },
    },
    "home_academy_card": {
        "title": "Academia Faro",
        "content": "Formaci??n b??blica y certificados ministeriales en rutas formales y no formales.",
    },
    "home_giving_card": {
        "title": "Dar con Prop??sito",
        "content": "Diezmos, ofrendas y campa??as especiales para sostener la misi??n en cada campus.",
    },
    "home_community_card": {
        "title": "Casas de Gloria",
        "content": "Encuentra un grupo cercano para crecer en la fe y vivir acompa??ado.",
    },
    "home_prayer_banner": {
        "title": "Peticiones de Oraci??n",
        "content": "Nuestro equipo responde cada d??a. Cu??ntanos c??mo podemos orar contigo.",
    },
    "home_impact_stats": {
        "content": {"courses": "42", "impact": "+3.2K", "volunteers": "780"}
    },
    "academy_hero": {
        "title": "Tu pr??xima clase empieza hoy",
        "content": "Contin??a tu proceso con cohortes guiadas, mentores y evaluaciones acreditadas.",
    },
    "academy_welcome_sub": {
        "title": "Portal estudiantil",
    },
    "donation_types": {
        "content": {
            "categories": [
                {
                    "id": "Diezmo",
                    "label": "Diezmo",
                    "icon": "Building",
                    "description": "Honra a Dios con el 10% de tus ingresos y s?? parte del avance de la iglesia.",
                },
                {
                    "id": "Ofrenda General",
                    "label": "Ofrenda General",
                    "icon": "Heart",
                    "description": "Sost??n proyectos pastorales, ayuda humanitaria y nuevas plantaciones.",
                },
                {
                    "id": "Misi??n Global",
                    "label": "Misi??n Global",
                    "icon": "Globe",
                    "description": "Impulsa la obra misionera y el entrenamiento de l??deres en otras ciudades.",
                },
            ]
        }
    },
    "support_page": {
        "title": "Centro de Ayuda",
        "content": {
            "description": "Nuestro equipo responde de lunes a s??bado. Elige el ??rea y abre un ticket.",
            "categories": [
                {
                    "title": "Soporte T??cnico",
                    "desc": "Acceso, contrase??as, problemas de video o sonido.",
                    "type": "tech",
                },
                {
                    "title": "Academia",
                    "desc": "Pagos, certificados, inscripciones y tareas.",
                    "type": "academic",
                },
                {
                    "title": "Pastoral",
                    "desc": "Consejer??a, visitas y acompa??amiento espiritual.",
                    "type": "pastoral",
                },
            ],
        },
    },
    "sermons_hero": {
        "title": "Biblioteca de Pr??dicas",
        "image_url": "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=1600&q=80",
        "content": {
            "subtitle": "Serie tras serie, descubre mensajes que forman, inspiran y activan tu fe.",
            "cta_label": "Ver ??ltimo mensaje",
        },
    },
    "books_hero": {
        "title": "Biblioteca Digital",
        "image_url": "https://images.unsplash.com/photo-1455885666463-1ef414b56a8b?auto=format&fit=crop&w=1600&q=80",
        "content": "Descarga manuales y libros recomendados por nuestros pastores.",
    },
    "testimonials_hero": {
        "title": "Historias de transformaci??n",
        "image_url": "https://images.unsplash.com/photo-1519687125932-bf58b84f31d3?auto=format&fit=crop&w=1600&q=80",
        "content": {
            "subtitle": "Cada semana recibimos testimonios de sanidad, provisi??n y restauraci??n.",
        },
    },
    "events_hero": {
        "title": "Agenda Viva",
        "image_url": "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?auto=format&fit=crop&w=1600&q=80",
        "content": {
            "subtitle": "Conoce los encuentros presenciales y online para servir, aprender y celebrar juntos.",
            "cta_label": "Descargar calendario",
        },
    },
    "privacy_policy": {
        "title": "Pol??tica de Privacidad",
        "content": {
            "subtitle": "Cuidamos tus datos personales con transparencia y responsabilidad.",
            "content": "Recopilamos la informaci??n necesaria para gestionar tu experiencia acad??mica y pastoral. Nunca vendemos ni compartimos tus datos con terceros no autorizados. Puedes solicitar la eliminaci??n de tu cuenta escribiendo a soporte@ccf.la.",
        },
    },
    "terms_of_service": {
        "title": "T??rminos de Servicio",
        "content": {
            "subtitle": "El uso de la plataforma implica aceptar estas condiciones.",
            "content": "Usa los materiales ??nicamente para tu crecimiento espiritual, respeta a otros participantes y evita compartir accesos. Las evaluaciones son personales y sujetas al reglamento acad??mico vigente.",
        },
    },
    "onboarding_page": {
        "content": {
            "steps": [
                {
                    "id": 1,
                    "title": "Herramientas para tu fe",
                    "description": "Sigue tus cursos, grupos y devocionales desde cualquier dispositivo.",
                    "features": [
                        {
                            "title": "Crecimiento",
                            "desc": "Planifica lecturas y tareas cada semana.",
                            "icon": "BookOpen",
                        },
                        {
                            "title": "Comunidad",
                            "desc": "Con??ctate a chats y reuniones h??bridas.",
                            "icon": "Users",
                        },
                        {
                            "title": "Prop??sito",
                            "desc": "Descubre nuevas ??reas de servicio.",
                            "icon": "Heart",
                        },
                    ],
                },
                {
                    "id": 2,
                    "title": "Personaliza tu experiencia",
                    "description": "Elige tu campus, activa notificaciones y recibe recordatorios.",
                    "features": [],
                },
            ]
        }
    },
    "faro_nav_items": {
        "title": "Navegacion FARO",
        "content": {
            "items": [
                {"label": "Sobre Nosotros", "href": "/faro/nosotros"},
                {"label": "Testimonios", "href": "/faro/testimonios"},
                {"label": "Eventos", "href": "/faro/eventos"},
                {"label": "Predicas", "href": "/faro/predicas"},
                {"label": "Cursos", "href": "/faro/cursos"},
                {"label": "Sedes", "href": "/faro/sedes"},
            ]
        },
    },
    "faro_home_hero": {
        "title": "Inicio FARO",
        "content": {
            "eyebrow": "Comunidad FARO",
            "title_lead": "Ilumina tu",
            "title_accent": "Camino",
            "description": "Una comunidad vibrante donde la fe encuentra propósito.",
            "primary_cta": "Únete a nosotros",
            "secondary_cta": "Ver Predicaciones",
            "bg_image": "https://images.unsplash.com/photo-1504051771394-dd2e66b2e08f?auto=format&fit=crop&w=1800&q=80",
        },
    },
    "faro_events_hero": {
        "title": "Eventos FARO",
        "content": {
            "eyebrow": "Calendario de Comunidad",
            "title": "Nuestra Agenda",
            "description": "Espacios diseñados para el crecimiento, la conexión y la guía espiritual.",
        },
    },
    "faro_public_events": {
        "title": "Agenda Publica FARO",
        "content": [
            {
                "title": "Noche de Iluminación: Adoración y Palabra",
                "date": "24 DE JUNIO, 2024",
                "location": "Auditorio Central",
                "excerpt": "Encuentro especial de adoración y enseñanza.",
                "category": "Destacado",
                "featured": True,
            },
            {
                "title": "Cena de Jóvenes",
                "date": "12",
                "location": "Sede Norte • 19:30 hrs",
                "excerpt": "Espacio de comunidad y conexión.",
                "category": "Jóvenes",
                "featured": False,
            },
        ],
    },
    "faro_testimonios_hero": {
        "title": "Testimonios FARO",
        "content": {
            "eyebrow": "Impacto Real",
            "title_lead": "Historias de",
            "title_accent": "Transformación",
            "description": "Descubre cómo la fe y la comunidad han iluminado vidas reales.",
        },
    },
    "faro_sermons_hero": {
        "title": "Predicas FARO",
        "content": {
            "eyebrow": "Mensaje Destacado",
            "title_lead": "Alimento para el",
            "title_accent": "Alma",
            "description": "Explora nuestra biblioteca de mensajes que iluminan el camino.",
        },
    },
    "faro_courses_hero": {
        "title": "Cursos FARO",
        "content": {
            "eyebrow": "Formación y Sabiduría",
            "title_lead": "El Camino",
            "title_accent": "del Faro",
            "description": "Explora cursos y recursos para profundizar tu fe.",
        },
    },
    "faro_courses_feed": {
        "title": "Cursos FARO — Contenido",
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
            "courses_description": "Programas estructurados para líderes, participantes y buscadores de la verdad.",
            "featured_course_id": None,
            "show_free_only": False,
        },
    },
    "faro_discover_hero": {
        "title": "Conocer a Jesus FARO",
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
        "title": "Conocer a Jesus FARO — Contenido",
        "content": {
            "intro_title": "Un Encuentro Personal",
            "intro_paragraph_1": "En FARO, creemos que cada historia es única. No importa dónde hayas estado o qué hayas hecho, la invitación es la misma: Ven y ve.",
            "intro_paragraph_2": "Descubre un espacio donde las preguntas son bienvenidas y la gracia es el lenguaje principal.",
            "testimonials_title": "Historias que iluminan",
            "testimonials_empty_title": "Próximamente compartiremos historias de transformación.",
            "contact_title": "Hablemos de Tu Caminar",
            "contact_description": "¿Tienes dudas? ¿Quieres orar por algo específico? Nuestro equipo está aquí para acompañarte sin juicios.",
            "contact_email": "",
            "contact_phone": "",
            "contact_address": "",
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
    "faro_about_hero": {
        "title": "Nosotros FARO",
        "content": {
            "eyebrow": "Nuestra Identidad",
            "title_lead": "Iluminando el",
            "title_accent": "camino juntos",
            "description": "Somos una comunidad vibrante dedicada a guiar personas hacia una vida con propósito.",
        },
    },
    "faro_locations_hero": {
        "title": "Sedes FARO",
        "content": {
            "eyebrow": "Nuestra Presencia",
            "title": "Nuestras Sedes",
            "search_placeholder": "Buscar ciudad o dirección...",
            "map_embed_url": "https://www.google.com/maps/d/embed?mid=1VDNpplw_9z1tcEhx25wEFRR5gQmnHgM&ehbc=2E312F",
        },
    },
    "faro_footer": {
        "title": "Footer FARO",
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
    "faro_testimonials_feed": {
        "title": "Testimonios FARO",
        "content": [
            {
                "id": 1,
                "content": "Llegué con ansiedad y hoy tengo paz y comunidad.",
                "emotion": "Restauración",
                "is_approved": True,
                "show_on_home": True,
                "author_id": 1,
                "author": {"id": 1, "username": "Comunidad FARO"},
                "created_at": "2026-01-10T10:00:00Z",
            }
        ],
    },
    "faro_announcements_feed": {
        "title": "Anuncios FARO",
        "content": [
            {
                "id": 1,
                "title": "Congreso de Jóvenes",
                "content": "Inscripciones abiertas en recepción y web.",
                "category": "Eventos",
                "is_active": True,
                "created_at": "2026-01-10T10:00:00Z",
            }
        ],
    },
}
