from backend.models_shared import *
from backend.models_shared import _utcnow


class NewsletterSubscription(Base):
    __tablename__ = "newsletter_subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(String(20), default="active")  # active, unsubscribed
    created_at = Column(DateTime, default=_utcnow)


class PageContent(Base):
    __tablename__ = "page_contents"
    id = Column(Integer, primary_key=True, index=True)
    page_key = Column(String(120), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class PageContentVersion(Base):
    __tablename__ = "page_content_versions"
    id = Column(Integer, primary_key=True, index=True)
    page_key = Column(String(120), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_utcnow)


class ContentPublication(Base):
    __tablename__ = "content_publications"
    id = Column(Integer, primary_key=True, index=True)
    page_key = Column(String(120), unique=True, nullable=False, index=True)
    status = Column(
        String(30), default="draft", index=True
    )  # draft, in_review, approved, published, archived
    publish_at = Column(DateTime, nullable=True)
    expire_at = Column(DateTime, nullable=True)
    last_published_at = Column(DateTime, nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class ContentMetric(Base):
    __tablename__ = "content_metrics"
    id = Column(Integer, primary_key=True, index=True)
    metric_key = Column(String(120), nullable=False, index=True)
    ref_id = Column(Integer, nullable=False, index=True)
    value = Column(Integer, default=0)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class MediaAsset(Base):
    __tablename__ = "media_assets"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    mime_type = Column(String(120), nullable=True)
    size_bytes = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow)


class CmsMediaItem(Base):
    __tablename__ = "cms_media_items"
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(500), nullable=False)
    alt_text = Column(String(255), nullable=True)
    dimensions = Column(String(50), nullable=True)
    filename = Column(String(255), nullable=True)
    mime_type = Column(String(120), nullable=True)
    file_size = Column(Integer, default=0)
    section = Column(String(120), nullable=False, index=True, default="general")
    tags = Column(JSON, default=[])
    status = Column(String(20), default="active", index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class CmsSite(Base):
    __tablename__ = "cms_sites"
    id = Column(Integer, primary_key=True, index=True)
    site_key = Column(String(80), unique=True, nullable=False, index=True)
    name = Column(String(120), nullable=False)
    base_path = Column(String(120), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class CmsTheme(Base):
    __tablename__ = "cms_themes"
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(
        Integer,
        ForeignKey("cms_sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(120), nullable=False)
    tokens_json = Column(JSON, default={})
    is_active = Column(Boolean, default=False, index=True)
    status = Column(String(20), default="active", index=True)
    version = Column(Integer, default=1)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class CmsMenu(Base):
    __tablename__ = "cms_menus"
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(
        Integer,
        ForeignKey("cms_sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    menu_key = Column(String(80), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        UniqueConstraint("site_id", "menu_key", name="uq_cms_menu_site_key"),
    )


class CmsMenuItem(Base):
    __tablename__ = "cms_menu_items"
    id = Column(Integer, primary_key=True, index=True)
    menu_id = Column(
        Integer,
        ForeignKey("cms_menus.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id = Column(
        Integer,
        ForeignKey("cms_menu_items.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    label = Column(String(120), nullable=False)
    href = Column(String(255), nullable=False)
    target = Column(String(20), default="_self")
    is_external = Column(Boolean, default=False)
    visibility = Column(String(20), default="public")
    sort_order = Column(Integer, default=0)
    meta_json = Column(JSON, default={})
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class CmsPage(Base):
    __tablename__ = "cms_pages"
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(
        Integer,
        ForeignKey("cms_sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slug = Column(String(160), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    status = Column(String(30), default="draft", index=True)
    seo_json = Column(JSON, default={})
    published_version_id = Column(
        Integer,
        ForeignKey(
            "cms_page_versions.id",
            name="fk_cms_pages_published_version",
            use_alter=True,
        ),
        nullable=True,
    )
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        UniqueConstraint("site_id", "slug", name="uq_cms_page_site_slug"),
    )


class CmsPageVersion(Base):
    __tablename__ = "cms_page_versions"
    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(
        Integer,
        ForeignKey(
            "cms_pages.id", ondelete="CASCADE", name="fk_cms_page_versions_page_id"
        ),
        nullable=False,
        index=True,
    )
    version_number = Column(Integer, nullable=False)
    snapshot_json = Column(JSON, default={})
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    __table_args__ = (
        UniqueConstraint(
            "page_id", "version_number", name="uq_cms_page_version_number"
        ),
    )


class CmsSection(Base):
    __tablename__ = "cms_sections"
    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(
        Integer,
        ForeignKey("cms_pages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_key = Column(String(120), nullable=False, index=True)
    type = Column(String(80), nullable=False, index=True)
    props_json = Column(JSON, default={})
    sort_order = Column(Integer, default=0)
    is_visible = Column(Boolean, default=True, index=True)
    status = Column(String(20), default="active", index=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class CmsPublishLog(Base):
    __tablename__ = "cms_publish_logs"
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(
        Integer,
        ForeignKey("cms_sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_id = Column(
        Integer,
        ForeignKey("cms_pages.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(Integer, nullable=True)
    action = Column(String(50), nullable=False, index=True)
    from_status = Column(String(30), nullable=True)
    to_status = Column(String(30), nullable=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    metadata_json = Column(JSON, default={})
    created_at = Column(DateTime, default=_utcnow, index=True)


class Announcement(Base):
    __tablename__ = "announcements"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), default="General")
    image_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    status = Column(String(20), default="published", index=True)
    published_at = Column(DateTime, default=_utcnow)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class Testimonial(Base):
    __tablename__ = "testimonials"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    emotion = Column(String(50), default="Gratitud")
    media_type = Column(String(30), default="text")
    media_url = Column(String(500), nullable=True)
    image_url = Column(String(500), nullable=True)
    video_url = Column(String(500), nullable=True)
    podcast_url = Column(String(500), nullable=True)
    is_approved = Column(Boolean, default=False)
    show_on_home = Column(Boolean, default=False)
    status = Column(String(20), default="pending", index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    author = relationship("User", foreign_keys=[author_id], lazy="joined")
