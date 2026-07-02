"use client";

import Link from "next/link";
import React from "react";
import { SITE_EMAIL, SITE_NAME } from "@/lib/site-config";
import OptimizedImage from "@/components/ui/OptimizedImage";
import { useSiteBranding } from "@/lib/site-branding";

type PublicLink = { href: string; label: string; kind?: string };

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

export default function FaroFooter() {
    const { logoUrl, logoName } = useSiteBranding({ logoName: SITE_NAME });
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

    const navLinks = fallbackNavLinks;
    const resourceLinks = fallbackResourceLinks;
    const socialLinks = fallbackSocialLinks;
    const description = "Iluminando el camino hacia una conexión profunda con lo divino a través de la comunidad y la guía espiritual. Una casa de fe abierta para toda la familia.";
    const brandName = logoName || SITE_NAME;
    const navSectionTitle = "Navegación";
    const resourceSectionTitle = "Recursos";
    const contactSectionTitle = "Contáctanos";
    const locationLabel = "Cartagena, Colombia";
    const newsletterLabel = "Boletín semanal";
    const copyrightCompany = "PLES SAS";
    const copyrightCompanyUrl = "https://ples.com.co";
    const copyrightText = "El uso inteligente de la experiencia. Todos los derechos reservados.";
    const privacyLabel = "Política de Privacidad";

    return (
        <footer
            className="w-full"
            style={{
                background: "var(--site-surface-container-lowest)",
                borderTop: "1px solid var(--site-outline-variant)",
            }}
        >
            {/* Main footer */}
            <div className="faro-container py-12 sm:py-16 lg:py-24">
                <div className="w-full">
                    <div className="grid grid-cols-2 gap-8 sm:gap-12 lg:grid-cols-12 lg:gap-16">
                        {/* Brand column */}
                        <div className="col-span-2 lg:col-span-5 space-y-4 text-center sm:text-left">
                            <div className="flex flex-col items-center gap-3 sm:flex-row sm:gap-4">
                                <div
                                    className="w-14 h-14 sm:w-16 sm:h-16 rounded-full flex items-center justify-center shrink-0 overflow-hidden"
                                    style={{ background: "var(--site-surface-container)" }}
                                >
                                    {logoUrl ? (
                                        <OptimizedImage src={logoUrl} alt={brandName} width={56} height={56} className="w-full h-full object-contain p-2" />
                                    ) : (
                                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="28" height="28" className="shrink-0 w-7 h-7 sm:w-8 sm:h-8" style={{ color: "var(--site-primary)" }}>
                                            <path d="M8 22L10 6L12 2L14 6L16 22H8Z" strokeLinejoin="round" />
                                            <circle cx="12" cy="4" r="1.5" fill="currentColor" />
                                        </svg>
                                    )}
                                </div>
                                <div>
                                    <div className="text-2xl sm:text-3xl lg:text-4xl font-bold tracking-tight" style={{ color: "var(--site-on-surface)" }}>
                                        {brandName}
                                    </div>
                                </div>
                            </div>
                            <p className="mx-auto max-w-[38rem] text-base leading-relaxed sm:mx-0 lg:max-w-md" style={{ color: "var(--site-on-surface-variant)" }}>
                                {description}
                            </p>
                            <div className="flex justify-center gap-4 pt-2 sm:justify-start">
                                {socialLinks.map(({ href, label, kind }) => (
                                    <a
                                        key={label}
                                        href={href}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="w-11 h-11 sm:w-12 sm:h-12 rounded-full flex items-center justify-center transition-all hover:scale-110"
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
                                {navSectionTitle}
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
                                {resourceSectionTitle}
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
                                {contactSectionTitle}
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
                            href="/privacidad"
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
