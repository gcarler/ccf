#!/usr/bin/env python3
"""Seed / migrate all public page fallbacks into CMS v2 (CmsPage + CmsSection).

Usage:
    cd /root/ccf && source venv/bin/activate && python scripts/seed_public_cms_v2_sections.py

The script is idempotent: it updates existing sections by ``section_key`` and only
publishes a new ``CmsPageVersion`` when the effective snapshot actually changes.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# ── 1. Project root & DATABASE_URL (must happen before any backend import) ─────
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next(
    (p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()),
    None,
)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")

# Load .env so pydantic can read it, then mirror the resolved DB URL into the
# environment. This prevents `seed_public_content.py` from setting an empty
# DATABASE_URL before SQLAlchemy initialises the engine.
from dotenv import load_dotenv  # noqa: E402

load_dotenv(_PROJECT_ROOT / ".env")


def _resolve_db_url() -> str:
    """Return the canonical DATABASE_URL, parsing .env manually if needed."""
    for key in ("DATABASE_URL", "database_url"):
        val = os.environ.get(key, "").strip()
        if val:
            return val
    env_path = _PROJECT_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            if k.strip().lower() == "database_url":
                v = v.strip().strip('"').strip("'")
                if v:
                    return v
    return "sqlite:///./ccf_dev.db"


_DB_URL = _resolve_db_url()
if _DB_URL:
    os.environ["DATABASE_URL"] = _DB_URL
    os.environ["database_url"] = _DB_URL

# If we still fall back to SQLite, force local environment so the validator
# does not reject the default database_url in non-local environments.
if _DB_URL.startswith("sqlite") and os.environ.get("environment", "local").lower() not in {
    "local",
    "test",
    "testing",
    "ci",
}:
    os.environ["environment"] = "local"

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if str(_PROJECT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "scripts"))

# ── 2. Backend models & session factory ────────────────────────────────────────
import backend.models as models  # noqa: E402

try:
    from backend.database import SessionLocal  # noqa: E402
except Exception:
    from backend.core.database import SessionLocal  # noqa: E402

# ── 3. Reuse the canonical public content blocks if available ──────────────────
try:
    import ensure_public_content_blocks as _ep  # noqa: E402
    import seed_public_content as _sp  # noqa: E402

    PUBLIC_BLOCKS: dict[str, Any] = deepcopy(getattr(_sp, "BLOCKS", {}))
    CMS_BLOCKS: dict[str, Any] = deepcopy(getattr(_ep, "BLOCKS", {}))
    CMS_MERGE: dict[str, Any] = deepcopy(getattr(_ep, "MERGE_BLOCKS", {}))
except Exception as exc:  # pragma: no cover
    print(f"Warning: could not import legacy seed modules ({exc}); using built-in fallbacks.")
    PUBLIC_BLOCKS = {}
    CMS_BLOCKS = {}
    CMS_MERGE = {}


# ── 4. Helpers ─────────────────────────────────────────────────────────────────
def _get_block(name: str, source: dict[str, Any] | None = None, default: Any | None = None) -> Any:
    src = source if source is not None else PUBLIC_BLOCKS
    block = src.get(name, {})
    return deepcopy(block.get("content", default))


def _content_json(obj: Any) -> dict[str, Any]:
    return {"content": json.dumps(obj, ensure_ascii=False)}


def _parsed(obj: Any) -> dict[str, Any]:
    return {"parsed": obj}


def _media_lookup(db: Any) -> Any:
    """Return a helper that prefers existing CmsMediaItem URLs."""
    try:
        rows = (
            db.query(models.CmsMediaItem)
            .filter(models.CmsMediaItem.url.like("%/cms/%"))
            .all()
        )
        urls = [r.url for r in rows]
    except Exception:
        urls = []

    def find(substring: str, fallback: str = "") -> str:
        for url in urls:
            if substring in url:
                return url
        return fallback

    return find


def _ensure_image(url: str, media_find: Any, substring: str, fallback: str = "") -> str:
    if url and isinstance(url, str) and ("picsum" in url or "unsplash" in url or "/api/static/cms/" in url):
        return url
    found = media_find(substring, fallback) if media_find else fallback
    return found or fallback


def _page_title(slug: str) -> str:
    return {
        "home": "Inicio",
        "about": "Quiénes Somos",
        "pastors": "Liderazgo Pastoral",
        "events": "Eventos",
        "sermons": "Prédicas",
        "discover": "Conocer a Jesús",
        "courses": "Cursos",
        "locations": "Sedes",
        "testimonials": "Testimonios",
        "boletin": "Boletín",
        "welcome": "Bienvenida",
        "privacy": "Política de Privacidad",
        "_global": "Global (nav / shared)",
    }.get(slug, slug.replace("-", " ").title())


_EXTERNAL_DOMAINS = {"unsplash.com", "picsum.photos"}
_EXTERNAL_RE = re.compile(r"https?://[^\s\"'\)<>]+")


def _is_external_url(url: str) -> bool:
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    return any(netloc == domain or netloc.endswith(f".{domain}") for domain in _EXTERNAL_DOMAINS)


def _replace_url_in_props(props: Any, old: str, new: str) -> Any:
    if isinstance(props, dict):
        return {k: _replace_url_in_props(v, old, new) for k, v in props.items()}
    if isinstance(props, list):
        return [_replace_url_in_props(item, old, new) for item in props]
    if isinstance(props, str):
        if old in props:
            return props.replace(old, new)
        try:
            parsed = json.loads(props)
        except (json.JSONDecodeError, TypeError):
            return props
        replaced = _replace_url_in_props(parsed, old, new)
        return json.dumps(replaced, ensure_ascii=False)
    return props


def _localize_external_images(db: Any, sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Replace any Unsplash/Picsum URLs with locally-hosted CmsMediaItem URLs.

    This keeps the seed idempotent even though the legacy seed modules still
    reference external placeholder images.
    """
    media_by_url_hash: dict[str, models.CmsMediaItem] = {}
    for m in db.query(models.CmsMediaItem).filter(models.CmsMediaItem.filename.like("%")).all():
        media_by_url_hash[m.filename] = m

    for spec in sections:
        props = spec.get("props", {})
        text = json.dumps(props, ensure_ascii=False)
        urls = sorted({m.group() for m in _EXTERNAL_RE.finditer(text) if _is_external_url(m.group())})
        for url in urls:
            url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
            media = media_by_url_hash.get(url_hash)
            if media:
                props = _replace_url_in_props(props, url, media.url)
        spec["props"] = props
    return sections


