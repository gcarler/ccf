from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from backend.schemas._common import AwareDateTime, PaginatedResponse, orm_config


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
    width: Optional[int] = Field(default=None, ge=1)
    height: Optional[int] = Field(default=None, ge=1)
    dimensions: Optional[str] = None
    status: str = "active"


class CmsMediaUpdate(BaseModel):
    url: Optional[str] = None
    alt_text: Optional[str] = None
    section: Optional[str] = None
    tags: Optional[List[str]] = None
    filename: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    width: Optional[int] = Field(default=None, ge=1)
    height: Optional[int] = Field(default=None, ge=1)
    dimensions: Optional[str] = None
    status: Optional[str] = None


class CmsMediaRead(BaseModel):
    id: UUID
    url: str
    alt_text: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
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
    # M-01 (errorescms.md): el modelo site_key es String(80) NOT NULL; sin
    # validacion Pydantic un site_key > 80 chars o vacio llegaba al motor DB
    # y responseaba 500 (IntegrityError) en vez de 422.  No aplicamos
    # regex restrictivo aquí porque el servidor hace lower+strip en el
    # CRUD; los tests coverage-verifican el happy-path.  El único contrato
    # duro es no-dejar-llegar-al-motor-length-overflow.
    site_key: str = Field(min_length=1, max_length=80)
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
    # M-02 (errorescms.md): el modelo slug es String(160) NOT NULL. Sin
    # validacion Pydantic un slug > 160 chars llegaba al INSERT en DB y
    # responseaba 500 en lugar de 422.  No aplicamos regex restrictivo
    # aquí porque el servidor normaliza via _slugify (NFKD + acentos
    # + whitespace → hyphens); un regexestricto romperia entradas con
    # acentos que _slugify ya maneja.  El único contrato duro es
    # no-dejar-llegar-al-motor-length-overflow.
    slug: str = Field(min_length=1, max_length=160)
    title: str
    status: str = "draft"
    seo_json: Dict[str, Any] = Field(default_factory=dict)
    # Scheduled publish + auto-archive (2026-07-06): una página puede
    # crearse directamente con ``publish_at`` o ``expires_at`` futuros,
    # que el scheduler externo (cron cada minuto) materializa.
    publish_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class CmsPageUpdate(BaseModel):
    slug: Optional[str] = Field(default=None, min_length=1, max_length=160)
    title: Optional[str] = None
    status: Optional[str] = None
    seo_json: Optional[Dict[str, Any]] = None
    # Scheduled publish + auto-archive (2026-07-06): desde update también
    # se pueden programar/reprogramar fechas futuras. ``status`` sigue
    # siendo manejado por el workflow endpoint (consistente).
    publish_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class CmsPageClone(BaseModel):
    """Body for POST /cms/v2/sites/{site_key}/pages/{slug}/clone (F-02).

    Clona una página existente con todas sus secciones.  La página clonada
    siempre arranca como ``draft`` (sin ``published_version_id``, sin
    ``publish_at``/``expires_at`` schedule) para que el editor la revise y
    publique manualmente via el workflow endpoint.
    """

    new_slug: str = Field(min_length=1, max_length=160)
    new_title: Optional[str] = None


class CmsPageRead(BaseModel):
    id: UUID
    site_id: UUID
    slug: str
    title: str
    status: str
    seo_json: Dict[str, Any] = Field(default_factory=dict)
    published_version_id: Optional[UUID] = None
    # Scheduled publish + auto-archive read-only fields (2026-07-06).
    publish_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
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


class SchedulePagePublish(BaseModel):
    scheduled_at: datetime


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
    pastoral_sort_order: int = 0
    is_pastoral_published: bool = True


