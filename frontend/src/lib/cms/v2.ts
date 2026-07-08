import { apiFetch } from "@/lib/http";
import { CmsCategory, CmsMenu, CmsMenuItem, CmsPage, CmsPageVersion, CmsPostWithTaxonomies, CmsPublicPost, CmsPublishLog, CmsPublicMenu, CmsPublicPage, CmsSection, CmsSectionType, CmsSite, CmsTag, CmsTheme } from "@/types/cms-v2";

export async function listCmsSites(token?: string | null) {
  return apiFetch<CmsSite[]>("/cms/v2/sites", { token });
}

export async function createCmsSite(
  payload: { site_key: string; name: string; base_path: string; is_active?: boolean },
  token?: string | null,
) {
  return apiFetch<CmsSite>("/cms/v2/sites", {
    method: "POST",
    token,
    body: payload,
  });
}

export async function patchCmsSite(siteKey: string, payload: { name?: string; base_path?: string; is_active?: boolean }, token?: string | null) {
  return apiFetch<CmsSite>(`/cms/v2/sites/${siteKey}`, {
    method: "PATCH",
    token,
    body: payload,
  });
}

export async function listCmsMenus(siteKey: string, token?: string | null) {
  return apiFetch<CmsMenu[]>(`/cms/v2/sites/${siteKey}/menus`, { token });
}

export async function patchCmsMenu(
  siteKey: string,
  menuKey: string,
  payload: { name?: string; is_active?: boolean },
  token?: string | null,
) {
  return apiFetch<CmsMenu>(`/cms/v2/sites/${siteKey}/menus/${menuKey}`, {
    method: "PATCH",
    token,
    body: payload,
  });
}

export async function deleteCmsMenu(siteKey: string, menuKey: string, token?: string | null) {
  await apiFetch<void>(`/cms/v2/sites/${siteKey}/menus/${menuKey}`, {
    method: "DELETE",
    token,
  });
}

export async function listCmsThemes(siteKey: string, token?: string | null) {
  return apiFetch<CmsTheme[]>(`/cms/v2/sites/${siteKey}/themes`, { token });
}

export async function createCmsTheme(
  siteKey: string,
  payload: { name: string; tokens_json: Record<string, string>; is_active?: boolean; status?: string },
  token?: string | null,
) {
  return apiFetch<CmsTheme>(`/cms/v2/sites/${siteKey}/themes`, {
    method: "POST",
    token,
    body: payload,
  });
}

export async function deleteCmsTheme(siteKey: string, themeId: string, token?: string | null) {
  await apiFetch<void>(`/cms/v2/sites/${siteKey}/themes/${themeId}`, {
    method: "DELETE",
    token,
  });
}

export async function activateCmsTheme(siteKey: string, themeId: string, token?: string | null) {
  return apiFetch<CmsTheme>(`/cms/v2/sites/${siteKey}/themes/${themeId}/activate`, {
    method: "POST",
    token,
  });
}

export async function patchCmsTheme(
  siteKey: string,
  themeId: string,
  payload: { name?: string; tokens_json?: Record<string, string>; is_active?: boolean; status?: string },
  token?: string | null,
) {
  return apiFetch<CmsTheme>(`/cms/v2/sites/${siteKey}/themes/${themeId}`, {
    method: "PATCH",
    token,
    body: payload,
  });
}

export async function listCmsMenuItems(siteKey: string, menuKey: string, token?: string | null) {
  return apiFetch<CmsMenuItem[]>(`/cms/v2/sites/${siteKey}/menus/${menuKey}/items`, { token });
}

export async function createCmsMenu(
  siteKey: string,
  payload: { menu_key: string; name: string; is_active?: boolean },
  token?: string | null,
) {
  return apiFetch<CmsMenu>(`/cms/v2/sites/${siteKey}/menus`, {
    method: "POST",
    token,
    body: payload,
  });
}

export async function createCmsMenuItem(
  siteKey: string,
  menuKey: string,
  payload: {
    label: string;
    href: string;
    parent_id?: string | null;
    target?: string;
    is_external?: boolean;
    visibility?: string;
    sort_order?: number;
    meta_json?: Record<string, unknown>;
  },
  token?: string | null,
) {
  return apiFetch<CmsMenuItem>(`/cms/v2/sites/${siteKey}/menus/${menuKey}/items`, {
    method: "POST",
    token,
    body: payload,
  });
}

