"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { apiFetch } from "@/lib/http";
import { toast } from "sonner";

export default function BoletinPage() {
    const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");
    const [email, setEmail] = useState("");

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setStatus("sending");
        try {
            await apiFetch("/public/newsletter/subscribe", {
                method: "POST",
                body: { email },
            });
            setStatus("sent");
            toast.success("¡Suscrito al boletín de FARO!");
        } catch {
            setStatus("error");
            toast.error("No se pudo suscribir. Intenta de nuevo.");
        }
    };

    return (
        <main className="pt-[88px] min-h-[80vh] flex items-center justify-center bg-faro-surface">
            <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-lg p-4 md:p-4 relative overflow-hidden text-center shadow-xl border"
                style={{
                    backgroundColor: "var(--faro-primary-container)",
                    borderColor: "var(--faro-outline-variant)"
                }}
            >
                <div className="relative z-10">
                    <h1 className="font-black text-xl md:text-xl tracking-tight mb-3" style={{ color: "var(--faro-on-background)" }}>
                        Suscríbete a nuestro boletín
                    </h1>
                    <p className="text-lg mb-3" style={{ color: "var(--faro-on-surface-variant)" }}>
                        Recibe meditaciones semanales, anuncios de eventos y contenido exclusivo directo a tu correo.
                    </p>
                    {status === "sent" ? (
                        <div className="text-lg font-bold text-faro-primary">¡Gracias por suscribirte!</div>
                    ) : (
                        <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-4 max-w-lg mx-auto">
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="Tu correo electrónico"
                                required
                                className="flex-grow rounded-lg px-3 py-1.5 text-sm focus:outline-none"
                                style={{
                                    background: "var(--faro-surface)",
                                    border: "2px solid var(--faro-outline-variant)",
                                    color: "var(--faro-on-surface)",
                                }}
                            />
                            <button
                                type="submit"
                                disabled={status === "sending"}
                                className="px-4 py-1.5 rounded-lg font-black text-sm uppercase tracking-wide text-white transition-all hover:scale-105 disabled:opacity-60 disabled:cursor-not-allowed"
                                style={{ background: "linear-gradient(135deg, var(--faro-primary) 0%, var(--faro-secondary) 100%)" }}
                            >
                                {status === "sending" ? "Enviando..." : "Suscribirme"}
                            </button>
                        </form>
                    )}
                </div>
            </motion.div>
        </main>
    );
}
