"use client";

import Link from "next/link";
import React, { useEffect, useState } from "react";
import { SITE_EMAIL, SITE_KEY, SITE_NAME } from "@/lib/site-config";
import { getCmsPublicPage } from "@/lib/cms/v2";
import OptimizedImage from "@/components/ui/OptimizedImage";
import { useSiteBranding } from "@/lib/site-branding";
import { ArrowUpRight, Mail, MapPin, Newspaper } from "lucide-react";

type PublicLink = { href: string; label: string; kind?: string };

type FooterConfig = {
  description?: string;
  nav_links?: unknown;
  resource_links?: unknown;
  social_links?: unknown;
  section_titles?: Record<string, unknown>;
  contact?: Record<string, unknown>;
  copyright?: Record<string, unknown>;
  privacy_label?: string;
};

function socialIcon(kindOrLabel: string) {
    const key = kindOrLabel.toLowerCase();
    if (key.includes("instagram")) {
        return (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="18" height="18" className="shrink-0">
                <rect x="2" y="2" width="20" height="20" rx="5" ry="5" />
                <circle cx="12" cy="12" r="4" />
                <circle cx="17.5" cy="6.5" r="0.5" fill="currentColor" stroke="none" />
            </svg>
        );
    }
    if (key.includes("youtube")) {
        return (
            <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18" className="shrink-0">
                <path d="M22.54 6.42a2.78 2.78 0 0 0-1.95-1.96C18.88 4 12 4 12 4s-6.88 0-8.59.46A2.78 2.78 0 0 0 1.46 6.42 29 29 0 0 0 1 12a29 29 0 0 0 .46 5.58 2.78 2.78 0 0 0 1.95 1.96C5.12 20 12 20 12 20s6.88 0 8.59-.46a2.78 2.78 0 0 0 1.95-1.96A29 29 0 0 0 23 12a29 29 0 0 0-.46-5.58z" />
                <polygon points="9.75 15.02 15.5 12 9.75 8.98 9.75 15.02" fill="white" />
            </svg>
        );
    }
    return (
        <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18" className="shrink-0">
            <path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z" />
        </svg>
    );
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function asRecord(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return {};
}

function asPublicLinks(value: unknown): PublicLink[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is PublicLink => {
    if (!item || typeof item !== "object") return false;
    const candidate = item as PublicLink;
    return typeof candidate.href === "string" && typeof candidate.label === "string";
  });
}

