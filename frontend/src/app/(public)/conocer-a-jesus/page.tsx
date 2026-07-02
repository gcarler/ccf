"use client";

import React, { useEffect, useState } from "react";

import { ArrowRight, Clock, Mail, Heart, Star, Shield } from "lucide-react";
import { useCmsV2Page } from "@/hooks/useCmsV2Page";
import { SITE_EMAIL } from "@/lib/site-config";
import RichText from "@/components/public/RichText";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { apiFetch } from "@/lib/http";

interface TestimonialItem {
    id: number;
    content: string;
    is_approved?: boolean;
    author?: { username: string } | null;
}

export default function ConocerAJesusPage() {
    const discoverPage = useCmsV2Page('discover');
    const heroContent = discoverPage?.blocks?.hero;
    const discoverContent = discoverPage?.blocks?.feed;
    const [testimonials, setTestimonials] = useState<TestimonialItem[]>([]);

    const discoverData = (discoverContent?.parsed && typeof discoverContent.parsed === "object" && !Array.isArray(discoverContent.parsed))
        ? discoverContent.parsed as Record<string, unknown>
        : null;

    useEffect(() => {
        apiFetch<TestimonialItem[]>("/cms/testimonials")
            .then((data) => {
                if (Array.isArray(data)) {
                    setTestimonials(data.filter((t) => t.is_approved).slice(0, 3));
                }
            })
            .catch(() => {});
    }, []);

    const heroEyebrow = heroContent?.eyebrow || "Inicia tu camino";
    const heroTitleLead = heroContent?.title_lead || "La Luz que ";
    const heroTitleAccent = heroContent?.title_accent || "Guía";
    const heroTitleTail = heroContent?.title_tail || " Tu Vida.";
    const heroDescription = heroContent?.description || "Conocer a Jesús no es una religión, es el comienzo de una relación que transforma la oscuridad en un propósito eterno.";
    const heroCta = heroContent?.cta || "Quiero conocer a Jesús";
    const heroBgImage = heroContent?.bg_image || null;
    const introTitle = (discoverData?.intro_title as string) || "Un Encuentro Personal";
    const introParagraph1 = (discoverData?.intro_paragraph_1 as string) || "En FARO, creemos que cada historia es única. No importa dónde hayas estado o qué hayas hecho, la invitación es la misma: Ven y ve.";
    const introParagraph2 = (discoverData?.intro_paragraph_2 as string) || "Descubre un espacio donde las preguntas son bienvenidas y la gracia es el lenguaje principal. Jesús ofrece descanso para el alma y una dirección clara para el futuro.";
    const testimonialsTitle = (discoverData?.testimonials_title as string) || "Historias que iluminan";
    const testimonialsEmptyTitle = (discoverData?.testimonials_empty_title as string) || "Próximamente compartiremos historias de transformación.";
    const contactTitle = (discoverData?.contact_title as string) || "Hablemos de Tu Caminar";
    const contactDescription = (discoverData?.contact_description as string) || "¿Tienes dudas? ¿Quieres orar por algo específico? Nuestro equipo está aquí para acompañarte sin juicios.";
    const nameLabel = (discoverData?.name_label as string) || "Nombre completo";
    const namePlaceholder = (discoverData?.name_placeholder as string) || "Tu nombre";
    const phoneLabel = (discoverData?.phone_label as string) || "WhatsApp";
    const phonePlaceholder = (discoverData?.phone_placeholder as string) || "+57 300...";
    const messageLabel = (discoverData?.message_label as string) || "¿En qué podemos ayudarte?";
    const messagePlaceholder = (discoverData?.message_placeholder as string) || "Cuéntanos un poco sobre ti o tu petición de oración...";
    const submitLabel = (discoverData?.submit_label as string) || "Enviar mensaje y conectar";
    const submitSending = (discoverData?.submit_sending as string) || "Enviando...";
    const successTitle = (discoverData?.success_title as string) || "¡Gracias!";
    const successDescription = (discoverData?.success_description as string) || "Hemos recibido tu mensaje. Te contactaremos pronto.";
    const errorMessage = (discoverData?.error_message as string) || "Hubo un error. Intenta de nuevo o escríbenos directamente.";
    const connectionError = (discoverData?.connection_error as string) || "Ocurrió un error inesperado de conexión.";

    const benefitCards = Array.isArray(discoverData?.benefits)
        ? discoverData.benefits as Array<{ icon: string; title: string; desc: string }>
        : [
            { icon: "Heart", title: "Gracia sin condenas", desc: "Eres bienvenido tal como eres." },
            { icon: "Star", title: "Propósito real", desc: "Descubre para qué fuiste creado." },
            { icon: "Shield", title: "Comunidad que cuida", desc: "No estarás solo en este camino." },
            { icon: "ArrowRight", title: "Primer paso simple", desc: "Escríbenos y conectamos." },
        ];

    const iconMap: Record<string, React.ReactNode> = {
        Heart: <Heart size={22} />,
        Star: <Star size={22} />,
        Shield: <Shield size={22} />,
        ArrowRight: <ArrowRight size={22} />,
    };

    const contactInfo = Array.isArray(discoverData?.contact_info)
        ? discoverData.contact_info as Array<{ icon: string; text: string }>
        : [
            { icon: "Clock", text: "Respuesta en menos de 24 horas" },
            ...(SITE_EMAIL ? [{ icon: "Mail", text: SITE_EMAIL }] : []),
        ];

    const contactIconMap: Record<string, React.ReactNode> = {
        Clock: <Clock size={18} />,
        Mail: <Mail size={18} />,
    };

    const [form, setForm] = useState({ name: "", phone: "", message: "" });
    const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setStatus("sending");
        try {
            await apiFetch("/public/contact", {
                method: "POST",
                body: {
                    full_name: form.name,
                    phone: form.phone,
                    notes: form.message,
                    status: "prospect",
                    source: "conocer-a-jesus",
                },
            });
            
            // Si no lanza un error (ApiError), asumimos que funcionó (porque apiFetch lanza excepción si no es ok)
            setStatus("sent");
            toast.success(successTitle);

        } catch {
            setStatus("error");
            toast.error(connectionError);
        }
    };

    return (
        <main className="pt-[88px]">
            {/* ── HERO ──────────────────────────────────────── */}
            <header className="relative min-h-[88svh] md:min-h-screen flex items-center overflow-hidden">
                {/* Background: lighthouse in fog */}
                <div
                    className="absolute inset-0 bg-cover bg-center"
                    style={{
                        backgroundImage: heroBgImage ? `url('${heroBgImage}')` : "linear-gradient(135deg, #0a1628 0%, #0d2244 50%, #0a1628 100%)",
                        filter: heroBgImage ? "brightness(0.25) saturate(0.4)" : undefined,
                    }}
                />
                <div
                    className="absolute inset-0"
                    style={{
                        background: "var(--site-hero-overlay)",
                    }}
                />
                <div
                    className="absolute inset-0 pointer-events-none"
                    style={{
                        background:
                            "radial-gradient(ellipse at 50% 30%, var(--site-glow-subtle) 0%, transparent 70%)",
                    }}
                />

                <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, ease: "easeOut" }}
                    className="relative z-10 px-4 sm:px-6 md:px-10 xl:px-16 pb-8 md:pb-16"
                >
                    <span
                        className="inline-block px-4 py-1.5 rounded-full border text-xs font-semibold uppercase tracking-wide mb-3"
                        style={{
                            borderColor: "var(--site-hero-badge-border)",
                            color: "var(--site-hero-badge-color)",
                            background: "var(--site-hero-badge-bg)",
                        }}
                    >
                        {heroEyebrow}
                    </span>
                    <h1
                        className="max-w-3xl text-5xl sm:text-6xl lg:text-8xl font-bold tracking-tight leading-[0.95] mb-3"
                        style={{ color: "var(--site-on-hero)" }}
                    >
                        {heroTitleLead}{" "}
                        <span
                            className="italic"
                            style={{
                                background: "var(--site-hero-accent-1)",
                                WebkitBackgroundClip: "text",
                                WebkitTextFillColor: "transparent",
                            }}
                        >
                            {heroTitleAccent}
                        </span>{" "}
                        {heroTitleTail}
                    </h1>
                    <RichText html={heroDescription} className="text-base sm:text-lg max-w-2xl leading-relaxed mb-3" />
                    <a
                        href="#contacto"
                        className="inline-flex items-center gap-3 px-4 py-2 rounded-full font-black text-sm uppercase tracking-wide transition-all hover:scale-105"
                        style={{
                            background: "var(--site-hero-cta-gradient)",
                            color: "var(--site-on-hero)",
                            boxShadow: "var(--site-hero-cta-shadow)",
                        }}
                    >
                        {heroCta}
                        <ArrowRight size={18} />
                    </a>
                </motion.div>
            </header>

            {/* ── INTRO EDITORIAL ─────────────────────────── */}
            <section
                className="py-8 md:py-12 lg:py-16 px-4 sm:px-6 md:px-8 xl:px-12"
                style={{ background: "var(--site-surface-container-low)" }}
            >
                <div className="grid md:grid-cols-2 gap-3 items-center">
                    <motion.div
                        initial={{ opacity: 0, x: -30 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                    >
                        <h2
                            className="text-lg font-bold mb-3"
                            style={{ color: "var(--site-primary)" }}
                        >
                            {introTitle}
                        </h2>
                        <div className="space-y-5">
                            <div
                                className="text-lg leading-relaxed"
                                style={{ color: "var(--site-on-surface-variant)" }}
                            >
                                <RichText html={introParagraph1} className="[&_strong]:text-site-on-surface" />
                            </div>
                            <p
                                className="text-lg leading-relaxed"
                                style={{ color: "var(--site-on-surface-variant)" }}
                            >
                                {introParagraph2}
                            </p>
                        </div>
                    </motion.div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {benefitCards.map(({ icon, title, desc }, idx) => (
                            <motion.div
                                key={title}
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ delay: 0.1 * (idx + 1) }}
                                className="rounded-lg p-3 transition-transform hover:-translate-y-1 hover:shadow-lg"
                                style={{ background: "var(--site-surface-container)" }}
                            >
                                <div
                                    className="w-10 h-10 rounded-md flex items-center justify-center mb-4"
                                    style={{
                                        background: "var(--site-primary-container)",
                                        color: "var(--site-primary)",
                                    }}
                                >
                                    {iconMap[icon] || <Heart size={22} />}
                                </div>
                                <h4
                                    className="font-black text-sm mb-1"
                                    style={{ color: "var(--site-on-surface)" }}
                                >
                                    {title}
                                </h4>
                                <p
                                    className="text-xs leading-relaxed"
                                    style={{ color: "var(--site-on-surface-variant)" }}
                                >
                                    {desc}
                                </p>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── TESTIMONIOS RÁPIDOS ──────────────────────── */}
            <section
                className="py-8 md:py-12 lg:py-16 px-4 sm:px-6 md:px-8 xl:px-12"
                style={{ background: "var(--site-surface)" }}
            >
                <div>
                    <h2
                        className="text-xl font-bold mb-3 text-center"
                        style={{ color: "var(--site-on-background)" }}
                    >
                        {testimonialsTitle}
                    </h2>
                    {testimonials.length === 0 ? (
                        <p className="text-center col-span-full py-8" style={{ color: "var(--site-on-surface-variant)" }}>
                            {testimonialsEmptyTitle}
                        </p>
                    ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                        {testimonials.map((t, idx) => (
                            <motion.div
                                key={t.id}
                                initial={{ opacity: 0, scale: 0.95 }}
                                whileInView={{ opacity: 1, scale: 1 }}
                                viewport={{ once: true }}
                                transition={{ delay: 0.1 * idx }}
                                className="rounded-lg p-4 border-b-4 hover:shadow-md transition-shadow"
                                style={{
                                    background: "var(--site-surface-container)",
                                    borderColor: "var(--site-primary)",
                                }}
                            >
                                <p
                                    className="text-lg italic leading-relaxed mb-3"
                                    style={{ color: "var(--site-on-surface)" }}
                                >
                                    &quot;{t.content}&quot;
                                </p>
                                <p
                                    className="text-xs font-semibold uppercase tracking-wide"
                                    style={{ color: "var(--site-primary)" }}
                                >
                                    — {(t.author?.username) || "Anónimo"}
                                </p>
                            </motion.div>
                        ))}
                    </div>
                    )}
                </div>
            </section>

            {/* ── FORMULARIO DE CONTACTO ───────────────────── */}
            <section
                id="contacto"
                className="py-8 md:py-12 lg:py-16 px-4 sm:px-6 md:px-8 xl:px-12"
                style={{ background: "var(--site-surface-container-low)" }}
            >
                <div className="grid md:grid-cols-2 gap-3 items-start">
                    {/* Info lado izq */}
                    <div>
                        <h2
                            className="text-lg font-bold mb-3"
                            style={{ color: "var(--site-on-background)" }}
                        >
                            {contactTitle}
                        </h2>
                        <p
                            className="text-lg leading-relaxed mb-3"
                            style={{ color: "var(--site-on-surface-variant)" }}
                        >
                            {contactDescription}
                        </p>
                        <div className="space-y-5">
                            {contactInfo.map(({ icon, text }) => (
                                <div
                                    key={text}
                                    className="flex items-center gap-4"
                                    style={{ color: "var(--site-on-surface-variant)" }}
                                >
                                    <div
                                        className="w-10 h-10 rounded-md flex items-center justify-center"
                                        style={{
                                            background: "var(--site-primary-container)",
                                            color: "var(--site-primary)",
                                        }}
                                    >
                                        {contactIconMap[icon] || <Mail size={18} />}
                                    </div>
                                    <span className="text-sm">{text}</span>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Formulario */}
                    <motion.div
                        initial={{ opacity: 0, x: 30 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                        className="rounded-lg p-4 md:p-4 shadow-xl backdrop-blur-xl"
                        style={{
                            background: "var(--site-surface-container)",
                            border: "1px solid var(--site-outline-variant)"
                        }}
                    >
                        {status === "sent" ? (
                            <div className="text-center py-1.5">
                                <div
                                    className="w-16 h-8 rounded-full flex items-center justify-center mx-auto mb-3"
                                    style={{ background: "var(--site-primary-container)" }}
                                >
                                    <Heart size={28} style={{ color: "var(--site-primary)" }} />
                                </div>
                                <h3
                                    className="text-lg font-bold mb-3"
                                    style={{ color: "var(--site-on-surface)" }}
                                >
                                    {successTitle}
                                </h3>
                                <p style={{ color: "var(--site-on-surface-variant)" }}>
                                    {successDescription}
                                </p>
                            </div>
                        ) : (
                            <form onSubmit={handleSubmit} className="space-y-3">
                                <div className="grid md:grid-cols-2 gap-3">
                                    {[
                                        { key: "name", label: nameLabel, placeholder: namePlaceholder, type: "text" },
                                        { key: "phone", label: phoneLabel, placeholder: phonePlaceholder, type: "tel" },
                                    ].map(({ key, label, placeholder, type }) => (
                                        <div key={key}>
                                            <label
                                                className="text-[10px] font-semibold uppercase tracking-wide block mb-3"
                                                style={{ color: "var(--site-on-surface-variant)" }}
                                            >
                                                {label}
                                            </label>
                                            <input
                                                type={type}
                                                value={form[key as keyof typeof form]}
                                                onChange={(e) =>
                                                    setForm((f) => ({ ...f, [key]: e.target.value }))
                                                }
                                                placeholder={placeholder}
                                                required
                                                className="w-full rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 transition-all"
                                                style={{
                                                    background: "var(--site-surface)",
                                                    border: "2px solid var(--site-outline-variant)",
                                                    color: "var(--site-on-surface)",
                                                    // @ts-expect-error Tailwind custom properties are not typed by default in React CSS properties
                                                    "--tw-ring-color": "var(--site-primary)",
                                                }}
                                            />
                                        </div>
                                    ))}
                                </div>
                                <div>
                                    <label
                                        className="text-[10px] font-semibold uppercase tracking-wide block mb-3"
                                        style={{ color: "var(--site-on-surface-variant)" }}
                                    >
                                        {messageLabel}
                                    </label>
                                    <textarea
                                        value={form.message}
                                        onChange={(e) =>
                                            setForm((f) => ({ ...f, message: e.target.value }))
                                        }
                                        placeholder={messagePlaceholder}
                                        rows={4}
                                        className="w-full rounded-lg px-3 py-1.5 text-sm focus:outline-none resize-none"
                                        style={{
                                            background: "var(--site-surface)",
                                            border: "2px solid var(--site-outline-variant)",
                                            color: "var(--site-on-surface)",
                                        }}
                                    />
                                </div>
                                    <button
                                        type="submit"
                                        disabled={status === "sending"}
                                        className="w-full py-2 rounded-lg font-black text-sm uppercase tracking-wide transition-all hover:scale-[1.02] disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:scale-100"
                                    style={{
                                        background:
                                            "linear-gradient(135deg, var(--site-primary), var(--site-secondary))",
                                        color: "var(--site-on-primary)",
                                        boxShadow: "var(--site-hero-cta-shadow)",
                                    }}
                                    >
                                    {status === "sending" ? submitSending : submitLabel}
                                    </button>
                                {status === "error" && (
                                    <p
                                        className="text-xs text-center font-bold"
                                        style={{ color: "var(--site-error)" }}
                                    >
                                        {errorMessage}
                                    </p>
                                )}
                            </form>
                        )}
                    </motion.div>
                </div>
            </section>
        </main>
    );
}
