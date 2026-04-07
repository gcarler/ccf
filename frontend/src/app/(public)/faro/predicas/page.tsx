"use client";

import React from "react";
import { motion } from "framer-motion";
import Image from "next/image";
import { PlayCircle, Clock, ChevronRight, Bookmark, Share2, Play } from "lucide-react";
import { useContentBlock } from "@/hooks/useContent";

export default function PredicasPage() {
    const { data: heroContent } = useContentBlock("faro_sermons_hero");
    const { data: sermonsContent } = useContentBlock("faro_sermons_feed");
    
    const heroEyebrow = heroContent?.eyebrow || "Mensaje Destacado";
    const heroTitleLead = heroContent?.title_lead || "Alimento para el";
    const heroAccent = heroContent?.title_accent || "Alma";
    const heroDescription = heroContent?.description || "Explora nuestra biblioteca de mensajes que iluminan el camino. Una guía espiritual diseñada para nutrir tu fe.";

    const fallbackSermons = [
        { title: "La paz que sobrepasa entendimiento", img: "https://images.unsplash.com/photo-1490730141103-6cac27aaab94?w=600&q=80", author: "Pr. David Miller", duration: "32 min" },
        { title: "Principios de sabiduría eterna", img: "https://images.unsplash.com/photo-1504052434569-70ad5836ab65?w=600&q=80", author: "Dra. Sarah Jenkins", duration: "45 min" }
    ];

    const sermons = (Array.isArray(sermonsContent?.parsed) && sermonsContent.parsed.length > 0 
        ? sermonsContent.parsed 
        : fallbackSermons) as any[];

    const featuredSermon = sermons.find(s => s.featured) || {
        title: "Encontrando luz en el desierto",
        speaker: "Pr. David Mendoza",
        duration: "45 min",
        series: "Renacer",
        thumbnail: "https://images.unsplash.com/photo-1493225255756-d9584f8606e9?w=1000&q=80"
    };

    const secondarySermons = sermons.filter(s => !s.featured).slice(0, 4);
    return (
        <main className="pt-[88px] bg-faro-surface">
            {/* ── HERO CINEMATOGRÁFICO ─────────────────────────── */}
            <section className="relative min-h-[80vh] flex items-end overflow-hidden">
                <div className="absolute inset-0">
                    <Image 
                        src="https://images.unsplash.com/photo-1507692049790-de58290a4334?w=1600&q=80" 
                        alt="Background"
                        fill
                        className="object-cover scale-105"
                        style={{ filter: "brightness(0.3) saturate(0.8)" }}
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-faro-surface via-transparent to-transparent" />
                    <div className="absolute inset-0 bg-gradient-to-r from-faro-surface/60 via-transparent to-transparent" />
                </div>

                <div className="relative z-10 max-w-6xl mx-auto px-6 md:px-16 lg:px-24 pb-20 w-full">
                    <motion.div
                        initial={{ opacity: 0, y: 30 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="max-w-3xl"
                    >
                        <div className="flex items-center gap-4 mb-6">
                            <span className="w-12 h-0.5 bg-faro-primary" />
                            <span className="text-xs font-black uppercase tracking-[0.4em]" style={{ color: "var(--faro-primary)" }}>
                                {heroEyebrow}
                            </span>
                        </div>
                        <h1 
                            className="font-black tracking-tighter leading-[0.9] mb-8"
                            style={{ 
                                fontSize: "clamp(3.5rem, 8vw, 7rem)",
                                color: "white"
                            }}
                        >
                            {heroTitleLead} <br/>
                            <span className="italic" style={{ color: "var(--faro-primary)" }}>{heroAccent}.</span>
                        </h1>
                        <p className="text-xl md:text-2xl opacity-70 mb-10 leading-relaxed" style={{ color: "white" }}>
                            {heroDescription}
                        </p>
                        <div className="flex flex-wrap gap-4">
                            <button 
                                className="flex items-center gap-3 px-10 py-5 rounded-2xl font-black text-sm uppercase tracking-widest text-white transition-all hover:scale-105 shadow-2xl"
                                style={{ background: "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary))" }}
                            >
                                <Play fill="currentColor" size={18} />
                                Ver ahora
                            </button>
                            <button className="flex items-center gap-3 px-10 py-5 rounded-2xl font-black text-sm uppercase tracking-widest bg-white/10 backdrop-blur-xl border border-white/20 text-white transition-all hover:bg-white/20">
                                <Bookmark size={18} />
                                Mi lista
                            </button>
                        </div>
                    </motion.div>
                </div>
            </section>

            {/* ── FILTROS Y CATEGORÍAS ───────────────────────── */}
            <section className="px-6 md:px-16 lg:px-24 -mt-10 relative z-20">
                <div 
                    className="rounded-[2.5rem] p-8 flex flex-col md:flex-row items-center justify-between gap-8 border backdrop-blur-3xl shadow-2xl"
                    style={{ 
                        background: "var(--faro-surface-container-highest)",
                        borderColor: "var(--faro-outline-variant)",
                        opacity: 0.95
                    }}
                >
                    <div className="flex flex-wrap justify-center gap-8 text-[10px] font-black uppercase tracking-[0.3em]">
                        {["Todas", "Series", "Oradores", "Temas"].map((cat, i) => (
                            <button key={cat} className={`transition-all hover:text-faro-primary ${i === 0 ? "text-faro-primary" : "opacity-50"}`}>
                                {cat}
                            </button>
                        ))}
                    </div>
                    <div className="w-full md:w-auto">
                        <select className="w-full md:w-64 bg-faro-surface-container-low rounded-xl px-4 py-3 text-xs font-black uppercase tracking-widest outline-none border border-transparent focus:border-faro-primary/30">
                            <option>Más recientes</option>
                            <option>Más vistos</option>
                            <option>Populares</option>
                        </select>
                    </div>
                </div>
            </section>

            {/* ── GALERÍA DE VÍDEOS ──────────────────────────── */}
            <section className="py-24 px-6 md:px-16 lg:px-24">
                <div className="max-w-7xl mx-auto space-y-16">
                    <div className="flex justify-between items-end">
                        <h2 className="text-4xl font-black" style={{ color: "var(--faro-on-surface)" }}>Nuevos Lanzamientos</h2>
                        <button className="text-xs font-black uppercase tracking-widest flex items-center gap-2 opacity-50 hover:opacity-100 transition-opacity">
                            Ver todo <ChevronRight size={16} />
                        </button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-12 gap-8">
                        {/* Featured Video */}
                        <motion.div 
                            whileHover={{ y: -10 }}
                            className="md:col-span-8 rounded-[3rem] overflow-hidden group cursor-pointer relative shadow-xl"
                            style={{ background: "var(--faro-surface-container)" }}
                        >
                            <div className="aspect-video relative overflow-hidden">
                                <Image 
                                    src="https://images.unsplash.com/photo-1493225255756-d9584f8606e9?w=1000&q=80" 
                                    className="object-cover transition-transform duration-700 group-hover:scale-105"
                                    alt="Video thumbnail"
                                    fill
                                />
                                <div className="absolute inset-0 bg-black/40 group-hover:bg-black/20 transition-colors" />
                                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-500">
                                    <div className="w-20 h-20 rounded-3xl bg-white/20 backdrop-blur-2xl flex items-center justify-center shadow-2xl">
                                        <Play fill="white" size={32} className="text-white" />
                                    </div>
                                </div>
                                <div className="absolute top-6 left-6 bg-faro-primary text-white text-[9px] font-black px-3 py-1.5 rounded-full uppercase tracking-widest">Estreno</div>
                            </div>
                            <div className="p-10">
                                <div className="flex items-center gap-4 mb-4 text-[10px] font-black uppercase tracking-widest opacity-50">
                                    <span style={{ color: "var(--faro-primary)" }}>Serie: {featuredSermon.series || "FARO"}</span>
                                    <span>•</span>
                                    <span>{featuredSermon.duration || "45 MIN"}</span>
                                </div>
                                <h3 className="text-3xl font-black mb-4 group-hover:text-faro-primary transition-colors">{featuredSermon.title}</h3>
                                <p className="text-lg opacity-70 line-clamp-2 max-w-2xl">{featuredSermon.excerpt || "Un mensaje profundo sobre la fe y la perseverancia cuando los caminos parecen cerrarse."}</p>
                            </div>
                        </motion.div>

                        {/* Secondary Videos */}
                        <div className="md:col-span-4 flex flex-col gap-8">
                            {secondarySermons.map((v: any, i: number) => (
                                <motion.div 
                                    key={i}
                                    whileHover={{ x: 10 }}
                                    className="rounded-[2.5rem] overflow-hidden group cursor-pointer border"
                                    style={{ 
                                        background: "var(--faro-surface-container-low)",
                                        borderColor: "var(--faro-outline-variant)"
                                    }}
                                >
                                    <div className="aspect-video relative">
                                        <Image src={v.thumbnail || v.img || "https://images.unsplash.com/photo-1493225255756-d9584f8606e9?w=1000&q=80"} alt="Thumbnail" fill className="object-cover group-hover:scale-105 transition-transform" />
                                        <div className="absolute inset-0 bg-black/20" />
                                        <div className="absolute bottom-4 right-4 bg-black/60 backdrop-blur-md text-[10px] px-2 py-1 rounded text-white font-black">{v.duration || "45:00"}</div>
                                    </div>
                                    <div className="p-6">
                                        <h4 className="font-black text-lg mb-2 group-hover:text-faro-primary transition-colors">{v.title}</h4>
                                        <p className="text-xs opacity-50 font-bold uppercase tracking-widest">{v.speaker || v.author}</p>
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
