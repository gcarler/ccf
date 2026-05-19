"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";

export default function BoletinPage() {
    const [status, setStatus] = useState<"idle" | "sending" | "sent">("idle");
    const [email, setEmail] = useState("");

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setStatus("sending");
        setTimeout(() => setStatus("sent"), 1500);
    };

    return (
        <main className="pt-[88px] min-h-[80vh] flex items-center justify-center bg-faro-surface">
            <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                className="max-w-2xl mx-auto rounded-[3rem] p-12 md:p-20 relative overflow-hidden text-center shadow-xl border"
                style={{
                    backgroundColor: "var(--faro-primary-container)",
                    borderColor: "var(--faro-outline-variant)"
                }}
            >
                <div className="relative z-10">
                    <h1 className="font-black text-3xl md:text-5xl tracking-tight mb-6" style={{ color: "var(--faro-on-background)" }}>
                        Suscríbete a nuestro boletín
                    </h1>
                    <p className="text-lg mb-10" style={{ color: "var(--faro-on-surface-variant)" }}>
                        Recibe meditaciones semanales, anuncios de eventos y contenido exclusivo directo a tu correo.
                    </p>
                    {status === "sent" ? (
                        <div className="text-2xl font-black text-faro-primary">¡Gracias por suscribirte!</div>
                    ) : (
                        <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-4 max-w-lg mx-auto">
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="Tu correo electrónico"
                                required
                                className="flex-grow rounded-2xl px-6 py-4 text-sm focus:outline-none"
                                style={{
                                    background: "var(--faro-surface)",
                                    border: "2px solid var(--faro-outline-variant)",
                                    color: "var(--faro-on-surface)",
                                }}
                            />
                            <button
                                type="submit"
                                disabled={status === "sending"}
                                className="px-8 py-4 rounded-2xl font-black text-sm uppercase tracking-widest text-white transition-all hover:scale-105 disabled:opacity-60 disabled:cursor-not-allowed"
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
