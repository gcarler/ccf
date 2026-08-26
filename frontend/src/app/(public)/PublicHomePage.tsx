"use client";

import Link from "next/link";
import React from "react";
import Image from "next/image";
import { ArrowRight, Sparkles } from "lucide-react";
import { motion } from "framer-motion";
import { SITE_NAME } from "@/lib/site-config";
import { useCmsV2Page } from "@/hooks/useCmsV2Page";
import { useState } from "react";
import { apiFetch } from "@/lib/http";
import { toast } from "sonner";
import PublicHeroWithSlides, { type PublicSlide } from "@/components/public/PublicHeroWithSlides";
import type { CmsPublicPage } from "@/types/cms-v2";

// Media ya publicada en el CMS. Se usa como respaldo mientras la sección Hero
// de producción no exponga sus slides; no reemplaza la configuración editable.
const PUBLISHED_HOME_HERO_MEDIA: PublicSlide[] = [
    {
        src: "/api/static/cms/public-site/645a6f5cfc2e41a290ace6da2bd16b55.webp",
        alt: "Comunidad reunida en adoración",
    },
    {
        src: "/api/static/cms/public-site/e96c6969f75347878c48ec968518c4a7.webp",
        alt: "Comunidad reunida en oración",
    },
    {
        src: "/api/static/cms/public-site/f5b69d948d934412a9470f557faf4f7f.webp",
        alt: "Comunidad celebrando junta",
    },
    {
        src: "/api/static/cms/public-site/5fff1d0f797e40c09b42873b6973bf7e.webp",
        alt: "Mensaje en comunidad",
    },
];

/**
 * La home es un client component, pero el hero sticky se renderiza en SSR
 * desde ``initialHomePage`` (fetched en page.tsx) para que el árbol servidor
 * y cliente coincidan y no haya hydration mismatch. El hook refresca luego.
 */
