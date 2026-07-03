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
  status: "draft" | "in_review" | "approved" | "published" | "archived" | string;
  seo_json: Record<string, unknown>;
  published_version_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface CmsSection {
  id: string;
  page_id: string;
  section_key: string;
  type: string;
  props_json: Record<string, unknown>;
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
  status: "draft" | "in_review" | "approved" | "published" | "archived" | string;
  seo_json: Record<string, unknown>;
  locale: string;
  published_at: string | null;
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

export interface BreadcrumbItem {
  name: string;
  item?: string;
}

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
  blocks?: Record<string, any>;
}
