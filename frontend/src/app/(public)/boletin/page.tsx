"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import RichText from "@/components/public/RichText";
import { useCmsV2Page } from "@/hooks/useCmsV2Page";
import { apiFetch } from "@/lib/http";

import { toast } from "sonner";

export default function BoletinPage() {
    const boletinPage = useCmsV2Page('boletin');
    const cms = boletinPage?.blocks?.hero;
    const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");
    const [email, setEmail] = useState("");

    const content = cms?.content ? JSON.parse(cms.content) : null;
    const title = content?.title || "Recibe nuestra palabra de aliento";
    const subtitle = content?.subtitle || "Boletín Semanal FARO";
    const description = content?.description || "Cada semana te enviamos una reflexión bíblica, un versículo de ánimo y consejos prácticos para fortalecer tu fe.";
    const ctaText = content?.cta_text || "Suscribirme ahora";
    const successMessage = content?.success_message || "¡Gracias por suscribirte!";
    const _errorMessage = content?.error_message || "No se pudo suscribir. Intenta de nuevo.";
    const emailPlaceholder = content?.email_placeholder || "Tu correo electrónico";
    const sendingLabel = content?.sending_label || "Enviando...";

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setStatus("sending");
        try {
            await apiFetch("/public/newsletter/subscribe", {
                method: "POST",
                body: { email, source: "newsletter-web", landing_page: "/boletin" },
            });
            setStatus("sent");
            toast.success("¡Suscrito al boletín de FARO!");
        } catch {
            setStatus("error");
            toast.error("No se pudo suscribir. Intenta de nuevo.");
        }
    };

    return (
        <main className="pt-[100px] flex-1 flex items-center justify-center">
            <section className="faro-section faro-container w-full flex items-center justify-center">
                <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="faro-card w-full max-w-3xl p-8 md:p-14 relative overflow-hidden text-center"
                    style={{
                        backgroundColor: "var(--site-primary-container)",
                    }}
                >
                    <div className="relative z-10">
                        <p className="text-sm font-semibold uppercase tracking-widest mb-3" style={{ color: "var(--site-primary)" }}>
                            {subtitle}
                        </p>
                        <h1 className="font-black faro-display text-3xl md:text-4xl lg:text-5xl mb-4" style={{ color: "var(--site-on-background)" }}>
                            {title}
                        </h1>
                        <RichText html={description} className="faro-body text-lg md:text-xl mb-8 max-w-xl mx-auto" />
                        {status === "sent" ? (
                            <motion.div
                                initial={{ opacity: 0, scale: 0.9 }}
                                animate={{ opacity: 1, scale: 1 }}
                                className="text-xl font-bold"
                                style={{ color: "var(--site-primary)" }}
                            >
                                {successMessage}
                            </motion.div>
                        ) : (
                            <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-4 max-w-lg mx-auto">
                                <input
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder={emailPlaceholder}
                                    required
                                    className="flex-grow rounded-xl px-5 py-3.5 text-base focus:outline-none focus:ring-2"
                                    style={{
                                        background: "var(--site-surface)",
                                        border: "2px solid var(--site-outline-variant)",
                                        color: "var(--site-on-surface)",
                                    }}
                                />
                                <button
                                    type="submit"
                                    disabled={status === "sending"}
                                    className="faro-button disabled:opacity-60 disabled:cursor-not-allowed"
                                    style={{ background: "var(--site-cta-gradient)", color: "var(--site-on-primary)" }}
                                >
                                    {status === "sending" ? sendingLabel : ctaText}
                                </button>
                            </form>
                        )}
                    </div>
                </motion.div>
            </section>
        </main>
    );
}
