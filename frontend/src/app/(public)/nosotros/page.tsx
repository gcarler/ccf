"use client";

import React from "react";
import Image from "next/image";
import Link from "next/link";
import { Target, Sparkles, Quote, Heart, Users, BookOpen, Cross, ArrowRight } from "lucide-react";
import { useCmsV2Page } from "@/hooks/useCmsV2Page";

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

    const hero = (heroCms?.parsed && typeof heroCms.parsed === "object" && !Array.isArray(heroCms.parsed))
        ? heroCms.parsed as Record<string, unknown>
        : null;

    const heroEyebrow    = typeof hero?.eyebrow === "string" ? hero.eyebrow : "";
    const heroTitleLead  = typeof hero?.title_lead === "string" ? hero.title_lead : "";
    const heroTitleAccent = typeof hero?.title_accent === "string" ? hero.title_accent : "";
    const heroDescription = typeof hero?.description === "string" ? hero.description : "";

    const about = (aboutCms?.parsed && typeof aboutCms.parsed === "object" && !Array.isArray(aboutCms.parsed))
        ? aboutCms.parsed as Record<string, unknown>
        : null;

    const cmsStats = Array.isArray(about?.stats) ? about!.stats as Array<{ value: string; label: string }> : [];
    const stats = (liveStats && liveStats.length > 0) ? liveStats : cmsStats;
    const valores = Array.isArray(about?.valores) ? about!.valores as Array<{ num?: string; key?: string; title?: string; desc?: string }> : [];

    const visionText  = typeof about?.vision_text === "string" ? about.vision_text : "";
    const misionText  = typeof about?.mision_text === "string" ? about.mision_text : "";
    const visionTitle = typeof about?.vision_title === "string" ? about.vision_title : "";
    const misionTitle = typeof about?.mision_title === "string" ? about.mision_title : "";

    const founderBio  = typeof about?.founder_bio === "string" ? about.founder_bio : "";
    const founderBio2 = typeof about?.founder_bio2 === "string" ? about.founder_bio2 : "";
    const founderCtaTeam = typeof about?.founder_cta_team === "string" ? about.founder_cta_team : "";
    const founderCtaVisit = typeof about?.founder_cta_visit === "string" ? about.founder_cta_visit : "";
    const valuesEyebrow = typeof about?.values_eyebrow === "string" ? about.values_eyebrow : "";

    const quoteText   = typeof about?.quote_text === "string" ? about.quote_text : "";
    const quoteAuthor = typeof about?.quote_author === "string" ? about.quote_author : "";
    const quoteSubtitle = typeof about?.quote_subtitle === "string" ? about.quote_subtitle : "";

    const ctaViewSedes = typeof about?.cta_view_sedes === "string" ? about.cta_view_sedes : "";
    const ctaViewEvents = typeof about?.cta_view_events === "string" ? about.cta_view_events : "";

    const founderLabel = typeof about?.founder_label === "string" ? about.founder_label : "";
    const founderTitle = typeof about?.founder_title === "string" ? about.founder_title : "";
    const founderTitleAccent = typeof about?.founder_title_accent === "string" ? about.founder_title_accent : "";
    const valoresTitle = typeof about?.valores_title === "string" ? about.valores_title : "";
    const ctaTitle = typeof about?.cta_title === "string" ? about.cta_title : "";
    const ctaDesc = typeof about?.cta_desc === "string" ? about.cta_desc : "";

    const founder1Name = typeof about?.founder1_name === "string" ? about.founder1_name : "";
    const founder1Role = typeof about?.founder1_role === "string" ? about.founder1_role : "";
    const founder1Image = typeof about?.founder1_image === "string" ? about.founder1_image : "";
    const founder2Name = typeof about?.founder2_name === "string" ? about.founder2_name : "";
    const founder2Role = typeof about?.founder2_role === "string" ? about.founder2_role : "";
    const founder2Image = typeof about?.founder2_image === "string" ? about.founder2_image : "";

    const hasHero = heroTitleLead || heroTitleAccent || heroDescription;
    const hasVisionMission = visionTitle || visionText || misionTitle || misionText;
    const hasFounders = founderTitle || founderTitleAccent || founderBio || founderBio2 || founder1Name || founder2Name;
    const hasValores = valores.length > 0;
    const hasQuote = quoteText && quoteAuthor;
    const hasCta = ctaTitle || ctaDesc;

    const heroSlides = Array.isArray(hero?.slides) && hero!.slides.length > 0
        ? (hero!.slides as Array<{ src?: string; alt?: string; title?: string; caption?: string }>)
            .filter(s => s && typeof s.src === "string")
            .map(s => ({ src: s.src!, alt: s.alt || "Comunidad Cristiana El Faro", title: s.title, caption: s.caption }))
        : [
            { src: "/api/static/cms/public-site/1930936676f84f6b97df83da209fd657.webp", alt: "Comunidad Cristiana El Faro — Nosotros" },
            { src: "/api/static/cms/public-site/a663278641a340028b26d6831b08f063.webp", alt: "Comunidad Cristiana El Faro — Nosotros" },
            { src: "/api/static/cms/public-site/7ca9cbaf381a48bc841a6f858abae2cb.webp", alt: "Comunidad Cristiana El Faro — Nosotros" },
        ];

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

            {hasHero && stats.length > 0 && (
                <section className="py-14 md:py-20 ccf-container relative z-10">
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-8 md:gap-12 items-start">
                        {stats.map((s, i) => (
                            <div
                                key={i}
                                className="group cursor-default select-none transition-all duration-300 transform hover:-translate-y-1.5"
                            >
                                <p
                                    className="font-black tracking-tighter leading-none transition-all duration-300 text-site-primary group-hover:text-transparent group-hover:bg-clip-text group-hover:bg-gradient-to-r group-hover:from-site-primary group-hover:via-site-primary-container group-hover:to-site-primary group-hover:animate-gradient-flow group-hover:drop-shadow-[0_8px_20px_var(--site-glow-subtle)]"
                                    style={{ fontSize: "clamp(2.8rem, 6.75vw, 6rem)" }}
                                >
                                    {s.value}
                                </p>
                                <p className="text-xs sm:text-sm md:text-base font-extrabold uppercase tracking-widest text-site-on-surface-variant group-hover:text-site-primary mt-3 md:mt-4 transition-colors duration-300">
                                    {s.label}
                                </p>
                                <div className="h-0.5 w-10 bg-site-primary/30 group-hover:w-20 group-hover:bg-site-primary mt-2 transition-all duration-300 rounded-full" />
                            </div>
                        ))}
                    </div>
                </section>
            )}

            {/* ── VISIÓN Y MISIÓN ── */}
            {hasVisionMission && (
                <section className="py-20 md:py-28 bg-site-surface-container-low/60 relative overflow-hidden">
                    {/* Background ambient lighting */}
                    <div className="absolute top-1/2 left-1/4 -translate-y-1/2 w-96 h-96 bg-site-primary/5 rounded-full blur-3xl pointer-events-none" />
                    <div className="absolute top-1/2 right-1/4 -translate-y-1/2 w-96 h-96 bg-site-primary-container/10 rounded-full blur-3xl pointer-events-none" />

                    <div className="ccf-container relative z-10 grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-10">
                        {/* Visión Card */}
                        {(visionTitle || visionText) && (
                            <div className="group relative rounded-3xl p-8 sm:p-10 md:p-12 bg-site-surface dark:bg-site-surface-container/60 backdrop-blur-xl border border-site-outline-variant/15 hover:border-site-primary/30 shadow-lg hover:shadow-2xl hover:shadow-site-primary/5 transition-all duration-500 transform hover:-translate-y-1.5 flex flex-col justify-between overflow-hidden">
                                {/* Watermark icon */}
                                <div className="absolute -bottom-6 -right-6 text-site-primary/[0.04] group-hover:text-site-primary/[0.08] transition-colors duration-500 pointer-events-none select-none">
                                    <Target size={180} />
                                </div>

                                <div>
                                    {/* Badge Header */}
                                    <div className="flex items-center justify-between mb-8">
                                        <div className="inline-flex items-center gap-2.5 px-4 py-2 rounded-full bg-site-primary/10 border border-site-primary/20 text-site-primary text-xs font-bold uppercase tracking-widest">
                                            <Target size={14} className="text-site-primary" />
                                            <span>Nuestra Visión</span>
                                        </div>
                                        <span className="text-3xl sm:text-4xl font-black text-site-outline-variant/30 select-none">
                                            01
                                        </span>
                                    </div>

                                    {visionTitle && (
                                        <h2 className="ccf-headline text-2xl sm:text-3xl md:text-4xl font-black text-site-on-surface mb-6 tracking-tight group-hover:text-site-primary transition-colors duration-300">
                                            {visionTitle}
                                        </h2>
                                    )}

                                    {visionText && (
                                        <RichText
                                            html={visionText}
                                            className="ccf-body text-base sm:text-lg leading-relaxed text-site-on-surface-variant [&_strong]:text-site-on-surface"
                                        />
                                    )}
                                </div>

                                <div className="mt-8 pt-6 border-t border-site-outline-variant/15 flex items-center gap-3 text-xs font-bold uppercase tracking-wider text-site-primary">
                                    <div className="w-8 h-0.5 rounded-full bg-site-primary group-hover:w-16 transition-all duration-500" />
                                    <span>Hacia dónde vamos</span>
                                </div>
                            </div>
                        )}

                        {/* Misión Card */}
                        {(misionTitle || misionText) && (
                            <div
                                className="group relative rounded-3xl p-8 sm:p-10 md:p-12 overflow-hidden shadow-xl hover:shadow-2xl transition-all duration-500 transform hover:-translate-y-1.5 flex flex-col justify-between"
                                style={{
                                    background: "var(--site-hero-cta-gradient)",
                                    boxShadow: "0 24px 64px -12px var(--site-glow-intense)",
                                }}
                            >
                                {/* Subtle inner pattern & watermark */}
                                <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(255,255,255,0.15),transparent_65%)] pointer-events-none" />
                                <div className="absolute -bottom-6 -right-6 text-white/[0.08] group-hover:text-white/[0.14] transition-colors duration-500 pointer-events-none select-none">
                                    <Sparkles size={180} />
                                </div>

                                <div className="relative z-10">
                                    {/* Badge Header */}
                                    <div className="flex items-center justify-between mb-8">
                                        <div className="inline-flex items-center gap-2.5 px-4 py-2 rounded-full bg-white/15 border border-white/25 text-white text-xs font-bold uppercase tracking-widest backdrop-blur-md">
                                            <Sparkles size={14} className="text-white" />
                                            <span>Nuestra Misión</span>
                                        </div>
                                        <span className="text-3xl sm:text-4xl font-black text-white/30 select-none">
                                            02
                                        </span>
                                    </div>

                                    {misionTitle && (
                                        <h2 className="ccf-headline text-2xl sm:text-3xl md:text-4xl font-black text-white mb-6 tracking-tight">
                                            {misionTitle}
                                        </h2>
                                    )}

                                    {misionText && (
                                        <RichText
                                            html={misionText}
                                            className="ccf-body text-base sm:text-lg leading-relaxed text-white/90 [&_strong]:text-white"
                                        />
                                    )}
                                </div>

                                <div className="relative z-10 mt-8 pt-6 border-t border-white/15 flex items-center gap-3 text-xs font-bold uppercase tracking-wider text-white/90">
                                    <div className="w-8 h-0.5 rounded-full bg-white group-hover:w-16 transition-all duration-500" />
                                    <span>Nuestra razón de ser</span>
                                </div>
                            </div>
                        )}
                    </div>
                </section>
            )}

            {/* ── FUNDADORES ── */}
            {hasFounders && (
                <section className="ccf-section">
                    <div className="ccf-container flex flex-col lg:flex-row items-center gap-16 lg:gap-20">
                        {/* Fotos */}
                        <div className="w-full lg:w-5/12 relative shrink-0">
                            <div className="relative h-[340px] sm:h-[420px] md:h-[520px] overflow-hidden ccf-image">
                                <div className="absolute left-0 top-0 w-[58%] aspect-[3/4] rounded-2xl overflow-hidden shadow-2xl ring-1 ring-site-outline-variant/20 z-10">
                                    {founder1Image ? (
                                        <Image
                                            src={founder1Image}
                                            alt={founder1Name}
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
                                            alt={founder2Name}
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
            )}

            {/* ── VALORES ── */}
            {hasValores && (
                <section className="ccf-section bg-site-surface-container-low">
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
            )}

            {/* ── CITA ── */}
            {hasQuote && (
                <section className="ccf-section">
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
            )}

            {/* ── CTA ── */}
            {hasCta && (
                <section className="ccf-section-tight">
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
            )}
        </main>
    );
}