def _build_pages(media_find: Any) -> dict[str, list[dict[str, Any]]]:
    """Return a slug -> list of section specs mapping."""

    # ── HOME ────────────────────────────────────────────────────────────────
    home_hero = _get_block("ccf_home_hero") or {
        "eyebrow": "BIENVENIDOS",
        "title_lead": "CCF:",
        "title_accent": "Tu Guía,",
        "title_tail": "Su Luz",
        "description": "Navegando juntos hacia la verdad. Un espacio de encuentro, fe y transformación en el corazón de nuestra comunidad.",
        "primary_cta": "Empezar mi viaje",
        "secondary_cta": "Ver Prédicas",
    }
    home_hero.setdefault("bg_image", _ensure_image("", media_find, "home_banner"))

    home_feed = _get_block("ccf_home_feed", CMS_BLOCKS) or {
        "eyebrow": "Nuestra esencia",
        "section_title": "Bienvenidos a Casa",
        "section_description": "Rutas públicas para conocer la comunidad, profundizar en la fe y encontrar dónde dar el siguiente paso.",
        "featured_card": {
            "title": "Conocer a Jesús",
            "desc": "Descubre la base de nuestra fe a través de un viaje personal y transformador.",
            "href": "/conocer-a-jesus",
            "cta": "Empezar el camino",
            "img": _ensure_image("", media_find, "home_banner"),
            "alt": "Equipo pastoral de CCF",
        },
        "cards": [
            {"title": "Librería", "desc": "Recursos para profundizar.", "href": "/cursos", "img": "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=600&q=80", "alt": "Libros"},
            {"title": "Horarios", "desc": "Reuniones presenciales y online.", "href": "/eventos", "img": "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?w=600&q=80", "alt": "Reunión"},
            {"title": "Sedes", "desc": "Encuéntranos en tu ciudad.", "href": "/sedes", "img": "https://images.unsplash.com/photo-1438032005730-c779502df39b?w=600&q=80", "alt": "Sede"},
        ],
    }
    home_feed.setdefault("activities_eyebrow", "Actualidad")
    home_feed.setdefault("activities_title", "Actividades Recientes")
    home_feed.setdefault("activities_view_all", "Ver calendario →")
    home_feed.setdefault("activities_empty", "Próximamente encontrarás aquí nuestras actividades. Mientras tanto, síguenos en redes sociales.")
    home_feed.setdefault("scroll_indicator", "Descubrir")
    home_feed.setdefault("newsletter_eyebrow", "Boletín semanal")
    home_feed.setdefault("newsletter_title", "¿Quieres recibir nuestras novedades?")
    home_feed.setdefault("newsletter_description", "Meditaciones semanales, eventos exclusivos y más.\nDirecto a tu correo.")
    home_feed.setdefault("newsletter_placeholder", "Tu correo electrónico")
    home_feed.setdefault("newsletter_submit", "Suscribirme")
    home_feed.setdefault("newsletter_success_title", "¡Gracias por suscribirte!")
    home_feed.setdefault("newsletter_success_desc", "Recibirás meditaciones y novedades semanales.")

    # ── ABOUT / NOSOTROS ────────────────────────────────────────────────────
    about_hero = _get_block("ccf_about_hero") or {
        "eyebrow": "Nuestra Identidad",
        "title_lead": "Iluminando el",
        "title_accent": "camino juntos.",
        "description": "Somos la Comunidad Cristiana CCF, una iglesia viva y en crecimiento que existe para conectar corazones con Dios y entre sí.",
    }
    about_content = _get_block("ccf_about_feed") or {
        "stats": [
            {"value": "+20", "label": "Años de ministerio"},
            {"value": "+8", "label": "Pastores activos"},
            {"value": "+500", "label": "Familias"},
            {"value": "3", "label": "Sedes"},
        ],
        "vision_title": "¿A dónde vamos?",
        "vision_text": "Ser una comunidad de fe que transforma vidas, familias y ciudades a través del poder del Evangelio.",
        "mision_title": "¿Por qué existimos?",
        "mision_text": "Guiar, equipar y movilizar a cada persona mediante la enseñanza bíblica profunda, el compañerismo genuino y el servicio desinteresado.",
        "founder_label": "Nuestros Pastores Principales",
        "founder_title": "Un llamado a construir",
        "founder_title_accent": "una familia de fe",
        "founder1_name": "Luis Ricardo Meza G.",
        "founder1_role": "Pastor Principal",
        "founder1_image": _ensure_image("", media_find, "db401ca5"),
        "founder2_name": "Histar Ariza Herrera",
        "founder2_role": "Pastor Principal",
        "founder2_image": _ensure_image("", media_find, "b84ca87b"),
        "founder_bio": "La Comunidad Cristiana CCF nació de un profundo encuentro con la paternidad de Dios. Nuestros pastores principales han dedicado más de dos décadas a construir una iglesia que sea verdaderamente una casa.",
        "founder_bio2": "Desde sus inicios, el ADN de CCF ha sido claro: sana doctrina, corazón pastoral y vida en comunidad.",
        "valores_title": "Valores que nos Guían",
        "valores": [
            {"num": "01", "key": "palabra", "title": "Palabra", "desc": "La Escritura es nuestra brújula."},
            {"num": "02", "key": "amor", "title": "Amor Radical", "desc": "Un compromiso inquebrantable de servir y acoger a todos."},
            {"num": "03", "key": "comunidad", "title": "Comunidad", "desc": "Creemos en la vida en familia."},
            {"num": "04", "key": "integridad", "title": "Integridad", "desc": "Vivir con coherencia entre lo que creemos y lo que hacemos."},
            {"num": "05", "key": "mision", "title": "Misión", "desc": "Somos enviados a alcanzar a los que aún no conocen el amor de Cristo."},
            {"num": "06", "key": "excelencia", "title": "Excelencia", "desc": "Damos lo mejor de nosotros en todo lo que hacemos."},
        ],
        "quote_text": "La luz que encontramos en CCF no es para guardarla — es para guiar a otros que aún caminan en la oscuridad.",
        "quote_author": "Pastor Histar Ariza Herrera",
        "quote_subtitle": "Comunidad Cristiana CCF",
        "cta_title": "¿Listo para ser parte?",
        "cta_desc": "Ven a conocernos. Tenemos puertas abiertas y un lugar reservado para ti y tu familia.",
    }
    about_content.setdefault("founder_cta_team", "Conoce al equipo")
    about_content.setdefault("founder_cta_visit", "Visítanos")
    about_content.setdefault("values_eyebrow", "Lo que nos define")
    about_content.setdefault("cta_view_sedes", "Ver sedes")
    about_content.setdefault("cta_view_events", "Próximos eventos")
    about_content.setdefault("breadcrumbInicio", "Inicio")
    about_content.setdefault("breadcrumbPage", "Quiénes Somos")

    # ── PASTORS ─────────────────────────────────────────────────────────────
    pastors_hero_obj = _get_block("ccf_pastores_hero") or {
        "title": "Liderazgo Pastoral",
        "description": "Hombres y mujeres llamados por Dios para servir, guiar y amar a esta casa.",
    }
    pastors_hero_obj.setdefault("bg_image", _ensure_image("", media_find, "pastores"))
    pastors_feed_labels = _get_block("ccf_pastores_index", CMS_BLOCKS) or {
        "hero_badge": "Conoce a nuestro equipo pastoral",
        "hero_title": "Liderazgo Pastoral",
        "hero_description": "Hombres y mujeres llamados por Dios para servir, guiar y amar a esta casa.",
        "loading_label": "Cargando...",
        "empty_title": "No hay líderes pastorales registrados aún.",
        "card_cta": "Conocer más",
        "principal_label": "Pastor Principal",
    }
    pastors_raw = _get_block("ccf_pastores_feed") or _get_block("ccf_pastores_feed", CMS_BLOCKS) or {}
    pastors_list = pastors_raw.get("pastors") if isinstance(pastors_raw, dict) else pastors_raw
    if not isinstance(pastors_list, list):
        pastors_list = []

    # ── EVENTS ──────────────────────────────────────────────────────────────
    events_hero = _get_block("ccf_events_hero") or {
        "eyebrow": "Agenda CCF",
        "title": "Próximos Eventos",
        "description": "Momentos diseñados para conectarte con Dios y con nuestra comunidad. ¡No te los pierdas!",
    }
    events_feed = _get_block("ccf_events_feed", CMS_BLOCKS) or {
        "empty_title": "Sin eventos publicados",
        "empty_description": "Cuando el CMS publique eventos, aparecerán aquí sin tarjetas inventadas.",
        "calendar_title": "Explora nuestro Calendario",
        "calendar_description": "Organiza tu tiempo con nuestras actividades comunitarias.",
        "today_label": "HOY",
        "upcoming_label": "Próximo en 48 horas",
        "featured_badge": "Destacado",
        "reserve_cta": "Reservar lugar",
        "filters": ["Todos", "Conferencias", "Grupos de Conexión", "Cursos & Talleres", "Especiales"],
        "featured_empty_title": "Evento destacado",
        "featured_empty_description": "Contenido real desde el CMS",
        "channel_link_label": "Ver canal",
        "filters_title": "Filtrar por tipo",
        "sync_calendar_cta": "Sincronizar Calendario",
        "sync_calendar_toast": "Calendario descargado — impórtalo en Google Calendar o Outlook",
        "notifications_title": "¿Quieres recordatorios?",
        "notifications_desc": "Recibe avisos de tus eventos favoritos.",
        "notifications_toast": "Notificaciones de eventos próximamente — te avisaremos",
        "highlights_title": "Destacados",
        "highlights_empty": "Sin destacados publicados todavía.",
        "no_upcoming_label": "Sin eventos próximos publicados.",
        "no_location": "Sin ubicación publicada",
    }
    events_parsed: list[dict[str, Any]] = []

    # ── SERMONS ─────────────────────────────────────────────────────────────
    sermons_hero = _get_block("ccf_sermons_hero") or {
        "eyebrow": "Mensaje Destacado",
        "title_lead": "Alimento para el",
        "title_accent": "Alma",
        "description": "Explora nuestra biblioteca de mensajes que iluminan el camino.",
    }
    sermons_feed = _get_block("ccf_sermons_feed", CMS_BLOCKS) or {
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
        "featured_badge": "Más reciente",
        "retry_label": "Reintentar",
        "share_whatsapp": "WhatsApp",
        "copy_link": "Copiar",
        "copied_label": "¡Copiado!",
        "view_on_youtube": "Ver en YouTube",
        "close": "Cerrar",
    }

    # ── DISCOVER / CONOCER A JESÚS ──────────────────────────────────────────
    discover_hero = _get_block("ccf_discover_hero") or {
        "eyebrow": "Inicia tu camino",
        "title_lead": "La Luz que ",
        "title_accent": "Guía",
        "title_tail": " Tu Vida.",
        "description": "Conocer a Jesús no es una religión, es el comienzo de una relación que transforma la oscuridad en un propósito eterno.",
        "cta": "Quiero conocer a Jesús",
    }
    discover_hero.setdefault("bg_image", "")
    discover_feed_public = _get_block("ccf_discover_feed") or {}
    discover_feed_cms = _get_block("ccf_discover_feed", CMS_BLOCKS) or {}
    discover_feed = {**discover_feed_cms, **discover_feed_public}
    discover_feed.setdefault("intro_title", "Un Encuentro Personal")
    discover_feed.setdefault("intro_paragraph_1", "En CCF, creemos que cada historia es única. No importa dónde hayas estado o qué hayas hecho, la invitación es la misma: <strong>Ven y ve.</strong>")
    discover_feed.setdefault("intro_paragraph_2", "Descubre un espacio donde las preguntas son bienvenidas y la gracia es el lenguaje principal. Jesús ofrece descanso para el alma y una dirección clara para el futuro.")
    discover_feed.setdefault("testimonials_title", "Historias que iluminan")
    discover_feed.setdefault("testimonials_empty_title", "Próximamente compartiremos historias de transformación.")
    discover_feed.setdefault("contact_title", "Hablemos de Tu Caminar")
    discover_feed.setdefault("contact_description", "¿Tienes dudas? ¿Quieres orar por algo específico? Nuestro equipo está aquí para acompañarte sin juicios.")
    discover_feed.setdefault("name_label", "Nombre completo")
    discover_feed.setdefault("name_placeholder", "Tu nombre")
    discover_feed.setdefault("phone_label", "WhatsApp")
    discover_feed.setdefault("phone_placeholder", "+57 300...")
    discover_feed.setdefault("message_label", "¿En qué podemos ayudarte?")
    discover_feed.setdefault("message_placeholder", "Cuéntanos un poco sobre ti o tu petición de oración...")
    discover_feed.setdefault("submit_label", "Enviar mensaje y conectar")
    discover_feed.setdefault("submit_sending", "Enviando...")
    discover_feed.setdefault("success_title", "¡Gracias!")
    discover_feed.setdefault("success_description", "Hemos recibido tu mensaje. Te contactaremos pronto.")
    discover_feed.setdefault("error_message", "Hubo un error. Intenta de nuevo o escríbenos directamente.")
    discover_feed.setdefault("connection_error", "Ocurrió un error inesperado de conexión.")
    discover_feed.setdefault("benefits", [
        {"icon": "Heart", "title": "Gracia sin condenas", "desc": "Eres bienvenido tal como eres."},
        {"icon": "Star", "title": "Propósito real", "desc": "Descubre para qué fuiste creado."},
        {"icon": "Shield", "title": "Comunidad que cuida", "desc": "No estarás solo en este camino."},
        {"icon": "ArrowRight", "title": "Primer paso simple", "desc": "Escríbenos y conectamos."},
    ])
    discover_feed.setdefault("contact_info", [
        {"icon": "Clock", "text": "Respuesta en menos de 24 horas"},
        {"icon": "Mail", "text": "info@ccfministerio.com"},
    ])

    # ── COURSES ─────────────────────────────────────────────────────────────
    courses_hero = _get_block("ccf_courses_hero") or {
        "eyebrow": "Formación & Sabiduría",
        "title_lead": "El Camino",
        "title_accent": "del Aprendizaje",
        "description": "Explora nuestra academia de cursos especializados y sumérgete en una selección literaria para iluminar tu entendimiento.",
    }
    courses_base = _get_block("ccf_courses_feed", CMS_BLOCKS) or {}
    courses_merge = _get_block("ccf_courses_feed", CMS_MERGE) or {}
    courses_feed = {**courses_base, **courses_merge}
    courses_feed.setdefault("cta_title", "Únete a la Academia")
    courses_feed.setdefault("cta_description", "Recibe actualizaciones sobre nuevos cursos, lanzamientos de libros y eventos exclusivos de formación directamente en tu correo.")
    courses_feed.setdefault("cta_placeholder", "Tu correo electrónico")
    courses_feed.setdefault("cta_submit", "Suscribirme")
    courses_feed.setdefault("newsletter_success_toast", "¡Te has suscrito con éxito a nuestra academia!")
    courses_feed.setdefault("newsletter_error_toast", "Error al suscribirse. Inténtalo de nuevo.")
    courses_feed.setdefault("wishlist_success_toast_prefix", "añadido a tu lista — te contactaremos con info")
    courses_feed.setdefault("wishlist_fallback_toast_prefix", "guardado en tu lista")

    # ── LOCATIONS ───────────────────────────────────────────────────────────
    locations_hero = _get_block("ccf_locations_hero") or {
        "eyebrow": "Nuestra Presencia",
        "title": "Nuestras Sedes",
        "search_placeholder": "Buscar ciudad o dirección...",
    }
    locations_hero.setdefault("map_embed_url", "https://www.google.com/maps/d/embed?mid=1VDNpplw_9z1tcEhx25wEFRR5gQmnHgM&ehbc=2E312F")
    locations_hero.setdefault("main_badge", "Principal")
    locations_hero.setdefault("directions_cta", "Cómo llegar")
    locations_hero.setdefault("empty_locations", "No hay sedes configuradas para mostrar.")
    locations_hero.setdefault("empty_search", "No se encontraron sedes con ese criterio.")
    locations_feed = _get_block("ccf_locations_feed") or [
        {"id": 1, "name": "Sede Central", "address": "Av. Esperanza 124, Centro Financiero", "phone": "+57 320 000 0000", "schedule": "Domingos 9 AM y 11 AM", "midweek": "Lunes 7 PM", "isMain": True, "services": ["Domingos 9 AM", "Domingos 11 AM", "Lunes 7 PM"]},
        {"id": 2, "name": "Campus Norte", "address": "Calle 170 #54-12, Sector Universitario", "phone": "+57 310 111 2222", "schedule": "Domingos 10 AM", "midweek": "Sábados 6 PM", "isMain": False, "services": ["Domingos 10 AM", "Sábados 6 PM"]},
    ]

    # ── TESTIMONIALS ────────────────────────────────────────────────────────
    testimonials_hero = _get_block("ccf_testimonios_hero") or {
        "eyebrow": "Impacto Real",
        "title_lead": "Historias de",
        "title_accent": "Transformación",
        "description": "Vidas reales, cambios reales. Así es como el amor de Dios se hace visible en nuestra comunidad.",
    }
    testimonials_feed = _get_block("ccf_testimonials_feed", CMS_BLOCKS) or {
        "search_placeholder": "Buscar por tema, nombre o palabra clave",
        "loading_label": "Cargando...",
        "empty_title": "Todavía no hay testimonios publicados",
        "empty_description": "Cuando el CMS publique testimonios, aparecerán aquí.",
        "cta_label": "Compartir mi historia",
    }

    # ── BOLETÍN ─────────────────────────────────────────────────────────────
    boletin_hero = _get_block("ccf_boletin_hero", CMS_BLOCKS) or {
        "subtitle": "Boletín Semanal CCF",
        "title": "Recibe nuestra palabra de aliento",
        "description": "Cada semana te enviamos una reflexión bíblica, un versículo de ánimo y consejos prácticos para fortalecer tu fe.",
        "cta_text": "Suscribirme ahora",
        "success_message": "¡Gracias por suscribirte!",
        "error_message": "No se pudo suscribir. Intenta de nuevo.",
        "email_placeholder": "Tu correo electrónico",
        "sending_label": "Enviando...",
    }

    # ── WELCOME ─────────────────────────────────────────────────────────────
    welcome_content = _get_block("ccf_welcome", CMS_BLOCKS) or {
        "eyebrow": "Bienvenida",
        "title_template": "Hola, {name}.",
        "description": "No encontramos una cuenta registrada todavía, pero no te dejamos en una pantalla vacía. Puedes empezar por la ruta pública de fe y crecimiento que preparamos para ti.",
        "primary_cta": {"href": "/cursos", "label": "Discipulado Básico"},
        "secondary_cta": {"href": "/conocer-a-jesus", "label": "Una nueva vida con Cristo"},
        "highlights": [
            {"title": "Discipulado Básico", "description": "Empieza por la ruta de fundamentos para crecer con orden y acompañamiento.", "href": "/cursos", "cta": "Ver academia", "icon": "book"},
            {"title": "Una nueva vida con Cristo", "description": "Conoce el mensaje central del evangelio en una ruta pública y clara.", "href": "/conocer-a-jesus", "cta": "Abrir ruta", "icon": "heart"},
        ],
    }

    # ── PRIVACY ─────────────────────────────────────────────────────────────
    privacy_content = _get_block("ccf_privacy", CMS_BLOCKS) or {
        "last_update": "12 de junio de 2026",
        "summary": "Esta política describe cómo PLES SAS y la Comunidad Cristiana CCF recopilan, usan, almacenan y protegen tus datos personales.",
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
    }

    # ── GLOBAL ──────────────────────────────────────────────────────────────
    nav_items = _get_block("ccf_nav_items") or {
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
    }
    footer_config = _get_block("ccf_footer", CMS_BLOCKS) or {
        "description": "Iluminando el camino hacia una conexión profunda con lo divino a través de la comunidad y la guía espiritual. Una casa de fe abierta para toda la familia.",
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
    }
    footer_config.setdefault("copyright_company", "PLES SAS")
    footer_config.setdefault("copyright_company_url", "https://ples.com.co")
    footer_config.setdefault("copyright_text", "El uso inteligente de la experiencia. Todos los derechos reservados.")
    footer_config.setdefault("privacy_label", "Política de Privacidad")
    footer_config.setdefault("nav_section_title", "Navegación")
    footer_config.setdefault("resource_section_title", "Recursos")
    footer_config.setdefault("contact_section_title", "Contáctanos")

    mobile_nav = _get_block("ccf_mobile_nav", CMS_BLOCKS) or {
        "items": [
            {"href": "/", "label": "Inicio", "icon": "home"},
            {"href": "/eventos", "label": "Eventos", "icon": "calendar"},
            {"href": "/predicas", "label": "Prédicas", "icon": "play"},
            {"href": "/sedes", "label": "Sedes", "icon": "map-pin"},
            {"href": "/conocer-a-jesus", "label": "Conectar", "icon": "menu"},
        ]
    }

    return {
        "home": [
            {"key": "hero", "type": "hero", "props": home_hero, "sort": 0},
            {"key": "feed", "type": "feed", "props": _parsed(home_feed), "sort": 1},
        ],
        "about": [
            {"key": "hero", "type": "hero", "props": _parsed(about_hero), "sort": 0},
            {"key": "about", "type": "rich_text", "props": _parsed(about_content), "sort": 1},
        ],
        "pastors": [
            {"key": "hero", "type": "hero", "props": _content_json(pastors_hero_obj), "sort": 0},
            {"key": "feed", "type": "feed", "props": _content_json(pastors_feed_labels), "sort": 1},
            {"key": "pastors", "type": "team", "props": {"pastors": pastors_list}, "sort": 2},
        ],
        "events": [
            {"key": "hero", "type": "hero", "props": events_hero, "sort": 0},
            {"key": "feed", "type": "feed", "props": _content_json(events_feed), "sort": 1},
            {"key": "events", "type": "events_calendar", "props": _parsed(events_parsed), "sort": 2},
        ],
        "sermons": [
            {"key": "hero", "type": "hero", "props": sermons_hero, "sort": 0},
            {"key": "feed", "type": "feed", "props": _content_json(sermons_feed), "sort": 1},
        ],
        "discover": [
            {"key": "hero", "type": "hero", "props": discover_hero, "sort": 0},
            {"key": "feed", "type": "feed", "props": _parsed(discover_feed), "sort": 1},
        ],
        "courses": [
            {"key": "hero", "type": "hero", "props": courses_hero, "sort": 0},
            {"key": "feed", "type": "feed", "props": _parsed(courses_feed), "sort": 1},
        ],
        "locations": [
            {"key": "hero", "type": "hero", "props": locations_hero, "sort": 0},
            {"key": "feed", "type": "feed", "props": _parsed(locations_feed), "sort": 1},
        ],
        "testimonials": [
            {"key": "hero", "type": "hero", "props": testimonials_hero, "sort": 0},
            {"key": "feed", "type": "feed", "props": _content_json(testimonials_feed), "sort": 1},
        ],
        "boletin": [
            {"key": "hero", "type": "hero", "props": _content_json(boletin_hero), "sort": 0},
        ],
        "welcome": [
            {"key": "welcome", "type": "welcome", "props": _parsed(welcome_content), "sort": 0},
        ],
        "privacy": [
            {"key": "privacy", "type": "policy_document", "props": _parsed(privacy_content), "sort": 0},
        ],
        "_global": [
            {"key": "nav_items", "type": "feed", "props": nav_items, "sort": 0},
            {"key": "navbar_items", "type": "feed", "props": deepcopy(nav_items), "sort": 1},
            {"key": "footer_config", "type": "footer_config", "props": footer_config, "sort": 2},
            {"key": "mobile_menu_config", "type": "mobile_menu_config", "props": mobile_nav, "sort": 3},
        ],
    }


