"""
Enterprise CMS Models — Audit Trail, Content Permissions, Notifications,
Webhooks, Custom Post Types, Search, Session Management.

All models follow CCF conventions:
- UUID primary keys for entities
- soft deletes via deleted_at or status
- DateTime(timezone=True) for all timestamps
- ForeignKey to personas.id for user references
"""
from backend.models_shared import *
from backend.models_shared import _utcnow

# ─── 1. AUDIT TRAIL ─────────────────────────────────────────────────────────

class AuditLog(Base):
    """Immutable audit trail. Every action on CMS content is logged here."""
    __tablename__ = "cms_audit_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True, index=True)
    actor_email = Column(String(255), nullable=True)
    actor_role = Column(String(80), nullable=True)
    action = Column(String(80), nullable=False, index=True)
    # e.g. page.create, page.update, section.delete, menu.reorder, theme.activate
    entity_type = Column(String(60), nullable=False, index=True)
    # e.g. cms_page, cms_section, cms_menu, cms_theme, media_asset
    entity_id = Column(String(120), nullable=True, index=True)
    entity_slug = Column(String(200), nullable=True)
    site_key = Column(String(80), nullable=True, index=True)
    changes_json = Column(JSON, nullable=True)
    # {"field": "title", "old": "Old Title", "new": "New Title"}
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    severity = Column(String(20), default="info", index=True)
    # info, warning, critical
    session_id = Column(String(120), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)


# ─── 2. CONTENT PERMISSIONS ─────────────────────────────────────────────────

class ContentPermission(Base):
    """Per-page or per-category access control. Overrides global RBAC."""
    __tablename__ = "cms_content_permissions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_key = Column(String(80), nullable=False, index=True)
    entity_type = Column(String(60), nullable=False, index=True)
    entity_id = Column(String(120), nullable=False, index=True)
    permission_type = Column(String(30), nullable=False)
    grant_type = Column(String(30), nullable=False, index=True)
    grant_target = Column(String(120), nullable=False)
    is_denied = Column(Boolean, default=False)
    created_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)


# ─── 3. NOTIFICATIONS ───────────────────────────────────────────────────────

class CmsNotification(Base):
    """In-app notifications for CMS events."""
    __tablename__ = "cms_notifications"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipient_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, index=True)
    actor_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    notification_type = Column(String(60), nullable=False, index=True)
    # mention, approval_requested, approval_granted, approval_rejected,
    # page_published, page_archived, comment_added, workflow_changed
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=True)
    entity_type = Column(String(60), nullable=True)
    entity_id = Column(String(120), nullable=True)
    entity_slug = Column(String(200), nullable=True)
    site_key = Column(String(80), nullable=True)
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    action_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)


# ─── 4. WEBHOOKS ────────────────────────────────────────────────────────────

class Webhook(Base):
    """Outbound webhook registrations for CMS events."""
    __tablename__ = "cms_webhooks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_key = Column(String(80), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    url = Column(String(500), nullable=False)
    secret = Column(String(255), nullable=True)
    events = Column(JSON, default=list)
    is_active = Column(Boolean, default=True, index=True)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    last_status_code = Column(Integer, nullable=True)
    failure_count = Column(Integer, default=0)
    created_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)


class WebhookDelivery(Base):
    """Delivery log for each webhook trigger."""
    __tablename__ = "cms_webhook_deliveries"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    webhook_id = Column(UUID(as_uuid=True), ForeignKey("cms_webhooks.id"), nullable=False, index=True)
    event = Column(String(80), nullable=False, index=True)
    payload_json = Column(JSON, nullable=True)
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    success = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)


# ─── 5. CUSTOM POST TYPES ──────────────────────────────────────────────────

class CmsCustomType(Base):
    """Registration of custom content types (policies, wiki, glossary, etc.)"""
    __tablename__ = "cms_custom_types"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_key = Column(String(80), nullable=False, index=True)
    type_key = Column(String(80), nullable=False, index=True)
    # policy, wiki_article, glossary_term, news, asset
    label = Column(String(120), nullable=False)
    label_plural = Column(String(120), nullable=True)
    icon = Column(String(60), nullable=True)
    supports = Column(JSON, default=list)
    # ["title", "editor", "excerpt", "thumbnail", "categories", "tags", "revisions"]
    fields_schema = Column(JSON, default=dict)
    # Custom fields: {"review_date": "date", "owner": "persona", "status": "select", ...}
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class CmsCustomEntry(Base):
    """Individual entries of custom post types."""
    __tablename__ = "cms_custom_entries"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_key = Column(String(80), nullable=False, index=True)
    type_key = Column(String(80), nullable=False, index=True)
    slug = Column(String(200), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    content_html = Column(Text, nullable=True)
    excerpt = Column(Text, nullable=True)
    fields_json = Column(JSON, default=dict)
    # Custom field values
    status = Column(String(30), default="draft", index=True)
    # draft, in_review, approved, published, archived, obsolete
    featured_image_url = Column(String(500), nullable=True)
    author_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    owner_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    # For policies: who owns this document
    review_date = Column(DateTime(timezone=True), nullable=True)
    # For policies: when must this be reviewed
    expiry_date = Column(DateTime(timezone=True), nullable=True)
    # For news: auto-archive after this date
    parent_id = Column(UUID(as_uuid=True), ForeignKey("cms_custom_entries.id"), nullable=True, index=True)
    # For wiki: hierarchical nesting
    sort_order = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    locale = Column(String(10), nullable=True, index=True)
    seo_json = Column(JSON, default=dict)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)


class CmsCustomEntryVersion(Base):
    """Version history for custom entries."""
    __tablename__ = "cms_custom_entry_versions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_id = Column(UUID(as_uuid=True), ForeignKey("cms_custom_entries.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    snapshot_json = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    created_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


