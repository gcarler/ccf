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


class CmsSite(Base):
    __tablename__ = "cms_sites"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_key = Column(String(80), unique=True, nullable=False, index=True)
    name = Column(String(120), nullable=False)
    base_path = Column(String(120), unique=True, nullable=False, index=True, default="/")
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


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
    created_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    updated_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        UniqueConstraint("site_id", "slug", name="uq_cms_page_site_slug"),
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
    is_global = Column(Boolean, default=False, server_default="0")
    global_key = Column(String(120), nullable=True, unique=True, index=True)
    locale = Column(String(5), default="es", server_default="es", index=True)
    created_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    updated_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
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


class CmsPageView(Base):
    __tablename__ = "cms_page_views"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id = Column(UUID(as_uuid=True), ForeignKey("cms_pages.id", ondelete="CASCADE"), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    referrer = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)


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
