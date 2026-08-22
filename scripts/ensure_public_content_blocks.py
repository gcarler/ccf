from __future__ import annotations

import sys
from pathlib import Path

# Locate the project root by walking up until we find the `backend/`
# package. This works whether the script lives in scripts/, scripts/seeding/
# scripts/migrations/, scripts/auditing/ or any other nested folder.
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next(
    (p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()),
    None,
)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

"""Seed CMS-managed PageContent blocks used by public pages.

The public React components keep local fallbacks for rollback safety, but these
blocks make the current production copy and navigation editable through CMS.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend import models  # noqa: E402
from backend.core.database import SessionLocal  # noqa: E402

BLOCKS = {
    "ccf_events_feed": {
        "title": "Eventos publico CCF",
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
            "month_names": [
                "Enero",
                "Febrero",
                "Marzo",
                "Abril",
                "Mayo",
                "Junio",
                "Julio",
                "Agosto",
                "Septiembre",
                "Octubre",
                "Noviembre",
                "Diciembre",
            ],
            "week_view_label": "Semanal",
            "month_view_label": "Mensual",
            "year_view_label": "Anual",
        },
    },
    "ccf_sermons_feed": {
        "title": "Prédicas publico CCF",
        "content": {
            "hero_eyebrow": "Ministerios CCF Oficial",
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
    "ccf_testimonials_hero": {
        "title": "Hero — Testimonios",
        "content": {
            "eyebrow": "Impacto Real",
            "title_lead": "Historias de",
            "title_accent": "Transformación",
            "description": "Vidas reales, cambios reales. Así es como el amor de Dios se hace visible en nuestra comunidad.",
        },
    },
    "ccf_testimonials_feed": {
        "title": "Testimonios publico CCF",
        "content": {
            "search_placeholder": "Buscar por tema, nombre o palabra clave",
            "loading_label": "Cargando...",
            "empty_title": "Todavía no hay testimonios publicados",
            "empty_description": "Cuando el CMS publique testimonios, aparecerán aquí.",
            "cta_label": "Compartir mi historia",
            "read_more_label": "Leer más",
            "hero_badge": "Impacto Real",
            "hero_title_lead": "Historias de",
            "hero_title_accent": "Transformación",
            "hero_description": "Descubre cómo la fe y la comunidad han iluminado el camino de personas reales.",
        },
    },
    "ccf_boletin_hero": {
        "title": "Boletín publico CCF",
        "content": {
            "subtitle": "Boletín Semanal CCF",
            "title": "Recibe nuestra palabra de aliento",
            "description": "Cada semana te enviamos una reflexión bíblica, un versículo de ánimo y consejos prácticos para fortalecer tu fe.",
            "cta_text": "Suscribirme ahora",
        },
    },
    "ccf_pastores_index": {
        "title": "Pastores publico CCF",
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
    "ccf_pastores_feed": {
        "title": "Grid — Pastores",
        "content": {
            "pastors": [
                {
                    "slug": "luis-ricardo-meza",
                    "name": "Luis Ricardo Meza Gutiérrez",
                    "role": "Pastor Principal",
                    "image": "/api/static/cms/pastores/db401ca5d8484ed3a15e3b7012a8b14f.webp",
                    "isMain": True,
                    "story": "Un testimonio de transformación profunda y pasión inagotable por la enseñanza de la Palabra.",
                    "quote": "La Palabra de Dios, correctamente dividida, es el alimento que da vida a la Iglesia.",
                    "verse": "Esdras 7:10",
                },
                {
                    "slug": "histar-ariza",
                    "name": "Histar Ariza Herrera",
                    "role": "Pastor Principal",
                    "image": "/api/static/cms/pastores/b84ca87b625d46bdbdd7d9d5bc41f994.webp",
                    "isMain": True,
                    "story": "El llamado pastoral, la visión de expansión y el corazón de paternidad espiritual que guía a nuestra congregación.",
                    "quote": "Nuestra mayor recompensa es ver corazones transformados por el amor del Padre.",
                    "verse": "Jeremías 3:15",
                },
                {
                    "slug": "alex-y-elvia",
                    "name": "Alex y Elvia",
                    "role": "Pastores de Familias",
                    "image": "/api/static/cms/pastores/8ccb39c52051473499a6ed33d6daea5d.webp",
                    "story": "Un testimonio vivo de gracia enfocado en la restauración matrimonial y el ministerio familiar.",
                },
                {
                    "slug": "alba-arias",
                    "name": "Alba Arias",
                    "role": "Pastora",
                    "image": "/api/static/cms/pastores/6f096b6128134a6db6cbc64fd5021fa5.webp",
                    "quote": "Mi mayor gozo no está en una posición o en un título, sino en pertenecer a la obra de Dios y ser útil en sus manos.",
                    "verse": "Juan 3:16",
                    "story": '<p>Antes de llegar a la Comunidad Cristiana CCF, la Pastora Alba Arias no había tenido acercamientos a ninguna iglesia ni una relación personal con Dios. Fue en este lugar donde experimentó la presencia del Espíritu Santo por primera vez, un encuentro que transformó su carácter, sanó su corazón y le dio una profunda identidad como hija amada. Esta revelación de la bondad del Padre la impulsó a compartir su amor con otros.</p><blockquote>"Elijo Juan 3:16 porque nos muestra la esencia misma de lo que Él es y lo que quiere con cada uno de nosotros."</blockquote><p>Lo que más le apasiona es enseñar, una vocación que también constituye su profesión. Alba cree firmemente que la educación transforma vidas y que, a través de ella, Dios le concede el privilegio de sembrar conocimiento y valores eternos en el corazón de cada estudiante.</p><p><strong>Perfil Ministerial:</strong> A lo largo de su servicio en la casa de Dios, Alba ha apoyado en múltiples áreas. Comenzó colaborando en la limpieza del templo y en diversas tareas logísticas; posteriormente se integró al equipo de bienvenida para recibir con amor a todos los que llegaban. Más adelante sirvió en el ministerio infantil (sala cuna y escuela dominical), sembrando principios bíblicos en la niñez. Actualmente se desempeña en el ministerio pastoral, apoyando a los pastores principales en las áreas administrativa y financiera.</p><p><strong>Perfil Familiar:</strong> Está casada con el Pastor Camilo Pájaro, a quien conoció en su etapa escolar. Juntos comenzaron asistiendo a los servicios de madrugón. Aunque en los inicios de su relación vivieron altibajos que los llevaron a separarse durante un año —período en el que Alba se alejó temporalmente de la iglesia—, el Señor restauró su lazo amoroso y ella regresó a CCF. En 2014 se bautizaron y se casaron. En doce años de matrimonio, el Padre los ha sustentado y hecho crecer ministerialmente. Hoy en día, tienen dos hermosas hijas, Sara Valentina y Shaddai Antonella, y su historia es un testimonio de la fidelidad y provisión divina.</p>',
                },
                {
                    "slug": "camilo-pajaro",
                    "name": "Camilo Pájaro",
                    "role": "Pastor",
                    "image": "/api/static/cms/pastores/6f096b6128134a6db6cbc64fd5021fa5.webp",
                    "quote": "He entendido que si es Él quien me guía y me dirige, en mi vida todo terminará ayudando para bien.",
                    "verse": "Salmo 23:1",
                    "story": '<p>Antes de conocer al Señor, Camilo Pájaro vivía una vida volcada al baile, la música secular y su mayor prioridad: el béisbol, deporte en el cual se formaba activamente. Sin embargo, Dios intervino de forma providencial, llamándolo a abandonar lo que creía que era su propósito terrenal para alinear su vida con su propósito eterno. Llegó a los pies del Señor con inseguridades y maldiciones generacionales, de las cuales fue totalmente libertado por el amor y la misericordia divina.</p><blockquote>"He entendido que si es Él quien me guía y me dirige, en mi vida todo terminará ayudando para bien."</blockquote><p>A Camilo le apasiona habitar en la presencia de Dios, cultivar una relación cercana con el Padre y agradarle en todo. Asimismo, tiene un profundo celo por las almas perdidas, sintiendo el llamado de apoyar a quienes andan sin rumbo y guiarlos de vuelta a la senda de Cristo.</p><p><strong>Perfil Ministerial:</strong> Su caminar en el servicio comenzó desde las tareas más sencillas, limpiando y colaborando con el aseo del templo. A medida que crecía espiritualmente, Dios abrió puertas en su liderazgo: se desempeñó como maestro de la Academia de Formación Ministerial, ministro de alabanza y miembro destacado de la agrupación musical Sonido de Gloria, y hoy en día sirve en el ministerio pastoral.</p><p><strong>Perfil Familiar:</strong> Está casado con la Pastora Alba Arias, con quien comparte su vida y ministerio. Se conocieron en el colegio y dieron sus primeros pasos espirituales asistiendo a los madrugones de la iglesia. Tras superar una separación de un año, se bautizaron y casaron en el 2014. Hoy, junto a sus hijas Sara Valentina y Shaddai Antonella, testifican que el Señor ha sido su sustento inquebrantable durante doce años de matrimonio.</p>',
                },
                {
                    "slug": "fernando-y-monica",
                    "name": "Fernando y Mónica",
                    "role": "Pastores de Discipulado",
                    "image": "/api/static/cms/pastores/8469c5cb7ba34701a53cf7775c4431f0.webp",
                    "story": "La historia de la fidelidad, el servicio incondicional y el acompañamiento constante.",
                },
                {
                    "slug": "nehemias-morales",
                    "name": "Nehemías Morales",
                    "role": "Pastor de Consolidación",
                    "image": "/api/static/cms/pastores/32c3590e08c8441f8fc639f56c437819.webp",
                    "story": "Enfocado en la resiliencia, la construcción de comunidad y la fe inquebrantable.",
                },
                {
                    "slug": "yair-macea",
                    "name": "Yair Macea",
                    "role": "Pastor Evangelístico",
                    "image": "/api/static/cms/pastores/407281c20f794aff8ad5feb7e5b67144.webp",
                    "story": "Un relato de gracia abrumadora, superación personal y un fuego evangelístico inextinguible.",
                },
                {
                    "slug": "yanedith-wilches",
                    "name": "Yanedith Wilches",
                    "role": "Pastora de Intercesión",
                    "image": "/api/static/cms/pastores/dec6d24cdea242d5b73630408b14111b.webp",
                    "story": "La fuerza inquebrantable de una mujer virtuosa, la intercesión y la compasión por los vulnerables.",
                },
                {
                    "slug": "martina-herrera",
                    "name": "Martina Herrera",
                    "role": "Pastora Fundadora",
                    "image": "/api/static/cms/pastores/f1233104623743879e328ffdd94abee5.webp",
                    "isMain": True,
                    "story": "Pastora fundadora del ministerio Comunidad Cristiana CCF junto a su esposo, Alejandro Ariza Torres, quien ya partió y está con el Señor.",
                    "bio_short": "Pastora fundadora del ministerio Comunidad Cristiana CCF junto a su esposo, Alejandro Ariza Torres, quien ya partió y está con el Señor.",
                    "bio_full": '<p>La Pastora Martina Herrera es la pastora fundadora del ministerio Comunidad Cristiana CCF. Junto a su esposo, Alejandro Ariza Torres, quien ya partió y está con el Señor, sembró con fe, oración y perseverancia las bases espirituales de esta casa.</p><blockquote>"La obra de Dios se edifica con fe, obediencia y amor por las almas."</blockquote><p>Desde los primeros días del ministerio, la Pastora Martina ha sido un pilar de oración, fidelidad y cuidado pastoral. Su corazón maternal ha acompañado a generaciones de creyentes que encontraron en ella una pastora, una consejera y una madre espiritual.</p><p>Su legado permanece vivo en la familia espiritual de Comunidad Cristiana CCF: una iglesia levantada para amar a Dios, servir a las personas y continuar la obra que el Señor puso en sus manos.</p>',
                },
            ]
        },
    },
    "ccf_courses_feed": {
        "title": "Cursos publico CCF",
        "content": {
            "library_title": "Nuestra Librería",
            "library_description": "Una curaduría de obras que han transformado generaciones. Desde clásicos de la patrística hasta literatura contemporánea.",
            "empty_books_message": "Próximamente tendremos libros disponibles.",
            "courses_title": "Cursos & Academia",
            "courses_description": "Programas estructurados para líderes, estudiantes y buscadores de la verdad. Formación teológica y práctica con estándares de excelencia.",
        },
    },
    "ccf_discover_feed": {
        "title": "Conocer a Jesús publico CCF",
        "content": {
            "intro_title": "Un Encuentro Personal",
            "intro_paragraph_1": "En CCF, creemos que cada historia es única. No importa dónde hayas estado o qué hayas hecho, la invitación es la misma: <strong>Ven y ve.</strong>",
            "intro_paragraph_2": "Descubre un espacio donde las preguntas son bienvenidas y la gracia es el lenguaje principal. Jesús ofrece descanso para el alma y una dirección clara para el futuro.",
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
            "steps": [
                {
                    "num": "01",
                    "title": "Reconoce tu necesidad",
                    "desc": "Todos hemos tomado decisiones que nos alejan de Dios. Ese es el punto de partida: honestidad ante Él.",
                },
                {
                    "num": "02",
                    "title": "Cree en Jesús",
                    "desc": "Jesús murió por tus errores y resucitó. Creer en Él es el acto de fe que lo cambia todo.",
                },
                {
                    "num": "03",
                    "title": "Comienza una nueva vida",
                    "desc": "La fe sin comunidad es frágil. Únete a nosotros para crecer y ser acompañado en este camino.",
                },
            ],
            "prayer_title": "Una oración para comenzar",
            "prayer_text": "Señor Jesús, reconozco que te necesito. Creo que moriste por mí y resucitaste. Te entrego mi vida hoy. Guíame, transfórmame y hazme tuyo. Amén.",
        },
    },
    "ccf_home_feed": {
        "title": "Home publico CCF",
        "content": {
            "eyebrow": "Nuestra esencia",
            "section_title": "Bienvenidos a Casa",
            "section_description": "Rutas públicas para conocer la comunidad, profundizar en la fe y encontrar dónde dar el siguiente paso.",
            "featured_card": {
                "title": "Conocer a Jesús",
                "desc": "Descubre la base de nuestra fe a través de un viaje personal y transformador. En CCF, te acompañamos en cada paso.",
                "href": "/conocer-a-jesus",
                "cta": "Empezar el camino",
                "img": "/api/static/cms/home_banner/a7e9a238a55d464cbf0cb6ff88f29671.webp",
                "alt": "Equipo pastoral de CCF",
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
    "ccf_footer": {
        "title": "Footer publico CCF",
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
                {"href": "https://facebook.com/comunidadccf", "label": "Facebook", "kind": "facebook"},
                {"href": "https://instagram.com/comunidadccf", "label": "Instagram", "kind": "instagram"},
                {"href": "https://youtube.com/comunidadccf", "label": "YouTube", "kind": "youtube"},
            ],
            "location_label": "Cartagena, Colombia",
            "newsletter_label": "Boletín semanal",
            "contact": {
                "email": "contactenos@ministerioselfaro.org",
                "location_label": "Cartagena, Colombia",
                "location_href": "/sedes",
                "newsletter_label": "Boletín semanal",
                "newsletter_href": "/boletin",
            },
            "privacy_href": "/privacy",
        },
    },
    "ccf_mobile_nav": {
        "title": "Navegacion movil publica CCF",
        "content": {
            "items": [
                {"href": "/", "label": "Inicio", "icon": "home"},
                {"href": "/eventos", "label": "Eventos", "icon": "calendar"},
                {"href": "/predicas", "label": "Prédicas", "icon": "play"},
                {"href": "/sedes", "label": "Sedes", "icon": "map-pin"},
            ]
        },
    },
    "ccf_welcome": {
        "title": "Bienvenida publica CCF",
        "content": {
            "eyebrow": "Bienvenida",
            "title_template": "Hola, {name}.",
            "description": (
                "No encontramos una cuenta registrada todavía, pero no te dejamos en una pantalla vacía. "
                "Puedes empezar por la ruta pública de fe y crecimiento que preparamos para ti."
            ),
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
    "ccf_privacy": {
        "title": "Política de privacidad CCF",
        "content": {
            "last_update": "12 de junio de 2026",
            "summary": (
                "Esta política describe cómo PLES SAS y la Comunidad Cristiana CCF "
                "recopilan, usan, almacenan y protegen tus datos personales."
            ),
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
    # ── CTA DESCUBRE (sección body del home) ─────────────────────────────────
    "ccf_home_discover_cta": {
        "title": "CTA Conocer a Jesús — Home",
        "content": {
            "eyebrow": "Una invitación para ti",
            "title": "¿Quieres conocer a Jesús?",
            "description": "No es una religión, es el comienzo de una relación que transforma la vida. Da el siguiente paso hoy.",
            "cta_label": "Quiero conocer a Jesús",
            "cta_href": "/conocer-a-jesus",
        },
    },
    # ── HEROES PÚBLICOS (unificados desde seed_public_content) ──────────────
    "ccf_home_hero": {
        "title": "Hero — Inicio",
        "content": {
            "eyebrow": "UNA COMUNIDAD QUE ILUMINA",
            "title_lead": "CCF:",
            "title_accent": "Tu Guía,",
            "title_tail": "Su Luz",
            "description": "Navegando juntos hacia la verdad. Un espacio de encuentro, fe y transformación en el corazón de nuestra comunidad.",
            "primary_cta": "Empezar mi viaje",
            "secondary_cta": "Ver Prédicas",
        },
    },
    "ccf_about_hero": {
        "title": "Hero — Quiénes Somos",
        "content": {
            "eyebrow": "Nuestra Identidad",
            "title_lead": "Iluminando el",
            "title_accent": "camino juntos.",
            "description": "Somos la <strong>Comunidad Cristiana CCF</strong>, una iglesia viva y en crecimiento que existe para conectar corazones con Dios y entre sí, fundamentada en la Palabra y movida por el amor.",
        },
    },
    "ccf_about_feed": {
        "title": "Contenido — Quiénes Somos",
        "content": {
            "stats": [
                {"value": "+20", "label": "Años de ministerio"},
                {"value": "+8", "label": "Pastores activos"},
                {"value": "+500", "label": "Familias"},
                {"value": "3", "label": "Sedes"},
            ],
            "vision_title": "Nuestra visión",
            "vision_text": (
                "Seremos una comunidad de fe donde el <strong>amor y el poder de Dios</strong> restauren vidas y familias, "
                "levantando generaciones apasionadas por Cristo, firmes en Su Palabra y llenas del Espíritu Santo. "
                "Formaremos creyentes con un carácter sólido y una fe inquebrantable, capacitados para transformar su "
                "entorno y ejercer una influencia sobrenatural en cada esfera de la sociedad. "
                "Nuestra misión es encender corazones con la verdad del Evangelio y expandir el Reino de Dios con "
                "autoridad, gracia y compasión."
            ),
            "mision_title": "Nuestra misión",
            "mision_text": (
                "Manifestar y expandir el <strong>Reino de Dios en cada esfera de la sociedad</strong>, llevando el amor "
                "inagotable del Padre, el poder transformador del Espíritu Santo y la verdad eterna de Su Palabra a "
                "todas las naciones. Nos comprometemos a cumplir la Gran Comisión (Mateo 28:19), formando discípulos "
                "que vivan en obediencia a Cristo, sean bautizados en Su nombre y reflejen Su gloria, para que el mundo "
                "sea alcanzado, restaurado y reconciliado con Dios."
            ),
            "founder_label": "Nuestros Pastores Principales",
            "founder1_name": "Luis Ricardo Meza",
            "founder1_role": "Pastor Principal",
            "founder1_image": "/api/static/cms/pastores/593ca8b22fd549228f27a5ed6b532674.webp",
            "founder2_name": "Histar Ariza",
            "founder2_role": "Pastora Principal",
            "founder2_image": "/api/static/cms/pastores/b8b07cb268184f9caf9aec8d93573ead.webp",
            "valores_title": "Valores que nos Guían",
            "valores": [
                {
                    "num": "01",
                    "key": "palabra",
                    "title": "Palabra",
                    "desc": "La Escritura es nuestra brújula. Cada decisión, enseñanza y acción está fundamentada en la sana doctrina de la Biblia.",
                },
                {
                    "num": "02",
                    "key": "amor",
                    "title": "Amor Radical",
                    "desc": "Un compromiso inquebrantable de servir y acoger a todos, sin importar su historia, origen o camino recorrido.",
                },
                {
                    "num": "03",
                    "key": "comunidad",
                    "title": "Comunidad",
                    "desc": "Creemos en la vida en familia. El crecimiento espiritual genuino ocurre en relación auténtica con otros.",
                },
                {
                    "num": "04",
                    "key": "integridad",
                    "title": "Integridad",
                    "desc": "Vivir con coherencia entre lo que creemos y lo que hacemos, permitiendo que nuestra fe sea visible en cada área de la vida.",
                },
                {
                    "num": "05",
                    "key": "mision",
                    "title": "Misión",
                    "desc": "No existimos solo para nosotros mismos. Somos enviados a alcanzar a los que aún no conocen el amor de Cristo.",
                },
                {
                    "num": "06",
                    "key": "excelencia",
                    "title": "Excelencia",
                    "desc": "Damos lo mejor de nosotros en todo lo que hacemos, como un acto de adoración y respeto a quien nos llamó.",
                },
            ],
            "quote_text": "La luz que encontramos en CCF no es para guardarla — es para guiar a otros que aún caminan en la oscuridad.",
            "quote_subtitle": "Comunidad Cristiana CCF",
            "cta_title": "¿Listo para ser parte?",
            "cta_desc": "Ven a conocernos. Tenemos puertas abiertas y un lugar reservado para ti y tu familia.",
        },
    },
    "ccf_pastores_hero": {
        "title": "Hero — Pastores",
        "content": {
            "title": "Liderazgo Pastoral",
            "description": "Hombres y mujeres llamados por Dios para servir, guiar y amar a esta casa.",
        },
    },
    "ccf_events_hero": {
        "title": "Hero — Eventos",
        "content": {
            "eyebrow": "Agenda CCF",
            "title": "Próximos Eventos",
            "description": "Momentos diseñados para conectarte con Dios y con nuestra comunidad. ¡No te los pierdas!",
        },
    },
    "ccf_sermons_hero": {
        "title": "Hero — Prédicas",
        "content": {
            "eyebrow": "Mensaje Destacado",
            "title_lead": "Alimento para el",
            "title_accent": "Alma",
            "description": "Explora nuestra biblioteca de mensajes que iluminan el camino. Una guía espiritual diseñada para nutrir tu fe.",
        },
    },
    "ccf_discover_hero": {
        "title": "Hero — Conocer a Jesús",
        "content": {
            "eyebrow": "Inicia tu camino",
            "title_lead": "La Luz que ",
            "title_accent": "Guía",
            "title_tail": " Tu Vida.",
            "description": "Conocer a Jesús no es una religión, es el comienzo de una relación que transforma la oscuridad en un propósito eterno.",
            "cta": "Quiero conocer a Jesús",
        },
    },
    "ccf_courses_hero": {
        "title": "Hero — Cursos",
        "content": {
            "eyebrow": "Formación & Sabiduría",
            "title_lead": "El Camino",
            "title_accent": "del CCF",
            "description": "Explora nuestra academia de cursos especializados y sumérgete en una selección literaria para iluminar tu entendimiento.",
        },
    },
    "ccf_locations_hero": {
        "title": "Hero — Sedes",
        "content": {
            "eyebrow": "Nuestra Presencia",
            "title": "Nuestras Sedes",
            "search_placeholder": "Buscar ciudad o dirección...",
        },
    },
    "ccf_locations_feed": {
        "title": "Listado — Sedes",
        "content": [
            {
                "id": 1,
                "name": "Sede Central — CCF",
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
    "ccf_nav_items": {
        "title": "Menú de Navegación",
        "content": {
            "items": [
                {"label": "Inicio", "href": "/"},
                {"label": "Quiénes Somos", "href": "/nosotros"},
                {"label": "Pastores", "href": "/pastores"},
                {"label": "Eventos", "href": "/eventos"},
                {"label": "Prédicas", "href": "/predicas"},
                {"label": "Cursos", "href": "/cursos"},
                {"label": "Sedes", "href": "/sedes"},
                {"label": "Conocer a Jesús", "href": "/conocer-a-jesus"},
            ]
        },
    },
}

MERGE_BLOCKS = {
    "ccf_courses_feed": {
        "title": "Feed — Cursos",
        "content": {
            "hero_image_url": "https://picsum.photos/seed/1481627834876-b7833e8f5570/1920/1080",
            "featured_fallback_image_url": "https://picsum.photos/seed/1524178232363-1fb2b075b655/800/600",
            "cta_images": [
                {"src": "https://picsum.photos/seed/academia1/800/800", "alt": "Estudio"},
                {"src": "https://picsum.photos/seed/academia2/800/800", "alt": "Librería"},
            ],
            "course_cards": [
                {
                    "id": "el-evangelio-que-no-conocias",
                    "title": "El Evangelio que no Conocías",
                    "desc": "Después de dos mil años, el Evangelio corre el riesgo de volverse una marca, un sistema de reglas o una terapia emocional.",
                    "tag": "Fundamentos Radicales",
                    "modality": "Presencial & Online",
                    "lessons": 10,
                    "cta": "Quiero Inscribirme",
                    "imageUrl": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=800&h=600&fit=crop",
                    "instructor": "Pastor Luis Ricardo Meza Gutiérrez",
                },
                {
                    "id": "jesus-el-subversivo",
                    "title": "Jesús el Subversivo",
                    "desc": "Recupera al Jesús real del contexto judío del Segundo Templo.",
                    "tag": "Teología Crítica",
                    "modality": "100% Online",
                    "lessons": 8,
                    "cta": "Quiero Conocerlo de Verdad",
                    "imageUrl": "https://images.unsplash.com/photo-1519681393784-d120267933ba?w=800&h=600&fit=crop",
                    "instructor": "Academia CCF — Teología Histórica",
                },
                {
                    "id": "escatologia-sin-miedo",
                    "title": "Escatología sin Apocalipsis-Fobia",
                    "desc": "El Apocalipsis como carta de resistencia y esperanza.",
                    "tag": "Profecía & Esperanza",
                    "modality": "100% Online",
                    "lessons": 8,
                    "cta": "Quiero Leer el Apocalipsis de Nuevo",
                    "imageUrl": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800&h=600&fit=crop",
                    "instructor": "Academia CCF — Teología Bíblica",
                },
                {
                    "id": "teodicea-dios-frente-al-sufrimiento",
                    "title": "Teodicea: Dios Frente al Sufrimiento",
                    "desc": "Las respuestas fáciles al sufrimiento son una ofensa a quienes sufren.",
                    "tag": "Apologética Profunda",
                    "modality": "Híbrido",
                    "lessons": 10,
                    "cta": "Quiero Afrontar Esta Pregunta",
                    "imageUrl": "https://images.unsplash.com/photo-1476611338391-6f395a0ebc7b?w=800&h=600&fit=crop",
                    "instructor": "Academia CCF — Filosofía y Teología",
                },
            ],
            "books": [
                {
                    "id": "b1",
                    "title": "La Búsqueda de Dios",
                    "author": "A.W. Tozer",
                    "price": "$15.00",
                    "img": "https://picsum.photos/seed/tozer-book/400/600",
                    "desc": "Un clásico indispensable sobre la sed espiritual y la verdadera intimidad con el Creador.",
                },
                {
                    "id": "b2",
                    "title": "Mero Cristianismo",
                    "author": "C.S. Lewis",
                    "price": "$18.50",
                    "img": "https://picsum.photos/seed/cslewis-book/400/600",
                    "desc": "La apología moderna más brillante sobre las bases objetivas de la fe cristiana.",
                },
                {
                    "id": "b3",
                    "title": "El Costo del Discipulado",
                    "author": "Dietrich Bonhoeffer",
                    "price": "$14.00",
                    "img": "https://picsum.photos/seed/bonhoeffer-book/400/600",
                    "desc": "La diferencia entre la gracia barata y la gracia costosa.",
                },
                {
                    "id": "b4",
                    "title": "La Política de Jesús",
                    "author": "John Howard Yoder",
                    "price": "$16.00",
                    "img": "https://picsum.photos/seed/yoder-book/400/600",
                    "desc": "Jesús como modelo de ética social.",
                },
            ],
        },
    },
}


def main() -> int:
    with SessionLocal() as db:
        created = 0
        updated = 0
        for page_key, payload in BLOCKS.items():
            content = json.dumps(payload["content"], ensure_ascii=False)
            row = db.query(models.PageContent).filter(models.PageContent.page_key == page_key).first()
            if row is None:
                row = models.PageContent(page_key=page_key, title=payload["title"], content=content)
                db.add(row)
                created += 1
            else:
                row.title = payload["title"]
                row.content = content
                updated += 1
            db.add(
                models.PageContentVersion(
                    page_key=page_key,
                    title=payload["title"],
                    content=content,
                )
            )
        for page_key, payload in MERGE_BLOCKS.items():
            row = db.query(models.PageContent).filter(models.PageContent.page_key == page_key).first()
            current = {}
            if row is not None:
                try:
                    current = json.loads(row.content or "{}")
                except json.JSONDecodeError:
                    current = {}
            # These fields were seeded with identities and photos that do not
            # belong to the current church leadership. They are editorial CMS
            # data, not safe bootstrap defaults, so never resurrect them from
            # this maintenance script.
            if page_key == "ccf_about_feed":
                for key in (
                    "founder_label", "founder_title", "founder_title_accent",
                    "founder1_name", "founder1_role", "founder1_image",
                    "founder2_name", "founder2_role", "founder2_image",
                    "founder_bio", "founder_bio2", "founder_cta_team",
                    "founder_cta_visit", "quote_author",
                ):
                    current.pop(key, None)
            next_content = {**current, **payload["content"]}
            content = json.dumps(next_content, ensure_ascii=False)
            if row is None:
                row = models.PageContent(page_key=page_key, title=payload["title"], content=content)
                db.add(row)
                created += 1
            else:
                row.title = row.title or payload["title"]
                row.content = content
                updated += 1
            db.add(
                models.PageContentVersion(
                    page_key=page_key,
                    title=row.title or payload["title"],
                    content=content,
                )
            )
        db.commit()
        print(f"Public content blocks ensured: {len(BLOCKS) + len(MERGE_BLOCKS)}")
        print(f"Created: {created}")
        print(f"Updated: {updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