export async function patchCmsMenuItem(
  siteKey: string,
  menuKey: string,
  itemId: string,
  payload: Partial<Pick<CmsMenuItem, "label" | "href" | "target" | "is_external" | "visibility" | "sort_order" | "parent_id">>,
  token?: string | null,
) {
  return apiFetch<CmsMenuItem>(`/cms/v2/sites/${siteKey}/menus/${menuKey}/items/${itemId}`, {
    method: "PATCH",
    token,
    body: payload,
  });
}

export async function deleteCmsMenuItem(siteKey: string, menuKey: string, itemId: string, token?: string | null) {
  await apiFetch<void>(`/cms/v2/sites/${siteKey}/menus/${menuKey}/items/${itemId}`, {
    method: "DELETE",
    token,
  });
}

export async function reorderCmsMenuItems(
  siteKey: string,
  menuKey: string,
  items: Array<{ id: string; parent_id: string | null; sort_order: number }>,
  token?: string | null,
) {
  return apiFetch<CmsMenuItem[]>(`/cms/v2/sites/${siteKey}/menus/${menuKey}/reorder`, {
    method: "POST",
    token,
    body: { items },
  });
}

export async function getCmsPublicMenu(siteKey: string, menuKey: string) {
  return apiFetch<CmsPublicMenu>(`/cms/v2/public/sites/${siteKey}/menus/${menuKey}`, { silent: true });
}

export async function listCmsPages(siteKey: string, token?: string | null) {
  const res = await apiFetch<{ items: CmsPage[]; total: number } | CmsPage[]>(`/cms/v2/sites/${siteKey}/pages`, { token });
  return Array.isArray(res) ? res : res?.items ?? [];
}

export async function createCmsPage(
  siteKey: string,
  payload: {
    slug: string;
    title: string;
    status?: string;
    seo_json?: Record<string, unknown>;
    publish_at?: string | null;
    expires_at?: string | null;
  },
  token?: string | null,
) {
  return apiFetch<CmsPage>(`/cms/v2/sites/${siteKey}/pages`, {
    method: "POST",
    token,
    body: payload,
  });
}

export async function patchCmsPage(
  siteKey: string,
  slug: string,
  payload: {
    slug?: string;
    title?: string;
    status?: string;
    seo_json?: Record<string, unknown>;
    publish_at?: string | null;
    expires_at?: string | null;
  },
  token?: string | null,
) {
  return apiFetch<CmsPage>(`/cms/v2/sites/${siteKey}/pages/${slug}`, {
    method: "PATCH",
    token,
    body: payload,
  });
}

export async function deleteCmsPage(siteKey: string, slug: string, token?: string | null) {
  await apiFetch<void>(`/cms/v2/sites/${siteKey}/pages/${slug}`, {
    method: "DELETE",
    token,
  });
}

export async function listCmsSections(siteKey: string, slug: string, token?: string | null): Promise<CmsSection[]> {
  const res = await apiFetch<{ items: CmsSection[]; total: number; skip: number; limit: number }>(
    `/cms/v2/sites/${siteKey}/pages/${slug}/sections`, { token }
  );
  return res.items ?? [];
}

export async function createCmsSection(
  siteKey: string,
  slug: string,
  payload: { type: string; props_json: Record<string, unknown>; sort_order?: number; is_visible?: boolean; status?: string },
  token?: string | null,
) {
  return apiFetch<CmsSection>(`/cms/v2/sites/${siteKey}/pages/${slug}/sections`, {
    method: "POST",
    token,
    body: payload,
  });
}

export async function patchCmsSection(
  siteKey: string,
  slug: string,
  sectionId: string,
  payload: { type?: string; props_json?: Record<string, unknown>; sort_order?: number; is_visible?: boolean; status?: string },
  token?: string | null,
) {
  return apiFetch<CmsSection>(`/cms/v2/sites/${siteKey}/pages/${slug}/sections/${sectionId}`, {
    method: "PATCH",
    token,
    body: payload,
  });
}

export async function deleteCmsSection(siteKey: string, slug: string, sectionId: string, token?: string | null) {
  await apiFetch<void>(`/cms/v2/sites/${siteKey}/pages/${slug}/sections/${sectionId}`, {
    method: "DELETE",
    token,
  });
}

export async function reorderCmsSections(
  siteKey: string,
  slug: string,
  items: Array<{ id: string; sort_order: number }>,
  token?: string | null,
) {
  return apiFetch<CmsSection[]>(`/cms/v2/sites/${siteKey}/pages/${slug}/sections/reorder`, {
    method: "POST",
    token,
    body: { items },
  });
}

