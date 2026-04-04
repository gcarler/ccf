"use client";

import React, { useState } from "react";
import Link from "next/link";
import { ArrowRight, Clock, Mail, Heart, Star, Shield } from "lucide-react";
import { useContentBlock } from "@/hooks/useContent";

export default function ConocerAJesusPage() {
    const { data: heroContent } = useContentBlock("faro_discover_hero");
    const heroEyebrow = heroContent?.eyebrow || "Inicia tu camino";
    const heroTitleLead = heroContent?.title_lead || "La Luz que ";
    const heroTitleAccent = heroContent?.title_accent || "Guía";
    const heroTitleTail = heroContent?.title_tail || " Tu Vida.";
    const heroDescription = heroContent?.description || "Conocer a Jesús no es una religión, es el comienzo de una relación que transforma la oscuridad en un propósito eterno.";
    const heroCta = heroContent?.cta || "Quiero conocer a Jesús";

    const [form, setForm] = useState({ name: "", phone: "", message: "" });
    const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setStatus("sending");
        try {
            const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
            const res = await fetch(`${API}/api/crm/members`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    full_name: form.name,
                    phone: form.phone,
                    notes: form.message,
                    status: "prospect",
                    source: "conocer-a-jesus",
                }),
            });
            if (res.ok) setStatus("sent");
            else setStatus("error");
        } catch {
            setStatus("error");
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
                            "url('https://images.unsplash.com/photo-1518623489648-a173ef7824f3?w=1600&q=80')",
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

                <div className="relative z-10 max-w-4xl mx-auto px-6 md:px-16 pb-20">
                    <span
                        className="inline-block px-4 py-1.5 rounded-full border text-xs font-black uppercase tracking-[0.25em] mb-8"
                        style={{
                            borderColor: "rgba(165,200,255,0.3)",
                            color: "rgba(165,200,255,0.9)",
                            background: "rgba(165,200,255,0.05)",
                        }}
                    >
                        {heroEyebrow}
                    </span>
                    <h1
                        className="font-black tracking-tight mb-8"
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
                        className="text-xl md:text-2xl max-w-2xl leading-relaxed mb-12"
                        style={{ color: "rgba(217,226,255,0.7)" }}
                    >
                        {heroDescription}
                    </p>
                    <a
                        href="#contacto"
                        className="inline-flex items-center gap-3 px-10 py-5 rounded-full font-black text-sm uppercase tracking-[0.2em] text-white transition-all hover:scale-105"
                        style={{
                            background:
                                "linear-gradient(135deg, #018abd 0%, #2c609d 100%)",
                            boxShadow: "0 12px 40px rgba(1,138,189,0.4)",
                        }}
                    >
                        {heroCta}
                        <ArrowRight size={18} />
                    </a>
                </div>
            </header>

            {/* ── INTRO EDITORIAL ─────────────────────────── */}
            <section
                className="py-24 px-6 md:px-16 lg:px-24"
                style={{ background: "var(--faro-surface-container-low)" }}
            >
                <div className="max-w-6xl mx-auto grid md:grid-cols-2 gap-16 items-center">
                    <div>
                        <h2
                            className="text-4xl font-black mb-6"
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
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        {[
                            { icon: <Heart size={22} />, title: "Gracia sin condenas", desc: "Eres bienvenido tal como eres." },
                            { icon: <Star size={22} />, title: "Propósito real", desc: "Descubre para qué fuiste creado." },
                            { icon: <Shield size={22} />, title: "Comunidad que cuida", desc: "No estarás solo en este camino." },
                            { icon: <ArrowRight size={22} />, title: "Primer paso simple", desc: "Escríbenos y conectamos." },
                        ].map(({ icon, title, desc }) => (
                            <div
                                key={title}
                                className="rounded-2xl p-6"
                                style={{ background: "var(--faro-surface-container)" }}
                            >
                                <div
                                    className="w-10 h-10 rounded-xl flex items-center justify-center mb-4"
                                    style={{
                                        background: "var(--faro-primary-container)",
                                        color: "var(--faro-primary)",
                                    }}
                                >
                                    {icon}
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
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── TESTIMONIOS RÁPIDOS ──────────────────────── */}
            <section
                className="py-20 px-6 md:px-16 lg:px-24"
                style={{ background: "var(--faro-surface)" }}
            >
                <div className="max-w-6xl mx-auto">
                    <h2
                        className="text-3xl font-black mb-12 text-center"
                        style={{ color: "var(--faro-on-background)" }}
                    >
                        Historias que{" "}
                        <span style={{ color: "var(--faro-secondary)" }}>Iluminan</span>
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {[
                            { q: "Encontré la paz que mi carrera no podía darme.", a: "Mateo R., Diseñador" },
                            { q: "Llegué buscando respuestas y encontré una familia que me aceptó tal cual soy.", a: "Lucía G." },
                            { q: "El curso de fundamentos cambió mi perspectiva sobre el propósito de mi vida diaria.", a: "Carlos M." },
                        ].map(({ q, a }) => (
                            <div
                                key={a}
                                className="rounded-2xl p-8 border-b-4"
                                style={{
                                    background: "var(--faro-surface-container)",
                                    borderColor: "var(--faro-primary)",
                                }}
                            >
                                <p
                                    className="text-lg italic leading-relaxed mb-6"
                                    style={{ color: "var(--faro-on-surface)" }}
                                >
                                    "{q}"
                                </p>
                                <p
                                    className="text-xs font-black uppercase tracking-widest"
                                    style={{ color: "var(--faro-primary)" }}
                                >
                                    — {a}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── FORMULARIO DE CONTACTO ───────────────────── */}
            <section
                id="contacto"
                className="py-24 px-6 md:px-16 lg:px-24"
                style={{ background: "var(--faro-surface-container-low)" }}
            >
                <div className="max-w-6xl mx-auto grid md:grid-cols-2 gap-16 items-start">
                    {/* Info lado izq */}
                    <div>
                        <h2
                            className="text-4xl font-black mb-6"
                            style={{ color: "var(--faro-on-background)" }}
                        >
                            Hablemos de Tu Caminar
                        </h2>
                        <p
                            className="text-lg leading-relaxed mb-10"
                            style={{ color: "var(--faro-on-surface-variant)" }}
                        >
                            ¿Tienes dudas? ¿Quieres orar por algo específico? Nuestro equipo
                            está aquí para acompañarte sin juicios.
                        </p>
                        <div className="space-y-5">
                            {[
                                { icon: <Clock size={18} />, text: "Respuesta en menos de 24 horas" },
                                { icon: <Mail size={18} />, text: "hola@comunidadfaro.org" },
                            ].map(({ icon, text }) => (
                                <div
                                    key={text}
                                    className="flex items-center gap-4"
                                    style={{ color: "var(--faro-on-surface-variant)" }}
                                >
                                    <div
                                        className="w-10 h-10 rounded-xl flex items-center justify-center"
                                        style={{
                                            background: "var(--faro-primary-container)",
                                            color: "var(--faro-primary)",
                                        }}
                                    >
                                        {icon}
                                    </div>
                                    <span className="text-sm">{text}</span>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Formulario */}
                    <div
                        className="rounded-3xl p-8 md:p-12"
                        style={{ background: "var(--faro-surface-container)" }}
                    >
                        {status === "sent" ? (
                            <div className="text-center py-16">
                                <div
                                    className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-6"
                                    style={{ background: "var(--faro-primary-container)" }}
                                >
                                    <Heart size={28} style={{ color: "var(--faro-primary)" }} />
                                </div>
                                <h3
                                    className="text-2xl font-black mb-3"
                                    style={{ color: "var(--faro-on-surface)" }}
                                >
                                    ¡Gracias!
                                </h3>
                                <p style={{ color: "var(--faro-on-surface-variant)" }}>
                                    Hemos recibido tu mensaje. Te contactaremos pronto.
                                </p>
                            </div>
                        ) : (
                            <form onSubmit={handleSubmit} className="space-y-6">
                                <div className="grid md:grid-cols-2 gap-6">
                                    {[
                                        { key: "name", label: "Nombre completo", placeholder: "Tu nombre", type: "text" },
                                        { key: "phone", label: "WhatsApp", placeholder: "+57 300...", type: "tel" },
                                    ].map(({ key, label, placeholder, type }) => (
                                        <div key={key}>
                                            <label
                                                className="text-[10px] font-black uppercase tracking-[0.2em] block mb-3"
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
                                                className="w-full rounded-2xl px-5 py-4 text-sm focus:outline-none focus:ring-2 transition-all"
                                                style={{
                                                    background: "var(--faro-surface)",
                                                    border: "2px solid var(--faro-outline-variant)",
                                                    color: "var(--faro-on-surface)",
                                                    // @ts-ignore
                                                    "--tw-ring-color": "var(--faro-primary)",
                                                }}
                                            />
                                        </div>
                                    ))}
                                </div>
                                <div>
                                    <label
                                        className="text-[10px] font-black uppercase tracking-[0.2em] block mb-3"
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
                                        className="w-full rounded-2xl px-5 py-4 text-sm focus:outline-none resize-none"
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
                                    className="w-full py-5 rounded-2xl font-black text-sm uppercase tracking-widest text-white transition-all hover:scale-[1.02] disabled:opacity-60"
                                    style={{
                                        background:
                                            "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary))",
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
                    </div>
                </div>
            </section>
        </main>
    );
}