export default function Footer() {
    const { logoUrl, logoName } = useSiteBranding({ logoName: SITE_NAME });
    const [footerConfig, setFooterConfig] = useState<FooterConfig | null>(null);

    useEffect(() => {
        let mounted = true;
        const loadFooter = async () => {
            try {
                const page = await getCmsPublicPage(SITE_KEY, "footer", { silent: true });
                const section = page?.sections?.find((s) => s.type === "footer_config");
                const props = section?.props_json ? asRecord(section.props_json) : {};
                if (mounted) {
                    setFooterConfig(props as FooterConfig);
                }
            } catch {
                // Ignore; empty defaults render a minimal footer.
            }
        };
        loadFooter();
        return () => {
            mounted = false;
        };
    }, []);

    const cfg = footerConfig ?? {};
    const brandName = logoName || SITE_NAME;
    const description = asString(cfg.description);
    const sectionTitles = asRecord(cfg.section_titles);
    const navSectionTitle = asString(sectionTitles.nav);
    const resourceSectionTitle = asString(sectionTitles.resources);
    const contactSectionTitle = asString(sectionTitles.contact);
    const contact = asRecord(cfg.contact);
    const locationLabel = asString(contact.location_label);
    const newsletterLabel = asString(contact.newsletter_label);
    const copyright = asRecord(cfg.copyright);
    const copyrightCompany = asString(copyright.company);
    const copyrightCompanyUrl = asString(copyright.company_url);
    const copyrightText = asString(copyright.text);
    const privacyLabel = asString(cfg.privacy_label);
    const navLinks = asPublicLinks(cfg.nav_links);
    const resourceLinks = asPublicLinks(cfg.resource_links);
    const socialLinks = asPublicLinks(cfg.social_links);

    return (
        <footer
            className="w-full overflow-hidden"
            style={{
                background: "var(--site-surface-container-lowest)",
                borderTop: "1px solid var(--site-outline-variant)",
            }}
        >
            {/* Main footer */}
            <div className="ccf-container py-16 sm:py-20 lg:py-28">
                <div className="w-full">
                    <div
                        className="mb-10 grid gap-8 rounded-[2rem] border p-6 shadow-2xl sm:p-8 lg:mb-14 lg:grid-cols-[1.08fr_0.92fr] lg:items-center lg:p-10"
                        style={{
                            background: "linear-gradient(135deg, var(--site-surface-container-low), var(--site-surface-container))",
                            borderColor: "var(--site-outline-variant)",
                            boxShadow: "var(--site-card-shadow)",
                        }}
                    >
                        <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
                            <div
                                className="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-[1.5rem] border sm:h-24 sm:w-24"
                                style={{
                                    background: "var(--site-surface-container-lowest)",
                                    borderColor: "var(--site-outline-variant)",
                                }}
                            >
                                {logoUrl ? (
                                    <OptimizedImage src={logoUrl} alt={brandName} width={96} height={96} className="h-full w-full object-contain p-3" />
                                ) : (
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="44" height="44" className="shrink-0" style={{ color: "var(--site-primary)" }}>
                                        <path d="M8 22L10 6L12 2L14 6L16 22H8Z" strokeLinejoin="round" />
                                        <circle cx="12" cy="4" r="1.5" fill="currentColor" />
                                    </svg>
                                )}
                            </div>
                            <div className="min-w-0 text-center sm:text-left">
                                <div className="text-3xl font-black leading-tight tracking-tight sm:text-4xl lg:text-5xl" style={{ color: "var(--site-on-surface)" }}>
                                    {brandName}
                                </div>
                                {description && (
                                    <p className="mt-4 max-w-2xl text-base leading-relaxed sm:text-lg" style={{ color: "var(--site-on-surface-variant)" }}>
                                        {description}
                                    </p>
                                )}
                            </div>
                        </div>

                        <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
                            {SITE_EMAIL ? (
                                <a
                                    href={`mailto:${SITE_EMAIL}`}
                                    className="group flex items-center gap-3 rounded-2xl border px-4 py-4 text-sm font-bold transition-transform hover:-translate-y-0.5"
                                    style={{
                                        background: "var(--site-surface-container-lowest)",
                                        borderColor: "var(--site-outline-variant)",
                                        color: "var(--site-on-surface)",
                                    }}
                                >
                                    <Mail size={18} aria-hidden="true" style={{ color: "var(--site-primary)" }} />
                                    <span className="min-w-0 flex-1 truncate">{SITE_EMAIL}</span>
                                    <ArrowUpRight size={16} className="opacity-60 transition-opacity group-hover:opacity-100" aria-hidden="true" />
                                </a>
                            ) : null}
                            {locationLabel && (
                                <Link
                                    href="/sedes"
                                    className="group flex items-center gap-3 rounded-2xl border px-4 py-4 text-sm font-bold transition-transform hover:-translate-y-0.5"
                                    style={{
                                        background: "var(--site-surface-container-lowest)",
                                        borderColor: "var(--site-outline-variant)",
                                        color: "var(--site-on-surface)",
                                    }}
                                >
                                    <MapPin size={18} aria-hidden="true" style={{ color: "var(--site-primary)" }} />
                                    <span className="min-w-0 flex-1 truncate">{locationLabel}</span>
                                    <ArrowUpRight size={16} className="opacity-60 transition-opacity group-hover:opacity-100" aria-hidden="true" />
                                </Link>
                            )}
                            {newsletterLabel && (
                                <Link
                                    href="/boletin"
                                    className="group flex items-center gap-3 rounded-2xl border px-4 py-4 text-sm font-bold transition-transform hover:-translate-y-0.5"
                                    style={{
                                        background: "var(--site-surface-container-lowest)",
                                        borderColor: "var(--site-outline-variant)",
                                        color: "var(--site-on-surface)",
                                    }}
                                >
                                    <Newspaper size={18} aria-hidden="true" style={{ color: "var(--site-primary)" }} />
                                    <span className="min-w-0 flex-1 truncate">{newsletterLabel}</span>
                                    <ArrowUpRight size={16} className="opacity-60 transition-opacity group-hover:opacity-100" aria-hidden="true" />
                                </Link>
                            )}
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-5 sm:gap-8 lg:grid-cols-12 lg:gap-8">
                        {/* Brand column */}
                        <div
                            className="col-span-2 rounded-[1.5rem] border p-5 sm:p-6 lg:col-span-4"
                            style={{
                                background: "var(--site-surface-container-low)",
                                borderColor: "var(--site-outline-variant)",
                            }}
                        >
                            <h4 className="text-xs font-bold uppercase tracking-widest" style={{ color: "var(--site-primary)" }}>
                                Comunidad
                            </h4>
                            <p className="mt-4 max-w-md text-sm leading-relaxed sm:text-base" style={{ color: "var(--site-on-surface-variant)" }}>
                                {description}
                            </p>
                            <div className="mt-6 flex flex-wrap gap-3">
                                {socialLinks.map(({ href, label, kind }) => (
                                    <a
                                        key={label}
                                        href={href}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="flex h-12 w-12 items-center justify-center rounded-full border transition-all hover:-translate-y-0.5"
                                        style={{
                                            background: "var(--site-surface-container)",
                                            borderColor: "var(--site-outline-variant)",
                                            color: "var(--site-on-surface-variant)",
                                        }}
                                        title={label}
                                        aria-label={label}
                                    >
                                        {socialIcon(kind || label)}
                                    </a>
                                ))}
                            </div>
                        </div>

                        {/* Navegación */}
                        <div
                            className="rounded-[1.5rem] border p-5 sm:p-6 lg:col-span-2"
                            style={{
                                background: "var(--site-surface-container-low)",
                                borderColor: "var(--site-outline-variant)",
                            }}
                        >
                            <h4 className="text-xs font-bold uppercase tracking-widest mb-5" style={{ color: "var(--site-primary)" }}>
                                {navSectionTitle}
                            </h4>
                            <ul className="grid gap-2.5">
                                {navLinks.map(({ href, label }) => (
                                    <li key={href}>
                                        <Link href={href} className="group flex min-h-9 items-center justify-between gap-3 rounded-xl px-2 py-1.5 text-sm font-semibold leading-snug transition-colors duration-200" style={{ color: "var(--site-on-surface-variant)" }}>
                                            {label}
                                            <ArrowUpRight size={13} className="opacity-0 transition-opacity group-hover:opacity-70" aria-hidden="true" />
                                        </Link>
                                    </li>
                                ))}
                            </ul>
                        </div>

                        {/* Recursos */}
                        <div
                            className="rounded-[1.5rem] border p-5 sm:p-6 lg:col-span-2"
                            style={{
                                background: "var(--site-surface-container-low)",
                                borderColor: "var(--site-outline-variant)",
                            }}
                        >
                            <h4 className="text-xs font-bold uppercase tracking-widest mb-5" style={{ color: "var(--site-primary)" }}>
                                {resourceSectionTitle}
                            </h4>
                            <ul className="grid gap-2.5">
                                {resourceLinks.map(({ href, label }) => (
                                    <li key={href}>
                                        <Link href={href} className="group flex min-h-9 items-center justify-between gap-3 rounded-xl px-2 py-1.5 text-sm font-semibold leading-snug transition-colors duration-200" style={{ color: "var(--site-on-surface-variant)" }}>
                                            {label}
                                            <ArrowUpRight size={13} className="opacity-0 transition-opacity group-hover:opacity-70" aria-hidden="true" />
                                        </Link>
                                    </li>
                                ))}
                            </ul>
                        </div>

                        {/* Redes y contacto */}
                        <div
                            className="col-span-2 rounded-[1.5rem] border p-5 sm:p-6 lg:col-span-4"
                            style={{
                                background: "var(--site-surface-container-low)",
                                borderColor: "var(--site-outline-variant)",
                            }}
                        >
                            <h4 className="text-xs font-bold uppercase tracking-widest mb-5" style={{ color: "var(--site-primary)" }}>
                                {contactSectionTitle}
                            </h4>
                            <ul className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
                                <li>
                                    {SITE_EMAIL ? (
                                        <a href={`mailto:${SITE_EMAIL}`} className="flex min-h-11 items-center gap-3 break-words rounded-xl px-2 py-2 text-sm font-semibold leading-snug transition-colors duration-200" style={{ color: "var(--site-on-surface-variant)" }}>
                                            <Mail size={16} aria-hidden="true" style={{ color: "var(--site-primary)" }} />
                                            <span className="min-w-0 truncate">{SITE_EMAIL}</span>
                                        </a>
                                    ) : null}
                                </li>
                                <li>
                                    <Link href="/sedes" className="flex min-h-11 items-center gap-3 rounded-xl px-2 py-2 text-sm font-semibold leading-snug transition-colors duration-200" style={{ color: "var(--site-on-surface-variant)" }}>
                                        <MapPin size={16} aria-hidden="true" style={{ color: "var(--site-primary)" }} />
                                        <span className="min-w-0 truncate">{locationLabel}</span>
                                    </Link>
                                </li>
                                <li>
                                    <Link href="/boletin" className="flex min-h-11 items-center gap-3 rounded-xl px-2 py-2 text-sm font-semibold leading-snug transition-colors duration-200" style={{ color: "var(--site-on-surface-variant)" }}>
                                        <Newspaper size={16} aria-hidden="true" style={{ color: "var(--site-primary)" }} />
                                        <span className="min-w-0 truncate">{newsletterLabel}</span>
                                    </Link>
                                </li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>

            {/* Bottom bar */}
            <div
                className="ccf-container py-7 sm:py-8 border-t"
                style={{ borderColor: "var(--site-outline-variant)" }}
            >
                <div className="flex w-full flex-col items-center justify-between gap-4 text-center sm:flex-row sm:text-left">
                    <p
                        className="max-w-[36rem] text-xs leading-relaxed sm:text-sm"
                        style={{ color: "var(--site-on-surface-variant)" }}
                    >
                        © {new Date().getFullYear()}{" "}
                        <a
                            href={copyrightCompanyUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:underline hover:text-[var(--site-primary)] transition-colors"
                        >
                            {copyrightCompany}
                        </a>
                        {" "}— {copyrightText}
                    </p>
                    <div className="flex shrink-0 items-center justify-center gap-4">
                        <Link
                            href="/privacy"
                            className="text-xs transition-colors hover:text-[var(--site-primary)] hover:underline"
                            style={{
                                color: "var(--site-on-surface-variant)",
                            }}
                        >
                            {privacyLabel}
                        </Link>
                    </div>
                </div>
            </div>
        </footer>
    );
}

export const Footer_compat = Footer;
