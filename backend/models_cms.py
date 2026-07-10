from backend.models_shared import *
from backend.models_shared import _utcnow


class CmsMediaItem(Base):
    __tablename__ = "cms_media_items"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(String(500), nullable=False)
    alt_text = Column(String(255), nullable=True)
    dimensions = Column(String(50), nullable=True)
    filename = Column(String(255), nullable=True)
    mime_type = Column(String(120), nullable=True)
    file_size = Column(Integer, default=0)
    section = Column(String(120), nullable=False, index=True, default="general")
    tags = Column(JSON, default=[])
    status = Column(String(20), default="active", index=True)
    created_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)
    # Axioma 3 — Multi-Tenant (added 2026-07-01 via alembic migration):
    # sede_id propio en cms_media_items para evitar el scope leak donde un
    # editor de sede_a podía listar/borrar imágenes de sede_b. Pre-migration
    # los media items estaban aislados de facto solo por su creator
    # (``created_by_persona_id``), pero el listado admin los agregaba a
    # nivel plataforma sin JOIN. Con sede_id propio el CRUD/API pueden
    # filtrar de forma directa y consistente.
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # ── Relationships (núcleo CMS) ──────────────────────────────────────
    created_by_persona = relationship("Persona", foreign_keys=[created_by_persona_id], lazy="joined")
    sede = relationship("Sede", foreign_keys=[sede_id], lazy="joined")


class CmsSite(Base):
    __tablename__ = "cms_sites"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_key = Column(String(80), unique=True, nullable=False, index=True)
    name = Column(String(120), nullable=False)
    base_path = Column(String(120), unique=True, nullable=False, index=True, default="/")
    is_active = Column(Boolean, default=True, index=True)
    # Axioma 3 — Multi-Tenant: cms_sites necesita sede_id para que el
    # dashboard CMS pueda filtrar métricas por sede. Todos los objetos
    # CMS v2 (pages, posts, categories, tags) tienen site_id FK; con
    # sede_id en el site, el scope por sede se resuelve vía JOIN sin
    # necesidad de agregar sede_id a cada tabla hija.
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # ── Relationships (núcleo CMS) ──────────────────────────────────────
    sede = relationship("Sede", foreign_keys=[sede_id], lazy="joined")
    themes = relationship("CmsTheme", back_populates="site", lazy="selectin")
    menus = relationship("CmsMenu", back_populates="site", lazy="selectin")
    pages = relationship("CmsPage", back_populates="site", lazy="selectin")
    categories = relationship("CmsCategory", back_populates="site", lazy="selectin")
    tags = relationship("CmsTag", back_populates="site", lazy="selectin")
    posts = relationship("CmsPost", back_populates="site", lazy="selectin")
    publish_logs = relationship("CmsPublishLog", back_populates="site", lazy="selectin")
    seo_snapshots = relationship("CmsSeoSnapshot", back_populates="site", lazy="selectin")


class CmsTheme(Base):
    __tablename__ = "cms_themes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(120), nullable=False)
    tokens_json = Column(JSON, default={})
    is_active = Column(Boolean, default=False, index=True)
    status = Column(String(20), default="active", index=True)
    version = Column(Integer, default=1)
    created_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    updated_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # ── Relationships (núcleo CMS) ──────────────────────────────────────
    site = relationship("CmsSite", back_populates="themes", lazy="joined")
    created_by_persona = relationship("Persona", foreign_keys=[created_by_persona_id], lazy="joined")
    updated_by_persona = relationship("Persona", foreign_keys=[updated_by_persona_id], lazy="joined")


class CmsMenu(Base):
    __tablename__ = "cms_menus"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    menu_key = Column(String(80), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        UniqueConstraint("site_id", "menu_key", name="uq_cms_menu_site_key"),
    )

    # ── Relationships (núcleo CMS) ──────────────────────────────────────
    site = relationship("CmsSite", back_populates="menus", lazy="joined")
    items = relationship("CmsMenuItem", back_populates="menu", lazy="selectin")


