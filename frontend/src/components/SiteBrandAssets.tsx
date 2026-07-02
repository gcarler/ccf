"use client";

import { useEffect } from "react";
import { useSiteBranding } from "@/lib/site-branding";
import { SITE_NAME } from "@/lib/site-config";

function upsertLink(rel: string, href: string, id: string) {
    if (typeof document === "undefined") return;

    const existing =
        document.querySelector<HTMLLinkElement>(`link[data-site-brand="${id}"]`) ||
        document.querySelector<HTMLLinkElement>(`link[rel="${rel}"]`);
    const link = existing || document.createElement("link");
    link.rel = rel;
    link.href = href;
    link.dataset.siteBrand = id;

    if (!existing) {
        document.head.appendChild(link);
    }
}

export default function SiteBrandAssets() {
    const { logoUrl, logoName } = useSiteBranding({ logoName: SITE_NAME });

    useEffect(() => {
        const iconHref = logoUrl || "/icon.png";
        const appleHref = logoUrl || "/apple-icon.png";

        upsertLink("icon", iconHref, "icon");
        upsertLink("shortcut icon", iconHref, "shortcut-icon");
        upsertLink("apple-touch-icon", appleHref, "apple-touch-icon");

        document.documentElement.style.setProperty("--site-logo-url", logoUrl || "");
        document.documentElement.style.setProperty("--site-logo-name", logoName || SITE_NAME);
    }, [logoName, logoUrl]);

    return null;
}
