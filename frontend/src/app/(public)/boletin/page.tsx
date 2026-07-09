"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import RichText from "@/components/public/RichText";
import { useCmsV2Page } from "@/hooks/useCmsV2Page";
import { apiFetch } from "@/lib/http";
import { SITE_NAME } from "@/lib/site-config";

import { toast } from "sonner";

export default function BoletinPage() {
    const boletinPage = useCmsV2Page('newsletter');
    const cms = boletinPage?.blocks?.hero;
    const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");
    const [email, setEmail] = useState("");

    const content = cms?.content ? JSON.parse(cms.content) : null;
    const title = typeof content?.title === "string" ? content.title : "";
    const subtitle = typeof content?.subtitle === "string" ? content.subtitle : "";
    const description = typeof content?.description === "string" ? content.description : "";
    const ctaText = typeof content?.cta_text === "string" ? content.cta_text : "";
    const successMessage = typeof content?.success_message === "string" ? content.success_message : "";
    const emailPlaceholder = typeof content?.email_placeholder === "string" ? content.email_placeholder : "";
    const sendingLabel = typeof content?.sending_label === "string" ? content.sending_label : "";

    const hasContent = title || subtitle || description || ctaText;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setStatus("sending");
        try {
            await apiFetch("/public/newsletter/subscribe", {
                method: "POST",
                body: { email, source: "newsletter-web", landing_page: "/boletin" },
            });
            setStatus("sent");
            toast.success(`¡Suscrito al boletín de ${SITE_NAME}!`);
        } catch {
            setStatus("error");
            toast.error("No se pudo suscribir. Intenta de nuevo.");
        }
    };

    return (
        <main className="pt-[100px] flex-1 flex items-center justify-center">
            {hasContent && (
                <section className="ccf-section ccf-container w-full flex items-center justify-center">
                    <motion.div
                        initial={{ opacity: 0, y: 30 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="ccf-card w-full max-w-3xl p-8 md:p-14 relative overflow-hidden text-center"
                        style={{
                            backgroundColor: "var(--site-primary-container)",
                        }}
                    >
                        <div className="relative z-10">
                            {subtitle && (
                                <p className="text-sm font-semibold uppercase tracking-widest mb-3" style={{ color: "var(--site-primary)" }}>
                                    {subtitle}
                                </p>
                            )}
                            {title && (
                                <h1 className="font-black ccf-display text-3xl md:text-4xl lg:text-5xl mb-4" style={{ color: "var(--site-on-background)" }}>
                                    {title}
                                </h1>
                            )}
                            {description && (
                                <RichText html={description} className="ccf-body text-lg md:text-xl mb-8 max-w-xl mx-auto" />
                            )}
                            {status === "sent" ? (
                                successMessage && (
                                    <motion.div
                                        initial={{ opacity: 0, scale: 0.9 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        className="text-xl font-bold"
                                        style={{ color: "var(--site-primary)" }}
                                    >
                                        {successMessage}
                                    </motion.div>
                                )
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
                                    {ctaText && (
                                        <button
                                            type="submit"
                                            disabled={status === "sending"}
                                            className="ccf-button disabled:opacity-60 disabled:cursor-not-allowed"
                                            style={{ background: "var(--site-cta-gradient)", color: "var(--site-on-primary)" }}
                                        >
                                            {status === "sending" ? sendingLabel || "Enviando..." : ctaText}
                                        </button>
                                    )}
                                </form>
                            )}
                        </div>
                    </motion.div>
                </section>
            )}
        </main>
    );
}
