"use client";

import React from "react";
import Image from "next/image";
import Link from "next/link";
import { Target, Sparkles, Quote, Heart, Users, BookOpen, Cross, ChevronRight, ArrowRight } from "lucide-react";
import { useCmsV2Page } from "@/hooks/useCmsV2Page";

import RichText from "@/components/public/RichText";

/* ── Fallbacks ── */
const DEFAULT_STATS = [
    { value: "+20", label: "Años de ministerio" },
    { value: "+8",  label: "Pastores activos" },
    { value: "+500", label: "Familias" },
    { value: "3",   label: "Sedes" },
];

const DEFAULT_VALORES = [
    { num: "01", key: "palabra",     title: "Palabra",        desc: "La Escritura es nuestra brújula. Cada decisión, enseñanza y acción está fundamentada en la sana doctrina de la Biblia." },
    { num: "02", key: "amor",        title: "Amor Radical",   desc: "Un compromiso inquebrantable de servir y acoger a todos, sin importar su historia, origen o camino recorrido." },
    { num: "03", key: "comunidad",   title: "Comunidad",      desc: "Creemos en la vida en familia. El crecimiento espiritual genuino ocurre en relación auténtica con otros." },
    { num: "04", key: "integridad",  title: "Integridad",     desc: "Vivir con coherencia entre lo que creemos y lo que hacemos, permitiendo que nuestra fe sea visible en cada área de la vida." },
    { num: "05", key: "mision",      title: "Misión",         desc: "No existimos solo para nosotros mismos. Somos enviados a alcanzar a los que aún no conocen el amor de Cristo." },
    { num: "06", key: "excelencia",  title: "Excelencia",     desc: "Damos lo mejor de nosotros en todo lo que hacemos, como un acto de adoración y respeto a quien nos llamó." },
];

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

    /* ── Hero ── */
    const hero = (heroCms?.parsed && typeof heroCms.parsed === "object" && !Array.isArray(heroCms.parsed))
        ? heroCms.parsed as Record<string, unknown>
        : null;

    const heroEyebrow    = (hero?.eyebrow    as string) || "Nuestra Identidad";
    const heroTitleLead  = (hero?.title_lead as string) || "Iluminando el";
    const heroTitleAccent = (hero?.title_accent as string) || "camino juntos.";
    const heroDescription = (hero?.description as string) || "Una iglesia viva y en crecimiento que existe para conectar corazones con Dios y entre sí, fundamentada en la Palabra y movida por el amor.";

    /* ── Feed / About ── */
    const about = (aboutCms?.parsed && typeof aboutCms.parsed === "object" && !Array.isArray(aboutCms.parsed))
        ? aboutCms.parsed as Record<string, unknown>
        : null;

    const stats  = (Array.isArray(about?.stats)  ? about!.stats  as typeof DEFAULT_STATS  : DEFAULT_STATS);
    const valores = (Array.isArray(about?.valores) ? about!.valores as typeof DEFAULT_VALORES : DEFAULT_VALORES);

    const visionText  = (about?.vision_text  as string) || "Ser una comunidad de fe que <strong>transforma vidas, familias y ciudades</strong> a través del poder del Evangelio, levantando discípulos que reflejen el carácter de Cristo en cada esfera de la sociedad.";
    const misionText  = (about?.mision_text  as string) || "Guiar, equipar y movilizar a cada persona de nuestra comunidad mediante la <strong>enseñanza bíblica profunda</strong>, el compañerismo genuino y el servicio desinteresado — llevando la luz de Cristo a donde haya oscuridad.";

    const founderBio  = (about?.founder_bio  as string) || "";
    const founderBio2 = (about?.founder_bio2 as string) || "";
    const founderCtaTeam = (about?.founder_cta_team as string) || "Conoce al equipo";
    const founderCtaVisit = (about?.founder_cta_visit as string) || "Visítanos";
    const valuesEyebrow = (about?.values_eyebrow as string) || "Lo que nos define";

    const quoteText   = (about?.quote_text   as string) || "";
    const quoteAuthor = (about?.quote_author as string) || "";

    const ctaViewSedes = (about?.cta_view_sedes as string) || "Ver sedes";
    const ctaViewEvents = (about?.cta_view_events as string) || "Próximos eventos";
    const breadcrumbInicio = (about?.breadcrumbInicio as string) || "Inicio";
    const breadcrumbPage = (about?.breadcrumbPage as string) || "Quiénes Somos";

    return (
        <main className="min-h-screen bg-site-background pt-[88px] overflow-hidden">

                {/* ── HERO ── */}
                <section className="relative ccf-section overflow-hidden">
                    <div className="absolute inset-0 pointer-events-none">
                        <div
                            className="absolute -top-40 -right-40 w-[600px] h-[600px] rounded-full blur-3xl"
                            style={{ background: "radial-gradient(ellipse, var(--site-glow-subtle) 0%, transparent 70%)" }}
                        />
                        <div
                            className="absolute -bottom-40 -left-40 w-[400px] h-[400px] rounded-full blur-3xl"
                            style={{ background: "radial-gradient(ellipse, var(--site-glow-subtle) 0%, transparent 70%)" }}
                        />
                    </div>
                    <div className="relative z-10 ccf-container">
                        <div className="flex items-center gap-2 text-xs text-site-outline mb-8">
                            <Link href="/" className="hover:text-site-primary transition-colors">{breadcrumbInicio}</Link>
                            <ChevronRight size={12} />
                            <span className="text-site-on-surface-variant">{breadcrumbPage}</span>
                        </div>

                        <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-site-primary mb-5">
                            <Sparkles size={12} className="animate-pulse" /> {heroEyebrow}
                        </span>
                        <h1
                            className="max-w-4xl font-black ccf-display text-5xl sm:text-6xl lg:text-7xl mb-6"
                        >
                            <span className="text-site-on-surface">{heroTitleLead}</span>
                            <br />
                            <span
                                className="italic"
                                style={{
                                    background: "var(--site-hero-cta-gradient)",
                                    WebkitBackgroundClip: "text",
                                    WebkitTextFillColor: "transparent",
                                }}
                            >
                                {heroTitleAccent}
                            </span>
                        </h1>
                        <RichText
                            html={heroDescription}
                            className="ccf-body text-lg md:text-xl text-site-on-surface-variant max-w-2xl mb-10 [&_strong]:text-site-on-surface"
                        />

                        {/* Stats */}
                        <div className="flex flex-wrap gap-8 md:gap-12">
                            {stats.map((s, i) => (
                                <div key={i}>
                                    <p className="text-3xl md:text-4xl font-black text-site-primary">{s.value}</p>
                                    <p className="text-xs font-bold uppercase tracking-widest text-site-outline mt-0.5">{s.label}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </section>

                {/* ── VISIÓN Y MISIÓN ── */}
                <section className="ccf-section bg-site-surface-container-low">
                    <div className="ccf-container grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8">
                        {/* Visión */}
                        <div className="ccf-card relative p-8 md:p-10 overflow-hidden bg-site-surface">
                            <div className="absolute top-6 right-6 opacity-[0.06] text-site-primary">
                                <Target size={100} />
                            </div>
                            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-site-primary/10 border border-site-primary/20 text-site-primary text-[10px] font-bold uppercase tracking-widest mb-5">
                                <Target size={11} /> Visión
                            </div>
                            <h2 className="ccf-headline text-2xl md:text-3xl font-black text-site-on-surface mb-4">
                                {(about?.vision_title as string) || "¿A dónde vamos?"}
                            </h2>
                            <RichText
                                html={visionText}
                                className="ccf-body text-base md:text-lg text-site-on-surface-variant [&_strong]:text-site-on-surface"
                            />
                        </div>

                        {/* Misión */}
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
                            <h2 className="ccf-headline text-2xl md:text-3xl font-black text-white mb-4">
                                {(about?.mision_title as string) || "¿Por qué existimos?"}
                            </h2>
                            <RichText
                                html={misionText}
                                className="ccf-body text-base md:text-lg text-white/85 [&_strong]:text-white"
                            />
                        </div>
                    </div>
                </section>

                {/* ── FUNDADORES ── */}
                <section className="ccf-section">
                    <div className="ccf-container flex flex-col lg:flex-row items-center gap-16 lg:gap-20">
                        {/* Fotos */}
                        <div className="w-full lg:w-5/12 relative shrink-0">
                            <div className="relative h-[340px] sm:h-[420px] md:h-[520px] overflow-hidden ccf-image">
                                <div className="absolute left-0 top-0 w-[58%] aspect-[3/4] rounded-2xl overflow-hidden shadow-2xl ring-1 ring-site-outline-variant/20 z-10">
                                    {about?.founder1_image ? (
                                        <Image
                                            src={about.founder1_image as string}
                                            alt={(about?.founder1_name as string) || "Pastor Luis Ricardo Meza Gutiérrez"}
                                            fill
                                            className="object-cover object-top"
                                        />
                                    ) : (
                                        <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-[hsl(var(--primary))/0.18] to-[hsl(var(--surface-2))/0.35]">
                                            <span className="text-4xl font-black text-[hsl(var(--primary))/0.35]">
                                                {((about?.founder1_name as string) || "L").charAt(0)}
                                            </span>
                                        </div>
                                    )}
                                    <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent" />
                                    <div className="absolute bottom-3 left-3 right-3">
                                        <p className="text-white text-xs font-bold drop-shadow-sm">
                                            {(about?.founder1_name as string) || "Luis Ricardo Meza G."}
                                        </p>
                                        <p className="text-white/70 text-[10px] font-medium uppercase tracking-wider drop-shadow-sm">
                                            {(about?.founder1_role as string) || "Pastor Principal"}
                                        </p>
                                    </div>
                                </div>
                                <div className="absolute right-0 bottom-0 w-[55%] aspect-[3/4] rounded-2xl overflow-hidden shadow-2xl ring-1 ring-site-outline-variant/20 z-20">
                                    {about?.founder2_image ? (
                                        <Image
                                            src={about.founder2_image as string}
                                            alt={(about?.founder2_name as string) || "Pastor Histar Ariza Herrera"}
                                            fill
                                            className="object-cover object-top"
                                        />
                                    ) : (
                                        <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-[hsl(var(--primary))/0.18] to-[hsl(var(--surface-2))/0.35]">
                                            <span className="text-4xl font-black text-[hsl(var(--primary))/0.35]">
                                                {((about?.founder2_name as string) || "H").charAt(0)}
                                            </span>
                                        </div>
                                    )}
                                    <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent" />
                                    <div className="absolute bottom-3 left-3 right-3">
                                        <p className="text-white text-xs font-bold drop-shadow-sm">
                                            {(about?.founder2_name as string) || "Histar Ariza Herrera"}
                                        </p>
                                        <p className="text-white/70 text-[10px] font-medium uppercase tracking-wider drop-shadow-sm">
                                            {(about?.founder2_role as string) || "Pastor Principal"}
                                        </p>
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
                            <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-site-primary mb-4">
                                <Heart size={12} /> {(about?.founder_label as string) || "Nuestros Pastores Principales"}
                            </span>
                            <h2 className="ccf-headline text-3xl md:text-4xl lg:text-5xl font-black text-site-on-surface mb-5">
                                {(about?.founder_title as string) || "Un llamado a construir"}
                                <br />
                                <span className="text-site-primary">
                                    {(about?.founder_title_accent as string) || "una familia de fe"}
                                </span>
                            </h2>
                            <div className="ccf-body space-y-4 text-base md:text-lg text-site-on-surface-variant [&_strong]:text-site-on-surface [&_em]:text-site-outline">
                                <RichText html={founderBio} />
                                <RichText html={founderBio2} />
                            </div>
                            <div className="mt-10 flex flex-wrap gap-4">
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
                                <Link
                                    href="/sedes"
                                    className="ccf-button bg-site-surface-container text-site-on-surface-variant border border-site-outline-variant/30"
                                >
                                    {founderCtaVisit}
                                </Link>
                            </div>
                        </div>
                    </div>
                </section>

                {/* ── VALORES ── */}
                <section className="ccf-section bg-site-surface-container-low">
                    <div className="ccf-container">
                        <div className="text-center mb-14">
                            <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-site-primary mb-3">
                                <Sparkles size={12} /> {valuesEyebrow}
                            </span>
                            <h2 className="ccf-headline text-3xl md:text-4xl lg:text-5xl font-black text-site-on-surface mb-4">
                                {(about?.valores_title as string) || "Valores que nos Guían"}
                            </h2>
                            <div className="h-1 w-16 rounded-full bg-site-primary mx-auto" />
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 md:gap-8">
                            {valores.map((v: any, idx: number) => (
                                <div
                                    key={v.key || v.num || idx}
                                    className="ccf-card group p-6 md:p-8 bg-site-surface"
                                    style={{ "--tw-shadow-color": "var(--site-glow-intense)" } as React.CSSProperties}
                                >
                                    <div className="flex items-start justify-between mb-5">
                                        <div className="w-10 h-10 rounded-xl bg-site-primary/10 flex items-center justify-center text-site-primary border border-site-primary/15">
                                            {VALOR_ICONS[v.key] || <Sparkles size={20} />}
                                        </div>
                                        <span className="text-4xl font-black text-site-outline-variant/40 select-none">
                                            {v.num || String(idx + 1).padStart(2, "0")}
                                        </span>
                                    </div>
                                    <h3 className="text-lg font-black text-site-on-surface mb-2 tracking-tight">{v.title}</h3>
                                    <p className="ccf-body text-sm text-site-on-surface-variant">{v.desc}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </section>

                {/* ── CITA ── */}
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
                                <p className="text-xs font-bold uppercase tracking-widest text-site-primary mt-0.5">
                                    {(about?.quote_subtitle as string) || ""}
                                </p>
                            </div>
                            <div className="h-px w-12 bg-gradient-to-l from-transparent to-site-primary/30" />
                        </div>
                    </div>
                </section>

                {/* ── CTA ── */}
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
                                <h2 className="ccf-headline text-3xl md:text-4xl font-black text-white mb-4">
                                    {(about?.cta_title as string) || "¿Listo para ser parte?"}
                                </h2>
                                <RichText
                                    html={(about?.cta_desc as string) || "Ven a conocernos. Tenemos puertas abiertas y un lugar reservado para ti y tu familia."}
                                    className="ccf-body text-base md:text-lg text-white/80 max-w-xl mx-auto mb-8"
                                />
                                <div className="flex flex-wrap items-center justify-center gap-4">
                                    <Link
                                        href="/sedes"
                                        className="ccf-button bg-[hsl(var(--bg-primary))] text-site-primary shadow-xl"
                                    >
                                        {ctaViewSedes} <ArrowRight size={14} />
                                    </Link>
                                    <Link
                                        href="/eventos"
                                        className="ccf-button bg-white/15 border border-white/25 text-white hover:bg-white/20"
                                    >
                                        {ctaViewEvents}
                                    </Link>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

        </main>
    );
}
