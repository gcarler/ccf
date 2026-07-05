"use client";

import Link from "next/link";
import React from "react";
import Image from "next/image";
import { ArrowRight, Play } from "lucide-react";
import { motion } from "framer-motion";
import { SITE_NAME } from "@/lib/site-config";
import { useCmsV2Page } from "@/hooks/useCmsV2Page";
import { useState } from "react";
import { apiFetch } from "@/lib/http";
import { toast } from "sonner";


export default function PublicHomePage() {
    const homePage = useCmsV2Page('home');
    const heroContent = homePage?.blocks?.hero;
    const homeFeedContent = homePage?.blocks?.feed;
    const eventsPage = useCmsV2Page('events');
    const eventsContent = eventsPage?.blocks?.events;










    const heroEyebrow = heroContent?.eyebrow || "BIENVENIDOS";
    const heroTitleLead = heroContent?.title_lead || SITE_NAME;
    const heroTitleAccent = heroContent?.title_accent || "";
    const heroTitleTail = heroContent?.title_tail || "";
    const heroDescription = heroContent?.description || "Navegando juntos hacia la verdad. Un espacio de encuentro, fe y transformación en el corazón de nuestra comunidad.";
    const heroPrimaryCta = heroContent?.primary_cta || "Empezar mi viaje";
    const heroSecondaryCta = heroContent?.secondary_cta || "Ver Prédicas";

    const homeFeed = (homeFeedContent?.parsed && typeof homeFeedContent.parsed === "object" && !Array.isArray(homeFeedContent.parsed))
        ? homeFeedContent.parsed as Record<string, unknown>
        : null;
    const homeEyebrow = (homeFeed?.eyebrow as string) || "Nuestra esencia";
    const homeSectionTitle = (homeFeed?.section_title as string) || "Bienvenidos a Casa";
    const homeSectionDescription = (homeFeed?.section_description as string) || "Rutas públicas para conocer la comunidad, profundizar en la fe y encontrar dónde dar el siguiente paso.";
    const activitiesEyebrow = (homeFeed?.activities_eyebrow as string) || "Actualidad";
    const activitiesTitle = (homeFeed?.activities_title as string) || "Actividades Recientes";
    const activitiesViewAll = (homeFeed?.activities_view_all as string) || "Ver calendario →";
    const activitiesEmpty = (homeFeed?.activities_empty as string) || "Próximamente encontrarás aquí nuestras actividades. Mientras tanto, síguenos en redes sociales.";
    const scrollIndicator = (homeFeed?.scroll_indicator as string) || "Descubrir";
    const newsletterEyebrow = (homeFeed?.newsletter_eyebrow as string) || "Boletín semanal";
    const newsletterTitle = (homeFeed?.newsletter_title as string) || "¿Quieres recibir nuestras novedades?";
    const newsletterDescription = (homeFeed?.newsletter_description as string) || "Meditaciones semanales, eventos exclusivos y más.\nDirecto a tu correo.";
    const newsletterPlaceholder = (homeFeed?.newsletter_placeholder as string) || "Tu correo electrónico";
    const newsletterSubmit = (homeFeed?.newsletter_submit as string) || "Suscribirme";
    const newsletterSuccessTitle = (homeFeed?.newsletter_success_title as string) || "¡Gracias por suscribirte!";
    const newsletterSuccessDesc = (homeFeed?.newsletter_success_desc as string) || "Recibirás meditaciones y novedades semanales.";
    const homeFeaturedCard = (homeFeed?.featured_card && typeof homeFeed.featured_card === "object" && !Array.isArray(homeFeed.featured_card))
        ? homeFeed.featured_card as Record<string, unknown>
        : null;
    const homeCards = Array.isArray(homeFeed?.cards)
        ? homeFeed.cards as Array<Record<string, unknown>>
        : [];

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
            toast.success(`¡Suscrito al boletín de ${SITE_NAME}!`);
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
            <section className="relative ccf-hero flex items-center justify-center overflow-hidden">
                {/* Background: imagen ccf con overlay */}
                <div
                    className="absolute inset-0 bg-cover bg-center"
                    style={{
                        backgroundImage: heroContent?.bg_image
                            ? `url('${heroContent.bg_image}')`
                            : "linear-gradient(135deg, #0a1628 0%, #0d2244 50%, #0a1628 100%)",
                        filter: heroContent?.bg_image ? "brightness(0.35) saturate(0.6)" : undefined,
                    }}
                />
                {/* Overlay gradiente azul marino */}
                <div
                    className="absolute inset-0"
                    style={{
                        background: "var(--site-hero-overlay)",
                    }}
                />
                {/* Beam glow */}
                <div
                    className="absolute inset-0 pointer-events-none"
                    style={{
                        background: "radial-gradient(ellipse at 60% 20%, var(--site-glow-subtle) 0%, transparent 60%)",
                    }}
                />

                {/* Content */}
                <div className="relative z-10 text-center w-full ccf-container pt-24">
                    <span
                        className="inline-block text-xs font-bold uppercase tracking-wide mb-3"
                        style={{ color: "var(--site-hero-badge-color)" }}
                    >
                        {heroEyebrow}
                    </span>
                    <h1
                        className="mx-auto max-w-5xl font-bold ccf-display mb-3 text-5xl sm:text-6xl lg:text-8xl"
                        style={{ color: "var(--site-on-hero)" }}
                    >
                        {heroTitleLead}{" "}
                        <span
                            style={{
                                background: "var(--site-hero-accent-1)",
                                WebkitBackgroundClip: "text",
                                WebkitTextFillColor: "transparent",
                            }}
                        >
                            {heroTitleAccent}
                        </span>
                        <br />
                        <span
                            style={{
                                background: "var(--site-hero-accent-2)",
                                WebkitBackgroundClip: "text",
                                WebkitTextFillColor: "transparent",
                            }}
                        >
                            {heroTitleTail}
                        </span>
                    </h1>
                    <p
                        className="ccf-body text-base sm:text-lg max-w-2xl mx-auto mb-8"
                        style={{ color: "var(--site-on-hero)", opacity: 0.8 }}
                    >
                        {heroDescription}
                    </p>
                    <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                        <Link
                            href="/conocer-a-jesus"
                            className="ccf-button group"
                            style={{
                                background: "var(--site-hero-cta-gradient)",
                                boxShadow: "var(--site-hero-cta-shadow)",
                                color: "var(--site-on-hero)",
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
                            className="ccf-button"
                            style={{
                                background: "var(--site-hero-bg-light)",
                                border: "2px solid var(--site-hero-border-light)",
                                color: "var(--site-on-hero)",
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
                        {scrollIndicator}
                    </span>
                </motion.div>
            </section>

            {/* ─── BENTO: Bienvenidos a Casa ────────────────────────── */}
            <section
                className="ccf-section overflow-hidden"
                style={{ background: "var(--site-surface-container-low)" }}
            >
                <div className="ccf-container">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true, margin: "-100px" }}
                        className="mb-14"
                    >
                        <span
                            className="text-xs font-bold uppercase tracking-widest block mb-4"
                            style={{ color: "var(--site-primary)" }}
                        >
                            {homeEyebrow}
                        </span>
                        <h2
                            className="font-black ccf-headline text-4xl sm:text-5xl lg:text-6xl"
                            style={{ color: "var(--site-on-background)" }}
                        >
                            {homeSectionTitle}
                        </h2>
                        <p className="ccf-body mt-6 text-base sm:text-lg max-w-3xl" style={{ color: "var(--site-on-surface-variant)" }}>
                            {homeSectionDescription}
                        </p>
                    </motion.div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-5 md:gap-6">
                        {/* Card grande — Conocer a Jesús */}
                        <motion.div
                            initial={{ opacity: 0, y: 30 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ delay: 0.1 }}
                            className="sm:col-span-2 md:col-span-2 rounded-2xl flex flex-col justify-end group relative overflow-hidden min-h-[420px]"
                        >
                            {homeFeaturedCard?.img ? (
                                <Image
                                    src={homeFeaturedCard.img as string}
                                    alt={(homeFeaturedCard?.alt as string) || "Equipo pastoral de la comunidad"}
                                    fill
                                    sizes="(max-width: 640px) 100vw, (max-width: 1024px) 100vw, 66vw"
                                    className="object-cover transition-transform duration-700 group-hover:scale-105"
                                />
                            ) : (
                                <div className="absolute inset-0 bg-gradient-to-br from-[hsl(var(--primary))/0.2] via-[hsl(var(--secondary))/0.18] to-[hsl(var(--background))]" />
                            )}
                            <div className="absolute inset-0" style={{ background: "linear-gradient(to top, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.3) 55%, transparent 100%)" }} />
                            <div className="relative z-10 p-8">
                                <h3 className="text-2xl md:text-3xl font-black text-white mb-3">
                                    {(homeFeaturedCard?.title as string) || "Conocer a Jesús"}
                                </h3>
                                <p className="text-white/80 leading-relaxed max-w-md mb-5 text-base">
                                    {(homeFeaturedCard?.desc as string) || "Descubre la base de nuestra fe a través de un viaje personal y transformador. Te acompañamos en cada paso."}
                                </p>
                                <Link
                                    href={(homeFeaturedCard?.href as string) || "/conocer-a-jesus"}
                                    className="inline-flex items-center gap-2 font-black text-sm uppercase tracking-wide text-white group-hover:gap-4 transition-all"
                                >
                                    {(homeFeaturedCard?.cta as string) || "Empezar el camino"} <ArrowRight size={16} />
                                </Link>
                            </div>
                        </motion.div>

                        {/* Mini cards con imagen */}
                        {homeCards.map((card, idx) => {
                            const title = card.title as string;
                            const desc = card.desc as string;
                            const href = card.href as string;
                            const img = card.img as string;
                            const alt = card.alt as string;
                            return (
                            <motion.div
                                key={title || idx}
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ delay: 0.1 * (idx + 1) }}
                            >
                                <Link
                                    href={href || "#"}
                                    className="block rounded-2xl overflow-hidden group relative min-h-[130px] flex flex-col justify-end transition-transform hover:scale-[1.02]"
                                >
                                    {img ? (
                                        <Image
                                            src={img}
                                            alt={alt || title}
                                            fill
                                            sizes="(max-width: 640px) 100vw, (max-width: 768px) 50vw, 33vw"
                                            className="object-cover transition-transform duration-500 group-hover:scale-105"
                                        />
                                    ) : (
                                        <div className="absolute inset-0 bg-gradient-to-br from-[hsl(var(--primary))/0.18] to-[hsl(var(--surface-2))/0.35]" />
                                    )}
                                    <div className="absolute inset-0" style={{ background: "linear-gradient(to top, rgba(0,0,0,0.78) 0%, rgba(0,0,0,0.1) 60%, transparent 100%)" }} />
                                    <div className="relative z-10 p-5">
                                        <h4 className="font-black text-white text-base mb-1">{title}</h4>
                                        <p className="text-white/70 text-xs leading-relaxed">{desc}</p>
                                    </div>
                                </Link>
                            </motion.div>
                            );
                        })}
                    </div>
                </div>
            </section>

            {/* ─── ACTIVIDADES RECIENTES ────────────────────────────── */}
            <section
                className="ccf-section-tight overflow-hidden"
                style={{ background: "var(--site-surface)" }}
            >
                <div className="ccf-container">
                    <motion.div
                        initial={{ opacity: 0, x: -30 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                        className="flex justify-between items-end mb-10"
                    >
                        <div>
                            <span
                                className="text-xs font-bold uppercase tracking-wide block mb-3"
                                style={{ color: "var(--site-primary)" }}
                            >
                                {activitiesEyebrow}
                            </span>
                            <h2
                                className="font-bold ccf-headline text-2xl md:text-3xl"
                                style={{ color: "var(--site-on-background)" }}
                            >
                                {activitiesTitle}
                            </h2>
                        </div>
                        <Link
                            href="/eventos"
                            className="hidden md:block text-sm font-bold uppercase tracking-wide border-b-2 pb-1 transition-all hover:-translate-y-1"
                            style={{
                                color: "var(--site-primary)",
                                borderColor: "var(--site-primary)",
                            }}
                        >
                            {activitiesViewAll}
                        </Link>
                    </motion.div>
                    {publicEvents.length === 0 ? (
                        <p className="ccf-body text-center py-2" style={{ color: "var(--site-on-surface-variant)" }}>
                            {activitiesEmpty}
                        </p>
                    ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-5 md:gap-6">
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
                                    style={{ background: "var(--site-surface-container-high)" }}
                                >
                                    {img ? (
                                        <Image
                                            src={img}
                                            alt={title || "Image"}
                                            fill
                                            sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
                                            className="object-cover group-hover:scale-105 transition-transform duration-700"
                                        />
                                    ) : (
                                        <div className="absolute inset-0 bg-gradient-to-br from-[hsl(var(--primary))/0.18] to-[hsl(var(--surface-2))/0.35]" />
                                    )}
                                </div>
                                <div className="flex gap-3 mb-3 items-center">
                                    <span
                                        className="px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider"
                                        style={{
                                            background: "var(--site-secondary-container)",
                                            color: "var(--site-on-secondary-container)",
                                        }}
                                    >
                                        {tag}
                                    </span>
                                    <span
                                        className="text-[10px] font-bold uppercase tracking-wider"
                                        style={{ color: "var(--site-on-surface-variant)" }}
                                    >
                                        {date}
                                    </span>
                                </div>
                                <h3
                                    className="font-bold text-lg mb-3 group-hover:opacity-80 transition-opacity"
                                    style={{ color: "var(--site-on-surface)" }}
                                >
                                    {title}
                                </h3>
                                <p
                                    className="text-sm leading-relaxed line-clamp-2"
                                    style={{ color: "var(--site-on-surface-variant)" }}
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
            <section className="ccf-section" style={{ background: "var(--site-surface-container-low)" }}>
                <motion.div
                    initial={{ opacity: 0, y: 24 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    className="ccf-container max-w-3xl mx-auto text-center"
                >
                    <span className="inline-block text-xs font-bold uppercase tracking-widest mb-5 px-4 py-1.5 rounded-full" style={{ background: "var(--site-primary-container)", color: "var(--site-primary)" }}>
                        {newsletterEyebrow}
                    </span>
                    <h2
                        className="font-black ccf-headline mb-5 text-3xl sm:text-4xl lg:text-5xl"
                        style={{ color: "var(--site-on-background)" }}
                    >
                        {newsletterTitle}
                    </h2>
                    <p className="ccf-body text-base sm:text-lg mb-10 mx-auto" style={{ color: "var(--site-on-surface-variant)" }}>
                        {newsletterDescription.split('\n').map((line, i) => (
                            <React.Fragment key={i}>
                                {i > 0 && <br />}
                                {i === newsletterDescription.split('\n').length - 1 ? (
                                    <span style={{ color: "var(--site-primary)" }}>{line}</span>
                                ) : line}
                            </React.Fragment>
                        ))}
                    </p>

                    {nlStatus === "sent" ? (
                        <div className="py-6">
                            <p className="text-2xl font-black mb-2" style={{ color: "var(--site-on-background)" }}>{newsletterSuccessTitle}</p>
                            <p className="ccf-body text-base mx-auto" style={{ color: "var(--site-on-surface-variant)" }}>{newsletterSuccessDesc}</p>
                        </div>
                    ) : (
                        <form onSubmit={handleNewsletterSubmit} className="flex flex-col sm:flex-row gap-3 max-w-xl mx-auto">
                            <input
                                type="email"
                                value={nlEmail}
                                onChange={(e) => setNlEmail(e.target.value)}
                                placeholder={newsletterPlaceholder}
                                required
                                disabled={nlStatus === "sending"}
                                className="flex-grow rounded-full px-6 py-4 text-base focus:outline-none disabled:opacity-60 focus:ring-2"
                                style={{
                                    background: "var(--site-surface)",
                                    border: "2px solid var(--site-outline-variant)",
                                    color: "var(--site-on-surface)",
                                }}
                            />
                            <button
                                type="submit"
                                disabled={nlStatus === "sending"}
                                className="ccf-button shrink-0"
                                style={{
                                    background: "var(--site-cta-gradient)",
                                    boxShadow: "var(--site-cta-shadow)",
                                    color: "var(--site-on-primary)",
                                }}
                            >
                                {nlStatus === "sending" ? "Enviando..." : newsletterSubmit}
                            </button>
                        </form>
                    )}
                </motion.div>
            </section>
        </main>

    );
}