# ─── 6. GLOSSARY ───────────────────────────────────────────────────────────

class CmsGlossaryTerm(Base):
    """Centralized corporate glossary with tooltips."""
    __tablename__ = "cms_glossary_terms"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_key = Column(String(80), nullable=False, index=True)
    term = Column(String(200), nullable=False, index=True)
    definition = Column(Text, nullable=False)
    aliases = Column(JSON, default=list)
    # ["SG", "Sistema de Gestión"]
    category = Column(String(100), nullable=True, index=True)
    language = Column(String(10), default="es", index=True)
    is_published = Column(Boolean, default=True, index=True)
    created_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


# ─── 7. SEARCH ──────────────────────────────────────────────────────────────

class SearchIndex(Base):
    """Full-text search index for CMS content."""
    __tablename__ = "cms_search_index"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_key = Column(String(80), nullable=False, index=True)
    entity_type = Column(String(60), nullable=False, index=True)
    entity_id = Column(String(120), nullable=False, index=True)
    entity_slug = Column(String(200), nullable=True)
    title = Column(String(300), nullable=True)
    body_text = Column(Text, nullable=True)
    # Extracted plain text for full-text search
    tags = Column(JSON, default=list)
    author_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    category = Column(String(100), nullable=True, index=True)
    locale = Column(String(10), nullable=True)
    is_published = Column(Boolean, default=True, index=True)
    ts_vector = Column(Text, nullable=True)
    # PostgreSQL tsvector stored as text for GIN index
    boost_score = Column(Integer, default=0)
    # Admin-promoted results get higher boost
    last_indexed_at = Column(DateTime(timezone=True), default=_utcnow)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class SearchPromotion(Base):
    """Admin-promoted search results for specific queries."""
    __tablename__ = "cms_search_promotions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_key = Column(String(80), nullable=False, index=True)
    query_text = Column(String(200), nullable=False, index=True)
    entity_type = Column(String(60), nullable=False)
    entity_id = Column(String(120), nullable=False)
    entity_slug = Column(String(200), nullable=True)
    title = Column(String(300), nullable=True)
    boost_score = Column(Integer, default=100)
    is_active = Column(Boolean, default=True, index=True)
    created_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


# ─── 8. SESSION MANAGEMENT ─────────────────────────────────────────────────

class UserSession(Base):
    """Track active user sessions for security management."""
    __tablename__ = "cms_user_sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, index=True)
    session_token = Column(String(255), nullable=False, index=True)
    device_info = Column(String(500), nullable=True)
    # User-Agent string
    ip_address = Column(String(45), nullable=True)
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)
    is_mobile = Column(Boolean, default=False)
    last_activity_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    revoked_at = Column(DateTime(timezone=True), nullable=True)


# ─── 9. MEDIA FOLDERS ──────────────────────────────────────────────────────

class MediaFolder(Base):
    """Real folder hierarchy for media organization."""
    __tablename__ = "cms_media_folders"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_key = Column(String(80), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), nullable=False, index=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("cms_media_folders.id"), nullable=True, index=True)
    path = Column(String(500), nullable=False)
    # Full path: /brand/logos/
    sort_order = Column(Integer, default=0)
    created_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


# ─── 10. FILE VERSIONS ─────────────────────────────────────────────────────

class MediaFileVersion(Base):
    """Version history for uploaded files (PDFs, docs, etc.)."""
    __tablename__ = "cms_media_file_versions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_item_id = Column(UUID(as_uuid=True), ForeignKey("cms_media_items.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    url = Column(String(500), nullable=False)
    file_size = Column(Integer, default=0)
    checksum = Column(String(64), nullable=True)
    # SHA-256
    notes = Column(Text, nullable=True)
    created_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


# ─── 11. REDIRECTS ─────────────────────────────────────────────────────────

class CmsRedirect(Base):
    """URL redirects for maintaining coherence during restructuring.

    F-04 (errorescms.md): soporta 3 match_types:
      - ``exact`` (default): match literal de from_path con el path pedido
      - ``wildcard``: ``*`` o ``?`` estilo glob, via fnmatch
      - ``regex``: Python ``re.search`` contra el path pedido

    ``resolve_redirect``Crud helper aplica prioridad exact > wildcard > regex
    y dentro de cada tipo por ``priority DESC`` (más alto = más prioritario).
    En caso de empate dentro del mismo tipo, recorre por longitud descending
    de ``from_path`` (más específico primero).
    """
    __tablename__ = "cms_redirects"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_key = Column(String(80), nullable=False, index=True)
    from_path = Column(String(500), nullable=False, index=True)
    to_path = Column(String(500), nullable=False)
    status_code = Column(Integer, default=301)
    # 301 permanent, 302 temporary
    is_active = Column(Boolean, default=True, index=True)
    # F-04: tipo de matching + prioridad dentro del tipo
    match_type = Column(String(20), nullable=False, default="exact", index=True)
    priority = Column(Integer, nullable=False, default=0)
    hit_count = Column(Integer, default=0)
    created_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


# ─── 12. BROKEN LINK CHECK ────────────────────────────────────────────────

class BrokenLinkCheck(Base):
    """Results of periodic broken link scans."""
    __tablename__ = "cms_broken_link_checks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_key = Column(String(80), nullable=False, index=True)
    source_url = Column(String(500), nullable=False)
    source_entity_type = Column(String(60), nullable=True)
    source_entity_id = Column(String(120), nullable=True)
    target_url = Column(String(500), nullable=False)
    status_code = Column(Integer, nullable=True)
    error_message = Column(String(500), nullable=True)
    is_broken = Column(Boolean, default=True, index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    checked_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
