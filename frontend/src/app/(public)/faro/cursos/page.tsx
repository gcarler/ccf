"use client";

import React from "react";
import Image from "next/image";
import { useContentBlock } from "@/hooks/useContent";

const BOOKS = [
    { title: "La Luz en la Tiniebla", author: "Roberto V. Solis", price: "$24.90", img: "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400&q=80", desc: "Un ensayo profundo sobre la esperanza en tiempos de incertidumbre." },
    { title: "Caminando con Gigantes", author: "Elena de los Ríos", price: "$19.50", img: "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=400&q=80", desc: "Biografías inspiradoras de líderes que cambiaron la historia cristiana." },
    { title: "El Faro Interior", author: "Manuel Farías", price: "$22.00", img: "https://images.unsplash.com/photo-1495446815901-a7297e633e8d?w=400&q=80", desc: "Manual de devoción diaria para el crecimiento espiritual sólido." },
    { title: "Mente & Espíritu", author: "Varios Autores", price: "$31.00", img: "https://images.unsplash.com/photo-1532012197267-da84d127e765?w=400&q=80", desc: "Intersección entre la psicología moderna y la fe profunda." },
];

export default function CursosPage() {
    const { data: heroContent } = useContentBlock("faro_courses_hero");
    const { data: coursesContent } = useContentBlock("faro_courses_feed");
    
    const heroEyebrow = heroContent?.eyebrow || "Formación & Sabiduría";
    const heroTitleLead = heroContent?.title_lead || "El Camino";
    const heroAccent = heroContent?.title_accent || "del Faro";
    const heroDescription = heroContent?.description || "Explora nuestra academia de cursos especializados y sumérgete en una selección literaria para iluminar tu entendimiento.";

    const fallbackCourses = [
        {
            tag: "Taller Práctico",
            title: "Liderazgo Eclesial Efectivo",
            desc: "Gestión y pastoreo para la nueva generación de líderes.",
            cta: "Inscripciones Abiertas",
        },
        {
            tag: "Seminario Online",
            title: "Arqueología Bíblica Nivel I",
            desc: "Hallazgos que dan contexto histórico a las escrituras.",
            cta: "Inicio: Octubre 15",
        },
    ];

    const courses = (Array.isArray(coursesContent?.parsed) && coursesContent.parsed.length > 0 
        ? coursesContent.parsed 
        : fallbackCourses) as any[];

    const featuredCourse = courses[0] || {
        title: "Fundamentos de Teología Contemporánea",
        lessons: "12 Semanas",
        modality: "Presencial",
        excerpt: "Un recorrido profundo por las bases de la fe aplicadas al contexto social y cultural del siglo XXI."
    };

    const secondaryCourses = courses.slice(1);

    return (
        <main className="pt-[88px] pb-32">
            {/* ── HERO ──────────────────────────────────── */}
            <section
                className="relative h-[560px] flex items-center px-8 md:px-20 overflow-hidden"
            >
                <div className="absolute inset-0 z-0">
                    <Image
                        src="https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=1600&q=80"
                        alt="Librería"
                        fill
                        className="object-cover"
                        style={{ filter: "brightness(0.3) saturate(0.5)" }}
                    />
                    <div
                        className="absolute inset-0"
                        style={{
                            background:
                                "linear-gradient(to right, var(--faro-background) 30%, transparent 70%)",
                        }}
                    />
                </div>
                <div className="relative z-10 max-w-4xl">
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
                                background:
                                    "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary))",
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
                </div>
            </section>

            {/* ── CURSOS BENTO ──────────────────────────── */}
            <section className="px-8 md:px-20 mt-24">
                <div className="flex flex-col md:flex-row md:items-end justify-between mb-14 gap-8">
                    <div className="max-w-2xl">
                        <h2
                            className="text-4xl font-black mb-4"
                            style={{ color: "var(--faro-on-surface)" }}
                        >
                            Cursos & Academia
                        </h2>
                        <p style={{ color: "var(--faro-on-surface-variant)" }}>
                            Programas estructurados para líderes, estudiantes y buscadores de
                            la verdad. Formación teológica y práctica con estándares de
                            excelencia.
                        </p>
                    </div>
                    <button
                        className="shrink-0 px-6 py-3 rounded-2xl border text-sm font-black uppercase tracking-widest transition-all hover:scale-105"
                        style={{
                            borderColor: "var(--faro-outline-variant)",
                            color: "var(--faro-on-surface-variant)",
                        }}
                    >
                        Ver todos
                    </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
                    {/* Featured course */}
                    <div
                        className="md:col-span-8 group relative rounded-3xl overflow-hidden min-h-[400px]"
                        style={{ background: "var(--faro-surface-container-low)" }}
                    >
                        <Image
                            src="https://images.unsplash.com/photo-1524178232363-1fb2b075b655?w=900&q=80"
                            alt="Fundamentos de Teología"
                            fill
                            className="object-cover transition-transform duration-700 group-hover:scale-105"
                            style={{ opacity: 0.45 }}
                        />
                        <div
                            className="absolute inset-0"
                            style={{
                                background:
                                    "linear-gradient(to top, var(--faro-surface-container-lowest) 0%, transparent 55%)",
                            }}
                        />
                        <div className="absolute bottom-0 p-8 w-full relative z-10">
                            <span
                                className="inline-block px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest mb-4"
                                style={{
                                    background: "rgba(44,96,157,0.2)",
                                    color: "var(--faro-primary)",
                                }}
                            >
                                Certificación Master
                            </span>
                            <h3
                                className="text-3xl font-black mb-2"
                                style={{ color: "var(--faro-on-surface)" }}
                            >
                                {featuredCourse.title}
                            </h3>
                            <p
                                className="max-w-lg mb-6 line-clamp-2"
                                style={{ color: "var(--faro-on-surface-variant)" }}
                            >
                                {featuredCourse.excerpt}
                            </p>
                            <div className="flex items-center gap-6">
                                <span
                                    className="flex items-center gap-2 text-xs font-bold"
                                    style={{ color: "var(--faro-primary)" }}
                                >
                                    <span className="material-symbols-outlined text-sm">schedule</span>
                                    {featuredCourse.lessons} Semanas
                                </span>
                                <span
                                    className="flex items-center gap-2 text-xs font-bold"
                                    style={{ color: "var(--faro-primary)" }}
                                >
                                    <span className="material-symbols-outlined text-sm">person</span>
                                    {featuredCourse.modality}
                                </span>
                                <button
                                    className="ml-auto px-8 py-3 rounded-2xl font-black text-sm text-white transition-all hover:scale-105"
                                    style={{
                                        background:
                                            "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary))",
                                    }}
                                >
                                    Inscribirse
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* Secondary courses */}
                    <div className="md:col-span-4 flex flex-col gap-5">
                        {secondaryCourses.map((c: any, i: number) => (
                            <div
                                key={i}
                                className="flex-1 rounded-2xl p-8 group cursor-pointer transition-all hover:-translate-y-1"
                                style={{
                                    background: "var(--faro-surface-container-high)",
                                    border: "1px solid var(--faro-outline-variant)",
                                }}
                            >
                                <span
                                    className="text-[10px] font-black uppercase tracking-widest mb-4 block"
                                    style={{ color: "var(--faro-secondary)" }}
                                >
                                    {c.modality || c.tag}
                                </span>
                                <h4
                                    className="text-xl font-black mb-3 group-hover:opacity-80 transition-opacity"
                                    style={{ color: "var(--faro-on-surface)" }}
                                >
                                    {c.title}
                                </h4>
                                <p
                                    className="text-sm leading-relaxed mb-6"
                                    style={{ color: "var(--faro-on-surface-variant)" }}
                                >
                                    {c.excerpt || c.desc}
                                </p>
                                <div className="flex justify-between items-center">
                                    <span
                                        className="font-black text-sm"
                                        style={{ color: "var(--faro-primary)" }}
                                    >
                                        {c.cta || "Inscribirse"}
                                    </span>
                                    <span
                                        className="material-symbols-outlined group-hover:translate-x-2 transition-transform"
                                        style={{ color: "var(--faro-primary)" }}
                                    >
                                        arrow_forward
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── LIBRERÍA ──────────────────────────────── */}
            <section
                className="px-8 md:px-20 mt-28 py-20"
                style={{ background: "var(--faro-surface-container-low)" }}
            >
                <div className="max-w-xl mb-14">
                    <h2
                        className="text-4xl font-black mb-4"
                        style={{ color: "var(--faro-on-surface)" }}
                    >
                        Nuestra Librería
                    </h2>
                    <p style={{ color: "var(--faro-on-surface-variant)" }}>
                        Una curaduría de obras que han transformado generaciones. Desde
                        clásicos de la patrística hasta literatura contemporánea.
                    </p>
                </div>
                <div className="flex gap-8 overflow-x-auto pb-10 hide-scrollbar snap-x">
                    {BOOKS.map(({ title, author, price, img, desc }) => (
                        <div key={title} className="flex-none w-64 snap-start group">
                            <div className="relative aspect-[2/3] rounded-2xl mb-5 overflow-hidden shadow-2xl transition-transform duration-500 group-hover:-rotate-2 group-hover:scale-105">
                                <Image
                                    src={img}
                                    alt={title}
                                    fill
                                    className="object-cover"
                                />
                                <div className="absolute inset-0 bg-black/15 group-hover:bg-transparent transition-colors" />
                            </div>
                            <h5
                                className="font-black text-lg mb-1"
                                style={{ color: "var(--faro-on-surface)" }}
                            >
                                {title}
                            </h5>
                            <p
                                className="text-xs font-bold mb-2 uppercase tracking-tight"
                                style={{ color: "var(--faro-primary)" }}
                            >
                                {author}
                            </p>
                            <p
                                className="text-sm leading-relaxed line-clamp-2 mb-4"
                                style={{ color: "var(--faro-on-surface-variant)" }}
                            >
                                {desc}
                            </p>
                            <div className="flex items-center justify-between">
                                <span
                                    className="text-xl font-black"
                                    style={{ color: "var(--faro-on-surface)" }}
                                >
                                    {price}
                                </span>
                                <button
                                    className="w-10 h-10 rounded-xl flex items-center justify-center transition-all hover:scale-110"
                                    style={{
                                        background: "var(--faro-primary-container)",
                                        color: "var(--faro-primary)",
                                    }}
                                >
                                    <span className="material-symbols-outlined text-xl">shopping_bag</span>
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            </section>

            {/* ── CTA ACADEMIA ─────────────────────────── */}
            <section className="px-8 md:px-20 mt-24">
                <div
                    className="rounded-3xl p-12 md:p-20 relative overflow-hidden"
                    style={{
                        background:
                            "linear-gradient(135deg, var(--faro-surface-container-high) 0%, var(--faro-surface-container-low) 100%)",
                        border: "1px solid var(--faro-outline-variant)",
                    }}
                >
                    <div
                        className="absolute top-0 right-0 w-64 h-64 blur-[100px] rounded-full -mr-20 -mt-20 pointer-events-none"
                        style={{ background: "rgba(44,96,157,0.12)" }}
                    />
                    <div className="relative z-10 grid grid-cols-1 md:grid-cols-2 gap-14 items-center">
                        <div>
                            <h2
                                className="text-4xl md:text-5xl font-black mb-5"
                                style={{ color: "var(--faro-on-surface)" }}
                            >
                                Únete a la Academia FARO
                            </h2>
                            <p
                                className="text-lg leading-relaxed mb-8"
                                style={{ color: "var(--faro-on-surface-variant)" }}
                            >
                                Recibe actualizaciones sobre nuevos cursos, lanzamientos de
                                libros y eventos exclusivos de formación directamente en tu
                                correo.
                            </p>
                            <form className="flex flex-col sm:flex-row gap-4">
                                <input
                                    type="email"
                                    placeholder="Tu correo electrónico"
                                    className="flex-1 rounded-2xl px-6 py-4 text-sm focus:outline-none"
                                    style={{
                                        background: "var(--faro-surface-container-highest)",
                                        color: "var(--faro-on-surface)",
                                        border: "2px solid var(--faro-outline-variant)",
                                    }}
                                />
                                <button
                                    type="button"
                                    className="px-10 py-4 rounded-2xl font-black text-sm text-white shadow-lg transition-all hover:scale-105"
                                    style={{
                                        background:
                                            "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary))",
                                    }}
                                >
                                    Suscribirme
                                </button>
                            </form>
                        </div>
                        <div className="hidden md:grid grid-cols-2 gap-4">
                            <div
                                className="relative aspect-square rounded-2xl overflow-hidden"
                                style={{ background: "var(--faro-surface)" }}
                            >
                                <Image
                                    src="https://images.unsplash.com/photo-1434030216411-0b793f4b4173?w=400&q=80"
                                    alt="Estudio"
                                    fill
                                    className="object-cover"
                                    style={{ opacity: 0.8 }}
                                />
                            </div>
                            <div
                                className="relative aspect-square rounded-2xl overflow-hidden mt-8"
                                style={{ background: "var(--faro-surface)" }}
                            >
                                <Image
                                    src="https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?w=400&q=80"
                                    alt="Librería"
                                    fill
                                    className="object-cover"
                                    style={{ opacity: 0.8 }}
                                />
                            </div>
                        </div>
                    </div>
                </div>
            </section>
        </main>
    );
}

