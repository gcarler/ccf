import { buildCmsPageBlocks } from "@/lib/cms/pageBlocks";
import type { CmsPublicMenu, CmsPublicPage, CmsTheme } from "@/types/cms-v2";

export type PublicBootstrapTheme = Pick<CmsTheme, "name" | "tokens_json">;

export interface PublicBootstrapState {
  theme?: PublicBootstrapTheme | null;
  menus?: Record<string, CmsPublicMenu | null>;
  pages?: Record<string, CmsPublicPage | null>;
  footerPage?: CmsPublicPage | null;
}

declare global {
  interface Window {
    __CCF_PUBLIC_BOOTSTRAP__?: PublicBootstrapState;
  }
}

export function readPublicBootstrap(): PublicBootstrapState | null {
  if (typeof window === "undefined") return null;
  return window.__CCF_PUBLIC_BOOTSTRAP__ || null;
}

export function readBootstrappedPage(slug: string): CmsPublicPage | null {
  const page = readPublicBootstrap()?.pages?.[slug] ?? null;
  if (!page) return null;
  return {
    ...page,
    blocks: buildCmsPageBlocks(page.sections),
  };
}

export function readBootstrappedMenu(menuKey: string): CmsPublicMenu | null {
  return readPublicBootstrap()?.menus?.[menuKey] ?? null;
}

export function readBootstrappedTheme(): PublicBootstrapTheme | null {
  return readPublicBootstrap()?.theme ?? null;
}

export function readBootstrappedFooterPage(): CmsPublicPage | null {
  return readPublicBootstrap()?.footerPage ?? null;
}

export function serializePublicBootstrap(state: PublicBootstrapState): string {
  return JSON.stringify(state).replace(/</g, "\\u003c");
}
