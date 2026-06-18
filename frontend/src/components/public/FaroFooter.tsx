"use client";

import Link from "next/link";
import React from "react";
import { useContentBlock } from "@/hooks/useContent";
import { SITE_EMAIL, SITE_KEY, SITE_NAME } from "@/lib/site-config";

type PublicLink = { href: string; label: string; kind?: string };

function readLinks(value: unknown, fallback: PublicLink[]) {
    if (!Array.isArray(value)) return fallback;
    const items = value
        .map((item) => item && typeof item === "object" ? item as Record<string, unknown> : null)
        .filter(Boolean)
        .map((item) => ({
            href: typeof item!.href === "string" ? item!.href : "",
            label: typeof item!.label === "string" ? item!.label : "",
            kind: typeof item!.kind === "string" ? item!.kind : undefined,
        }))
        .filter((item) => item.href && item.label);
    return items.length > 0 ? items : fallback;
}

function socialIcon(kindOrLabel: string) {
    const key = kindOrLabel.toLowerCase();
    if (key.includes("instagram")) {
        return (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="16" height="16" className="shrink-0">
                <rect x="2" y="2" width="20" height="20" rx="5" ry="5" />
                <circle cx="12" cy="12" r="4" />
                <circle cx="17.5" cy="6.5" r="0.5" fill="currentColor" stroke="none" />
            </svg>
        );
    }
    if (key.includes("youtube")) {
        return (
            <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16" className="shrink-0">
                <path d="M22.54 6.42a2.78 2.78 0 0 0-1.95-1.96C18.88 4 12 4 12 4s-6.88 0-8.59.46A2.78 2.78 0 0 0 1.46 6.42 29 29 0 0 0 1 12a29 29 0 0 0 .46 5.58 2.78 2.78 0 0 0 1.95 1.96C5.12 20 12 20 12 20s6.88 0 8.59-.46a2.78 2.78 0 0 0 1.95-1.96A29 29 0 0 0 23 12a29 29 0 0 0-.46-5.58z" />
                <polygon points="9.75 15.02 15.5 12 9.75 8.98 9.75 15.02" fill="white" />
            </svg>
        );
    }
    return (
        <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16" className="shrink-0">
            <path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z" />
        </svg>
    );
}

