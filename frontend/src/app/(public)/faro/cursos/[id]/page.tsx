"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { PREMIUM_COURSES, CourseItem } from "@/lib/data/cursos";
import { ArrowLeft, CheckCircle2, Clock, User, BookOpen, Share2 } from "lucide-react";
import { apiFetch } from "@/lib/http";

export default function CursoDetailPage() {
    const params = useParams();
    const router = useRouter();
    const id = params?.id as string;

    const [course, setCourse] = useState<CourseItem | null>(null);
    const [loading, setLoading] = useState(true);
    const [toastMessage, setToastMessage] = useState<string | null>(null);
    const [enrolled, setEnrolled] = useState(false);

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
        setEnrolled(true);
        showToast(`Inscripción a "${course?.title}" iniciada. Revisa tu correo.`);
    };

    if (loading) {
        return (
            <main className="pt-[120px] pb-32 min-h-screen flex items-center justify-center">
                <div className="w-8 h-8 border-4 border-t-transparent rounded-full animate-spin" style={{ borderColor: "var(--faro-primary) transparent transparent transparent" }} />
            </main>
        );
    }

    if (!course) {
        return (
            <main className="pt-[120px] pb-32 min-h-[70vh] flex flex-col items-center justify-center text-center px-6">
                <BookOpen size={80} className="mb-6 opacity-20" style={{ color: "var(--faro-primary)" }} />
                <h1 className="text-4xl font-black mb-4" style={{ color: "var(--faro-on-background)" }}>Curso no encontrado</h1>
                <p className="text-xl mb-8 opacity-70 max-w-lg" style={{ color: "var(--faro-on-surface-variant)" }}>
                    El curso que buscas ya no está disponible o el enlace es incorrecto.
                </p>
                <button
                    onClick={() => router.push('/faro/cursos')}
                    className="flex items-center gap-2 px-8 py-4 rounded-full text-sm font-black uppercase tracking-widest transition-all hover:-translate-x-2"
                    style={{ background: "var(--faro-primary)", color: "var(--faro-on-primary)" }}
                >
                    <ArrowLeft size={16} /> Ver todos los cursos
                </button>
            </main>
        );
    }

    return (
        <main className="pt-[88px] pb-32 min-h-screen overflow-hidden">
            {/* ── TOAST NOTIFICATION ────────────────────── */}
            <AnimatePresence>
                {toastMessage && (
                    <motion.div
                        initial={{ opacity: 0, y: 50, scale: 0.9 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 20, scale: 0.9 }}
                        className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 px-6 py-4 rounded-full shadow-2xl border"
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
            <header className="relative px-6 md:px-20 py-12 md:py-24">
                <motion.div 
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="max-w-6xl mx-auto mb-8"
                >
                    <Link
                        href="/faro/cursos"
                        className="inline-flex items-center gap-2 text-sm font-black uppercase tracking-widest transition-all hover:opacity-70"
                        style={{ color: "var(--faro-primary)" }}
                    >
                        <ArrowLeft size={16} /> Volver a Academia
                    </Link>
                </motion.div>

                <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
                    <motion.div 
                        initial={{ opacity: 0, y: 30 }}
                        animate={{ opacity: 1, y: 0 }}
                    >
                        <span 
                            className="inline-block px-4 py-2 rounded-full text-xs font-black uppercase tracking-widest mb-6"
                            style={{ background: "var(--faro-primary-container)", color: "var(--faro-primary)" }}
                        >
                            {course.tag || "Academia FARO"}
                        </span>
                        <h1 className="text-5xl md:text-7xl font-black tracking-tight mb-8 leading-[1.05]" style={{ color: "var(--faro-on-surface)" }}>
                            {course.title}
                        </h1>
                        <p className="text-xl md:text-2xl leading-relaxed mb-10 opacity-80" style={{ color: "var(--faro-on-surface-variant)" }}>
                            {course.excerpt || course.desc}
                        </p>
                        
                        <div className="flex flex-wrap items-center gap-6 mb-12">
                            {course.lessons && (
                                <span className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest" style={{ color: "var(--faro-on-surface)" }}>
                                    <Clock size={16} style={{ color: "var(--faro-primary)" }} />
                                    {course.lessons} Semanas
                                </span>
                            )}
                            <span className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest" style={{ color: "var(--faro-on-surface)" }}>
                                <User size={16} style={{ color: "var(--faro-primary)" }} />
                                {course.modality || "Online"}
                            </span>
                        </div>

                        <div className="flex items-center gap-4">
                            <button
                                onClick={handleEnroll}
                                disabled={enrolled}
                                className={`px-10 py-4 rounded-2xl font-black text-sm transition-all uppercase tracking-widest ${enrolled ? 'opacity-50 cursor-not-allowed' : 'hover:scale-105 shadow-xl'}`}
                                style={{
                                    background: enrolled ? "var(--faro-surface-container-highest)" : "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary))",
                                    color: enrolled ? "var(--faro-on-surface)" : "var(--faro-on-primary)"
                                }}
                            >
                                {enrolled ? "Inscrito" : course.cta || "Inscribirme al Curso"}
                            </button>
                            <button
                                onClick={() => navigator.clipboard.writeText(window.location.href).then(() => showToast("Enlace copiado"))}
                                className="w-14 h-14 rounded-2xl flex items-center justify-center transition-all hover:bg-black/5"
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
                        className="relative aspect-video lg:aspect-square rounded-[3rem] overflow-hidden shadow-2xl border"
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
            <section className="px-6 md:px-20 py-24" style={{ background: "var(--faro-surface-container-lowest)" }}>
                <div className="max-w-4xl mx-auto">
                    <h2 className="text-4xl font-black mb-12" style={{ color: "var(--faro-on-surface)" }}>Acerca de este programa</h2>
                    <p className="text-xl leading-relaxed mb-16" style={{ color: "var(--faro-on-surface-variant)" }}>
                        {course.desc}
                    </p>

                    {course.instructor && (
                        <div className="mb-16 p-8 rounded-3xl" style={{ background: "var(--faro-surface-container-low)" }}>
                            <p className="text-xs font-black uppercase tracking-[0.2em] mb-2" style={{ color: "var(--faro-primary)" }}>Instructor Principal</p>
                            <p className="text-2xl font-bold" style={{ color: "var(--faro-on-surface)" }}>{course.instructor}</p>
                        </div>
                    )}

                    {course.syllabus && course.syllabus.length > 0 && (
                        <div>
                            <h3 className="text-2xl font-black mb-8" style={{ color: "var(--faro-on-surface)" }}>Temario del Curso</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {course.syllabus.map((item, idx) => (
                                    <div 
                                        key={idx}
                                        className="flex items-center gap-4 p-6 rounded-2xl transition-all hover:translate-x-2"
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
        </main>
    );
}
