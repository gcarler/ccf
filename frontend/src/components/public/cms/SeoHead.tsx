"use client";

import { useEffect } from "react";
import { SITE_NAME } from "@/lib/site-config";

interface SeoHeadProps {
    slug?: string;
    fallbackTitle?: string;
    fallbackDescription?: string;
    fallbackImage?: string;
    fallbackType?: string;
    canonicalUrl?: string;
    robotsMeta?: string;
    jsonLd?: Record<string, unknown> | null;
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

function removeJsonLdScripts() {
    const existing = document.querySelectorAll('script[type="application/ld+json"]');
    existing.forEach((el) => el.remove());
}

function injectJsonLd(data: Record<string, unknown>) {
    removeJsonLdScripts();
    const script = document.createElement("script");
    script.type = "application/ld+json";
    script.textContent = JSON.stringify(data);
    document.head.appendChild(script);
}

export default function SeoHead({
    fallbackTitle,
    fallbackDescription,
    fallbackImage,
    fallbackType = "website",
    canonicalUrl,
    robotsMeta,
    jsonLd,
}: SeoHeadProps) {
    useEffect(() => {
        const title = fallbackTitle || SITE_NAME;
        const description = fallbackDescription || "";
        const image = fallbackImage || "";
        const canonical = canonicalUrl || (typeof window !== "undefined" ? window.location.href : "");
        const robots = robotsMeta || "index, follow";
        const author = SITE_NAME;
        const twitterCard = "summary_large_image";
        const locale = "es_CO";
        const siteName = SITE_NAME;

        // Title
        document.title = title;

        // Basic meta
        setMeta("name", "description", description);
        setMeta("name", "author", author);
        setMeta("name", "robots", robots);

        // Open Graph
        setMeta("property", "og:title", title);
        setMeta("property", "og:description", description);
        setMeta("property", "og:type", fallbackType);
        setMeta("property", "og:url", canonical);
        setMeta("property", "og:site_name", siteName);
        setMeta("property", "og:locale", locale);
        if (image) setMeta("property", "og:image", image);
        if (image) setMeta("property", "og:image:alt", title);

        // Twitter Card
        setMeta("name", "twitter:card", twitterCard);
        setMeta("name", "twitter:title", title);
        setMeta("name", "twitter:description", description);
        if (image) setMeta("name", "twitter:image", image);

        // Canonical
        if (canonical) setLink("canonical", canonical);

        // JSON-LD
        if (jsonLd) {
            injectJsonLd(jsonLd);
        } else {
            removeJsonLdScripts();
        }

        // Additional SEO meta
        setMeta("name", "theme-color", "var(--site-primary)");
    }, [fallbackTitle, fallbackDescription, fallbackImage, fallbackType, canonicalUrl, robotsMeta, jsonLd]);

    return null;
}