export default function FaroFooter() {
    const { data: footerContent } = useContentBlock(`${SITE_KEY}_footer`);
    const footer = (footerContent?.parsed && typeof footerContent.parsed === "object" && !Array.isArray(footerContent.parsed))
        ? footerContent.parsed as Record<string, unknown>
        : {};

    const fallbackNavLinks: PublicLink[] = [
        { href: "/", label: "Inicio" },
        { href: "/nosotros", label: "Sobre Nosotros" },
        { href: "/pastores", label: "Pastores" },
        { href: "/eventos", label: "Eventos" },
        { href: "/predicas", label: "Prédicas" },
        { href: "/cursos", label: "Cursos" },
    ];

    const fallbackResourceLinks: PublicLink[] = [
        { href: "/conocer-a-jesus", label: "Conocer a Jesús" },
        { href: "/testimonios", label: "Testimonios" },
        { href: "/sedes", label: "Sedes" },
        { href: "/boletin", label: "Boletín" },
    ];

    const fallbackSocialLinks: PublicLink[] = [
        { href: "https://facebook.com/comunidadfaro", label: "Facebook", kind: "facebook" },
        { href: "https://instagram.com/comunidadfaro", label: "Instagram", kind: "instagram" },
        { href: "https://youtube.com/comunidadfaro", label: "YouTube", kind: "youtube" },
    ];

    const navLinks = readLinks(footer.nav_links, fallbackNavLinks);
    const resourceLinks = readLinks(footer.resource_links, fallbackResourceLinks);
    const socialLinks = readLinks(footer.social_links, fallbackSocialLinks);
    const description = typeof footer.description === "string"
        ? footer.description
        : "Iluminando el camino hacia una conexión profunda con lo divino a través de la comunidad y la guía espiritual. Una casa de fe abierta para toda la familia.";
    const locationLabel = typeof footer.location_label === "string" ? footer.location_label : "Cartagena, Colombia";
    const newsletterLabel = typeof footer.newsletter_label === "string" ? footer.newsletter_label : "Boletín semanal";

    return (
        <footer
            className="w-full"
            style={{
                background: "var(--site-surface-container-lowest)",
                borderTop: "1px solid var(--site-outline-variant)",
            }}
        >
            {/* Main footer */}
            <div className="px-4 sm:px-6 lg:px-8 xl:px-12 py-8 sm:py-10 lg:py-16">
                <div className="mx-auto w-full max-w-7xl">
                    <div className="grid grid-cols-2 gap-5 sm:gap-8 lg:grid-cols-12 lg:gap-12">
                        {/* Brand column */}
                        <div className="col-span-2 lg:col-span-5 space-y-4 text-center sm:text-left">
                            <div className="flex flex-col items-center gap-3 sm:flex-row sm:gap-4">
                                <div
                                    className="w-12 h-12 sm:w-14 sm:h-14 rounded-full flex items-center justify-center shrink-0"
                                    style={{ background: "var(--site-cta-gradient)" }}
                                >
                                    <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" width="24" height="24" className="shrink-0 w-6 h-6 sm:w-7 sm:h-7">
                                        <path d="M8 22L10 6L12 2L14 6L16 22H8Z" strokeLinejoin="round" />
                                        <circle cx="12" cy="4" r="1.5" fill="white" />
                                    </svg>
                                </div>
                                <div>
                                    <div className="text-xl sm:text-2xl font-bold tracking-tight" style={{ color: "var(--site-on-surface)" }}>
                                        {SITE_NAME}
                                    </div>
                                </div>
                            </div>
                            <p className="mx-auto max-w-[34rem] text-sm leading-relaxed sm:mx-0 lg:max-w-sm" style={{ color: "var(--site-on-surface-variant)" }}>
                                {description}
                            </p>
                            <div className="flex justify-center gap-3 pt-1 sm:justify-start">
                                {socialLinks.map(({ href, label, kind }) => (
                                    <a
                                        key={label}
                                        href={href}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="w-10 h-10 rounded-full flex items-center justify-center transition-all hover:scale-110"
                                        style={{ background: "var(--site-surface-container)", color: "var(--site-on-surface-variant)" }}
                                        title={label}
                                    >
                                        {socialIcon(kind || label)}
                                    </a>
                                ))}
                            </div>
                        </div>

                        {/* Navegación */}
                        <div
                            className="rounded-lg border p-4 sm:p-0 sm:border-0 lg:col-span-2"
                            style={{ borderColor: "var(--site-outline-variant)" }}
                        >
                            <h4 className="text-[10px] font-bold uppercase tracking-widest mb-4 sm:mb-6" style={{ color: "var(--site-primary)" }}>
                                Navegación
                            </h4>
                            <ul className="grid gap-2.5 sm:gap-3">
                                {navLinks.map(({ href, label }) => (
                                    <li key={href}>
                                        <Link href={href} className="block min-h-7 text-sm leading-snug transition-colors duration-200 hover:text-[var(--site-primary)]" style={{ color: "var(--site-on-surface-variant)" }}>
                                            {label}
                                        </Link>
                                    </li>
                                ))}
                            </ul>
                        </div>

                        {/* Recursos */}
                        <div
                            className="rounded-lg border p-4 sm:p-0 sm:border-0 lg:col-span-2"
                            style={{ borderColor: "var(--site-outline-variant)" }}
                        >
                            <h4 className="text-[10px] font-bold uppercase tracking-widest mb-4 sm:mb-6" style={{ color: "var(--site-primary)" }}>
                                Recursos
                            </h4>
                            <ul className="grid gap-2.5 sm:gap-3">
                                {resourceLinks.map(({ href, label }) => (
                                    <li key={href}>
                                        <Link href={href} className="block min-h-7 text-sm leading-snug transition-colors duration-200 hover:text-[var(--site-primary)]" style={{ color: "var(--site-on-surface-variant)" }}>
                                            {label}
                                        </Link>
                                    </li>
                                ))}
                            </ul>
                        </div>

                        {/* Redes y contacto */}
                        <div
                            className="col-span-2 rounded-lg border p-4 sm:p-0 sm:border-0 sm:col-span-2 lg:col-span-3"
                            style={{ borderColor: "var(--site-outline-variant)" }}
                        >
                            <h4 className="text-[10px] font-bold uppercase tracking-widest mb-4 sm:mb-6" style={{ color: "var(--site-primary)" }}>
                                Contáctanos
                            </h4>
                            <ul className="grid gap-2.5 sm:grid-cols-3 lg:grid-cols-1 sm:gap-3">
                                <li>
                                    {SITE_EMAIL ? (
                                        <a href={`mailto:${SITE_EMAIL}`} className="block min-h-7 break-words text-sm leading-snug transition-colors duration-200 hover:text-[var(--site-primary)]" style={{ color: "var(--site-on-surface-variant)" }}>
                                            {SITE_EMAIL}
                                        </a>
                                    ) : null}
                                </li>
                                <li>
                                    <Link href="/sedes" className="block min-h-7 text-sm leading-snug transition-colors duration-200 hover:text-[var(--site-primary)]" style={{ color: "var(--site-on-surface-variant)" }}>
                                        {locationLabel}
                                    </Link>
                                </li>
                                <li>
                                    <Link href="/boletin" className="block min-h-7 text-sm leading-snug transition-colors duration-200 hover:text-[var(--site-primary)]" style={{ color: "var(--site-on-surface-variant)" }}>
                                        {newsletterLabel}
                                    </Link>
                                </li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>

            {/* Bottom bar */}
            <div
                className="px-4 sm:px-6 lg:px-8 xl:px-12 py-5 border-t"
                style={{ borderColor: "var(--site-outline-variant)" }}
            >
                <div className="mx-auto flex w-full max-w-7xl flex-col items-center justify-between gap-3 text-center sm:flex-row sm:text-left">
                    <p
                        className="max-w-[32rem] text-[11px] leading-relaxed sm:text-xs"
                        style={{ color: "var(--site-on-surface-variant)" }}
                    >
                        © {new Date().getFullYear()}{" "}
                        <a
                            href="https://ples.com.co"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:underline hover:text-[var(--site-primary)] transition-colors"
                        >
                            PLES SAS
                        </a>
                        {" "}— El uso inteligente de la experiencia. Todos los derechos reservados.
                    </p>
                    <div className="flex shrink-0 items-center justify-center gap-4">
                        <Link
                            href="/privacidad"
                            className="text-xs transition-colors hover:text-[var(--site-primary)] hover:underline"
                            style={{
                                color: "var(--site-on-surface-variant)",
                            }}
                        >
                            Política de Privacidad
                        </Link>
                    </div>
                </div>
            </div>
        </footer>
    );
}