export async function workflowCmsPage(
  siteKey: string,
  slug: string,
  action: "submit_review" | "approve" | "publish" | "archive" | "revert_draft",
  notes: string | undefined,
  token?: string | null,
) {
  return apiFetch<CmsPage>(`/cms/v2/sites/${siteKey}/pages/${slug}/workflow`, {
    method: "POST",
    token,
    body: { action, notes },
  });
}

export async function listCmsPageVersions(siteKey: string, slug: string, token?: string | null): Promise<CmsPageVersion[]> {
  const res = await apiFetch<{ items: CmsPageVersion[]; total: number; skip: number; limit: number }>(
    `/cms/v2/sites/${siteKey}/pages/${slug}/versions`, { token }
  );
  return res.items ?? [];
}

export async function listCmsPagePublishLog(siteKey: string, slug: string, token?: string | null): Promise<CmsPublishLog[]> {
  const res = await apiFetch<{ items: CmsPublishLog[]; total: number; skip: number; limit: number }>(
    `/cms/v2/sites/${siteKey}/pages/${slug}/publish-log`, { token }
  );
  return res.items ?? [];
}

export async function rollbackCmsPageVersion(siteKey: string, slug: string, versionId: string, token?: string | null) {
  return apiFetch<CmsPage>(`/cms/v2/sites/${siteKey}/pages/${slug}/rollback/${versionId}`, {
    method: "POST",
    token,
  });
}

export async function getCmsPublicPage(siteKey: string, slug: string, options?: { silent?: boolean }) {
  return apiFetch<CmsPublicPage>(`/cms/v2/public/sites/${siteKey}/pages/${slug}`, {
    silent: options?.silent,
  });
}

export async function getCmsPagePreview(siteKey: string, slug: string, token?: string | null) {
  return apiFetch<CmsPublicPage>(`/cms/v2/sites/${siteKey}/pages/${slug}/preview`, { token, cache: "no-store" });
}

export interface PastoralProfile {
  id: string;
  name: string;
  slug: string;
  photo_url?: string | null;
  bio_short?: string | null;
  bio_full?: string | null;
  role?: string | null;
  social_instagram?: string | null;
  social_facebook?: string | null;
  social_twitter?: string | null;
  is_main_pastor: boolean;
  pastoral_sort_order?: number;
  is_pastoral_published?: boolean;
}

export async function getPublicPastoralTeam(siteKey: string): Promise<PastoralProfile[]> {
  return apiFetch<PastoralProfile[]>(`/cms/v2/public/sites/${siteKey}/pastoral-team`);
}

export async function getCmsPastoralTeam(token?: string | null): Promise<PastoralProfile[]> {
  return apiFetch<PastoralProfile[]>(`/cms/v2/cms/pastoral-team`, { token });
}

export async function updateCmsPastoralProfile(personaId: string, payload: Partial<PastoralProfile>, token?: string | null): Promise<PastoralProfile> {
  return apiFetch<PastoralProfile>(`/cms/v2/cms/pastoral-team/${personaId}`, {
    method: "PATCH",
    token,
    body: payload,
  });
}

// ── Section Types (platform-wide catalog) ─────────────────────────────────
//
// Endpoints are global (no site scoping). Read endpoints require cms:read;
// write endpoints require CMS_PUBLISHER_ROLES server-side. Client-side we
// let ``canPublishCms(user.role)`` decide whether to render write controls.

export async function listCmsSectionTypes(
  onlyActive?: boolean,
  token?: string | null,
): Promise<CmsSectionType[]> {
  return apiFetch<CmsSectionType[]>("/cms/v2/section-types", {
    query: onlyActive ? { only_active: true } : undefined,
    token,
  });
}

export async function createCmsSectionType(
  payload: { name: string; description?: string | null; is_active?: boolean },
  token?: string | null,
): Promise<CmsSectionType> {
  return apiFetch<CmsSectionType>("/cms/v2/section-types", {
    method: "POST",
    token,
    body: payload,
  });
}

export async function patchCmsSectionType(
  name: string,
  payload: { description?: string | null; is_active?: boolean },
  token?: string | null,
): Promise<CmsSectionType> {
  return apiFetch<CmsSectionType>(`/cms/v2/section-types/${name}`, {
    method: "PATCH",
    token,
    body: payload,
  });
}

