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

function removeMeta(attr: string, key: string) {
    document.querySelector(`meta[${attr}="${key}"]`)?.remove();
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

function removeLink(rel: string) {
    document.querySelector(`link[rel="${rel}"]`)?.remove();
}

function upsertJsonLd(data: Record<string, unknown>) {
    // Remove any previous client-injected JSON-LD scripts
    document.querySelectorAll('script[data-seo-head]').forEach((el) => el.remove());

    const dataStr = JSON.stringify(data);
    // Check if identical script already exists (server-rendered)
    const existing = document.querySelectorAll('script[type="application/ld+json"]');
    for (const el of existing) {
        if (el.textContent === dataStr) return;
    }
    const script = document.createElement("script");
    script.type = "application/ld+json";
    script.setAttribute("data-seo-head", "1");
    script.textContent = dataStr;
    document.head.appendChild(script);
}

function removeClientJsonLd() {
    document.querySelectorAll('script[data-seo-head]').forEach((el) => el.remove());
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
        const author = SITE_NAME;
        const twitterCard = "summary_large_image";
        const locale = "es_CO";
        const siteName = SITE_NAME;

        // Title
        document.title = title;

        // Basic meta
        setMeta("name", "description", description);
        setMeta("name", "author", author);
        // Robots — set or remove to avoid stale values between navigations
        const robotsEl = document.querySelector('meta[name="robots"]') as HTMLMetaElement | null;
        if (robotsMeta) {
            setMeta("name", "robots", robotsMeta);
        } else if (robotsEl) {
            robotsEl.remove();
        }

        // Open Graph
        setMeta("property", "og:title", title);
        setMeta("property", "og:description", description);
        setMeta("property", "og:type", fallbackType);
        setMeta("property", "og:url", canonical);
        setMeta("property", "og:site_name", siteName);
        setMeta("property", "og:locale", locale);
        if (image) {
            setMeta("property", "og:image", image);
            setMeta("property", "og:image:alt", title);
        } else {
            removeMeta("property", "og:image");
            removeMeta("property", "og:image:alt");
        }

        // Twitter Card
        setMeta("name", "twitter:card", twitterCard);
        setMeta("name", "twitter:title", title);
        setMeta("name", "twitter:description", description);
        if (image) setMeta("name", "twitter:image", image);
        else removeMeta("name", "twitter:image");

        // Canonical
        if (canonical) setLink("canonical", canonical);
        else removeLink("canonical");

        // JSON-LD — upsert without destroying server-rendered scripts (e.g. breadcrumb)
        if (jsonLd) {
            upsertJsonLd(jsonLd);
        } else {
            removeClientJsonLd();
        }

        // Additional SEO meta
        setMeta("name", "theme-color", "var(--site-primary)");
    }, [fallbackTitle, fallbackDescription, fallbackImage, fallbackType, canonicalUrl, robotsMeta, jsonLd]);

    return null;
}
