"""Pydantic schemas for CMS v2 section props validation."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, field_validator, model_validator


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