export default function PublicHomePage({ initialHomePage }: { initialHomePage?: CmsPublicPage | null }) {
    const homePage = useCmsV2Page('home') ?? initialHomePage;
    const heroContent = homePage?.blocks?.hero;
    const homeFeedContent = homePage?.blocks?.feed;
    const eventsPage = useCmsV2Page('events');
    const eventsContent = eventsPage?.blocks?.events;










    const heroEyebrow = (heroContent?.eyebrow as string) ?? "";
    const heroTitleLead = (heroContent?.title_lead as string) ?? "";
    const heroTitleAccent = (heroContent?.title_accent as string) ?? "";
    const heroTitleTail = (heroContent?.title_tail as string) ?? "";
    const heroDescription = (heroContent?.description as string) ?? "";
    const heroPrimaryCta = (heroContent?.primary_cta as string) ?? "";
    const heroSecondaryCta = (heroContent?.secondary_cta as string) ?? "";

    const homeFeed = (homeFeedContent?.parsed && typeof homeFeedContent.parsed === "object" && !Array.isArray(homeFeedContent.parsed))
        ? homeFeedContent.parsed as Record<string, unknown>
        : null;
    const discoverCtaContent = (homePage?.blocks?.discover_cta as Record<string, unknown> | undefined) ?? null;
    const homeEyebrow = (homeFeed?.eyebrow as string) ?? "";
    const homeSectionTitle = (homeFeed?.section_title as string) ?? "";
    const homeSectionDescription = (homeFeed?.section_description as string) ?? "";
    const activitiesEyebrow = (homeFeed?.activities_eyebrow as string) ?? "";
    const activitiesTitle = (homeFeed?.activities_title as string) ?? "";
    const activitiesViewAll = (homeFeed?.activities_view_all as string) ?? "";
    const activitiesViewAllHref = (homeFeed?.activities_view_all_href as string) ?? "/eventos";
    const activitiesEmpty = (homeFeed?.activities_empty as string) ?? "";
    const scrollIndicator = (homeFeed?.scroll_indicator as string) ?? "";
    const discoverCtaEyebrow = (discoverCtaContent?.eyebrow as string) ?? "";
    const discoverCtaTitle = (discoverCtaContent?.title as string) ?? "";
    const discoverCtaDescription = (discoverCtaContent?.description as string) ?? "";
    const discoverCtaLabel = (discoverCtaContent?.cta_label as string) ?? "";
    const discoverCtaHref = (discoverCtaContent?.cta_href as string) ?? "";
    const hasDiscoverCta = Boolean(
        discoverCtaEyebrow || discoverCtaTitle || discoverCtaDescription || (discoverCtaLabel && discoverCtaHref),
    );
    const newsletterEyebrow = (homeFeed?.newsletter_eyebrow as string) ?? "";
    const newsletterTitle = (homeFeed?.newsletter_title as string) ?? "";
    const newsletterDescription = (homeFeed?.newsletter_description as string) ?? "";
    const newsletterPlaceholder = (homeFeed?.newsletter_placeholder as string) ?? "";
    const newsletterSubmit = (homeFeed?.newsletter_submit as string) ?? "";
    const newsletterSendingLabel = (homeFeed?.newsletter_sending_label as string) ?? "Enviando...";
    const newsletterSuccessToast = (homeFeed?.newsletter_success_toast as string) ?? `¡Suscrito al boletín de ${SITE_NAME}!`;
    const newsletterErrorToast = (homeFeed?.newsletter_error_toast as string) ?? "No se pudo suscribir. Intenta de nuevo.";
    const newsletterSuccessTitle = (homeFeed?.newsletter_success_title as string) ?? "";
    const newsletterSuccessDesc = (homeFeed?.newsletter_success_desc as string) ?? "";
    const homeFeaturedCard = (homeFeed?.featured_card && typeof homeFeed.featured_card === "object" && !Array.isArray(homeFeed.featured_card))
        ? homeFeed.featured_card as Record<string, unknown>
        : null;
    const homeCards = Array.isArray(homeFeed?.cards)
        ? homeFeed.cards as Array<Record<string, unknown>>
        : [];
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
    const hasBento = homeFeaturedCard?.title || homeFeaturedCard?.desc || homeCards.length > 0;
    const hasNewsletter = newsletterTitle || newsletterDescription;

    interface PublicEventItem {
        img?: string;
        tag?: string;
        date?: string;
        title?: string;
        desc?: string;
        status?: string;
    }

    const [nlEmail, setNlEmail] = useState("");
    const [nlStatus, setNlStatus] = useState<"idle" | "sending" | "sent">("idle");

    const handleNewsletterSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!nlEmail) return;
        setNlStatus("sending");
        try {
            await apiFetch("/cms/v2/public/subscribe", {
                method: "POST",
                body: { site_key: "ccf", email: nlEmail },
            });
            setNlStatus("sent");
            setNlEmail("");
            if (newsletterSuccessToast) toast.success(newsletterSuccessToast);
        } catch {
            setNlStatus("idle");
            if (newsletterErrorToast) toast.error(newsletterErrorToast);
        }
    };

    const publicEvents: PublicEventItem[] = Array.isArray(eventsContent?.parsed)
        ? (eventsContent?.parsed as PublicEventItem[]).filter((event) => event.status !== "archived")
        : [];

    const homeSlides: PublicSlide[] = [
        ...cmsHeroSlides,
        ...(cmsHeroSlides.length === 0 && heroBgImage
            ? [{
                src: heroBgImage,
                alt: heroTitleLead || heroTitleAccent || heroTitleTail || "Imagen principal",
                title: heroTitleLead || heroTitleAccent || heroTitleTail || "CCF",
                caption: heroDescription || undefined,
            }]
            : []),
    ].filter((slide): slide is PublicSlide => Boolean(slide));
    const hasHero = homeSlides.length > 0 || heroTitleLead || heroTitleAccent || heroTitleTail || heroDescription;

    // Extraer el primer slide del hero del CMS que tenga href para mostrarlo
    // como CTA persistente (ej. banner de aniversario).
    const heroAnniversarySlide = cmsHeroSlides.find((s) => s.href);
    const heroTertiaryCta = heroAnniversarySlide
        ? { label: heroAnniversarySlide.title || "Celebrar aniversario", href: heroAnniversarySlide.href! }
        : undefined;

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

            {/* ─── BENTO: Bienvenidos a Casa ────────────────────────── */}
            {hasBento && (
                <section
                    className="ccf-section overflow-hidden"
                    style={{ background: "var(--site-surface-container-low)" }}
                >
                    <div className="ccf-container">
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true, margin: "-100px" }}
                            className="mb-14"
                        >
                            {homeEyebrow && (
                                <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.3em] mb-4 px-4 py-2 rounded-full border" style={{ color: "var(--site-primary)", borderColor: "var(--site-primary-container)", background: "var(--site-surface-container-low)" }}>
                                    <Sparkles size={12} /> {homeEyebrow}
                                </span>
                            )}
                            {homeSectionTitle && (
                                <h2
                                    className="font-black ccf-headline text-4xl sm:text-5xl lg:text-6xl max-w-3xl"
                                    style={{ color: "var(--site-on-background)" }}
                                >
                                    {homeSectionTitle}
                                </h2>
                            )}
                            {homeSectionDescription && (
                                <p className="ccf-body mt-6 text-base sm:text-lg max-w-3xl" style={{ color: "var(--site-on-surface-variant)" }}>
                                    {homeSectionDescription}
                                </p>
                            )}
                        </motion.div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-5 md:gap-6">
                            {/* Card grande */}
                            {homeFeaturedCard && ((homeFeaturedCard.title as string | undefined) || (homeFeaturedCard.desc as string | undefined)) && (
                                <motion.div
                                    initial={{ opacity: 0, y: 30 }}
                                    whileInView={{ opacity: 1, y: 0 }}
                                    viewport={{ once: true }}
                                    transition={{ delay: 0.1 }}
                                    className="sm:col-span-2 md:col-span-2 rounded-2xl flex flex-col justify-end group relative overflow-hidden min-h-[420px]"
                                >
                                    {homeFeaturedCard.img ? (
                                        <Image
                                            src={homeFeaturedCard.img as string}
                                            alt={(homeFeaturedCard?.alt as string) ?? ""}
                                            fill
                                            sizes="(max-width: 640px) 100vw, (max-width: 1024px) 100vw, 66vw"
                                            className="object-cover transition-transform duration-700 group-hover:scale-105"
                                        />
                                    ) : (
                                        <div className="absolute inset-0 bg-gradient-to-br from-[hsl(var(--primary))/0.2] via-[hsl(var(--secondary))/0.18] to-[hsl(var(--background))]" />
                                    )}
                                    <div className="absolute inset-0" style={{ background: "linear-gradient(to top, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.3) 55%, transparent 100%)" }} />
                                    <div className="relative z-10 p-8">
                                        {(homeFeaturedCard.title as string | undefined) && (
                                            <h3 className="text-2xl md:text-3xl font-black text-white mb-3">
                                                {homeFeaturedCard.title as string}
                                            </h3>
                                        )}
                                        {(homeFeaturedCard.desc as string | undefined) && (
                                            <p className="text-white/80 leading-relaxed max-w-md mb-5 text-base">
                                                {homeFeaturedCard.desc as string}
                                            </p>
                                        )}
                                        {(homeFeaturedCard.cta as string | undefined) && (
                                            <Link
                                                href={(homeFeaturedCard.href as string) || "#"}
                                                className="inline-flex items-center gap-2 font-black text-sm uppercase tracking-wide text-white group-hover:gap-4 transition-all"
                                            >
                                                {homeFeaturedCard.cta as string} <ArrowRight size={16} />
                                            </Link>
                                        )}
                                    </div>
                                </motion.div>
                            )}

                            {/* Mini cards con imagen */}
                            {homeCards.map((card, idx) => {
                                const title = card.title as string;
                                const desc = card.desc as string;
                                const href = card.href as string;
                                const img = card.img as string;
                                const alt = card.alt as string;
                                if (!title && !desc && !img) return null;
                                return (
                                    <motion.div
                                        key={title || idx}
                                        initial={{ opacity: 0, y: 20 }}
                                        whileInView={{ opacity: 1, y: 0 }}
                                        viewport={{ once: true }}
                                        transition={{ delay: 0.1 * (idx + 1) }}
                                    >
                                        <Link
                                            href={href || "#"}
                                            className="block rounded-2xl overflow-hidden group relative min-h-[130px] flex flex-col justify-end transition-transform hover:scale-[1.02]"
                                        >
                                            {img ? (
                                                <Image
                                                    src={img}
                                                    alt={alt || title || ""}
                                                    fill
                                                    sizes="(max-width: 640px) 100vw, (max-width: 768px) 50vw, 33vw"
                                                    className="object-cover transition-transform duration-500 group-hover:scale-105"
                                                />
                                            ) : (
                                                <div className="absolute inset-0 bg-gradient-to-br from-[hsl(var(--primary))/0.18] to-[hsl(var(--surface-2))/0.35]" />
                                            )}
                                            <div className="absolute inset-0" style={{ background: "linear-gradient(to top, rgba(0,0,0,0.78) 0%, rgba(0,0,0,0.1) 60%, transparent 100%)" }} />
                                            <div className="relative z-10 p-5">
                                                {title && <h4 className="font-black text-white text-base mb-1">{title}</h4>}
                                                {desc && <p className="text-white/70 text-xs leading-relaxed">{desc}</p>}
                                            </div>
                                        </Link>
                                    </motion.div>
                                );
                            })}
                        </div>
                    </div>
                </section>
            )}

            {/* ─── ACTIVIDADES RECIENTES ────────────────────────────── */}
            {(activitiesTitle || activitiesEyebrow || publicEvents.length > 0) && (
                <section
                    className="ccf-section-tight overflow-hidden"
                    style={{ background: "var(--site-surface)" }}
                >
                    <div className="ccf-container">
                        <motion.div
                            initial={{ opacity: 0, x: -30 }}
                            whileInView={{ opacity: 1, x: 0 }}
                            viewport={{ once: true }}
                            className="flex justify-between items-end mb-10"
                        >
                            <div>
                                {activitiesEyebrow && (
                                    <span
                                        className="text-xs font-bold uppercase tracking-wide block mb-3"
                                        style={{ color: "var(--site-primary)" }}
                                    >
                                        {activitiesEyebrow}
                                    </span>
                                )}
                                {activitiesTitle && (
                                    <h2
                                        className="font-bold ccf-headline text-2xl md:text-3xl"
                                        style={{ color: "var(--site-on-background)" }}
                                    >
                                        {activitiesTitle}
                                    </h2>
                                )}
                            </div>
                            {activitiesViewAll && (
                                <Link
                                    href={activitiesViewAllHref}
                                    className="hidden md:block text-sm font-bold uppercase tracking-wide border-b-2 pb-1 transition-all hover:-translate-y-1"
                                    style={{
                                        color: "var(--site-primary)",
                                        borderColor: "var(--site-primary)",
                                    }}
                                >
                                    {activitiesViewAll}
                                </Link>
                            )}
                        </motion.div>
                        {publicEvents.length === 0 ? (
                            activitiesEmpty && (
                                <p className="ccf-body text-center py-2" style={{ color: "var(--site-on-surface-variant)" }}>
                                    {activitiesEmpty}
                                </p>
                            )
                        ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-5 md:gap-6">
                        {publicEvents.slice(0, 3).map(({ img, tag, date, title, desc }, idx: number) => (
                            <motion.div
                                key={title}
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
                                    {img ? (
                                        <Image
                                            src={img}
                                            alt={title || "Image"}
                                            fill
                                            sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
                                            className="object-cover group-hover:scale-105 transition-transform duration-700"
                                        />
                                    ) : (
                                        <div className="absolute inset-0 bg-gradient-to-br from-[hsl(var(--primary))/0.18] to-[hsl(var(--surface-2))/0.35]" />
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
                                    {title}
                                </h3>
                                <p
                                    className="text-sm leading-relaxed line-clamp-2"
                                    style={{ color: "var(--site-on-surface-variant)" }}
                                >
                                    {desc}
                                </p>
                            </motion.div>
                        ))}
                    </div>
                    )}
                </div>
            </section>
            )}

            {/* ─── CTA NEWSLETTER ───────────────────────────────────── */}
            {hasNewsletter && (
                <section className="ccf-section" style={{ background: "var(--site-surface-container-low)" }}>
                    <motion.div
                        initial={{ opacity: 0, y: 24 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="ccf-container max-w-3xl mx-auto text-center"
                    >
                        {newsletterEyebrow && (
                            <span className="inline-block text-xs font-bold uppercase tracking-widest mb-5 px-4 py-1.5 rounded-full" style={{ background: "var(--site-primary-container)", color: "var(--site-primary)" }}>
                                {newsletterEyebrow}
                            </span>
                        )}
                        {newsletterTitle && (
                            <h2
                                className="font-black ccf-headline mb-5 text-3xl sm:text-4xl lg:text-5xl"
                                style={{ color: "var(--site-on-background)" }}
                            >
                                {newsletterTitle}
                            </h2>
                        )}
                        {newsletterDescription && (
                            <p className="ccf-body text-base sm:text-lg mb-10 mx-auto" style={{ color: "var(--site-on-surface-variant)" }}>
                                {newsletterDescription.split('\n').map((line, i) => (
                                    <React.Fragment key={i}>
                                        {i > 0 && <br />}
                                        {i === newsletterDescription.split('\n').length - 1 ? (
                                            <span style={{ color: "var(--site-primary)" }}>{line}</span>
                                        ) : line}
                                    </React.Fragment>
                                ))}
                            </p>
                        )}

                        {nlStatus === "sent" ? (
                            <div className="py-6">
                                {newsletterSuccessTitle && <p className="text-2xl font-black mb-2" style={{ color: "var(--site-on-background)" }}>{newsletterSuccessTitle}</p>}
                                {newsletterSuccessDesc && <p className="ccf-body text-base mx-auto" style={{ color: "var(--site-on-surface-variant)" }}>{newsletterSuccessDesc}</p>}
                            </div>
                        ) : (
                            <form onSubmit={handleNewsletterSubmit} className="flex flex-col sm:flex-row gap-3 max-w-xl mx-auto">
                                <input
                                    type="email"
                                    value={nlEmail}
                                    onChange={(e) => setNlEmail(e.target.value)}
                                    placeholder={newsletterPlaceholder}
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
                                    {nlStatus === "sending" ? (newsletterSendingLabel || "Enviando...") : newsletterSubmit}
                                </button>
                            </form>
                        )}
                    </motion.div>
                </section>
            )}

            {/* ─── CTA: QUIERO CONOCER A JESÚS ───────────────────────── */}
            {hasDiscoverCta && <section
                className="ccf-section overflow-hidden"
                style={{ background: "var(--site-surface-container-lowest)" }}
            >
                <motion.div
                    initial={{ opacity: 0, y: 24 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: "-100px" }}
                    className="ccf-container max-w-4xl mx-auto text-center"
                >
                    {discoverCtaEyebrow && (
                        <span
                            className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.3em] mb-5 px-4 py-2 rounded-full border"
                            style={{
                                color: "var(--site-primary)",
                                borderColor: "var(--site-primary-container)",
                                background: "var(--site-surface-container-low)",
                            }}
                        >
                            <Sparkles size={12} /> {discoverCtaEyebrow}
                        </span>
                    )}
                    {discoverCtaTitle && (
                        <h2
                            className="font-black ccf-headline mb-6 text-3xl sm:text-4xl lg:text-5xl"
                            style={{ color: "var(--site-on-background)" }}
                        >
                            {discoverCtaTitle}
                        </h2>
                    )}
                    {discoverCtaDescription && (
                        <p
                            className="ccf-body text-base sm:text-lg mb-10 max-w-2xl mx-auto"
                            style={{ color: "var(--site-on-surface-variant)" }}
                        >
                            {discoverCtaDescription}
                        </p>
                    )}
                    {discoverCtaLabel && discoverCtaHref && (
                        <Link
                            href={discoverCtaHref}
                            className="ccf-button group inline-flex items-center justify-center gap-2 rounded-full px-8 py-4 text-base font-bold transition-transform hover:-translate-y-0.5"
                            style={{
                                background: "var(--site-primary)",
                                color: "var(--site-on-primary)",
                                boxShadow: "0 18px 42px color-mix(in srgb, var(--site-primary) 28%, transparent)",
                            }}
                        >
                            <span>{discoverCtaLabel}</span>
                            <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" aria-hidden="true" />
                        </Link>
                    )}
                </motion.div>
            </section>}
        </div>
        </>
    );
}
