// React hook for CMS v2 public pages from a client component.
//
// Pattern mirrors `frontend/src/hooks/useWikiDocument`: initial render
// resolves to the bootstrapped page (SSR), then refetches via `useEffect`
// only when the page is missing from the bootstrap. Call sites use
// optional chaining (e.g. `page?.blocks?.hero`) to render gracefully.
//
// Two design notes that shaped this implementation:
//
// 1. Why a React hook instead of a plain async fetcher: every page
//    under `frontend/src/app/(public)/*` that consumes this hook is
//    marked `"use client"` and uses interactive hooks
//    (useState/useEffect/useMemo). A client component cannot `await`
//    at top level, so the original async fetcher signature produced
//    a TS2339 error
//    (`Property 'blocks' does not exist on type 'Promise<CmsPublicPage>'`).
//    Returning `CmsPublicPage | null` synchronously fixes that and keeps
//    each page's existing optional-chaining fallbacks
//    (e.g. `hero?.eyebrow || "BIENVENIDOS"`) intact.
//
// 2. Why we read the bootstrap from the React context instead of
//    `window.__CCF_PUBLIC_BOOTSTRAP__`: the context is fed by
//    `PublicBootstrapProvider` in the server layout, so it holds the same
//    pages on the server AND on the client. Reading `window` directly
//    returned `null` during SSR (no `window`), so the server rendered an
//    empty tree while the client hydrated with real data → hydration
//    mismatch (React error #418) and empty SSR (no SEO). The context keeps
//    both renders identical.
//
// 3. Why we derive `blocks` from `sections`: the API
//    (`/cms/v2/public/sites/{site_key}/pages/{slug}`) returns a list of
//    `CmsSection` rows. The page files under `(public)/*` address
//    sections by friendly key (`page?.blocks?.hero`, `page?.blocks?.events`)
//    rather than iterating the array. Without this derivation, those
//    accesses typed-error out and silently fall back to sentinel defaults.
//    Indexing by `section_key` exposes the raw `props_json` of each
//    section, matching the call-site access pattern.
import { useEffect, useMemo, useState } from "react";
import { getCmsPublicPage } from "@/lib/cms/v2";
import { buildCmsPageBlocks } from "@/lib/cms/pageBlocks";
import { usePublicBootstrap } from "@/components/public/PublicBootstrapProvider";
import { SITE_KEY } from "@/lib/site-config";
import type { CmsPublicPage } from "@/types/cms-v2";

export function useCmsV2Page(slug: string): CmsPublicPage | null {
  const bootstrap = usePublicBootstrap();

  // useMemo sobre el bootstrap del contexto: la página bootstrapeada se deriva
  // de forma determinista (mismo objeto para misma referencia de bootstrap),
  // evitando el loop infinito ("Maximum update depth exceeded") que ocurría
  // cuando se derivaba la página del bootstrap en cada render sin memoizar
  // (referencia nueva → setPage → re-render → objeto nuevo → loop).
  const bootstrappedPage = useMemo(() => {
    const page = bootstrap?.pages?.[slug] ?? null;
    if (!page) return null;
    return { ...page, blocks: buildCmsPageBlocks(page.sections) };
  }, [bootstrap, slug]);

  const [page, setPage] = useState<CmsPublicPage | null>(bootstrappedPage);

  useEffect(() => {
    if (bootstrappedPage) {
      setPage(bootstrappedPage);
      return;
    }

    let alive = true;
    // Fallback para slugs ausentes del bootstrap: fetch directo. Silent error
    // handling — pages render sentinel defaults when CMS data is absent, so a
    // fetch failure must not break the UI.
    getCmsPublicPage(SITE_KEY, slug)
      .then((p) => {
        if (!alive) return;
        setPage({ ...p, blocks: buildCmsPageBlocks(p.sections) });
      })
      .catch(() => {
        /* fallback handled by call-site defaults */
      });
    return () => {
      alive = false;
    };
  }, [slug, bootstrappedPage]);

  return page;
}