class PastoralProfileUpdate(BaseModel):
    photo_url: Optional[str] = None
    bio_short: Optional[str] = None
    bio_full: Optional[str] = None
    social_instagram: Optional[str] = None
    social_facebook: Optional[str] = None
    social_twitter: Optional[str] = None
    is_main_pastor: Optional[bool] = None
    is_pastoral_leader: Optional[bool] = None
    pastoral_sort_order: Optional[int] = None
    is_pastoral_published: Optional[bool] = None


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
    # H-07 (errorescms.md): el modelo ``CmsPost`` tiene ``locale`` con
    # server_default="es" (models_cms.py) y ``CmsPage`` ya lo expone, pero
    # ``CmsPostCreate`` y ``CmsPostUpdate`` no lo incluian — sin este
    # campo un post siempre se crea con locale="es" sin API para
    # cambiarlo.  Exponerlo alinea el contrato con el modelo.
    locale: Optional[str] = None
    seo_json: Dict[str, Any] = Field(default_factory=dict)
    category_ids: List[UUID] = Field(default_factory=list)
    tag_ids: List[UUID] = Field(default_factory=list)
    published_at: Optional[datetime] = None
    # Auto-archive (2026-07-06): al expirar el post se auto-archiva.
    expires_at: Optional[datetime] = None


class CmsPostUpdate(BaseModel):
    slug: Optional[str] = None
    title: Optional[str] = None
    excerpt: Optional[str] = None
    content: Optional[str] = None
    featured_image_url: Optional[str] = None
    status: Optional[str] = None
    locale: Optional[str] = None  # ver H-07 arriba
    seo_json: Optional[Dict[str, Any]] = None
    category_ids: Optional[List[UUID]] = None
    tag_ids: Optional[List[UUID]] = None
    published_at: Optional[datetime] = None
    # Auto-archive (2026-07-06): reprogramable.
    expires_at: Optional[datetime] = None


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
    # Auto-archive (2026-07-06): read-only.
    expires_at: Optional[datetime] = None
    author_persona_id: Optional[UUID] = None
    created_by_persona_id: Optional[UUID] = None
    updated_by_persona_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


class CmsPostReadWithTaxonomies(CmsPostRead):
    categories: List[CmsCategoryRead] = Field(default_factory=list)
    tags: List[CmsTagRead] = Field(default_factory=list)


class CmsPostCreateWithCategory(CmsPostCreate):
    """Create payload for posts that must belong to a canonical category."""

    category_slug: Literal["testimonials", "announcements"]


class CmsPublicPostRead(BaseModel):
    site_key: Optional[str] = None
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
    # NOTE (MEMORY §79 + Fase 3.1 fix 2026-07-28): ``from_attributes=True``
    # permite ``model_validate(post)`` desde el ORM ``CmsPost``. Los campos
    # ``site_key``, ``author_name``, ``canonical_url`` no existen en el ORM
    # — los endpoints publicos los rellenan manualmente despues de
    # ``model_validate`` (patron consistente dentro del schema CmsPublicPostRead).
    # ``seo_json`` en el ORM es JSON default={}; Pydantic lo accepta porque
    # ``from_attributes`` lee el valor via getattr, no via __init__.
    model_config = orm_config


# ── SEO Audit (faro CMS — global, sin scope por sede) ───────────────────────────
# CmsSite y CmsPage son globales por dise\u00f1o (Axioma 3: el faro CMS es
# cross-sede para preservar coherencia visual). Los modelos a continuaci\u00f3n
# describen el resultado del endpoint
# GET /api/cms/v2/sites/{site_key}/seo-audit. El endpoint ejecuta 3 queries
# (pages \u2192 sections \u2192 media items referenciados) y agrega hallazgos in-memory.

SeoFindingSeverity = Literal["info", "warning", "error"]


class SeoFinding(BaseModel):
    """Hallazgo unitario del audit SEO de una p\u00e1gina.

    ``code`` es la llave estable que el frontend usa para localizar el issue
    en pantalla; ``field_ref`` y ``section_id`` son deep-links opcionales que
    el panel UI traduce a acciones ``Ir al builder`` / ``Ir a la p\u00e1gina``.
    """

    code: str
    severity: SeoFindingSeverity
    message: str
    impact_points: int = Field(
        ge=0,
        description="Puntos que se restan al score del p\u00e1gina (0-100).",
    )
    hint: str = Field(description="Acci\u00f3n sugerida que el editor puede ejecutar.")
    field_ref: Optional[str] = Field(
        default=None,
        description="Ruta l\u00f3gica al campo afectado (ej: seo_json.meta_description ).",
    )
    section_id: Optional[UUID] = Field(
        default=None,
        description="Si el hallazgo apunta a una secci\u00f3n, el UUID para",
    )


