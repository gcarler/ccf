"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { CourseItem } from "@/lib/data/cursos";
import { ArrowLeft, CheckCircle2, Clock, User, BookOpen, Share2 } from "lucide-react";
import { apiFetch } from "@/lib/http";
import { toast } from "sonner";
import { Header, Footer_Simple } from "@/components/public/Shared";
import { useCmsV2Page } from "@/hooks/useCmsV2Page";

function getString(props: Record<string, unknown> | undefined, key: string): string {
    const value = props?.[key];
    return typeof value === "string" ? value : "";
}

function applyTemplate(template: string, vars: Record<string, string>): string {
    return template.replace(/\{(\w+)\}/g, (_, name) => vars[name] ?? "");
}

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

    const cmsPage = useCmsV2Page("courses");
    const cms = cmsPage?.blocks?.detail_template as Record<string, unknown> | undefined;

    useEffect(() => {
        // First try the API
        apiFetch<CourseItem>(`/public/courses/${id}`, { silent: true })
            .then(data => {
                setCourse(data);
                setLoading(false);
            })
            .catch(() => {
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
            await apiFetch(`/public/courses/${id}/enroll`, {
                method: "POST",
                body: {
                    full_name: enrollForm.fullName,
                    email: enrollForm.email,
                    phone: enrollForm.phone,
                    landing_page: `/cursos/${id}`,
                },
            });
            setEnrolled(true);
            setShowEnrollModal(false);
            setEnrollForm({ fullName: "", email: "", phone: "" });
            const successToast = getString(cms, "enroll_success_toast");
            if (successToast) {
                toast.success(applyTemplate(successToast, { title: course?.title ?? "" }));
            }
        } catch {
            const errorToast = getString(cms, "enroll_error_toast");
            if (errorToast) toast.error(errorToast);
        } finally {
            setEnrollSubmitting(false);
        }
    };

    if (loading) {
        return (
            <main className="pt-[120px] pb-4 min-h-screen flex items-center justify-center">
                <div className="w-8 h-8 border-4 border-t-transparent rounded-full animate-spin" style={{ borderColor: "var(--site-primary) transparent transparent transparent" }} />
            </main>
        );
    }

    if (!course) {
        return (
            <main className="pt-[120px] pb-4 min-h-[70vh] flex flex-col items-center justify-center text-center px-3">
                <BookOpen size={80} className="mb-3 opacity-20" style={{ color: "var(--site-primary)" }} />
                <h1 className="text-lg font-bold mb-4" style={{ color: "var(--site-on-background)" }}>Curso no encontrado</h1>
                <p className="text-xl mb-3 opacity-70 max-w-lg" style={{ color: "var(--site-on-surface-variant)" }}>
                    El curso que buscas ya no está disponible o el enlace es incorrecto.
                </p>
                <button
                    onClick={() => router.push('/cursos')}
                    className="flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-semibold uppercase tracking-wide transition-all hover:-translate-x-2"
                    style={{ background: "var(--site-primary)", color: "var(--site-on-primary)" }}
                >
                    <ArrowLeft size={16} /> Ver todos los cursos
                </button>
            </main>
        );
    }

    return (
        <div className="min-h-screen flex flex-col" style={{ background: "var(--site-background)", color: "var(--site-on-background)" }}>
            <Header />

            {/* ── TOAST NOTIFICATION ────────────────────── */}
            <AnimatePresence>
                {toastMessage && (
                    <motion.div
                        initial={{ opacity: 0, y: 50, scale: 0.9 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 20, scale: 0.9 }}
                        className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 px-3 py-1.5 rounded-full shadow-2xl border"
                        style={{
                            background: "var(--site-surface)",
                            borderColor: "var(--site-outline-variant)",
                            color: "var(--site-on-surface)"
                        }}
                    >
                        <CheckCircle2 size={20} style={{ color: "var(--site-primary)" }} />
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
                        style={{ color: "var(--site-primary)" }}
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
                            style={{ background: "var(--site-primary-container)", color: "var(--site-primary)" }}
                        >
                            {course.tag || "Academia"}
                        </span>
                        <h1 className="text-xl md:text-xl font-bold tracking-tight mb-3 leading-[1.05]" style={{ color: "var(--site-on-surface)" }}>
                            {course.title}
                        </h1>
                        <p className="text-xl md:text-lg leading-relaxed mb-3 opacity-80" style={{ color: "var(--site-on-surface-variant)" }}>
                            {course.excerpt || course.desc}
                        </p>
                        
                        <div className="flex flex-wrap items-center gap-3 mb-3">
                            {course.lessons && (
                                <span className="flex items-center gap-2 text-sm font-bold uppercase tracking-wide" style={{ color: "var(--site-on-surface)" }}>
                                    <Clock size={16} style={{ color: "var(--site-primary)" }} />
                                    {course.lessons} Semanas
                                </span>
                            )}
                            <span className="flex items-center gap-2 text-sm font-bold uppercase tracking-wide" style={{ color: "var(--site-on-surface)" }}>
                                <User size={16} style={{ color: "var(--site-primary)" }} />
                                {course.modality || "Online"}
                            </span>
                        </div>

                        <div className="flex items-center gap-4">
                            <button
                                onClick={handleEnroll}
                                disabled={enrolled}
                                className={`px-4 py-1.5 rounded-lg font-black text-sm transition-all uppercase tracking-wide ${enrolled ? 'opacity-50 cursor-not-allowed' : 'hover:scale-105 shadow-xl'}`}
                                style={{
                                    background: enrolled ? "var(--site-surface-container-highest)" : "linear-gradient(135deg, var(--site-primary), var(--site-secondary))",
                                    color: enrolled ? "var(--site-on-surface)" : "var(--site-on-primary)"
                                }}
                            >
                                {enrolled ? getString(cms, "enrolled_label") : course.cta || getString(cms, "enroll_button_default")}
                            </button>
                            <button
                                onClick={() => navigator.clipboard.writeText(window.location.href).then(() => {
                                    const msg = getString(cms, "share_toast_success");
                                    if (msg) showToast(msg);
                                })}
                                className="w-14 h-8 rounded-lg flex items-center justify-center transition-all hover:bg-black/5"
                                style={{ color: "var(--site-on-surface)", border: "2px solid var(--site-outline-variant)" }}
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
                        style={{ borderColor: "var(--site-outline-variant)" }}
                    >
                        {course.imageUrl ? (
                            <Image
                                src={course.imageUrl}
                                alt={course.title}
                                fill
                                className="object-cover"
                                priority
                            />
                        ) : (
                            <div className="absolute inset-0 bg-gradient-to-br from-[hsl(var(--primary))/0.18] to-[hsl(var(--surface-2))/0.35]" />
                        )}
                    </motion.div>
                </div>
            </header>

            {/* ── SYLLABUS & DETAILS ──────────────────────────────── */}
            <section className="px-3 md:px-6 lg:px-8 xl:px-12 py-8 md:py-12 lg:py-16" style={{ background: "var(--site-surface-container-lowest)" }}>
                <div>
                    {getString(cms, "about_title") && (
                        <h2 className="text-lg font-bold mb-3" style={{ color: "var(--site-on-surface)" }}>{getString(cms, "about_title")}</h2>
                    )}
                    <p className="text-xl leading-relaxed mb-16" style={{ color: "var(--site-on-surface-variant)" }}>
                        {course.desc}
                    </p>

                    {course.instructor && getString(cms, "instructor_label") && (
                        <div className="mb-16 p-4 rounded-lg" style={{ background: "var(--site-surface-container-low)" }}>
                            <p className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: "var(--site-primary)" }}>{getString(cms, "instructor_label")}</p>
                            <p className="text-lg font-bold" style={{ color: "var(--site-on-surface)" }}>{course.instructor}</p>
                        </div>
                    )}

                    {course.syllabus && course.syllabus.length > 0 && getString(cms, "syllabus_title") && (
                        <div>
                            <h3 className="text-lg font-bold mb-3" style={{ color: "var(--site-on-surface)" }}>{getString(cms, "syllabus_title")}</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {course.syllabus.map((item, idx) => (
                                    <div 
                                        key={idx}
                                        className="flex items-center gap-4 p-3 rounded-lg transition-all hover:translate-x-2"
                                        style={{ background: "var(--site-surface)", border: "1px solid var(--site-outline-variant)" }}
                                    >
                                        <div className="w-10 h-10 rounded-full flex items-center justify-center font-black" style={{ background: "var(--site-primary-container)", color: "var(--site-primary)" }}>
                                            {idx + 1}
                                        </div>
                                        <p className="font-bold text-lg" style={{ color: "var(--site-on-surface)" }}>{item}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </section>

            {/* ── ENROLLMENT DRAWER ────────────────────── */}
            <AnimatePresence>
                {showEnrollModal && (
                    <>
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="fixed inset-0 z-50 backdrop-blur-sm"
                            style={{ backgroundColor: "hsl(var(--site-background) / 0.70)" }}
                            onClick={() => setShowEnrollModal(false)}
                        />
                        <motion.aside
                            initial={{ x: "100%", opacity: 0 }}
                            animate={{ x: 0, opacity: 1 }}
                            exit={{ x: "100%", opacity: 0 }}
                            transition={{ type: "spring", damping: 26, stiffness: 260 }}
                            className="fixed top-0 right-0 z-[60] h-screen w-full max-w-md overflow-hidden border-l shadow-2xl"
                            style={{
                                background: "var(--site-surface-container-lowest)",
                                borderColor: "var(--site-outline-variant)",
                            }}
                        >
                            <div className="flex h-full flex-col">
                                <div className="flex items-start justify-between gap-4 border-b px-5 py-5" style={{ borderColor: "var(--site-outline-variant)" }}>
                                    <div className="min-w-0">
                                        {getString(cms, "enroll_drawer_title") && (
                                            <h3 className="text-lg font-bold leading-tight" style={{ color: "var(--site-on-surface)" }}>
                                                {applyTemplate(getString(cms, "enroll_drawer_title"), { title: course?.title ?? "" })}
                                            </h3>
                                        )}
                                        {getString(cms, "enroll_drawer_description") && (
                                            <p className="mt-1 text-sm" style={{ color: "var(--site-on-surface-variant)" }}>
                                                {getString(cms, "enroll_drawer_description")}
                                            </p>
                                        )}
                                    </div>
                                    <button
                                        type="button"
                                        onClick={() => setShowEnrollModal(false)}
                                        className="size-10 rounded-lg border text-sm transition-all"
                                        style={{
                                            background: "var(--site-surface-container)",
                                            borderColor: "var(--site-outline-variant)",
                                            color: "var(--site-on-surface-variant)",
                                        }}
                                    >
                                        ×
                                    </button>
                                </div>

                                <form id="course-enroll-form" onSubmit={submitEnroll} className="flex-1 space-y-4 overflow-y-auto px-5 py-5">
                                    {getString(cms, "enroll_name_label") && (
                                        <div>
                                            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide" style={{ color: "var(--site-on-surface-variant)" }}>
                                                {getString(cms, "enroll_name_label")}
                                            </label>
                                            <input
                                                type="text"
                                                value={enrollForm.fullName}
                                                onChange={(e) => setEnrollForm(f => ({ ...f, fullName: e.target.value }))}
                                                required
                                                className="w-full rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2"
                                                style={{ background: "var(--site-surface)", border: "2px solid var(--site-outline-variant)", color: "var(--site-on-surface)" }}
                                            />
                                        </div>
                                    )}
                                    {getString(cms, "enroll_email_label") && (
                                        <div>
                                            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide" style={{ color: "var(--site-on-surface-variant)" }}>
                                                {getString(cms, "enroll_email_label")}
                                            </label>
                                            <input
                                                type="email"
                                                value={enrollForm.email}
                                                onChange={(e) => setEnrollForm(f => ({ ...f, email: e.target.value }))}
                                                required
                                                className="w-full rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2"
                                                style={{ background: "var(--site-surface)", border: "2px solid var(--site-outline-variant)", color: "var(--site-on-surface)" }}
                                            />
                                        </div>
                                    )}
                                    {getString(cms, "enroll_phone_label") && (
                                        <div>
                                            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide" style={{ color: "var(--site-on-surface-variant)" }}>
                                                {getString(cms, "enroll_phone_label")}
                                            </label>
                                            <input
                                                type="tel"
                                                value={enrollForm.phone}
                                                onChange={(e) => setEnrollForm(f => ({ ...f, phone: e.target.value }))}
                                                className="w-full rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2"
                                                style={{ background: "var(--site-surface)", border: "2px solid var(--site-outline-variant)", color: "var(--site-on-surface)" }}
                                            />
                                        </div>
                                    )}
                                </form>

                                <div className="flex gap-3 border-t px-5 py-4" style={{ borderColor: "var(--site-outline-variant)" }}>
                                    {getString(cms, "enroll_cancel_label") && (
                                        <button
                                            type="button"
                                            onClick={() => setShowEnrollModal(false)}
                                            className="flex-1 rounded-lg py-2 text-sm font-bold transition-all"
                                            style={{ background: "var(--site-surface-container)", color: "var(--site-on-surface-variant)" }}
                                        >
                                            {getString(cms, "enroll_cancel_label")}
                                        </button>
                                    )}
                                    {getString(cms, "enroll_submit_label") && (
                                        <button
                                            type="submit"
                                            form="course-enroll-form"
                                            disabled={enrollSubmitting}
                                            className="flex-1 rounded-lg py-2 text-sm font-bold text-white transition-all disabled:opacity-60"
                                            style={{ background: "var(--site-cta-gradient)" }}
                                        >
                                            {enrollSubmitting ? getString(cms, "enroll_submitting_label") : getString(cms, "enroll_submit_label")}
                                        </button>
                                    )}
                                </div>
                            </div>
                        </motion.aside>
                    </>
                )}
            </AnimatePresence>

            <Footer_Simple />
        </div>
    );
}
