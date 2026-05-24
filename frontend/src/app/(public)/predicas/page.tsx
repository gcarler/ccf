"use client";

import React from "react";
import { motion } from "framer-motion";
import Image from "next/image";
import { ChevronRight, Bookmark, Play } from "lucide-react";
import { useContentBlock } from "@/hooks/useContent";

export default function PredicasPage() {
    const { data: heroContent } = useContentBlock("faro_sermons_hero");
    const { data: sermonsContent } = useContentBlock("faro_sermons_feed");
    
    const heroEyebrow = heroContent?.eyebrow || "Mensaje Destacado";
    const heroTitleLead = heroContent?.title_lead || "Alimento para el";
    const heroAccent = heroContent?.title_accent || "Alma";
    const heroDescription = heroContent?.description || "Explora nuestra biblioteca de mensajes que iluminan el camino. Una guía espiritual diseñada para nutrir tu fe.";

    interface SermonItem {
        title?: string;
        img?: string;
        thumbnail?: string;
        author?: string;
        speaker?: string;
        duration?: string;
        series?: string;
        excerpt?: string;
        featured?: boolean;
    }

    const sermons: SermonItem[] = Array.isArray(sermonsContent?.parsed) && sermonsContent.parsed.length > 0 
        ? sermonsContent.parsed as SermonItem[]
        : [];

    const featuredSermon = sermons.find((s) => s.featured);

    const secondarySermons = sermons.filter((s) => !s.featured).slice(0, 4);
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
                            <button className="flex items-center gap-3 px-4 py-2 rounded-lg font-black text-sm uppercase tracking-wide transition-all hover:scale-105 shadow-2xl"
                                style={{ background: "var(--faro-hero-cta-gradient)", color: "var(--faro-on-hero)" }}
                            >
                                <Play fill="currentColor" size={18} />
                                Ver ahora
                            </button>
                            <button className="flex items-center gap-3 px-4 py-2 rounded-lg font-black text-sm uppercase tracking-wide transition-all hover:scale-105"
                                style={{
                                    background: "var(--faro-hero-bg-light)",
                                    backdropFilter: "blur(20px)",
                                    border: "1px solid var(--faro-hero-border-light)",
                                    color: "var(--faro-on-hero)",
                                }}>
                                <Bookmark size={18} />
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
                        {["Todas", "Series", "Oradores", "Temas"].map((cat, i) => (
                            <button key={cat} className={`transition-all hover:text-faro-primary ${i === 0 ? "text-faro-primary" : "opacity-50"}`}>
                                {cat}
                            </button>
                        ))}
                    </div>
                    <div className="w-full md:w-auto">
                        <select className="w-full md:w-64 bg-faro-surface-container-low rounded-md px-4 py-3 text-xs font-semibold uppercase tracking-wide outline-none border border-transparent focus:border-faro-primary/30">
                            <option>Más recientes</option>
                            <option>Más vistos</option>
                            <option>Populares</option>
                        </select>
                    </div>
                </div>
            </section>

            {/* ── GALERÍA DE VÍDEOS ──────────────────────────── */}
            <section className="py-1.5 px-3 md:px-4 lg:px-8 xl:px-12">
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
                                    src="https://picsum.photos/seed/1493225255756-d9584f8606e9/800/600" 
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
                                <div className="absolute top-3 left-6 bg-faro-primary text-white font-semibold px-3 py-1.5 rounded-full uppercase tracking-wide">Estreno</div>
                            </div>
                            <div className="p-4">
                                <div className="flex items-center gap-4 mb-4 text-[10px] font-semibold uppercase tracking-wide opacity-50">
                                    <span style={{ color: "var(--faro-primary)" }}>Serie: {featuredSermon?.series ?? ""}</span>
                                    <span>•</span>
                                    <span>{featuredSermon?.duration ?? ""}</span>
                                </div>
                                <h3 className="text-xl font-bold mb-4 group-hover:text-faro-primary transition-colors">{featuredSermon?.title ?? ""}</h3>
                                <p className="text-lg opacity-70 line-clamp-2 max-w-2xl">{featuredSermon?.excerpt ?? ""}</p>
                            </div>
                        </motion.div>

                        {/* Secondary Videos */}
                        <div className="md:col-span-4 flex flex-col gap-3">
                            {secondarySermons.map((v: SermonItem, i: number) => (
                                <motion.div 
                                    key={i}
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
                                        <p className="text-xs opacity-50 font-bold uppercase tracking-wide">{v.speaker || v.author}</p>
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    </div>
                </div>
            </section>
        </main>
    );
}


