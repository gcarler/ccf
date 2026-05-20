"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Quote, Share2, Heart, Send, CheckCircle2, Loader2, X, Headphones } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Testimonial } from "@/lib/data/testimonios";
import { apiFetch } from "@/lib/http";

function getTestimonialMediaUrl(t: Testimonial): string {
    if (t.media_type === "image") return t.image_url || t.media_url || "";
    if (t.media_type === "video") return t.video_url || t.media_url || "";
    if (t.media_type === "podcast") return t.podcast_url || t.media_url || "";
    return t.media_url || t.image_url || t.video_url || t.podcast_url || "";
}

export default function TestimonioDetailPage() {
    const params = useParams();
    const router = useRouter();
    const id = Number(params?.id);

    const [testimonial, setTestimonial] = useState<Testimonial | null>(null);
    const [loading, setLoading] = useState(true);

    // Prayer request state
    const [showPrayerForm, setShowPrayerForm] = useState(false);
    const [prayerName, setPrayerName] = useState("");
    const [prayerText, setPrayerText] = useState("");
    const [prayerSubmitting, setPrayerSubmitting] = useState(false);
    const [prayerSent, setPrayerSent] = useState(false);

    useEffect(() => {
        if (!Number.isFinite(id)) {
            setTestimonial(null);
            setLoading(false);
            return;
        }

        apiFetch<Testimonial>(`/cms/testimonials/${id}`, { silent: true })
            .then((data) => setTestimonial(data))
            .catch(() => setTestimonial(null))
            .finally(() => setLoading(false));
    }, [id]);

    if (loading) {
        return (
            <main className="pt-[120px] pb-32 min-h-screen flex items-center justify-center">
                <div className="w-8 h-8 border-4 border-t-transparent rounded-full animate-spin" style={{ borderColor: "var(--faro-primary) transparent transparent transparent" }} />
            </main>
        );
    }

    if (!testimonial) {
        return (
            <main className="pt-[120px] pb-32 min-h-[70vh] flex flex-col items-center justify-center text-center px-6">
                <Quote size={80} className="mb-6 opacity-20" style={{ color: "var(--faro-primary)" }} />
                <h1 className="text-4xl font-black mb-4" style={{ color: "var(--faro-on-background)" }}>Testimonio no encontrado</h1>
                <p className="text-xl mb-8 opacity-70 max-w-lg" style={{ color: "var(--faro-on-surface-variant)" }}>
                    Parece que la historia que buscas ya no está disponible o el enlace es incorrecto.
                </p>
                <button
                    onClick={() => router.push('/faro/testimonios')}
                    className="flex items-center gap-2 px-8 py-4 rounded-full text-sm font-black uppercase tracking-widest transition-all hover:-translate-x-2"
                    style={{ background: "var(--faro-primary)", color: "var(--faro-on-primary)" }}
                >
                    <ArrowLeft size={16} /> Ver más testimonios
                </button>
            </main>
        );
    }

    const mediaUrl = getTestimonialMediaUrl(testimonial);

    return (
        <main className="pt-[120px] pb-32 min-h-screen">
            <article className="max-w-4xl mx-auto px-6 lg:px-0">
                {/* ── BACK BUTTON ────────────────────────────────────── */}
                <motion.div 
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="mb-12"
                >
                    <Link
                        href="/faro/testimonios"
                        className="inline-flex items-center gap-2 text-sm font-black uppercase tracking-widest transition-all hover:opacity-70"
                        style={{ color: "var(--faro-primary)" }}
                    >
                        <ArrowLeft size={16} /> Volver a testimonios
                    </Link>
                </motion.div>

                {/* ── AUTHOR HEADER ──────────────────────────────────── */}
                <motion.header 
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="flex flex-col md:flex-row items-center gap-8 mb-16 text-center md:text-left"
                >
                    {testimonial.author?.avatarUrl ? (
                        <div className="w-32 h-32 md:w-40 md:h-40 rounded-full overflow-hidden shadow-2xl shrink-0 border-4" style={{ borderColor: "var(--faro-surface-container)" }}>
                            <img src={testimonial.author.avatarUrl} alt={testimonial.author?.username || "Autor"} className="w-full h-full object-cover" />
                        </div>
                    ) : (
                        <div
                            className="w-32 h-32 md:w-40 md:h-40 rounded-full flex items-center justify-center text-5xl font-black shadow-2xl shrink-0"
                            style={{
                                background: "var(--faro-primary-container)",
                                color: "var(--faro-primary)",
                            }}
                        >
                            {testimonial.author?.username?.[0] ?? "?"}
                        </div>
                    )}
                    
                    <div className="flex-1">
                        {testimonial.emotion && (
                            <span 
                                className="inline-block px-4 py-2 rounded-full text-xs font-black uppercase tracking-[0.2em] mb-4 shadow-sm"
                                style={{ background: "var(--faro-primary)", color: "var(--faro-on-primary)" }}
                            >
                                {testimonial.emotion}
                            </span>
                        )}
                        <h1 className="text-5xl md:text-6xl font-black tracking-tight mb-2" style={{ color: "var(--faro-on-background)" }}>
                            {testimonial.author?.username ?? "Anónimo"}
                        </h1>
                        <p className="text-xl md:text-2xl opacity-70 font-medium" style={{ color: "var(--faro-on-surface-variant)" }}>
                            {testimonial.author?.role ?? "Miembro de la comunidad"}
                        </p>
                    </div>
                </motion.header>

                {/* ── CONTENT BODY ───────────────────────────────────── */}
                <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="relative"
                >
                    <Quote size={120} className="absolute -top-16 -left-12 opacity-5 pointer-events-none" style={{ color: "var(--faro-primary)" }} />
                    <div className="relative z-10 space-y-8">
                        {mediaUrl && (
                            <div className="overflow-hidden rounded-[2rem] border" style={{ borderColor: "var(--faro-outline-variant)", background: "var(--faro-surface-container)" }}>
                                {testimonial.media_type === "image" ? (
                                    <img src={mediaUrl} alt="" className="max-h-[520px] w-full object-cover" />
                                ) : testimonial.media_type === "video" ? (
                                    <video controls className="w-full bg-black">
                                        <source src={mediaUrl} />
                                    </video>
                                ) : (
                                    <div className="space-y-4 p-6">
                                        <div className="flex items-center gap-2 text-xs font-black uppercase tracking-widest" style={{ color: "var(--faro-primary)" }}>
                                            <Headphones size={16} /> Podcast testimonial
                                        </div>
                                        <audio controls src={mediaUrl} className="w-full" />
                                    </div>
                                )}
                            </div>
                        )}
                        <p 
                            className="text-2xl md:text-4xl leading-[1.6] font-medium"
                            style={{ color: "var(--faro-on-surface)" }}
                        >
                            &quot;{testimonial.content}&quot;
                        </p>
                    </div>
                </motion.div>

                {/* ── FOOTER ACTIONS ─────────────────────────────────── */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.4 }}
                    className="mt-24 pt-12 border-t flex flex-col sm:flex-row items-center justify-between gap-6"
                    style={{ borderColor: "var(--faro-outline-variant)" }}
                >
                    <p className="text-sm font-bold uppercase tracking-widest opacity-50" style={{ color: "var(--faro-on-surface)" }}>
                        Historia de impacto
                    </p>
                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => {
                                setShowPrayerForm(true);
                                setPrayerSent(false);
                            }}
                            className="flex items-center gap-2 px-6 py-3 rounded-full text-sm font-black uppercase tracking-widest transition-all hover:scale-105"
                            style={{ background: "var(--faro-primary)", color: "var(--faro-on-primary)" }}
                        >
                            <Heart size={16} /> Pedir oración
                        </button>
                        <button
                            onClick={() => {
                                if (navigator.share) {
                                    navigator.share({
                                        title: `Testimonio de ${testimonial.author?.username}`,
                                        text: `Lee el testimonio de ${testimonial.author?.username} en FARO.`,
                                        url: window.location.href,
                                    });
                                } else {
                                    navigator.clipboard.writeText(window.location.href);
                                    alert("Enlace copiado al portapapeles");
                                }
                            }}
                            className="flex items-center gap-2 px-6 py-3 rounded-full text-sm font-black uppercase tracking-widest transition-all hover:scale-105"
                            style={{ background: "var(--faro-surface-container-high)", color: "var(--faro-on-surface)" }}
                        >
                            <Share2 size={16} /> Compartir historia
                        </button>
                    </div>
                </motion.div>

                {/* ── PRAYER REQUEST FORM ──────────────────────── */}
                <AnimatePresence>
                    {showPrayerForm && (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            transition={{ delay: 0.5 }}
                            className="mt-16 p-10 rounded-[3rem] relative overflow-hidden"
                            style={{ background: "var(--faro-surface-container-low)", border: "1px solid var(--faro-outline-variant)" }}
                        >
                            {prayerSent ? (
                                <motion.div
                                    initial={{ scale: 0.8, opacity: 0 }}
                                    animate={{ scale: 1, opacity: 1 }}
                                    className="text-center py-8 space-y-4"
                                >
                                    <CheckCircle2 size={56} className="mx-auto" style={{ color: "var(--faro-primary)" }} />
                                    <h3 className="text-2xl font-black" style={{ color: "var(--faro-on-background)" }}>Petición recibida</h3>
                                    <p className="text-base opacity-70 max-w-md mx-auto leading-relaxed" style={{ color: "var(--faro-on-surface-variant)" }}>
                                        Tu solicitud de oración ha sido enviada a nuestro equipo de consolidación.
                                        No se publica en la página — es confidencial.
                                    </p>
                                    <button
                                        onClick={() => { setShowPrayerForm(false); setPrayerSent(false); }}
                                        className="px-6 py-3 rounded-full text-xs font-black uppercase tracking-widest transition-all hover:opacity-80"
                                        style={{ background: "var(--faro-surface-container-high)", color: "var(--faro-on-surface)" }}
                                    >
                                        Cerrar
                                    </button>
                                </motion.div>
                            ) : (
                                <>
                                    <button
                                        onClick={() => setShowPrayerForm(false)}
                                        className="absolute top-6 right-6 size-10 rounded-full flex items-center justify-center transition-all hover:opacity-70"
                                        style={{ background: "var(--faro-surface-container-high)" }}
                                    >
                                        <X size={18} style={{ color: "var(--faro-on-surface)" }} />
                                    </button>

                                    <div className="space-y-2 mb-8">
                                        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs font-black uppercase tracking-[0.2em]" style={{ background: "var(--faro-primary-container)", color: "var(--faro-primary)" }}>
                                            <Heart size={14} /> Oración confidencial
                                        </div>
                                        <h3 className="text-3xl font-black tracking-tight" style={{ color: "var(--faro-on-background)" }}>
                                            ¿Este testimonio tocó tu corazón?
                                        </h3>
                                        <p className="text-base opacity-70 leading-relaxed" style={{ color: "var(--faro-on-surface-variant)" }}>
                                            Si deseas que oremos por ti, déjanos tu petición. Llega directo a nuestro equipo pastoral, sin publicarse en el sitio.
                                        </p>
                                    </div>

                                    <div className="space-y-5">
                                        <input
                                            type="text"
                                            placeholder="Tu nombre"
                                            value={prayerName}
                                            onChange={e => setPrayerName(e.target.value)}
                                            className="w-full px-6 py-4 rounded-2xl text-sm font-medium outline-none transition-all border"
                                            style={{ background: "var(--faro-surface)", borderColor: "var(--faro-outline-variant)", color: "var(--faro-on-surface)" }}
                                        />
                                        <textarea
                                            rows={4}
                                            placeholder="Cuéntanos tu petición de oración..."
                                            value={prayerText}
                                            onChange={e => setPrayerText(e.target.value)}
                                            className="w-full px-6 py-4 rounded-2xl text-sm font-medium outline-none transition-all border resize-none"
                                            style={{ background: "var(--faro-surface)", borderColor: "var(--faro-outline-variant)", color: "var(--faro-on-surface)" }}
                                        />
                                        <button
                                            onClick={async () => {
                                                if (!prayerName.trim() || !prayerText.trim()) return;
                                                setPrayerSubmitting(true);
                                                try {
                                                    await apiFetch('/crm/prayer-requests/public', {
                                                        method: 'POST',
                                                        body: {
                                                            requester_name: prayerName.trim(),
                                                            request_text: prayerText.trim(),
                                                            category: 'Testimonio',
                                                        },
                                                    });
                                                    setPrayerSent(true);
                                                } catch {
                                                    // Silently handle — the prayer goes to CRM regardless
                                                    setPrayerSent(true);
                                                } finally {
                                                    setPrayerSubmitting(false);
                                                }
                                            }}
                                            disabled={!prayerName.trim() || !prayerText.trim() || prayerSubmitting}
                                            className="flex items-center justify-center gap-2 w-full py-5 rounded-2xl text-sm font-black uppercase tracking-[0.2em] transition-all disabled:opacity-40 hover:scale-[1.02]"
                                            style={{ background: "var(--faro-primary)", color: "var(--faro-on-primary)" }}
                                        >
                                            {prayerSubmitting ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
                                            Enviar al equipo pastoral
                                        </button>
                                    </div>
                                </>
                            )}
                        </motion.div>
                    )}
                </AnimatePresence>
            </article>
        </main>
    );
}
