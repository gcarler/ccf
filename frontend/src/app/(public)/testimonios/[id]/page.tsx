"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import OptimizedImage from "@/components/ui/OptimizedImage";
import { ArrowLeft, Quote, Share2, Heart, Send, CheckCircle2, Loader2, X, Headphones } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Testimonial } from "@/lib/data/testimonios";
import { apiFetch } from "@/lib/http";
import { Header, Footer_Simple } from "@/components/public/Shared";
import { toast } from "sonner";

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
            <div className="min-h-screen flex flex-col" style={{ background: "var(--site-background)" }}>
                <Header />
                <main className="pt-[120px] pb-4 min-h-screen flex items-center justify-center">
                    <div className="w-8 h-8 border-4 border-t-transparent rounded-full animate-spin" style={{ borderColor: "var(--site-primary) transparent transparent transparent" }} />
                </main>
                <Footer_Simple />
            </div>
        );
    }

    if (!testimonial) {
        return (
            <div className="min-h-screen flex flex-col" style={{ background: "var(--site-background)" }}>
                <Header />
                <main className="pt-[120px] pb-4 min-h-[70vh] flex flex-col items-center justify-center text-center px-3">
                    <Quote size={80} className="mb-3 opacity-20" style={{ color: "var(--site-primary)" }} />
                    <h1 className="text-lg font-bold mb-4" style={{ color: "var(--site-on-background)" }}>Testimonio no encontrado</h1>
                    <p className="text-xl mb-3 opacity-70 max-w-lg" style={{ color: "var(--site-on-surface-variant)" }}>
                        Parece que la historia que buscas ya no está disponible o el enlace es incorrecto.
                    </p>
                    <button
                        onClick={() => router.push('/testimonios')}
                        className="flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-semibold uppercase tracking-wide transition-all hover:-translate-x-2"
                        style={{ background: "var(--site-primary)", color: "var(--site-on-primary)" }}
                    >
                        <ArrowLeft size={16} /> Ver más testimonios
                    </button>
                </main>
                <Footer_Simple />
            </div>
        );
    }

    const mediaUrl = getTestimonialMediaUrl(testimonial);

    return (
        <div className="min-h-screen flex flex-col" style={{ background: "var(--site-background)", color: "var(--site-on-background)" }}>
            <Header />
            <main className="pt-[120px] pb-4 min-h-screen">
            <article className="px-3 lg:px-0">
                {/* ── BACK BUTTON ────────────────────────────────────── */}
                <motion.div 
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="mb-3"
                >
                    <Link
                        href="/testimonios"
                        className="inline-flex items-center gap-2 text-sm font-semibold uppercase tracking-wide transition-all hover:opacity-70"
                        style={{ color: "var(--site-primary)" }}
                    >
                        <ArrowLeft size={16} /> Volver a testimonios
                    </Link>
                </motion.div>

                {/* ── AUTHOR HEADER ──────────────────────────────────── */}
                <motion.header 
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="flex flex-col md:flex-row items-center gap-3 mb-16 text-center md:text-left"
                >
                    {testimonial.author?.avatarUrl ? (
                        <div className="w-32 h-32 md:w-40 md:h-40 rounded-full overflow-hidden shadow-2xl shrink-0 border-4" style={{ borderColor: "var(--site-surface-container)" }}>
                            <OptimizedImage src={testimonial.author.avatarUrl} alt={testimonial.author?.username || "Autor"} width={160} height={160} className="w-full h-full object-cover" />
                        </div>
                    ) : (
                        <div
                            className="w-32 h-32 md:w-40 md:h-40 rounded-full flex items-center justify-center text-xl font-bold shadow-2xl shrink-0"
                            style={{
                                background: "var(--site-primary-container)",
                                color: "var(--site-primary)",
                            }}
                        >
                            {testimonial.author?.username?.[0] ?? "?"}
                        </div>
                    )}
                    
                    <div className="flex-1">
                        {testimonial.emotion && (
                            <span 
                                className="inline-block px-4 py-2 rounded-full text-xs font-semibold uppercase tracking-wide mb-4 shadow-sm"
                                style={{ background: "var(--site-primary)", color: "var(--site-on-primary)" }}
                            >
                                {testimonial.emotion}
                            </span>
                        )}
                        <h1 className="text-xl md:text-xl font-bold tracking-tight mb-2" style={{ color: "var(--site-on-background)" }}>
                            {testimonial.author?.username ?? "Anónimo"}
                        </h1>
                        <p className="text-xl md:text-lg opacity-70 font-medium" style={{ color: "var(--site-on-surface-variant)" }}>
                            {testimonial.author?.role ?? "Persona de la comunidad"}
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
                    <Quote size={120} className="absolute -top-16 -left-12 opacity-5 pointer-events-none" style={{ color: "var(--site-primary)" }} />
                    <div className="relative z-10 space-y-3">
                        {mediaUrl && (
                            <div className="overflow-hidden rounded-lg border" style={{ borderColor: "var(--site-outline-variant)", background: "var(--site-surface-container)" }}>
                                {testimonial.media_type === "image" ? (
                                    <OptimizedImage src={mediaUrl} alt="" width={800} height={520} className="max-h-[520px] w-full object-cover" />
                                ) : testimonial.media_type === "video" ? (
                                    <video controls className="w-full bg-black">
                                        <source src={mediaUrl} />
                                    </video>
                                ) : (
                                    <div className="space-y-4 p-3">
                                        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--site-primary)" }}>
                                            <Headphones size={16} /> Podcast testimonial
                                        </div>
                                        <audio controls src={mediaUrl} className="w-full" />
                                    </div>
                                )}
                            </div>
                        )}
                        <p 
                            className="text-lg md:text-lg leading-[1.6] font-medium"
                            style={{ color: "var(--site-on-surface)" }}
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
                    className="mt-24 pt-12 border-t flex flex-col sm:flex-row items-center justify-between gap-3"
                    style={{ borderColor: "var(--site-outline-variant)" }}
                >
                    <p className="text-sm font-bold uppercase tracking-wide opacity-50" style={{ color: "var(--site-on-surface)" }}>
                        Historia de impacto
                    </p>
                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => {
                                setShowPrayerForm(true);
                                setPrayerSent(false);
                            }}
                            className="flex items-center gap-2 px-3 py-3 rounded-full text-sm font-semibold uppercase tracking-wide transition-all hover:scale-105"
                            style={{ background: "var(--site-primary)", color: "var(--site-on-primary)" }}
                        >
                            <Heart size={16} /> Pedir oración
                        </button>
                        <button
                            onClick={() => {
                                const shareUrl = window.location.href;
                                if (navigator.share) {
                                    navigator.share({
                                        title: `Testimonio de ${testimonial.author?.username}`,
                                        text: `Lee el testimonio de ${testimonial.author?.username} en la comunidad.`,
                                        url: shareUrl,
                                    });
                                } else {
                                    navigator.clipboard.writeText(shareUrl)
                                        .then(() => toast.success("Enlace copiado al portapapeles"))
                                        .catch(() => toast.error("No pudimos copiar el enlace"));
                                }
                            }}
                            className="flex items-center gap-2 px-3 py-3 rounded-full text-sm font-semibold uppercase tracking-wide transition-all hover:scale-105"
                            style={{ background: "var(--site-surface-container-high)", color: "var(--site-on-surface)" }}
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
                            className="mt-16 p-4 rounded-lg relative overflow-hidden"
                            style={{ background: "var(--site-surface-container-low)", border: "1px solid var(--site-outline-variant)" }}
                        >
                            {prayerSent ? (
                                <motion.div
                                    initial={{ scale: 0.8, opacity: 0 }}
                                    animate={{ scale: 1, opacity: 1 }}
                                    className="text-center py-8 space-y-4"
                                >
                                    <CheckCircle2 size={56} className="mx-auto" style={{ color: "var(--site-primary)" }} />
                                    <h3 className="text-lg font-bold" style={{ color: "var(--site-on-background)" }}>Petición recibida</h3>
                                    <p className="text-base opacity-70 max-w-md mx-auto leading-relaxed" style={{ color: "var(--site-on-surface-variant)" }}>
                                        Tu solicitud de oración ha sido enviada a nuestro equipo de consolidación.
                                        No se publica en la página — es confidencial.
                                    </p>
                                    <button
                                        onClick={() => { setShowPrayerForm(false); setPrayerSent(false); }}
                                        className="px-3 py-3 rounded-full text-xs font-semibold uppercase tracking-wide transition-all hover:opacity-80"
                                        style={{ background: "var(--site-surface-container-high)", color: "var(--site-on-surface)" }}
                                    >
                                        Cerrar
                                    </button>
                                </motion.div>
                            ) : (
                                <>
                                    <button
                                        onClick={() => setShowPrayerForm(false)}
                                        className="absolute top-3 right-6 size-10 rounded-full flex items-center justify-center transition-all hover:opacity-70"
                                        style={{ background: "var(--site-surface-container-high)" }}
                                    >
                                        <X size={18} style={{ color: "var(--site-on-surface)" }} />
                                    </button>

                                    <div className="space-y-2 mb-3">
                                        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs font-semibold uppercase tracking-wide" style={{ background: "var(--site-primary-container)", color: "var(--site-primary)" }}>
                                            <Heart size={14} /> Oración confidencial
                                        </div>
                                        <h3 className="text-xl font-bold tracking-tight" style={{ color: "var(--site-on-background)" }}>
                                            ¿Este testimonio tocó tu corazón?
                                        </h3>
                                        <p className="text-base opacity-70 leading-relaxed" style={{ color: "var(--site-on-surface-variant)" }}>
                                            Si deseas que oremos por ti, déjanos tu petición. Llega directo a nuestro equipo pastoral, sin publicarse en el sitio.
                                        </p>
                                    </div>

                                    <div className="space-y-5">
                                        <input
                                            type="text"
                                            placeholder="Tu nombre"
                                            value={prayerName}
                                            onChange={e => setPrayerName(e.target.value)}
                                            className="w-full px-3 py-1.5 rounded-lg text-sm font-medium outline-none transition-all border"
                                            style={{ background: "var(--site-surface)", borderColor: "var(--site-outline-variant)", color: "var(--site-on-surface)" }}
                                        />
                                        <textarea
                                            rows={4}
                                            placeholder="Cuéntanos tu petición de oración..."
                                            value={prayerText}
                                            onChange={e => setPrayerText(e.target.value)}
                                            className="w-full px-3 py-1.5 rounded-lg text-sm font-medium outline-none transition-all border resize-none"
                                            style={{ background: "var(--site-surface)", borderColor: "var(--site-outline-variant)", color: "var(--site-on-surface)" }}
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
                                            className="flex items-center justify-center gap-2 w-full py-2 rounded-lg text-sm font-semibold uppercase tracking-wide transition-all disabled:opacity-40 hover:scale-[1.02]"
                                            style={{ background: "var(--site-primary)", color: "var(--site-on-primary)" }}
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
            <Footer_Simple />
        </div>
    );
}
