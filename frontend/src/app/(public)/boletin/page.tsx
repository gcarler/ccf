"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import RichText from "@/components/public/RichText";
import { useContentBlock } from "@/hooks/useContent";
import { FaroNavbar, FaroFooter } from "@/components/public/FAROShared";
import { apiFetch } from "@/lib/http";
import { toast } from "sonner";

export default function BoletinPage() {
    const { data: cms } = useContentBlock("faro_boletin_hero");
    const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");
    const [email, setEmail] = useState("");

    const content = cms?.content ? JSON.parse(cms.content) : null;
    const title = content?.title || "Recibe nuestra palabra de aliento";
    const subtitle = content?.subtitle || "Boletín Semanal FARO";
    const description = content?.description || "Cada semana te enviamos una reflexión bíblica, un versículo de ánimo y consejos prácticos para fortalecer tu fe.";
    const ctaText = content?.cta_text || "Suscribirme ahora";

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
        <div className="min-h-screen flex flex-col bg-faro-surface">
            <FaroNavbar />
            <main className="flex-1 flex items-center justify-center px-3 md:px-6 lg:px-8 xl:px-12 py-8 md:py-12 lg:py-16">
                <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="w-full max-w-3xl rounded-2xl p-8 md:p-12 relative overflow-hidden text-center shadow-2xl border"
                    style={{
                        backgroundColor: "var(--faro-primary-container)",
                        borderColor: "var(--faro-outline-variant)"
                    }}
                >
                    <div className="relative z-10">
                        <p className="text-sm font-semibold uppercase tracking-widest mb-3" style={{ color: "var(--faro-primary)" }}>
                            {subtitle}
                        </p>
                        <h1 className="font-black text-3xl md:text-4xl lg:text-5xl tracking-tight mb-4" style={{ color: "var(--faro-on-background)" }}>
                            {title}
                        </h1>
                        <RichText html={description} className="text-lg md:text-xl mb-8 max-w-xl mx-auto leading-relaxed" />
                        {status === "sent" ? (
                            <motion.div
                                initial={{ opacity: 0, scale: 0.9 }}
                                animate={{ opacity: 1, scale: 1 }}
                                className="text-xl font-bold"
                                style={{ color: "var(--faro-primary)" }}
                            >
                                ¡Gracias por suscribirte!
                            </motion.div>
                        ) : (
                            <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-4 max-w-lg mx-auto">
                                <input
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder="Tu correo electrónico"
                                    required
                                    className="flex-grow rounded-xl px-5 py-3.5 text-base focus:outline-none focus:ring-2"
                                    style={{
                                        background: "var(--faro-surface)",
                                        border: "2px solid var(--faro-outline-variant)",
                                        color: "var(--faro-on-surface)",
                                    }}
                                />
                                <button
                                    type="submit"
                                    disabled={status === "sending"}
                                    className="px-8 py-3.5 rounded-xl font-bold text-base text-white transition-all hover:scale-105 disabled:opacity-60 disabled:cursor-not-allowed shadow-lg"
                                    style={{ background: "linear-gradient(135deg, var(--faro-primary) 0%, var(--faro-secondary) 100%)" }}
                                >
                                    {status === "sending" ? "Enviando..." : ctaText}
                                </button>
                            </form>
                        )}
                    </div>
                </motion.div>
            </main>
            <FaroFooter />
        </div>
    );
}
