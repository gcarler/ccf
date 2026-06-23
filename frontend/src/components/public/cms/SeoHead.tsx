"use client";

import { useEffect } from "react";
import { useContentBlock } from "@/hooks/useContent";
import { SITE_KEY, SITE_NAME, SITE_URL } from "@/lib/site-config";

interface SeoMeta {
    title?: string;
    description?: string;
    image?: string;
    type?: string;
    url?: string;
    canonical?: string;
    robots?: string;
    keywords?: string;
    author?: string;
    twitter_card?: string;
    twitter_site?: string;
    twitter_creator?: string;
    locale?: string;
    site_name?: string;
    article_published?: string;
    article_modified?: string;
    no_index?: boolean;
    no_follow?: boolean;
}

function setMeta(attr: string, key: string, content: string) {
    if (!content) return;
    let el = document.querySelector(`meta[${attr}="${key}"]`) as HTMLMetaElement | null;
    if (!el) {
        el = document.createElement("meta");
        el.setAttribute(attr, key);
        document.head.appendChild(el);
    }
    el.setAttribute("content", content);
}

function setLink(rel: string, href: string) {
    if (!href) return;
    let el = document.querySelector(`link[rel="${rel}"]`) as HTMLLinkElement | null;
    if (!el) {
        el = document.createElement("link");
        el.setAttribute("rel", rel);
        document.head.appendChild(el);
    }
    el.setAttribute("href", href);
}

interface SeoHeadProps {
    slug: string;
    fallbackTitle?: string;
    fallbackDescription?: string;
    fallbackImage?: string;
    fallbackType?: string;
}

export default function SeoHead({
    slug,
    fallbackTitle,
    fallbackDescription,
    fallbackImage,
    fallbackType = "website",
}: SeoHeadProps) {
    const { data: metaContent } = useContentBlock(`${SITE_KEY}_${slug}_meta`);

    useEffect(() => {
        const meta = (metaContent?.parsed && typeof metaContent.parsed === "object" && !Array.isArray(metaContent.parsed))
            ? metaContent.parsed as SeoMeta
            : {};

        const title = meta.title || fallbackTitle || SITE_NAME;
        const description = meta.description || fallbackDescription || "";
        const image = meta.image || fallbackImage || "";
        const type = meta.type || fallbackType;
        const canonical = meta.canonical || (typeof window !== "undefined" ? window.location.href : "");
        const robotsDirectives = [
            meta.no_index ? "noindex" : "index",
            meta.no_follow ? "nofollow" : "follow",
        ].join(", ");
        const robots = meta.robots || robotsDirectives;
        const keywords = meta.keywords || "";
        const author = meta.author || SITE_NAME;
        const twitterCard = meta.twitter_card || "summary_large_image";
        const twitterSite = meta.twitter_site || "";
        const twitterCreator = meta.twitter_creator || "";
        const locale = meta.locale || "es_CO";
        const siteName = meta.site_name || SITE_NAME;
        const published = meta.article_published || "";
        const modified = meta.article_modified || "";

        // Title
        document.title = title;

        // Basic meta
        setMeta("name", "description", description);
        setMeta("name", "keywords", keywords);
        setMeta("name", "author", author);
        setMeta("name", "robots", robots);

        // Open Graph
        setMeta("property", "og:title", title);
        setMeta("property", "og:description", description);
        setMeta("property", "og:type", type);
        setMeta("property", "og:url", canonical);
        setMeta("property", "og:site_name", siteName);
        setMeta("property", "og:locale", locale);
        if (image) setMeta("property", "og:image", image);
        if (image) setMeta("property", "og:image:alt", title);
        if (published) setMeta("property", "article:published_time", published);
        if (modified) setMeta("property", "article:modified_time", modified);

        // Twitter Card
        setMeta("name", "twitter:card", twitterCard);
        setMeta("name", "twitter:title", title);
        setMeta("name", "twitter:description", description);
        if (image) setMeta("name", "twitter:image", image);
        if (twitterSite) setMeta("name", "twitter:site", twitterSite);
        if (twitterCreator) setMeta("name", "twitter:creator", twitterCreator);

        // Canonical
        if (canonical) setLink("canonical", canonical);

        // Additional SEO meta
        setMeta("name", "theme-color", "var(--site-primary)");
    }, [metaContent, fallbackTitle, fallbackDescription, fallbackImage, fallbackType, slug]);

    return null;
}