export async function deleteCmsSectionType(name: string, token?: string | null): Promise<void> {
  await apiFetch<void>(`/cms/v2/section-types/${name}`, {
    method: "DELETE",
    token,
  });
}

// ── Categories ─────────────────────────────────────────────────────────────

export async function listCmsCategories(siteKey: string, token?: string | null) {
  return apiFetch<CmsCategory[]>(`/cms/v2/sites/${siteKey}/categories`, { token });
}

export async function createCmsCategory(
  siteKey: string,
  payload: { slug: string; name: string; description?: string | null; parent_id?: string | null; is_active?: boolean },
  token?: string | null,
) {
  return apiFetch<CmsCategory>(`/cms/v2/sites/${siteKey}/categories`, {
    method: "POST",
    token,
    body: payload,
  });
}

export async function patchCmsCategory(
  siteKey: string,
  slug: string,
  payload: { slug?: string; name?: string; description?: string | null; parent_id?: string | null; is_active?: boolean },
  token?: string | null,
) {
  return apiFetch<CmsCategory>(`/cms/v2/sites/${siteKey}/categories/${slug}`, {
    method: "PATCH",
    token,
    body: payload,
  });
}

export async function deleteCmsCategory(siteKey: string, slug: string, token?: string | null) {
  await apiFetch<void>(`/cms/v2/sites/${siteKey}/categories/${slug}`, {
    method: "DELETE",
    token,
  });
}

// ── Tags ───────────────────────────────────────────────────────────────────

export async function listCmsTags(siteKey: string, token?: string | null) {
  return apiFetch<CmsTag[]>(`/cms/v2/sites/${siteKey}/tags`, { token });
}

export async function createCmsTag(
  siteKey: string,
  payload: { slug: string; name: string; is_active?: boolean },
  token?: string | null,
) {
  return apiFetch<CmsTag>(`/cms/v2/sites/${siteKey}/tags`, {
    method: "POST",
    token,
    body: payload,
  });
}

export async function patchCmsTag(
  siteKey: string,
  slug: string,
  payload: { slug?: string; name?: string; is_active?: boolean },
  token?: string | null,
) {
  return apiFetch<CmsTag>(`/cms/v2/sites/${siteKey}/tags/${slug}`, {
    method: "PATCH",
    token,
    body: payload,
  });
}

export async function deleteCmsTag(siteKey: string, slug: string, token?: string | null) {
  await apiFetch<void>(`/cms/v2/sites/${siteKey}/tags/${slug}`, {
    method: "DELETE",
    token,
  });
}

// ── Posts ──────────────────────────────────────────────────────────────────

export async function listCmsPosts(siteKey: string, token?: string | null) {
  const res = await apiFetch<{ items: CmsPostWithTaxonomies[]; total: number } | CmsPostWithTaxonomies[]>(`/cms/v2/sites/${siteKey}/posts`, { token });
  return Array.isArray(res) ? res : res?.items ?? [];
}

export async function createCmsPost(
  siteKey: string,
  payload: {
    slug: string;
    title: string;
    excerpt?: string | null;
    content?: string | null;
    featured_image_url?: string | null;
    status?: string;
    seo_json?: Record<string, unknown>;
    category_ids?: string[];
    tag_ids?: string[];
    published_at?: string | null;
    expires_at?: string | null;
  },
  token?: string | null,
) {
  return apiFetch<CmsPostWithTaxonomies>(`/cms/v2/sites/${siteKey}/posts`, {
    method: "POST",
    token,
    body: payload,
  });
}

export async function patchCmsPost(
  siteKey: string,
  slug: string,
  payload: {
    slug?: string;
    title?: string;
    excerpt?: string | null;
    content?: string | null;
    featured_image_url?: string | null;
    status?: string;
    seo_json?: Record<string, unknown>;
    category_ids?: string[];
    tag_ids?: string[];
    published_at?: string | null;
    expires_at?: string | null;
  },
  token?: string | null,
) {
  return apiFetch<CmsPostWithTaxonomies>(`/cms/v2/sites/${siteKey}/posts/${slug}`, {
    method: "PATCH",
    token,
    body: payload,
  });
}

export async function deleteCmsPost(siteKey: string, slug: string, token?: string | null) {
  await apiFetch<void>(`/cms/v2/sites/${siteKey}/posts/${slug}`, {
    method: "DELETE",
    token,
  });
}