class PageSeoAudit(BaseModel):
    """Audit consolidado de una p\u00e1gina individual."""

    page_id: UUID
    slug: str
    title: str
    status: str
    score: int = Field(ge=0, le=100)
    findings: List[SeoFinding] = Field(default_factory=list)


class SiteSeoStats(BaseModel):
    """Aggregate a nivel de site para alimentar el dashboard del editor."""

    average_score: int = Field(ge=0, le=100)
    total_pages: int = Field(ge=0)
    pages_with_errors: int = Field(ge=0)
    critical_issues: int = Field(ge=0)
    by_severity: Dict[str, int] = Field(default_factory=dict)


class SeoAuditResponse(BaseModel):
    site_key: str
    aggregate: SiteSeoStats
    pages: List[PageSeoAudit] = Field(default_factory=list)


# ── CMS Readiness / Production Health ────────────────────────────────────────

CmsReadinessSeverity = Literal["info", "warning", "error"]
CmsReadinessCapabilityStatus = Literal["ready", "partial", "attention"]


class CmsReadinessMetric(BaseModel):
    key: str
    label: str
    value: int
    href: Optional[str] = None


class CmsReadinessIssue(BaseModel):
    code: str
    severity: CmsReadinessSeverity
    title: str
    detail: str
    count: int = Field(ge=0)
    href: Optional[str] = None


class CmsReadinessCapability(BaseModel):
    key: str
    label: str
    status: CmsReadinessCapabilityStatus
    detail: str
    href: Optional[str] = None


class CmsReadinessResponse(BaseModel):
    site_key: str
    score: int = Field(ge=0, le=100)
    generated_at: datetime
    metrics: List[CmsReadinessMetric] = Field(default_factory=list)
    issues: List[CmsReadinessIssue] = Field(default_factory=list)
    capabilities: List[CmsReadinessCapability] = Field(default_factory=list)


# ── F-07 (errorescms.md): historico de snapshots SEO por site ────────
# El CRUD ``capture_daily_seo_snapshots`` ya persiste ``CmsSeoSnapshot``
# filas por dia; antes solo existia un aggregator ``get_seo_trend`` que
# agrupaba series en un dict (no un listado paginado de rows crudos).
# Este schema expone el row ORM con todos los campos por site para que el
# frontend pueda renderizar tablas de historico y comparar dias.


class CmsSeoSnapshotRead(BaseModel):
    id: UUID
    site_id: UUID
    sede_id: Optional[UUID] = None
    captured_date: datetime  # Date field, serialized as ISO date
    captured_at: datetime
    average_score: int
    total_pages: int
    pages_with_errors: int
    critical_issues: int
    by_severity_json: Dict[str, Any] = Field(default_factory=dict)

    model_config = orm_config


# ── Native Popups (R3-BE) ───────────────────────────────────────────────────

TriggerType = Literal["time_delay", "scroll_percent", "exit_intent", "on_load"]


class CmsPopupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    content_html: str = Field(..., description="HTML content for the popup")
    trigger_type: TriggerType = Field(default="on_load")
    trigger_value: Optional[int] = Field(default=None, ge=0)
    is_active: bool = Field(default=True)
    show_on_pages: List[str] = Field(default_factory=list)


class CmsPopupUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    content_html: Optional[str] = None
    trigger_type: Optional[TriggerType] = None
    trigger_value: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None
    show_on_pages: Optional[List[str]] = None


class CmsPopupRead(BaseModel):
    id: UUID
    site_id: UUID
    name: str
    content_html: str
    trigger_type: str
    trigger_value: Optional[int] = None
    is_active: bool
    show_on_pages: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = orm_config


# ── Contact Forms (R1-BE) ───────────────────────────────────────────────────


class CmsFormCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=500)
    fields: List[Dict[str, Any]] = Field(default_factory=list)
    submit_button_text: str = Field(default="Enviar", max_length=100)
    success_message: str = Field(default="¡Gracias por tu mensaje!", max_length=255)
    notify_emails: List[str] = Field(default_factory=list)
    is_active: bool = Field(default=True)
    # plan_de_form_builder
    settings_json: Dict[str, Any] = Field(default_factory=dict)
    captcha_enabled: bool = False
    captcha_provider: str = Field(default="hcaptcha", max_length=20)
    honeypot_enabled: bool = True


class CmsFormUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=500)
    fields: Optional[List[Dict[str, Any]]] = None
    submit_button_text: Optional[str] = Field(default=None, max_length=100)
    success_message: Optional[str] = Field(default=None, max_length=255)
    notify_emails: Optional[List[str]] = None
    is_active: Optional[bool] = None
    # plan_de_form_builder
    settings_json: Optional[Dict[str, Any]] = None
    captcha_enabled: Optional[bool] = None
    captcha_provider: Optional[str] = Field(default=None, max_length=20)
    honeypot_enabled: Optional[bool] = None


class CmsFormRead(BaseModel):
    id: UUID
    site_id: UUID
    name: str
    description: Optional[str] = None
    fields: List[Dict[str, Any]] = Field(default_factory=list)
    submit_button_text: str = "Enviar"
    success_message: str = "¡Gracias por tu mensaje!"
    notify_emails: List[str] = Field(default_factory=list)
    is_active: bool = True
    # plan_de_form_builder
    settings_json: Dict[str, Any] = Field(default_factory=dict)
    captcha_enabled: bool = False
    captcha_provider: str = "hcaptcha"
    honeypot_enabled: bool = True
    created_at: datetime
    updated_at: datetime
    submission_count: Optional[int] = None

    model_config = orm_config


class CmsFormSubmissionCreate(BaseModel):
    data: Dict[str, Any] = Field(default_factory=dict)


class CmsFormSubmissionRead(BaseModel):
    id: UUID
    form_id: UUID
    data: Dict[str, Any]
    submitted_at: datetime
    ip_address: Optional[str] = None

    model_config = orm_config


class CmsFormSubmissionPaginated(BaseModel):
    page: int
    page_size: int
    total: int
    items: List[CmsFormSubmissionRead]


# ── Email Marketing / Newsletter (R2-BE) ───────────────────────────────────

NewsletterStatus = Literal["draft", "scheduled", "sent"]
SubscriberSource = Literal["form", "manual", "import"]


class CmsNewsletterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    subject: str = Field(..., min_length=1, max_length=255)
    content_html: str = Field(..., description="HTML content of newsletter")
    status: NewsletterStatus = Field(default="draft")
    scheduled_at: Optional[datetime] = None


class CmsNewsletterUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    subject: Optional[str] = Field(default=None, min_length=1, max_length=255)
    content_html: Optional[str] = None
    status: Optional[NewsletterStatus] = None
    scheduled_at: Optional[datetime] = None


class CmsNewsletterRead(BaseModel):
    id: UUID
    site_id: UUID
    name: str
    subject: str
    content_html: str
    status: str
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    recipient_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = orm_config


