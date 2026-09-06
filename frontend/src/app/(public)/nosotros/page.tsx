"use client";

import React from "react";
import Image from "next/image";
import Link from "next/link";
import { Target, Sparkles, Quote, Heart, Users, BookOpen, Cross, ArrowRight } from "lucide-react";
import { useCmsV2Page } from "@/hooks/useCmsV2Page";
import type { CmsSection } from "@/types/cms-v2";

import RichText from "@/components/public/RichText";
import PublicHeroWithSlides from "@/components/public/PublicHeroWithSlides";

const VALOR_ICONS: Record<string, React.ReactNode> = {
    palabra:    <BookOpen size={20} />,
    amor:       <Heart size={20} />,
    comunidad:  <Users size={20} />,
    integridad: <Cross size={20} />,
    mision:     <Target size={20} />,
    excelencia: <Sparkles size={20} />,
};

// ─── Module-scope Subcomponents ──────────────────────────────────────────────

function NosotrosStatsSection({
    section,
    fallbackAbout,
    liveStats,
}: {
    section?: CmsSection;
    fallbackAbout?: Record<string, unknown> | null;
    liveStats?: Array<{ value: string; label: string }> | null;
}) {
    const raw = (section?.props_json as Record<string, unknown> | undefined) ?? {};
    const fallback = fallbackAbout ?? {};

    const rawStats = Array.isArray(raw.stats)
        ? (raw.stats as Array<{ value: string; label: string }>)
        : (Array.isArray(fallback.stats) ? (fallback.stats as Array<{ value: string; label: string }>) : []);

    const stats = (liveStats && liveStats.length > 0) ? liveStats : rawStats;
    if (!stats || stats.length === 0) return null;

    return (
        <section
            data-testid="public-nosotros-stats"
            data-section-key="stats"
            className="ccf-section-tight ccf-container"
        >
            <div className="flex flex-wrap gap-8 md:gap-12">
                {stats.map((s, i) => (
                    <div key={i}>
                        <p className="text-3xl md:text-4xl font-black text-site-primary">{s.value}</p>
                        <p className="text-xs font-bold uppercase tracking-widest text-site-outline mt-0.5">{s.label}</p>
                    </div>
                ))}
            </div>
        </section>
    );
}

function NosotrosVisionMisionSection({
    section,
    fallbackAbout,
}: {
    section?: CmsSection;
    fallbackAbout?: Record<string, unknown> | null;
}) {
    const raw = (section?.props_json as Record<string, unknown> | undefined) ?? {};
    const fallback = fallbackAbout ?? {};

    const visionTitle = (raw.vision_title as string) ?? (fallback.vision_title as string) ?? "";
    const visionText = (raw.vision_text as string) ?? (fallback.vision_text as string) ?? "";
    const misionTitle = (raw.mision_title as string) ?? (fallback.mision_title as string) ?? "";
    const misionText = (raw.mision_text as string) ?? (fallback.mision_text as string) ?? "";

    const hasVisionMission = Boolean(visionTitle || visionText || misionTitle || misionText);
    if (!hasVisionMission) return null;

    return (
        <section
            data-testid="public-nosotros-vision-mision"
            data-section-key="vision_mision"
            className="ccf-section bg-site-surface-container-low"
        >
            <div className="ccf-container grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8">
                {/* Visión */}
                {(visionTitle || visionText) && (
                    <div className="ccf-card relative p-8 md:p-10 overflow-hidden bg-site-surface">
                        <div className="absolute top-6 right-6 opacity-[0.06] text-site-primary">
                            <Target size={100} />
                        </div>
                        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-site-primary/10 border border-site-primary/20 text-site-primary text-2xs font-bold uppercase tracking-widest mb-5">
                            <Target size={11} /> Visión
                        </div>
                        {visionTitle && (
                            <h2 className="ccf-headline text-2xl md:text-3xl font-black text-site-on-surface mb-4">
                                {visionTitle}
                            </h2>
                        )}
                        {visionText && (
                            <RichText
                                html={visionText}
                                className="ccf-body text-base md:text-lg text-site-on-surface-variant [&_strong]:text-site-on-surface"
                            />
                        )}
                    </div>
                )}

                {/* Misión */}
                {(misionTitle || misionText) && (
                    <div
                        className="relative rounded-2xl p-8 md:p-10 overflow-hidden shadow-2xl"
                        style={{
                            background: "var(--site-hero-cta-gradient)",
                            boxShadow: "0 20px 60px -10px var(--site-glow-intense)",
                        }}
                    >
                        <div className="absolute top-6 right-6 opacity-10">
                            <Sparkles size={100} className="text-white" />
                        </div>
                        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/15 border border-white/20 text-white text-2xs font-bold uppercase tracking-widest mb-5">
                            <Sparkles size={11} /> Misión
                        </div>
                        {misionTitle && (
                            <h2 className="ccf-headline text-2xl md:text-3xl font-black text-white mb-4">
                                {misionTitle}
                            </h2>
                        )}
                        {misionText && (
                            <RichText
                                html={misionText}
                                className="ccf-body text-base md:text-lg text-white/85 [&_strong]:text-white"
                            />
                        )}
                    </div>
                )}
            </div>
        </section>
    );
}

