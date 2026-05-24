"use client";

import React, { useEffect, useState } from "react";

import { ArrowRight, Clock, Mail, Heart, Star, Shield } from "lucide-react";
import { useContentBlock } from "@/hooks/useContent";
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
    const { data: heroContent } = useContentBlock("faro_discover_hero");
    const { data: discoverContent } = useContentBlock("faro_discover_feed");
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
            { icon: "Mail", text: "hola@comunidadfaro.org" },
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
            toast.success("¡Mensaje enviado con éxito! Te contactaremos pronto.");

        } catch {
            setStatus("error");
            toast.error("Ocurrió un error inesperado de conexión.");
        }
    };

    return (
        <main className="pt-[88px]">
            {/* ── HERO ──────────────────────────────────────── */}
            <header className="relative min-h-screen flex items-center overflow-hidden">
                {/* Background: lighthouse in fog */}
                <div
                    className="absolute inset-0 bg-cover bg-center"
                    style={{
                        backgroundImage:
                            "url('https://picsum.photos/seed/1518623489648-a173ef7824f3/800/600')",
                        filter: "brightness(0.25) saturate(0.4)",
                    }}
                />
                <div
                    className="absolute inset-0"
                    style={{
                        background:
                            "linear-gradient(to bottom, rgba(0,13,42,0.5) 0%, rgba(0,13,42,0.6) 50%, var(--faro-background) 100%)",
                    }}
                />
                <div
                    className="absolute inset-0 pointer-events-none"
                    style={{
                        background:
                            "radial-gradient(ellipse at 50% 30%, rgba(165,200,255,0.08) 0%, transparent 70%)",
                    }}
                />

                <motion.div 
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, ease: "easeOut" }}
                    className="relative z-10 px-3 md:px-4 pb-4"
                >
                    <span
                        className="inline-block px-4 py-1.5 rounded-full border text-xs font-semibold uppercase tracking-wide mb-3"
                        style={{
                            borderColor: "rgba(165,200,255,0.3)",
                            color: "rgba(165,200,255,0.9)",
                            background: "rgba(165,200,255,0.05)",
                        }}
                    >
                        {heroEyebrow}
                    </span>
                    <h1
                        className="font-bold tracking-tight mb-3"
                        style={{
                            fontSize: "clamp(3.5rem, 8vw, 7rem)",
                            color: "white",
                            lineHeight: 0.95,
                        }}
                    >
                        {heroTitleLead}{" "}
                        <span
                            className="italic"
                            style={{
                                background:
                                    "linear-gradient(135deg, #a5c8ff 0%, #018abd 100%)",
                                WebkitBackgroundClip: "text",
                                WebkitTextFillColor: "transparent",
                            }}
                        >
                            {heroTitleAccent}
                        </span>{" "}
                        {heroTitleTail}
                    </h1>
                    <p
                        className="text-xl md:text-lg max-w-2xl leading-relaxed mb-3"
                        style={{ color: "rgba(217,226,255,0.7)" }}
                    >
                        {heroDescription}
                    </p>
                    <a
                        href="#contacto"
                        className="inline-flex items-center gap-3 px-4 py-2 rounded-full font-black text-sm uppercase tracking-wide text-white transition-all hover:scale-105"
                        style={{
                            background:
                                "linear-gradient(135deg, #018abd 0%, #2c609d 100%)",
                            boxShadow: "0 12px 40px rgba(1,138,189,0.4)",
                        }}
                    >
                        {heroCta}
                        <ArrowRight size={18} />
                    </a>
                </motion.div>
            </header>

            {/* ── INTRO EDITORIAL ─────────────────────────── */}
            <section
                className="py-1.5 px-3 md:px-4 lg:px-24"
                style={{ background: "var(--faro-surface-container-low)" }}
            >
                <div className="grid md:grid-cols-2 gap-3 items-center">
                    <motion.div
                        initial={{ opacity: 0, x: -30 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                    >
                        <h2
                            className="text-lg font-bold mb-3"
                            style={{ color: "var(--faro-primary)" }}
                        >
                            Un Encuentro Personal
                        </h2>
                        <div className="space-y-5">
                            <p
                                className="text-lg leading-relaxed"
                                style={{ color: "var(--faro-on-surface-variant)" }}
                            >
                                En FARO, creemos que cada historia es única. No importa
                                dónde hayas estado o qué hayas hecho, la invitación es la
                                misma:{" "}
                                <span
                                    className="font-black"
                                    style={{ color: "var(--faro-on-surface)" }}
                                >
                                    Ven y ve.
                                </span>
                            </p>
                            <p
                                className="text-lg leading-relaxed"
                                style={{ color: "var(--faro-on-surface-variant)" }}
                            >
                                Descubre un espacio donde las preguntas son bienvenidas y la
                                gracia es el lenguaje principal. Jesús ofrece descanso para el
                                alma y una dirección clara para el futuro.
                            </p>
                        </div>
                    </motion.div>
                    <div className="grid grid-cols-2 gap-4">
                        {benefitCards.map(({ icon, title, desc }, idx) => (
                            <motion.div
                                key={title}
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ delay: 0.1 * (idx + 1) }}
                                className="rounded-lg p-3 transition-transform hover:-translate-y-1 hover:shadow-lg"
                                style={{ background: "var(--faro-surface-container)" }}
                            >
                                <div
                                    className="w-10 h-10 rounded-md flex items-center justify-center mb-4"
                                    style={{
                                        background: "var(--faro-primary-container)",
                                        color: "var(--faro-primary)",
                                    }}
                                >
                                    {iconMap[icon] || <Heart size={22} />}
                                </div>
                                <h4
                                    className="font-black text-sm mb-1"
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
                            </motion.div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── TESTIMONIOS RÁPIDOS ──────────────────────── */}
            <section
                className="py-1.5 px-3 md:px-4 lg:px-24"
                style={{ background: "var(--faro-surface)" }}
            >
                <div>
                    <h2
                        className="text-xl font-bold mb-3 text-center"
                        style={{ color: "var(--faro-on-background)" }}
                    >
                        Historias que{" "}
                        <span style={{ color: "var(--faro-secondary)" }}>Iluminan</span>
                    </h2>
                    {testimonials.length === 0 ? (
                        <p className="text-center col-span-full py-8" style={{ color: "var(--faro-on-surface-variant)" }}>
                            Próximamente compartiremos historias de transformación.
                        </p>
                    ) : (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        {testimonials.map((t, idx) => (
                            <motion.div
                                key={t.id}
                                initial={{ opacity: 0, scale: 0.95 }}
                                whileInView={{ opacity: 1, scale: 1 }}
                                viewport={{ once: true }}
                                transition={{ delay: 0.1 * idx }}
                                className="rounded-lg p-4 border-b-4 hover:shadow-md transition-shadow"
                                style={{
                                    background: "var(--faro-surface-container)",
                                    borderColor: "var(--faro-primary)",
                                }}
                            >
                                <p
                                    className="text-lg italic leading-relaxed mb-3"
                                    style={{ color: "var(--faro-on-surface)" }}
                                >
                                    &quot;{t.content}&quot;
                                </p>
                                <p
                                    className="text-xs font-semibold uppercase tracking-wide"
                                    style={{ color: "var(--faro-primary)" }}
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
                className="py-1.5 px-3 md:px-4 lg:px-24"
                style={{ background: "var(--faro-surface-container-low)" }}
            >
                <div className="grid md:grid-cols-2 gap-3 items-start">
                    {/* Info lado izq */}
                    <div>
                        <h2
                            className="text-lg font-bold mb-3"
                            style={{ color: "var(--faro-on-background)" }}
                        >
                            Hablemos de Tu Caminar
                        </h2>
                        <p
                            className="text-lg leading-relaxed mb-3"
                            style={{ color: "var(--faro-on-surface-variant)" }}
                        >
                            ¿Tienes dudas? ¿Quieres orar por algo específico? Nuestro equipo
                            está aquí para acompañarte sin juicios.
                        </p>
                        <div className="space-y-5">
                            {contactInfo.map(({ icon, text }) => (
                                <div
                                    key={text}
                                    className="flex items-center gap-4"
                                    style={{ color: "var(--faro-on-surface-variant)" }}
                                >
                                    <div
                                        className="w-10 h-10 rounded-md flex items-center justify-center"
                                        style={{
                                            background: "var(--faro-primary-container)",
                                            color: "var(--faro-primary)",
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
                            background: "var(--faro-surface-container)",
                            border: "1px solid rgba(255,255,255,0.05)"
                        }}
                    >
                        {status === "sent" ? (
                            <div className="text-center py-1.5">
                                <div
                                    className="w-16 h-8 rounded-full flex items-center justify-center mx-auto mb-3"
                                    style={{ background: "var(--faro-primary-container)" }}
                                >
                                    <Heart size={28} style={{ color: "var(--faro-primary)" }} />
                                </div>
                                <h3
                                    className="text-lg font-bold mb-3"
                                    style={{ color: "var(--faro-on-surface)" }}
                                >
                                    ¡Gracias!
                                </h3>
                                <p style={{ color: "var(--faro-on-surface-variant)" }}>
                                    Hemos recibido tu mensaje. Te contactaremos pronto.
                                </p>
                            </div>
                        ) : (
                            <form onSubmit={handleSubmit} className="space-y-3">
                                <div className="grid md:grid-cols-2 gap-3">
                                    {[
                                        { key: "name", label: "Nombre completo", placeholder: "Tu nombre", type: "text" },
                                        { key: "phone", label: "WhatsApp", placeholder: "+57 300...", type: "tel" },
                                    ].map(({ key, label, placeholder, type }) => (
                                        <div key={key}>
                                            <label
                                                className="text-[10px] font-semibold uppercase tracking-wide block mb-3"
                                                style={{ color: "var(--faro-on-surface-variant)" }}
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
                                                    background: "var(--faro-surface)",
                                                    border: "2px solid var(--faro-outline-variant)",
                                                    color: "var(--faro-on-surface)",
                                                    // @ts-expect-error Tailwind custom properties are not typed by default in React CSS properties
                                                    "--tw-ring-color": "var(--faro-primary)",
                                                }}
                                            />
                                        </div>
                                    ))}
                                </div>
                                <div>
                                    <label
                                        className="text-[10px] font-semibold uppercase tracking-wide block mb-3"
                                        style={{ color: "var(--faro-on-surface-variant)" }}
                                    >
                                        ¿En qué podemos ayudarte?
                                    </label>
                                    <textarea
                                        value={form.message}
                                        onChange={(e) =>
                                            setForm((f) => ({ ...f, message: e.target.value }))
                                        }
                                        placeholder="Cuéntanos un poco sobre ti o tu petición de oración..."
                                        rows={4}
                                        className="w-full rounded-lg px-3 py-1.5 text-sm focus:outline-none resize-none"
                                        style={{
                                            background: "var(--faro-surface)",
                                            border: "2px solid var(--faro-outline-variant)",
                                            color: "var(--faro-on-surface)",
                                        }}
                                    />
                                </div>
                                <button
                                    type="submit"
                                    disabled={status === "sending"}
                                    className="w-full py-2 rounded-lg font-black text-sm uppercase tracking-wide transition-all hover:scale-[1.02] disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:scale-100"
                                    style={{
                                        background:
                                            "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary))",
                                        color: "var(--faro-on-primary)",
                                        boxShadow: "0 8px 24px rgba(44,96,157,0.3)",
                                    }}
                                >
                                    {status === "sending"
                                        ? "Enviando..."
                                        : "Enviar mensaje y conectar"}
                                </button>
                                {status === "error" && (
                                    <p
                                        className="text-xs text-center font-bold"
                                        style={{ color: "var(--faro-error)" }}
                                    >
                                        Hubo un error. Intenta de nuevo o escríbenos directamente.
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

