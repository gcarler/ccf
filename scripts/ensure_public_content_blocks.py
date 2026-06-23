"""Seed CMS-managed PageContent blocks used by public pages.

The public React components keep local fallbacks for rollback safety, but these
blocks make the current production copy and navigation editable through CMS.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend import models  # noqa: E402
from backend.core.database import SessionLocal  # noqa: E402


BLOCKS = {
    "faro_events_feed": {
        "title": "Eventos publico FARO",
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
        "title": "Prédicas publico FARO",
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
        "title": "Hero testimonios publico FARO",
        "content": {
            "eyebrow": "Impacto Real",
            "title_lead": "Historias de",
            "title_accent": "Transformación",
            "description": "Descubre cómo la fe y la comunidad han iluminado el camino de personas reales.",
        },
    },
    "faro_testimonials_feed": {
        "title": "Testimonios publico FARO",
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
        "title": "Boletín publico FARO",
        "content": {
            "subtitle": "Boletín Semanal FARO",
            "title": "Recibe nuestra palabra de aliento",
            "description": "Cada semana te enviamos una reflexión bíblica, un versículo de ánimo y consejos prácticos para fortalecer tu fe.",
            "cta_text": "Suscribirme ahora",
        },
    },
    "faro_pastores_index": {
        "title": "Pastores publico FARO",
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
    "faro_pastores_feed": {
        "title": "Pastores publico FARO",
        "content": {
            "pastors": [
                {
                    "slug": "luis-ricardo-meza",
                    "name": "Luis Ricardo Meza Gutiérrez",
                    "role": "Pastor Principal",
                    "image": "/images/pastores/luis_ricardo_meza.webp",
                    "isMain": True,
                    "story": "Un testimonio de transformación profunda y pasión inagotable por la enseñanza de la Palabra.",
                },
                {
                    "slug": "histar-ariza",
                    "name": "Histar Ariza Herrera",
                    "role": "Pastor Principal",
                    "image": "/images/pastores/histar_ariza.webp",
                    "isMain": True,
                    "story": "El llamado pastoral, la visión de expansión y el corazón de paternidad espiritual que guía a nuestra congregación.",
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
                    "story": "Le apasiona enseñar, convencida de que la educación transforma vidas y le da el privilegio de sembrar conocimiento y valores.",
                },
                {
                    "slug": "camilo-pajaro",
                    "name": "Camilo Pájaro",
                    "role": "Pastor",
                    "image": "/images/pastores/camilo_alba.webp",
                    "story": "Le apasiona habitar en la presencia del Padre y siente un profundo celo por apoyar y guiar a las almas perdidas.",
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
                {
                    "slug": "martina-herrera",
                    "name": "Martina Herrera",
                    "role": "Pastora Fundadora",
                    "image": "/images/pastores/martina_herrera.webp",
                    "isMain": True,
                    "story": "Pastora fundadora del ministerio Comunidad Cristiana El Faro junto a su esposo, Alejandro Ariza Torres, quien ya partió y está con el Señor.",
                    "bio_short": "Pastora fundadora del ministerio Comunidad Cristiana El Faro junto a su esposo, Alejandro Ariza Torres, quien ya partió y está con el Señor.",
                    "bio_full": "<p>La Pastora Martina Herrera es la pastora fundadora del ministerio Comunidad Cristiana El Faro. Junto a su esposo, Alejandro Ariza Torres, quien ya partió y está con el Señor, sembró con fe, oración y perseverancia las bases espirituales de esta casa.</p><blockquote>\"La obra de Dios se edifica con fe, obediencia y amor por las almas.\"</blockquote><p>Desde los primeros días del ministerio, la Pastora Martina ha sido un pilar de oración, fidelidad y cuidado pastoral. Su corazón maternal ha acompañado a generaciones de creyentes que encontraron en ella una pastora, una consejera y una madre espiritual.</p><p>Su legado permanece vivo en la familia espiritual de Comunidad Cristiana El Faro: una iglesia levantada para amar a Dios, servir a las personas y continuar la obra que el Señor puso en sus manos.</p>",
                },
            ]
        },
    },
    "faro_courses_feed": {
        "title": "Cursos publico FARO",
        "content": {
            "library_title": "Nuestra Librería",
            "library_description": "Una curaduría de obras que han transformado generaciones. Desde clásicos de la patrística hasta literatura contemporánea.",
            "empty_books_message": "Próximamente tendremos libros disponibles.",
            "courses_title": "Cursos & Academia",
            "courses_description": "Programas estructurados para líderes, estudiantes y buscadores de la verdad. Formación teológica y práctica con estándares de excelencia.",
        },
    },
    "faro_discover_feed": {
        "title": "Conocer a Jesús publico FARO",
        "content": {
            "intro_title": "Un Encuentro Personal",
            "intro_paragraph_1": "En FARO, creemos que cada historia es única. No importa dónde hayas estado o qué hayas hecho, la invitación es la misma: <strong>Ven y ve.</strong>",
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
        },
    },
    "faro_home_feed": {
        "title": "Home publico FARO",
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
    "faro_footer": {
        "title": "Footer publico FARO",
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
        "title": "Navegacion movil publica FARO",
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
    "faro_welcome": {
        "title": "Bienvenida publica FARO",
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
    "faro_privacy": {
        "title": "Política de privacidad FARO",
        "content": {
            "last_update": "12 de junio de 2026",
            "summary": (
                "Esta política describe cómo PLES SAS y la Comunidad Cristiana El Faro "
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
}

MERGE_BLOCKS = {
    "faro_courses_feed": {
        "title": "Feed — Cursos",
        "content": {
            "hero_image_url": "https://picsum.photos/seed/1481627834876-b7833e8f5570/1920/1080",
            "featured_fallback_image_url": "https://picsum.photos/seed/1524178232363-1fb2b075b655/800/600",
            "cta_images": [
                {"src": "https://picsum.photos/seed/academia1/800/800", "alt": "Estudio"},
                {"src": "https://picsum.photos/seed/academia2/800/800", "alt": "Librería"},
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