export async function getCmsPublicPosts(
  siteKey: string,
  options?: { category_slug?: string; tag_slug?: string; skip?: number; limit?: number },
) {
  return apiFetch<CmsPublicPost[]>(`/cms/v2/public/sites/${siteKey}/posts`, {
    query: options,
  });
}

export async function getCmsPublicPost(siteKey: string, slug: string) {
  return apiFetch<CmsPublicPost>(`/cms/v2/public/sites/${siteKey}/posts/${slug}`);
}

// ── Scheduled publish + auto-archive helpers (2026-07-06) ────────────────
//
// Helper UI utilities for the calendar + detail views. Formatters convert
// ISO datetime strings (UTC, returned by the API) into local form for
// display. The page object now carries ``publish_at`` and ``expires_at``
// optional fields (typed in ``@/types/cms-v2``).

export interface ScheduleDraftPayload {
  publish_at?: string | null;
  expires_at?: string | null;
}

export function isScheduledPage(page: { status?: string | null; publish_at?: string | null } | null | undefined): boolean {
  if (!page) return false;
  if (page.status === "scheduled") return true;
  return Boolean(page.publish_at);
}

export function isExpiringPage(page: { status?: string | null; expires_at?: string | null } | null | undefined): boolean {
  if (!page) return false;
  if (page.status === "published" && page.expires_at) return true;
  return Boolean(page.expires_at);
}

export type ScheduleCalendarColor = "blue" | "emerald" | "amber" | "rose";

export function scheduleEventColor(
  status: string | null | undefined,
  kind: "publish" | "expiry",
): ScheduleCalendarColor {
  if (kind === "expiry") {
    // Auto-archive pending.
    if (status === "published") return "amber";
    return "rose";
  }
  // Publishing event.
  if (status === "scheduled") return "blue";
  if (status === "published") return "emerald";
  if (status === "approved") return "blue";
  return "rose";
}

export function toLocalDateTimeInputValue(iso: string | null | undefined): string {
  if (!iso) return "";
  // ``<input type="datetime-local">`` wants ``YYYY-MM-DDTHH:mm`` (no TZ).
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "";
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  } catch {
    return "";
  }
}

export function fromLocalDateTimeInputValue(localStr: string | null | undefined): string | null {
  if (!localStr) return null;
  // Treat as local time, serialize to UTC ISO for the backend. The browser
  // Date constructor interprets ``YYYY-MM-DDTHH:mm`` as local time which
  // is what we want here (``datetime-local`` input is local).
  try {
    const d = new Date(localStr);
    if (Number.isNaN(d.getTime())) return null;
    return d.toISOString();
  } catch {
    return null;
  }
}


// ── SEO Audit (Faro global) ───────────────────────────────────────────────────
//
// Endpoint GET /cms/v2/sites/{site_key}/seo-audit (CMS_EDITOR_ROLES).
// Devuelve aggregate + hallazgos por página (Pydantic: SeoAuditResponse).

export type SeoFindingCode =
  | "meta_description_missing"
  | "meta_description_too_short"
  | "meta_description_too_long"
  | "title_length_out_of_range"
  | "noindex_on_published"
  | "nofollow_on_published"
  | "no_visible_sections"
  | "thin_content_sections"
  | "thin_content_text"
  | "image_missing_alt"
  | "image_url_missing_alt"
  | "og_image_missing";

export type SeoSeverity = "info" | "warning" | "error";

export interface SeoFinding {
  code: SeoFindingCode | string;
  severity: SeoSeverity;
  message: string;
  impact_points: number;
  hint: string;
  field_ref: string | null;
  section_id: string | null;
}

export interface PageSeoAudit {
  page_id: string;
  slug: string;
  title: string;
  status: string;
  score: number;
  findings: SeoFinding[];
}

export interface SiteSeoStats {
  average_score: number;
  total_pages: number;
  pages_with_errors: number;
  critical_issues: number;
  by_severity: Record<string, number>;
}

export interface SeoAuditResponse {
  site_key: string;
  aggregate: SiteSeoStats;
  pages: PageSeoAudit[];
}

export async function getSeoAudit(
  siteKey: string,
  options?: { status?: string; min_score?: number; skip?: number; limit?: number },
  token?: string | null,
): Promise<SeoAuditResponse> {
  return apiFetch<SeoAuditResponse>(`/cms/v2/sites/${siteKey}/seo-audit`, {
    token,
    cache: "no-store",
    query: options,
  });
}
