"use client";

import React, { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useContentBlock } from "@/hooks/useContent";
import { motion, AnimatePresence } from "framer-motion";
import { PREMIUM_COURSES, PREMIUM_BOOKS, CourseItem, BookItem } from "@/lib/data/cursos";
import { ShoppingBag, ArrowRight, Clock, User, CheckCircle2 } from "lucide-react";
import { apiFetch } from "@/lib/http";

export default function CursosPage() {
    const { data: heroContent } = useContentBlock("faro_courses_hero");
    const { data: coursesContent } = useContentBlock("faro_courses_feed");
    
    // State
    const [toastMessage, setToastMessage] = useState<string | null>(null);
    const [email, setEmail] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [apiCourses, setApiCourses] = useState<CourseItem[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        apiFetch<CourseItem[]>("/public/courses", { silent: true })
            .then(data => setApiCourses(data))
            .catch(() => setApiCourses([])) // Fallback will be handled below
            .finally(() => setIsLoading(false));
    }, []);

    const showToast = (message: string) => {
        setToastMessage(message);
        setTimeout(() => setToastMessage(null), 3000);
    };

    const handleNewsletterSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!email.trim() || isSubmitting) return;
        
        setIsSubmitting(true);
        try {
            await apiFetch("/public/newsletter/subscribe", {
                method: "POST",
                body: { email }
            });
            showToast("¡Te has suscrito con éxito a nuestra academia!");
            setEmail("");
        } catch (error) {
            showToast("Error al suscribirse. Inténtalo de nuevo.");
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleAddToCart = (title: string) => {
        showToast(`"${title}" añadido al carrito de compras`);
    };

    const heroEyebrow = heroContent?.eyebrow || "Formación & Sabiduría";
    const heroTitleLead = heroContent?.title_lead || "El Camino";
    const heroAccent = heroContent?.title_accent || "del Faro";
    const heroDescription = heroContent?.description || "Explora nuestra academia de cursos especializados y sumérgete en una selección literaria para iluminar tu entendimiento.";

    const cmsCourses: CourseItem[] = Array.isArray(coursesContent?.parsed) && coursesContent.parsed.length > 0 
        ? coursesContent.parsed as CourseItem[]
        : [];

    // Prioritize Backend API Courses -> CMS Courses -> Local Fallback Premium Courses
    let activeCourses = apiCourses.length > 0 ? apiCourses : cmsCourses;
    if (activeCourses.length === 0 && !isLoading) {
        activeCourses = PREMIUM_COURSES;
    }

    const featuredCourse = activeCourses[0];
    const secondaryCourses = activeCourses.slice(1);

    const cmsBooks: BookItem[] = (coursesContent?.parsed && typeof coursesContent.parsed === "object" && !Array.isArray(coursesContent.parsed) && Array.isArray((coursesContent.parsed as Record<string, unknown>).books))
        ? (coursesContent.parsed as Record<string, unknown>).books as BookItem[]
        : [];
        
    const books = cmsBooks.length > 0 ? cmsBooks : PREMIUM_BOOKS;

    return (
        <main className="pt-[88px] pb-32 overflow-hidden">
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

            {/* ── HERO ──────────────────────────────────── */}
            <section className="relative h-[560px] flex items-center px-8 md:px-20 overflow-hidden">
                <div className="absolute inset-0 z-0">
                    <Image
                        src="https://picsum.photos/seed/1481627834876-b7833e8f5570/1920/1080"
                        alt="Librería"
                        fill
                        priority
                        className="object-cover"
                        style={{ filter: "brightness(0.3) saturate(0.5)" }}
                    />
                    <div
                        className="absolute inset-0"
                        style={{
                            background: "linear-gradient(to right, var(--faro-background) 30%, transparent 70%)",
                        }}
                    />
                </div>
                <motion.div 
                    initial={{ opacity: 0, x: -30 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.8 }}
                    className="relative z-10 max-w-4xl"
                >
                    <span
                        className="text-xs font-black uppercase tracking-[0.25em] mb-4 block"
                        style={{ color: "var(--faro-primary)" }}
                    >
                        {heroEyebrow}
                    </span>
                    <h1
                        className="font-black tracking-tighter leading-none mb-6"
                        style={{
                            fontSize: "clamp(3rem, 8vw, 7rem)",
                            color: "var(--faro-on-background)",
                        }}
                    >
                        {heroTitleLead}
                        <br />
                        <span
                            style={{
                                background: "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary))",
                                WebkitBackgroundClip: "text",
                                WebkitTextFillColor: "transparent",
                            }}
                        >
                            {heroAccent}.
                        </span>
                    </h1>
                    <p
                        className="text-xl max-w-xl leading-relaxed"
                        style={{ color: "var(--faro-on-surface-variant)" }}
                    >
                        {heroDescription}
                    </p>
                </motion.div>
            </section>

            {/* ── CURSOS BENTO ──────────────────────────── */}
            <section className="px-8 md:px-20 mt-24">
                <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    className="flex flex-col md:flex-row md:items-end justify-between mb-14 gap-8"
                >
                    <div className="max-w-2xl">
                        <h2
                            className="text-4xl md:text-5xl font-black mb-4 tracking-tight"
                            style={{ color: "var(--faro-on-surface)" }}
                        >
                            Cursos & Academia
                        </h2>
                        <p className="text-lg leading-relaxed" style={{ color: "var(--faro-on-surface-variant)" }}>
                            Programas estructurados para líderes, estudiantes y buscadores de
                            la verdad. Formación teológica y práctica con estándares de excelencia.
                        </p>
                    </div>
                </motion.div>

                <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
                    {/* Featured course */}
                    {featuredCourse && (
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            whileInView={{ opacity: 1, scale: 1 }}
                            viewport={{ once: true }}
                            transition={{ duration: 0.5 }}
                            className="md:col-span-8 group relative rounded-3xl overflow-hidden min-h-[450px] cursor-pointer"
                            style={{ background: "var(--faro-surface-container-low)" }}
                        >
                            <Link href={`/faro/cursos/${featuredCourse.id || "1"}`} className="block absolute inset-0 z-20" />
                            <Image
                                src={featuredCourse.imageUrl || "https://picsum.photos/seed/1524178232363-1fb2b075b655/800/600"}
                                alt={featuredCourse.title}
                                fill
                                className="object-cover transition-transform duration-700 group-hover:scale-105"
                                style={{ opacity: 0.5 }}
                            />
                            <div
                                className="absolute inset-0"
                                style={{
                                    background: "linear-gradient(to top, var(--faro-surface-container-lowest) 0%, transparent 60%)",
                                }}
                            />
                            <div className="absolute bottom-0 p-8 md:p-12 w-full relative z-10 flex flex-col justify-end h-full">
                                <div>
                                    <span
                                        className="inline-block px-4 py-1.5 rounded-full text-xs font-black uppercase tracking-widest mb-6"
                                        style={{
                                            background: "rgba(44,96,157,0.2)",
                                            color: "var(--faro-primary)",
                                            backdropFilter: "blur(8px)"
                                        }}
                                    >
                                        {featuredCourse.tag || "Destacado"}
                                    </span>
                                    <h3
                                        className="text-4xl md:text-5xl font-black mb-4 tracking-tight"
                                        style={{ color: "var(--faro-on-surface)" }}
                                    >
                                        {featuredCourse.title}
                                    </h3>
                                    <p className="max-w-2xl mb-8 text-lg line-clamp-2 leading-relaxed" style={{ color: "var(--faro-on-surface-variant)" }}>
                                        {featuredCourse.excerpt || featuredCourse.desc}
                                    </p>
                                    <div className="flex flex-wrap items-center gap-6">
                                        {featuredCourse.lessons && (
                                            <span className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest" style={{ color: "var(--faro-on-surface)" }}>
                                                <Clock size={16} style={{ color: "var(--faro-primary)" }} />
                                                {featuredCourse.lessons} Semanas
                                            </span>
                                        )}
                                        <span className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest" style={{ color: "var(--faro-on-surface)" }}>
                                            <User size={16} style={{ color: "var(--faro-primary)" }} />
                                            {featuredCourse.modality || "Online"}
                                        </span>
                                        <button
                                            className="ml-auto px-8 py-3.5 rounded-2xl font-black text-sm text-white transition-all hover:scale-105 uppercase tracking-widest flex items-center gap-2"
                                            style={{ background: "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary))" }}
                                        >
                                            {featuredCourse.cta || "Ver Curso"} <ArrowRight size={16} />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </motion.div>
                    )}

                    {/* Secondary courses */}
                    <div className="md:col-span-4 flex flex-col gap-6">
                        {secondaryCourses.map((c: CourseItem, i: number) => (
                            <Link href={`/faro/cursos/${c.id || i}`} key={i} className="block flex-1">
                                <motion.div
                                    initial={{ opacity: 0, x: 20 }}
                                    whileInView={{ opacity: 1, x: 0 }}
                                    viewport={{ once: true }}
                                    transition={{ delay: i * 0.1 }}
                                    className="h-full rounded-3xl p-8 group transition-all hover:-translate-y-2 hover:shadow-2xl flex flex-col justify-between"
                                    style={{
                                        background: "var(--faro-surface-container-high)",
                                        border: "1px solid var(--faro-outline-variant)",
                                    }}
                                >
                                    <div>
                                        <span
                                            className="text-[10px] font-black uppercase tracking-[0.2em] mb-4 block"
                                            style={{ color: "var(--faro-secondary)" }}
                                        >
                                            {c.modality || c.tag}
                                        </span>
                                        <h4
                                            className="text-2xl font-black mb-4 group-hover:opacity-80 transition-opacity leading-tight"
                                            style={{ color: "var(--faro-on-surface)" }}
                                        >
                                            {c.title}
                                        </h4>
                                        <p
                                            className="text-sm leading-relaxed line-clamp-3 mb-8"
                                            style={{ color: "var(--faro-on-surface-variant)" }}
                                        >
                                            {c.excerpt || c.desc}
                                        </p>
                                    </div>
                                    <div className="flex justify-between items-center mt-auto border-t pt-6" style={{ borderColor: "var(--faro-outline-variant)" }}>
                                        <span
                                            className="font-black text-xs uppercase tracking-widest"
                                            style={{ color: "var(--faro-primary)" }}
                                        >
                                            {c.cta || "Ver Curso"}
                                        </span>
                                        <ArrowRight 
                                            size={20}
                                            className="group-hover:translate-x-2 transition-transform"
                                            style={{ color: "var(--faro-primary)" }}
                                        />
                                    </div>
                                </motion.div>
                            </Link>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── LIBRERÍA ──────────────────────────────── */}
            <section
                className="px-8 md:px-20 mt-32 py-24"
                style={{ background: "var(--faro-surface-container-low)" }}
            >
                <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    className="max-w-xl mb-16"
                >
                    <h2
                        className="text-4xl md:text-5xl font-black mb-6 tracking-tight"
                        style={{ color: "var(--faro-on-surface)" }}
                    >
                        Nuestra Librería
                    </h2>
                    <p className="text-lg leading-relaxed" style={{ color: "var(--faro-on-surface-variant)" }}>
                        Una curaduría de obras que han transformado generaciones. Desde
                        clásicos de la patrística hasta literatura contemporánea.
                    </p>
                </motion.div>
                
                {books.length === 0 ? (
                    <p className="text-center py-8 text-sm" style={{ color: "var(--faro-on-surface-variant)" }}>
                        Próximamente tendremos libros disponibles.
                    </p>
                ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-8">
                        {books.map((book, i) => (
                            <motion.div 
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ delay: i * 0.1 }}
                                key={book.title} 
                                className="group flex flex-col h-full"
                            >
                                <div className="relative w-full aspect-[2/3] rounded-2xl mb-6 overflow-hidden shadow-xl transition-all duration-500 group-hover:-translate-y-2 group-hover:shadow-2xl">
                                    <Image
                                        src={book.img}
                                        alt={book.title}
                                        fill
                                        sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 25vw"
                                        className="object-cover transition-transform duration-700 group-hover:scale-105"
                                    />
                                    <div className="absolute inset-0 bg-black/5 group-hover:bg-transparent transition-colors" />
                                </div>
                                <h5
                                    className="font-black text-xl mb-2 leading-tight"
                                    style={{ color: "var(--faro-on-surface)" }}
                                >
                                    {book.title}
                                </h5>
                                <p
                                    className="text-xs font-black mb-3 uppercase tracking-widest"
                                    style={{ color: "var(--faro-primary)" }}
                                >
                                    {book.author}
                                </p>
                                <p
                                    className="text-sm leading-relaxed mb-6 flex-grow"
                                    style={{ color: "var(--faro-on-surface-variant)" }}
                                >
                                    {book.desc}
                                </p>
                                <div className="flex items-center justify-between pt-4 border-t" style={{ borderColor: "var(--faro-outline-variant)" }}>
                                    <span
                                        className="text-2xl font-black"
                                        style={{ color: "var(--faro-on-surface)" }}
                                    >
                                        {book.price}
                                    </span>
                                    <button
                                        onClick={() => handleAddToCart(book.title)}
                                        className="w-12 h-12 rounded-2xl flex items-center justify-center transition-all hover:scale-110 hover:-rotate-6"
                                        style={{
                                            background: "var(--faro-primary-container)",
                                            color: "var(--faro-primary)",
                                        }}
                                    >
                                        <ShoppingBag size={20} />
                                    </button>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                )}
            </section>

            {/* ── CTA ACADEMIA ─────────────────────────── */}
            <section className="px-8 md:px-20 mt-32">
                <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    className="rounded-[3rem] p-12 md:p-24 relative overflow-hidden shadow-2xl"
                    style={{
                        background: "linear-gradient(135deg, var(--faro-surface-container-high) 0%, var(--faro-surface-container-low) 100%)",
                        border: "1px solid var(--faro-outline-variant)",
                    }}
                >
                    <div
                        className="absolute top-0 right-0 w-96 h-96 blur-[120px] rounded-full -mr-32 -mt-32 pointer-events-none"
                        style={{ background: "rgba(44,96,157,0.15)" }}
                    />
                    <div className="relative z-10 grid grid-cols-1 md:grid-cols-2 gap-16 items-center">
                        <div>
                            <h2
                                className="text-4xl md:text-6xl font-black mb-6 tracking-tight leading-[1.1]"
                                style={{ color: "var(--faro-on-surface)" }}
                            >
                                Únete a la <br/>Academia FARO
                            </h2>
                            <p
                                className="text-xl leading-relaxed mb-10"
                                style={{ color: "var(--faro-on-surface-variant)" }}
                            >
                                Recibe actualizaciones sobre nuevos cursos, lanzamientos de
                                libros y eventos exclusivos de formación directamente en tu
                                correo.
                            </p>
                            <form onSubmit={handleNewsletterSubmit} className="flex flex-col sm:flex-row gap-4">
                                <input
                                    type="email"
                                    required
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder="Tu correo electrónico"
                                    disabled={isSubmitting}
                                    className="flex-1 rounded-2xl px-6 py-4 text-lg focus:outline-none transition-shadow focus:shadow-xl"
                                    style={{
                                        background: "var(--faro-surface-container-highest)",
                                        color: "var(--faro-on-surface)",
                                        border: "2px solid var(--faro-outline-variant)",
                                    }}
                                />
                                <button
                                    type="submit"
                                    className="px-10 py-4 rounded-2xl font-black text-sm text-white shadow-lg transition-all hover:scale-105 uppercase tracking-widest"
                                    style={{
                                        background: "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary))",
                                    }}
                                >
                                    Suscribirme
                                </button>
                            </form>
                        </div>
                        <div className="hidden md:grid grid-cols-2 gap-6">
                            <motion.div
                                initial={{ y: 20 }}
                                whileInView={{ y: 0 }}
                                className="relative aspect-square rounded-[2rem] overflow-hidden shadow-2xl"
                                style={{ background: "var(--faro-surface)" }}
                            >
                                <Image
                                    src="https://picsum.photos/seed/academia1/800/800"
                                    alt="Estudio"
                                    fill
                                    className="object-cover"
                                    style={{ opacity: 0.9 }}
                                />
                            </motion.div>
                            <motion.div
                                initial={{ y: 40 }}
                                whileInView={{ y: 20 }}
                                className="relative aspect-square rounded-[2rem] overflow-hidden shadow-2xl"
                                style={{ background: "var(--faro-surface)" }}
                            >
                                <Image
                                    src="https://picsum.photos/seed/academia2/800/800"
                                    alt="Librería"
                                    fill
                                    className="object-cover"
                                    style={{ opacity: 0.9 }}
                                />
                            </motion.div>
                        </div>
                    </div>
                </motion.div>
            </section>
        </main>
    );
}
