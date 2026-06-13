"use client";

import React from "react";
import Image from "next/image";
import Link from "next/link";
import { Target, Sparkles, Quote, Heart, Users, BookOpen, Cross, ChevronRight, ArrowRight } from "lucide-react";
import { useContentBlock } from "@/hooks/useContent";
import RichText from "@/components/public/RichText";
import CmsPageOverride from "@/components/public/cms/CmsPageOverride";

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
    const { data: heroCms }   = useContentBlock("faro_about_hero");
    const { data: aboutCms }  = useContentBlock("faro_about_feed");

    /* ── Hero ── */
    const hero = (heroCms?.parsed && typeof heroCms.parsed === "object" && !Array.isArray(heroCms.parsed))
        ? heroCms.parsed as Record<string, unknown>
        : null;

    const heroEyebrow    = (hero?.eyebrow    as string) || "Nuestra Identidad";
    const heroTitleLead  = (hero?.title_lead as string) || "Iluminando el";
    const heroTitleAccent = (hero?.title_accent as string) || "camino juntos.";
    const heroDescription = (hero?.description as string) || "Somos la <strong>Comunidad Cristiana El Faro</strong>, una iglesia viva y en crecimiento que existe para conectar corazones con Dios y entre sí, fundamentada en la Palabra y movida por el amor.";

    /* ── Feed / About ── */
    const about = (aboutCms?.parsed && typeof aboutCms.parsed === "object" && !Array.isArray(aboutCms.parsed))
        ? aboutCms.parsed as Record<string, unknown>
        : null;

    const stats  = (Array.isArray(about?.stats)  ? about!.stats  as typeof DEFAULT_STATS  : DEFAULT_STATS);
    const valores = (Array.isArray(about?.valores) ? about!.valores as typeof DEFAULT_VALORES : DEFAULT_VALORES);

    const visionText  = (about?.vision_text  as string) || "Ser una comunidad de fe que <strong>transforma vidas, familias y ciudades</strong> a través del poder del Evangelio, levantando discípulos que reflejen el carácter de Cristo en cada esfera de la sociedad.";
    const misionText  = (about?.mision_text  as string) || "Guiar, equipar y movilizar a cada persona de nuestra comunidad mediante la <strong>enseñanza bíblica profunda</strong>, el compañerismo genuino y el servicio desinteresado — llevando la luz de Cristo a donde haya oscuridad.";

    const founderBio  = (about?.founder_bio  as string) || "La Comunidad Cristiana El Faro nació de un profundo encuentro con la paternidad de Dios. Nuestros pastores principales, <strong>Luis Ricardo Meza Gutiérrez</strong> e <strong>Histar Ariza Herrera</strong>, han dedicado más de dos décadas a construir una iglesia que sea verdaderamente una casa — un lugar donde cada persona sea vista, amada y formada.";
    const founderBio2 = (about?.founder_bio2 as string) || "Desde sus inicios, el ADN de El Faro ha sido claro: <em>sana doctrina, corazón pastoral y vida en comunidad</em>. Una iglesia que no teme enseñar la Palabra en su profundidad y que, al mismo tiempo, envuelve a cada persona con la calidez del amor de Cristo.";

    const quoteText   = (about?.quote_text   as string) || "La luz que encontramos en El Faro no es para guardarla — es para guiar a otros que aún caminan en la oscuridad.";
    const quoteAuthor = (about?.quote_author as string) || "Pastor Histar Ariza Herrera";

    return (
        <CmsPageOverride slug="nosotros">
            <main className="min-h-screen bg-faro-background pt-[88px] overflow-hidden">

                {/* ── HERO ── */}
                <section className="relative px-4 md:px-6 lg:px-8 xl:px-12 py-16 md:py-24 lg:py-28 overflow-hidden">
                    <div className="absolute inset-0 pointer-events-none">
                        <div
                            className="absolute -top-40 -right-40 w-[600px] h-[600px] rounded-full blur-3xl"
                            style={{ background: "radial-gradient(ellipse, var(--faro-glow-subtle) 0%, transparent 70%)" }}
                        />
                        <div
                            className="absolute -bottom-40 -left-40 w-[400px] h-[400px] rounded-full blur-3xl"
                            style={{ background: "radial-gradient(ellipse, var(--faro-glow-subtle) 0%, transparent 70%)" }}
                        />
                    </div>
                    <div className="relative z-10 max-w-7xl mx-auto">
                        <div className="flex items-center gap-2 text-xs text-faro-outline mb-8">
                            <Link href="/" className="hover:text-faro-primary transition-colors">Inicio</Link>
                            <ChevronRight size={12} />
                            <span className="text-faro-on-surface-variant">Quiénes Somos</span>
                        </div>

                        <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-faro-primary mb-5">
                            <Sparkles size={12} className="animate-pulse" /> {heroEyebrow}
                        </span>
                        <h1
                            className="font-black tracking-tight leading-[0.95] mb-6"
                            style={{ fontSize: "clamp(2.8rem, 7vw, 6.5rem)" }}
                        >
                            <span className="text-faro-on-surface">{heroTitleLead}</span>
                            <br />
                            <span
                                className="italic"
                                style={{
                                    background: "var(--faro-hero-cta-gradient)",
                                    WebkitBackgroundClip: "text",
                                    WebkitTextFillColor: "transparent",
                                }}
                            >
                                {heroTitleAccent}
                            </span>
                        </h1>
                        <RichText
                            html={heroDescription}
                            className="text-lg md:text-xl text-faro-on-surface-variant leading-relaxed max-w-2xl mb-10 [&_strong]:text-faro-on-surface"
                        />

                        {/* Stats */}
                        <div className="flex flex-wrap gap-8 md:gap-12">
                            {stats.map((s, i) => (
                                <div key={i}>
                                    <p className="text-3xl md:text-4xl font-black text-faro-primary">{s.value}</p>
                                    <p className="text-xs font-bold uppercase tracking-widest text-faro-outline mt-0.5">{s.label}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </section>

                {/* ── VISIÓN Y MISIÓN ── */}
                <section className="px-4 md:px-6 lg:px-8 xl:px-12 py-16 md:py-20 bg-faro-surface-container-low">
                    <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Visión */}
                        <div className="relative rounded-2xl p-8 md:p-10 overflow-hidden bg-faro-surface border border-faro-outline-variant/20 shadow-sm">
                            <div className="absolute top-6 right-6 opacity-[0.06] text-faro-primary">
                                <Target size={100} />
                            </div>
                            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-faro-primary/10 border border-faro-primary/20 text-faro-primary text-[10px] font-bold uppercase tracking-widest mb-5">
                                <Target size={11} /> Visión
                            </div>
                            <h2 className="text-2xl md:text-3xl font-black text-faro-on-surface tracking-tight leading-tight mb-4">
                                {(about?.vision_title as string) || "¿A dónde vamos?"}
                            </h2>
                            <RichText
                                html={visionText}
                                className="text-base md:text-lg text-faro-on-surface-variant leading-relaxed [&_strong]:text-faro-on-surface"
                            />
                        </div>

                        {/* Misión */}
                        <div
                            className="relative rounded-2xl p-8 md:p-10 overflow-hidden shadow-2xl"
                            style={{
                                background: "var(--faro-hero-cta-gradient)",
                                boxShadow: "0 20px 60px -10px var(--faro-glow-intense)",
                            }}
                        >
                            <div className="absolute top-6 right-6 opacity-10">
                                <Sparkles size={100} className="text-white" />
                            </div>
                            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/15 border border-white/20 text-white text-[10px] font-bold uppercase tracking-widest mb-5">
                                <Sparkles size={11} /> Misión
                            </div>
                            <h2 className="text-2xl md:text-3xl font-black text-white tracking-tight leading-tight mb-4">
                                {(about?.mision_title as string) || "¿Por qué existimos?"}
                            </h2>
                            <RichText
                                html={misionText}
                                className="text-base md:text-lg text-white/85 leading-relaxed [&_strong]:text-white"
                            />
                        </div>
                    </div>
                </section>

                {/* ── FUNDADORES ── */}
                <section className="px-4 md:px-6 lg:px-8 xl:px-12 py-20 md:py-28">
                    <div className="max-w-7xl mx-auto flex flex-col lg:flex-row items-center gap-16 lg:gap-20">
                        {/* Fotos */}
                        <div className="w-full lg:w-5/12 relative shrink-0">
                            <div className="relative h-[480px] md:h-[560px]">
                                <div className="absolute left-0 top-0 w-[58%] aspect-[3/4] rounded-2xl overflow-hidden shadow-2xl ring-1 ring-faro-outline-variant/20 z-10">
                                    <Image
                                        src={(about?.founder1_image as string) || "/pastores/luis_ricardo_meza_1777656765476.png"}
                                        alt={(about?.founder1_name as string) || "Pastor Luis Ricardo Meza Gutiérrez"}
                                        fill
                                        className="object-cover object-top"
                                    />
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
                                <div className="absolute right-0 bottom-0 w-[55%] aspect-[3/4] rounded-2xl overflow-hidden shadow-2xl ring-1 ring-faro-outline-variant/20 z-20">
                                    <Image
                                        src={(about?.founder2_image as string) || "/pastores/histar_ariza_1777656780660.png"}
                                        alt={(about?.founder2_name as string) || "Pastor Histar Ariza Herrera"}
                                        fill
                                        className="object-cover object-top"
                                    />
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
                                    style={{ background: "var(--faro-glow-subtle)" }}
                                />
                            </div>
                        </div>

                        {/* Texto */}
                        <div className="w-full lg:w-7/12">
                            <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-faro-primary mb-4">
                                <Heart size={12} /> {(about?.founder_label as string) || "Nuestros Pastores Principales"}
                            </span>
                            <h2 className="text-3xl md:text-4xl lg:text-5xl font-black text-faro-on-surface tracking-tight leading-tight mb-5">
                                {(about?.founder_title as string) || "Un llamado a construir"}
                                <br />
                                <span className="text-faro-primary">
                                    {(about?.founder_title_accent as string) || "una familia de fe"}
                                </span>
                            </h2>
                            <div className="space-y-4 text-base md:text-lg text-faro-on-surface-variant leading-relaxed [&_strong]:text-faro-on-surface [&_em]:text-faro-outline">
                                <RichText html={founderBio} />
                                <RichText html={founderBio2} />
                            </div>
                            <div className="mt-8 flex flex-wrap gap-3">
                                <Link
                                    href="/pastores"
                                    className="inline-flex items-center gap-2.5 px-6 py-3 rounded-xl text-faro-on-primary text-xs font-bold uppercase tracking-wider hover:scale-105 transition-all"
                                    style={{
                                        background: "var(--faro-cta-gradient)",
                                        boxShadow: "var(--faro-cta-shadow)",
                                    }}
                                >
                                    Conoce al equipo <ArrowRight size={14} />
                                </Link>
                                <Link
                                    href="/sedes"
                                    className="inline-flex items-center gap-2.5 px-6 py-3 rounded-xl bg-faro-surface-container text-faro-on-surface-variant text-xs font-bold uppercase tracking-wider hover:scale-105 transition-all border border-faro-outline-variant/30"
                                >
                                    Visítanos
                                </Link>
                            </div>
                        </div>
                    </div>
                </section>

                {/* ── VALORES ── */}
                <section className="px-4 md:px-6 lg:px-8 xl:px-12 py-20 md:py-24 bg-faro-surface-container-low">
                    <div className="max-w-7xl mx-auto">
                        <div className="text-center mb-14">
                            <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-faro-primary mb-3">
                                <Sparkles size={12} /> Lo que nos define
                            </span>
                            <h2 className="text-3xl md:text-4xl lg:text-5xl font-black text-faro-on-surface tracking-tight mb-4">
                                {(about?.valores_title as string) || "Valores que nos Guían"}
                            </h2>
                            <div className="h-1 w-16 rounded-full bg-faro-primary mx-auto" />
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                            {valores.map((v: any, idx: number) => (
                                <div
                                    key={v.key || v.num || idx}
                                    className="group p-6 md:p-7 rounded-2xl bg-faro-surface border border-faro-outline-variant/20 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-400"
                                    style={{ "--tw-shadow-color": "var(--faro-glow-intense)" } as React.CSSProperties}
                                >
                                    <div className="flex items-start justify-between mb-5">
                                        <div className="w-10 h-10 rounded-xl bg-faro-primary/10 flex items-center justify-center text-faro-primary border border-faro-primary/15">
                                            {VALOR_ICONS[v.key] || <Sparkles size={20} />}
                                        </div>
                                        <span className="text-4xl font-black text-faro-outline-variant/40 select-none">
                                            {v.num || String(idx + 1).padStart(2, "0")}
                                        </span>
                                    </div>
                                    <h3 className="text-lg font-black text-faro-on-surface mb-2 tracking-tight">{v.title}</h3>
                                    <p className="text-sm text-faro-on-surface-variant leading-relaxed">{v.desc}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </section>

                {/* ── CITA ── */}
                <section className="px-4 md:px-6 lg:px-8 xl:px-12 py-20 md:py-28">
                    <div className="max-w-4xl mx-auto text-center">
                        <Quote size={48} className="mx-auto mb-6 text-faro-primary/20" />
                        <blockquote className="text-2xl md:text-3xl lg:text-4xl font-black text-faro-on-surface leading-tight italic tracking-tight mb-6">
                            &ldquo;{quoteText}&rdquo;
                        </blockquote>
                        <div className="flex items-center justify-center gap-3">
                            <div className="h-px w-12 bg-gradient-to-r from-transparent to-faro-primary/30" />
                            <div>
                                <p className="font-bold text-faro-on-surface">{quoteAuthor}</p>
                                <p className="text-xs font-bold uppercase tracking-widest text-faro-primary mt-0.5">
                                    {(about?.quote_subtitle as string) || "Comunidad Cristiana El Faro"}
                                </p>
                            </div>
                            <div className="h-px w-12 bg-gradient-to-l from-transparent to-faro-primary/30" />
                        </div>
                    </div>
                </section>

                {/* ── CTA ── */}
                <section className="px-4 md:px-6 lg:px-8 xl:px-12 pb-20 md:pb-28">
                    <div className="max-w-7xl mx-auto">
                        <div
                            className="relative rounded-3xl overflow-hidden p-10 md:p-14 text-center"
                            style={{
                                background: "var(--faro-cta-gradient)",
                                boxShadow: "var(--faro-cta-shadow)",
                            }}
                        >
                            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(255,255,255,0.12),transparent_60%)] pointer-events-none" />
                            <div className="relative z-10">
                                <h2 className="text-3xl md:text-4xl font-black text-white tracking-tight mb-4">
                                    {(about?.cta_title as string) || "¿Listo para ser parte?"}
                                </h2>
                                <RichText
                                    html={(about?.cta_desc as string) || "Ven a conocernos. Tenemos puertas abiertas y un lugar reservado para ti y tu familia."}
                                    className="text-base md:text-lg text-white/80 leading-relaxed max-w-xl mx-auto mb-8"
                                />
                                <div className="flex flex-wrap items-center justify-center gap-3">
                                    <Link
                                        href="/sedes"
                                        className="inline-flex items-center gap-2.5 px-7 py-3.5 rounded-xl bg-white text-faro-primary text-xs font-black uppercase tracking-wider hover:scale-105 transition-all shadow-xl"
                                    >
                                        Ver sedes <ArrowRight size={14} />
                                    </Link>
                                    <Link
                                        href="/eventos"
                                        className="inline-flex items-center gap-2.5 px-7 py-3.5 rounded-xl bg-white/15 border border-white/25 text-white text-xs font-bold uppercase tracking-wider hover:scale-105 hover:bg-white/20 transition-all"
                                    >
                                        Próximos eventos
                                    </Link>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

            </main>
        </CmsPageOverride>
    );
}
