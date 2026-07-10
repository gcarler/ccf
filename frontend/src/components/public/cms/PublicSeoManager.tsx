"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { SITE_KEY } from "@/lib/site-config";
import SeoHead from "./SeoHead";

const SITE_NAME = process.env.NEXT_PUBLIC_SITE_NAME ?? "Mi Comunidad";
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

const ROUTE_META_MAP: Record<string, { slug: string }> = {
    "/":                  { slug: "home" },
    "/nosotros":          { slug: "about" },
    "/pastores":          { slug: "pastors" },
    "/conocer-a-jesus":   { slug: "discover" },
    "/eventos":           { slug: "events" },
    "/predicas":          { slug: "sermons" },
    "/cursos":            { slug: "courses" },
    "/sedes":             { slug: "locations" },
    "/boletin":           { slug: "newsletter" },
    "/testimonios":       { slug: "testimonials" },
    "/privacidad":        { slug: "privacy" },
};

function matchRoute(pathname: string): { slug: string } | null {
    if (ROUTE_META_MAP[pathname]) return ROUTE_META_MAP[pathname];
    if (pathname.startsWith("/pastores/")) return { slug: "pastores" };
    if (pathname.startsWith("/cursos/")) return { slug: "cursos" };
    if (pathname.startsWith("/testimonios/")) return { slug: "testimonios" };
    return null;
}

interface CmsSeoData {
    title?: string;
    description?: string;
    robots_meta?: string;
    canonical_url?: string;
    json_ld?: Record<string, unknown> | null;
    breadcrumb_json_ld?: Record<string, unknown> | null;
}

export default function PublicSeoManager() {
    const pathname = usePathname() || "/";
    const match = matchRoute(pathname);
    const [cmsSeo, setCmsSeo] = useState<CmsSeoData | null>(null);

    useEffect(() => {
        if (!match) return;

        const controller = new AbortController();
        const url = `${API_BASE}/cms/v2/public/sites/${SITE_KEY}/pages/${match.slug}`;

        fetch(url, { signal: controller.signal })
            .then((r) => (r.ok ? r.json() : null))
            .then((data) => {
                if (!data) return;
                const seo = data.seo_json && typeof data.seo_json === "object" ? data.seo_json : {};
                setCmsSeo({
                    title: typeof seo.meta_title === "string" ? seo.meta_title : undefined,
                    description: typeof seo.meta_description === "string" ? seo.meta_description : undefined,
                    robots_meta: typeof seo.robots_meta === "string" ? seo.robots_meta : undefined,
                    canonical_url: data.canonical_url ?? undefined,
                    json_ld: data.json_ld ?? null,
                    breadcrumb_json_ld: data.breadcrumb_json_ld ?? null,
                });
            })
            .catch(() => {});

        return () => controller.abort();
    }, [match?.slug]);

    if (!match) return null;

    const fallbackTitle = cmsSeo?.title || SITE_NAME;
    const fallbackDescription = cmsSeo?.description || "";

    return (
        <SeoHead
            slug={match.slug}
            fallbackTitle={fallbackTitle}
            fallbackDescription={fallbackDescription}
            robotsMeta={cmsSeo?.robots_meta}
            canonicalUrl={cmsSeo?.canonical_url}
            jsonLd={cmsSeo?.json_ld}
        />
    );
}
