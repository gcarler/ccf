"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import RichText from "@/components/public/RichText";
import { useCmsV2Page } from "@/hooks/useCmsV2Page";
import { apiFetch } from "@/lib/http";

import { toast } from "sonner";
import CmsPageOverride from "@/components/public/cms/CmsPageOverride";

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
        <CmsPageOverride slug="boletin">
            <main className="pt-[100px] flex-1 flex items-center justify-center px-3 md:px-6 lg:px-8 xl:px-12 py-8 md:py-12 lg:py-16">
                <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="w-full max-w-3xl rounded-2xl p-8 md:p-12 relative overflow-hidden text-center shadow-2xl border"
                    style={{
                        backgroundColor: "var(--site-primary-container)",
                        borderColor: "var(--site-outline-variant)"
                    }}
                >
                    <div className="relative z-10">
                        <p className="text-sm font-semibold uppercase tracking-widest mb-3" style={{ color: "var(--site-primary)" }}>
                            {subtitle}
                        </p>
                        <h1 className="font-black text-3xl md:text-4xl lg:text-5xl tracking-tight mb-4" style={{ color: "var(--site-on-background)" }}>
                            {title}
                        </h1>
                        <RichText html={description} className="text-lg md:text-xl mb-8 max-w-xl mx-auto leading-relaxed" />
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
                                    className="px-8 py-3.5 rounded-xl font-bold text-base text-white transition-all hover:scale-105 disabled:opacity-60 disabled:cursor-not-allowed shadow-lg"
                                    style={{ background: "var(--site-cta-gradient)" }}
                                >
                                    {status === "sending" ? sendingLabel : ctaText}
                                </button>
                            </form>
                        )}
                    </div>
                </motion.div>
            </main>
        </CmsPageOverride>
    );
}
