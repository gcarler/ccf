"""Pydantic schemas for CMS v2 section props validation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, field_validator

from backend.core.sanitize_html import sanitize_props_html


class ButtonItem(BaseModel):
    label: str = "Click"
    href: str = "/"
    variant: str = "primary"
    size: str = "md"
    icon: Optional[str] = None

    @field_validator("variant")
    @classmethod
    def validate_variant(cls, v: str) -> str:
        allowed = {"primary", "outline", "ghost"}
        if v not in allowed:
            raise ValueError(f"variant must be one of {allowed}")
        return v

    @field_validator("size")
    @classmethod
    def validate_size(cls, v: str) -> str:
        allowed = {"sm", "md", "lg"}
        if v not in allowed:
            raise ValueError(f"size must be one of {allowed}")
        return v


class TocItem(BaseModel):
    label: str = "Sección"
    href: str = "#"


class CollapsibleItem(BaseModel):
    question: str = "Pregunta"
    answer: str = "Respuesta"


class SocialLinkItem(BaseModel):
    platform: str = "facebook"
    url: str = "#"
    label: str = ""

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        allowed = {
            "facebook",
            "instagram",
            "youtube",
            "tiktok",
            "whatsapp",
            "twitter",
            "telegram",
            "linkedin",
            "spotify",
            "apple-podcasts",
        }
        if v not in allowed:
            raise ValueError(f"platform must be one of {allowed}")
        return v


class CalendarItem(BaseModel):
    title: str = "Evento"
    date: Optional[str] = None
    time: Optional[str] = None
    location: Optional[str] = None


class ContentBlock(BaseModel):
    type: str = "text"
    content: Optional[str] = None
    image_url: Optional[str] = None
    alt: Optional[str] = None
    caption: Optional[str] = None
    text: Optional[str] = None
    author: Optional[str] = None
    height: Optional[str] = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed = {"text", "image", "video", "quote", "divider", "spacer", "list"}
        if v not in allowed:
            raise ValueError(f"block type must be one of {allowed}")
        return v


# Section-specific props schemas
class ButtonProps(BaseModel):
    buttons: List[ButtonItem] = []
    align: str = "center"
    gap: str = "4"


class TocProps(BaseModel):
    title: str = "En esta página"
    items: List[TocItem] = []
    style: str = "numbered"


class DividerProps(BaseModel):
    style: str = "solid"
    color: str = "primary"
    thickness: str = "2"
    margin_top: str = "8"
    margin_bottom: str = "8"
    width: str = "full"


class CollapsibleProps(BaseModel):
    title: str = "Información"
    default_open: bool = False
    content_html: str = ""
    bg_color: str = "surface"
    border: bool = True


class SocialLinksProps(BaseModel):
    title: str = "Síguenos"
    items: List[SocialLinkItem] = []
    layout: str = "row"
    show_labels: bool = True
    icon_size: str = "24"


class SpacerProps(BaseModel):
    height: str = "32"
    bg_color: str = "transparent"
    label: str = "Espacio"


class CalendarProps(BaseModel):
    title: str = "Próximos Eventos"
    source: str = "manual"
    api_endpoint: Optional[str] = None
    view: str = "list"
    max_events: int = 10
    show_time: bool = True
    show_location: bool = True
    items: List[CalendarItem] = []


class MapProps(BaseModel):
    title: str = "Encuéntranos"
    provider: str = "google"
    embed_url: str = ""
    address: str = ""
    lat: Optional[float] = None
    lng: Optional[float] = None
    zoom: int = 15
    height: str = "400"
    show_directions_link: bool = True


class DocumentUploadProps(BaseModel):
    title: str = "Subir Documento"
    description: str = ""
    accepted_types: str = ".pdf,.doc,.docx,.jpg,.png"
    max_size_mb: str = "10"
    upload_endpoint: Optional[str] = None
    success_message: str = "Documento enviado correctamente"
    show_file_list: bool = True


class ContentBlocksProps(BaseModel):
    layout: str = "grid"
    columns: str = "2"
    items: List[ContentBlock] = []


class AccordionProps(BaseModel):
    title: str = ""
    subtitle: str = ""
    items: List[CollapsibleItem] = []
    style: str = "bordered"
    open_multiple: bool = False


class PopupProps(BaseModel):
    title: str = "Aviso Importante"
    body: str = ""
    cta_label: str = "Ver Más"
    cta_href: str = "/"
    delay_ms: int = 2000
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    show_on_paths: List[str] = []
    hide_on_paths: List[str] = []
    dismiss_mode: str = "local"
    dismiss_days: int = 30
    dismiss_key: str = ""

    @field_validator("dismiss_mode")
    @classmethod
    def validate_dismiss_mode(cls, v: str) -> str:
        allowed = {"local", "session", "none"}
        value = (v or "").strip().lower()
        if value not in allowed:
            raise ValueError(f"dismiss_mode must be one of {allowed}")
        return value

    @field_validator("dismiss_days")
    @classmethod
    def validate_dismiss_days(cls, v: int) -> int:
        # M-06 (errorescms.md): Pydantic v2 ya valida el tipo int antes de
        # llamar el field_validator, asi que v siempre es int aqui. El int(v)
        # anterior era redundante y daba falsa sensacion de robustez; sin el,
        # un string no convertible como "abc" se rechaza con 422 en la capa
        # de Pydantic (no 500). El clamp [1, 3650] es el rango logico.
        return max(1, min(v, 3650))


class EventsCalendarProps(BaseModel):
    title: str = "Próximos Eventos"
    subtitle: str = ""
    show_filters: bool = True
    filters: List[str] = ["Todos", "Conferencias", "Grupos de Conexión", "Cursos & Talleres", "Especiales"]
    max_events: int = 50
    show_ics_export: bool = True
    empty_title: str = "Sin eventos publicados"
    empty_description: str = "Cuando el CMS publique eventos, aparecerán aquí."
    featured_badge: str = "Destacado"
    reserve_cta: str = "Reservar lugar"


class VideoGridProps(BaseModel):
    title: str = "Prédicas & Mensajes"
    subtitle: str = ""
    channel_url: str = ""
    channel_label: str = "Ver canal"
    max_videos: int = 12
    search_placeholder: str = "Buscar por título o predicador…"
    empty_title: str = "No se pudieron cargar los videos"
    empty_description: str = "Verifica tu conexión o intenta nuevamente."


class LocationItem(BaseModel):
    name: str = "Sede"
    address: str = ""
    city: str = ""
    phone: str = ""
    schedule: str = ""
    embed_url: str = ""
    lat: Optional[float] = None
    lng: Optional[float] = None
    is_main: bool = False


class LocationsListProps(BaseModel):
    title: str = "Nuestras Sedes"
    subtitle: str = ""
    search_placeholder: str = "Buscar ciudad o dirección..."
    show_map: bool = True
    locations: List[LocationItem] = []


class ContactFormProps(BaseModel):
    title: str = "Hablemos de Tu Caminar"
    subtitle: str = ""
    name_label: str = "Nombre completo"
    name_placeholder: str = "Tu nombre"
    email_label: str = "Correo electrónico"
    email_placeholder: str = "tu@email.com (opcional)"
    phone_label: str = "WhatsApp"
    phone_placeholder: str = "+57 300..."
    message_label: str = "¿En qué podemos ayudarte?"
    message_placeholder: str = "Cuéntanos un poco sobre ti o tu petición de oración..."
    submit_label: str = "Enviar mensaje y conectar"
    success_message: str = "Gracias. Te contactaremos pronto."
    action_url: str = "/public/contact"
    reset_label: str = "Enviar otro mensaje"
    full_bleed: bool = False


class PrayerFormProps(BaseModel):
    title: str = "Pedir oración"
    subtitle: str = ""
    name_label: str = "Nombre"
    name_placeholder: str = "Tu nombre"
    request_label: str = "Petición de oración"
    request_placeholder: str = "Comparte tu necesidad..."
    submit_label: str = "Enviar al equipo pastoral"
    success_message: str = "Tu petición ha sido enviada."
    action_url: str = "/crm/prayer-requests/public"
    reset_label: str = "Enviar otra petición"


class CourseItem(BaseModel):
    id: str = ""
    title: str = ""
    description: str = ""
    instructor: str = ""
    modality: str = ""
    lessons: int = 0
    image_url: Optional[str] = None
    cta_label: str = "Quiero Inscribirme"


class CourseGridProps(BaseModel):
    title: str = "Cursos & Academia"
    subtitle: str = ""
    courses_title: str = "Cursos & Academia"
    courses_description: str = ""
    featured_course_id: Optional[str] = None
    show_free_only: bool = False
    courses: List[CourseItem] = []
    empty_title: str = "No hay cursos disponibles"
    empty_description: str = "Próximamente publicaremos nuevos cursos."


class BookItem(BaseModel):
    id: str = ""
    title: str = ""
    author: str = ""
    price: str = ""
    description: str = ""
    image_url: Optional[str] = None


class BookShopProps(BaseModel):
    title: str = "Nuestra Librería"
    subtitle: str = ""
    books: List[BookItem] = []
    empty_message: str = "Próximamente tendremos libros disponibles."


class TestimonialItem(BaseModel):
    author: str = ""
    role: str = ""
    content: str = ""
    image_url: Optional[str] = None
    stars: int = 5


class TestimonialsMasonryProps(BaseModel):
    title: str = "Historias de Transformación"
    subtitle: str = ""
    testimonials: List[TestimonialItem] = []
    cta_label: str = "Compartir mi historia"
    cta_href: str = "#"
    empty_title: str = "Próximamente compartiremos historias de transformación."


class PolicySectionItem(BaseModel):
    id: str = ""
    title: str = ""
    content: str = ""


class PolicyDocumentProps(BaseModel):
    title: str = "Política de Privacidad"
    last_update: str = ""
    summary: str = ""
    sections: List[PolicySectionItem] = []


class FooterLinkGroup(BaseModel):
    title: str = ""
    links: List[SocialLinkItem] = []


class FooterConfigProps(BaseModel):
    model_config = {"extra": "ignore"}
    # Shape realmente persistida/consumida por FaroFooter/Footer. El schema
    # estricto anterior (extra=ignore) descartaba todas estas claves al guardar
    # desde el builder, rompiendo el footer publicado.
    description: Optional[str] = None
    nav_links: Optional[List[Dict[str, Any]]] = None
    resource_links: Optional[List[Dict[str, Any]]] = None
    social_links: Optional[List[Dict[str, Any]]] = None
    section_titles: Optional[Dict[str, Any]] = None
    contact: Optional[Dict[str, Any]] = None
    copyright: Optional[Dict[str, Any]] = None
    privacy_label: Optional[str] = None
    privacy_href: Optional[str] = None
    location_label: Optional[str] = None
    newsletter_label: Optional[str] = None
    copyright_company: Optional[str] = None
    copyright_company_url: Optional[str] = None
    copyright_text: Optional[str] = None
    nav_section_title: Optional[str] = None
    resource_section_title: Optional[str] = None
    contact_section_title: Optional[str] = None
    # Compatibility keys (renderer de config) — se conservan para compatibilidad
    brand_description: Optional[str] = None
    copyright_url: Optional[str] = None
    nav_groups: Optional[List[FooterLinkGroup]] = None


class MobileMenuItem(BaseModel):
    label: str = ""
    href: str = ""
    icon: str = ""


class MobileMenuConfigProps(BaseModel):
    items: List[MobileMenuItem] = []


# ── C-06/H-11 hardening: schemas for the 24 section types that previously
#    fell through validate_section_props with only HTML sanitisation and no
#    structural validation. Every schema is permissive (extra="ignore") and
#    mirrors the frontend ``PublicSectionRenderer`` contract (field names +
#    defaults match what ``val(props, key, default)`` reads). HTML-bearing
#    fields are still routed through ``sanitize_props_html`` upstream.
class _PermissiveProps(BaseModel):
    model_config = {"extra": "ignore"}


class HeroSlideItem(BaseModel):
    model_config = {"extra": "ignore"}
    src: Optional[str] = None
    url: Optional[str] = None
    alt: Optional[str] = None
    title: Optional[str] = None
    caption: Optional[str] = None
    href: Optional[str] = None
    status: Optional[str] = None


class HeroProps(_PermissiveProps):
    title: str = ""
    title_lead: str = ""
    title_accent: str = ""
    title_tail: str = ""
    description: str = ""
    body: str = ""
    eyebrow: str = ""
    primary_cta: str = ""
    primary_cta_href: str = "/"
    secondary_cta: str = ""
    secondary_cta_href: str = "/"
    cta_label: str = ""
    cta_href: str = "/"
    bg_image: str = ""
    image_url: str = ""
    image_alt: str = ""
    slides: List[HeroSlideItem] = []
    items: List[HeroSlideItem] = []


class VideoHeroProps(_PermissiveProps):
    title: str = ""
    body: str = ""
    cta_label: str = ""
    cta_href: str = "/"
    video_url: str = ""
    full_bleed: bool = False


class RichTextProps(_PermissiveProps):
    title: str = ""
    body: str = ""
    cta_label: str = ""
    cta_href: str = "/"
    # Blog archive_template (etiqueta/categoría)
    category_title_prefix: Optional[str] = None
    category_description_template: Optional[str] = None
    tag_title_prefix: Optional[str] = None
    tag_description_template: Optional[str] = None
    back_to_blog_label: Optional[str] = None
    empty_tag_title: Optional[str] = None
    empty_tag_description: Optional[str] = None
    empty_category_title: Optional[str] = None
    empty_category_description: Optional[str] = None
    full_bleed: bool = False
    # Detail templates (testimonios)
    footer_label: Optional[str] = None
    back_label: Optional[str] = None
    not_found_title: Optional[str] = None
    not_found_description: Optional[str] = None
    not_found_cta: Optional[str] = None
    prayer_action_label: Optional[str] = None
    share_action_label: Optional[str] = None
    share_toast_success: Optional[str] = None
    share_toast_error: Optional[str] = None
    prayer_success_title: Optional[str] = None
    prayer_success_description: Optional[str] = None
    prayer_success_close: Optional[str] = None
    prayer_form_badge: Optional[str] = None
    prayer_form_title: Optional[str] = None
    prayer_form_description: Optional[str] = None
    prayer_name_placeholder: Optional[str] = None
    prayer_request_placeholder: Optional[str] = None
    prayer_submit_label: Optional[str] = None
    # Detail templates (cursos)
    about_title: Optional[str] = None
    instructor_label: Optional[str] = None
    syllabus_title: Optional[str] = None
    enroll_button_default: Optional[str] = None
    enrolled_label: Optional[str] = None
    enroll_drawer_title: Optional[str] = None
    enroll_drawer_description: Optional[str] = None
    enroll_name_label: Optional[str] = None
    enroll_email_label: Optional[str] = None
    enroll_phone_label: Optional[str] = None
    enroll_cancel_label: Optional[str] = None
    enroll_submit_label: Optional[str] = None
    enroll_submitting_label: Optional[str] = None
    enroll_success_toast: Optional[str] = None
    enroll_error_toast: Optional[str] = None
    # Detail templates (pastores)
    badge_label: Optional[str] = None
    role_fallback: Optional[str] = None
    quote_subtitle: Optional[str] = None
    tags: Optional[List[str]] = None
    motto_label: Optional[str] = None
    story_title: Optional[str] = None
    story_subtitle: Optional[str] = None
    cta_eyebrow: Optional[str] = None
    cta_description: Optional[str] = None
    cta_primary_label: Optional[str] = None
    cta_secondary_label: Optional[str] = None


class RichTextColumnsProps(_PermissiveProps):
    title: str = ""
    body: str = ""
    body_2: str = ""


class AboutProps(_PermissiveProps):
    stats: List[Dict[str, Any]] = []
    vision_title: str = ""
    vision_text: str = ""
    mision_title: str = ""
    mision_text: str = ""
    founder_label: str = ""
    founder_title: str = ""
    founder_title_accent: str = ""
    founder1_name: str = ""
    founder1_role: str = ""
    founder1_image: str = ""
    founder2_name: str = ""
    founder2_role: str = ""
    founder2_image: str = ""
    founder_bio: str = ""
    founder_bio2: str = ""
    valores_title: str = ""
    valores: List[Dict[str, Any]] = []
    quote_text: str = ""
    quote_author: str = ""
    quote_subtitle: str = ""
    cta_title: str = ""
    cta_desc: str = ""
    founder_cta_team: str = ""
    founder_cta_visit: str = ""
    values_eyebrow: str = ""
    cta_view_sedes: str = ""
    cta_view_events: str = ""
    breadcrumbInicio: str = ""
    breadcrumbPage: str = ""
    title: str = ""
    body: str = ""
    cta_label: str = ""
    cta_href: str = "/"


class CardItem(BaseModel):
    model_config = {"extra": "ignore"}
    title: Optional[str] = None
    body: Optional[str] = None
    href: Optional[str] = None
    icon: Optional[str] = None


class CardsProps(_PermissiveProps):
    title: str = ""
    body: str = ""
    items: List[CardItem] = []
    # Blog feed is seeded as ``cards`` (seed_blog_sermons_cms) and reads
    # these extra keys from the public page.
    search_placeholder: Optional[str] = None
    empty_title: Optional[str] = None
    empty_description: Optional[str] = None
    read_more_label: Optional[str] = None


class CtaBannerProps(_PermissiveProps):
    title: str = ""
    body: str = ""
    cta_label: str = ""
    cta_href: str = "/"
    cta_label_2: str = ""
    cta_href_2: str = "/"


class GalleryItem(BaseModel):
    model_config = {"extra": "ignore"}
    url: Optional[str] = None
    alt: Optional[str] = None
    caption: Optional[str] = None


class GalleryProps(_PermissiveProps):
    title: str = ""
    body: str = ""
    image_url: str = ""
    image_alt: str = ""
    items: List[GalleryItem] = []


class GalleryMasonryProps(_PermissiveProps):
    """Gallery block with an optional horizontal carousel presentation."""

    title: str = ""
    body: str = ""
    columns: int = 3
    images: List[GalleryItem] = []
    layout: str = "masonry"
    album_url: str = ""
    album_label: str = "Ver más fotos"
    autoplay: bool = False
    full_bleed: bool = False


class FaqItem(BaseModel):
    model_config = {"extra": "ignore"}
    q: Optional[str] = None
    a: Optional[str] = None


class FaqProps(_PermissiveProps):
    title: str = ""
    items: List[FaqItem] = []


class EmbedProps(_PermissiveProps):
    title: str = ""
    body: str = ""
    embed_url: str = ""


class FeedProps(_PermissiveProps):
    # Home / landing page style
    eyebrow: Optional[str] = None
    section_title: Optional[str] = None
    section_description: Optional[str] = None
    featured_card: Optional[Dict[str, Any]] = None
    cards: Optional[List[Dict[str, Any]]] = None
    activities_eyebrow: Optional[str] = None
    activities_title: Optional[str] = None
    activities_view_all: Optional[str] = None
    activities_view_all_href: Optional[str] = None
    activities_empty: Optional[str] = None
    scroll_indicator: Optional[str] = None
    newsletter_eyebrow: Optional[str] = None
    newsletter_title: Optional[str] = None
    newsletter_description: Optional[str] = None
    newsletter_placeholder: Optional[str] = None
    newsletter_submit: Optional[str] = None
    newsletter_sending_label: Optional[str] = None
    newsletter_success_title: Optional[str] = None
    newsletter_success_desc: Optional[str] = None

    # Sermons / predicas style
    content: Optional[str] = None
    hero_eyebrow: Optional[str] = None
    youtube_channel_url: Optional[str] = None
    # Overrides editoriales por ID de video; el feed anidado en ``content``
    # sigue siendo JSON libre y se valida/renderiza en el frontend.
    thumbnail_overrides: Optional[Dict[str, str]] = None

    # Courses / cursos style
    hero_image_url: Optional[str] = None
    courses_title: Optional[str] = None
    courses_description: Optional[str] = None
    empty_title: Optional[str] = None
    empty_description: Optional[str] = None
    cta_images: Optional[List[Dict[str, Any]]] = None
    library_title: Optional[str] = None
    library_description: Optional[str] = None
    empty_books_message: Optional[str] = None
    featured_fallback_image_url: Optional[str] = None
    course_cards: Optional[List[Dict[str, Any]]] = None
    books: Optional[List[Dict[str, Any]]] = None
    cta_title: Optional[str] = None
    cta_description: Optional[str] = None
    cta_placeholder: Optional[str] = None
    cta_submit: Optional[str] = None
    newsletter_success_toast: Optional[str] = None
    newsletter_error_toast: Optional[str] = None
    wishlist_success_toast_prefix: Optional[str] = None
    wishlist_fallback_toast_prefix: Optional[str] = None

    # Testimonials style
    search_placeholder: Optional[str] = None
    loading_label: Optional[str] = None
    hero_badge: Optional[str] = None
    hero_title_lead: Optional[str] = None
    hero_title_accent: Optional[str] = None
    hero_description: Optional[str] = None
    cta_label: Optional[str] = None

    # Events style
    no_events_title: Optional[str] = None
    no_events_description: Optional[str] = None
    calendar_title: Optional[str] = None
    calendar_description: Optional[str] = None
    today_label: Optional[str] = None
    upcoming_label: Optional[str] = None
    featured_badge: Optional[str] = None
    reserve_cta: Optional[str] = None
    filters: Optional[List[str]] = None
    featured_empty_title: Optional[str] = None
    featured_empty_description: Optional[str] = None
    channel_link_label: Optional[str] = None
    filters_title: Optional[str] = None
    sync_calendar_cta: Optional[str] = None
    sync_calendar_toast: Optional[str] = None
    notifications_title: Optional[str] = None
    notifications_desc: Optional[str] = None
    notifications_toast: Optional[str] = None
    highlights_title: Optional[str] = None
    highlights_empty: Optional[str] = None
    no_upcoming_label: Optional[str] = None
    no_location: Optional[str] = None
    month_names: Optional[List[str]] = None
    week_view_label: Optional[str] = None
    month_view_label: Optional[str] = None
    year_view_label: Optional[str] = None
    read_more_label: Optional[str] = None

    # Pastors style
    hero_title: Optional[str] = None
    card_cta: Optional[str] = None
    principal_label: Optional[str] = None

    # Generic fallback
    title: Optional[str] = None
    body: Optional[str] = None
    items: Optional[List[Dict[str, Any]]] = None


class TestimonialItemPublic(BaseModel):
    model_config = {"extra": "ignore"}
    author: Optional[str] = None
    role: Optional[str] = None
    content: Optional[str] = None
    stars: int = 5


class TestimonialsProps(_PermissiveProps):
    title: str = "Testimonios"
    items: List[TestimonialItemPublic] = []


class StatItem(BaseModel):
    model_config = {"extra": "ignore"}
    value: Optional[str] = None
    label: Optional[str] = None


class StatsProps(_PermissiveProps):
    title: str = ""
    items: List[StatItem] = []


class TeamMemberItem(BaseModel):
    model_config = {"extra": "ignore"}
    name: Optional[str] = None
    role: Optional[str] = None
    image: Optional[str] = None
    bio: Optional[str] = None


class TeamProps(_PermissiveProps):
    title: str = "Nuestro Equipo"
    items: List[TeamMemberItem] = []


class CountdownProps(_PermissiveProps):
    title: str = "Próximo Evento"
    target_date: str = ""
    body: str = ""


class PricingItem(BaseModel):
    model_config = {"extra": "ignore"}
    name: Optional[str] = None
    price: Optional[str] = None
    features: Optional[str] = None
    btn: Optional[str] = None
    btn_href: Optional[str] = None


class PricingProps(_PermissiveProps):
    title: str = "Opciones"
    items: List[PricingItem] = []


class ImageTextProps(_PermissiveProps):
    title: str = ""
    body: str = ""
    image_url: str = ""
    image_alt: str = ""
    cta_label: str = ""
    cta_href: str = "/"
    image_side: str = "right"


class TimelineEntryItem(BaseModel):
    model_config = {"extra": "ignore"}
    year: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None


class TimelineProps(_PermissiveProps):
    title: str = ""
    items: List[TimelineEntryItem] = []
    full_bleed: bool = False


class IconGridItem(BaseModel):
    model_config = {"extra": "ignore"}
    icon: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None


class IconGridProps(_PermissiveProps):
    title: str = ""
    body: str = ""
    items: List[IconGridItem] = []


class NewsletterProps(_PermissiveProps):
    title: str = "Mantente conectado"
    body: str = ""
    cta_label: str = "Suscribirse"
    action_url: str = ""


class CivicHeroSearchProps(_PermissiveProps):
    eyebrow: str = ""
    title: str = "¿Qué trámite buscas?"
    subtitle: str = "Encuentra todo en un solo lugar."
    placeholder: str = "Buscar trámites..."
    action_url: str = "/buscar"
    background_image: str = ""
    suggestions: List[str] = []


class CivicConvocatoriaItem(BaseModel):
    model_config = {"extra": "ignore"}
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    deadline: Optional[str] = None
    category: Optional[str] = None
    href: Optional[str] = None


class CivicConvocatoriaCardsProps(_PermissiveProps):
    title: str = "Convocatorias"
    body: str = ""
    items: List[CivicConvocatoriaItem] = []


class CivicQuickLinkItem(BaseModel):
    model_config = {"extra": "ignore"}
    icon: Optional[str] = None
    label: Optional[str] = None
    href: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None


class CivicQuickLinksProps(_PermissiveProps):
    title: str = "Accesos Rápidos"
    body: str = ""
    columns: str = "4"
    items: List[CivicQuickLinkItem] = []


class CivicFileDownloadItem(BaseModel):
    model_config = {"extra": "ignore"}
    name: Optional[str] = None
    file_url: Optional[str] = None
    format: Optional[str] = None
    size_label: Optional[str] = None
    description: Optional[str] = None


class CivicFileDownloadsProps(_PermissiveProps):
    title: str = "Documentos para descarga"
    body: str = ""
    items: List[CivicFileDownloadItem] = []


class CivicDataTableProps(_PermissiveProps):
    title: str = ""
    caption: str = ""
    headers: List[str] = []
    rows: List[List[str]] = []
    highlight_first_col: bool = True
    striped: bool = True
    footer_note: str = ""


class CivicAlertBannerProps(_PermissiveProps):
    level: str = "warning"
    title: str = ""
    message: str = ""
    cta_label: str = ""
    cta_href: str = ""
    dismissible: bool = True


# Union schema for validation dispatch
SECTION_PROPS_SCHEMAS: Dict[str, type[BaseModel]] = {
    "button": ButtonProps,
    "toc": TocProps,
    "divider": DividerProps,
    "collapsible": CollapsibleProps,
    "social_links": SocialLinksProps,
    "spacer": SpacerProps,
    "calendar": CalendarProps,
    "map": MapProps,
    "document_upload": DocumentUploadProps,
    "content_blocks": ContentBlocksProps,
    "accordion": AccordionProps,
    "popup_banner": PopupProps,
    "events_calendar": EventsCalendarProps,
    "video_grid": VideoGridProps,
    "locations_list": LocationsListProps,
    "contact_form": ContactFormProps,
    "prayer_form": PrayerFormProps,
    "course_grid": CourseGridProps,
    "book_shop": BookShopProps,
    "testimonials_masonry": TestimonialsMasonryProps,
    "policy_document": PolicyDocumentProps,
    "footer_config": FooterConfigProps,
    "mobile_menu_config": MobileMenuConfigProps,
    # C-06/H-11: previously fell through to partial sanitisation only
    "hero": HeroProps,
    "video_hero": VideoHeroProps,
    "rich_text": RichTextProps,
    "rich_text_columns": RichTextColumnsProps,
    "about": AboutProps,
    "cards": CardsProps,
    "cta_banner": CtaBannerProps,
    "gallery": GalleryProps,
    "gallery_masonry": GalleryMasonryProps,
    "faq": FaqProps,
    "embed": EmbedProps,
    "testimonials": TestimonialsProps,
    "stats": StatsProps,
    "team": TeamProps,
    "countdown": CountdownProps,
    "pricing": PricingProps,
    "image_text": ImageTextProps,
    "timeline": TimelineProps,
    "icon_grid": IconGridProps,
    "newsletter": NewsletterProps,
    "civic_hero_search": CivicHeroSearchProps,
    "civic_convocatoria_cards": CivicConvocatoriaCardsProps,
    "civic_quick_links": CivicQuickLinksProps,
    "civic_file_downloads": CivicFileDownloadsProps,
    "civic_data_table": CivicDataTableProps,
    "civic_alert_banner": CivicAlertBannerProps,
    "feed": FeedProps,
}


def validate_section_props(section_type: str, props: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitise props against the schema for a given section type.

    Besides Pydantic validation, every string field that contains or looks
    like HTML is run through the whitelist-based sanitiser to mitigate
    stored XSS in public rendering.

    Returns the validated/sanitised props dict, or raises ValueError with details.
    Falls through to ``sanitize_props_html`` only for section types not in
    ``SECTION_PROPS_SCHEMAS`` (custom admin types registered without a schema) —
    that path keeps the mitigation for unschema'd types but cannot enforce
    structure. All canonical ``get_allowed_section_types()`` now have schemas.
    """
    schema_cls = SECTION_PROPS_SCHEMAS.get(section_type)
    if schema_cls is None:
        return sanitize_props_html(props) if props else props

    try:
        cleaned = sanitize_props_html(props)
        validated = schema_cls.model_validate(cleaned)
        # exclude_unset preserves partial admin edits; model_config extra="ignore"
        # silently drops unexpected keys so stored props stay clean.
        return validated.model_dump(exclude_unset=True)
    except Exception as e:
        raise ValueError(f"Invalid props for section type '{section_type}': {e}")