class CmsMenuItem(Base):
    __tablename__ = "cms_menu_items"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    menu_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_menus.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id = Column(
        UUID(as_uuid=True),
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
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # ── Relationships (núcleo CMS) ──────────────────────────────────────
    menu = relationship("CmsMenu", back_populates="items", lazy="joined")
    parent = relationship(
        "CmsMenuItem",
        remote_side=[id],
        back_populates="children",
        lazy="joined",
    )
    children = relationship(
        "CmsMenuItem",
        back_populates="parent",
        lazy="selectin",
    )


class CmsPage(Base):
    __tablename__ = "cms_pages"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slug = Column(String(160), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    status = Column(String(30), default="draft", index=True)
    seo_json = Column(JSON, default={})
    published_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "cms_page_versions.id",
            name="fk_cms_pages_published_version",
            use_alter=True,
        ),
        nullable=True,
    )
    locale = Column(String(5), default="es", server_default="es", index=True)
    # Scheduled publish + auto-archive (added 2026-07-06 via alembic migration):
    # ``publish_at`` es el momento futuro en que el scheduler automático
    # transiciona ``draft|in_review|approved|scheduled`` → ``published``.
    # ``expires_at`` es el momento en que un ``published`` debe auto-
    # archivar. Ambas columnas nullable — el control es 100% lógico y
    # compatible con el workflow API existente.
    publish_at = Column(DateTime(timezone=True), nullable=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    updated_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        UniqueConstraint("site_id", "slug", name="uq_cms_page_site_slug"),
    )

    # ── Relationships (núcleo CMS) ──────────────────────────────────────
    site = relationship("CmsSite", back_populates="pages", lazy="joined")
    sections = relationship("CmsSection", back_populates="page", lazy="selectin")
    versions = relationship("CmsPageVersion", back_populates="page", lazy="selectin", foreign_keys="CmsPageVersion.page_id")
    views = relationship("CmsPageView", back_populates="page", lazy="selectin")
    publish_logs = relationship("CmsPublishLog", back_populates="page", lazy="selectin")
    created_by_persona = relationship("Persona", foreign_keys=[created_by_persona_id], lazy="joined")
    updated_by_persona = relationship("Persona", foreign_keys=[updated_by_persona_id], lazy="joined")
    published_version = relationship(
        "CmsPageVersion",
        foreign_keys=[published_version_id],
        lazy="joined",
    )


class CmsPageVersion(Base):
    __tablename__ = "cms_page_versions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "cms_pages.id", ondelete="CASCADE", name="fk_cms_page_versions_page_id"
        ),
        nullable=False,
        index=True,
    )
    version_number = Column(Integer, nullable=False)
    snapshot_json = Column(JSON, default={})
    notes = Column(Text, nullable=True)
    created_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        UniqueConstraint(
            "page_id", "version_number", name="uq_cms_page_version_number"
        ),
    )

    # ── Relationships (núcleo CMS) ──────────────────────────────────────
    page = relationship(
        "CmsPage",
        back_populates="versions",
        foreign_keys=[page_id],
        lazy="joined",
    )
    created_by_persona = relationship("Persona", foreign_keys=[created_by_persona_id], lazy="joined")


class CmsSection(Base):
    __tablename__ = "cms_sections"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id = Column(
        UUID(as_uuid=True),
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
    is_global = Column(Boolean, default=False, server_default="0", index=True)
    global_key = Column(String(120), nullable=True, unique=True, index=True)
    locale = Column(String(5), default="es", server_default="es", index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    updated_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # ── Relationships (núcleo CMS) ──────────────────────────────────────
    page = relationship("CmsPage", back_populates="sections", lazy="joined")
    created_by_persona = relationship("Persona", foreign_keys=[created_by_persona_id], lazy="joined")
    updated_by_persona = relationship("Persona", foreign_keys=[updated_by_persona_id], lazy="joined")


class CmsSectionType(Base):
    __tablename__ = "cms_section_types"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(80), nullable=False, unique=True, index=True)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class CmsPublishLog(Base):
    __tablename__ = "cms_publish_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_pages.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(String(120), nullable=True)
    action = Column(String(50), nullable=False, index=True)
    from_status = Column(String(30), nullable=True)
    to_status = Column(String(30), nullable=True)
    actor_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    metadata_json = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)

    # ── Relationships (núcleo CMS) ──────────────────────────────────────
    site = relationship("CmsSite", back_populates="publish_logs", lazy="joined")
    page = relationship("CmsPage", back_populates="publish_logs", lazy="joined")
    actor_persona = relationship("Persona", foreign_keys=[actor_persona_id], lazy="joined")


