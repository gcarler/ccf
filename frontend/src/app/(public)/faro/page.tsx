"use client";

import Link from "next/link";
import React from "react";
import Image from "next/image";
import { ArrowRight, Play, Calendar, MapPin, BookOpen } from "lucide-react";
import { motion } from "framer-motion";
import { useContentBlock } from "@/hooks/useContent";
import { FARO_EVENTS_BLOCK_KEY } from "@/lib/cms/blocks";
import Footer from "@/components/Footer";

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

    // v2.3 — despliegue automático verificado

    interface PublicEventItem {
        img?: string;
        tag?: string;
        date?: string;
        title?: string;
        desc?: string;
        status?: string;
    }

    const publicEvents: PublicEventItem[] = Array.isArray(eventsContent?.parsed)
        ? (eventsContent?.parsed as PublicEventItem[]).filter((event) => event.status !== "archived")
        : [];

    return (
        <main>
            {/* ─── HERO ─────────────────────────────────────────────── */}
            <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
                {/* Background: imagen faro con overlay */}
                <div
                    className="absolute inset-0 bg-cover bg-center"
                    style={{
                        backgroundImage:
                            "url('https://picsum.photos/seed/1506905925346-21bda4d32df4/800/600')",
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
                <div className="relative z-10 text-center w-full px-3 md:px-4 lg:px-24 pt-24">
                    <span
                        className="inline-block text-xs font-bold uppercase tracking-wide mb-3"
                        style={{ color: "rgba(165, 200, 255, 0.7)" }}
                    >
                        {heroEyebrow}
                    </span>
                    <h1
                        className="font-bold tracking-tight leading-[0.9] mb-3"
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
                        className="text-lg md:text-xl max-w-2xl mx-auto leading-relaxed mb-3"
                        style={{ color: "rgba(217, 226, 255, 0.75)" }}
                    >
                        {heroDescription}
                    </p>
                    <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                        <Link
                            href="/faro/conocer-a-jesus"
                            className="group flex items-center gap-3 px-4 py-1.5 rounded-full text-sm font-bold uppercase tracking-wide text-white transition-all hover:scale-105"
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
                            className="flex items-center gap-3 px-4 py-1.5 rounded-full text-sm font-bold uppercase tracking-wide transition-all hover:scale-105"
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
                <motion.div 
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 0.4 }}
                    transition={{ delay: 1, duration: 1 }}
                    className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2"
                >
                    <div className="w-px h-8 bg-white animate-pulse" />
                    <span className="text-white text-[9px] uppercase tracking-wide">
                        Descubrir
                    </span>
                </motion.div>
            </section>

            {/* ─── BENTO: Bienvenidos a Casa ────────────────────────── */}
            <section
                className="py-1.5 px-3 md:px-4 lg:px-24 overflow-hidden"
                style={{ background: "var(--faro-surface-container-low)" }}
            >
                <div className="w-full max-w-[1600px] mx-auto px-3 md:px-4 lg:px-24">
                    <motion.div 
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true, margin: "-100px" }}
                        className="mb-3"
                    >
                        <span
                            className="text-xs font-bold uppercase tracking-wide block mb-3"
                            style={{ color: "var(--faro-primary)" }}
                        >
                            Nuestra esencia
                        </span>
                        <h2
                            className="font-bold text-lg md:text-xl tracking-tight"
                            style={{ color: "var(--faro-on-background)" }}
                        >
                            Bienvenidos a Casa
                        </h2>
                    </motion.div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        {/* Feature grande */}
                        <motion.div
                            initial={{ opacity: 0, y: 30 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ delay: 0.1 }}
                            className="md:col-span-2 rounded-lg p-4 flex flex-col justify-between group relative overflow-hidden min-h-[280px]"
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
                                    className="w-12 h-8 rounded-lg flex items-center justify-center mb-3"
                                    style={{ background: "var(--faro-primary-container)" }}
                                >
                                    <span style={{ color: "var(--faro-primary)", fontSize: "22px" }}>✦</span>
                                </div>
                                <h3
                                    className="text-lg font-bold mb-3"
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
                            <div className="relative z-10 mt-3">
                                <Link
                                    href="/faro/conocer-a-jesus"
                                    className="inline-flex items-center gap-2 font-bold text-sm uppercase tracking-wide group-hover:gap-4 transition-all"
                                    style={{ color: "var(--faro-primary)" }}
                                >
                                    Empezar el camino
                                    <ArrowRight size={16} />
                                </Link>
                            </div>
                        </motion.div>

                        {/* Mini cards */}
                        {[
                            { icon: <BookOpen size={22} />, title: "Librería", desc: "Recursos para profundizar en tu estudio bíblico." },
                            { icon: <Calendar size={22} />, title: "Horarios", desc: "Reuniones presenciales y online cada semana." },
                            { icon: <MapPin size={22} />, title: "Sedes", desc: "Encuéntranos en tu ciudad." },
                        ].map(({ icon, title, desc }, idx) => (
                            <motion.div
                                key={title}
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ delay: 0.1 * (idx + 1) }}
                                className="rounded-lg p-4 flex items-center gap-3 transition-all hover:scale-[1.02]"
                                style={{ background: "var(--faro-surface-container)" }}
                            >
                                <div
                                    className="w-12 h-8 rounded-lg flex items-center justify-center shrink-0"
                                    style={{
                                        background: "var(--faro-primary-container)",
                                        color: "var(--faro-primary)",
                                    }}
                                >
                                    {icon}
                                </div>
                                <div>
                                    <h4
                                        className="font-bold mb-1"
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
                            </motion.div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ─── ACTIVIDADES RECIENTES ────────────────────────────── */}
            <section
                className="py-1.5 px-3 md:px-4 lg:px-24 overflow-hidden"
                style={{ background: "var(--faro-surface)" }}
            >
                <div className="w-full max-w-[1600px] mx-auto px-3 md:px-4 lg:px-24">
                    <motion.div 
                        initial={{ opacity: 0, x: -30 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                        className="flex justify-between items-end mb-3"
                    >
                        <div>
                            <span
                                className="text-xs font-bold uppercase tracking-wide block mb-3"
                                style={{ color: "var(--faro-primary)" }}
                            >
                                Actualidad
                            </span>
                            <h2
                                className="font-bold text-lg md:text-xl tracking-tight"
                                style={{ color: "var(--faro-on-background)" }}
                            >
                                Actividades Recientes
                            </h2>
                        </div>
                        <Link
                            href="/faro/eventos"
                            className="hidden md:block text-sm font-bold uppercase tracking-wide border-b-2 pb-1 transition-all hover:-translate-y-1"
                            style={{
                                color: "var(--faro-primary)",
                                borderColor: "var(--faro-primary)",
                            }}
                        >
                            Ver calendario →
                        </Link>
                    </motion.div>
                    {publicEvents.length === 0 ? (
                        <p className="text-center py-1.5" style={{ color: "var(--faro-on-surface-variant)" }}>
                            Próximamente encontrarás aquí nuestras actividades. Mientras tanto, síguenos en redes sociales.
                        </p>
                    ) : (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
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
                                    className="relative aspect-video rounded-lg overflow-hidden mb-3 shadow-md"
                                    style={{ background: "var(--faro-surface-container-high)" }}
                                >
                                    <Image
                                        src={img || "https://picsum.photos/seed/1506905925346-21bda4d32df4/800/600"}
                                        alt={title || "Image"}
                                        fill
                                        className="object-cover group-hover:scale-105 transition-transform duration-700"
                                    />
                                </div>
                                <div className="flex gap-3 mb-3 items-center">
                                    <span
                                        className="px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider"
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
                                    className="font-bold text-lg mb-3 group-hover:opacity-80 transition-opacity"
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
                            </motion.div>
                        ))}
                    </div>
                    )}
                </div>
            </section>

            {/* ─── CTA NEWSLETTER ───────────────────────────────────── */}
            <section
                className="py-1.5 px-3 md:px-4 lg:px-24"
                style={{ background: "var(--faro-surface-container-low)" }}
            >
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    whileInView={{ opacity: 1, scale: 1 }}
                    viewport={{ once: true }}
                    className="max-w-4xl mx-auto rounded-lg p-4 md:p-4 relative overflow-hidden text-center shadow-[0_32px_64px_-16px_rgba(0,0,0,0.1)] backdrop-blur-2xl"
                    style={{
                        background:
                            "linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(0,0,0,0.02) 100%)",
                        border: "1px solid rgba(255,255,255,0.1)",
                        backgroundColor: "var(--faro-primary-container)"
                    }}
                >
                    <div
                        className="absolute inset-0 opacity-40 pointer-events-none mix-blend-overlay"
                        style={{
                            background:
                                "radial-gradient(circle at 30% 50%, rgba(165, 200, 255, 0.5) 0%, transparent 60%)",
                        }}
                    />
                    <div className="relative z-10">
                        <h2
                            className="font-bold text-lg md:text-xl tracking-tight mb-3"
                            style={{ color: "var(--faro-on-background)" }}
                        >
                            ¿Quieres recibir nuestras novedades?
                        </h2>
                        <p
                            className="text-lg mb-3"
                            style={{ color: "var(--faro-on-surface-variant)" }}
                        >
                            Meditaciones semanales, eventos exclusivos y más. Directo a tu correo.
                        </p>
                        <form className="flex flex-col sm:flex-row gap-4 max-w-lg mx-auto">
                            <input
                                type="email"
                                placeholder="Tu correo electrónico"
                                className="flex-grow rounded-lg px-3 py-1.5 text-sm focus:outline-none"
                                style={{
                                    background: "var(--faro-surface)",
                                    border: "2px solid var(--faro-outline-variant)",
                                    color: "var(--faro-on-surface)",
                                }}
                            />
                            <button
                                type="button"
                                className="px-4 py-1.5 rounded-lg font-bold text-sm uppercase tracking-wide text-white transition-all hover:scale-105"
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
                </motion.div>
            </section>
            <Footer />
        </main>
    );
}

