from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from backend.schemas._common import orm_config


class CmsMetrics(BaseModel):
    testimonials_total: int
    testimonials_approved: int
    announcements_total: int
    announcements_active: int
    media_total: int = 0
    media_images: int = 0
    media_videos: int = 0
    media_audio: int = 0


class CmsMediaCreate(BaseModel):
    url: str
    alt_text: Optional[str] = None
    section: str = "general"
    tags: List[str] = Field(default_factory=list)
    filename: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    status: str = "active"


class CmsMediaUpdate(BaseModel):
    url: Optional[str] = None
    alt_text: Optional[str] = None
    section: Optional[str] = None
    tags: Optional[List[str]] = None
    filename: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    status: Optional[str] = None


class CmsMediaRead(BaseModel):
    id: UUID
    url: str
    alt_text: Optional[str] = None
    dimensions: Optional[str] = None
    filename: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    section: str
    tags: List[str] = Field(default_factory=list)
    status: str = "active"
    created_by_persona_id: Optional[UUID] = None
    # Axioma 3 — Multi-Tenant: ``sede_id`` read-only se expone para que
    # el frontend pueda auditar a qué sede pertenece cada media sin un
    # JOIN adicional. No editable vía Create/Update (server-side derivar).
    sede_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


class CmsSiteCreate(BaseModel):
    site_key: str
    name: str
    base_path: str
    is_active: bool = True
    sede_id: Optional[UUID] = None


class CmsSiteUpdate(BaseModel):
    name: Optional[str] = None
    base_path: Optional[str] = None
    is_active: Optional[bool] = None
    sede_id: Optional[UUID] = None


class CmsSiteRead(BaseModel):
    id: UUID
    site_key: str
    name: str
    base_path: str
    is_active: bool
    sede_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


CmsThemeStatus = Literal["active", "archived"]


class CmsThemeCreate(BaseModel):
    name: str
    tokens_json: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = False
    status: CmsThemeStatus = "active"


class CmsThemeUpdate(BaseModel):
    name: Optional[str] = None
    tokens_json: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    status: Optional[CmsThemeStatus] = None


class CmsThemeRead(BaseModel):
    id: UUID
    site_id: UUID
    name: str
    tokens_json: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool
    status: CmsThemeStatus = "active"
    version: int
    created_by_persona_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


class CmsMenuCreate(BaseModel):
    menu_key: str
    name: str
    is_active: bool = True


class CmsMenuUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


class CmsMenuRead(BaseModel):
    id: UUID
    site_id: UUID
    menu_key: str
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


class CmsMenuItemCreate(BaseModel):
    label: str
    href: str
    parent_id: Optional[UUID] = None
    target: str = "_self"
    is_external: bool = False
    visibility: str = "public"
    sort_order: int = 0
    meta_json: Dict[str, Any] = Field(default_factory=dict)


class CmsMenuItemUpdate(BaseModel):
    label: Optional[str] = None
    href: Optional[str] = None
    parent_id: Optional[UUID] = None
    target: Optional[str] = None
    is_external: Optional[bool] = None
    visibility: Optional[str] = None
    sort_order: Optional[int] = None
    meta_json: Optional[Dict[str, Any]] = None


class CmsMenuItemReorderItem(BaseModel):
    id: UUID
    parent_id: Optional[UUID] = None
    sort_order: int


class CmsMenuItemReorderPayload(BaseModel):
    items: List[CmsMenuItemReorderItem]


class CmsMenuItemRead(BaseModel):
    id: UUID
    menu_id: UUID
    parent_id: Optional[UUID] = None
    label: str
    href: str
    target: str
    is_external: bool
    visibility: str
    sort_order: int
    meta_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


class CmsPageCreate(BaseModel):
    slug: str
    title: str
    status: str = "draft"
    seo_json: Dict[str, Any] = Field(default_factory=dict)


class CmsPageUpdate(BaseModel):
    slug: Optional[str] = None
    title: Optional[str] = None
    status: Optional[str] = None
    seo_json: Optional[Dict[str, Any]] = None


class CmsPageRead(BaseModel):
    id: UUID
    site_id: UUID
    slug: str
    title: str
    status: str
    seo_json: Dict[str, Any] = Field(default_factory=dict)
    published_version_id: Optional[UUID] = None
    created_by_persona_id: Optional[UUID] = None
    updated_by_persona_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


class CmsSectionCreate(BaseModel):
    section_key: Optional[str] = None
    type: str
    props_json: Dict[str, Any] = Field(default_factory=dict)
    sort_order: int = 0
    is_visible: bool = True
    status: str = "active"
    is_global: bool = False
    global_key: Optional[str] = None


class CmsSectionUpdate(BaseModel):
    type: Optional[str] = None
    props_json: Optional[Dict[str, Any]] = None
    sort_order: Optional[int] = None
    is_visible: Optional[bool] = None
    status: Optional[str] = None
    is_global: Optional[bool] = None
    global_key: Optional[str] = None


