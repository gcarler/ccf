"use client";

import Link from "next/link";
import React from "react";
import Image from "next/image";
import { ArrowRight, Play, Calendar, MapPin, BookOpen } from "lucide-react";
import { motion } from "framer-motion";
import { useContentBlock } from "@/hooks/useContent";
import { FARO_EVENTS_BLOCK_KEY } from "@/lib/cms/blocks";
import { useState } from "react";
import { apiFetch } from "@/lib/http";
import { toast } from "sonner";

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

    const [nlEmail, setNlEmail] = useState("");
    const [nlStatus, setNlStatus] = useState<"idle" | "sending" | "sent">("idle");

    const handleNewsletterSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!nlEmail) return;
        setNlStatus("sending");
        try {
            await apiFetch("/public/newsletter/subscribe", {
                method: "POST",
                body: { email: nlEmail, source: "newsletter-web", landing_page: "/" },
            });
            setNlStatus("sent");
            setNlEmail("");
            toast.success("¡Suscrito al boletín de FARO!");
        } catch {
            setNlStatus("idle");
            toast.error("No se pudo suscribir. Intenta de nuevo.");
        }
    };

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
                        background: "var(--faro-hero-overlay)",
                    }}
                />
                {/* Beam glow */}
                <div
                    className="absolute inset-0 pointer-events-none"
                    style={{
                        background: "radial-gradient(ellipse at 60% 20%, var(--faro-glow-subtle) 0%, transparent 60%)",
                    }}
                />

                {/* Content */}
                <div className="relative z-10 text-center w-full px-3 md:px-4 lg:px-8 xl:px-12 pt-24">
                    <span
                        className="inline-block text-xs font-bold uppercase tracking-wide mb-3"
                        style={{ color: "var(--faro-hero-badge-color)" }}
                    >
                        {heroEyebrow}
                    </span>
                    <h1
                        className="font-bold tracking-tight leading-[0.9] mb-3"
                        style={{
                            fontSize: "clamp(3.5rem, 9vw, 8rem)",
                            color: "var(--faro-on-hero)",
                        }}
                    >
                        {heroTitleLead}{" "}
                        <span
                            style={{
                                background: "var(--faro-hero-accent-1)",
                                WebkitBackgroundClip: "text",
                                WebkitTextFillColor: "transparent",
                            }}
                        >
                            {heroTitleAccent}
                        </span>
                        <br />
                        <span
                            style={{
                                background: "var(--faro-hero-accent-2)",
                                WebkitBackgroundClip: "text",
                                WebkitTextFillColor: "transparent",
                            }}
                        >
                            {heroTitleTail}
                        </span>
                    </h1>
                    <p
                        className="text-lg md:text-xl max-w-2xl mx-auto leading-relaxed mb-3"
                        style={{ color: "var(--faro-on-hero)", opacity: 0.75 }}
                    >
                        {heroDescription}
                    </p>
                    <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                        <Link
                            href="/conocer-a-jesus"
                            className="group flex items-center gap-3 px-4 py-1.5 rounded-full text-sm font-bold uppercase tracking-wide text-white transition-all hover:scale-105"
                            style={{
                                background: "var(--faro-hero-cta-gradient)",
                                boxShadow: "var(--faro-hero-cta-shadow)",
                            }}
                        >
                            {heroPrimaryCta}
                            <ArrowRight
                                size={16}
                                className="group-hover:translate-x-1 transition-transform"
                            />
                        </Link>
                        <Link
                            href="/predicas"
                            className="flex items-center gap-3 px-4 py-1.5 rounded-full text-sm font-bold uppercase tracking-wide transition-all hover:scale-105"
                            style={{
                                background: "var(--faro-hero-bg-light)",
                                border: "2px solid var(--faro-hero-border-light)",
                                color: "var(--faro-on-hero)",
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
                className="py-8 md:py-12 px-3 md:px-4 lg:px-8 xl:px-12 overflow-hidden"
                style={{ background: "var(--faro-surface-container-low)" }}
            >
                <div className="w-full px-3 md:px-8 lg:px-12 xl:px-16">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true, margin: "-100px" }}
                        className="mb-6"
                    >
                        <span
                            className="text-xs font-bold uppercase tracking-wide block mb-4"
                            style={{ color: "var(--faro-primary)" }}
                        >
                            Nuestra esencia
                        </span>
                        <h2
                            className="font-bold text-2xl md:text-3xl tracking-tight"
                            style={{ color: "var(--faro-on-background)" }}
                        >
                            Bienvenidos a Casa
                        </h2>
                    </motion.div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {/* Feature grande */}
                        <motion.div
                            initial={{ opacity: 0, y: 30 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ delay: 0.1 }}
                            className="md:col-span-2 rounded-xl p-6 md:p-8 flex flex-col justify-between group relative overflow-hidden min-h-[320px]"
                            style={{ background: "var(--faro-surface-container)" }}
                        >
                            <div
                                className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-700"
                                style={{
                                    background:
                                        "radial-gradient(ellipse at 80% 20%, var(--faro-glow-subtle) 0%, transparent 70%)",
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
                                    href="/conocer-a-jesus"
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
                            { icon: <BookOpen size={22} />, title: "Librería", desc: "Recursos para profundizar en tu estudio bíblico.", href: "/cursos" },
                            { icon: <Calendar size={22} />, title: "Horarios", desc: "Reuniones presenciales y online cada semana.", href: "/eventos" },
                            { icon: <MapPin size={22} />, title: "Sedes", desc: "Encuéntranos en tu ciudad.", href: "/sedes" },
                        ].map(({ icon, title, desc, href }, idx) => (
                            <Link
                                key={title}
                                href={href}
                                className="block rounded-xl p-5 flex items-center gap-4 transition-all hover:scale-[1.02]"
                                style={{ background: "var(--faro-surface-container)" }}
                            >
                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    whileInView={{ opacity: 1, y: 0 }}
                                    viewport={{ once: true }}
                                    transition={{ delay: 0.1 * (idx + 1) }}
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
                                </motion.div>
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
                            </Link>
                        ))}
                    </div>
                </div>
            </section>

            {/* ─── ACTIVIDADES RECIENTES ────────────────────────────── */}
            <section
                className="py-8 md:py-12 px-3 md:px-4 lg:px-8 xl:px-12 overflow-hidden"
                style={{ background: "var(--faro-surface)" }}
            >
                <div className="w-full px-3 md:px-8 lg:px-12 xl:px-16">
                    <motion.div
                        initial={{ opacity: 0, x: -30 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                        className="flex justify-between items-end mb-6"
                    >
                        <div>
                            <span
                                className="text-xs font-bold uppercase tracking-wide block mb-3"
                                style={{ color: "var(--faro-primary)" }}
                            >
                                Actualidad
                            </span>
                            <h2
                                className="font-bold text-2xl md:text-3xl tracking-tight"
                                style={{ color: "var(--faro-on-background)" }}
                            >
                                Actividades Recientes
                            </h2>
                        </div>
                        <Link
                            href="/eventos"
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
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
                                    className="relative aspect-video rounded-lg overflow-hidden mb-4 shadow-md"
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
                className="py-8 md:py-12 px-3 md:px-4 lg:px-8 xl:px-12"
                style={{ background: "var(--faro-surface-container-low)" }}
            >
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    whileInView={{ opacity: 1, scale: 1 }}
                    viewport={{ once: true }}
                    className="max-w-4xl mx-auto rounded-xl p-8 md:p-10 relative overflow-hidden text-center backdrop-blur-2xl"
                    style={{
                        background: "var(--faro-card-glass-gradient)",
                        backgroundColor: "var(--faro-primary-container)",
                        border: "1px solid var(--faro-glass-border)",
                        boxShadow: "var(--faro-card-shadow)",
                    }}
                >
                    <div
                        className="absolute inset-0 opacity-40 pointer-events-none mix-blend-overlay"
                        style={{
                            background:
                                "radial-gradient(circle at 30% 50%, var(--faro-card-glass-glow) 0%, transparent 60%)",
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
                        {nlStatus === "sent" ? (
                            <div className="relative z-10">
                                <h2 className="font-bold text-lg md:text-xl tracking-tight mb-3" style={{ color: "var(--faro-on-background)" }}>
                                    ¡Gracias por suscribirte!
                                </h2>
                                <p className="text-lg" style={{ color: "var(--faro-on-surface-variant)" }}>
                                    Recibirás meditaciones y novedades semanales.
                                </p>
                            </div>
                        ) : (
                            <form onSubmit={handleNewsletterSubmit} className="flex flex-col sm:flex-row gap-4 max-w-lg mx-auto">
                                <input
                                    type="email"
                                    value={nlEmail}
                                    onChange={(e) => setNlEmail(e.target.value)}
                                    placeholder="Tu correo electrónico"
                                    required
                                    disabled={nlStatus === "sending"}
                                    className="flex-grow rounded-lg px-3 py-1.5 text-sm focus:outline-none disabled:opacity-60"
                                    style={{
                                        background: "var(--faro-surface)",
                                        border: "2px solid var(--faro-outline-variant)",
                                        color: "var(--faro-on-surface)",
                                    }}
                                />
                                <button
                                    type="submit"
                                    disabled={nlStatus === "sending"}
                                className="px-4 py-1.5 rounded-lg font-bold text-sm uppercase tracking-wide text-white transition-all hover:scale-105"
                                style={{
                                    background:
                                        "linear-gradient(135deg, var(--faro-primary) 0%, var(--faro-secondary) 100%)",
                                    boxShadow: "var(--faro-hero-cta-shadow)",
                                }}
                            >
                                Suscribirme
                            </button>
                        </form>
                        )}
                    </div>
                </motion.div>
            </section>
        </main>
    );
}

