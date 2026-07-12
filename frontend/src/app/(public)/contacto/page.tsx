"use client";

import React, { useState } from "react";
import { Send, CheckCircle, Mail, Phone, User, MessageSquare, Loader2 } from "lucide-react";
import { apiFetch } from "@/lib/http";
import { toast } from "sonner";

export default function ContactoPage() {
    const [form, setForm] = useState({ full_name: "", email: "", phone: "", notes: "" });
    const [submitted, setSubmitted] = useState(false);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.full_name.trim() || !form.email.trim()) return;

        // Basic email validation
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
            toast.error("Por favor ingresa un email válido");
            return;
        }

        setLoading(true);
        try {
            await apiFetch("/public/contact", {
                method: "POST",
                body: {
                    full_name: form.full_name.trim(),
                    email: form.email.trim(),
                    phone: form.phone.trim() || undefined,
                    notes: form.notes.trim() || undefined,
                    source: "contacto-web",
                },
                silent: true,
            });
            setSubmitted(true);
            toast.success("¡Gracias! Te contactaremos pronto.");
        } catch {
            toast.error("Error al enviar. Intenta de nuevo.");
        } finally {
            setLoading(false);
        }
    };

    if (submitted) {
        return (
            <main className="min-h-screen bg-[hsl(var(--bg-primary))] flex items-center justify-center p-4">
                <div className="max-w-md text-center space-y-6">
                    <div className="size-16 rounded-full bg-emerald-100 dark:bg-emerald-900/20 flex items-center justify-center mx-auto">
                        <CheckCircle size={32} className="text-emerald-600" />
                    </div>
                    <h1 className="text-2xl font-bold text-[hsl(var(--text-primary))]">¡Mensaje enviado!</h1>
                    <p className="text-[hsl(var(--text-secondary))]">
                        Gracias <strong>{form.full_name}</strong>. Nuestro equipo te contactará pronto al email <strong>{form.email}</strong>.
                    </p>
                    <button
                        onClick={() => { setSubmitted(false); setForm({ full_name: "", email: "", phone: "", notes: "" }); }}
                        className="px-6 py-3 bg-[hsl(var(--primary))] text-white rounded-lg font-bold text-sm hover:opacity-90 transition-opacity"
                    >
                        Enviar otro mensaje
                    </button>
                </div>
            </main>
        );
    }

    return (
        <main className="min-h-screen bg-[hsl(var(--bg-primary))] py-20 px-4">
            <div className="max-w-2xl mx-auto">
                {/* Header */}
                <div className="text-center mb-10">
                    <h1 className="text-3xl font-bold text-[hsl(var(--text-primary))] mb-3">Contáctanos</h1>
                    <p className="text-[hsl(var(--text-secondary))] max-w-md mx-auto">
                        ¿Tienes preguntas? ¿Quieres conocernos? Déjanos tus datos y te contactaremos pronto.
                    </p>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-2xl p-8 space-y-6 shadow-lg">
                    {/* Name */}
                    <div className="space-y-2">
                        <label className="flex items-center gap-2 text-sm font-semibold text-[hsl(var(--text-primary))]">
                            <User size={16} className="text-[hsl(var(--primary))]" />
                            Nombre completo *
                        </label>
                        <input
                            type="text"
                            required
                            value={form.full_name}
                            onChange={e => setForm({ ...form, full_name: e.target.value })}
                            placeholder="Tu nombre"
                            className="w-full px-4 py-3 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-black/20 outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/30 focus:border-[hsl(var(--primary))] text-[hsl(var(--text-primary))] transition-all"
                        />
                    </div>

                    {/* Email */}
                    <div className="space-y-2">
                        <label className="flex items-center gap-2 text-sm font-semibold text-[hsl(var(--text-primary))]">
                            <Mail size={16} className="text-[hsl(var(--primary))]" />
                            Email *
                        </label>
                        <input
                            type="email"
                            required
                            value={form.email}
                            onChange={e => setForm({ ...form, email: e.target.value })}
                            placeholder="tu@email.com"
                            className="w-full px-4 py-3 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-black/20 outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/30 focus:border-[hsl(var(--primary))] text-[hsl(var(--text-primary))] transition-all"
                        />
                    </div>

                    {/* Phone */}
                    <div className="space-y-2">
                        <label className="flex items-center gap-2 text-sm font-semibold text-[hsl(var(--text-primary))]">
                            <Phone size={16} className="text-[hsl(var(--primary))]" />
                            Teléfono
                        </label>
                        <input
                            type="tel"
                            value={form.phone}
                            onChange={e => setForm({ ...form, phone: e.target.value })}
                            placeholder="+57 300 123 4567"
                            className="w-full px-4 py-3 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-black/20 outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/30 focus:border-[hsl(var(--primary))] text-[hsl(var(--text-primary))] transition-all"
                        />
                    </div>

                    {/* Message */}
                    <div className="space-y-2">
                        <label className="flex items-center gap-2 text-sm font-semibold text-[hsl(var(--text-primary))]">
                            <MessageSquare size={16} className="text-[hsl(var(--primary))]" />
                            ¿En qué te podemos ayudar?
                        </label>
                        <textarea
                            value={form.notes}
                            onChange={e => setForm({ ...form, notes: e.target.value })}
                            placeholder="Cuéntanos cómo podemos ayudarte..."
                            rows={4}
                            className="w-full px-4 py-3 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-black/20 outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/30 focus:border-[hsl(var(--primary))] text-[hsl(var(--text-primary))] transition-all resize-none"
                        />
                    </div>

                    {/* Submit */}
                    <button
                        type="submit"
                        disabled={loading || !form.full_name.trim() || !form.email.trim()}
                        className="w-full flex items-center justify-center gap-3 px-6 py-4 bg-[hsl(var(--primary))] text-white rounded-xl font-bold text-sm uppercase tracking-wide shadow-xl shadow-blue-500/20 hover:opacity-90 active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {loading ? (
                            <Loader2 size={18} className="animate-spin" />
                        ) : (
                            <Send size={18} />
                        )}
                        {loading ? "Enviando..." : "Enviar mensaje"}
                    </button>
                </form>

                {/* Footer info */}
                <div className="mt-8 text-center text-sm text-[hsl(var(--text-secondary))]">
                    <p>También puedes llamarnos directamente o visitarnos en nuestras sedes.</p>
                </div>
            </div>
        </main>
    );
}
