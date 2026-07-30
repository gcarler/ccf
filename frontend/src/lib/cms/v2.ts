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
    silent: options?.silent ?? true,
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
  return apiFetch<PastoralProfile[]>(`/cms/v2/public/sites/${siteKey}/pastoral-team`, { silent: true });
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

export async function getCmsPost(siteKey: string, slug: string, token?: string | null) {
  return apiFetch<CmsPostWithTaxonomies>(`/cms/v2/sites/${siteKey}/posts/${slug}`, { token });
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
  return apiFetch<CmsPublicPost>(`/cms/v2/public/sites/${siteKey}/posts/${slug}`, { silent: true });
}

/** v2 public helper: fetch testimonials via public API, return v1-compatible shape.
 *
 * The backend stores testimonials as CmsPost rows categorised as ``testimonials``.
 * This function maps the public CmsPublicPost shape (which has ``author_name``
 * instead of an author object, and v1 fields in ``seo_json``) into a flat shape
 * that the existing public UI components can consume without modification.
 *
 * NOTE: ``author.avatarUrl`` and ``author.role`` are not available via the public
 * endpoint; the UI gracefully falls back to initials / "Persona".
 */
export interface PublicTestimonialItem {
  id: string;
  slug: string;
  content: string;
  emotion: string;
  media_type: string;
  media_url: string | null;
  image_url: string | null;
  video_url: string | null;
  podcast_url: string | null;
  author: { username: string; avatarUrl?: string; role?: string } | null;
  is_approved?: boolean;
  show_on_home?: boolean;
  created_at?: string;
}

export async function getPublicTestimonials(
  siteKey: string,
): Promise<PublicTestimonialItem[]> {
  const posts = await getCmsPublicPosts(siteKey, {
    category_slug: "testimonials",
  });
  return posts.map(_publicPostToTestimonial);
}

function _publicPostToTestimonial(post: CmsPublicPost): PublicTestimonialItem {
  const seo = (post.seo_json ?? {}) as Record<string, unknown>;
  return {
    id: post.slug,
    slug: post.slug,
    content: post.content ?? "",
    emotion: (seo.emotion as string) || "Testimonio",
    media_type: (seo.media_type as string) || "text",
    media_url: null,
    image_url: post.featured_image_url,
    video_url: (seo.video_url as string | null) ?? null,
    podcast_url: (seo.podcast_url as string | null) ?? null,
    author: post.author_name ? { username: post.author_name } : null,
    is_approved: true,
    show_on_home: Boolean(seo.show_on_home),
    created_at: post.published_at ?? undefined,
  };
}

// ── Posts by Canonical Category (Testimonials / Announcements) ──────────────
// Replaces v1 shim endpoints: /cms/testimonials, /cms/announcements
// These wrap the generic post CRUD, filtering by category client-side since
// the backend stores testimonials/announcements as CmsPost rows with a
// canonical category association.

export type CanonicalCategory = "testimonials" | "announcements";

export async function listCmsPostsByCategory(
  siteKey: string,
  category: CanonicalCategory,
  options?: { status?: string; skip?: number; limit?: number; include_archived?: boolean },
  token?: string | null,
): Promise<CmsPostWithTaxonomies[]> {
  const cats = await listCmsCategories(siteKey, token);
  const cat = cats.find((c) => c.slug === category);
  if (!cat) return [];
  const posts = await listCmsPosts(siteKey, token);
  return posts.filter((p) => p.categories?.some((c) => c.id === cat.id));
}

export async function createCmsPostByCategory(
  siteKey: string,
  category: CanonicalCategory,
  payload: {
    slug?: string;
    title: string;
    excerpt?: string | null;
    content?: string | null;
    featured_image_url?: string | null;
    status?: string;
    seo_json?: Record<string, unknown>;
    tag_ids?: string[];
    published_at?: string | null;
    expires_at?: string | null;
  },
  token?: string | null,
) {
  const cats = await listCmsCategories(siteKey, token);
  const existing = cats.find((c) => c.slug === category);
  const catId = existing ? existing.id : (await createCmsCategory(siteKey, { slug: category, name: category, is_active: true }, token)).id;
  return createCmsPost(siteKey, { ...payload, slug: payload.slug ?? `${category}-${Date.now()}`, category_ids: [catId] }, token);
}