class CmsPageView(Base):
    __tablename__ = "cms_page_views"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id = Column(UUID(as_uuid=True), ForeignKey("cms_pages.id", ondelete="CASCADE"), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    referrer = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)

    # ── Relationships (núcleo CMS) ──────────────────────────────────────
    page = relationship("CmsPage", back_populates="views", lazy="joined")


class SavedView(Base):
    """Saved table views with schema, filters, grouping, and conditional format."""
    __tablename__ = "saved_views"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    schema_json = Column(JSON, default={})
    filters_json = Column(JSON, default=[])
    grouping_json = Column(JSON, default=[])
    conditional_format_json = Column(JSON, default=[])
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # ── Relationships (núcleo CMS) ──────────────────────────────────────
    persona = relationship("Persona", foreign_keys=[persona_id], lazy="joined")


class Announcement(Base):
    __tablename__ = "announcements"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), default="General")
    image_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    status = Column(String(20), default="published", index=True)
    # Axioma 3 — Multi-Tenant (added 2026-07-01 via alembic migration):
    # ``Announcement`` no tenía FK a persona ni filtro de sede. Un editor de
    # sede_a podía crear/editar anuncios que aparecían en la home pública
    # de sede_b. ``sede_id`` propio + ``created_by_persona_id`` permiten
    # scope tanto en API como en CRUD layer (defense-in-depth).
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=False, index=True)
    created_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)
    published_at = Column(DateTime(timezone=True), default=_utcnow)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # ── Relationships (núcleo CMS) ──────────────────────────────────────
    created_by_persona = relationship("Persona", foreign_keys=[created_by_persona_id], lazy="joined")
    sede = relationship("Sede", foreign_keys=[sede_id], lazy="joined")


class Testimonial(Base):
    __tablename__ = "testimonials"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    author_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)
    # Axioma 3 — Multi-Tenant (added 2026-07-01 via alembic migration):
    # ``Testimonial`` solo tenía FK a ``author_persona_id``. Sin sede_id
    # propio, scope del CRUD/API requería JOIN con ``personas.sede_id``.
    # Columna directa acelera queries y permite backfill estable desde
    # author.sede_id. El contrato estricto exige autor y sede para impedir
    # contenido sin ownership o aislamiento tenant verificable.
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    author = relationship("Persona", foreign_keys=[author_persona_id], lazy="joined")
    sede = relationship("Sede", foreign_keys=[sede_id], lazy="joined")


# ── Posts & Taxonomías (Blog/Noticias) ─────────────────────────────────────

class CmsCategory(Base):
    __tablename__ = "cms_categories"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_categories.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    slug = Column(String(160), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        UniqueConstraint("site_id", "slug", name="uq_cms_category_site_slug"),
    )

    # ── Relationships (núcleo CMS) ──────────────────────────────────────
    site = relationship("CmsSite", back_populates="categories", lazy="joined")
    parent = relationship(
        "CmsCategory",
        remote_side=[id],
        back_populates="children",
        lazy="joined",
    )
    children = relationship(
        "CmsCategory",
        back_populates="parent",
        lazy="selectin",
    )
    posts = relationship(
        "CmsPost",
        secondary="cms_post_categories",
        back_populates="categories",
        lazy="selectin",
    )


class CmsTag(Base):
    __tablename__ = "cms_tags"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slug = Column(String(160), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        UniqueConstraint("site_id", "slug", name="uq_cms_tag_site_slug"),
    )

    # ── Relationships (núcleo CMS) ──────────────────────────────────────
    site = relationship("CmsSite", back_populates="tags", lazy="joined")
    posts = relationship(
        "CmsPost",
        secondary="cms_post_tags",
        back_populates="tags",
        lazy="selectin",
    )


