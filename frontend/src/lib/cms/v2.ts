import { apiFetch } from "@/lib/http";
import { CmsMenu, CmsMenuItem, CmsPublicMenu, CmsSite, CmsTheme } from "@/types/cms-v2";

export async function listCmsSites(token?: string | null) {
  return apiFetch<CmsSite[]>("/cms/v2/sites", { token });
}

export async function listCmsThemes(siteKey: string, token?: string | null) {
  return apiFetch<CmsTheme[]>(`/cms/v2/sites/${siteKey}/themes`, { token });
}

export async function createCmsTheme(
  siteKey: string,
  payload: { name: string; tokens_json: Record<string, string>; is_active?: boolean },
  token?: string | null,
) {
  return apiFetch<CmsTheme>(`/cms/v2/sites/${siteKey}/themes`, {
    method: "POST",
    token,
    body: payload,
  });
}

export async function activateCmsTheme(siteKey: string, themeId: number, token?: string | null) {
  return apiFetch<CmsTheme>(`/cms/v2/sites/${siteKey}/themes/${themeId}/activate`, {
    method: "POST",
    token,
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
  payload: Partial<Pick<CmsMenuItem, "label" | "href" | "target" | "is_external" | "visibility" | "sort_order">>,
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

export async function getCmsPublicMenu(siteKey: string, menuKey: string) {
  return apiFetch<CmsPublicMenu>(`/cms/v2/public/sites/${siteKey}/menus/${menuKey}`);
}

export async function listCmsPages(siteKey: string, token?: string | null) {
  return apiFetch<Array<{ id: number; slug: string; title: string; status: string }>>(
    `/cms/v2/sites/${siteKey}/pages`,
    { token },
  );
}

export async function createCmsPage(
  siteKey: string,
  payload: { slug: string; title: string; status?: string; seo_json?: Record<string, unknown> },
  token?: string | null,
) {
  return apiFetch<{ id: number; slug: string; title: string; status: string }>(`/cms/v2/sites/${siteKey}/pages`, {
    method: "POST",
    token,
    body: payload,
  });
}

export async function listCmsSections(siteKey: string, slug: string, token?: string | null) {
  return apiFetch<Array<{ id: number; type: string; props_json: Record<string, unknown>; sort_order: number; is_visible: boolean }>>(
    `/cms/v2/sites/${siteKey}/pages/${slug}/sections`,
    { token },
  );
}

export async function createCmsSection(
  siteKey: string,
  slug: string,
  payload: { type: string; props_json: Record<string, unknown>; sort_order?: number; is_visible?: boolean },
  token?: string | null,
) {
  return apiFetch<{ id: number; type: string }>(`/cms/v2/sites/${siteKey}/pages/${slug}/sections`, {
    method: "POST",
    token,
    body: payload,
  });
}
