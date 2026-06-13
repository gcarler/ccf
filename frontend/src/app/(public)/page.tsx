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
import CmsPageOverride from "@/components/public/cms/CmsPageOverride";

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
        <CmsPageOverride slug="home">
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
                    <div className="w-px h-8 bg-[hsl(var(--bg-primary))] animate-pulse" />
                    <span className="text-white text-[9px] uppercase tracking-wide">
                        Descubrir
                    </span>
                </motion.div>
            </section>

            {/* ─── BENTO: Bienvenidos a Casa ────────────────────────── */}
            <section
                className="py-16 md:py-24 px-3 md:px-4 lg:px-8 xl:px-12 overflow-hidden"
                style={{ background: "var(--faro-surface-container-low)" }}
            >
                <div className="w-full">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true, margin: "-100px" }}
                        className="mb-10"
                    >
                        <span
                            className="text-xs font-bold uppercase tracking-widest block mb-4"
                            style={{ color: "var(--faro-primary)" }}
                        >
                            Nuestra esencia
                        </span>
                        <h2
                            className="font-black tracking-tight leading-tight"
                            style={{ fontSize: "clamp(2.5rem, 6vw, 4.5rem)", color: "var(--faro-on-background)" }}
                        >
                            Bienvenidos a Casa
                        </h2>
                    </motion.div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {/* Card grande — Conocer a Jesús */}
                        <motion.div
                            initial={{ opacity: 0, y: 30 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ delay: 0.1 }}
                            className="md:col-span-2 rounded-2xl flex flex-col justify-end group relative overflow-hidden min-h-[420px]"
                        >
                            <Image
                                src="https://images.unsplash.com/photo-1519671482749-fd09be7ccebf?w=900&q=80"
                                alt="Comunidad El Faro"
                                fill
                                className="object-cover transition-transform duration-700 group-hover:scale-105"
                            />
                            <div className="absolute inset-0" style={{ background: "linear-gradient(to top, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.3) 55%, transparent 100%)" }} />
                            <div className="relative z-10 p-8">
                                <h3 className="text-2xl md:text-3xl font-black text-white mb-3">
                                    Conocer a Jesús
                                </h3>
                                <p className="text-white/80 leading-relaxed max-w-md mb-5 text-base">
                                    Descubre la base de nuestra fe a través de un viaje personal y
                                    transformador. En FARO, te acompañamos en cada paso.
                                </p>
                                <Link
                                    href="/conocer-a-jesus"
                                    className="inline-flex items-center gap-2 font-black text-sm uppercase tracking-wide text-white group-hover:gap-4 transition-all"
                                >
                                    Empezar el camino <ArrowRight size={16} />
                                </Link>
                            </div>
                        </motion.div>

                        {/* Mini cards con imagen */}
                        {[
                            {
                                title: "Librería",
                                desc: "Recursos para profundizar en tu estudio bíblico.",
                                href: "/cursos",
                                img: "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=600&q=80",
                            },
                            {
                                title: "Horarios",
                                desc: "Reuniones presenciales y online cada semana.",
                                href: "/eventos",
                                img: "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?w=600&q=80",
                            },
                            {
                                title: "Sedes",
                                desc: "Encuéntranos en tu ciudad.",
                                href: "/sedes",
                                img: "https://images.unsplash.com/photo-1438032005730-c779502df39b?w=600&q=80",
                            },
                        ].map(({ title, desc, href, img }, idx) => (
                            <motion.div
                                key={title}
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ delay: 0.1 * (idx + 1) }}
                            >
                                <Link
                                    href={href}
                                    className="block rounded-2xl overflow-hidden group relative min-h-[130px] flex flex-col justify-end transition-transform hover:scale-[1.02]"
                                >
                                    <Image
                                        src={img}
                                        alt={title}
                                        fill
                                        className="object-cover transition-transform duration-500 group-hover:scale-105"
                                    />
                                    <div className="absolute inset-0" style={{ background: "linear-gradient(to top, rgba(0,0,0,0.78) 0%, rgba(0,0,0,0.1) 60%, transparent 100%)" }} />
                                    <div className="relative z-10 p-5">
                                        <h4 className="font-black text-white text-base mb-1">{title}</h4>
                                        <p className="text-white/70 text-xs leading-relaxed">{desc}</p>
                                    </div>
                                </Link>
                            </motion.div>
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
            <section className="py-16 md:py-24 px-3 md:px-4 lg:px-8 xl:px-12" style={{ background: "var(--faro-surface-container-low)" }}>
                <motion.div
                    initial={{ opacity: 0, y: 24 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    className="max-w-3xl mx-auto text-center"
                >
                    <span className="inline-block text-xs font-bold uppercase tracking-widest mb-5 px-4 py-1.5 rounded-full" style={{ background: "var(--faro-primary-container)", color: "var(--faro-primary)" }}>
                        Boletín semanal
                    </span>
                    <h2
                        className="font-black tracking-tight mb-5 leading-tight"
                        style={{ fontSize: "clamp(2rem, 5vw, 3.5rem)", color: "var(--faro-on-background)" }}
                    >
                        ¿Quieres recibir nuestras novedades?
                    </h2>
                    <p className="text-lg md:text-xl mb-10 leading-relaxed" style={{ color: "var(--faro-on-surface-variant)" }}>
                        Meditaciones semanales, eventos exclusivos y más.<br />
                        <span style={{ color: "var(--faro-primary)" }}>Directo a tu correo.</span>
                    </p>

                    {nlStatus === "sent" ? (
                        <div className="py-6">
                            <p className="text-2xl font-black mb-2" style={{ color: "var(--faro-on-background)" }}>¡Gracias por suscribirte!</p>
                            <p className="text-base" style={{ color: "var(--faro-on-surface-variant)" }}>Recibirás meditaciones y novedades semanales.</p>
                        </div>
                    ) : (
                        <form onSubmit={handleNewsletterSubmit} className="flex flex-col sm:flex-row gap-3 max-w-xl mx-auto">
                            <input
                                type="email"
                                value={nlEmail}
                                onChange={(e) => setNlEmail(e.target.value)}
                                placeholder="Tu correo electrónico"
                                required
                                disabled={nlStatus === "sending"}
                                className="flex-grow rounded-full px-6 py-4 text-base focus:outline-none disabled:opacity-60 focus:ring-2"
                                style={{
                                    background: "var(--faro-surface)",
                                    border: "2px solid var(--faro-outline-variant)",
                                    color: "var(--faro-on-surface)",
                                }}
                            />
                            <button
                                type="submit"
                                disabled={nlStatus === "sending"}
                                className="shrink-0 px-8 py-4 rounded-full font-black text-sm uppercase tracking-wider text-white transition-all hover:scale-105 disabled:opacity-60"
                                style={{
                                    background: "var(--faro-cta-gradient)",
                                    boxShadow: "var(--faro-cta-shadow)",
                                }}
                            >
                                {nlStatus === "sending" ? "Enviando..." : "Suscribirme"}
                            </button>
                        </form>
                    )}
                </motion.div>
            </section>
        </main>
        </CmsPageOverride>
    );
}

