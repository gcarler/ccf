// React hook for CMS v2 public pages from a client component.
//
// Pattern mirrors `frontend/src/hooks/useWikiDocument`: initial render
// returns `null`, then resolves to the live page via `useEffect`. Call
// sites use optional chaining (e.g. `page?.blocks?.hero`) to render
// gracefully during the first paint before CMS data arrives.
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
// 2. Why we derive `blocks` from `sections`: the API
//    (`/cms/v2/public/sites/{site_key}/pages/{slug}`) returns a list of
//    `CmsSection` rows. The 13 page-specific files under `(public)/*`
//    address sections by friendly key (`page?.blocks?.hero`,
//    `page?.blocks?.events`) rather than iterating the array. Without
//    this derivation, those accesses typed-error out
//    (`Property 'blocks' does not exist on type 'CmsPublicPage'`),
//    and at runtime they silently fall back to sentinel defaults.
//    Indexing by `section_key` exposes the raw `props_json` of each
//    section, matching the call-site access pattern.
import { useEffect, useState } from "react";
import { getCmsPublicPage } from "@/lib/cms/v2";
import { SITE_KEY } from "@/lib/site-config";
import type { CmsPublicPage } from "@/types/cms-v2";

export function useCmsV2Page(slug: string): CmsPublicPage | null {
  const [page, setPage] = useState<CmsPublicPage | null>(null);

  useEffect(() => {
    let alive = true;
    // Silent error handling: pages render sentinel defaults when CMS data is
    // absent, so a fetch failure must not break the UI.
    getCmsPublicPage(SITE_KEY, slug)
      .then((p) => {
        if (!alive) return;
        // Derive a `blocks` index keyed by `section_key` so call sites can do
        // `page?.blocks?.hero?.eyebrow` instead of hunting the array. Last
        // section with a duplicate key wins (CMS schema reserves uniqueness).
        const blocks: Record<string, Record<string, unknown>> = {};
        for (const section of p.sections ?? []) {
          if (section.section_key) {
            blocks[section.section_key] = section.props_json ?? {};
          }
        }
        setPage({ ...p, blocks });
      })
      .catch(() => {
        /* fallback handled by call-site defaults */
      });
    return () => {
      alive = false;
    };
  }, [slug]);

  return page;
}
