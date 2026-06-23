"use client";

import React, { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useContentBlock } from "@/hooks/useContent";
import { SITE_KEY } from "@/lib/site-config";
import RichText from "@/components/public/RichText";
import { motion, AnimatePresence } from "framer-motion";
import { PREMIUM_COURSES, PREMIUM_BOOKS, CourseItem, BookItem } from "@/lib/data/cursos";
import { ShoppingBag, ArrowRight, Clock, User, CheckCircle2 } from "lucide-react";
import { apiFetch } from "@/lib/http";
import CmsPageOverride from "@/components/public/cms/CmsPageOverride";

export default function CursosPage() {
    const { data: heroContent } = useContentBlock(`${SITE_KEY}_courses_hero`);
    const { data: coursesContent } = useContentBlock(`${SITE_KEY}_courses_feed`);
    
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
                body: { email, source: "newsletter-web", landing_page: "/cursos" }
            });
            showToast(newsletterSuccessToast);
            setEmail("");
        } catch (error) {
            showToast(newsletterErrorToast);
        } finally {
            setIsSubmitting(false);
        }
    };

    const [wishlist, setWishlist] = useState<string[]>([]);

    const handleAddToCart = async (title: string) => {
        if (wishlist.includes(title)) return;
        try {
            await apiFetch("/public/wishlist", {
                method: "POST",
                body: { title, landing_page: "/cursos" },
            });
            setWishlist((prev) => [...prev, title]);
            showToast(`"${title}" ${wishlistSuccessPrefix}`);
        } catch {
            showToast(`"${title}" ${wishlistFallbackPrefix}`);
            setWishlist((prev) => [...prev, title]);
        }
    };

    const heroEyebrow = heroContent?.eyebrow || "Formación & Sabiduría";
    const heroTitleLead = heroContent?.title_lead || "El Camino";
    const heroAccent = heroContent?.title_accent || "del Aprendizaje";
    const heroDescription = heroContent?.description || "Explora nuestra academia de cursos especializados y sumérgete en una selección literaria para iluminar tu entendimiento.";
    const courseFeed = (coursesContent?.parsed && typeof coursesContent.parsed === "object" && !Array.isArray(coursesContent.parsed))
        ? coursesContent.parsed as Record<string, unknown>
        : {};
    const heroImageUrl = typeof courseFeed.hero_image_url === "string"
        ? courseFeed.hero_image_url
        : "https://picsum.photos/seed/1481627834876-b7833e8f5570/1920/1080";
    const featuredFallbackImageUrl = typeof courseFeed.featured_fallback_image_url === "string"
        ? courseFeed.featured_fallback_image_url
        : "https://picsum.photos/seed/1524178232363-1fb2b075b655/800/600";
    const ctaImages = Array.isArray(courseFeed.cta_images) && courseFeed.cta_images.length >= 2
        ? courseFeed.cta_images.map((item) => item && typeof item === "object" ? item as Record<string, unknown> : {}).map((item) => ({
            src: typeof item.src === "string" ? item.src : "",
            alt: typeof item.alt === "string" ? item.alt : "Academia",
        })).filter((item) => item.src)
        : [
            { src: "https://picsum.photos/seed/academia1/800/800", alt: "Estudio" },
            { src: "https://picsum.photos/seed/academia2/800/800", alt: "Librería" },
        ];
    const libraryTitle = typeof courseFeed.library_title === "string" ? courseFeed.library_title : "Nuestra Librería";
    const libraryDescription = typeof courseFeed.library_description === "string" ? courseFeed.library_description : "Una curaduría de obras que han transformado generaciones. Desde clásicos de la patrística hasta literatura contemporánea.";
    const emptyBooksMessage = typeof courseFeed.empty_books_message === "string" ? courseFeed.empty_books_message : "Próximamente tendremos libros disponibles.";
    const coursesTitle = typeof courseFeed.courses_title === "string" ? courseFeed.courses_title : "Cursos & Academia";
    const coursesDescription = typeof courseFeed.courses_description === "string" ? courseFeed.courses_description : "Programas estructurados para líderes, estudiantes y buscadores de la verdad. Formación teológica y práctica con estándares de excelencia.";
    const ctaTitle = typeof courseFeed.cta_title === "string" ? courseFeed.cta_title : "Únete a la Academia FARO";
    const ctaDescription = typeof courseFeed.cta_description === "string" ? courseFeed.cta_description : "Recibe actualizaciones sobre nuevos cursos, lanzamientos de libros y eventos exclusivos de formación directamente en tu correo.";
    const ctaPlaceholder = typeof courseFeed.cta_placeholder === "string" ? courseFeed.cta_placeholder : "Tu correo electrónico";
    const ctaSubmit = typeof courseFeed.cta_submit === "string" ? courseFeed.cta_submit : "Suscribirme";
    const newsletterSuccessToast = typeof courseFeed.newsletter_success_toast === "string" ? courseFeed.newsletter_success_toast : "¡Te has suscrito con éxito a nuestra academia!";
    const newsletterErrorToast = typeof courseFeed.newsletter_error_toast === "string" ? courseFeed.newsletter_error_toast : "Error al suscribirse. Inténtalo de nuevo.";
    const wishlistSuccessPrefix = typeof courseFeed.wishlist_success_toast_prefix === "string" ? courseFeed.wishlist_success_toast_prefix : "añadido a tu lista — te contactaremos con info";
    const wishlistFallbackPrefix = typeof courseFeed.wishlist_fallback_toast_prefix === "string" ? courseFeed.wishlist_fallback_toast_prefix : "guardado en tu lista";

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
        <CmsPageOverride slug="cursos">
            <main className="pt-[88px] pb-4 overflow-hidden">
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

            {/* ── HERO ──────────────────────────────────── */}
            <section className="relative min-h-[380px] md:h-[560px] flex items-center px-4 sm:px-6 md:px-8 lg:px-12 overflow-hidden">
                <div className="absolute inset-0 z-0">
                    <Image
                        src={heroImageUrl}
                        alt="Librería"
                        fill
                        priority
                        className="object-cover"
                        style={{ filter: "brightness(0.3) saturate(0.5)" }}
                    />
                    <div
                        className="absolute inset-0"
                        style={{
                            background: "linear-gradient(to right, var(--site-background) 30%, transparent 70%)",
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
                        className="text-xs font-semibold uppercase tracking-wide mb-4 block"
                        style={{ color: "var(--site-primary)" }}
                    >
                        {heroEyebrow}
                    </span>
                    <h1
                        className="max-w-4xl font-bold tracking-tighter leading-none mb-3 text-5xl sm:text-6xl lg:text-8xl"
                        style={{ color: "var(--site-on-background)" }}
                    >
                        {heroTitleLead}
                        <br />
                        <span
                            style={{
                                background: "linear-gradient(135deg, var(--site-primary), var(--site-secondary))",
                                WebkitBackgroundClip: "text",
                                WebkitTextFillColor: "transparent",
                            }}
                        >
                            {heroAccent}.
                        </span>
                    </h1>
                    <RichText html={heroDescription} className="text-base sm:text-lg max-w-xl leading-relaxed" />
                </motion.div>
            </section>

            {/* ── CURSOS BENTO ──────────────────────────── */}
            <section className="px-4 sm:px-6 md:px-8 lg:px-12 mt-10 md:mt-24">
                <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    className="flex flex-col md:flex-row md:items-end justify-between mb-14 gap-3"
                >
                    <div className="max-w-2xl">
                        <h2
                            className="text-lg md:text-xl font-bold mb-4 tracking-tight"
                            style={{ color: "var(--site-on-surface)" }}
                        >
                            {coursesTitle}
                        </h2>
                        <p className="text-lg leading-relaxed" style={{ color: "var(--site-on-surface-variant)" }}>
                            {coursesDescription}
                        </p>
                    </div>
                </motion.div>

                <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
                    {/* Featured course */}
                    {featuredCourse && (
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            whileInView={{ opacity: 1, scale: 1 }}
                            viewport={{ once: true }}
                            transition={{ duration: 0.5 }}
                            className="md:col-span-8 group relative rounded-lg overflow-hidden min-h-[280px] md:min-h-[450px] cursor-pointer"
                            style={{ background: "var(--site-surface-container-low)" }}
                        >
                            <Link href={`/cursos/${featuredCourse.id || "1"}`} className="block absolute inset-0 z-20" />
                            <Image
                                src={featuredCourse.imageUrl || featuredFallbackImageUrl}
                                alt={featuredCourse.title}
                                fill
                                className="object-cover transition-transform duration-700 group-hover:scale-105"
                                style={{ opacity: 0.5 }}
                            />
                            <div
                                className="absolute inset-0"
                                style={{
                                    background: "linear-gradient(to top, var(--site-surface-container-lowest) 0%, transparent 60%)",
                                }}
                            />
                            <div className="absolute bottom-0 p-4 md:p-4 w-full relative z-10 flex flex-col justify-end h-full">
                                <div>
                                    <span
                                        className="inline-block px-4 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wide mb-3"
                                        style={{
                                            background: "var(--site-card-highlight)",
                                            color: "var(--site-primary)",
                                            backdropFilter: "blur(8px)"
                                        }}
                                    >
                                        {featuredCourse.tag || "Destacado"}
                                    </span>
                                    <h3
                                        className="text-lg md:text-xl font-bold mb-4 tracking-tight"
                                        style={{ color: "var(--site-on-surface)" }}
                                    >
                                        {featuredCourse.title}
                                    </h3>
                                    <p className="max-w-2xl mb-3 text-lg line-clamp-2 leading-relaxed" style={{ color: "var(--site-on-surface-variant)" }}>
                                        {featuredCourse.excerpt || featuredCourse.desc}
                                    </p>
                                    <div className="flex flex-wrap items-center gap-3">
                                        {featuredCourse.lessons && (
                                            <span className="flex items-center gap-2 text-sm font-bold uppercase tracking-wide" style={{ color: "var(--site-on-surface)" }}>
                                                <Clock size={16} style={{ color: "var(--site-primary)" }} />
                                                {featuredCourse.lessons} Semanas
                                            </span>
                                        )}
                                        <span className="flex items-center gap-2 text-sm font-bold uppercase tracking-wide" style={{ color: "var(--site-on-surface)" }}>
                                            <User size={16} style={{ color: "var(--site-primary)" }} />
                                            {featuredCourse.modality || "Online"}
                                        </span>
                                        <button
                                            className="ml-auto px-4 py-1.5 rounded-lg font-black text-sm text-white transition-all hover:scale-105 uppercase tracking-wide flex items-center gap-2"
                                            style={{ background: "var(--site-cta-gradient)" }}
                                        >
                                            {featuredCourse.cta || "Ver Curso"} <ArrowRight size={16} />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </motion.div>
                    )}

                    {/* Secondary courses */}
                    <div className="md:col-span-4 flex flex-col gap-3">
                        {secondaryCourses.map((c: CourseItem, i: number) => (
                            <Link href={`/cursos/${c.id || i}`} key={i} className="block flex-1">
                                <motion.div
                                    initial={{ opacity: 0, x: 20 }}
                                    whileInView={{ opacity: 1, x: 0 }}
                                    viewport={{ once: true }}
                                    transition={{ delay: i * 0.1 }}
                                    className="h-full rounded-lg p-4 group transition-all hover:-translate-y-2 hover:shadow-2xl flex flex-col justify-between"
                                    style={{
                                        background: "var(--site-surface-container-high)",
                                        border: "1px solid var(--site-outline-variant)",
                                    }}
                                >
                                    <div>
                                        <span
                                            className="text-[10px] font-semibold uppercase tracking-wide mb-4 block"
                                            style={{ color: "var(--site-secondary)" }}
                                        >
                                            {c.modality || c.tag}
                                        </span>
                                        <h4
                                            className="text-lg font-bold mb-4 group-hover:opacity-80 transition-opacity leading-tight"
                                            style={{ color: "var(--site-on-surface)" }}
                                        >
                                            {c.title}
                                        </h4>
                                        <p
                                            className="text-sm leading-relaxed line-clamp-3 mb-3"
                                            style={{ color: "var(--site-on-surface-variant)" }}
                                        >
                                            {c.excerpt || c.desc}
                                        </p>
                                    </div>
                                    <div className="flex justify-between items-center mt-auto border-t pt-6" style={{ borderColor: "var(--site-outline-variant)" }}>
                                        <span
                                            className="font-black text-xs uppercase tracking-wide"
                                            style={{ color: "var(--site-primary)" }}
                                        >
                                            {c.cta || "Ver Curso"}
                                        </span>
                                        <ArrowRight 
                                            size={20}
                                            className="group-hover:translate-x-2 transition-transform"
                                            style={{ color: "var(--site-primary)" }}
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
                className="px-4 sm:px-6 md:px-8 lg:px-12 mt-32 py-8 md:py-12 lg:py-16"
                style={{ background: "var(--site-surface-container-low)" }}
            >
                <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    className="max-w-xl mb-16"
                >
                        <h2
                            className="text-lg md:text-xl font-bold mb-3 tracking-tight"
                            style={{ color: "var(--site-on-surface)" }}
                        >
                        {libraryTitle}
                        </h2>
                        <p className="text-lg leading-relaxed" style={{ color: "var(--site-on-surface-variant)" }}>
                        {libraryDescription}
                        </p>
                    </motion.div>
                
                {books.length === 0 ? (
                    <p className="text-center py-8 text-sm" style={{ color: "var(--site-on-surface-variant)" }}>
                        {emptyBooksMessage}
                    </p>
                ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
                        {books.map((book, i) => (
                            <motion.div 
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ delay: i * 0.1 }}
                                key={book.title} 
                                className="group flex flex-col h-full"
                            >
                                <div className="relative w-full aspect-[2/3] rounded-lg mb-3 overflow-hidden shadow-xl transition-all duration-500 group-hover:-translate-y-2 group-hover:shadow-2xl">
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
                                    style={{ color: "var(--site-on-surface)" }}
                                >
                                    {book.title}
                                </h5>
                                <p
                                    className="text-xs font-semibold mb-3 uppercase tracking-wide"
                                    style={{ color: "var(--site-primary)" }}
                                >
                                    {book.author}
                                </p>
                                <p
                                    className="text-sm leading-relaxed mb-3 flex-grow"
                                    style={{ color: "var(--site-on-surface-variant)" }}
                                >
                                    {book.desc}
                                </p>
                                <div className="flex items-center justify-between pt-4 border-t" style={{ borderColor: "var(--site-outline-variant)" }}>
                                    <span
                                        className="text-lg font-bold"
                                        style={{ color: "var(--site-on-surface)" }}
                                    >
                                        {book.price}
                                    </span>
                                    <button
                                        onClick={() => handleAddToCart(book.title)}
                                        disabled={wishlist.includes(book.title)}
                                        className="w-12 h-8 rounded-lg flex items-center justify-center transition-all hover:scale-110 hover:-rotate-6 disabled:opacity-50 disabled:hover:scale-100 disabled:hover:rotate-0"
                                        style={{
                                            background: wishlist.includes(book.title) ? "var(--site-surface-container-highest)" : "var(--site-primary-container)",
                                            color: "var(--site-primary)",
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
            <section className="px-4 sm:px-6 md:px-8 lg:px-12 mt-16 md:mt-32">
                <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    className="rounded-lg p-6 md:p-14 lg:p-20 relative overflow-hidden shadow-2xl"
                    style={{
                        background: "linear-gradient(135deg, var(--site-surface-container-high) 0%, var(--site-surface-container-low) 100%)",
                        border: "1px solid var(--site-outline-variant)",
                    }}
                >
                    <div
                        className="absolute top-0 right-0 w-96 h-96 blur-[120px] rounded-full -mr-32 -mt-32 pointer-events-none"
                        style={{ background: "var(--site-card-highlight)" }}
                    />
                    <div className="relative z-10 grid grid-cols-1 md:grid-cols-2 gap-3 items-center">
                        <div>
                            <h2
                                className="text-lg md:text-xl font-bold mb-3 tracking-tight leading-[1.1]"
                                style={{ color: "var(--site-on-surface)" }}
                            >
                                {ctaTitle}
                            </h2>
                            <p
                                className="text-xl leading-relaxed mb-3"
                                style={{ color: "var(--site-on-surface-variant)" }}
                            >
                                {ctaDescription}
                            </p>
                            <form onSubmit={handleNewsletterSubmit} className="flex flex-col sm:flex-row gap-4">
                                <input
                                    type="email"
                                    required
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder={ctaPlaceholder}
                                    disabled={isSubmitting}
                                    className="flex-1 rounded-lg px-3 py-1.5 text-lg focus:outline-none transition-shadow focus:shadow-xl"
                                    style={{
                                        background: "var(--site-surface-container-highest)",
                                        color: "var(--site-on-surface)",
                                        border: "2px solid var(--site-outline-variant)",
                                    }}
                                />
                                <button
                                    type="submit"
                                    className="px-4 py-1.5 rounded-lg font-black text-sm text-white shadow-lg transition-all hover:scale-105 uppercase tracking-wide"
                                    style={{
                                        background: "var(--site-cta-gradient)",
                                    }}
                                >
                                    {ctaSubmit}
                                </button>
                            </form>
                        </div>
                        <div className="hidden md:grid grid-cols-2 gap-3">
                            <motion.div
                                initial={{ y: 20 }}
                                whileInView={{ y: 0 }}
                                className="relative aspect-square rounded-lg overflow-hidden shadow-2xl"
                                style={{ background: "var(--site-surface)" }}
                            >
                                <Image
                                    src={ctaImages[0]?.src || "https://picsum.photos/seed/academia1/800/800"}
                                    alt={ctaImages[0]?.alt || "Estudio"}
                                    fill
                                    className="object-cover"
                                    style={{ opacity: 0.9 }}
                                />
                            </motion.div>
                            <motion.div
                                initial={{ y: 40 }}
                                whileInView={{ y: 20 }}
                                className="relative aspect-square rounded-lg overflow-hidden shadow-2xl"
                                style={{ background: "var(--site-surface)" }}
                            >
                                <Image
                                    src={ctaImages[1]?.src || "https://picsum.photos/seed/academia2/800/800"}
                                    alt={ctaImages[1]?.alt || "Librería"}
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
        </CmsPageOverride>
    );
}
