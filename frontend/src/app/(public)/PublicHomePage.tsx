"use client";

import Link from "next/link";
import React, { useState, useEffect, useMemo } from "react";
import Image from "next/image";
import { ArrowRight, Sparkles } from "lucide-react";
import { motion } from "framer-motion";
import { SITE_NAME } from "@/lib/site-config";
import { useCmsV2Page } from "@/hooks/useCmsV2Page";
import { apiFetch } from "@/lib/http";
import { toast } from "sonner";
import PublicHeroWithSlides, { type PublicSlide } from "@/components/public/PublicHeroWithSlides";
import type { CmsPublicPage, CmsSection } from "@/types/cms-v2";

export interface PublicEventItem {
    img?: string;
    tag?: string;
    date?: string;
    title?: string;
    desc?: string;
    status?: string;
}

// ─── Module-scope Subcomponents ──────────────────────────────────────────────

export function HomeWelcomeSection({
    section,
    fallbackFeed,
}: {
    section?: CmsSection;
    fallbackFeed?: Record<string, unknown> | null;
}) {
    const raw = (section?.props_json as Record<string, unknown> | undefined) ?? {};
    const fallback = fallbackFeed ?? {};

    const eyebrow = (raw.eyebrow as string) ?? (fallback.eyebrow as string) ?? "";
    const title = (raw.section_title as string)
        ?? (raw.title as string)
        ?? (fallback.section_title as string)
        ?? (fallback.title as string)
        ?? "";
    const description = (raw.section_description as string)
        ?? (raw.description as string)
        ?? (fallback.section_description as string)
        ?? (fallback.description as string)
        ?? "";

    const featuredRaw = (raw.featured_card && typeof raw.featured_card === "object" && !Array.isArray(raw.featured_card))
        ? (raw.featured_card as Record<string, unknown>)
        : ((fallback.featured_card && typeof fallback.featured_card === "object" && !Array.isArray(fallback.featured_card))
            ? (fallback.featured_card as Record<string, unknown>)
            : null);

    const cardsRaw = Array.isArray(raw.cards)
        ? (raw.cards as Array<Record<string, unknown>>)
        : (Array.isArray(fallback.cards) ? (fallback.cards as Array<Record<string, unknown>>) : []);

    const hasBento = Boolean(title || description || (featuredRaw && (featuredRaw.title || featuredRaw.desc)) || cardsRaw.length > 0);
    if (!hasBento) return null;

    return (
        <section
            data-testid="public-section-welcome"
            data-section-key="welcome"
            className="ccf-section overflow-hidden"
            style={{ background: "var(--site-surface-container-low)" }}
        >
            <div className="ccf-container" data-testid="public-home-section-welcome">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: "-100px" }}
                    className="mb-14"
                >
                    {eyebrow && (
                        <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.3em] mb-4 px-4 py-2 rounded-full border" style={{ color: "var(--site-primary)", borderColor: "var(--site-primary-container)", background: "var(--site-surface-container-low)" }}>
                            <Sparkles size={12} /> {eyebrow}
                        </span>
                    )}
                    {title && (
                        <h2
                            className="font-black ccf-headline text-4xl sm:text-5xl lg:text-6xl max-w-3xl"
                            style={{ color: "var(--site-on-background)" }}
                        >
                            {title}
                        </h2>
                    )}
                    {description && (
                        <p className="ccf-body mt-6 text-base sm:text-lg max-w-3xl" style={{ color: "var(--site-on-surface-variant)" }}>
                            {description}
                        </p>
                    )}
                </motion.div>

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-5 md:gap-6">
                    {/* Card grande */}
                    {featuredRaw && Boolean(featuredRaw.title || featuredRaw.desc) && (
                        <motion.div
                            initial={{ opacity: 0, y: 30 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ delay: 0.1 }}
                            className="sm:col-span-2 md:col-span-2 rounded-2xl flex flex-col justify-end group relative overflow-hidden min-h-[420px]"
                        >
                            {featuredRaw.img ? (
                                <Image
                                    src={featuredRaw.img as string}
                                    alt={(featuredRaw.alt as string) ?? ""}
                                    fill
                                    sizes="(max-width: 640px) 100vw, (max-width: 1024px) 100vw, 66vw"
                                    className="object-cover transition-transform duration-700 group-hover:scale-105"
                                />
                            ) : (
                                <div className="absolute inset-0 bg-gradient-to-br from-site-primary/20 via-site-secondary/20 to-site-background" />
                            )}
                            <div className="absolute inset-0" style={{ background: "linear-gradient(to top, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.3) 55%, transparent 100%)" }} />
                            <div className="relative z-10 p-8">
                                {Boolean(featuredRaw.title) && (
                                    <h3 className="text-2xl md:text-3xl font-black text-white mb-3">
                                        {featuredRaw.title as string}
                                    </h3>
                                )}
                                {Boolean(featuredRaw.desc) && (
                                    <p className="text-white/80 leading-relaxed max-w-md mb-5 text-base">
                                        {featuredRaw.desc as string}
                                    </p>
                                )}
                                {Boolean(featuredRaw.cta) && (
                                    <Link
                                        href={(featuredRaw.href as string) || "#"}
                                        className="inline-flex items-center gap-2 font-black text-sm uppercase tracking-wide text-white group-hover:gap-4 transition-all"
                                    >
                                        {featuredRaw.cta as string} <ArrowRight size={16} />
                                    </Link>
                                )}
                            </div>
                        </motion.div>
                    )}

                    {/* Mini cards con imagen */}
                    {cardsRaw.map((card, idx) => {
                        const cardTitle = card.title as string | undefined;
                        const cardDesc = card.desc as string | undefined;
                        const cardHref = card.href as string | undefined;
                        const cardImg = card.img as string | undefined;
                        const cardAlt = card.alt as string | undefined;
                        if (!cardTitle && !cardDesc && !cardImg) return null;
                        return (
                            <motion.div
                                key={cardTitle || idx}
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ delay: 0.1 * (idx + 1) }}
                            >
                                <Link
                                    href={cardHref || "#"}
                                    className="block rounded-2xl overflow-hidden group relative min-h-[130px] flex flex-col justify-end transition-transform hover:scale-[1.02]"
                                >
                                    {cardImg ? (
                                        <Image
                                            src={cardImg}
                                            alt={cardAlt || cardTitle || ""}
                                            fill
                                            sizes="(max-width: 640px) 100vw, (max-width: 768px) 50vw, 33vw"
                                            className="object-cover transition-transform duration-500 group-hover:scale-105"
                                        />
                                    ) : (
                                        <div className="absolute inset-0 bg-gradient-to-br from-site-primary/20 to-site-surface-container-low" />
                                    )}
                                    <div className="absolute inset-0" style={{ background: "linear-gradient(to top, rgba(0,0,0,0.78) 0%, rgba(0,0,0,0.1) 60%, transparent 100%)" }} />
                                    <div className="relative z-10 p-5">
                                        {cardTitle && <h4 className="font-black text-white text-base mb-1">{cardTitle}</h4>}
                                        {cardDesc && <p className="text-white/70 text-xs leading-relaxed">{cardDesc}</p>}
                                    </div>
                                </Link>
                            </motion.div>
                        );
                    })}
                </div>
            </div>
        </section>
    );
}

