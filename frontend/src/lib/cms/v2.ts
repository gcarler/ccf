import { apiFetch } from "@/lib/http";
import { CmsMenu, CmsMenuItem, CmsPage, CmsPageVersion, CmsPublishLog, CmsPublicMenu, CmsPublicPage, CmsSection, CmsSite, CmsTheme } from "@/types/cms-v2";

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

export async function deleteCmsTheme(siteKey: string, themeId: number, token?: string | null) {
  await apiFetch<void>(`/cms/v2/sites/${siteKey}/themes/${themeId}`, {
    method: "DELETE",
    token,
  });
}

export async function activateCmsTheme(siteKey: string, themeId: number, token?: string | null) {
  return apiFetch<CmsTheme>(`/cms/v2/sites/${siteKey}/themes/${themeId}/activate`, {
    method: "POST",
    token,
  });
}

export async function patchCmsTheme(
  siteKey: string,
  themeId: number,
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
    parent_id?: number | null;
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
  itemId: number,
  payload: Partial<Pick<CmsMenuItem, "label" | "href" | "target" | "is_external" | "visibility" | "sort_order" | "parent_id">>,
  token?: string | null,
) {
  return apiFetch<CmsMenuItem>(`/cms/v2/sites/${siteKey}/menus/${menuKey}/items/${itemId}`, {
    method: "PATCH",
    token,
    body: payload,
  });
}

export async function deleteCmsMenuItem(siteKey: string, menuKey: string, itemId: number, token?: string | null) {
  await apiFetch<void>(`/cms/v2/sites/${siteKey}/menus/${menuKey}/items/${itemId}`, {
    method: "DELETE",
    token,
  });
}

export async function reorderCmsMenuItems(
  siteKey: string,
  menuKey: string,
  items: Array<{ id: number; parent_id: number | null; sort_order: number }>,
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
  return apiFetch<CmsPage[]>(`/cms/v2/sites/${siteKey}/pages`, { token });
}

export async function createCmsPage(
  siteKey: string,
  payload: { slug: string; title: string; status?: string; seo_json?: Record<string, unknown> },
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
  payload: { slug?: string; title?: string; status?: string; seo_json?: Record<string, unknown> },
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

export async function listCmsSections(siteKey: string, slug: string, token?: string | null) {
  return apiFetch<CmsSection[]>(`/cms/v2/sites/${siteKey}/pages/${slug}/sections`, { token });
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
  sectionId: number,
  payload: { type?: string; props_json?: Record<string, unknown>; sort_order?: number; is_visible?: boolean; status?: string },
  token?: string | null,
) {
  return apiFetch<CmsSection>(`/cms/v2/sites/${siteKey}/pages/${slug}/sections/${sectionId}`, {
    method: "PATCH",
    token,
    body: payload,
  });
}

export async function deleteCmsSection(siteKey: string, slug: string, sectionId: number, token?: string | null) {
  await apiFetch<void>(`/cms/v2/sites/${siteKey}/pages/${slug}/sections/${sectionId}`, {
    method: "DELETE",
    token,
  });
}

export async function reorderCmsSections(
  siteKey: string,
  slug: string,
  items: Array<{ id: number; sort_order: number }>,
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

export async function listCmsPageVersions(siteKey: string, slug: string, token?: string | null) {
  return apiFetch<CmsPageVersion[]>(`/cms/v2/sites/${siteKey}/pages/${slug}/versions`, { token });
}

export async function listCmsPagePublishLog(siteKey: string, slug: string, token?: string | null) {
  return apiFetch<CmsPublishLog[]>(`/cms/v2/sites/${siteKey}/pages/${slug}/publish-log`, { token });
}

export async function rollbackCmsPageVersion(siteKey: string, slug: string, versionId: number, token?: string | null) {
  return apiFetch<CmsPage>(`/cms/v2/sites/${siteKey}/pages/${slug}/rollback/${versionId}`, {
    method: "POST",
    token,
  });
}

export async function getCmsPublicPage(siteKey: string, slug: string) {
  return apiFetch<CmsPublicPage>(`/cms/v2/public/sites/${siteKey}/pages/${slug}`);
}

export async function getCmsPagePreview(siteKey: string, slug: string, token?: string | null) {
  return apiFetch<CmsPublicPage>(`/cms/v2/sites/${siteKey}/pages/${slug}/preview`, { token, cache: "no-store" });
}
