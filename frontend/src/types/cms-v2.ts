import type { CmsSectionTypeToProps } from "./cms-section-props";

/** Discriminated union of every section variant (re-export for callers). */
export type { CmsSectionDiscriminated } from "./cms-section-props";

export interface CmsSite {
  id: string;
  site_key: string;
  name: string;
  base_path: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CmsTheme {
  id: string;
  site_id: string;
  name: string;
  tokens_json: Record<string, string>;
  is_active: boolean;
  status: "active" | "archived" | string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface CmsMenu {
  id: string;
  site_id: string;
  menu_key: string;
  name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CmsMenuItem {
  id: string;
  menu_id: string;
  parent_id: string | null;
  label: string;
  href: string;
  target: string;
  is_external: boolean;
  visibility: string;
  sort_order: number;
  meta_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CmsPublicMenu {
  site_key: string;
  menu_key: string;
  items: Array<{
    id: string;
    parent_id: string | null;
    label: string;
    href: string;
    target: string;
    is_external: boolean;
    visibility: string;
    sort_order: number;
    meta_json: Record<string, unknown>;
  }>;
}

export interface CmsPage {
  id: string;
  site_id: string;
  slug: string;
  title: string;
  status: "draft" | "in_review" | "approved" | "scheduled" | "published" | "archived" | string;
  seo_json: Record<string, unknown>;
  published_version_id: string | null;
  // Scheduled publish + auto-archive (2026-07-06).
  publish_at: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

/**
 * A CMS section row, optionally narrowed by ``type`` for typed ``props_json``.
 *
 * The default shape preserves the historical contract where ``type`` is an
 * arbitrary ``string`` and ``props_json`` is an opaque ``Record<string,
 * unknown>``. All existing consumers (the 275 call-sites that read
 * ``section.props_json`` and pass it to ``val()`` / ``asItems()``) continue
 * to typecheck unchanged — the generic defaults give them back the previous
 * behaviour.
 *
 * For type-tight call-sites, pass an explicit section type — the props
 * interface narrows automatically:
 *
 *   function HeroSection({ section }: { section: CmsSection<"hero"> }) {
 *     section.props_json.title;        // string | undefined
 *     section.props_json.image_alt;    // string | undefined
 *   }
 *
 * The 44 recognised type strings and their contracts live in
 * ``cms-section-props.ts`` (∷ CmsSectionTypeToProps). Discriminated union
 * ``CmsSectionDiscriminated`` is also exported from that module for callers
 * that iterate a heterogeneous section array.
 */
export interface CmsSection<T extends string = string> {
  id: string;
  page_id: string;
  section_key: string;
  type: T;
  props_json: T extends keyof CmsSectionTypeToProps ? CmsSectionTypeToProps[T] : Record<string, unknown>;
  sort_order: number;
  is_visible: boolean;
  status: "active" | "archived" | string;
  created_at: string;
  updated_at: string;
}

export interface CmsPageVersion {
  id: string;
  page_id: string;
  version_number: number;
  snapshot_json: Record<string, unknown>;
  notes: string | null;
  created_at: string;
}

export interface CmsPublishLog {
  id: string;
  site_id: string;
  page_id: string | null;
  entity_type: string;
  entity_id: string | null;
  action: string;
  from_status: string | null;
  to_status: string | null;
  actor_persona_id: string | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

/**
 * Catalog entry for the global platform-wide ``CmsSectionType`` table.
 * Section types are not site-scoped — they define which ``type`` strings
 * a CMS editor can use when building pages.
 *
 * The associated Pydantic backend shape (see
 * ``backend.schemas.cms.CmsSectionTypeRead``) is alphabetized, so the
 * frontend reads them in name-ascending order.
 */
export interface CmsSectionType {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CmsCategory {
  id: string;
  site_id: string;
  parent_id: string | null;
  slug: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CmsTag {
  id: string;
  site_id: string;
  slug: string;
  name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CmsPost {
  id: string;
  site_id: string;
  slug: string;
  title: string;
  excerpt: string | null;
  content: string | null;
  featured_image_url: string | null;
  status: "draft" | "in_review" | "approved" | "scheduled" | "published" | "archived" | string;
  seo_json: Record<string, unknown>;
  locale: string;
  published_at: string | null;
  // Auto-archive (2026-07-06).
  expires_at: string | null;
  author_persona_id: string | null;
  created_by_persona_id: string | null;
  updated_by_persona_id: string | null;
  created_at: string;
  updated_at: string;
  categories?: CmsCategory[];
  tags?: CmsTag[];
}

export interface CmsPostWithTaxonomies extends CmsPost {
  categories: CmsCategory[];
  tags: CmsTag[];
}

export interface CmsPublicPost {
  site_key: string;
  slug: string;
  title: string;
  excerpt: string | null;
  content: string | null;
  featured_image_url: string | null;
  seo_json: Record<string, unknown>;
  published_at: string | null;
  author_name: string | null;
  categories: CmsCategory[];
  tags: CmsTag[];
  json_ld?: Record<string, unknown> | null;
  canonical_url?: string | null;
}

// ── v1-compat shapes (Testimonial / Announcement) ───────────────────────────
// These mirror the backend CmsTestimonialRead / CmsAnnouncementRead schemas
// which flatten seo_json fields for gradual frontend migration.

export interface CmsTestimonial extends CmsPostWithTaxonomies {
  emotion: string;
  media_type: string;
  media_url?: string | null;
  image_url?: string | null;
  video_url?: string | null;
  podcast_url?: string | null;
  is_approved: boolean;
  show_on_home: boolean;
}

export interface CmsAnnouncement extends CmsPostWithTaxonomies {
  category: string;
  is_featured: boolean;
  image_url?: string | null;
  is_active: boolean;
}

export type CanonicalCategory = "testimonials" | "announcements";

export interface BreadcrumbItem {
  name: string;
  item?: string;
}

export interface CmsPageBlock extends Record<string, unknown> {
  parsed: Record<string, unknown>;
  content: string;
}

export type CmsPageBlocks = Record<string, CmsPageBlock>;

export interface CmsPublicPage {
  site_key: string;
  slug: string;
  title: string;
  seo_json: Record<string, unknown>;
  sections: CmsSection[];
  /** Auto-generated JSON-LD Schema.org structured data. */
  json_ld?: Record<string, unknown> | null;
  /** Canonical URL for this page (auto-generated or overridden). */
  canonical_url?: string | null;
  /** Derived breadcrumb trail from slug hierarchy. */
  breadcrumbs?: BreadcrumbItem[] | null;
  /** Auto-generated JSON-LD BreadcrumbList structured data. */
  breadcrumb_json_ld?: Record<string, unknown> | null;
  /**
   * Derived map keyed by ``CmsSection.section_key`` (``"hero"``,
   * ``"feed"``, ``"events"``, ``"pastors"`` …). Each entry is the raw
   * ``props_json`` of the matching section, so call sites can do
   * ``page?.blocks?.hero?.eyebrow`` without unwrapping ``props_json``.
   * Computed client-side by ``useCmsV2Page`` — the API itself returns
   * ``sections`` only; this field is optional for backward compat with
   * the catch-all renderer that iterates ``page.sections``.
   */
  blocks?: CmsPageBlocks;
}

export type PopupTriggerType = "on_load" | "time_delay" | "scroll_percent" | "exit_intent";

export interface CmsPopup {
  id: string;
  site_id: string;
  name: string;
  content_html: string;
  trigger_type: PopupTriggerType;
  trigger_value: number | null;
  is_active: boolean;
  show_on_pages: string[];
  created_at: string;
  updated_at: string;
}

export interface CmsPublicPopup {
  id: string;
  name: string;
  content_html: string;
  trigger_type: PopupTriggerType;
  trigger_value: number | null;
  show_on_pages: string[];
}

/**
 * Tipos de campo del form builder dinámico (plan_de_form_builder).
 * Espejo de ``backend.services.form_validation.FIELD_TYPES``.
 */
export type CmsFormFieldType =
  | "text"
  | "email"
  | "phone"
  | "textarea"
  | "select"
  | "checkbox"
  | "number"
  | "date"
  | "datetime"
  | "url"
  | "select_multiple"
  | "radio"
  | "rating"
  | "slider"
  | "file"
  | "section"
  | "page"
  | "divider"
  | "captcha";

/** Condición de visibilidad (``visible_if``) — espejo de ``_OPERATORS``. */
export type CmsFormConditionOperator =
  | "eq"
  | "neq"
  | "in"
  | "not_in"
  | "contains"
  | "gt"
  | "lt"
  | "gte"
  | "lte"
  | "checked"
  | "not_checked"
  | "empty"
  | "not_empty";

export interface CmsFormVisibleIf {
  field_id: string;
  operator: CmsFormConditionOperator;
  value?: unknown;
}

/**
 * Contrato de un campo del form builder (superset del schema V1).
 * Los campos V1 (6 tipos) siguen siendo válidos — ``CmsFormField`` es
 * retro-compatible con el shape anterior (``id,type,label,placeholder,
 * required,options``).
 */
export interface CmsFormField {
  id: string;
  type: CmsFormFieldType;
  label: string;
  placeholder?: string;
  required: boolean;
  options?: string[];
  /** select/radio/select_multiple: permitir "Otra opción" libre. */
  allow_other?: boolean;
  /** text/textarea/email: límites de longitud. */
  min_length?: number;
  max_length?: number;
  /** text/textarea: patrón de validación + mensaje. */
  regex_pattern?: string;
  regex_message?: string;
  /** number/rating/slider: rango permitido. */
  min_value?: number;
  max_value?: number;
  /** slider: tamaño del paso (solo UI; el backend valida rango). */
  step?: number;
  /** file: tamaño máximo en MB y MIME permitidos (p.ej. "image/*"). */
  max_file_mb?: number;
  accept?: string;
  /** helper_text: texto de ayuda bajo el campo. */
  helper_text?: string;
  /** Lógica condicional — campo solo visible si se cumple. */
  visible_if?: CmsFormVisibleIf;
}

/** Metadatos públicos de un formulario (excluye notify_emails). */
export interface CmsFormPublicRead {
  id: string;
  name: string;
  description: string | null;
  fields: CmsFormField[];
  submit_button_text: string;
  success_message: string;
  captcha_enabled: boolean;
  captcha_provider: string;
  captcha_site_key: string | null;
  honeypot_enabled: boolean;
  settings_json: Record<string, unknown>;
  is_active: boolean;
}

export interface CmsForm {
  id: string;
  site_id: string;
  name: string;
  description: string | null;
  fields: CmsFormField[];
  submit_button_text: string;
  success_message: string;
  notify_emails: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
  submission_count?: number;
  settings_json?: Record<string, unknown>;
  captcha_enabled?: boolean;
  captcha_provider?: string;
  honeypot_enabled?: boolean;
}

export interface CmsFormSubmission {
  id: string;
  form_id: string;
  data: Record<string, unknown>;
  submitted_at: string;
  ip_address: string | null;
}

export interface CmsFormSubmissionPaginated {
  page: number;
  page_size: number;
  total: number;
  items: CmsFormSubmission[];
}

export interface CmsNewsletter {
  id: string;
  site_id: string;
  name: string;
  subject: string;
  content_html: string;
  status: "draft" | "scheduled" | "sent" | string;
  scheduled_at: string | null;
  sent_at: string | null;
  recipient_count: number;
  created_at: string;
  updated_at: string;
}

export interface CmsSubscriber {
  id: string;
  site_id: string;
  email: string;
  name: string | null;
  is_active: boolean;
  subscribed_at: string;
  unsubscribed_at: string | null;
  source: "form" | "manual" | "import" | string;
}

export type CmsAbTestStatus = "active" | "paused" | "completed";

export interface CmsAbTest {
  id: string;
  site_id: string;
  page_id: string;
  name: string;
  section_a_id: string;
  section_b_id: string;
  traffic_split: number;
  status: CmsAbTestStatus;
  winner_section_id: string | null;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
}

export interface CmsAbTestEvent {
  id: string;
  test_id: string;
  variant: "a" | "b";
  event_type: "view" | "click" | "conversion";
  visitor_id: string;
  created_at: string;
}

export interface CmsAbTestResults {
  test_id: string;
  views_a: number;
  views_b: number;
  clicks_a: number;
  clicks_b: number;
  conversions_a: number;
  conversions_b: number;
  conversion_rate_a: number;
  conversion_rate_b: number;
  statistical_significance: number;
  is_significant: boolean;
  recommended_winner: "a" | "b" | null;
}

export type CmsCommentStatus = "pending" | "approved" | "spam" | "deleted";

export interface CmsPostComment {
  id: string;
  post_id: string;
  parent_id: string | null;
  author_name: string;
  author_email: string;
  content: string;
  status: CmsCommentStatus;
  post_title?: string | null;
  post_slug?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CmsPublicPostComment {
  id: string;
  post_id: string;
  parent_id: string | null;
  author_name: string;
  content: string;
  created_at: string;
  replies: CmsPublicPostComment[];
}

export interface CmsPostCommentsPaginated {
  items: CmsPostComment[];
  total: number;
  skip: number;
  limit: number;
  pending_count: number;
}
