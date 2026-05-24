"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { PREMIUM_COURSES, CourseItem } from "@/lib/data/cursos";
import { ArrowLeft, CheckCircle2, Clock, User, BookOpen, Share2 } from "lucide-react";
import { apiFetch } from "@/lib/http";
import { toast } from "sonner";

export default function CursoDetailPage() {
    const params = useParams();
    const router = useRouter();
    const id = params?.id as string;

    const [course, setCourse] = useState<CourseItem | null>(null);
    const [loading, setLoading] = useState(true);
    const [toastMessage, setToastMessage] = useState<string | null>(null);
    const [enrolled, setEnrolled] = useState(false);
    const [showEnrollModal, setShowEnrollModal] = useState(false);
    const [enrollForm, setEnrollForm] = useState({ fullName: "", email: "", phone: "" });
    const [enrollSubmitting, setEnrollSubmitting] = useState(false);

    useEffect(() => {
        // First try the API
        apiFetch<CourseItem>(`/public/courses/${id}`, { silent: true })
            .then(data => {
                setCourse(data);
                setLoading(false);
            })
            .catch(() => {
                // Try finding locally as fallback
                const localCourse = PREMIUM_COURSES.find(c => c.id === id);
                if (localCourse) {
                    setCourse(localCourse);
                }
                setLoading(false);
            });
    }, [id]);

    const showToast = (message: string) => {
        setToastMessage(message);
        setTimeout(() => setToastMessage(null), 3000);
    };

    const handleEnroll = () => {
        if (enrolled) return;
        setShowEnrollModal(true);
    };

    const submitEnroll = async (e: React.FormEvent) => {
        e.preventDefault();
        setEnrollSubmitting(true);
        try {
            await apiFetch(`/public/courses/${params.id}/enroll`, {
                method: "POST",
                body: {
                    full_name: enrollForm.fullName,
                    email: enrollForm.email,
                    phone: enrollForm.phone,
                    landing_page: `/cursos/${params.id}`,
                },
            });
            setEnrolled(true);
            setShowEnrollModal(false);
            setEnrollForm({ fullName: "", email: "", phone: "" });
            toast.success(`Inscrito en "${course?.title}". Revisa tu correo.`);
        } catch {
            toast.error("No se pudo completar la inscripción. Intenta de nuevo.");
        } finally {
            setEnrollSubmitting(false);
        }
    };

    if (loading) {
        return (
            <main className="pt-[120px] pb-4 min-h-screen flex items-center justify-center">
                <div className="w-8 h-8 border-4 border-t-transparent rounded-full animate-spin" style={{ borderColor: "var(--faro-primary) transparent transparent transparent" }} />
            </main>
        );
    }

    if (!course) {
        return (
            <main className="pt-[120px] pb-4 min-h-[70vh] flex flex-col items-center justify-center text-center px-3">
                <BookOpen size={80} className="mb-3 opacity-20" style={{ color: "var(--faro-primary)" }} />
                <h1 className="text-lg font-bold mb-4" style={{ color: "var(--faro-on-background)" }}>Curso no encontrado</h1>
                <p className="text-xl mb-3 opacity-70 max-w-lg" style={{ color: "var(--faro-on-surface-variant)" }}>
                    El curso que buscas ya no está disponible o el enlace es incorrecto.
                </p>
                <button
                    onClick={() => router.push('/cursos')}
                    className="flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-semibold uppercase tracking-wide transition-all hover:-translate-x-2"
                    style={{ background: "var(--faro-primary)", color: "var(--faro-on-primary)" }}
                >
                    <ArrowLeft size={16} /> Ver todos los cursos
                </button>
            </main>
        );
    }

    return (
        <main className="pt-[88px] pb-4 min-h-screen overflow-hidden">
            {/* ── TOAST NOTIFICATION ────────────────────── */}
            <AnimatePresence>
                {toastMessage && (
                    <motion.div
                        initial={{ opacity: 0, y: 50, scale: 0.9 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 20, scale: 0.9 }}
                        className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 px-3 py-1.5 rounded-full shadow-2xl border"
                        style={{
                            background: "var(--faro-surface)",
                            borderColor: "var(--faro-outline-variant)",
                            color: "var(--faro-on-surface)"
                        }}
                    >
                        <CheckCircle2 size={20} style={{ color: "var(--faro-primary)" }} />
                        <span className="font-bold text-sm tracking-wide">{toastMessage}</span>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* ── HEADER ──────────────────────────────────── */}
            <header className="relative px-3 md:px-6 lg:px-8 xl:px-12 py-6 md:py-10 lg:py-14">
                <motion.div
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="mb-3"
                >
                    <Link
                        href="/cursos"
                        className="inline-flex items-center gap-2 text-sm font-semibold uppercase tracking-wide transition-all hover:opacity-70"
                        style={{ color: "var(--faro-primary)" }}
                    >
                        <ArrowLeft size={16} /> Volver a Academia
                    </Link>
                </motion.div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 items-center">
                    <motion.div 
                        initial={{ opacity: 0, y: 30 }}
                        animate={{ opacity: 1, y: 0 }}
                    >
                        <span 
                            className="inline-block px-4 py-2 rounded-full text-xs font-semibold uppercase tracking-wide mb-3"
                            style={{ background: "var(--faro-primary-container)", color: "var(--faro-primary)" }}
                        >
                            {course.tag || "Academia FARO"}
                        </span>
                        <h1 className="text-xl md:text-xl font-bold tracking-tight mb-3 leading-[1.05]" style={{ color: "var(--faro-on-surface)" }}>
                            {course.title}
                        </h1>
                        <p className="text-xl md:text-lg leading-relaxed mb-3 opacity-80" style={{ color: "var(--faro-on-surface-variant)" }}>
                            {course.excerpt || course.desc}
                        </p>
                        
                        <div className="flex flex-wrap items-center gap-3 mb-3">
                            {course.lessons && (
                                <span className="flex items-center gap-2 text-sm font-bold uppercase tracking-wide" style={{ color: "var(--faro-on-surface)" }}>
                                    <Clock size={16} style={{ color: "var(--faro-primary)" }} />
                                    {course.lessons} Semanas
                                </span>
                            )}
                            <span className="flex items-center gap-2 text-sm font-bold uppercase tracking-wide" style={{ color: "var(--faro-on-surface)" }}>
                                <User size={16} style={{ color: "var(--faro-primary)" }} />
                                {course.modality || "Online"}
                            </span>
                        </div>

                        <div className="flex items-center gap-4">
                            <button
                                onClick={handleEnroll}
                                disabled={enrolled}
                                className={`px-4 py-1.5 rounded-lg font-black text-sm transition-all uppercase tracking-wide ${enrolled ? 'opacity-50 cursor-not-allowed' : 'hover:scale-105 shadow-xl'}`}
                                style={{
                                    background: enrolled ? "var(--faro-surface-container-highest)" : "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary))",
                                    color: enrolled ? "var(--faro-on-surface)" : "var(--faro-on-primary)"
                                }}
                            >
                                {enrolled ? "Inscrito" : course.cta || "Inscribirme al Curso"}
                            </button>
                            <button
                                onClick={() => navigator.clipboard.writeText(window.location.href).then(() => showToast("Enlace copiado"))}
                                className="w-14 h-8 rounded-lg flex items-center justify-center transition-all hover:bg-black/5"
                                style={{ color: "var(--faro-on-surface)", border: "2px solid var(--faro-outline-variant)" }}
                            >
                                <Share2 size={20} />
                            </button>
                        </div>
                    </motion.div>

                    <motion.div 
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: 0.2 }}
                        className="relative aspect-video lg:aspect-square rounded-lg overflow-hidden shadow-2xl border"
                        style={{ borderColor: "var(--faro-outline-variant)" }}
                    >
                        <Image
                            src={course.imageUrl || "https://picsum.photos/seed/default-course/800/800"}
                            alt={course.title}
                            fill
                            className="object-cover"
                            priority
                        />
                    </motion.div>
                </div>
            </header>

            {/* ── SYLLABUS & DETAILS ──────────────────────────────── */}
            <section className="px-3 md:px-6 lg:px-8 xl:px-12 py-8 md:py-12 lg:py-16" style={{ background: "var(--faro-surface-container-lowest)" }}>
                <div>
                    <h2 className="text-lg font-bold mb-3" style={{ color: "var(--faro-on-surface)" }}>Acerca de este programa</h2>
                    <p className="text-xl leading-relaxed mb-16" style={{ color: "var(--faro-on-surface-variant)" }}>
                        {course.desc}
                    </p>

                    {course.instructor && (
                        <div className="mb-16 p-4 rounded-lg" style={{ background: "var(--faro-surface-container-low)" }}>
                            <p className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: "var(--faro-primary)" }}>Instructor Principal</p>
                            <p className="text-lg font-bold" style={{ color: "var(--faro-on-surface)" }}>{course.instructor}</p>
                        </div>
                    )}

                    {course.syllabus && course.syllabus.length > 0 && (
                        <div>
                            <h3 className="text-lg font-bold mb-3" style={{ color: "var(--faro-on-surface)" }}>Temario del Curso</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {course.syllabus.map((item, idx) => (
                                    <div 
                                        key={idx}
                                        className="flex items-center gap-4 p-3 rounded-lg transition-all hover:translate-x-2"
                                        style={{ background: "var(--faro-surface)", border: "1px solid var(--faro-outline-variant)" }}
                                    >
                                        <div className="w-10 h-10 rounded-full flex items-center justify-center font-black" style={{ background: "var(--faro-primary-container)", color: "var(--faro-primary)" }}>
                                            {idx + 1}
                                        </div>
                                        <p className="font-bold text-lg" style={{ color: "var(--faro-on-surface)" }}>{item}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </section>

            {/* ── ENROLLMENT MODAL ────────────────────── */}
            {showEnrollModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "var(--faro-overlay-bg)", backdropFilter: "blur(8px)" }}>
                    <div
                        className="w-full max-w-md rounded-lg p-4 shadow-2xl border"
                        style={{
                            background: "var(--faro-surface-container-lowest)",
                            borderColor: "var(--faro-outline-variant)",
                        }}
                    >
                        <h3 className="text-lg font-bold mb-1" style={{ color: "var(--faro-on-surface)" }}>
                            Inscribirme en {course?.title}
                        </h3>
                        <p className="text-sm mb-3" style={{ color: "var(--faro-on-surface-variant)" }}>
                            Déjanos tus datos para crear tu acceso al curso.
                        </p>
                        <form onSubmit={submitEnroll} className="space-y-3">
                            <div>
                                <label className="text-[10px] font-semibold uppercase tracking-wide block mb-1" style={{ color: "var(--faro-on-surface-variant)" }}>
                                    Nombre completo
                                </label>
                                <input
                                    type="text"
                                    value={enrollForm.fullName}
                                    onChange={(e) => setEnrollForm(f => ({ ...f, fullName: e.target.value }))}
                                    required
                                    className="w-full rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2"
                                    style={{ background: "var(--faro-surface)", border: "2px solid var(--faro-outline-variant)", color: "var(--faro-on-surface)" }}
                                />
                            </div>
                            <div>
                                <label className="text-[10px] font-semibold uppercase tracking-wide block mb-1" style={{ color: "var(--faro-on-surface-variant)" }}>
                                    Email
                                </label>
                                <input
                                    type="email"
                                    value={enrollForm.email}
                                    onChange={(e) => setEnrollForm(f => ({ ...f, email: e.target.value }))}
                                    required
                                    className="w-full rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2"
                                    style={{ background: "var(--faro-surface)", border: "2px solid var(--faro-outline-variant)", color: "var(--faro-on-surface)" }}
                                />
                            </div>
                            <div>
                                <label className="text-[10px] font-semibold uppercase tracking-wide block mb-1" style={{ color: "var(--faro-on-surface-variant)" }}>
                                    WhatsApp (opcional)
                                </label>
                                <input
                                    type="tel"
                                    value={enrollForm.phone}
                                    onChange={(e) => setEnrollForm(f => ({ ...f, phone: e.target.value }))}
                                    className="w-full rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2"
                                    style={{ background: "var(--faro-surface)", border: "2px solid var(--faro-outline-variant)", color: "var(--faro-on-surface)" }}
                                />
                            </div>
                            <div className="flex gap-2 pt-2">
                                <button
                                    type="button"
                                    onClick={() => setShowEnrollModal(false)}
                                    className="flex-1 py-2 rounded-lg text-sm font-bold transition-all"
                                    style={{ background: "var(--faro-surface-container)", color: "var(--faro-on-surface-variant)" }}
                                >
                                    Cancelar
                                </button>
                                <button
                                    type="submit"
                                    disabled={enrollSubmitting}
                                    className="flex-1 py-2 rounded-lg text-sm font-bold text-white transition-all disabled:opacity-60"
                                    style={{ background: "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary))" }}
                                >
                                    {enrollSubmitting ? "Inscribiendo..." : "Inscribirme"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </main>
    );
}
