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

    const stats  = Array.isArray(about?.stats) ? about!.stats as Array<{ value: string; label: string }> : [];
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

    return (
        <main className="min-h-screen bg-site-background pt-[88px] overflow-hidden">
            {/* ── HERO ── */}
            {hasHero && (
                <PublicHeroWithSlides
                    eyebrow={heroEyebrow}
                    titleLead={heroTitleLead}
                    titleAccent={heroTitleAccent}
                    description={heroDescription}
                    slides={[]}
                />
            )}

            {hasHero && stats.length > 0 && (
                <section className="ccf-section-tight ccf-container">
                    <div className="flex flex-wrap gap-8 md:gap-12">
                        {stats.map((s, i) => (
                            <div key={i}>
                                <p className="text-3xl md:text-4xl font-black text-site-primary">{s.value}</p>
                                <p className="text-xs font-bold uppercase tracking-widest text-site-outline mt-0.5">{s.label}</p>
                            </div>
                        ))}
                    </div>
                </section>
            )}

            {/* ── VISIÓN Y MISIÓN ── */}
            {hasVisionMission && (
                <section className="ccf-section bg-site-surface-container-low">
                    <div className="ccf-container grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8">
                        {/* Visión */}
                        {(visionTitle || visionText) && (
                            <div className="ccf-card relative p-8 md:p-10 overflow-hidden bg-site-surface">
                                <div className="absolute top-6 right-6 opacity-[0.06] text-site-primary">
                                    <Target size={100} />
                                </div>
                                <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-site-primary/10 border border-site-primary/20 text-site-primary text-[10px] font-bold uppercase tracking-widest mb-5">
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
                                <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/15 border border-white/20 text-white text-[10px] font-bold uppercase tracking-widest mb-5">
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
                                        <p className="text-white/70 text-[10px] font-medium uppercase tracking-wider drop-shadow-sm">{founder1Role}</p>
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
                                        <p className="text-white/70 text-[10px] font-medium uppercase tracking-wider drop-shadow-sm">{founder2Role}</p>
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
