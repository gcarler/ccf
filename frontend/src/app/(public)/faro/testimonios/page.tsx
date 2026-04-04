"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Quote, Play, ArrowRight, Users } from "lucide-react";
import { useContentBlock } from "@/hooks/useContent";

interface Testimonial {
    id: number;
    content: string;
    emotion?: string;
    author?: { username: string };
    is_approved?: boolean;
    show_on_home?: boolean;
}

const FALLBACK: Testimonial[] = [
    {
        id: 1,
        content: "Encontré un propósito que nunca imaginé posible. La comunidad FARO me recibió sin juicios y me cambió la vida.",
        emotion: "Transformación",
        author: { username: "Elena Martínez" },
    },
    {
        id: 2,
        content: "Llegué a FARO buscando respuestas y encontré una familia que me aceptó tal cual soy.",
        emotion: "Comunidad",
        author: { username: "Lucía García" },
    },
    {
        id: 3,
        content: "El curso de fundamentos cambió mi perspectiva sobre el propósito de mi vida diaria.",
        emotion: "Formación",
        author: { username: "Carlos Méndez" },
    },
    {
        id: 4,
        content: "La paz que encontré aquí no tiene comparación. Mi familia también encontró su fe aquí.",
        emotion: "Fe",
        author: { username: "Roberto Sánchez" },
    },
];

