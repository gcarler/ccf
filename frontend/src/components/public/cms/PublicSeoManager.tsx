"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname } from "next/navigation";
import { SITE_KEY } from "@/lib/site-config";
import { apiFetch } from "@/lib/http";
import { CmsPublicPage, CmsPublicPost } from "@/types/cms-v2";
import SeoHead from "./SeoHead";
import { usePublicBootstrap } from "../PublicBootstrapProvider";

const SITE_NAME = process.env.NEXT_PUBLIC_SITE_NAME ?? "Mi Comunidad";

interface CmsSeoData {
    title?: string;
    description?: string;
    image?: string;
    robots_meta?: string;
    canonical_url?: string;
    json_ld?: Record<string, unknown> | null;
    breadcrumb_json_ld?: Record<string, unknown> | null;
}

type RouteKind = "page" | "blog" | "post" | "category" | "tag" | "fallback";

type RouteDescriptor = {
    kind: RouteKind;
    slug?: string;
    fallbackTitle: string;
    fallbackDescription: string;
    fallbackType: "website" | "article";
};

const ROUTE_META_MAP: Record<string, { slug: string; fallbackTitle: string }> = {
    "/":                { slug: "home", fallbackTitle: SITE_NAME },
    "/nosotros":        { slug: "about", fallbackTitle: "Nosotros" },
    "/pastores":        { slug: "pastors", fallbackTitle: "Pastores" },
    "/conocer-a-jesus": { slug: "discover", fallbackTitle: "Conocer a Jesús" },
    "/eventos":         { slug: "events", fallbackTitle: "Eventos" },
    "/predicas":        { slug: "sermons", fallbackTitle: "Prédicas" },
    "/cursos":          { slug: "courses", fallbackTitle: "Cursos" },
    "/sedes":           { slug: "locations", fallbackTitle: "Sedes" },
    "/boletin":         { slug: "newsletter", fallbackTitle: "Boletín" },
    "/testimonios":     { slug: "testimonials", fallbackTitle: "Testimonios" },
    "/privacy":         { slug: "privacy", fallbackTitle: "Privacidad" },
};

function humanizeSlug(slug: string) {
    return decodeURIComponent(slug)
        .replace(/[-_]+/g, " ")
        .split(" ")
        .filter(Boolean)
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" ");
}