export async function getCmsPostByCategory(
  siteKey: string,
  slug: string,
  category: CanonicalCategory,
  token?: string | null,
): Promise<CmsPostWithTaxonomies | null> {
  const post = await getCmsPost(siteKey, slug, token).catch(() => null);
  if (!post) return null;
  if (!post.categories?.some((c) => c.slug === category)) return null;
  return post;
}

export async function patchCmsPostByCategory(
  siteKey: string,
  slug: string,
  category: CanonicalCategory,
  payload: {
    slug?: string;
    title?: string;
    excerpt?: string | null;
    content?: string | null;
    featured_image_url?: string | null;
    status?: string;
    seo_json?: Record<string, unknown>;
    tag_ids?: string[];
    published_at?: string | null;
    expires_at?: string | null;
  },
  token?: string | null,
) {
  return patchCmsPost(siteKey, slug, payload, token);
}

export async function deleteCmsPostByCategory(
  siteKey: string,
  slug: string,
  _category: CanonicalCategory,
  token?: string | null,
) {
  await deleteCmsPost(siteKey, slug, token);
}

// ── v1-compat adapters: CmsPostWithTaxonomies ⇄ Testimonial/Announcement ────
// Frontend shim: testimonials and announcements now live as CmsPost rows
// categorised by canonical "testimonials"/"announcements" categories, with
// emotion/media_type/etc. flattened into ``seo_json``. These adapters keep
// the v1-shaped objects the admin UI still expects (TestimonialRead /
// AnnouncementRead) so pages can migrate to the v2 endpoints without a large
// UI rewrite. Once the UI reads the v2 shape (CmsPostReadWithTaxonomies)
// directly, these can be removed.

export interface V1TestimonialShape {
  id: string;
  slug: string;
  content: string;
  emotion: string;
  media_type?: "text" | "image" | "video" | "podcast" | string;
  media_url?: string | null;
  image_url?: string | null;
  video_url?: string | null;
  podcast_url?: string | null;
  created_at: string;
  author_persona_id?: string | null;
  published?: boolean;
  is_approved?: boolean;
  show_on_home?: boolean;
  status?: "pending" | "approved" | "archived" | string;
}

export interface V1AnnouncementShape {
  id: string;
  slug: string;
  title: string;
  content: string;
  category: string;
  image_url?: string | null;
  is_active: boolean;
  is_featured: boolean;
  status: string;
  created_at: string;
  published_at?: string;
}

function _testimonialStatusFromPost(status: string | undefined | null): string {
  if (status === "published") return "approved";
  if (status === "archived") return "archived";
  return "pending";
}

/** Convert a v2 CmsPost into the v1 TestimonialRead shape the admin UI expects. */
export function postToTestimonial(post: CmsPostWithTaxonomies): V1TestimonialShape {
  const seo = (post.seo_json ?? {}) as Record<string, unknown>;
  const emotion = (seo.emotion as string) || "Testimonio";
  const mediaType = (seo.media_type as string) || "text";
  const mediaUrl = (seo.media_url as string | null | undefined) ?? null;
  const isApproved = post.status === "published";
  return {
    id: post.id,
    slug: post.slug,
    content: post.content ?? "",
    emotion,
    media_type: mediaType as V1TestimonialShape["media_type"],
    media_url: mediaUrl,
    image_url: post.featured_image_url ?? null,
    video_url: (seo.video_url as string | null | undefined) ?? null,
    podcast_url: (seo.podcast_url as string | null | undefined) ?? null,
    created_at: post.created_at,
    author_persona_id: post.author_persona_id ?? null,
    published: isApproved,
    is_approved: isApproved,
    show_on_home: Boolean(seo.show_on_home),
    status: _testimonialStatusFromPost(post.status),
  };
}

