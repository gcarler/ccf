from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from backend.schemas._common import orm_config


class PageContentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


class PageContentRead(BaseModel):
    id: int
    page_key: str
    title: str
    content: str
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


class PageContentVersionRead(BaseModel):
    id: int
    page_key: str
    title: str
    content: str
    created_at: datetime
    model_config = orm_config


class ContentWorkflowUpdate(BaseModel):
    action: str
    notes: Optional[str] = None
    publish_at: Optional[datetime] = None
    expire_at: Optional[datetime] = None


class ContentWorkflowRead(BaseModel):
    page_key: str
    status: str
    publish_at: Optional[datetime] = None
    expire_at: Optional[datetime] = None
    last_published_at: Optional[datetime] = None
    notes: Optional[str] = None
    updated_at: datetime


class CmsMetrics(BaseModel):
    total_blocks: int
    draft_blocks: int
    in_review_blocks: int
    approved_blocks: int
    published_blocks: int
    archived_blocks: int
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
    id: int
    url: str
    alt_text: Optional[str] = None
    dimensions: Optional[str] = None
    filename: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    section: str
    tags: List[str] = Field(default_factory=list)
    status: str = "active"
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


class CmsSiteCreate(BaseModel):
    site_key: str
    name: str
    base_path: str
    is_active: bool = True


class CmsSiteUpdate(BaseModel):
    name: Optional[str] = None
    base_path: Optional[str] = None
    is_active: Optional[bool] = None


class CmsSiteRead(BaseModel):
    id: int
    site_key: str
    name: str
    base_path: str
    is_active: bool
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
    id: int
    site_id: int
    name: str
    tokens_json: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool
    status: CmsThemeStatus = "active"
    version: int
    created_by: Optional[int] = None
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
    id: int
    site_id: int
    menu_key: str
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


class CmsMenuItemCreate(BaseModel):
    label: str
    href: str
    parent_id: Optional[int] = None
    target: str = "_self"
    is_external: bool = False
    visibility: str = "public"
    sort_order: int = 0
    meta_json: Dict[str, Any] = Field(default_factory=dict)


class CmsMenuItemUpdate(BaseModel):
    label: Optional[str] = None
    href: Optional[str] = None
    parent_id: Optional[int] = None
    target: Optional[str] = None
    is_external: Optional[bool] = None
    visibility: Optional[str] = None
    sort_order: Optional[int] = None
    meta_json: Optional[Dict[str, Any]] = None


class CmsMenuItemReorderItem(BaseModel):
    id: int
    parent_id: Optional[int] = None
    sort_order: int


class CmsMenuItemReorderPayload(BaseModel):
    items: List[CmsMenuItemReorderItem]


class CmsMenuItemRead(BaseModel):
    id: int
    menu_id: int
    parent_id: Optional[int] = None
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
    id: int
    site_id: int
    slug: str
    title: str
    status: str
    seo_json: Dict[str, Any] = Field(default_factory=dict)
    published_version_id: Optional[int] = None
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
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


class CmsSectionUpdate(BaseModel):
    type: Optional[str] = None
    props_json: Optional[Dict[str, Any]] = None
    sort_order: Optional[int] = None
    is_visible: Optional[bool] = None
    status: Optional[str] = None


class CmsSectionReorderItem(BaseModel):
    id: int
    sort_order: int


class CmsSectionReorderPayload(BaseModel):
    items: List[CmsSectionReorderItem]


class CmsSectionRead(BaseModel):
    id: int
    page_id: int
    section_key: str
    type: str
    props_json: Dict[str, Any] = Field(default_factory=dict)
    sort_order: int
    is_visible: bool
    status: str = "active"
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


class CmsPageVersionRead(BaseModel):
    id: int
    page_id: int
    version_number: int
    snapshot_json: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime
    model_config = orm_config


class CmsPublishLogRead(BaseModel):
    id: int
    site_id: int
    page_id: Optional[int] = None
    entity_type: str
    entity_id: Optional[int] = None
    action: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    actor_user_id: Optional[int] = None
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
    id: int
    title: str
    content: str
    category: str
    image_url: Optional[str] = None
    is_featured: bool
    status: AnnouncementStatus
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
    author_id: Optional[int] = None


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
    id: int
    username: str
    model_config = orm_config


class TestimonialRead(BaseModel):
    id: int
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
    author_id: Optional[int] = None
    author: Optional[TestimonialAuthorRead] = None
    created_at: datetime
    model_config = orm_config


class NewsletterSubscriptionCreate(BaseModel):
    email: str


class NewsletterSubscriptionRead(BaseModel):
    id: int
    email: str
    status: str
    created_at: datetime
    model_config = orm_config