function NosotrosFoundersSection({
    section,
    fallbackAbout,
}: {
    section?: CmsSection;
    fallbackAbout?: Record<string, unknown> | null;
}) {
    const raw = (section?.props_json as Record<string, unknown> | undefined) ?? {};
    const fallback = fallbackAbout ?? {};

    const founderLabel = (raw.founder_label as string) ?? (fallback.founder_label as string) ?? "";
    const founderTitle = (raw.founder_title as string) ?? (fallback.founder_title as string) ?? "";
    const founderTitleAccent = (raw.founder_title_accent as string) ?? (fallback.founder_title_accent as string) ?? "";
    const founderBio = (raw.founder_bio as string) ?? (fallback.founder_bio as string) ?? "";
    const founderBio2 = (raw.founder_bio2 as string) ?? (fallback.founder_bio2 as string) ?? "";
    const founder1Name = (raw.founder1_name as string) ?? (fallback.founder1_name as string) ?? "";
    const founder1Role = (raw.founder1_role as string) ?? (fallback.founder1_role as string) ?? "";
    const founder1Image = (raw.founder1_image as string) ?? (fallback.founder1_image as string) ?? "";
    const founder2Name = (raw.founder2_name as string) ?? (fallback.founder2_name as string) ?? "";
    const founder2Role = (raw.founder2_role as string) ?? (fallback.founder2_role as string) ?? "";
    const founder2Image = (raw.founder2_image as string) ?? (fallback.founder2_image as string) ?? "";
    const founderCtaTeam = (raw.founder_cta_team as string) ?? (fallback.founder_cta_team as string) ?? "";
    const founderCtaVisit = (raw.founder_cta_visit as string) ?? (fallback.founder_cta_visit as string) ?? "";

    const hasFounders = Boolean(founderTitle || founderTitleAccent || founderBio || founderBio2 || founder1Name || founder2Name);
    if (!hasFounders) return null;

    return (
        <section
            data-testid="public-nosotros-founders"
            data-section-key="founders"
            className="ccf-section"
        >
            <div className="ccf-container flex flex-col lg:flex-row items-center gap-16 lg:gap-20">
                {/* Fotos */}
                <div className="w-full lg:w-5/12 relative shrink-0">
                    <div className="relative h-[340px] sm:h-[420px] md:h-[520px] overflow-hidden ccf-image">
                        <div className="absolute left-0 top-0 w-[58%] aspect-[3/4] rounded-2xl overflow-hidden shadow-2xl ring-1 ring-site-outline-variant/20 z-10">
                            {founder1Image ? (
                                <Image
                                    src={founder1Image}
                                    alt={founder1Name || "Pastor Principal"}
                                    fill
                                    className="object-cover object-top"
                                />
                            ) : (
                                <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-[hsl(var(--primary))/0.18] to-[hsl(var(--surface-2))/0.35]">
                                    <span className="text-4xl font-black text-[hsl(var(--primary))/0.35]">
                                        {founder1Name.charAt(0) || "?"}
                                    </span>
                                </div>
                            )}
                            <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent" />
                            <div className="absolute bottom-3 left-3 right-3">
                                <p className="text-white text-xs font-bold drop-shadow-sm">{founder1Name}</p>
                                <p className="text-white/70 text-2xs font-medium uppercase tracking-wider drop-shadow-sm">{founder1Role}</p>
                            </div>
                        </div>
                        <div className="absolute right-0 bottom-0 w-[55%] aspect-[3/4] rounded-2xl overflow-hidden shadow-2xl ring-1 ring-site-outline-variant/20 z-20">
                            {founder2Image ? (
                                <Image
                                    src={founder2Image}
                                    alt={founder2Name || "Pastor Principal"}
                                    fill
                                    className="object-cover object-top"
                                />
                            ) : (
                                <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-[hsl(var(--primary))/0.18] to-[hsl(var(--surface-2))/0.35]">
                                    <span className="text-4xl font-black text-[hsl(var(--primary))/0.35]">
                                        {founder2Name.charAt(0) || "?"}
                                    </span>
                                </div>
                            )}
                            <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent" />
                            <div className="absolute bottom-3 left-3 right-3">
                                <p className="text-white text-xs font-bold drop-shadow-sm">{founder2Name}</p>
                                <p className="text-white/70 text-2xs font-medium uppercase tracking-wider drop-shadow-sm">{founder2Role}</p>
                            </div>
                        </div>
                        <div
                            className="absolute top-1/3 right-1/4 w-32 h-32 rounded-full blur-2xl -z-10"
                            style={{ background: "var(--site-glow-subtle)" }}
                        />
                    </div>
                </div>

                {/* Texto */}
                <div className="w-full lg:w-7/12">
                    {founderLabel && (
                        <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-site-primary mb-4">
                            <Heart size={12} /> {founderLabel}
                        </span>
                    )}
                    {(founderTitle || founderTitleAccent) && (
                        <h2 className="ccf-headline text-3xl md:text-4xl lg:text-5xl font-black text-site-on-surface mb-5">
                            {founderTitle}
                            <br />
                            <span className="text-site-primary">{founderTitleAccent}</span>
                        </h2>
                    )}
                    {(founderBio || founderBio2) && (
                        <div className="ccf-body space-y-4 text-base md:text-lg text-site-on-surface-variant [&_strong]:text-site-on-surface [&_em]:text-site-outline">
                            {founderBio && <RichText html={founderBio} />}
                            {founderBio2 && <RichText html={founderBio2} />}
                        </div>
                    )}
                    {(founderCtaTeam || founderCtaVisit) && (
                        <div className="mt-10 flex flex-wrap gap-4">
                            {founderCtaTeam && (
                                <Link
                                    href="/pastores"
                                    className="ccf-button"
                                    style={{
                                        background: "var(--site-cta-gradient)",
                                        boxShadow: "var(--site-cta-shadow)",
                                        color: "var(--site-on-primary)",
                                    }}
                                >
                                    {founderCtaTeam} <ArrowRight size={14} />
                                </Link>
                            )}
                            {founderCtaVisit && (
                                <Link
                                    href="/sedes"
                                    className="ccf-button bg-site-surface-container text-site-on-surface-variant border border-site-outline-variant/30"
                                >
                                    {founderCtaVisit}
                                </Link>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </section>
    );
}

function NosotrosValuesSection({
    section,
    fallbackAbout,
}: {
    section?: CmsSection;
    fallbackAbout?: Record<string, unknown> | null;
}) {
    const raw = (section?.props_json as Record<string, unknown> | undefined) ?? {};
    const fallback = fallbackAbout ?? {};

    const valuesEyebrow = (raw.values_eyebrow as string) ?? (fallback.values_eyebrow as string) ?? "";
    const valoresTitle = (raw.valores_title as string) ?? (fallback.valores_title as string) ?? "";
    const valores = Array.isArray(raw.valores)
        ? (raw.valores as Array<{ num?: string; key?: string; title?: string; desc?: string }>)
        : (Array.isArray(fallback.valores) ? (fallback.valores as Array<{ num?: string; key?: string; title?: string; desc?: string }>) : []);

    if (valores.length === 0 && !valoresTitle) return null;

    return (
        <section
            data-testid="public-nosotros-values"
            data-section-key="values"
            className="ccf-section bg-site-surface-container-low"
        >
            <div className="ccf-container">
                <div className="text-center mb-14">
                    {valuesEyebrow && (
                        <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-site-primary mb-3">
                            <Sparkles size={12} /> {valuesEyebrow}
                        </span>
                    )}
                    {valoresTitle && (
                        <h2 className="ccf-headline text-3xl md:text-4xl lg:text-5xl font-black text-site-on-surface mb-4">
                            {valoresTitle}
                        </h2>
                    )}
                    <div className="h-1 w-16 rounded-full bg-site-primary mx-auto" />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 md:gap-8">
                    {valores.map((v, idx) => (
                        <div
                            key={v.key || v.num || idx}
                            className="ccf-card group p-6 md:p-8 bg-site-surface"
                            style={{ "--tw-shadow-color": "var(--site-glow-intense)" } as React.CSSProperties}
                        >
                            <div className="flex items-start justify-between mb-5">
                                <div className="w-10 h-10 rounded-xl bg-site-primary/10 flex items-center justify-center text-site-primary border border-site-primary/15">
                                    {v.key ? VALOR_ICONS[v.key] || <Sparkles size={20} /> : <Sparkles size={20} />}
                                </div>
                                <span className="text-4xl font-black text-site-outline-variant/40 select-none">
                                    {v.num || String(idx + 1).padStart(2, "0")}
                                </span>
                            </div>
                            {v.title && <h3 className="text-lg font-black text-site-on-surface mb-2 tracking-tight">{v.title}</h3>}
                            {v.desc && <p className="ccf-body text-sm text-site-on-surface-variant">{v.desc}</p>}
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}

function NosotrosQuoteSection({
    section,
    fallbackAbout,
}: {
    section?: CmsSection;
    fallbackAbout?: Record<string, unknown> | null;
}) {
    const raw = (section?.props_json as Record<string, unknown> | undefined) ?? {};
    const fallback = fallbackAbout ?? {};

    const quoteText = (raw.quote_text as string) ?? (fallback.quote_text as string) ?? "";
    const quoteAuthor = (raw.quote_author as string) ?? (fallback.quote_author as string) ?? "";
    const quoteSubtitle = (raw.quote_subtitle as string) ?? (fallback.quote_subtitle as string) ?? "";

    if (!quoteText) return null;

    return (
        <section
            data-testid="public-nosotros-quote"
            data-section-key="quote"
            className="ccf-section"
        >
            <div className="ccf-container max-w-4xl text-center">
                <Quote size={48} className="mx-auto mb-6 text-site-primary/20" />
                <blockquote className="ccf-headline text-2xl md:text-3xl lg:text-4xl font-black text-site-on-surface italic mb-6">
                    &ldquo;{quoteText}&rdquo;
                </blockquote>
                <div className="flex items-center justify-center gap-3">
                    <div className="h-px w-12 bg-gradient-to-r from-transparent to-site-primary/30" />
                    <div>
                        <p className="font-bold text-site-on-surface">{quoteAuthor}</p>
                        {quoteSubtitle && <p className="text-xs font-bold uppercase tracking-widest text-site-primary mt-0.5">{quoteSubtitle}</p>}
                    </div>
                    <div className="h-px w-12 bg-gradient-to-l from-transparent to-site-primary/30" />
                </div>
            </div>
        </section>
    );
}

function NosotrosCtaSection({
    section,
    fallbackAbout,
}: {
    section?: CmsSection;
    fallbackAbout?: Record<string, unknown> | null;
}) {
    const raw = (section?.props_json as Record<string, unknown> | undefined) ?? {};
    const fallback = fallbackAbout ?? {};

    const ctaTitle = (raw.cta_title as string) ?? (fallback.cta_title as string) ?? "";
    const ctaDesc = (raw.cta_desc as string) ?? (fallback.cta_desc as string) ?? "";
    const ctaViewSedes = (raw.cta_view_sedes as string) ?? (fallback.cta_view_sedes as string) ?? "";
    const ctaViewEvents = (raw.cta_view_events as string) ?? (fallback.cta_view_events as string) ?? "";

    if (!ctaTitle && !ctaDesc) return null;

    return (
        <section
            data-testid="public-nosotros-cta"
            data-section-key="cta"
            className="ccf-section-tight"
        >
            <div className="ccf-container">
                <div
                    className="relative rounded-3xl overflow-hidden p-6 md:p-10 lg:p-14 text-center"
                    style={{
                        background: "var(--site-cta-gradient)",
                        boxShadow: "var(--site-cta-shadow)",
                    }}
                >
                    <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(255,255,255,0.12),transparent_60%)] pointer-events-none" />
                    <div className="relative z-10">
                        {ctaTitle && (
                            <h2 className="ccf-headline text-3xl md:text-4xl font-black text-white mb-4">
                                {ctaTitle}
                            </h2>
                        )}
                        {ctaDesc && (
                            <RichText
                                html={ctaDesc}
                                className="ccf-body text-base md:text-lg text-white/80 max-w-xl mx-auto mb-8"
                            />
                        )}
                        <div className="flex flex-wrap items-center justify-center gap-4">
                            {ctaViewSedes && (
                                <Link
                                    href="/sedes"
                                    className="ccf-button bg-[hsl(var(--bg-primary))] text-site-primary shadow-xl"
                                >
                                    {ctaViewSedes} <ArrowRight size={14} />
                                </Link>
                            )}
                            {ctaViewEvents && (
                                <Link
                                    href="/eventos"
                                    className="ccf-button bg-white/15 border border-white/25 text-white hover:bg-white/20"
                                >
                                    {ctaViewEvents}
                                </Link>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
}

// ─── Main Page Component ─────────────────────────────────────────────────────

export default function NosotrosPage() {
    const heroPage = useCmsV2Page('about');
    const heroCms = heroPage?.blocks?.hero;
    const aboutCms = heroPage?.blocks?.about;

    const [liveStats, setLiveStats] = React.useState<Array<{ value: string; label: string }> | null>(null);

    React.useEffect(() => {
        let mounted = true;
        fetch('/api/public/stats')
            .then(res => res.ok ? res.json() : null)
            .then(data => {
                if (mounted && data?.stats && Array.isArray(data.stats) && data.stats.length > 0) {
                    setLiveStats(data.stats);
                }
            })
            .catch(() => {});
        return () => { mounted = false; };
    }, []);

    // Secciones ordenadas desde el CMS
    const visibleSections = React.useMemo(() => {
        return (heroPage?.sections || [])
            .filter((s) => s.is_visible !== false && s.status !== "archived")
            .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
    }, [heroPage?.sections]);

    const heroSection = visibleSections.find((s) => s.section_key === "hero");
    const contentSections = visibleSections.filter((s) => s.section_key !== "hero");

    const heroRaw = (heroSection?.props_json as Record<string, unknown> | undefined)
        ?? ((heroCms?.parsed && typeof heroCms.parsed === "object" && !Array.isArray(heroCms.parsed))
            ? (heroCms.parsed as Record<string, unknown>)
            : null);

    const heroEyebrow = typeof heroRaw?.eyebrow === "string" ? heroRaw.eyebrow : "";
    const heroTitleLead = typeof heroRaw?.title_lead === "string" ? heroRaw.title_lead : "";
    const heroTitleAccent = typeof heroRaw?.title_accent === "string" ? heroRaw.title_accent : "";
    const heroDescription = typeof heroRaw?.description === "string" ? heroRaw.description : "";

    const hasHero = Boolean(heroTitleLead || heroTitleAccent || heroDescription);

    const heroSlides = Array.isArray(heroRaw?.slides) && heroRaw!.slides.length > 0
        ? (heroRaw!.slides as Array<{ src?: string; alt?: string; title?: string; caption?: string }>)
            .filter(s => s && typeof s.src === "string")
            .map(s => ({ src: s.src!, alt: s.alt || "Comunidad Cristiana El Faro", title: s.title, caption: s.caption }))
        : [
            { src: "/api/static/cms/public-site/1930936676f84f6b97df83da209fd657.webp", alt: "Comunidad Cristiana El Faro — Nosotros" },
            { src: "/api/static/cms/public-site/a663278641a340028b26d6831b08f063.webp", alt: "Comunidad Cristiana El Faro — Nosotros" },
            { src: "/api/static/cms/public-site/7ca9cbaf381a48bc841a6f858abae2cb.webp", alt: "Comunidad Cristiana El Faro — Nosotros" },
        ];

    const fallbackAbout = (aboutCms?.parsed && typeof aboutCms.parsed === "object" && !Array.isArray(aboutCms.parsed))
        ? (aboutCms.parsed as Record<string, unknown>)
        : null;

    const hasModularSections = contentSections.length > 0;

    return (
        <main className="min-h-screen bg-site-background pt-[88px] overflow-hidden">
            {/* ── HERO ── */}
            {hasHero && (
                <PublicHeroWithSlides
                    eyebrow={heroEyebrow}
                    titleLead={heroTitleLead}
                    titleAccent={heroTitleAccent}
                    description={heroDescription}
                    slides={heroSlides}
                />
            )}

            {/* ── SECCIONES MODULARES DINÁMICAS (Ordenadas por sort_order) ── */}
            {contentSections.map((section) => {
                switch (section.section_key) {
                    case "stats":
                        return (
                            <NosotrosStatsSection
                                key={section.id || "stats"}
                                section={section}
                                fallbackAbout={fallbackAbout}
                                liveStats={liveStats}
                            />
                        );

                    case "vision_mision":
                        return (
                            <NosotrosVisionMisionSection
                                key={section.id || "vision_mision"}
                                section={section}
                                fallbackAbout={fallbackAbout}
                            />
                        );

                    case "founders":
                        return (
                            <NosotrosFoundersSection
                                key={section.id || "founders"}
                                section={section}
                                fallbackAbout={fallbackAbout}
                            />
                        );

                    case "values":
                        return (
                            <NosotrosValuesSection
                                key={section.id || "values"}
                                section={section}
                                fallbackAbout={fallbackAbout}
                            />
                        );

                    case "quote":
                        return (
                            <NosotrosQuoteSection
                                key={section.id || "quote"}
                                section={section}
                                fallbackAbout={fallbackAbout}
                            />
                        );

                    case "cta":
                        return (
                            <NosotrosCtaSection
                                key={section.id || "cta"}
                                section={section}
                                fallbackAbout={fallbackAbout}
                            />
                        );

                    default:
                        if (section.type === "stats_counter") {
                            return <NosotrosStatsSection key={section.id} section={section} fallbackAbout={fallbackAbout} liveStats={liveStats} />;
                        }
                        if (section.type === "vision_mision") {
                            return <NosotrosVisionMisionSection key={section.id} section={section} fallbackAbout={fallbackAbout} />;
                        }
                        if (section.type === "founders_profile") {
                            return <NosotrosFoundersSection key={section.id} section={section} fallbackAbout={fallbackAbout} />;
                        }
                        if (section.type === "values_grid") {
                            return <NosotrosValuesSection key={section.id} section={section} fallbackAbout={fallbackAbout} />;
                        }
                        if (section.type === "quote_callout") {
                            return <NosotrosQuoteSection key={section.id} section={section} fallbackAbout={fallbackAbout} />;
                        }
                        if (section.type === "cta_banner") {
                            return <NosotrosCtaSection key={section.id} section={section} fallbackAbout={fallbackAbout} />;
                        }
                        return null;
                }
            })}

            {/* Fallback si no hay secciones modulares (legado monolithic 'about') */}
            {!hasModularSections && fallbackAbout && (
                <>
                    <NosotrosStatsSection fallbackAbout={fallbackAbout} liveStats={liveStats} />
                    <NosotrosVisionMisionSection fallbackAbout={fallbackAbout} />
                    <NosotrosFoundersSection fallbackAbout={fallbackAbout} />
                    <NosotrosValuesSection fallbackAbout={fallbackAbout} />
                    <NosotrosQuoteSection fallbackAbout={fallbackAbout} />
                    <NosotrosCtaSection fallbackAbout={fallbackAbout} />
                </>
            )}
        </main>
    );
}