/** Convert a v2 CmsPost into the v1 AnnouncementRead shape the admin UI expects. */
export function postToAnnouncement(post: CmsPostWithTaxonomies): V1AnnouncementShape {
  const seo = (post.seo_json ?? {}) as Record<string, unknown>;
  const isActive = post.status === "published";
  return {
    id: post.id,
    slug: post.slug,
    title: post.title ?? "",
    content: post.content ?? "",
    category: (seo.category as string) || "announcements",
    image_url: post.featured_image_url ?? null,
    is_active: isActive,
    is_featured: Boolean(seo.is_featured),
    status: post.status ?? "draft",
    created_at: post.created_at,
    published_at: post.published_at ?? undefined,
  };
}

/** Save a testimonial edit via v2, mapping v1 flat fields back to content+seo_json. */
export async function saveTestimonial(
  siteKey: string,
  slug: string,
  data: {
    content: string;
    emotion: string;
    media_type: string;
    media_url?: string | null;
    image_url?: string | null;
    video_url?: string | null;
    podcast_url?: string | null;
    show_on_home?: boolean;
    status?: string;
  },
  token?: string | null,
): Promise<V1TestimonialShape> {
  const post = await patchCmsPostByCategory(
    siteKey,
    slug,
    "testimonials",
    {
      content: data.content,
      featured_image_url: data.media_type === "image" ? (data.image_url ?? data.media_url ?? null) : null,
      status: data.status === "approved" ? "published" : data.status === "archived" ? "archived" : "draft",
      seo_json: {
        emotion: data.emotion,
        media_type: data.media_type,
        media_url: data.media_type === "text" ? null : (data.media_url ?? null),
        image_url: data.media_type === "image" ? (data.image_url ?? null) : null,
        video_url: data.media_type === "video" ? (data.video_url ?? null) : null,
        podcast_url: data.media_type === "podcast" ? (data.podcast_url ?? null) : null,
        show_on_home: data.show_on_home ?? false,
      },
    },
    token,
  );
  return postToTestimonial(post);
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

export type CmsReadinessSeverity = "info" | "warning" | "error";
export type CmsReadinessCapabilityStatus = "ready" | "partial" | "attention";

export interface CmsReadinessMetric {
  key: string;
  label: string;
  value: number;
  href: string | null;
}

export interface CmsReadinessIssue {
  code: string;
  severity: CmsReadinessSeverity;
  title: string;
  detail: string;
  count: number;
  href: string | null;
}

export interface CmsReadinessCapability {
  key: string;
  label: string;
  status: CmsReadinessCapabilityStatus;
  detail: string;
  href: string | null;
}

export interface CmsReadinessResponse {
  site_key: string;
  score: number;
  generated_at: string;
  metrics: CmsReadinessMetric[];
  issues: CmsReadinessIssue[];
  capabilities: CmsReadinessCapability[];
}

export async function getCmsReadiness(
  siteKey: string,
  token?: string | null,
): Promise<CmsReadinessResponse> {
  return apiFetch<CmsReadinessResponse>(`/cms/v2/sites/${siteKey}/readiness`, {
    token,
    cache: "no-store",
  });
}

export interface PageAnalytics {
  page_key: string;
  total_views: number;
  days: number;
  daily_views: Array<{ date: string; views: number }>;
}

export async function getPageAnalytics(
  pageKey: string,
  days: number = 30,
  token?: string | null,
): Promise<PageAnalytics> {
  return apiFetch<PageAnalytics>(`/cms/v2/analytics/${encodeURIComponent(pageKey)}?days=${days}`, {
    token,
    cache: "no-store",
  });
}

// ── Public testimonials (replaces GET /cms/testimonials) ───────────────────
// The public v2 posts endpoint returns only status=="published" rows and uses
// the CmsPublicPost shape (no numeric id, no status; seo_json holds the v1
// flat fields). These adapters restore the shape the public/community pages
// consumed from the v1 shim.

export interface PublicTestimonial {
  id: string;
  slug: string;
  content: string;
  emotion: string;
  media_type?: "text" | "image" | "video" | "podcast" | string;
  media_url?: string | null;
  image_url?: string | null;
  video_url?: string | null;
  podcast_url?: string | null;
  author_name?: string | null;
  author_username?: string | null;
  is_approved?: boolean;
  show_on_home?: boolean;
  created_at?: string;
  published_at?: string | null;
}

export function publicPostToTestimonial(post: CmsPublicPost): PublicTestimonial {
  const seo = (post.seo_json ?? {}) as Record<string, unknown>;
  return {
    id: post.slug,
    slug: post.slug,
    content: post.content ?? "",
    emotion: (seo.emotion as string) || "General",
    media_type: (seo.media_type as string) || "text",
    media_url: (seo.media_url as string | null | undefined) ?? null,
    image_url: post.featured_image_url ?? (seo.image_url as string | null | undefined) ?? null,
    video_url: (seo.video_url as string | null | undefined) ?? null,
    podcast_url: (seo.podcast_url as string | null | undefined) ?? null,
    author_name: post.author_name ?? null,
    author_username: post.author_name ?? null,
    is_approved: true,
    show_on_home: Boolean(seo.show_on_home),
    created_at: post.published_at ?? undefined,
    published_at: post.published_at,
  };
}

/** List published testimonials via the public v2 endpoint (no token required). */
export async function listPublicTestimonials(
  siteKey: string,
  options?: { skip?: number; limit?: number },
): Promise<PublicTestimonial[]> {
  const posts = await getCmsPublicPosts(siteKey, { category_slug: "testimonials", ...options });
  return Array.isArray(posts) ? posts.map(publicPostToTestimonial) : [];
}

// ── Announcement wrappers (replaces GET/POST /cms/announcements, /admin/announcements) ──

/** High-level wrapper: list announcements via v2, returning v1 AnnouncementRead shape. */
export async function listAnnouncements(
  siteKey: string,
  options?: { status?: string; include_archived?: boolean; skip?: number; limit?: number },
  token?: string | null,
): Promise<V1AnnouncementShape[]> {
  const posts = await listCmsPostsByCategory(siteKey, "announcements", options, token);
  return posts.map(postToAnnouncement);
}

/** Toggle announcement status between draft/published/archived via v2. */
export async function setAnnouncementStatus(
  siteKey: string,
  slug: string,
  v1Status: "draft" | "active" | "archived",
  token?: string | null,
): Promise<V1AnnouncementShape> {
  const v2Status = v1Status === "active" ? "published" : v1Status === "archived" ? "archived" : "draft";
  const post = await patchCmsPostByCategory(siteKey, slug, "announcements", { status: v2Status }, token);
  return postToAnnouncement(post);
}

// ── Public announcements (replaces GET /cms/announcements) ─────────────────

export interface PublicAnnouncement {
  id: string;
  slug: string;
  title: string;
  content: string;
  category: string;
  image_url?: string | null;
  is_featured: boolean;
  created_at?: string;
  published_at?: string | null;
}

export function publicPostToAnnouncement(post: CmsPublicPost): PublicAnnouncement {
  const seo = (post.seo_json ?? {}) as Record<string, unknown>;
  return {
    id: post.slug,
    slug: post.slug,
    title: post.title,
    content: post.content ?? "",
    category: (seo.category as string) || "announcements",
    image_url: post.featured_image_url ?? null,
    is_featured: Boolean(seo.is_featured),
    created_at: post.published_at ?? undefined,
    published_at: post.published_at,
  };
}

/** List published announcements via the public v2 endpoint (no token required). */
export async function listPublicAnnouncements(
  siteKey: string,
  options?: { skip?: number; limit?: number },
): Promise<PublicAnnouncement[]> {
  const posts = await getCmsPublicPosts(siteKey, { category_slug: "announcements", ...options });
  return Array.isArray(posts) ? posts.map(publicPostToAnnouncement) : [];
}