class CmsSubscriberCreate(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    name: Optional[str] = Field(default=None, max_length=255)
    is_active: bool = Field(default=True)
    source: SubscriberSource = Field(default="manual")


class CmsSubscriberUpdate(BaseModel):
    email: Optional[str] = Field(default=None, min_length=3, max_length=255)
    name: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = None
    source: Optional[SubscriberSource] = None


class CmsSubscriberRead(BaseModel):
    id: UUID
    site_id: UUID
    email: str
    name: Optional[str] = None
    is_active: bool = True
    subscribed_at: datetime
    unsubscribed_at: Optional[datetime] = None
    source: str = "manual"

    model_config = orm_config


class CmsSubscriberImportItem(BaseModel):
    email: str
    name: Optional[str] = None


class CmsSubscriberImportPayload(BaseModel):
    emails: Optional[List[str]] = None
    subscribers: Optional[List[CmsSubscriberImportItem]] = None
    csv_content: Optional[str] = None


class CmsPublicSubscribeRequest(BaseModel):
    site_key: Optional[str] = None
    email: str = Field(..., min_length=3, max_length=255)
    name: Optional[str] = Field(default=None, max_length=255)


class CmsPublicUnsubscribeRequest(BaseModel):
    site_key: Optional[str] = None
    email: str = Field(..., min_length=3, max_length=255)


# ── A/B Testing of Sections (R3-BE) ─────────────────────────────────────────

AbTestStatus = Literal["active", "paused", "completed"]
AbTestVariant = Literal["a", "b"]
AbTestEventType = Literal["view", "click", "conversion"]


class CmsAbTestCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    page_id: UUID
    section_a_id: UUID
    section_b_id: UUID
    traffic_split: float = Field(default=0.5, ge=0.0, le=1.0)


class CmsAbTestUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    traffic_split: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    status: Optional[AbTestStatus] = None


class CmsAbTestRead(BaseModel):
    id: UUID
    site_id: UUID
    page_id: UUID
    name: str
    section_a_id: UUID
    section_b_id: UUID
    traffic_split: float = 0.5
    status: str = "active"
    winner_section_id: Optional[UUID] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    model_config = orm_config


class CmsAbTestEventCreate(BaseModel):
    variant: AbTestVariant
    event_type: AbTestEventType
    visitor_id: str = Field(..., min_length=1, max_length=255)


class CmsAbTestEventRead(BaseModel):
    id: UUID
    test_id: UUID
    variant: str
    event_type: str
    visitor_id: str
    created_at: datetime

    model_config = orm_config


class CmsAbTestResults(BaseModel):
    test_id: UUID
    views_a: int = 0
    views_b: int = 0
    clicks_a: int = 0
    clicks_b: int = 0
    conversions_a: int = 0
    conversions_b: int = 0
    conversion_rate_a: float = 0.0
    conversion_rate_b: float = 0.0
    statistical_significance: float = 0.0
    is_significant: bool = False
    recommended_winner: Optional[str] = None


class CmsAbTestApplyWinner(BaseModel):
    winner_variant: Optional[AbTestVariant] = None
    winner_section_id: Optional[UUID] = None


class CmsPostCommentCreate(BaseModel):
    author_name: str = Field(..., min_length=1, max_length=120)
    author_email: str = Field(..., min_length=3, max_length=255)
    content: str = Field(..., min_length=1)
    parent_id: Optional[UUID] = None


class CmsPostCommentStatusUpdate(BaseModel):
    status: Literal["pending", "approved", "spam", "deleted"]


class CmsPostCommentRead(BaseModel):
    id: UUID
    post_id: UUID
    parent_id: Optional[UUID] = None
    author_name: str
    author_email: str
    content: str
    status: str
    post_title: Optional[str] = None
    post_slug: Optional[str] = None
    created_at: AwareDateTime
    updated_at: AwareDateTime

    model_config = orm_config


class CmsPostCommentPublicRead(BaseModel):
    id: UUID
    post_id: UUID
    parent_id: Optional[UUID] = None
    author_name: str
    content: str
    created_at: AwareDateTime
    replies: List[CmsPostCommentPublicRead] = Field(default_factory=list)

    model_config = orm_config


class CmsPostCommentListResponse(PaginatedResponse[CmsPostCommentRead]):
    pending_count: int = 0


# ── Form Builder dinámico (plan_de_form_builder) ────────────────────────────
# Schemas para el render público: no exponen notify_emails ni otros datos
# sensibles. Los campos se validan con ``services/form_validation.py``.


class CmsFormPublicRead(BaseModel):
    """Metadatos públicos del formulario para renderizar en el sitio.

    Excluye ``notify_emails`` (dato sensible) y los campos inactivos. El
    ``captcha_site_key`` se expone para que el frontend renderice el widget
    de hCaptcha (es una clave pública, por diseño).
    """

    id: UUID
    name: str
    description: Optional[str] = None
    fields: List[Dict[str, Any]] = Field(default_factory=list)
    submit_button_text: str = "Enviar"
    success_message: str = "¡Gracias por tu mensaje!"
    captcha_enabled: bool = False
    captcha_provider: str = "hcaptcha"
    captcha_site_key: Optional[str] = None
    honeypot_enabled: bool = True
    settings_json: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True

    model_config = orm_config


class CmsFormSubmissionCreateV2(BaseModel):
    """Submit público con validación server-side de campos dinámicos.

    ``data`` es un dict ``{field_id: value}``. El backend valida cada valor
    contra el ``fields`` definido en el ``CmsForm``. ``captcha_token`` es
    obligatorio cuando el formulario tiene ``captcha_enabled=True``.
    ``_hp`` es el honeypot — debe venir vacío (los bots lo rellenan).
    """

    data: Dict[str, Any] = Field(default_factory=dict)
    captcha_token: Optional[str] = None
    _hp: Optional[str] = None