class CmsSectionReorderItem(BaseModel):
    id: UUID
    sort_order: int


class CmsSectionReorderPayload(BaseModel):
    items: List[CmsSectionReorderItem]


class CmsSectionRead(BaseModel):
    id: UUID
    page_id: UUID
    section_key: str
    type: str
    props_json: Dict[str, Any] = Field(default_factory=dict)
    sort_order: int
    is_visible: bool
    status: str = "active"
    is_global: bool = False
    global_key: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


class CmsPageVersionRead(BaseModel):
    id: UUID
    page_id: UUID
    version_number: int
    snapshot_json: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None
    created_by_persona_id: Optional[UUID] = None
    created_at: datetime
    model_config = orm_config


class CmsPublishLogRead(BaseModel):
    id: UUID
    site_id: UUID
    page_id: Optional[UUID] = None
    entity_type: str
    entity_id: Optional[str] = None
    action: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    actor_persona_id: Optional[UUID] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    model_config = orm_config


class CmsWorkflowAction(BaseModel):
    action: str
    notes: Optional[str] = None


class CmsPublicPageRead(BaseModel):
    site_key: str
    slug: str
    title: str
    seo_json: Dict[str, Any] = Field(default_factory=dict)
    sections: List[CmsSectionRead] = Field(default_factory=list)
    json_ld: Optional[Dict[str, Any]] = None
    canonical_url: Optional[str] = None
    breadcrumbs: Optional[List[Dict[str, str]]] = None
    breadcrumb_json_ld: Optional[Dict[str, Any]] = None


# ── Announcements ───────────────────────────────────────

AnnouncementStatus = Literal["draft", "published", "archived"]
TestimonialStatus = Literal["pending", "approved", "archived"]


class AnnouncementCreate(BaseModel):
    title: str
    content: str
    category: str = "General"
    image_url: Optional[str] = None
    is_featured: bool = False
    status: AnnouncementStatus = "published"


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    is_featured: Optional[bool] = None
    status: Optional[AnnouncementStatus] = None


class AnnouncementRead(BaseModel):
    id: UUID
    title: str
    content: str
    category: str
    image_url: Optional[str] = None
    is_featured: bool
    status: AnnouncementStatus
    # Axioma 3 — Multi-Tenant: expone ``sede_id`` y ``created_by_persona_id``
    # read-only para audit. No editables vía Create/Update.
    sede_id: Optional[UUID] = None
    created_by_persona_id: Optional[UUID] = None
    published_at: datetime
    created_at: datetime
    model_config = orm_config


# ── Testimonials ────────────────────────────────────────


class TestimonialCreate(BaseModel):
    content: str
    emotion: str = "Gratitud"
    media_type: str = "text"
    media_url: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    podcast_url: Optional[str] = None
    is_approved: bool = False
    show_on_home: bool = False
    status: Optional[TestimonialStatus] = None
    author_persona_id: Optional[UUID] = None


class TestimonialUpdate(BaseModel):
    content: Optional[str] = None
    emotion: Optional[str] = None
    media_type: Optional[str] = None
    media_url: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    podcast_url: Optional[str] = None
    is_approved: Optional[bool] = None
    show_on_home: Optional[bool] = None
    status: Optional[TestimonialStatus] = None


class TestimonialAuthorRead(BaseModel):
    """Schema representation of a ``Testimonial.author`` (``Persona``).

    Nota: ``username`` es ``Optional`` porque el modelo ``Persona`` no
    expone ese atributo. La intención original era un apodo legible,
    pero como todavía no está en el modelo, retornamos ``None`` cuando
    no exista (Pydantic ``from_attributes`` rellena con ``None`` vía
    ``Optional``). Si en el futuro el modelo incluye ``username``,
    basta cambiar el default a un str derivado. Mantener
    ``id`` como obligatorio porque es la FK de la relación.
    """

    id: UUID
    username: Optional[str] = None
    model_config = orm_config


class TestimonialRead(BaseModel):
    id: UUID
    content: str
    emotion: str
    media_type: str = "text"
    media_url: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    podcast_url: Optional[str] = None
    is_approved: bool
    show_on_home: bool
    status: TestimonialStatus = "pending"
    author_persona_id: Optional[UUID] = None
    # Axioma 3 — Multi-Tenant: ``sede_id`` read-only. Backfilled desde
    # ``author.sede_id`` en la migración; si author fue None queda NULL
    # y el row sólo es visible a superadmins sin sede asignada.
    sede_id: Optional[UUID] = None
    author: Optional[TestimonialAuthorRead] = None
    created_at: datetime
    model_config = orm_config


class NewsletterSubscriptionCreate(BaseModel):
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    source: Optional[str] = "newsletter-web"
    landing_page: Optional[str] = None
    campaign: Optional[str] = None


class NewsletterSubscriptionRead(BaseModel):
    id: UUID
    email: str
    status: str
    created_at: datetime
    model_config = orm_config