function matchRoute(pathname: string): RouteDescriptor {
    const mapped = ROUTE_META_MAP[pathname];
    if (mapped) {
        return {
            kind: "page",
            slug: mapped.slug,
            fallbackTitle: mapped.fallbackTitle,
            fallbackDescription: `Contenido oficial de ${mapped.fallbackTitle} en ${SITE_NAME}.`,
            fallbackType: "website",
        };
    }

    if (pathname === "/blog") {
        return {
            kind: "blog",
            slug: "blog",
            fallbackTitle: "Blog",
            fallbackDescription: `Publicaciones y recursos del blog de ${SITE_NAME}.`,
            fallbackType: "website",
        };
    }

    if (pathname.startsWith("/blog/")) {
        const slug = pathname.replace(/^\/blog\//, "").split("/")[0] || "";
        return {
            kind: "post",
            slug,
            fallbackTitle: "Blog",
            fallbackDescription: `Artículo del blog de ${SITE_NAME}.`,
            fallbackType: "article",
        };
    }

    if (pathname.startsWith("/categoria/")) {
        const slug = pathname.replace(/^\/categoria\//, "").split("/")[0] || "";
        const name = humanizeSlug(slug) || "Categoría";
        return {
            kind: "category",
            slug,
            fallbackTitle: `Categoría: ${name}`,
            fallbackDescription: `Artículos publicados en la categoría ${name}.`,
            fallbackType: "website",
        };
    }

    if (pathname.startsWith("/etiqueta/")) {
        const slug = pathname.replace(/^\/etiqueta\//, "").split("/")[0] || "";
        const name = humanizeSlug(slug) || "Etiqueta";
        return {
            kind: "tag",
            slug,
            fallbackTitle: `Etiqueta: ${name}`,
            fallbackDescription: `Artículos publicados con la etiqueta ${name}.`,
            fallbackType: "website",
        };
    }

    if (pathname.startsWith("/pastores/")) {
        return {
            kind: "page",
            slug: "pastors",
            fallbackTitle: "Pastores",
            fallbackDescription: `Contenido oficial de Pastores en ${SITE_NAME}.`,
            fallbackType: "website",
        };
    }

    if (pathname.startsWith("/cursos/")) {
        return {
            kind: "page",
            slug: "courses",
            fallbackTitle: "Cursos",
            fallbackDescription: `Contenido oficial de Cursos en ${SITE_NAME}.`,
            fallbackType: "website",
        };
    }

    if (pathname.startsWith("/testimonios/")) {
        return {
            kind: "page",
            slug: "testimonials",
            fallbackTitle: "Testimonios",
            fallbackDescription: `Contenido oficial de Testimonios en ${SITE_NAME}.`,
            fallbackType: "website",
        };
    }

    return {
        kind: "fallback",
        fallbackTitle: SITE_NAME,
        fallbackDescription: `Sitio oficial de ${SITE_NAME}.`,
        fallbackType: "website",
    };
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null;
}

function normalizeSeoJson(data: { seo_json?: unknown; canonical_url?: unknown; json_ld?: unknown; breadcrumb_json_ld?: unknown }) {
    const seo = isRecord(data.seo_json) ? data.seo_json : {};
    return {
        title: typeof seo.meta_title === "string" ? seo.meta_title : undefined,
        description: typeof seo.meta_description === "string" ? seo.meta_description : undefined,
        image: typeof seo.meta_image === "string" ? seo.meta_image : undefined,
        robots_meta: typeof seo.robots_meta === "string" ? seo.robots_meta : undefined,
        canonical_url: typeof data.canonical_url === "string" ? data.canonical_url : undefined,
        json_ld: isRecord(data.json_ld) ? data.json_ld : null,
        breadcrumb_json_ld: isRecord(data.breadcrumb_json_ld) ? data.breadcrumb_json_ld : null,
    } satisfies CmsSeoData;
}

async function fetchPublicPage(slug: string, signal: AbortSignal): Promise<CmsSeoData | null> {
    try {
        const page = await apiFetch<CmsPublicPage>(`/cms/v2/public/sites/${SITE_KEY}/pages/${slug}`, {
            signal,
            silent: true,
        });
        const seo = normalizeSeoJson(page);
        return {
            ...seo,
            title: seo.title || page.title,
        };
    } catch {
        return null;
    }
}

async function fetchPublicPost(slug: string, signal: AbortSignal): Promise<CmsSeoData | null> {
    try {
        const post = await apiFetch<CmsPublicPost>(`/cms/v2/public/sites/${SITE_KEY}/posts/${slug}`, {
            signal,
            silent: true,
        });
        const seo = normalizeSeoJson(post);
        return {
            ...seo,
            title: seo.title || post.title,
        };
    } catch {
        return null;
    }
}

async function fetchArchiveSeo(
    params: { category_slug?: string; tag_slug?: string },
    signal: AbortSignal,
    fallbackTitle: string,
    fallbackDescription: string,
): Promise<CmsSeoData> {
    try {
        const response = await apiFetch<CmsPublicPost[] | { items?: CmsPublicPost[] }>(
            `/cms/v2/public/sites/${SITE_KEY}/posts`,
            {
                signal,
                silent: true,
                query: params,
            },
        );

        const posts = Array.isArray(response)
            ? response
            : "items" in response && Array.isArray(response.items)
                ? response.items
                : [];
        const first = posts[0];
        if (!first) {
            return {
                title: fallbackTitle,
                description: fallbackDescription,
                canonical_url: undefined,
                json_ld: null,
                breadcrumb_json_ld: null,
            };
        }

        const collectionName =
            params.category_slug && Array.isArray(first.categories)
                ? first.categories.find((category) => category.slug === params.category_slug)?.name
                : params.tag_slug && Array.isArray(first.tags)
                    ? first.tags.find((tag) => tag.slug === params.tag_slug)?.name
                    : undefined;

        return {
            title: collectionName ? `${collectionName} | Blog` : fallbackTitle,
            description: fallbackDescription,
            canonical_url: undefined,
            json_ld: null,
            breadcrumb_json_ld: null,
        };
    } catch {
        return {
            title: fallbackTitle,
            description: fallbackDescription,
            canonical_url: undefined,
            json_ld: null,
            breadcrumb_json_ld: null,
        };
    }
}

export default function PublicSeoManager() {
    const pathname = usePathname() || "/";
    const route = matchRoute(pathname);
    const bootstrap = usePublicBootstrap();
    const bootstrappedPage = route.kind === "page" ? bootstrap?.pages?.[route.slug || ""] ?? null : route.kind === "blog" ? bootstrap?.pages?.[route.slug || "blog"] ?? null : null;
    const initialSeo = useMemo(() => {
        if (!bootstrappedPage) return null;
        const seo = normalizeSeoJson(bootstrappedPage);
        return {
            ...seo,
            title: seo.title || bootstrappedPage.title,
        };
    }, [bootstrappedPage]);
    const [cmsSeo, setCmsSeo] = useState<CmsSeoData | null>(initialSeo);

    useEffect(() => {
        let active = true;
        const controller = new AbortController();
        if (bootstrappedPage) {
            setCmsSeo(initialSeo);
            return () => {
                active = false;
                controller.abort();
            };
        }

        setCmsSeo(null);

        async function loadSeo() {
            let nextSeo: CmsSeoData | null = null;

            if (route.kind === "page") {
                nextSeo = await fetchPublicPage(route.slug || "", controller.signal);
            } else if (route.kind === "blog") {
                nextSeo = await fetchPublicPage(route.slug || "blog", controller.signal);
            } else if (route.kind === "post") {
                nextSeo = route.slug ? await fetchPublicPost(route.slug, controller.signal) : null;
            } else if (route.kind === "category") {
                nextSeo = await fetchArchiveSeo(
                    { category_slug: route.slug },
                    controller.signal,
                    route.fallbackTitle,
                    route.fallbackDescription,
                );
            } else if (route.kind === "tag") {
                nextSeo = await fetchArchiveSeo(
                    { tag_slug: route.slug },
                    controller.signal,
                    route.fallbackTitle,
                    route.fallbackDescription,
                );
            }

            if (!active) return;
            setCmsSeo(nextSeo);
        }

        loadSeo().catch(() => {});

        return () => {
            active = false;
            controller.abort();
        };
    }, [pathname, route.kind, route.slug, route.fallbackTitle, route.fallbackDescription, route.fallbackType, bootstrappedPage, initialSeo]);

    const fallbackTitle = cmsSeo?.title || route.fallbackTitle;
    const fallbackDescription = cmsSeo?.description || route.fallbackDescription;

    return (
        <SeoHead
            slug={route.slug}
            fallbackTitle={fallbackTitle}
            fallbackDescription={fallbackDescription}
            robotsMeta={cmsSeo?.robots_meta}
            canonicalUrl={cmsSeo?.canonical_url}
            jsonLd={cmsSeo?.json_ld}
            breadcrumbJsonLd={cmsSeo?.breadcrumb_json_ld}
            fallbackImage={cmsSeo?.image}
            fallbackType={route.fallbackType}
        />
    );
}