class CmsPost(Base):
    __tablename__ = "cms_posts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slug = Column(String(160), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    excerpt = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    featured_image_url = Column(String(500), nullable=True)
    status = Column(String(30), default="draft", index=True)
    seo_json = Column(JSON, default={})
    locale = Column(String(5), default="es", server_default="es", index=True)
    published_at = Column(DateTime(timezone=True), nullable=True, index=True)
    # Auto-archive (added 2026-07-06 via alembic migration): ``expires_at``
    # indica el momento en que un ``published`` debe auto-archivarse.
    # ``publish_at`` ya existe como ``published_at`` (semánticamente
    # equivalente; alineamos nomenclatura en próximos refactors).
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    author_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    created_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    updated_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        UniqueConstraint("site_id", "slug", name="uq_cms_post_site_slug"),
    )

    # ── Relationships (núcleo CMS) ──────────────────────────────────────
    site = relationship("CmsSite", back_populates="posts", lazy="joined")
    author_persona = relationship("Persona", foreign_keys=[author_persona_id], lazy="joined")
    created_by_persona = relationship("Persona", foreign_keys=[created_by_persona_id], lazy="joined")
    updated_by_persona = relationship("Persona", foreign_keys=[updated_by_persona_id], lazy="joined")
    categories = relationship(
        "CmsCategory",
        secondary="cms_post_categories",
        back_populates="posts",
        lazy="selectin",
    )
    tags = relationship(
        "CmsTag",
        secondary="cms_post_tags",
        back_populates="posts",
        lazy="selectin",
    )


class CmsPostCategory(Base):
    __tablename__ = "cms_post_categories"
    post_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_posts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_categories.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # ── Relationships (núcleo CMS) ──────────────────────────────────────
    post = relationship("CmsPost", lazy="joined")
    category = relationship("CmsCategory", lazy="joined")


class CmsPostTag(Base):
    __tablename__ = "cms_post_tags"
    post_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_posts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_tags.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # ── Relationships (núcleo CMS) ──────────────────────────────────────
    post = relationship("CmsPost", lazy="joined")
    tag = relationship("CmsTag", lazy="joined")


class CmsSeoSnapshot(Base):
    """Daily SEO score snapshot per ``CmsSite`` (faro global model).

    Captured by ``backend.scheduler`` (cron) to power the "SEO score trend"
    widget on ``/plataforma/dashboard/cms``. Today the audit is computed
    on-the-fly by ``GET /api/cms/v2/sites/{site_key}/seo-audit`` — that
    means there is no historical data unless we record daily snapshots
    ourselves. This table is the source of truth for *historical* widget
    data.

    Notes:
      * ``UNIQUE(site_id, captured_date)`` guarantees idempotency: even
        if the cron retries twice in the same day, ``INSERT ... ON
        CONFLICT DO NOTHING`` keeps exactly one row per site/per day.
      * ``sede_id`` mirrors ``cms_sites.sede_id`` at capture time so the
        widget can be filtered Axioma 3-style without re-joining.
      * ``by_severity_json`` snapshots the per-severity counts so we
        don't have to recompute the distribution on every chart render.
      * ``captured_at`` (tz-aware ``DateTime``) is the wall-clock time
        when the snapshot was recorded; ``captured_date`` is the calendar
        day (UTC) used as the dedupe key.
    """

    __tablename__ = "cms_seo_snapshots"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sede_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sedes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    captured_date = Column(Date, nullable=False, index=True)
    captured_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: dt.datetime.now(dt.timezone.utc)
    )
    average_score = Column(Integer, nullable=False, default=0)
    total_pages = Column(Integer, nullable=False, default=0)
    pages_with_errors = Column(Integer, nullable=False, default=0)
    critical_issues = Column(Integer, nullable=False, default=0)
    by_severity_json = Column(JSON, default=dict)

    __table_args__ = (
        UniqueConstraint("site_id", "captured_date", name="uq_cms_seo_snapshot_site_date"),
    )

    # ── Relationships (núcleo CMS) ──────────────────────────────────────
    site = relationship("CmsSite", back_populates="seo_snapshots", lazy="joined")
    sede = relationship("Sede", foreign_keys=[sede_id], lazy="joined")
