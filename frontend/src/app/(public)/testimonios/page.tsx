"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import OptimizedImage from "@/components/ui/OptimizedImage";
import { Quote, ArrowRight, Sparkles, Search, Users, Headphones, ImageIcon, PlayCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useCmsV2Page } from "@/hooks/useCmsV2Page";
import PublicHeroWithSlides from "@/components/public/PublicHeroWithSlides";

import { apiFetch } from "@/lib/http";
import { Testimonial } from "@/lib/data/testimonios";

const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { type: "spring", bounce: 0.4 } }
};

function getTestimonialMediaUrl(t: Testimonial): string {
    if (t.media_type === "image") return t.image_url || t.media_url || "";
    if (t.media_type === "video") return t.video_url || t.media_url || "";
    if (t.media_type === "podcast") return t.podcast_url || t.media_url || "";
    return t.media_url || t.image_url || t.video_url || t.podcast_url || "";
}

// Extracted Component for Expandable Testimonial Card
function TestimonialCard({ t, isHighlight }: { t: Testimonial; isHighlight: boolean }) {
    const limit = isHighlight ? 180 : 120;
    const isLongText = t.content.length > limit;
    const mediaUrl = getTestimonialMediaUrl(t);

    // We truncate nicely without cutting words if possible
    const truncatedText = useMemo(() => {
        if (!isLongText) return t.content;
        const lastSpace = t.content.substring(0, limit).lastIndexOf(' ');
        return t.content.substring(0, lastSpace > 0 ? lastSpace : limit) + '...';
    }, [t.content, limit, isLongText]);

    return (
        <motion.div
            layout
            variants={itemVariants}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ duration: 0.4 }}
            className="break-inside-avoid relative rounded-lg p-6 lg:p-8 border transition-shadow duration-500 hover:shadow-2xl overflow-hidden group flex flex-col h-fit"
            style={{
                background: isHighlight ? "var(--site-primary-container)" : "var(--site-surface-container-low)",
                borderColor: isHighlight ? "var(--site-primary)" : "var(--site-outline-variant)",
                boxShadow: isHighlight ? "0 20px 40px var(--site-card-highlight)" : "none"
            }}
        >
            {isHighlight && (
                <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity pointer-events-none">
                    <Quote size={80} style={{ color: "var(--site-primary)" }} />
                </div>
            )}

            <div className="relative z-10 flex flex-col flex-grow justify-between gap-3">
                <div>
                    {mediaUrl && (
                        <div className="mb-3 overflow-hidden rounded-lg border" style={{ borderColor: "var(--site-outline-variant)", background: "var(--site-surface-container)" }}>
                            {t.media_type === "image" ? (
                                <OptimizedImage src={mediaUrl} alt="" width={400} height={192} className="h-48 w-full object-cover" />
                            ) : t.media_type === "video" ? (
                                <video controls className="w-full bg-black">
                                    <source src={mediaUrl} />
                                </video>
                            ) : (
                                <div className="space-y-3 p-4">
                                    <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--site-primary)" }}>
                                        <Headphones size={16} /> Podcast
                                    </div>
                                    <audio controls src={mediaUrl} className="w-full" />
                                </div>
                            )}
                        </div>
                    )}
                    <motion.p
                        layout="position"
                        className={isHighlight ? 'text-lg lg:text-xl font-bold leading-snug' : 'text-lg lg:text-xl italic leading-relaxed'}
                        style={{ color: isHighlight ? "var(--site-on-secondary-container)" : "var(--site-on-surface)" }}
                    >
                        &quot;{truncatedText}&quot;
                    </motion.p>

                    {isLongText && (
                        <Link
                            href={`/testimonios/${t.id}`}
                            className="mt-4 flex items-center gap-1.5 text-sm font-semibold uppercase tracking-wide transition-all w-fit hover:opacity-70"
                            style={{ color: "var(--site-primary)" }}
                        >
                            Leer más <ArrowRight size={16} />
                        </Link>
                    )}
                </div>

                <div>
                    <div className="flex items-center gap-4 pt-6 border-t mb-3" style={{ borderColor: "var(--site-outline-variant)", borderTopWidth: isHighlight ? '2px' : '1px', opacity: isHighlight ? 0.3 : 0.5 }} />

                    <motion.div layout="position" className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            {t.author?.avatarUrl ? (
                                <div className="w-12 h-8 rounded-full overflow-hidden border-2 shrink-0" style={{ borderColor: isHighlight ? "var(--site-primary)" : "var(--site-surface-container-highest)" }}>
                                    <OptimizedImage src={t.author.avatarUrl} alt={t.author?.username || "Autor"} width={48} height={32} className="w-full h-full object-cover" />
                                </div>
                            ) : (
                                <div
                                    className="w-12 h-8 rounded-full flex items-center justify-center text-lg font-bold shrink-0"
                                    style={{
                                        background: isHighlight ? "var(--site-primary)" : "var(--site-surface-container-highest)",
                                        color: isHighlight ? "var(--site-on-primary)" : "var(--site-primary)",
                                    }}
                                >
                                    {t.author?.username?.[0] ?? "?"}
                                </div>
                            )}
                            <div className="min-w-0">
                                <p className="font-semibold text-base truncate" style={{ color: "var(--site-on-surface)" }}>
                                    {t.author?.username ?? "Anónimo"}
                                </p>
                                <p
                                    className="text-[10px] uppercase tracking-wide font-bold opacity-80 truncate"
                                    style={{ color: "var(--site-on-surface-variant)" }}
                                >
                                    {t.author?.role ?? "Persona"}
                                </p>
                            </div>
                        </div>

                        <div className="hidden sm:flex flex-col items-end shrink-0 ml-2">
                            {t.emotion && (
                                <span
                                    className="px-3 py-1.5 rounded-full text-[10px] font-semibold uppercase tracking-wide"
                                    style={{
                                        background: "var(--site-surface-dim)",
                                        color: "var(--site-primary)"
                                    }}
                                >
                                    {t.emotion}
                                </span>
                            )}
                            {mediaUrl && (
                                <span
                                    className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[10px] font-semibold uppercase tracking-wide"
                                    style={{ background: "var(--site-surface-dim)", color: "var(--site-on-surface-variant)" }}
                                >
                                    {t.media_type === "video" ? <PlayCircle size={12} /> : t.media_type === "podcast" ? <Headphones size={12} /> : <ImageIcon size={12} />}
                                    {t.media_type === "video" ? "Video" : t.media_type === "podcast" ? "Podcast" : "Imagen"}
                                </span>
                            )}
                        </div>
                    </motion.div>
                </div>
            </div>
        </motion.div>
    );
}