export function HomeActivitiesSection({
    section,
    fallbackFeed,
    publicEvents,
}: {
    section?: CmsSection;
    fallbackFeed?: Record<string, unknown> | null;
    publicEvents: PublicEventItem[];
}) {
    const raw = (section?.props_json as Record<string, unknown> | undefined) ?? {};
    const fallback = fallbackFeed ?? {};
    const isFeed = section?.section_key === "feed";

    const eyebrow = (isFeed
        ? ((raw.activities_eyebrow as string) ?? (fallback.activities_eyebrow as string))
        : ((raw.eyebrow as string) ?? (raw.activities_eyebrow as string) ?? (fallback.activities_eyebrow as string) ?? (fallback.eyebrow as string)))
        ?? "";

    const title = (isFeed
        ? ((raw.activities_title as string) ?? (fallback.activities_title as string))
        : ((raw.title as string) ?? (raw.activities_title as string) ?? (fallback.activities_title as string) ?? (fallback.title as string)))
        ?? "";

    const viewAll = (isFeed
        ? ((raw.activities_view_all as string) ?? (fallback.activities_view_all as string))
        : ((raw.view_all as string) ?? (raw.activities_view_all as string) ?? (fallback.activities_view_all as string) ?? (fallback.view_all as string)))
        ?? "";

    const viewAllHref = (isFeed
        ? ((raw.activities_view_all_href as string) ?? (fallback.activities_view_all_href as string))
        : ((raw.view_all_href as string) ?? (raw.activities_view_all_href as string) ?? (fallback.activities_view_all_href as string) ?? (fallback.view_all_href as string)))
        ?? "/eventos";

    const empty = (isFeed
        ? ((raw.activities_empty as string) ?? (fallback.activities_empty as string))
        : ((raw.empty as string) ?? (raw.activities_empty as string) ?? (fallback.activities_empty as string) ?? (fallback.empty as string)))
        ?? "";

    const shouldRender = Boolean(title || eyebrow || publicEvents.length > 0);
    if (!shouldRender) return null;

    return (
        <section
            data-testid="public-section-activities"
            data-section-key="activities"
            className="ccf-section-tight overflow-hidden"
            style={{ background: "var(--site-surface)" }}
        >
            <div className="ccf-container" data-testid="public-home-section-activities">
                <motion.div
                    initial={{ opacity: 0, x: -30 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    className="flex justify-between items-end mb-10"
                >
                    <div>
                        {eyebrow && (
                            <span
                                className="text-xs font-bold uppercase tracking-wide block mb-3"
                                style={{ color: "var(--site-primary)" }}
                            >
                                {eyebrow}
                            </span>
                        )}
                        {title && (
                            <h2
                                className="font-bold ccf-headline text-2xl md:text-3xl"
                                style={{ color: "var(--site-on-background)" }}
                            >
                                {title}
                            </h2>
                        )}
                    </div>
                    {viewAll && (
                        <Link
                            href={viewAllHref}
                            className="hidden md:block text-sm font-bold uppercase tracking-wide border-b-2 pb-1 transition-all hover:-translate-y-1"
                            style={{
                                color: "var(--site-primary)",
                                borderColor: "var(--site-primary)",
                            }}
                        >
                            {viewAll}
                        </Link>
                    )}
                </motion.div>
                {publicEvents.length === 0 ? (
                    empty ? (
                        <p className="ccf-body text-center py-2" style={{ color: "var(--site-on-surface-variant)" }}>
                            {empty}
                        </p>
                    ) : null
                ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-5 md:gap-6">
                        {publicEvents.slice(0, 3).map(({ img, tag, date, title: eventTitle, desc }, idx: number) => {
                            const activityCards = Array.isArray(raw.cards) ? (raw.cards as Array<Record<string, unknown>>) : [];
                            const matchedCard = activityCards.find(
                                (c) => typeof c?.title === "string" && eventTitle && c.title.trim().toLowerCase() === eventTitle.trim().toLowerCase()
                            );
                            const slotCard = activityCards[idx];
                            const resolvedImg = img 
                                || (matchedCard?.img as string) 
                                || (slotCard?.img as string) 
                                || (raw.default_image as string) 
                                || (fallback.default_image as string) 
                                || "";

                            return (
                            <motion.div
                                key={eventTitle || idx}
                                initial={{ opacity: 0, y: 40 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true, margin: "-50px" }}
                                transition={{ delay: idx * 0.15 }}
                                className="group cursor-pointer"
                            >
                                <div
                                    className="relative aspect-video rounded-lg overflow-hidden mb-4 shadow-md"
                                    style={{ background: "var(--site-surface-container-high)" }}
                                >
                                    {resolvedImg ? (
                                        <Image
                                            src={resolvedImg}
                                            alt={eventTitle || "Image"}
                                            fill
                                            sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
                                            className="object-cover group-hover:scale-105 transition-transform duration-700"
                                        />
                                    ) : (
                                        <div className="absolute inset-0 bg-gradient-to-br from-site-primary/20 to-site-surface-container-low" />
                                    )}
                                </div>
                                <div className="flex gap-3 mb-3 items-center">
                                    <span
                                        className="px-3 py-1 rounded-full text-2xs font-bold uppercase tracking-wider"
                                        style={{
                                            background: "var(--site-secondary-container)",
                                            color: "var(--site-on-secondary-container)",
                                        }}
                                    >
                                        {tag}
                                    </span>
                                    <span
                                        className="text-2xs font-bold uppercase tracking-wider"
                                        style={{ color: "var(--site-on-surface-variant)" }}
                                    >
                                        {date}
                                    </span>
                                </div>
                                <h3
                                    className="font-bold text-lg mb-3 group-hover:opacity-80 transition-opacity"
                                    style={{ color: "var(--site-on-surface)" }}
                                >
                                    {eventTitle}
                                </h3>
                                <p
                                    className="text-sm leading-relaxed line-clamp-2"
                                    style={{ color: "var(--site-on-surface-variant)" }}
                                >
                                    {desc}
                                </p>
                            </motion.div>
                            );
                        })}
                    </div>
                )}
            </div>
        </section>
    );
}

export function HomeNewsletterSection({
    section,
    fallbackFeed,
    nlEmail: externalEmail,
    setNlEmail: externalSetEmail,
    nlStatus: externalStatus,
    handleNewsletterSubmit: externalSubmit,
}: {
    section?: CmsSection;
    fallbackFeed?: Record<string, unknown> | null;
    nlEmail?: string;
    setNlEmail?: (val: string) => void;
    nlStatus?: "idle" | "sending" | "sent";
    handleNewsletterSubmit?: (e: React.FormEvent) => Promise<void>;
}) {
    const raw = (section?.props_json as Record<string, unknown> | undefined) ?? {};
    const fallback = fallbackFeed ?? {};
    const isFeed = section?.section_key === "feed";

    const eyebrow = (isFeed
        ? ((raw.newsletter_eyebrow as string) ?? (fallback.newsletter_eyebrow as string))
        : ((raw.eyebrow as string) ?? (raw.newsletter_eyebrow as string) ?? (fallback.newsletter_eyebrow as string) ?? (fallback.eyebrow as string)))
        ?? "";

    const title = (isFeed
        ? ((raw.newsletter_title as string) ?? (fallback.newsletter_title as string))
        : ((raw.title as string) ?? (raw.newsletter_title as string) ?? (fallback.newsletter_title as string) ?? (fallback.title as string)))
        ?? "";

    const description = (isFeed
        ? ((raw.newsletter_description as string) ?? (fallback.newsletter_description as string))
        : ((raw.description as string) ?? (raw.newsletter_description as string) ?? (fallback.newsletter_description as string) ?? (fallback.description as string)))
        ?? "";

    const placeholder = (isFeed
        ? ((raw.newsletter_placeholder as string) ?? (fallback.newsletter_placeholder as string))
        : ((raw.placeholder as string) ?? (raw.newsletter_placeholder as string) ?? (fallback.newsletter_placeholder as string) ?? (fallback.placeholder as string)))
        ?? "";

    const submit = (isFeed
        ? ((raw.newsletter_submit as string) ?? (fallback.newsletter_submit as string))
        : ((raw.submit as string) ?? (raw.newsletter_submit as string) ?? (fallback.newsletter_submit as string) ?? (fallback.submit as string)))
        ?? "";

    const sendingLabel = (isFeed
        ? ((raw.newsletter_sending_label as string) ?? (fallback.newsletter_sending_label as string))
        : ((raw.sending_label as string) ?? (raw.newsletter_sending_label as string) ?? (fallback.newsletter_sending_label as string) ?? (fallback.sending_label as string)))
        ?? "Enviando...";

    const successTitle = (isFeed
        ? ((raw.newsletter_success_title as string) ?? (fallback.newsletter_success_title as string))
        : ((raw.success_title as string) ?? (raw.newsletter_success_title as string) ?? (fallback.newsletter_success_title as string) ?? (fallback.success_title as string)))
        ?? "";

    const successDesc = (isFeed
        ? ((raw.newsletter_success_desc as string) ?? (fallback.newsletter_success_desc as string))
        : ((raw.success_desc as string) ?? (raw.newsletter_success_desc as string) ?? (fallback.newsletter_success_desc as string) ?? (fallback.success_desc as string)))
        ?? "";

    const successToast = (isFeed
        ? ((raw.newsletter_success_toast as string) ?? (fallback.newsletter_success_toast as string))
        : ((raw.success_toast as string) ?? (raw.newsletter_success_toast as string) ?? (fallback.newsletter_success_toast as string) ?? (fallback.success_toast as string)))
        ?? `¡Suscrito al boletín de ${SITE_NAME}!`;

    const errorToast = (isFeed
        ? ((raw.newsletter_error_toast as string) ?? (fallback.newsletter_error_toast as string))
        : ((raw.error_toast as string) ?? (raw.newsletter_error_toast as string) ?? (fallback.newsletter_error_toast as string) ?? (fallback.error_toast as string)))
        ?? "No se pudo suscribir. Intenta de nuevo.";

    const [internalEmail, setInternalEmail] = useState("");
    const [internalStatus, setInternalStatus] = useState<"idle" | "sending" | "sent">("idle");

    const nlEmail = externalEmail !== undefined ? externalEmail : internalEmail;
    const setNlEmail = externalSetEmail ?? setInternalEmail;
    const nlStatus = externalStatus !== undefined ? externalStatus : internalStatus;

    const handleSubmit = async (e: React.FormEvent) => {
        if (externalSubmit) {
            return externalSubmit(e);
        }
        e.preventDefault();
        if (!nlEmail) return;
        setInternalStatus("sending");
        try {
            await apiFetch("/cms/v2/public/subscribe", {
                method: "POST",
                body: { site_key: "ccf", email: nlEmail },
            });
            setInternalStatus("sent");
            setNlEmail("");
            if (successToast) toast.success(successToast);
        } catch {
            setInternalStatus("idle");
            if (errorToast) toast.error(errorToast);
        }
    };

    const hasNewsletter = Boolean(title || description);
    if (!hasNewsletter) return null;

    return (
        <section
            data-testid="public-section-newsletter"
            data-section-key="newsletter"
            className="ccf-section"
            style={{ background: "var(--site-surface-container-low)" }}
        >
            <div data-testid="public-home-section-newsletter">
                <motion.div
                    initial={{ opacity: 0, y: 24 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    className="ccf-container max-w-3xl mx-auto text-center"
                >
                    {eyebrow && (
                        <span className="inline-block text-xs font-bold uppercase tracking-widest mb-5 px-4 py-1.5 rounded-full" style={{ background: "var(--site-primary-container)", color: "var(--site-primary)" }}>
                            {eyebrow}
                        </span>
                    )}
                    {title && (
                        <h2
                            className="font-black ccf-headline mb-5 text-3xl sm:text-4xl lg:text-5xl"
                            style={{ color: "var(--site-on-background)" }}
                        >
                            {title}
                        </h2>
                    )}
                    {description && (
                        <p className="ccf-body text-base sm:text-lg mb-10 mx-auto" style={{ color: "var(--site-on-surface-variant)" }}>
                            {String(description).split("\n").map((line, i, arr) => (
                                <React.Fragment key={i}>
                                    {i > 0 && <br />}
                                    {i === arr.length - 1 ? (
                                        <span style={{ color: "var(--site-primary)" }}>{line}</span>
                                    ) : line}
                                </React.Fragment>
                            ))}
                        </p>
                    )}

                    {nlStatus === "sent" ? (
                        <div className="py-6">
                            {successTitle && <p className="text-2xl font-black mb-2" style={{ color: "var(--site-on-background)" }}>{successTitle}</p>}
                            {successDesc && <p className="ccf-body text-base mx-auto" style={{ color: "var(--site-on-surface-variant)" }}>{successDesc}</p>}
                        </div>
                    ) : (
                        <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3 max-w-xl mx-auto">
                            <input
                                type="email"
                                value={nlEmail}
                                onChange={(e) => setNlEmail(e.target.value)}
                                placeholder={placeholder}
                                required
                                disabled={nlStatus === "sending"}
                                className="flex-grow rounded-full px-6 py-4 text-base focus:outline-none disabled:opacity-60 focus:ring-2"
                                style={{
                                    background: "var(--site-surface)",
                                    border: "2px solid var(--site-outline-variant)",
                                    color: "var(--site-on-surface)",
                                }}
                            />
                            <button
                                type="submit"
                                disabled={nlStatus === "sending"}
                                className="ccf-button shrink-0"
                                style={{
                                    background: "var(--site-cta-gradient)",
                                    boxShadow: "var(--site-cta-shadow)",
                                    color: "var(--site-on-primary)",
                                }}
                            >
                                {nlStatus === "sending" ? (sendingLabel || "Enviando...") : submit}
                            </button>
                        </form>
                    )}
                </motion.div>
            </div>
        </section>
    );
}

export function HomeDiscoverCtaSection({
    section,
    fallbackCta,
}: {
    section?: CmsSection;
    fallbackCta?: Record<string, unknown> | null;
}) {
    const raw = (section?.props_json as Record<string, unknown> | undefined) ?? {};
    const fallback = fallbackCta ?? {};

    const eyebrow = (raw.eyebrow as string)
        ?? (fallback.eyebrow as string)
        ?? "Una invitación para ti";

    const title = (raw.title as string)
        ?? (fallback.title as string)
        ?? "¿Quieres conocer a Jesús?";

    const description = (raw.description as string)
        ?? (fallback.description as string)
        ?? "No es una religión, es el comienzo de una relación que transforma la vida. Da el siguiente paso hoy.";

    const ctaLabel = (raw.cta_label as string)
        ?? (raw.label as string)
        ?? (fallback.cta_label as string)
        ?? (fallback.label as string)
        ?? "Quiero conocer a Jesús";

    const ctaHref = (raw.cta_href as string)
        ?? (raw.href as string)
        ?? (fallback.cta_href as string)
        ?? (fallback.href as string)
        ?? "/conocer-a-jesus";

    const secondaryCtaLabel = (raw.secondary_cta_label as string)
        ?? (fallback.secondary_cta_label as string)
        ?? "";

    const secondaryCtaHref = (raw.secondary_cta_href as string)
        ?? (fallback.secondary_cta_href as string)
        ?? "";

    return (
        <section
            data-testid="public-section-discover_cta"
            data-section-key="discover_cta"
            className="ccf-section overflow-hidden"
            style={{ background: "var(--site-surface-container-lowest)" }}
        >
            <div className="ccf-container max-w-4xl mx-auto text-center" data-testid="public-home-section-discover_cta">
                <motion.div
                    initial={{ opacity: 0, y: 24 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: "-100px" }}
                >
                    {eyebrow && (
                        <span
                            className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.3em] mb-5 px-4 py-2 rounded-full border"
                            style={{
                                color: "var(--site-primary)",
                                borderColor: "var(--site-primary-container)",
                                background: "var(--site-surface-container-low)",
                            }}
                        >
                            <Sparkles size={12} /> {eyebrow}
                        </span>
                    )}
                    {title && (
                        <h2
                            className="font-black ccf-headline mb-6 text-3xl sm:text-4xl lg:text-5xl"
                            style={{ color: "var(--site-on-background)" }}
                        >
                            {title}
                        </h2>
                    )}
                    {description && (
                        <p
                            className="ccf-body text-base sm:text-lg mb-10 max-w-2xl mx-auto"
                            style={{ color: "var(--site-on-surface-variant)" }}
                        >
                            {description}
                        </p>
                    )}
                    <div className="inline-flex flex-wrap items-center justify-center gap-4">
                        {ctaLabel && ctaHref && (
                            <Link
                                href={ctaHref}
                                className="ccf-button group inline-flex items-center justify-center gap-2 rounded-full px-8 py-4 text-base font-bold transition-transform hover:-translate-y-0.5"
                                style={{
                                    background: "var(--site-primary)",
                                    color: "var(--site-on-primary)",
                                    boxShadow: "0 18px 42px color-mix(in srgb, var(--site-primary) 28%, transparent)",
                                }}
                            >
                                <span>{ctaLabel}</span>
                                <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" aria-hidden="true" />
                            </Link>
                        )}
                        {secondaryCtaLabel && secondaryCtaHref && (
                            <Link
                                href={secondaryCtaHref}
                                className="ccf-button-secondary inline-flex items-center justify-center gap-2 rounded-full px-8 py-4 text-base font-bold transition-transform hover:-translate-y-0.5 border"
                            >
                                <span>{secondaryCtaLabel}</span>
                            </Link>
                        )}
                    </div>
                </motion.div>
            </div>
        </section>
    );
}

// ─── Main PublicHomePage Component ───────────────────────────────────────────

/**
 * La home es un client component, pero el hero sticky se renderiza en SSR
 * desde ``initialHomePage`` (fetched en page.tsx) para que el árbol servidor
 * y cliente coincidan y no haya hydration mismatch. El hook refresca luego.
 */
export default function PublicHomePage({ initialHomePage }: { initialHomePage?: CmsPublicPage | null }) {
    const homePage = useCmsV2Page('home') ?? initialHomePage;
    const allSections = homePage?.sections ?? initialHomePage?.sections ?? [];

    const fallbackSections: CmsSection[] = [
        {
            id: "default-welcome",
            page_id: "",
            section_key: "welcome",
            type: "feed",
            sort_order: 1,
            is_visible: true,
            status: "active",
            props_json: (homePage?.blocks?.welcome?.parsed as Record<string, unknown>)
                ?? (homePage?.blocks?.feed?.parsed as Record<string, unknown>)
                ?? {},
            created_at: "",
            updated_at: "",
        },
        {
            id: "default-activities",
            page_id: "",
            section_key: "activities",
            type: "events_calendar",
            sort_order: 2,
            is_visible: true,
            status: "active",
            props_json: (homePage?.blocks?.activities?.parsed as Record<string, unknown>)
                ?? (homePage?.blocks?.feed?.parsed as Record<string, unknown>)
                ?? {},
            created_at: "",
            updated_at: "",
        },
        {
            id: "default-newsletter",
            page_id: "",
            section_key: "newsletter",
            type: "newsletter",
            sort_order: 3,
            is_visible: true,
            status: "active",
            props_json: (homePage?.blocks?.newsletter?.parsed as Record<string, unknown>)
                ?? (homePage?.blocks?.feed?.parsed as Record<string, unknown>)
                ?? {},
            created_at: "",
            updated_at: "",
        },
        {
            id: "default-discover-cta",
            page_id: "",
            section_key: "discover_cta",
            type: "cta_block",
            sort_order: 4,
            is_visible: true,
            status: "active",
            props_json: (homePage?.blocks?.discover_cta?.parsed as Record<string, unknown>)
                ?? (homePage?.blocks?.discover_cta as Record<string, unknown>)
                ?? {},
            created_at: "",
            updated_at: "",
        },
    ];

    const rawSections = allSections.length > 0 ? allSections : fallbackSections;

    // Filter out hero and deleted/archived/hidden sections, then sort ascending by sort_order
    const visibleSections = useMemo(() => {
        return [...rawSections]
            .filter((s) => {
                if (s.section_key === "hero" || s.type === "hero") return false;
                if (s.is_visible === false) return false;
                if (s.status === "archived") return false;
                if ((s as { deleted_at?: string | null }).deleted_at) return false;
                return true;
            })
            .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
    }, [rawSections]);

    // Check presence of modular sections for feed fallback handling
    const hasModularWelcome = visibleSections.some((s) => s.section_key === "welcome");
    const hasModularActivities = visibleSections.some((s) => s.section_key === "activities");
    const hasModularNewsletter = visibleSections.some((s) => s.section_key === "newsletter");
    const hasModularSections = hasModularWelcome || hasModularActivities || hasModularNewsletter;

    // Extract fallback feeds and props
    const fallbackFeedSection = allSections.find((s) => s.section_key === "feed");
    const fallbackFeedProps = (fallbackFeedSection?.props_json as Record<string, unknown> | undefined)
        ?? (homePage?.blocks?.feed?.parsed as Record<string, unknown> | undefined)
        ?? (homePage?.blocks?.feed as Record<string, unknown> | undefined)
        ?? null;

    const discoverCtaSection = allSections.find((s) => s.section_key === "discover_cta");
    const discoverCtaContent = (discoverCtaSection?.props_json as Record<string, unknown> | undefined)
        ?? (homePage?.blocks?.discover_cta?.parsed as Record<string, unknown> | undefined)
        ?? (homePage?.blocks?.discover_cta as Record<string, unknown> | undefined)
        ?? null;

    // ── Hero resolution ───────────────────────────────────────────────────────
    const heroSection = allSections.find(
        (s) => (s.section_key === "hero" || s.type === "hero") && s.is_visible !== false
    );
    const heroContent = (heroSection?.props_json as Record<string, unknown> | undefined)
        ?? (homePage?.blocks?.hero?.parsed as Record<string, unknown> | undefined)
        ?? (homePage?.blocks?.hero as Record<string, unknown> | undefined);

    const welcomeSection = allSections.find((s) => s.section_key === "welcome");
    const scrollIndicator = (welcomeSection?.props_json?.scroll_indicator as string)
        ?? (fallbackFeedSection?.props_json?.scroll_indicator as string)
        ?? (homePage?.blocks?.welcome?.parsed?.scroll_indicator as string)
        ?? (homePage?.blocks?.feed?.parsed?.scroll_indicator as string)
        ?? (heroContent?.scroll_indicator as string)
        ?? "";

    const heroEyebrow = (heroContent?.eyebrow as string) ?? "";
    const heroTitleLead = (heroContent?.title_lead as string) ?? "";
    const heroTitleAccent = (heroContent?.title_accent as string) ?? "";
    const heroTitleTail = (heroContent?.title_tail as string) ?? "";
    const heroDescription = (heroContent?.description as string) ?? "";
    const heroPrimaryCta = (heroContent?.primary_cta as string) ?? "";
    const heroSecondaryCta = (heroContent?.secondary_cta as string) ?? "";

    const cmsHeroSlides: PublicSlide[] = (Array.isArray(heroContent?.slides) ? heroContent.slides : [])
        .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
        .map((item) => ({
            src: typeof item.src === "string" ? item.src : typeof item.url === "string" ? item.url : "",
            alt: typeof item.alt === "string" && item.alt.trim() ? item.alt : "Imagen principal",
            title: typeof item.title === "string" ? item.title : undefined,
            caption: typeof item.caption === "string" ? item.caption : undefined,
            href: typeof item.href === "string" ? item.href : undefined,
        }))
        .filter((slide) => Boolean(slide.src));

    const homeGallerySection = allSections.find(
        (section) => section.type === "gallery" && Array.isArray(section.props_json?.items),
    );
    const homeGallerySource =
        homePage?.blocks?.home_hero_gallery
        ?? allSections.find((section) => section.section_key === "home_hero_gallery" && Array.isArray(section.props_json?.items))
        ?? homePage?.blocks?.gallery
        ?? homePage?.blocks?.media_gallery
        ?? homeGallerySection;

    const homeGallery = (() => {
        if (!homeGallerySource) return [];
        if ("parsed" in homeGallerySource) {
            const parsed = homeGallerySource.parsed;
            if (parsed && typeof parsed === "object" && !Array.isArray(parsed) && Array.isArray((parsed as Record<string, unknown>).items)) {
                return (parsed as { items: Array<Record<string, unknown>> }).items;
            }
        }
        if ("props_json" in homeGallerySource) {
            const propsJson = homeGallerySource.props_json;
            if (propsJson && typeof propsJson === "object" && !Array.isArray(propsJson) && Array.isArray((propsJson as Record<string, unknown>).items)) {
                return (propsJson as { items: Array<Record<string, unknown>> }).items;
            }
        }
        return [];
    })();

    const gallerySlides: PublicSlide[] = (homeGallery
        .map((item, index) => {
            const src = typeof item.url === "string" ? item.url : typeof item.src === "string" ? item.src : "";
            if (!src) return null;
            return {
                src,
                alt: typeof item.alt === "string" && item.alt.trim() ? item.alt : `Foto ${index + 1}`,
                title: typeof item.caption === "string" && item.caption.trim() ? item.caption : undefined,
                caption: typeof item.description === "string" && item.description.trim() ? item.description : undefined,
            };
        }) as (PublicSlide | null)[])
        .filter((slide): slide is PublicSlide => Boolean(slide));

    const homeSlides: PublicSlide[] = [
        ...cmsHeroSlides,
        ...gallerySlides,
    ].filter((slide): slide is PublicSlide => Boolean(slide));

    const hasHero = homeSlides.length > 0 || Boolean(heroTitleLead || heroTitleAccent || heroTitleTail || heroDescription);

    const heroAnniversarySlide = cmsHeroSlides.find((s) => s.href);
    const heroTertiaryCta = heroAnniversarySlide
        ? { label: heroAnniversarySlide.title || "Celebrar aniversario", href: heroAnniversarySlide.href! }
        : undefined;

    // ── Eventos de evangelismo públicos ──────────────────────────────────────
    type EvangelismEvent = {
        id: string; nombre: string; typology: string;
        dia_reunion: string; hora_reunion: string;
        next_date: string; next_datetime: string;
    };
    const [evangelismEvents, setEvangelismEvents] = useState<EvangelismEvent[]>([]);
    useEffect(() => {
        apiFetch<EvangelismEvent[]>("/evangelism/public/upcoming-events", { silent: true })
            .then(setEvangelismEvents)
            .catch(() => setEvangelismEvents([]));
    }, []);

    const eventsPage = useCmsV2Page('events');
    const eventsContent = eventsPage?.blocks?.events;

    const cmsEvents: PublicEventItem[] = Array.isArray(eventsContent?.parsed)
        ? (eventsContent?.parsed as PublicEventItem[]).filter((event) => event.status !== "archived")
        : [];

    const DIAS_ES: Record<string, string> = {
        lunes: "Lunes", martes: "Martes", miércoles: "Miércoles", miercoles: "Miércoles",
        jueves: "Jueves", viernes: "Viernes", sábado: "Sábado", sabado: "Sábado", domingo: "Domingo",
    };
    const evangelismAsEvents: PublicEventItem[] = evangelismEvents.map((ev) => {
        const fecha = new Date(ev.next_datetime);
        const dateLabel = fecha.toLocaleDateString("es-CO", { day: "numeric", month: "long" });
        return {
            title: ev.nombre,
            date: `${DIAS_ES[ev.dia_reunion?.toLowerCase()] ?? ev.dia_reunion} ${dateLabel} · ${ev.hora_reunion}`,
            tag: ev.typology ?? "Evangelismo",
            desc: `Próxima actividad: ${DIAS_ES[ev.dia_reunion?.toLowerCase()] ?? ev.dia_reunion} a las ${ev.hora_reunion}`,
            img: "",
            status: "published",
        } as PublicEventItem;
    });

    const publicEvents: PublicEventItem[] = [...cmsEvents, ...evangelismAsEvents];

    return (
        <>
            {/* ─── HERO sticky — hijo directo del <main> del layout ─────────────
                El sticky se limita a su contenedor: sin wrapper, el hero recorre
                toda la página y el contenido (z-10) pasa por encima al hacer scroll. */}
            {hasHero && (
                <PublicHeroWithSlides
                    home
                    eyebrow={heroEyebrow}
                    titleLead={heroTitleLead}
                    titleAccent={heroTitleAccent}
                    titleTail={heroTitleTail}
                    description={heroDescription}
                    primaryCta={heroPrimaryCta ? { label: heroPrimaryCta, href: (heroContent?.primary_cta_href as string) || "/conocer-a-jesus" } : undefined}
                    secondaryCta={heroSecondaryCta ? { label: heroSecondaryCta, href: (heroContent?.secondary_cta_href as string) || "/predicas" } : undefined}
                    tertiaryCta={heroTertiaryCta}
                    slides={homeSlides}
                    scrollIndicator={scrollIndicator}
                />
            )}

            {/* ─── CONTENIDO (pasa por encima del hero) ──────────────
                bg-site-background vía clase: React SSR descarta el inline
                `background: var(--site-background)` (shorthand con var),
                dejando el contenedor transparente. */}
            <div className="relative z-10 bg-site-background">
                {visibleSections.map((section) => {
                    const key = section.section_key;

                    switch (key) {
                        case "welcome":
                            return (
                                <HomeWelcomeSection
                                    key={section.id || "welcome"}
                                    section={section}
                                    fallbackFeed={fallbackFeedProps}
                                />
                            );

                        case "activities":
                            return (
                                <HomeActivitiesSection
                                    key={section.id || "activities"}
                                    section={section}
                                    fallbackFeed={fallbackFeedProps}
                                    publicEvents={publicEvents}
                                />
                            );

                        case "newsletter":
                            return (
                                <HomeNewsletterSection
                                    key={section.id || "newsletter"}
                                    section={section}
                                    fallbackFeed={fallbackFeedProps}
                                />
                            );

                        case "discover_cta":
                            return (
                                <HomeDiscoverCtaSection
                                    key={section.id || "discover_cta"}
                                    section={section}
                                    fallbackCta={discoverCtaContent}
                                />
                            );

                        case "feed":
                            if (hasModularSections) {
                                // If modular welcome already exists, don't duplicate Bento
                                if (hasModularWelcome) return null;
                                return (
                                    <HomeWelcomeSection
                                        key={section.id || "feed-welcome"}
                                        section={section}
                                        fallbackFeed={fallbackFeedProps}
                                    />
                                );
                            } else {
                                // Pure monolithic feed: render Bento, Activities, Newsletter in sequence
                                return (
                                    <React.Fragment key={section.id || "feed-fallback"}>
                                        <HomeWelcomeSection
                                            section={section}
                                            fallbackFeed={fallbackFeedProps}
                                        />
                                        <HomeActivitiesSection
                                            section={section}
                                            fallbackFeed={fallbackFeedProps}
                                            publicEvents={publicEvents}
                                        />
                                        <HomeNewsletterSection
                                            section={section}
                                            fallbackFeed={fallbackFeedProps}
                                        />
                                    </React.Fragment>
                                );
                            }

                        default:
                            if (section.type === "events_calendar") {
                                return (
                                    <HomeActivitiesSection
                                        key={section.id || "activities"}
                                        section={section}
                                        fallbackFeed={fallbackFeedProps}
                                        publicEvents={publicEvents}
                                    />
                                );
                            }
                            if (section.type === "newsletter") {
                                return (
                                    <HomeNewsletterSection
                                        key={section.id || "newsletter"}
                                        section={section}
                                        fallbackFeed={fallbackFeedProps}
                                    />
                                );
                            }
                            if (section.type === "cta_block") {
                                return (
                                    <HomeDiscoverCtaSection
                                        key={section.id || "discover_cta"}
                                        section={section}
                                        fallbackCta={discoverCtaContent}
                                    />
                                );
                            }
                            return null;
                    }
                })}
            </div>
        </>
    );
}
