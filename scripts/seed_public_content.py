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
            "founder1_image": "/pastores/luis_ricardo_meza_1777656765476.png",
            "founder2_name": "Histar Ariza Herrera",
            "founder2_role": "Pastor Principal",
            "founder2_image": "/pastores/histar_ariza_1777656780660.png",
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
                    "image": "/pastores/luis_ricardo_meza_1777656765476.png",
                    "isMain": True,
                    "story": "Un testimonio de transformación profunda y pasión inagotable por la enseñanza de la Palabra.",
                    "quote": "La Palabra de Dios, correctamente dividida, es el alimento que da vida a la Iglesia.",
                    "verse": "Esdras 7:10",
                },
                {
                    "slug": "histar-ariza",
                    "name": "Histar Ariza Herrera",
                    "role": "Pastor Principal",
                    "image": "/pastores/histar_ariza_1777656780660.png",
                    "isMain": True,
                    "story": "El llamado pastoral, la visión de expansión y el corazón de paternidad espiritual que guía a nuestra congregación.",
                    "quote": "Nuestra mayor recompensa es ver corazones transformados por el amor del Padre.",
                    "verse": "Jeremías 3:15",
                },
                {
                    "slug": "alex-y-elvia",
                    "name": "Alex y Elvia",
                    "role": "Pastores de Familias",
                    "image": "/pastores/alex_elvia_1777656808218.png",
                    "story": "Un testimonio vivo de gracia enfocado en la restauración matrimonial y el ministerio familiar.",
                },
                {
                    "slug": "alba-arias",
                    "name": "Alba Arias",
                    "role": "Pastora",
                    "image": "/pastores/camilo_alba_1777656794964.png",
                    "quote": "Mi mayor gozo no está en una posición o en un título, sino en pertenecer a la obra de Dios y ser útil en sus manos.",
                    "verse": "Juan 3:16",
                    "story": "<p>Antes de llegar a la Comunidad Cristiana El Faro, la Pastora Alba Arias no había tenido acercamientos a ninguna iglesia ni una relación personal con Dios. Fue en este lugar donde experimentó la presencia del Espíritu Santo por primera vez, un encuentro que transformó su carácter, sanó su corazón y le dio una profunda identidad como hija amada. Esta revelación de la bondad del Padre la impulsó a compartir su amor con otros.</p><blockquote>\"Elijo Juan 3:16 porque nos muestra la esencia misma de lo que Él es y lo que quiere con cada uno de nosotros.\"</blockquote><p>Lo que más le apasiona es enseñar, una vocación que también constituye su profesión. Alba cree firmemente que la educación transforma vidas y que, a través de ella, Dios le concede el privilegio de sembrar conocimiento y valores eternos en el corazón de cada estudiante.</p><p><strong>Perfil Ministerial:</strong> A lo largo de su servicio en la casa de Dios, Alba ha apoyado en múltiples áreas. Comenzó colaborando en la limpieza del templo y en diversas tareas logísticas; posteriormente se integró al equipo de bienvenida para recibir con amor a todos los que llegaban. Más adelante sirvió en el ministerio infantil (sala cuna y escuela dominical), sembrando principios bíblicos en la niñez. Actualmente se desempeña en el ministerio pastoral, apoyando a los pastores principales en las áreas administrativa y financiera.</p><p><strong>Perfil Familiar:</strong> Está casada con el Pastor Camilo Pájaro, a quien conoció en su etapa escolar. Juntos comenzaron asistiendo a los servicios de madrugón. Aunque en los inicios de su relación vivieron altibajos que los llevaron a separarse durante un año —período en el que Alba se alejó temporalmente de la iglesia—, el Señor restauró su lazo amoroso y ella regresó a El Faro. En 2014 se bautizaron y se casaron. En doce años de matrimonio, el Padre los ha sustentado y hecho crecer ministerialmente. Hoy en día, tienen dos hermosas hijas, Sara Valentina y Shaddai Antonella, y su historia es un testimonio de la fidelidad y provisión divina.</p>",
                },
                {
                    "slug": "camilo-pajaro",
                    "name": "Camilo Pájaro",
                    "role": "Pastor",
                    "image": "/pastores/camilo_alba_1777656794964.png",
                    "quote": "He entendido que si es Él quien me guía y me dirige, en mi vida todo terminará ayudando para bien.",
                    "verse": "Salmo 23:1",
                    "story": "<p>Antes de conocer al Señor, Camilo Pájaro vivía una vida volcada al baile, la música secular y su mayor prioridad: el béisbol, deporte en el cual se formaba activamente. Sin embargo, Dios intervino de forma providencial, llamándolo a abandonar lo que creía que era su propósito terrenal para alinear su vida con su propósito eterno. Llegó a los pies del Señor con inseguridades y maldiciones generacionales, de las cuales fue totalmente libertado por el amor y la misericordia divina.</p><blockquote>\"He entendido que si es Él quien me guía y me dirige, en mi vida todo terminará ayudando para bien.\"</blockquote><p>A Camilo le apasiona habitar en la presencia de Dios, cultivar una relación cercana con el Padre y agradarle en todo. Asimismo, tiene un pfofundo celo por las almas perdidas, sintiendo el llamado de apoyar a quienes andan sin rumbo y guiarlos de vuelta a la senda de Cristo.</p><p><strong>Perfil Ministerial:</strong> Su caminar en el servicio comenzó desde las tareas más sencillas, limpiando y colaborando con el aseo del templo. A medida que crecía espiritualmente, Dios abrió puertas en su liderazgo: se desempeñó como maestro de la Academia de Formación Ministerial, ministro de alabanza y miembro destacado de la agrupación musical Sonido de Gloria, y hoy en día sirve en el ministerio pastoral.</p><p><strong>Perfil Familiar:</strong> Está casado con la Pastora Alba Arias, con quien comparte su vida y ministerio. Se conocieron en el colegio y dieron sus primeros pasos espirituales asistiendo a los madrugones de la iglesia. Tras superar una separación de un año, se bautizaron y casaron en el 2014. Hoy, junto a sus hijas Sara Valentina y Shaddai Antonella, testifican que el Señor ha sido su sustento inquebrantable durante doce años de matrimonio.</p>",
                },
                {
                    "slug": "fernando-y-monica",
                    "name": "Fernando y Mónica",
                    "role": "Pastores de Discipulado",
                    "image": "/pastores/fernando_monica_1777656831456.png",
                    "story": "La historia de la fidelidad, el servicio incondicional y el acompañamiento constante.",
                },
                {
                    "slug": "nehemias-morales",
                    "name": "Nehemías Morales",
                    "role": "Pastor de Consolidación",
                    "image": "/pastores/nehemias_morales_1777656877353.png",
                    "story": "Enfocado en la resiliencia, la construcción de comunidad y la fe inquebrantable.",
                },
                {
                    "slug": "yair-macea",
                    "name": "Yair Macea",
                    "role": "Pastor Evangelístico",
                    "image": "/pastores/yair_macea_1777656845407.png",
                    "story": "Un relato de gracia abrumadora, superación personal y un fuego evangelístico inextinguible.",
                },
                {
                    "slug": "yanedith-wilches",
                    "name": "Yanedith Wilches",
                    "role": "Pastora de Intercesión",
                    "image": "/pastores/yanedith_wilches_1777656863437.png",
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

    # ── PRÉDICAS ────────────────────────────────────────────────────────────
    "faro_sermons_hero": {
        "title": "Hero — Prédicas",
        "content": {
            "eyebrow": "Mensaje Destacado",
            "title_lead": "Alimento para el",
            "title_accent": "Alma",
            "description": "Explora nuestra biblioteca de mensajes que iluminan el camino. Una guía espiritual diseñada para nutrir tu fe.",
        },
    },
    "faro_sermons_feed": {
        "title": "Feed — Prédicas",
        "content": {
            "featured_label": "Mensaje de la Semana",
            "grid_label": "Mensajes Recientes",
            "empty_message": "Próximamente nuevos mensajes.",
        },
    },

    # ── EVENTOS ─────────────────────────────────────────────────────────────
    "faro_events_hero": {
        "title": "Hero — Eventos",
        "content": {
            "eyebrow": "Agenda El Faro",
            "title": "Próximos Eventos",
            "description": "Momentos diseñados para conectarte con Dios y con nuestra comunidad. ¡No te los pierdas!",
        },
    },

    # ── CURSOS ──────────────────────────────────────────────────────────────
    "faro_courses_hero": {
        "title": "Hero — Cursos",
        "content": {
            "eyebrow": "Formación & Sabiduría",
            "title_lead": "El Camino",
            "title_accent": "del Faro",
            "description": "Explora nuestra academia de cursos especializados y sumérgete en una selección literaria para iluminar tu entendimiento.",
        },
    },
    "faro_courses_feed": {
        "title": "Feed — Cursos",
        "content": {
            "featured_label": "Curso Destacado",
            "grid_label": "Todos los Cursos",
            "empty_message": "Próximamente nuevos cursos. ¡Estate atento!",
        },
    },

    # ── TESTIMONIOS ─────────────────────────────────────────────────────────
    "faro_testimonios_hero": {
        "title": "Hero — Testimonios",
        "content": {
            "eyebrow": "Impacto Real",
            "title_lead": "Historias de",
            "title_accent": "Transformación",
            "description": "Vidas reales, cambios reales. Así es como el amor de Dios se hace visible en nuestra comunidad.",
        },
    },

    # ── BOLETÍN ─────────────────────────────────────────────────────────────
    "faro_boletin_hero": {
        "title": "Hero — Boletín",
        "content": {
            "subtitle": "Boletín Semanal — Comunidad Cristiana El Faro",
            "title": "Recibe nuestra palabra de aliento",
            "description": "Cada semana te enviamos una reflexión bíblica, un versículo de ánimo y consejos prácticos para fortalecer tu fe.",
            "cta_text": "Suscribirme ahora",
        },
    },

    # ── CONOCER A JESÚS ─────────────────────────────────────────────────────
    "faro_discover_hero": {
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
    "faro_discover_feed": {
        "title": "Feed — Conocer a Jesús",
        "content": {
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

    # ── PRIVACIDAD ─────────────────────────────────────────────────────────
    "faro_privacidad": {
        "title": "Política de Privacidad",
        "content": {
            "title": "Política de Privacidad",
            "last_update": "12 de junio de 2026",
            "intro": "Esta política describe cómo PLES SAS y la Comunidad Cristiana El Faro recopilan, usan, almacenan y protegen tus datos personales conforme a la Ley 1581 de 2012.",
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
