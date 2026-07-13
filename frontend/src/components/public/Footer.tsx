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

function FooterLinkColumn({ title, links }: { title: string; links: PublicLink[] }) {
    if (!links.length) return null;

    return (
        <div className="min-w-0">
            <h4 className="text-[11px] font-semibold uppercase tracking-[0.2em]" style={{ color: "var(--site-primary)" }}>
                {title}
            </h4>
            <ul className="mt-5 grid gap-1.5">
                {links.map(({ href, label }) => (
                    <li key={href}>
                        <Link
                            href={href}
                            className="group flex min-h-10 items-center justify-between gap-3 rounded-xl px-0 py-1.5 text-sm font-medium leading-snug transition-colors sm:text-[15px]"
                            style={{ color: "var(--site-on-surface-variant)" }}
                        >
                            <span className="min-w-0 truncate">{label}</span>
                            <ArrowUpRight size={14} className="shrink-0 opacity-0 transition-opacity group-hover:opacity-70" aria-hidden="true" />
                        </Link>
                    </li>
                ))}
            </ul>
        </div>
    );
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
    const navSectionTitle = asString(sectionTitles.nav, "Navegacion");
    const resourceSectionTitle = asString(sectionTitles.resources, "Recursos");
    const contactSectionTitle = asString(sectionTitles.contact, "Contacto");
    const contact = asRecord(cfg.contact);
    const locationLabel = asString(contact.location_label);
    const newsletterLabel = asString(contact.newsletter_label);
    const copyright = asRecord(cfg.copyright);
    const copyrightCompany = asString(copyright.company, brandName);
    const copyrightCompanyUrl = asString(copyright.company_url, "/");
    const copyrightText = asString(copyright.text, "Todos los derechos reservados.");
    const privacyLabel = asString(cfg.privacy_label, "Privacidad");
    const navLinks = asPublicLinks(cfg.nav_links);
    const resourceLinks = asPublicLinks(cfg.resource_links);
    const socialLinks = asPublicLinks(cfg.social_links);

    return (
        <footer
            className="w-full overflow-hidden border-t"
            style={{
                background: "linear-gradient(135deg, var(--site-surface-container-low), var(--site-surface-container-lowest))",
                borderColor: "var(--site-outline-variant)",
            }}
        >
            <div className="w-full">
                <div className="ccf-container max-w-[1500px]">
                    <div className="grid gap-10 py-14 sm:py-16 lg:grid-cols-[1.15fr_0.85fr] lg:items-center lg:py-20">
                        <div className="min-w-0">
                            <Link href="/" className="inline-flex max-w-full items-center gap-4">
                                <span
                                    className="grid h-16 w-16 shrink-0 place-items-center overflow-hidden rounded-2xl border sm:h-20 sm:w-20"
                                    style={{
                                        background: "var(--site-surface-container-lowest)",
                                        borderColor: "var(--site-outline-variant)",
                                    }}
                                >
                                    {logoUrl ? (
                                        <OptimizedImage src={logoUrl} alt={brandName} width={80} height={80} className="h-full w-full object-contain p-3" />
                                    ) : (
                                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="38" height="38" className="shrink-0" style={{ color: "var(--site-primary)" }}>
                                            <path d="M8 22L10 6L12 2L14 6L16 22H8Z" strokeLinejoin="round" />
                                            <circle cx="12" cy="4" r="1.5" fill="currentColor" />
                                        </svg>
                                    )}
                                </span>
                                <span className="min-w-0">
                                    <span className="block truncate text-2xl font-semibold leading-tight sm:text-3xl" style={{ color: "var(--site-on-surface)" }}>
                                        {brandName}
                                    </span>
                                    <span className="mt-1 block text-[11px] font-semibold uppercase tracking-[0.2em]" style={{ color: "var(--site-primary)" }}>
                                        Comunidad cristiana
                                    </span>
                                </span>
                            </Link>

                            {description && (
                                <p className="mt-7 max-w-2xl text-base leading-relaxed sm:text-lg" style={{ color: "var(--site-on-surface-variant)" }}>
                                    {description}
                                </p>
                            )}

                            {socialLinks.length ? (
                                <div className="mt-8 flex flex-wrap gap-3">
                                    {socialLinks.map(({ href, label, kind }) => (
                                        <a
                                            key={`${href}-${label}`}
                                            href={href}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="flex h-11 w-11 items-center justify-center rounded-full border transition-all hover:-translate-y-0.5"
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
                            ) : null}
                        </div>

                        <div className="grid gap-2 border-y py-4 sm:grid-cols-3 lg:grid-cols-1 lg:border-y-0 lg:border-l lg:py-2 lg:pl-10" style={{ borderColor: "var(--site-outline-variant)" }}>
                            {SITE_EMAIL ? (
                                <a href={`mailto:${SITE_EMAIL}`} className="group flex items-center gap-3 rounded-2xl px-4 py-3.5 text-sm font-semibold transition-colors" style={{ color: "var(--site-on-surface)" }}>
                                    <Mail size={18} aria-hidden="true" style={{ color: "var(--site-primary)" }} />
                                    <span className="min-w-0 flex-1 truncate">{SITE_EMAIL}</span>
                                    <ArrowUpRight size={15} className="shrink-0 opacity-50 transition-opacity group-hover:opacity-100" aria-hidden="true" />
                                </a>
                            ) : null}
                            {locationLabel ? (
                                <Link href="/sedes" className="group flex items-center gap-3 rounded-2xl px-4 py-3.5 text-sm font-semibold transition-colors" style={{ color: "var(--site-on-surface)" }}>
                                    <MapPin size={18} aria-hidden="true" style={{ color: "var(--site-primary)" }} />
                                    <span className="min-w-0 flex-1 truncate">{locationLabel}</span>
                                    <ArrowUpRight size={15} className="shrink-0 opacity-50 transition-opacity group-hover:opacity-100" aria-hidden="true" />
                                </Link>
                            ) : null}
                            {newsletterLabel ? (
                                <Link href="/boletin" className="group flex items-center gap-3 rounded-2xl px-4 py-3.5 text-sm font-semibold transition-colors" style={{ color: "var(--site-on-surface)" }}>
                                    <Newspaper size={18} aria-hidden="true" style={{ color: "var(--site-primary)" }} />
                                    <span className="min-w-0 flex-1 truncate">{newsletterLabel}</span>
                                    <ArrowUpRight size={15} className="shrink-0 opacity-50 transition-opacity group-hover:opacity-100" aria-hidden="true" />
                                </Link>
                            ) : null}
                        </div>
                    </div>
                </div>

                <div className="w-full border-t" style={{ borderColor: "var(--site-outline-variant)" }}>
                    <div className="ccf-container grid max-w-[1500px] gap-10 py-10 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_1.15fr] lg:py-12">
                        <FooterLinkColumn title={navSectionTitle} links={navLinks} />
                        <FooterLinkColumn title={resourceSectionTitle} links={resourceLinks} />

                        <div className="min-w-0 sm:col-span-2 lg:col-span-1">
                            <h4 className="text-[11px] font-semibold uppercase tracking-[0.2em]" style={{ color: "var(--site-primary)" }}>
                                {contactSectionTitle}
                            </h4>
                            <div className="mt-5 grid gap-2">
                                {SITE_EMAIL ? (
                                    <a href={`mailto:${SITE_EMAIL}`} className="flex min-h-10 items-center gap-3 text-sm font-medium sm:text-[15px]" style={{ color: "var(--site-on-surface-variant)" }}>
                                        <Mail size={16} className="shrink-0" aria-hidden="true" style={{ color: "var(--site-primary)" }} />
                                        <span className="min-w-0 truncate">{SITE_EMAIL}</span>
                                    </a>
                                ) : null}
                                {locationLabel ? (
                                    <Link href="/sedes" className="flex min-h-10 items-center gap-3 text-sm font-medium sm:text-[15px]" style={{ color: "var(--site-on-surface-variant)" }}>
                                        <MapPin size={16} className="shrink-0" aria-hidden="true" style={{ color: "var(--site-primary)" }} />
                                        <span className="min-w-0 truncate">{locationLabel}</span>
                                    </Link>
                                ) : null}
                                {newsletterLabel ? (
                                    <Link href="/boletin" className="flex min-h-10 items-center gap-3 text-sm font-medium sm:text-[15px]" style={{ color: "var(--site-on-surface-variant)" }}>
                                        <Newspaper size={16} className="shrink-0" aria-hidden="true" style={{ color: "var(--site-primary)" }} />
                                        <span className="min-w-0 truncate">{newsletterLabel}</span>
                                    </Link>
                                ) : null}
                            </div>
                        </div>
                    </div>
                </div>

                <div className="w-full border-t" style={{ borderColor: "var(--site-outline-variant)" }}>
                    <div className="ccf-container flex max-w-[1500px] flex-col gap-4 py-6 text-sm sm:flex-row sm:items-center sm:justify-between">
                        <p className="max-w-[44rem] leading-relaxed" style={{ color: "var(--site-on-surface-variant)" }}>
                            © {new Date().getFullYear()}{" "}
                            <a href={copyrightCompanyUrl} target="_blank" rel="noopener noreferrer" className="font-semibold transition-colors hover:text-[var(--site-primary)]">
                                {copyrightCompany}
                            </a>
                            {" "}— {copyrightText}
                        </p>
                        <Link href="/privacy" className="shrink-0 font-semibold transition-colors hover:text-[var(--site-primary)]" style={{ color: "var(--site-on-surface-variant)" }}>
                            {privacyLabel}
                        </Link>
                    </div>
                </div>
            </div>
        </footer>
    );
}

export const Footer_compat = Footer;
