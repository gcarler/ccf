"use client";

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Star, Plus, Loader2, Share2, HeartHandshake } from 'lucide-react';
import { apiFetch } from '@/lib/http';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';

export default function TestimoniesWall() {
    const { isAuthenticated, token } = useAuth();
    const [activeTab, setActiveTab] = useState('Todos');
    const [testimonials, setTestimonials] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchTestimonials = async () => {
            try {
                const data = await apiFetch<any[]>('/cms/testimonials', { token: token || undefined });
                setTestimonials(data);
            } catch (err) {
                console.error('Error fetching testimonials:', err);
            } finally {
                setLoading(false);
            }
        };
        fetchTestimonials();
    }, [token]);

    if (!isAuthenticated) return null;

    const tabs = ['Todos', 'Sanidad', 'Familia', 'Finanzas', 'Salvación', 'Milagro'];

    const filteredTestimonials = testimonials.filter(t => 
        activeTab === 'Todos' || t.emotion === activeTab
    );

    return (
        <div className="p-4 lg:p-4 space-y-3 max-w-5xl mx-auto animate-in fade-in duration-700">
            {/* Header Section */}
            <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-1">
                    <div className="flex items-center gap-2 text-[hsl(var(--primary))] font-semibold uppercase tracking-wide text-[10px]">
                        <Star size={14} className="fill-current shadow-[0_0_8px_currentColor]" />
                        Muro de Milagros
                    </div>
                    <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] tracking-tighter">Testimonios</h1>
                    <p className="text-[hsl(var(--text-secondary))] text-sm font-medium mt-1">Lo que Dios ha hecho, lo volverá a hacer.</p>
                </div>
                
                <Link href="/community/testimonies/publish" className="h-8 px-3 bg-[hsl(var(--primary))] text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-primary/30 hover:bg-[hsl(var(--primary)/0.9)] transition-all active:scale-95 flex items-center gap-3">
                    <Plus size={20} strokeWidth={2.5} />
                    Publicar Milagro
                </Link>
            </header>

            {/* Featured Hero Section - Refined */}
            <motion.div 
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="relative flex flex-col justify-end overflow-hidden rounded-lg min-h-[360px] shadow-2xl group border border-[hsl(var(--border))]"
            >
                <div className="absolute inset-0 bg-cover bg-center transition-transform duration-1000 group-hover:scale-105" style={{ backgroundImage: 'url("https://picsum.photos/seed/1438232992991-995b7058bbb3/800/600")' }}>
                </div>
                <div className="absolute inset-0 bg-gradient-to-t from-[hsl(var(--bg-primary))] via-[hsl(var(--bg-primary)/0.4)] to-transparent"></div>
                <div className="relative p-3 md:p-4">
                    <motion.span 
                        initial={{ x: -20, opacity: 0 }}
                        animate={{ x: 0, opacity: 1 }}
                        transition={{ delay: 0.2 }}
                        className="inline-block bg-[hsl(var(--primary))] px-4 py-1.5 rounded-md text-[10px] font-semibold uppercase tracking-wide text-white mb-4 shadow-lg"
                    >
                        Historias de Fe
                    </motion.span>
                    <motion.h2 
                        initial={{ y: 20, opacity: 0 }}
                        animate={{ y: 0, opacity: 1 }}
                        transition={{ delay: 0.3 }}
                        className="text-[hsl(var(--text-primary))] text-lg md:text-xl font-bold leading-tight tracking-tighter"
                    >
                        Milagros que <br /> Transforman
                    </motion.h2>
                </div>
            </motion.div>

            {/* Content Area */}
            <div className="space-y-3">
                {/* Filter Tabs */}
                <div className="flex gap-4 border-b border-[hsl(var(--border))] px-2 overflow-x-auto hide-scrollbar">
                    {tabs.map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={`pb-4 text-[10px] font-semibold uppercase tracking-wide transition-all relative whitespace-nowrap ${activeTab === tab
                                ? 'text-[hsl(var(--primary))]'
                                : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]'
                                }`}
                        >
                            {tab}
                            {activeTab === tab && (
                                <motion.div 
                                    layoutId="testimony-tab"
                                    className="absolute bottom-[-1px] left-0 right-0 h-0.5 bg-[hsl(var(--primary))] shadow-[0_0_12px_hsl(var(--primary)/0.5)]" 
                                />
                            )}
                        </button>
                    ))}
                </div>

                {/* Testimonies List */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pb-4">
                    <AnimatePresence mode="popLayout">
                        {loading ? (
                            <div className="col-span-full flex flex-col items-center justify-center py-1.5 gap-4">
                                <Loader2 className="w-12 h-8 animate-spin text-[hsl(var(--primary))]" strokeWidth={1.5} />
                                <p className="text-[hsl(var(--text-secondary))] font-semibold uppercase tracking-wide text-[10px]">Cargando Historias...</p>
                            </div>
                        ) : filteredTestimonials.length > 0 ? (
                            filteredTestimonials.map((testimony, idx) => (
                                <motion.article 
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: idx * 0.05 }}
                                    key={testimony.id} 
                                    className="surface-card p-4 bg-[hsl(var(--surface-1))] border-[hsl(var(--border))] hover:border-[hsl(var(--primary)/0.3)] hover:shadow-xl transition-all flex flex-col gap-4"
                                >
                                    <div className="flex justify-between items-start">
                                        <div className="flex items-center gap-4">
                                            <div className="size-9 rounded-lg bg-[hsl(var(--surface-3))] flex items-center justify-center text-[hsl(var(--text-primary))] border border-[hsl(var(--border))] shadow-inner font-black text-xs">
                                                {testimony.author?.username?.substring(0, 2).toUpperCase() || "AN"}
                                            </div>
                                            <div>
                                                <h4 className="text-sm font-bold tracking-tight text-[hsl(var(--text-primary))]">
                                                    {testimony.author?.username || "Anónimo"}
                                                </h4>
                                                <p className="text-[10px] text-[hsl(var(--text-secondary))] font-semibold uppercase tracking-wide mt-0.5 opacity-60">
                                                    {new Date(testimony.created_at).toLocaleDateString()}
                                                </p>
                                            </div>
                                        </div>
                                        {testimony.emotion && (
                                            <span className="font-semibold px-3 py-1 rounded-md tracking-wide">
                                                {testimony.emotion}
                                            </span>
                                        )}
                                    </div>
                                    
                                    <div className="relative flex-1">
                                        <div className="absolute -top-4 -left-2 text-xl text-[hsl(var(--primary)/0.05)] font-serif select-none">&ldquo;</div>
                                        <p className="text-sm leading-relaxed text-[hsl(var(--text-secondary))] font-medium italic relative z-10 pl-6 border-l-2 border-[hsl(var(--primary)/0.2)]">
                                            {testimony.content}
                                        </p>
                                    </div>
                                    
                                    <div className="flex items-center justify-between pt-6 border-t border-[hsl(var(--border))] mt-auto">
                                        <div className="flex gap-4">
                                            <button className="flex items-center gap-2 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors group/btn">
                                                <HeartHandshake size={18} className="group-hover/btn:scale-110 transition-transform" />
                                                <span className="text-[10px] font-semibold uppercase tracking-wide">Amén</span>
                                            </button>
                                            <button className="flex items-center gap-2 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors">
                                                <Share2 size={18} />
                                                <span className="text-[10px] font-semibold uppercase tracking-wide">Compatir</span>
                                            </button>
                                        </div>
                                    </div>
                                </motion.article>
                            ))
                        ) : (
                            <div className="col-span-full text-center py-1.5 bg-[hsl(var(--surface-2))] rounded-lg border border-dashed border-[hsl(var(--border))]">
                                <p className="text-[hsl(var(--text-secondary))] font-semibold uppercase tracking-wide text-[10px]">No hay testimonios en esta categoría.</p>
                                <p className="text-[hsl(var(--text-secondary))] text-[12px] mt-2 font-medium opacity-60">¡Sé el primero en compartir lo que Dios ha hecho!</p>
                            </div>
                        )}
                    </AnimatePresence>
                </div>
            </div>
        </div>
    );
}