# ── Pastoral Profile ───────────────────────────────────────────────────────


class PastoralProfileRead(BaseModel):
    id: UUID
    name: str
    slug: str
    photo_url: Optional[str] = None
    bio_short: Optional[str] = None
    bio_full: Optional[str] = None
    role: Optional[str] = None
    social_instagram: Optional[str] = None
    social_facebook: Optional[str] = None
    social_twitter: Optional[str] = None
    is_main_pastor: bool = False


class PastoralProfileUpdate(BaseModel):
    photo_url: Optional[str] = None
    bio_short: Optional[str] = None
    bio_full: Optional[str] = None
    social_instagram: Optional[str] = None
    social_facebook: Optional[str] = None
    social_twitter: Optional[str] = None
    is_main_pastor: Optional[bool] = None
    is_pastoral_leader: Optional[bool] = None


# ── Section Types (platform-wide catalog) ────────────────────────
#
# A CmsSectionType is the schema-of-schemas: it defines which ``type``
# strings a ``CmsSection`` is allowed to use. Catalog is global — there
# is no site FK because section types are shared across all CMS sites


class CmsSectionTypeCreate(BaseModel):
    """Payload to register a new section type in the platform catalog."""

    # ``name`` mirrors ``CmsSectionType.name`` ``String(80)`` in the DB
    # schema. The ``max_length`` constraint here prevents 500 on commit
    # when an oversized name is submitted via the API.
    name: str = Field(min_length=1, max_length=80)
    description: Optional[str] = Field(default=None, max_length=255)
    # Creating with ``is_active=False`` is intentional: a type can be
    # provisioned before the renderer ships.
    is_active: bool = True


class CmsSectionTypeUpdate(BaseModel):
    """Payload to update an existing section type entry.

    ``name`` is intentionally NOT exposed: ``CmsSection.type`` is a
    free-string column with no FK to ``cms_section_types``. A rename
    would orphan every existing section that uses the type. To rename,
    admins must DELETE (soft) and recreate.
    """

    description: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = None


class CmsSectionTypeRead(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


# ── Posts & Taxonomías ─────────────────────────────────────────────────────


class CmsCategoryCreate(BaseModel):
    slug: str
    name: str
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    is_active: bool = True


class CmsCategoryUpdate(BaseModel):
    slug: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class CmsCategoryRead(BaseModel):
    id: UUID
    site_id: UUID
    parent_id: Optional[UUID] = None
    slug: str
    name: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


class CmsTagCreate(BaseModel):
    slug: str
    name: str
    is_active: bool = True


class CmsTagUpdate(BaseModel):
    slug: Optional[str] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None


class CmsTagRead(BaseModel):
    id: UUID
    site_id: UUID
    slug: str
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


class CmsPostCreate(BaseModel):
    slug: str
    title: str
    excerpt: Optional[str] = None
    content: Optional[str] = None
    featured_image_url: Optional[str] = None
    status: str = "draft"
    seo_json: Dict[str, Any] = Field(default_factory=dict)
    category_ids: List[UUID] = Field(default_factory=list)
    tag_ids: List[UUID] = Field(default_factory=list)
    published_at: Optional[datetime] = None


class CmsPostUpdate(BaseModel):
    slug: Optional[str] = None
    title: Optional[str] = None
    excerpt: Optional[str] = None
    content: Optional[str] = None
    featured_image_url: Optional[str] = None
    status: Optional[str] = None
    seo_json: Optional[Dict[str, Any]] = None
    category_ids: Optional[List[UUID]] = None
    tag_ids: Optional[List[UUID]] = None
    published_at: Optional[datetime] = None


class CmsPostRead(BaseModel):
    id: UUID
    site_id: UUID
    slug: str
    title: str
    excerpt: Optional[str] = None
    content: Optional[str] = None
    featured_image_url: Optional[str] = None
    status: str
    seo_json: Dict[str, Any] = Field(default_factory=dict)
    locale: str
    published_at: Optional[datetime] = None
    author_persona_id: Optional[UUID] = None
    created_by_persona_id: Optional[UUID] = None
    updated_by_persona_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


class CmsPostReadWithTaxonomies(CmsPostRead):
    categories: List[CmsCategoryRead] = Field(default_factory=list)
    tags: List[CmsTagRead] = Field(default_factory=list)


class CmsPublicPostRead(BaseModel):
    site_key: str
    slug: str
    title: str
    excerpt: Optional[str] = None
    content: Optional[str] = None
    featured_image_url: Optional[str] = None
    seo_json: Dict[str, Any] = Field(default_factory=dict)
    published_at: Optional[datetime] = None
    author_name: Optional[str] = None
    categories: List[CmsCategoryRead] = Field(default_factory=list)
    tags: List[CmsTagRead] = Field(default_factory=list)
    json_ld: Optional[Dict[str, Any]] = None
    canonical_url: Optional[str] = None
