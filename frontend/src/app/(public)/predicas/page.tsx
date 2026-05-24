"use client";

import React, { useState, useMemo } from "react";
import { motion } from "framer-motion";
import Image from "next/image";
import Link from "next/link";
import { ChevronRight, Bookmark, Play } from "lucide-react";
import { useContentBlock } from "@/hooks/useContent";

export default function PredicasPage() {
    const { data: heroContent } = useContentBlock("faro_sermons_hero");
    const { data: sermonsContent } = useContentBlock("faro_sermons_feed");
    const [activeFilter, setActiveFilter] = useState("Todas");
    const [sortBy, setSortBy] = useState("recent");
    const [bookmarked, setBookmarked] = useState<Set<string>>(new Set());

    const heroEyebrow = heroContent?.eyebrow || "Mensaje Destacado";
    const heroTitleLead = heroContent?.title_lead || "Alimento para el";
    const heroAccent = heroContent?.title_accent || "Alma";
    const heroDescription = heroContent?.description || "Explora nuestra biblioteca de mensajes que iluminan el camino. Una guía espiritual diseñada para nutrir tu fe.";

    interface SermonItem {
        title?: string;
        slug?: string;
        img?: string;
        thumbnail?: string;
        author?: string;
        speaker?: string;
        duration?: string;
        series?: string;
        excerpt?: string;
        featured?: boolean;
        topics?: string[];
    }

    const sermons: SermonItem[] = Array.isArray(sermonsContent?.parsed) && sermonsContent.parsed.length > 0
        ? sermonsContent.parsed as SermonItem[]
        : [];

    const featuredSermon = sermons.find((s) => s.featured) || sermons[0];

    const filteredSermons = useMemo(() => {
        let filtered = sermons.filter((s) => !s.featured);
        if (activeFilter === "Series" && filtered.length > 0) {
            filtered = filtered.filter((s) => s.series);
        }
        if (activeFilter === "Oradores" && filtered.length > 0) {
            filtered = filtered.filter((s) => s.speaker || s.author);
        }
        return sortBy === "recent" ? filtered : [...filtered].reverse();
    }, [sermons, activeFilter, sortBy]);

    const secondarySermons = filteredSermons.slice(0, 4);

    const toggleBookmark = (title: string) => {
        setBookmarked((prev) => {
            const next = new Set(prev);
            if (next.has(title)) next.delete(title);
            else next.add(title);
            return next;
        });
    };

    const hasSermons = sermons.length > 0;

    const DEFAULT_SERMONS: SermonItem[] = [
        { title: "La luz en la oscuridad", speaker: "Pastor Juan", duration: "42:15", series: "Fe Viva", excerpt: "Un mensaje sobre encontrar esperanza en los momentos más difíciles." },
        { title: "Caminar en propósito", speaker: "Pastora María", duration: "38:30", series: "Propósito", excerpt: "Descubre el plan que Dios tiene para tu vida." },
        { title: "Gracia que transforma", speaker: "Pastor Carlos", duration: "50:00", series: "Gracia", excerpt: "Cómo la gracia de Dios cambia nuestra perspectiva." },
        { title: "Comunidad que sana", speaker: "Pastor Luis", duration: "35:45", series: "Fe Viva", excerpt: "El poder sanador de estar en comunidad." },
    ];

    const displaySermons = hasSermons ? secondarySermons : DEFAULT_SERMONS;
    const displayFeatured = hasSermons ? featuredSermon : DEFAULT_SERMONS[0];

    return (
        <main className="pt-[88px] bg-faro-surface">
            {/* ── HERO CINEMATOGRÁFICO ─────────────────────────── */}
            <section className="relative min-h-[80vh] flex items-end overflow-hidden">
                <div className="absolute inset-0">
                    <Image
                        src="https://picsum.photos/seed/1507692049790-de58290a4334/800/600"
                        alt="Background"
                        fill
                        className="object-cover scale-105"
                        style={{ filter: "brightness(0.3) saturate(0.8)" }}
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-faro-surface via-transparent to-transparent" />
                    <div className="absolute inset-0 bg-gradient-to-r from-faro-surface/60 via-transparent to-transparent" />
                </div>

                <div className="relative z-10 px-3 md:px-4 lg:px-8 xl:px-12 pb-4 w-full">
                    <motion.div
                        initial={{ opacity: 0, y: 30 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="max-w-3xl"
                    >
                        <div className="flex items-center gap-4 mb-3">
                            <span className="w-12 h-0.5 bg-faro-primary" />
                            <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--faro-primary)" }}>
                                {heroEyebrow}
                            </span>
                        </div>
                        <h1
                            className="font-bold tracking-tighter leading-[0.9] mb-3"
                            style={{
                                fontSize: "clamp(3.5rem, 8vw, 7rem)",
                                color: "var(--faro-on-hero)"
                            }}
                        >
                            {heroTitleLead} <br/>
                            <span className="italic" style={{ color: "var(--faro-primary)" }}>{heroAccent}.</span>
                        </h1>
                        <p className="text-xl md:text-lg opacity-70 mb-3 leading-relaxed" style={{ color: "var(--faro-on-hero)" }}>
                            {heroDescription}
                        </p>
                        <div className="flex flex-wrap gap-4">
                            <Link
                                href={hasSermons && featuredSermon?.slug ? `/predicas/${featuredSermon.slug}` : "#"}
                                className="flex items-center gap-3 px-4 py-2 rounded-lg font-black text-sm uppercase tracking-wide transition-all hover:scale-105 shadow-2xl"
                                style={{ background: "var(--faro-hero-cta-gradient)", color: "var(--faro-on-hero)" }}
                            >
                                <Play fill="currentColor" size={18} />
                                {hasSermons ? "Ver ahora" : "Próximamente"}
                            </Link>
                            <button
                                onClick={() => hasSermons && featuredSermon?.title && toggleBookmark(featuredSermon.title)}
                                className="flex items-center gap-3 px-4 py-2 rounded-lg font-black text-sm uppercase tracking-wide transition-all hover:scale-105"
                                style={{
                                    background: "var(--faro-hero-bg-light)",
                                    backdropFilter: "blur(20px)",
                                    border: "1px solid var(--faro-hero-border-light)",
                                    color: "var(--faro-on-hero)",
                                }}
                            >
                                <Bookmark size={18} fill={hasSermons && featuredSermon?.title && bookmarked.has(featuredSermon.title) ? "currentColor" : "none"} />
                                Mi lista
                            </button>
                        </div>
                    </motion.div>
                </div>
            </section>

            {/* ── FILTROS Y CATEGORÍAS ───────────────────────── */}
            <section className="px-3 md:px-4 lg:px-8 xl:px-12 -mt-3 relative z-20">
                <div
                    className="rounded-lg p-4 flex flex-col md:flex-row items-center justify-between gap-3 border backdrop-blur-3xl shadow-2xl"
                    style={{
                        background: "var(--faro-surface-container-highest)",
                        borderColor: "var(--faro-outline-variant)",
                        opacity: 0.95
                    }}
                >
                    <div className="flex flex-wrap justify-center gap-3 text-[10px] font-semibold uppercase tracking-wide">
                        {["Todas", "Series", "Oradores"].map((cat) => (
                            <button
                                key={cat}
                                onClick={() => setActiveFilter(cat)}
                                className={`transition-all ${activeFilter === cat ? "text-faro-primary font-bold" : "opacity-50 hover:text-faro-primary hover:opacity-100"}`}
                            >
                                {cat}
                            </button>
                        ))}
                    </div>
                    <div className="w-full md:w-auto">
                        <select
                            value={sortBy}
                            onChange={(e) => setSortBy(e.target.value)}
                            className="w-full md:w-64 bg-faro-surface-container-low rounded-md px-4 py-3 text-xs font-semibold uppercase tracking-wide outline-none border border-transparent focus:border-faro-primary/30"
                        >
                            <option value="recent">Más recientes</option>
                            <option value="popular">Más vistos</option>
                        </select>
                    </div>
                </div>
            </section>

            {/* ── GALERÍA DE VÍDEOS ──────────────────────────── */}
            <section className="py-1.5 px-3 md:px-4 lg:px-8 xl:px-12">
                {!hasSermons ? (
                    <div className="text-center py-16">
                        <Play size={64} className="mx-auto mb-4 opacity-20" style={{ color: "var(--faro-primary)" }} />
                        <h2 className="text-xl font-bold mb-3" style={{ color: "var(--faro-on-surface)" }}>
                            Prédicas próximamente
                        </h2>
                        <p className="text-sm max-w-md mx-auto" style={{ color: "var(--faro-on-surface-variant)" }}>
                            Estamos preparando nuestra biblioteca de mensajes. Vuelve pronto para encontrar alimento espiritual.
                        </p>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-8 max-w-2xl mx-auto">
                            {DEFAULT_SERMONS.map((s, i) => (
                                <div key={i} className="rounded-lg p-4 border" style={{ background: "var(--faro-surface-container)", borderColor: "var(--faro-outline-variant)" }}>
                                    <h4 className="font-bold text-sm mb-1" style={{ color: "var(--faro-on-surface)" }}>{s.title}</h4>
                                    <p className="text-xs opacity-50">{s.speaker} · {s.duration}</p>
                                    <p className="text-xs mt-2 line-clamp-2" style={{ color: "var(--faro-on-surface-variant)" }}>{s.excerpt}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                ) : (
                <div className="space-y-3">
                    <div className="flex justify-between items-end">
                        <h2 className="text-lg font-bold" style={{ color: "var(--faro-on-surface)" }}>Nuevos Lanzamientos</h2>
                        <button className="text-xs font-semibold uppercase tracking-wide flex items-center gap-2 opacity-50 hover:opacity-100 transition-opacity">
                            Ver todo <ChevronRight size={16} />
                        </button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
                        {/* Featured Video */}
                        <motion.div
                            whileHover={{ y: -10 }}
                            className="md:col-span-8 rounded-lg overflow-hidden group cursor-pointer relative shadow-xl"
                            style={{ background: "var(--faro-surface-container)" }}
                        >
                            <div className="aspect-video relative overflow-hidden">
                                <Image
                                    src={displayFeatured.thumbnail || displayFeatured.img || "https://picsum.photos/seed/1493225255756-d9584f8606e9/800/600"}
                                    className="object-cover transition-transform duration-700 group-hover:scale-105"
                                    alt="Video thumbnail"
                                    fill
                                />
                                <div className="absolute inset-0" style={{ background: "var(--faro-overlay-bg)" }} />
                                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-500">
                                    <div className="w-20 h-20 rounded-lg backdrop-blur-2xl flex items-center justify-center shadow-2xl"
                                        style={{ background: "var(--faro-hero-bg-light)" }}>
                                        <Play size={32} style={{ color: "var(--faro-on-hero)" }} />
                                    </div>
                                </div>
                                {displayFeatured.series && (
                                    <div className="absolute top-3 left-6 bg-faro-primary text-white font-semibold px-3 py-1.5 rounded-full uppercase tracking-wide">
                                        Serie: {displayFeatured.series}
                                    </div>
                                )}
                            </div>
                            <div className="p-4">
                                <div className="flex items-center gap-4 mb-4 text-[10px] font-semibold uppercase tracking-wide opacity-50">
                                    {displayFeatured.duration && <span>{displayFeatured.duration}</span>}
                                </div>
                                <h3 className="text-xl font-bold mb-4 group-hover:text-faro-primary transition-colors">{displayFeatured.title}</h3>
                                <p className="text-lg opacity-70 line-clamp-2 max-w-2xl">{displayFeatured.excerpt}</p>
                            </div>
                        </motion.div>

                        {/* Secondary Videos */}
                        <div className="md:col-span-4 flex flex-col gap-3">
                            {displaySermons.map((v: SermonItem, i: number) => (
                                <motion.div
                                    key={v.title || i}
                                    whileHover={{ x: 10 }}
                                    className="rounded-lg overflow-hidden group cursor-pointer border"
                                    style={{
                                        background: "var(--faro-surface-container-low)",
                                        borderColor: "var(--faro-outline-variant)"
                                    }}
                                >
                                    <div className="aspect-video relative">
                                        <Image src={v.thumbnail || v.img || "https://picsum.photos/seed/1493225255756-d9584f8606e9/800/600"} alt="Thumbnail" fill className="object-cover group-hover:scale-105 transition-transform" />
                                        <div className="absolute inset-0" style={{ background: "var(--faro-overlay-bg)" }} />
                                        <div className="absolute bottom-4 right-4 text-[10px] px-2 py-1 rounded font-black" style={{ background: "var(--faro-overlay-bg)", color: "var(--faro-on-hero)", backdropFilter: "blur(12px)" }}>{v.duration || "45:00"}</div>
                                    </div>
                                    <div className="p-3">
                                        <h4 className="font-black text-lg mb-2 group-hover:text-faro-primary transition-colors">{v.title}</h4>
                                        <p className="text-xs opacity-50 font-bold uppercase tracking-wide">{v.speaker || v.author || "FARO"}</p>
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    </div>
                </div>
                )}
            </section>
        </main>
    );
}


