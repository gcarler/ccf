"use client";


import React from "react";
import Image from "next/image";
import { motion } from "framer-motion";
import { Target, Sparkles, Quote } from "lucide-react";
import { useContentBlock } from "@/hooks/useContent";

export default function NosotrosPage() {
    const { data: heroContent } = useContentBlock("faro_about_hero");
    const { data: aboutContent } = useContentBlock("faro_about_feed");

    const aboutData = (aboutContent?.parsed && typeof aboutContent.parsed === "object" && !Array.isArray(aboutContent.parsed))
        ? aboutContent.parsed as Record<string, unknown>
        : null;

    const heroEyebrow = heroContent?.eyebrow || "Nuestra Identidad";
    const heroTitleLead = heroContent?.title_lead || "Iluminando el";
    const heroTitleAccent = heroContent?.title_accent || "camino juntos";
    const heroDescription = heroContent?.description || "Somos una comunidad vibrante dedicada a guiar a las personas hacia una vida llena de propósito y luz a través del mensaje de esperanza.";

    return (
        <main className="pt-[88px]">
            {/* ── HERO EDITORIAL ────────────────────────────────── */}
            <section className="relative px-3 md:px-4 lg:px-24 py-1.5 overflow-hidden">
                <div className="absolute inset-0 bg-light-glow pointer-events-none opacity-50" />
                <div className="max-w-6xl mx-auto relative z-10">
                    <motion.div 
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="max-w-3xl"
                    >
                        <span 
                            className="text-xs font-semibold uppercase tracking-wide mb-3 block"
                            style={{ color: "var(--faro-primary)" }}
                        >
                            {heroEyebrow}
                        </span>
                        <h1 
                            className="font-bold tracking-tighter leading-[0.9] mb-3"
                            style={{ 
                                fontSize: "clamp(3.5rem, 8vw, 7.5rem)",
                                color: "var(--faro-on-background)"
                            }}
                        >
                            {heroTitleLead} <br/>
                            <span 
                                className="italic"
                                style={{ 
                                    background: "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary))",
                                    WebkitBackgroundClip: "text",
                                    WebkitTextFillColor: "transparent"
                                }}
                            >
                                {heroTitleAccent}.
                            </span>
                        </h1>
                        <p 
                            className="text-xl md:text-lg leading-relaxed opacity-80"
                            style={{ color: "var(--faro-on-surface-variant)" }}
                        >
                            {heroDescription}
                        </p>
                    </motion.div>
                </div>
            </section>

            {/* ── VISIÓN Y MISIÓN: BENTO GRID ────────────────────── */}
            <section 
                className="py-1.5 px-3 md:px-4 lg:px-24"
                style={{ background: "var(--faro-surface-container-low)" }}
            >
                <div className="max-w-6xl mx-auto">
                    <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
                        <motion.div 
                            initial={{ opacity: 0, x: -20 }}
                            whileInView={{ opacity: 1, x: 0 }}
                            viewport={{ once: true }}
                            className="md:col-span-7 rounded-lg p-4 relative overflow-hidden flex flex-col justify-end min-h-[400px]"
                            style={{ background: "var(--faro-surface-container-high)" }}
                        >
                            <div className="absolute top-10 left-10 opacity-20">
                                <Target size={80} style={{ color: "var(--faro-primary)" }} />
                            </div>
                            <div className="relative z-10">
                                <h3 className="text-lg font-black mb-3" style={{ color: "var(--faro-on-surface)" }}>Nuestra Visión</h3>
                                <p className="text-lg leading-relaxed opacity-80" style={{ color: "var(--faro-on-surface-variant)" }}>
                                    Ser un faro global de transformación espiritual, donde cada individuo descubra su luz interior y se convierta en un agente de cambio positivo en su sociedad, fundamentado en el amor y la verdad.
                                </p>
                            </div>
                        </motion.div>

                        <motion.div 
                            initial={{ opacity: 0, x: 20 }}
                            whileInView={{ opacity: 1, x: 0 }}
                            viewport={{ once: true }}
                            className="md:col-span-5 rounded-lg p-4 flex flex-col justify-between border"
                            style={{ 
                                background: "var(--faro-surface-bright)",
                                borderColor: "var(--faro-outline-variant)"
                            }}
                        >
                            <Sparkles size={48} style={{ color: "var(--faro-secondary)" }} className="mb-3" />
                            <div>
                                <h3 className="text-lg font-black mb-3" style={{ color: "var(--faro-on-surface)" }}>Nuestra Misión</h3>
                                <p className="text-lg leading-relaxed opacity-80" style={{ color: "var(--faro-on-surface-variant)" }}>
                                    Guiar, equipar y movilizar a la comunidad a través de la enseñanza práctica, el compañerismo genuino y el servicio desinteresado, reflejando el carácter de Jesús.
                                </p>
                            </div>
                        </motion.div>
                    </div>
                </div>
            </section>

            {/* ── FUNDADORES ────────────────────────────────────── */}
            <section className="py-1.5 px-3 md:px-4 lg:px-24">
                <div className="max-w-6xl mx-auto flex flex-col lg:flex-row items-center gap-20">
                    <div className="w-full lg:w-1/2 relative">
                        <div className="relative z-10 aspect-[4/5] rounded-lg overflow-hidden shadow-2xl">
                            <Image
                                className="object-cover"
                                alt={(aboutData?.founder_name as string) || "Fundadores"}
                                src={(aboutData?.founder_image as string) || "https://picsum.photos/seed/1516585424602-c210be8163f5/800/600"}
                                fill
                                priority
                            />
                        </div>
                        <div 
                            className="absolute -bottom-8 -right-8 w-64 h-48 blur-[100px] -z-10 rounded-full"
                            style={{ background: "rgba(1, 138, 189, 0.15)" }}
                        />
                    </div>
                    <div className="w-full lg:w-1/2">
                        <span className="text-xs font-semibold uppercase tracking-wide mb-4 block" style={{ color: "var(--faro-primary)" }}>
                            {aboutData?.founder_label as string || "Nuestros Fundadores"}
                        </span>
                        <h2 className="text-xl md:text-xl font-black mb-3 leading-tight" style={{ color: "var(--faro-on-background)" }}>
                            {(aboutData?.founder_name as string) || "Nuestros Fundadores"}
                        </h2>
                        <div className="space-y-6 text-lg leading-relaxed opacity-80" style={{ color: "var(--faro-on-surface-variant)" }}>
                            <p>
                                {(aboutData?.founder_bio as string) || "Nuestros fundadores han dedicado su vida a construir una comunidad vibrante de fe, amor y servicio."}
                            </p>
                            <p>
                                Su enfoque editorial y estético no es solo una elección visual, sino una declaración de que la espiritualidad puede ser clara, profesional y profundamente hermosa.
                            </p>
                            {aboutData && Array.isArray(aboutData.stats) ? (
                                <div className="pt-8 flex gap-3">
                                    {(aboutData.stats as Array<{ value: string; label: string; color?: string }>).map((stat, i) => (
                                        <React.Fragment key={stat.label}>
                                            {i > 0 && <div className="w-px h-8 bg-slate-200 dark:bg-white/10" />}
                                            <div>
                                                <span className="text-lg font-black block" style={{ color: stat.color || "var(--faro-primary)" }}>{stat.value}</span>
                                                <span className="text-[10px] font-semibold uppercase tracking-wide opacity-50">{stat.label}</span>
                                            </div>
                                        </React.Fragment>
                                    ))}
                                </div>
                            ) : null}
                        </div>
                    </div>
                </div>
            </section>

            {/* ── VALORES ───────────────────────────────────────── */}
            <section 
                className="py-1.5 px-3 md:px-4 lg:px-24"
                style={{ background: "var(--faro-surface-container-lowest)" }}
            >
                <div className="max-w-6xl mx-auto">
                    <div className="mb-20 text-center">
                        <h2 className="text-lg font-black" style={{ color: "var(--faro-on-surface)" }}>Valores que nos Guían</h2>
                        <div 
                            className="h-1.5 w-24 mx-auto mt-3 rounded-full"
                            style={{ background: "linear-gradient(to right, var(--faro-primary), var(--faro-secondary))" }}
                        />
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        {(Array.isArray(aboutData?.valores)
                            ? aboutData.valores as Array<{ num: string; title: string; desc: string }>
                            : [
                                { num: "01", title: "Integridad", desc: "Vivir con transparencia, permitiendo que nuestra luz interior sea coherente con nuestras acciones." },
                                { num: "02", title: "Innovación", desc: "Abrazamos el futuro y las nuevas formas de conectar sin perder la esencia de los principios eternos." },
                                { num: "03", title: "Amor Radical", desc: "Un compromiso inquebrantable de servir a todos, sin importar su origen o camino recorrido." }
                            ]
                        ).map((v) => (
                            <div key={v.num} className="space-y-4">
                                <div className="text-xl font-black opacity-10" style={{ color: "var(--faro-primary)" }}>{v.num}</div>
                                <h4 className="text-lg font-black" style={{ color: "var(--faro-on-surface)" }}>{v.title}</h4>
                                <p className="leading-relaxed opacity-70" style={{ color: "var(--faro-on-surface-variant)" }}>{v.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── QUOTE EDITORIAL ───────────────────────────────── */}
            <section className="py-1.5 px-3 md:px-4 text-center">
                <div className="max-w-3xl mx-auto">
                    <Quote size={60} className="mx-auto mb-3 opacity-20" style={{ color: "var(--faro-primary)" }} />
                    <blockquote
                        className="text-xl md:text-xl font-black leading-tight italic mb-3"
                        style={{ color: "var(--faro-on-surface)" }}
                    >
                        {aboutData?.quote_text as string || "La luz que encontramos en FARO no es para guardarla, es para guiar a otros que aún caminan en la oscuridad."}
                    </blockquote>
                    <p className="font-black text-xl" style={{ color: "var(--faro-on-surface)" }}>{aboutData?.quote_author as string || "Pastor Luis Ricardo Meza Gutiérrez"}</p>
                    <p className="text-xs font-semibold uppercase tracking-wide mt-2" style={{ color: "var(--faro-primary)" }}>{aboutData?.quote_subtitle as string || "Visión 2026"}</p>
                </div>
            </section>
        </main>
    );
}