def _snapshot(page: Any, sections: list[dict[str, Any]]) -> dict[str, Any]:
    # Snapshot reflects the target published state so that a freshly-created
    # page (initially ``draft``) matches its first published version afterwards.
    return {
        "page": {
            "id": str(page.id),
            "slug": page.slug,
            "title": page.title,
            "status": "published",
            "seo_json": page.seo_json or {},
            "locale": page.locale,
        },
        "sections": [
            {
                "section_key": s["key"],
                "type": s["type"],
                "props_json": s["props"],
                "sort_order": s["sort"],
                "is_visible": True,
                "status": "active",
            }
            for s in sections
        ],
    }


def run() -> int:
    db = SessionLocal()
    try:
        print("=" * 60)
        print(" Seed public pages into CMS v2")
        print("=" * 60)

        # ── Site ────────────────────────────────────────────────────────────
        site = db.query(models.CmsSite).filter(models.CmsSite.is_active.is_(True)).first()
        if site is None:
            site = db.query(models.CmsSite).filter_by(site_key="ccf").first()
        if site is None:
            site = models.CmsSite(site_key="ccf", name="CCF", base_path="/", is_active=True)
            db.add(site)
            db.commit()
            db.refresh(site)
            print(f"Created CmsSite: {site.site_key} ({site.id})")
        else:
            print(f"Using CmsSite: {site.site_key} ({site.id})")

        media_find = _media_lookup(db)
        pages_specs = _build_pages(media_find)

        created_pages = 0
        updated_pages = 0
        created_sections = 0
        updated_sections = 0
        deleted_sections = 0
        published_versions = 0
        unchanged = 0

        for slug, sections in pages_specs.items():
            page = db.query(models.CmsPage).filter_by(site_id=site.id, slug=slug).first()
            if page is None:
                page = models.CmsPage(
                    site_id=site.id,
                    slug=slug,
                    title=_page_title(slug),
                    status="draft",
                    seo_json={},
                    locale="es",
                )
                db.add(page)
                db.commit()
                db.refresh(page)
                created_pages += 1
                print(f"Created page: {slug}")
            else:
                updated_pages += 1
                print(f"Updating page: {slug}")

            existing_sections = {
                s.section_key: s
                for s in db.query(models.CmsSection).filter_by(page_id=page.id).all()
            }
            desired_keys = {s["key"] for s in sections}

            # Remove stale sections for this page
            for key, section in existing_sections.items():
                if key not in desired_keys:
                    db.delete(section)
                    deleted_sections += 1
            db.commit()

            # Localize any external placeholder images before writing sections
            sections = _localize_external_images(db, sections)

            # Upsert desired sections
            for spec in sections:
                key = spec["key"]
                if key in existing_sections:
                    section = existing_sections[key]
                    section.type = spec["type"]
                    section.props_json = spec["props"]
                    section.sort_order = spec["sort"]
                    section.is_visible = True
                    section.status = "active"
                    section.deleted_at = None
                    updated_sections += 1
                else:
                    section = models.CmsSection(
                        page_id=page.id,
                        section_key=key,
                        type=spec["type"],
                        props_json=spec["props"],
                        sort_order=spec["sort"],
                        is_visible=True,
                        status="active",
                    )
                    db.add(section)
                    created_sections += 1
                db.commit()

            # Refresh page relationship for snapshot
            db.refresh(page)

            new_snapshot = _snapshot(page, sections)
            current_version = None
            if page.published_version_id:
                current_version = (
                    db.query(models.CmsPageVersion)
                    .filter_by(id=page.published_version_id)
                    .first()
                )

            if (
                page.status == "published"
                and current_version is not None
                and current_version.snapshot_json == new_snapshot
            ):
                unchanged += 1
                print(f"  → unchanged (published v{current_version.version_number})")
                continue

            # Determine next version number
            max_version = (
                db.query(models.CmsPageVersion)
                .filter_by(page_id=page.id)
                .order_by(models.CmsPageVersion.version_number.desc())
                .first()
            )
            next_version = (max_version.version_number + 1) if max_version else 1

            version = models.CmsPageVersion(
                page_id=page.id,
                version_number=next_version,
                snapshot_json=new_snapshot,
                notes="Seed public CMS v2 sections",
            )
            db.add(version)
            db.commit()
            db.refresh(version)

            page.published_version_id = version.id
            page.status = "published"
            db.add(page)
            db.commit()

            log = models.CmsPublishLog(
                site_id=site.id,
                page_id=page.id,
                entity_type="page",
                entity_id=str(page.id),
                action="publish",
                from_status=current_version and "published" or "draft",
                to_status="published",
                metadata_json={"version_id": str(version.id), "version_number": next_version},
            )
            db.add(log)
            db.commit()

            published_versions += 1
            print(f"  → published version {next_version}")

        print("=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"  Pages created: {created_pages}")
        print(f"  Pages updated: {updated_pages}")
        print(f"  Sections created: {created_sections}")
        print(f"  Sections updated: {updated_sections}")
        print(f"  Sections deleted: {deleted_sections}")
        print(f"  Versions published: {published_versions}")
        print(f"  Pages unchanged: {unchanged}")
        print("Done.")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"ERROR: {exc}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(run())