export default function TestimoniosPage() {
    const heroPage = useCmsV2Page('testimonials');
    const heroContent = heroPage?.blocks?.hero;
    const feedContent = heroPage?.blocks?.feed;
    const [testimonials, setTestimonials] = useState<Testimonial[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState("");

    useEffect(() => {
        apiFetch<Testimonial[]>("/cms/testimonials", { silent: true })
            .then((data) => setTestimonials(Array.isArray(data) ? data : []))
            .catch(() => setTestimonials([]))
            .finally(() => setLoading(false));
    }, []);

    const heroEyebrow = typeof heroContent?.eyebrow === "string" ? heroContent.eyebrow : "";
    const heroTitleLead = typeof heroContent?.title_lead === "string" ? heroContent.title_lead : "";
    const heroTitleAccent = typeof heroContent?.title_accent === "string" ? heroContent.title_accent : "";
    const heroDescription = typeof heroContent?.description === "string" ? heroContent.description : "";
    const feed = feedContent?.parsed && typeof feedContent.parsed === "object" && !Array.isArray(feedContent.parsed)
        ? feedContent.parsed as Record<string, unknown>
        : {};
    const searchPlaceholder = typeof feed.search_placeholder === "string" ? feed.search_placeholder : "";
    const loadingLabel = typeof feed.loading_label === "string" ? feed.loading_label : "";
    const emptyTitle = typeof feed.empty_title === "string" ? feed.empty_title : "";
    const emptyDescription = typeof feed.empty_description === "string" ? feed.empty_description : "";
    const storyCta = typeof feed.cta_label === "string" ? feed.cta_label : "";
    const ctaTitle = typeof feed.cta_title === "string" ? feed.cta_title : "";
    const ctaDescription = typeof feed.cta_description === "string" ? feed.cta_description : "";

    const hasHero = heroTitleLead || heroTitleAccent || heroDescription || heroEyebrow;
    const hasCtaBanner = ctaTitle || ctaDescription || storyCta;
    const heroSlides = testimonials
        .map((testimonial) => {
            const mediaUrl = getTestimonialMediaUrl(testimonial);
            if (!mediaUrl || testimonial.media_type !== "image") return null;
            return {
                src: mediaUrl,
                alt: testimonial.author?.username || testimonial.author?.role || "Testimonio",
                title: testimonial.author?.username || "Testimonio",
                caption: testimonial.content.slice(0, 120),
            };
        })
        .filter((slide): slide is { src: string; alt: string; title: string; caption: string } => Boolean(slide))
        .slice(0, 4);

    const filteredTestimonials = useMemo(() => {
        if (!searchQuery.trim()) return testimonials;
        const lowerQuery = searchQuery.toLowerCase();
        return testimonials.filter(t =>
            t.content.toLowerCase().includes(lowerQuery) ||
            (t.author?.username || "").toLowerCase().includes(lowerQuery) ||
            (t.emotion || "").toLowerCase().includes(lowerQuery) ||
            (t.author?.role || "").toLowerCase().includes(lowerQuery)
        );
    }, [testimonials, searchQuery]);

    if (loading) {
        return (
            <main className="pt-[88px] pb-4 min-h-screen flex items-center justify-center">
                    <div className="flex flex-col items-center gap-4">
                        <div className="w-8 h-8 border-4 border-t-transparent rounded-full animate-spin" style={{ borderColor: "var(--site-primary) transparent transparent transparent" }} />
                    <p className="text-lg font-bold tracking-wide uppercase" style={{ color: "var(--site-primary)" }}>{loadingLabel}</p>
                </div>
            </main>
        );
    }

    return (
        <main className="pt-[88px] pb-4 overflow-hidden">
            {/* ── HERO ──────────────────────────────────────────── */}
            {hasHero && (
                <PublicHeroWithSlides
                    eyebrow={heroEyebrow}
                    titleLead={heroTitleLead}
                    titleAccent={heroTitleAccent}
                    description={heroDescription}
                    slides={heroSlides}
                />
            )}

            {/* ── SEARCH & CALL TO ACTION BANNER ────────────────── */}
            <section className="ccf-section-tight ccf-container">
                <div className="flex flex-col lg:flex-row gap-4">
                    {/* Search Bar */}
                    <div className="flex-1 rounded-lg p-4 flex items-center gap-4 border transition-all focus-within:shadow-2xl focus-within:-translate-y-1"
                         style={{
                             background: "var(--site-surface-container)",
                             borderColor: "var(--site-outline-variant)"
                         }}>
                        <Search size={24} style={{ color: "var(--site-primary)" }} className="opacity-70 ml-2" />
                        <input
                            type="text"
                            placeholder={searchPlaceholder}
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full bg-transparent border-none outline-none text-lg font-medium"
                            style={{ color: "var(--site-on-surface)" }}
                        />
                    </div>

                    {/* CTA */}
                    {hasCtaBanner && (
                        <div className="rounded-lg p-4 flex items-center justify-between gap-3 border"
                             style={{
                                 background: "var(--site-surface-container)",
                                 borderColor: "var(--site-outline-variant)"
                             }}>
                            <div className="flex items-center gap-4 hidden md:flex">
                                <div className="w-12 h-8 rounded-lg flex items-center justify-center" style={{ background: "var(--site-hero-cta-gradient)", boxShadow: "0 8px 32px var(--site-hero-cta-shadow)" }}>
                                    <Sparkles size={20} style={{ color: "var(--site-on-hero)" }} />
                                </div>
                                {ctaTitle && (
                                    <div className="mr-4">
                                        <h3 className="font-black" style={{ color: "var(--site-on-surface)" }}>{ctaTitle}</h3>
                                        {ctaDescription && <p className="text-sm" style={{ color: "var(--site-on-surface-variant)" }}>{ctaDescription}</p>}
                                    </div>
                                )}
                            </div>
                            {storyCta && (
                                <Link
                                    href="/conocer-a-jesus"
                                    className="ccf-button w-full justify-center md:w-auto"
                                    style={{
                                        background: "var(--site-primary)",
                                        color: "var(--site-on-primary)",
                                    }}
                                >
                                    {storyCta} <ArrowRight size={16} />
                                </Link>
                            )}
                        </div>
                    )}
                </div>
            </section>

            {/* ── MASONRY GRID ───────────────────────────────────── */}
            <section className="ccf-section-tight ccf-container min-h-[50vh]">
                <AnimatePresence mode="popLayout">
                    {filteredTestimonials.length === 0 ? (
                        <motion.div
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.9 }}
                            className="flex flex-col items-center justify-center text-center py-1.5"
                        >
                            <Users size={64} className="mb-3 opacity-20" style={{ color: "var(--site-primary)" }} />
                            <h3 className="text-xl font-bold mb-4" style={{ color: "var(--site-on-surface)" }}>{emptyTitle}</h3>
                            <p className="ccf-body text-lg opacity-80 max-w-md mx-auto" style={{ color: "var(--site-on-surface-variant)" }}>
                                {emptyDescription}
                            </p>
                        </motion.div>
                    ) : (
                        <motion.div
                            layout
                            className="columns-1 md:columns-2 xl:columns-3 gap-5 space-y-5"
                        >
                            {filteredTestimonials.map((t, index) => (
                                <TestimonialCard
                                    key={t.id}
                                    t={t}
                                    isHighlight={index === 0 && searchQuery === ""}
                                />
                            ))}
                        </motion.div>
                    )}
                </AnimatePresence>
            </section>
        </main>
    );
}
