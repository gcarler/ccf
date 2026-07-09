"""Pydantic schemas for CMS v2 section props validation."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, field_validator


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
        allowed = {"facebook", "instagram", "youtube", "tiktok", "whatsapp", "twitter", "telegram", "linkedin", "spotify", "apple-podcasts"}
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
        return max(1, min(int(v), 3650))


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
    phone_label: str = "WhatsApp"
    phone_placeholder: str = "+57 300..."
    message_label: str = "¿En qué podemos ayudarte?"
    message_placeholder: str = "Cuéntanos un poco sobre ti o tu petición de oración..."
    submit_label: str = "Enviar mensaje y conectar"
    success_message: str = "Gracias. Te contactaremos pronto."
    action_url: str = "/public/contact"


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
    brand_description: str = ""
    location_label: str = ""
    newsletter_label: str = ""
    copyright: str = ""
    copyright_url: str = ""
    nav_groups: List[FooterLinkGroup] = []
    social_links: List[SocialLinkItem] = []


class MobileMenuItem(BaseModel):
    label: str = ""
    href: str = ""
    icon: str = ""


class MobileMenuConfigProps(BaseModel):
    items: List[MobileMenuItem] = []


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
}


def validate_section_props(section_type: str, props: Dict[str, Any]) -> Dict[str, Any]:
    """Validate props against the schema for a given section type.
    
    Returns the validated props dict, or raises ValueError with details.
    Falls through gracefully for section types without schemas (existing 19).
    """
    schema_cls = SECTION_PROPS_SCHEMAS.get(section_type)
    if schema_cls is None:
        return props  # No schema defined, pass through
    
    try:
        validated = schema_cls.model_validate(props)
        return validated.model_dump(exclude_unset=True)
    except Exception as e:
        raise ValueError(f"Invalid props for section type '{section_type}': {e}")
