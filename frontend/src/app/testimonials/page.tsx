"use client";

import React, { useEffect, useState } from 'react';
import Navbar from '@/components/Navbar';
import { motion } from 'framer-motion';
import { Heart, Search, User } from 'lucide-react';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { apiFetch } from '@/lib/http';

interface Testimonial {
    id: number;
    content: string;
    emotion?: string;
    author?: { id: number; username: string } | null;
    is_approved?: boolean;
    show_on_home?: boolean;
    created_at?: string;
}

export default function TestimonialsPage() {
    const [testimonials, setTestimonials] = useState<Testimonial[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [cat, setCat] = useState('Todos');
    const [selected, setSelected] = useState<Testimonial | null>(null);

    useEffect(() => {
        apiFetch<Testimonial[]>("/cms/testimonials")
            .then((data) => setTestimonials(Array.isArray(data) ? data : []))
            .catch(() => setTestimonials([]))
            .finally(() => setLoading(false));
    }, []);

    const categories = ['Todos', ...Array.from(new Set(testimonials.map((t) => t.emotion || 'General')))];

    const filtered = testimonials.filter((t) => {
        const matchesCat = cat === 'Todos' || (t.emotion || 'General') === cat;
        const matchesSearch = (t.author?.username || '').toLowerCase().includes(search.toLowerCase()) ||
            t.content.toLowerCase().includes(search.toLowerCase());
        return matchesCat && matchesSearch;
    });

    return (
        <main className="min-h-screen bg-slate-950">
            <Navbar />
            <div className="pt-28" />

            {/* Hero */}
            <section className="py-20 px-6 text-center relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-b from-rose-600/10 to-transparent pointer-events-none" />
                <div className="max-w-4xl mx-auto relative">
                    <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-rose-500/20 text-rose-400 text-[11px] font-black uppercase tracking-widest mb-6">
                        <Heart size={11} /> Historias Reales
                    </span>
                    <h1 className="text-5xl font-black text-white mb-4 tracking-tight">
                        Vidas que han sido<br /><span className="text-rose-400">Transformadas</span>
                    </h1>
                    <p className="text-slate-400 text-lg mb-8 max-w-xl mx-auto">
                        Miles de personas han experimentado el poder de Dios en su vida. Estas son algunas de sus historias.
                    </p>
                    <div className="max-w-lg mx-auto relative">
                        <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" />
                        <input value={search} onChange={e => setSearch(e.target.value)}
                            placeholder="Buscar testimonio..."
                            className="w-full pl-12 pr-5 py-4 rounded-2xl bg-white/5 border border-white/10 text-white placeholder:text-slate-500 text-[14px] outline-none focus:ring-2 focus:ring-rose-500/30 backdrop-blur" />
                    </div>
                </div>
            </section>

            {loading ? (
                <div className="max-w-6xl mx-auto px-6 pb-20 text-center">
                    <p className="text-slate-400">Cargando testimonios...</p>
                </div>
            ) : testimonials.length === 0 ? (
                <div className="max-w-6xl mx-auto px-6 pb-20 text-center">
                    <p className="text-slate-400 text-lg">Aún no hay testimonios publicados.</p>
                </div>
            ) : (
                <>
                    {/* Category Filter */}
                    <div className="max-w-6xl mx-auto px-6 flex items-center gap-2 flex-wrap mb-8">
                        {categories.map(c => (
                            <button key={c} onClick={() => setCat(c)}
                                className={`px-4 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${cat === c ? 'bg-rose-600 text-white' : 'bg-white/5 text-slate-400 hover:text-white hover:bg-white/10'}`}>
                                {c}
                            </button>
                        ))}
                    </div>

                    {/* Grid */}
                    <div className="max-w-6xl mx-auto px-6 pb-20">
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {filtered.map((t, i) => (
                                <motion.div key={t.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
                                    className="bg-white/5 hover:bg-white/8 border border-white/5 hover:border-rose-500/20 rounded-3xl p-6 cursor-pointer group transition-all hover:shadow-xl hover:shadow-rose-500/5"
                                    onClick={() => setSelected(t)}>
                                    <div className="text-4xl text-rose-500/30 font-black leading-none mb-3">&quot;</div>
                                    <p className="text-[13px] text-slate-300 leading-relaxed line-clamp-4 mb-5 group-hover:text-white transition-colors">
                                        {t.content}
                                    </p>
                                    <div className="flex items-center gap-3">
                                        <div className="size-10 rounded-xl bg-gradient-to-br from-rose-500/20 to-pink-500/20 flex items-center justify-center text-rose-400 text-sm font-black shrink-0">
                                            <User size={16} />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-[12px] font-bold text-white truncate">{t.author?.username || 'Anónimo'}</p>
                                        </div>
                                        <div className="flex flex-col items-end gap-1">
                                            <span className="text-[9px] px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-400 font-black uppercase tracking-widest">{t.emotion || 'General'}</span>
                                        </div>
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    </div>
                </>
            )}

            {/* DRAWER Detail */}
            <WorkspaceDrawer
                isOpen={!!selected}
                onClose={() => setSelected(null)}
                title="Testimonio"
                subtitle={selected?.author?.username || ""}
            >
                {selected && (
                    <div className="space-y-8 mt-4">
                        <div className="text-5xl text-rose-500/30 font-black leading-none">&quot;</div>
                        <p className="text-slate-700 dark:text-slate-200 text-[15px] leading-relaxed">{selected.content}</p>
                        <div className="flex items-center gap-4">
                            <div className="size-14 rounded-2xl bg-gradient-to-br from-rose-500/20 to-pink-500/20 flex items-center justify-center text-rose-400">
                                <User size={24} />
                            </div>
                            <div>
                                <p className="font-bold text-slate-800 dark:text-white text-base">{selected.author?.username || 'Anónimo'}</p>
                                <span className="text-[9px] px-2 py-0.5 rounded-full bg-rose-50 dark:bg-rose-500/20 text-rose-600 dark:text-rose-400 font-black uppercase tracking-widest mt-1 inline-block">{selected.emotion || 'General'}</span>
                            </div>
                        </div>
                    </div>
                )}
            </WorkspaceDrawer>
        </main>
    );
}
