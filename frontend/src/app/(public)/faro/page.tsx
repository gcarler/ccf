"use client";

import Link from "next/link";
import React from "react";
import { ArrowRight, Play, Calendar, MapPin, BookOpen } from "lucide-react";
import { useContentBlock } from "@/hooks/useContent";
import { FARO_EVENTS_BLOCK_KEY } from "@/lib/cms/blocks";

export default function PublicHomePage() {
    const { data: heroContent } = useContentBlock("faro_home_hero");
    const { data: eventsContent } = useContentBlock(FARO_EVENTS_BLOCK_KEY);

    const heroEyebrow = heroContent?.eyebrow || "UNA COMUNIDAD QUE ILUMINA";
    const heroTitleLead = heroContent?.title_lead || "FARO: ";
    const heroTitleAccent = heroContent?.title_accent || "Tu Guía,";
    const heroTitleTail = heroContent?.title_tail || "Su Luz";
    const heroDescription = heroContent?.description || "Navegando juntos hacia la verdad. Un espacio de encuentro, fe y transformación en el corazón de nuestra comunidad.";
    const heroPrimaryCta = heroContent?.primary_cta || "Empezar mi viaje";
    const heroSecondaryCta = heroContent?.secondary_cta || "Ver Prédicas";

    const publicEvents = Array.isArray(eventsContent?.parsed)
        ? eventsContent?.parsed
        : [
            {
                img: "https://images.unsplash.com/photo-1517457373958-b7bdd4587205?w=600&q=80",
                tag: "Música",
                date: "12 OCT 2025",
                title: "Noche de Adoración: Luz en Casa",
                desc: "Una experiencia inmersiva de música y oración para toda la familia.",
            },
            {
                img: "https://images.unsplash.com/photo-1552664730-d307ca884978?w=600&q=80",
                tag: "Liderazgo",
                date: "15 OCT 2025",
                title: "Curso: Liderazgo con Propósito",
                desc: "Herramientas prácticas para influir en tu entorno con propósito.",
            },
            {
                img: "https://images.unsplash.com/photo-1593113630400-ea4288922559?w=600&q=80",
                tag: "Social",
                date: "20 OCT 2025",
                title: "Proyecto: Manos que Iluminan",
                desc: "Jornada mensual de apoyo comunitario y entrega de alimentos.",
            },
        ];

    return (
        <main>
            {/* ─── HERO ─────────────────────────────────────────────── */}
            <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
                {/* Background: imagen faro con overlay */}
                <div
                    className="absolute inset-0 bg-cover bg-center"
                    style={{
                        backgroundImage:
                            "url('https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1600&q=80')",
                        filter: "brightness(0.35) saturate(0.6)",
                    }}
                />
                {/* Overlay gradiente azul marino */}
                <div
                    className="absolute inset-0"
                    style={{
                        background:
                            "linear-gradient(to bottom, rgba(0,13,42,0.7) 0%, rgba(0,13,42,0.4) 50%, rgba(0,13,42,0.85) 100%)",
                    }}
                />
                {/* Beam glow */}
                <div
                    className="absolute inset-0 pointer-events-none"
                    style={{
                        background:
                            "radial-gradient(ellipse at 60% 20%, rgba(1,138,189,0.15) 0%, transparent 60%)",
                    }}
                />

                {/* Content */}
                <div className="relative z-10 text-center px-6 max-w-5xl mx-auto pt-24">
                    <span
                        className="inline-block text-xs font-black uppercase tracking-[0.5em] mb-8"
                        style={{ color: "rgba(165, 200, 255, 0.7)" }}
                    >
                        {heroEyebrow}
                    </span>
                    <h1
                        className="font-black tracking-tight leading-[0.9] mb-8"
                        style={{
                            fontSize: "clamp(3.5rem, 9vw, 8rem)",
                            color: "white",
                        }}
                    >
                        {heroTitleLead}{" "}
                        <span
                            style={{
                                background:
                                    "linear-gradient(135deg, #a5c8ff 0%, #018abd 100%)",
                                WebkitBackgroundClip: "text",
                                WebkitTextFillColor: "transparent",
                            }}
                        >
                            {heroTitleAccent}
                        </span>
                        <br />
                        <span
                            style={{
                                background:
                                    "linear-gradient(135deg, #a5c8ff 0%, #2c609d 100%)",
                                WebkitBackgroundClip: "text",
                                WebkitTextFillColor: "transparent",
                            }}
                        >
                            {heroTitleTail}
                        </span>
                    </h1>
                    <p
                        className="text-lg md:text-xl max-w-2xl mx-auto leading-relaxed mb-12"
                        style={{ color: "rgba(217, 226, 255, 0.75)" }}
                    >
                        {heroDescription}
                    </p>
                    <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                        <Link
                            href="/faro/conocer-a-jesus"
                            className="group flex items-center gap-3 px-8 py-4 rounded-full text-sm font-black uppercase tracking-[0.2em] text-white transition-all hover:scale-105"
                            style={{
                                background:
                                    "linear-gradient(135deg, #018abd 0%, #2c609d 100%)",
                                boxShadow: "0 8px 32px rgba(1, 138, 189, 0.4)",
                            }}
                        >
                            {heroPrimaryCta}
                            <ArrowRight
                                size={16}
                                className="group-hover:translate-x-1 transition-transform"
                            />
                        </Link>
                        <Link
                            href="/faro/predicas"
                            className="flex items-center gap-3 px-8 py-4 rounded-full text-sm font-black uppercase tracking-[0.2em] transition-all hover:scale-105"
                            style={{
                                background: "rgba(255,255,255,0.08)",
                                border: "2px solid rgba(255,255,255,0.15)",
                                color: "white",
                                backdropFilter: "blur(10px)",
                            }}
                        >
                            <Play size={14} />
                            {heroSecondaryCta}
                        </Link>
                    </div>
                </div>

                {/* Scroll indicator */}
                <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 opacity-40">
                    <div className="w-px h-12 bg-white animate-pulse" />
                    <span className="text-white text-[9px] uppercase tracking-[0.3em]">
                        Descubrir
                    </span>
                </div>
            </section>

            {/* ─── BENTO: Bienvenidos a Casa ────────────────────────── */}
            <section
                className="py-24 px-6 md:px-16 lg:px-24"
                style={{ background: "var(--faro-surface-container-low)" }}
            >
                <div className="max-w-6xl mx-auto">
                    <div className="mb-14">
                        <span
                            className="text-xs font-black uppercase tracking-[0.25em] block mb-4"
                            style={{ color: "var(--faro-primary)" }}
                        >
                            Nuestra esencia
                        </span>
                        <h2
                            className="font-black text-4xl md:text-5xl tracking-tight"
                            style={{ color: "var(--faro-on-background)" }}
                        >
                            Bienvenidos a Casa
                        </h2>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {/* Feature grande */}
                        <div
                            className="md:col-span-2 rounded-3xl p-10 flex flex-col justify-between group relative overflow-hidden min-h-[280px]"
                            style={{ background: "var(--faro-surface-container)" }}
                        >
                            <div
                                className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-700"
                                style={{
                                    background:
                                        "radial-gradient(ellipse at 80% 20%, rgba(1, 138, 189, 0.08) 0%, transparent 70%)",
                                }}
                            />
                            <div className="relative z-10">
                                <div
                                    className="w-12 h-12 rounded-2xl flex items-center justify-center mb-6"
                                    style={{ background: "var(--faro-primary-container)" }}
                                >
                                    <span style={{ color: "var(--faro-primary)", fontSize: "22px" }}>✦</span>
                                </div>
                                <h3
                                    className="text-2xl font-black mb-4"
                                    style={{ color: "var(--faro-on-surface)" }}
                                >
                                    Conocer a Jesús
                                </h3>
                                <p
                                    className="leading-relaxed max-w-md"
                                    style={{ color: "var(--faro-on-surface-variant)" }}
                                >
                                    Descubre la base de nuestra fe a través de un viaje personal y
                                    transformador. En FARO, te acompañamos en cada paso.
                                </p>
                            </div>
                            <div className="relative z-10 mt-8">
                                <Link
                                    href="/faro/conocer-a-jesus"
                                    className="inline-flex items-center gap-2 font-black text-sm uppercase tracking-widest group-hover:gap-4 transition-all"
                                    style={{ color: "var(--faro-primary)" }}
                                >
                                    Empezar el camino
                                    <ArrowRight size={16} />
                                </Link>
                            </div>
                        </div>

                        {/* Testimonio */}
                        <div
                            className="rounded-3xl p-10 flex flex-col items-center justify-center text-center"
                            style={{
                                background: "var(--faro-primary-container)",
                                opacity: 0.9,
                            }}
                        >
                            <span
                                className="text-5xl mb-4 block"
                                style={{ color: "var(--faro-primary)" }}
                            >
                                99
                            </span>
                            <h3
                                className="text-xl font-black mb-4"
                                style={{ color: "var(--faro-on-primary-container)" }}
                            >
                                Testimonios
                            </h3>
                            <p
                                className="text-sm italic leading-relaxed mb-6"
                                style={{ color: "var(--faro-on-surface-variant)" }}
                            >
                                "Encontré una familia y un propósito cuando más lo necesitaba."
                            </p>
                            <span
                                className="font-black text-sm"
                                style={{ color: "var(--faro-primary)" }}
                            >
                                — Elena M.
                            </span>
                        </div>

                        {/* Mini cards */}
                        {[
                            { icon: <BookOpen size={22} />, title: "Librería", desc: "Recursos para profundizar en tu estudio bíblico." },
                            { icon: <Calendar size={22} />, title: "Horarios", desc: "Reuniones presenciales y online cada semana." },
                            { icon: <MapPin size={22} />, title: "Sedes", desc: "Encuéntranos en tu ciudad." },
                        ].map(({ icon, title, desc }) => (
                            <div
                                key={title}
                                className="rounded-2xl p-7 flex items-center gap-5 transition-all hover:scale-[1.02]"
                                style={{ background: "var(--faro-surface-container)" }}
                            >
                                <div
                                    className="w-12 h-12 rounded-2xl flex items-center justify-center shrink-0"
                                    style={{
                                        background: "var(--faro-primary-container)",
                                        color: "var(--faro-primary)",
                                    }}
                                >
                                    {icon}
                                </div>
                                <div>
                                    <h4
                                        className="font-black mb-1"
                                        style={{ color: "var(--faro-on-surface)" }}
                                    >
                                        {title}
                                    </h4>
                                    <p
                                        className="text-xs leading-relaxed"
                                        style={{ color: "var(--faro-on-surface-variant)" }}
                                    >
                                        {desc}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ─── ACTIVIDADES RECIENTES ────────────────────────────── */}
            <section
                className="py-24 px-6 md:px-16 lg:px-24"
                style={{ background: "var(--faro-surface)" }}
            >
                <div className="max-w-6xl mx-auto">
                    <div className="flex justify-between items-end mb-14">
                        <div>
                            <span
                                className="text-xs font-black uppercase tracking-[0.25em] block mb-4"
                                style={{ color: "var(--faro-primary)" }}
                            >
                                Actualidad
                            </span>
                            <h2
                                className="font-black text-4xl md:text-5xl tracking-tight"
                                style={{ color: "var(--faro-on-background)" }}
                            >
                                Actividades Recientes
                            </h2>
                        </div>
                        <Link
                            href="/faro/eventos"
                            className="hidden md:block text-sm font-black uppercase tracking-widest border-b-2 pb-1 transition-all"
                            style={{
                                color: "var(--faro-primary)",
                                borderColor: "var(--faro-primary)",
                            }}
                        >
                            Ver calendario →
                        </Link>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
                        {publicEvents.slice(0, 3).map(({ img, tag, date, title, desc }: any) => (
                            <div key={title} className="group cursor-pointer">
                                <div
                                    className="aspect-video rounded-2xl overflow-hidden mb-6"
                                    style={{ background: "var(--faro-surface-container-high)" }}
                                >
                                    <img
                                        src={img || "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=600&q=80"}
                                        alt={title}
                                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                                    />
                                </div>
                                <div className="flex gap-3 mb-3 items-center">
                                    <span
                                        className="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider"
                                        style={{
                                            background: "var(--faro-secondary-container)",
                                            color: "var(--faro-on-secondary-container)",
                                        }}
                                    >
                                        {tag}
                                    </span>
                                    <span
                                        className="text-[10px] font-bold uppercase tracking-wider"
                                        style={{ color: "var(--faro-on-surface-variant)" }}
                                    >
                                        {date}
                                    </span>
                                </div>
                                <h3
                                    className="font-black text-xl mb-2 group-hover:opacity-80 transition-opacity"
                                    style={{ color: "var(--faro-on-surface)" }}
                                >
                                    {title}
                                </h3>
                                <p
                                    className="text-sm leading-relaxed line-clamp-2"
                                    style={{ color: "var(--faro-on-surface-variant)" }}
                                >
                                    {desc}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ─── CTA NEWSLETTER ───────────────────────────────────── */}
            <section
                className="py-24 px-6 md:px-16 lg:px-24"
                style={{ background: "var(--faro-surface-container-low)" }}
            >
                <div
                    className="max-w-4xl mx-auto rounded-[2.5rem] p-12 md:p-20 relative overflow-hidden text-center"
                    style={{
                        background:
                            "linear-gradient(135deg, var(--faro-primary-container) 0%, var(--faro-surface-container-high) 100%)",
                        border: "1px solid var(--faro-outline-variant)",
                    }}
                >
                    <div
                        className="absolute inset-0 opacity-20 pointer-events-none"
                        style={{
                            background:
                                "radial-gradient(circle at 30% 50%, rgba(165, 200, 255, 0.5) 0%, transparent 60%)",
                        }}
                    />
                    <div className="relative z-10">
                        <h2
                            className="font-black text-3xl md:text-5xl tracking-tight mb-6"
                            style={{ color: "var(--faro-on-background)" }}
                        >
                            ¿Quieres recibir nuestras novedades?
                        </h2>
                        <p
                            className="text-lg mb-10"
                            style={{ color: "var(--faro-on-surface-variant)" }}
                        >
                            Meditaciones semanales, eventos exclusivos y más. Directo a tu correo.
                        </p>
                        <form className="flex flex-col sm:flex-row gap-4 max-w-lg mx-auto">
                            <input
                                type="email"
                                placeholder="Tu correo electrónico"
                                className="flex-grow rounded-2xl px-6 py-4 text-sm focus:outline-none"
                                style={{
                                    background: "var(--faro-surface)",
                                    border: "2px solid var(--faro-outline-variant)",
                                    color: "var(--faro-on-surface)",
                                }}
                            />
                            <button
                                type="button"
                                className="px-8 py-4 rounded-2xl font-black text-sm uppercase tracking-widest text-white transition-all hover:scale-105"
                                style={{
                                    background:
                                        "linear-gradient(135deg, var(--faro-primary) 0%, var(--faro-secondary) 100%)",
                                    boxShadow: "0 8px 24px rgba(44, 96, 157, 0.3)",
                                }}
                            >
                                Suscribirme
                            </button>
                        </form>
                    </div>
                </div>
            </section>
        </main>
    );
}