export default function TestimoniosPage() {
    const { data: heroContent } = useContentBlock("faro_testimonios_hero");
    const { data: feedContent } = useContentBlock("faro_testimonials_feed");

    const heroEyebrow = heroContent?.eyebrow || "Impacto Real";
    const heroTitleLead = heroContent?.title_lead || "Historias de ";
    const heroTitleAccent = heroContent?.title_accent || "Transformación";
    const heroDescription = heroContent?.description || "Descubre cómo la fe y la comunidad han iluminado el camino de personas reales. No son solo palabras, son vidas cambiadas.";

    const testimonials = Array.isArray(feedContent?.parsed) ? feedContent?.parsed : FALLBACK;

    const display = testimonials.length > 0 ? testimonials : FALLBACK;
    const [featured, ...rest] = display;

    return (
        <main className="pt-[88px] pb-32">
            {/* ── HERO ──────────────────────────────────────────── */}
            <header
                className="relative px-6 md:px-16 lg:px-24 py-20 overflow-hidden"
                style={{ background: "var(--faro-surface-container-low)" }}
            >
                <div
                    className="absolute top-0 right-0 w-[500px] h-[500px] rounded-full blur-[120px] -translate-y-1/2 translate-x-1/3 pointer-events-none"
                    style={{ background: "rgba(0, 102, 143, 0.08)" }}
                />
                <div className="max-w-6xl mx-auto relative z-10">
                    <span
                        className="text-xs font-black uppercase tracking-[0.3em] block mb-4"
                        style={{ color: "var(--faro-primary)" }}
                    >
                        {heroEyebrow}
                    </span>
                    <h1
                        className="font-black tracking-tight leading-tight mb-6"
                        style={{
                            fontSize: "clamp(3rem, 7vw, 6rem)",
                            color: "var(--faro-on-background)",
                        }}
                    >
                        {heroTitleLead}{" "}
                        <span
                            className="italic"
                            style={{ color: "var(--faro-primary)" }}
                        >
                            {heroTitleAccent}
                        </span>
                    </h1>
                    <p
                        className="text-lg max-w-xl leading-relaxed"
                        style={{ color: "var(--faro-on-surface-variant)" }}
                    >
                        {heroDescription}
                    </p>
                </div>
            </header>

            {/* ── BENTO GRID ─────────────────────────────────────── */}
            <section className="px-6 md:px-16 lg:px-24 py-16 max-w-7xl mx-auto">
                <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
                    {/* Featured big card */}
                    <div
                        className="md:col-span-8 rounded-3xl overflow-hidden relative group min-h-[440px] flex flex-col justify-end"
                        style={{ background: "var(--faro-surface-container)" }}
                    >
                        <div
                            className="absolute inset-0"
                            style={{
                                background:
                                    "linear-gradient(to top, var(--faro-surface-container-lowest) 0%, transparent 60%)",
                            }}
                        />
                        {/* Avatar area */}
                        <div className="absolute top-8 left-8 flex items-center gap-3">
                            <div
                                className="w-14 h-14 rounded-2xl flex items-center justify-center text-xl font-black"
                                style={{
                                    background: "var(--faro-primary-container)",
                                    color: "var(--faro-primary)",
                                }}
                            >
                                {featured?.author?.username?.[0] ?? "E"}
                            </div>
                            <div>
                                <p
                                    className="font-black"
                                    style={{ color: "var(--faro-on-surface)" }}
                                >
                                    {featured?.author?.username ?? "Elena Martínez"}
                                </p>
                                <p
                                    className="text-xs font-bold uppercase tracking-wider"
                                    style={{ color: "var(--faro-primary)" }}
                                >
                                    {featured?.emotion ?? "Transformación"}
                                </p>
                            </div>
                        </div>
                        <div className="relative z-10 p-10">
                            <Quote
                                size={40}
                                className="mb-4"
                                style={{ color: "var(--faro-primary)", opacity: 0.6 }}
                            />
                            <p
                                className="text-2xl font-bold leading-snug mb-6"
                                style={{ color: "var(--faro-on-surface)" }}
                            >
                                "{featured?.content ?? FALLBACK[0].content}"
                            </p>
                        </div>
                    </div>

                    {/* Video testimonial preview */}
                    <div
                        className="md:col-span-4 rounded-3xl p-8 flex flex-col justify-between relative overflow-hidden"
                        style={{ background: "var(--faro-surface-container-high)" }}
                    >
                        <div>
                            <div
                                className="w-12 h-12 rounded-2xl flex items-center justify-center mb-6"
                                style={{
                                    background:
                                        "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary))",
                                }}
                            >
                                <Play size={20} color="white" />
                            </div>
                            <h4
                                className="font-black text-xl mb-3"
                                style={{ color: "var(--faro-on-surface)" }}
                            >
                                Testimonio en Video
                            </h4>
                            <p
                                className="text-sm leading-relaxed"
                                style={{ color: "var(--faro-on-surface-variant)" }}
                            >
                                Mira la historia de Lucas y su camino hacia la recuperación a
                                través del grupo de apoyo FARO.
                            </p>
                        </div>
                        <button
                            className="mt-8 w-full py-4 rounded-2xl font-black text-xs uppercase tracking-wider text-white transition-all hover:scale-105"
                            style={{
                                background:
                                    "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary))",
                            }}
                        >
                            Reproducir
                        </button>
                    </div>

                    {/* Rest of testimonials */}
                    {rest.slice(0, 4).map((t, i) => (
                        <div
                            key={t.id}
                            className={`${i < 2 ? "md:col-span-4" : "md:col-span-3"} rounded-2xl p-7 border-l-4 flex flex-col justify-between`}
                            style={{
                                background: "var(--faro-surface-container)",
                                borderColor: i % 2 === 0 ? "var(--faro-primary)" : "var(--faro-secondary)",
                            }}
                        >
                            <p
                                className="text-base italic leading-relaxed mb-6"
                                style={{ color: "var(--faro-on-surface-variant)" }}
                            >
                                "{t.content}"
                            </p>
                            <div className="flex items-center gap-3">
                                <div
                                    className="w-8 h-8 rounded-xl flex items-center justify-center text-xs font-black"
                                    style={{
                                        background: "var(--faro-primary-container)",
                                        color: "var(--faro-primary)",
                                    }}
                                >
                                    {t.author?.username?.[0] ?? "?"}
                                </div>
                                <div>
                                    <p
                                        className="text-sm font-black"
                                        style={{ color: "var(--faro-on-surface)" }}
                                    >
                                        {t.author?.username ?? "Miembro"}
                                    </p>
                                    <p
                                        className="text-[10px] uppercase tracking-widest font-bold"
                                        style={{ color: "var(--faro-primary)" }}
                                    >
                                        {t.emotion ?? "FARO"}
                                    </p>
                                </div>
                            </div>
                        </div>
                    ))}

                    {/* Stats card */}
                    <div
                        className="md:col-span-4 rounded-2xl p-8 flex flex-col items-center justify-center text-center"
                        style={{ background: "var(--faro-primary-container)", opacity: 0.9 }}
                    >
                        <Users size={36} style={{ color: "var(--faro-primary)" }} className="mb-4" />
                        <div
                            className="text-5xl font-black mb-2"
                            style={{ color: "var(--faro-primary)" }}
                        >
                            +500
                        </div>
                        <p
                            className="text-xs uppercase tracking-widest font-bold"
                            style={{ color: "var(--faro-on-surface-variant)" }}
                        >
                            vidas impactadas este mes
                        </p>
                        <Link
                            href="/faro/conocer-a-jesus"
                            className="mt-6 inline-flex items-center gap-2 text-sm font-black uppercase tracking-wider transition-all"
                            style={{ color: "var(--faro-primary)" }}
                        >
                            Comparte tu historia <ArrowRight size={14} />
                        </Link>
                    </div>
                </div>
            </section>

            {/* ── QUOTE EDITORIAL ─────────────────────────────── */}
            <section
                className="py-24 px-6 md:px-16 relative overflow-hidden"
                style={{ background: "var(--faro-surface-container-low)" }}
            >
                <div
                    className="absolute top-0 left-0 w-full h-px"
                    style={{
                        background:
                            "linear-gradient(to right, transparent, var(--faro-primary), transparent)",
                        opacity: 0.3,
                    }}
                />
                <div className="max-w-3xl mx-auto text-center">
                    <span
                        className="text-8xl font-black block mb-6 leading-none"
                        style={{ color: "var(--faro-primary)", opacity: 0.15 }}
                    >
                        "
                    </span>
                    <blockquote
                        className="text-3xl md:text-4xl font-black leading-tight italic mb-10"
                        style={{ color: "var(--faro-on-surface)" }}
                    >
                        La luz que encontramos en FARO no es para guardarla, es para
                        guiar a otros que aún caminan en la oscuridad.
                    </blockquote>
                    <p
                        className="font-black text-lg"
                        style={{ color: "var(--faro-on-surface)" }}
                    >
                        Pastor David Vance
                    </p>
                    <p
                        className="text-xs uppercase tracking-[0.3em] font-bold mt-1"
                        style={{ color: "var(--faro-primary)" }}
                    >
                        Visión 2025
                    </p>
                </div>
            </section>
        </main>
    );
}
