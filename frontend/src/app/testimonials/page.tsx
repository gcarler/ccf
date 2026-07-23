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
        <main className="min-h-screen bg-[hsl(var(--bg-muted))]">
            <Navbar />
            <div className="pt-28" />

            {/* Hero */}
            <section className="py-1.5 px-3 text-center relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-b to-[hsl(var(--danger)/10%)] to-transparent pointer-events-none" />
                <div className="max-w-4xl mx-auto relative">
                    <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[hsl(var(--danger))]/20 text-[hsl(var(--danger))] text-[11px] font-bold uppercase tracking-wide mb-3">
                        <Heart size={11} /> Historias Reales
                    </span>
                    <h1 className="text-xl font-bold text-white mb-3 tracking-tight">
                        Vidas que han sido<br /><span className="text-[hsl(var(--danger))]">Transformadas</span>
                    </h1>
                    <p className="text-[hsl(var(--text-secondary))] text-lg mb-3 max-w-xl mx-auto">
                        Miles de personas han experimentado el poder de Dios en su vida. Estas son algunas de sus historias.
                    </p>
                    <div className="max-w-lg mx-auto relative">
                        <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
                        <input value={search} onChange={e => setSearch(e.target.value)}
                            placeholder="Buscar testimonio..."
                            className="w-full pl-12 pr-5 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white placeholder:text-[hsl(var(--text-secondary))] text-sm outline-none focus:ring-2 focus:ring-[hsl(var(--danger)/30%)] backdrop-blur" />
                    </div>
                </div>
            </section>

            {loading ? (
                <div className="max-w-6xl mx-auto px-3 pb-4 text-center">
                    <p className="text-[hsl(var(--text-secondary))]">Cargando testimonios...</p>
                </div>
            ) : testimonials.length === 0 ? (
                <div className="max-w-6xl mx-auto px-3 pb-4 text-center">
                    <p className="text-[hsl(var(--text-secondary))] text-lg">Aún no hay testimonios publicados.</p>
                </div>
            ) : (
                <>
                    {/* Category Filter */}
                    <div className="max-w-6xl mx-auto px-3 flex items-center gap-2 flex-wrap mb-3">
                        {categories.map(c => (
                            <button key={c} onClick={() => setCat(c)}
                                className={`px-4 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wide transition-all ${cat === c ? 'bg-[hsl(var(--danger))] text-white' : 'bg-white/5 text-[hsl(var(--text-secondary))] hover:text-white hover:bg-white/10'}`}>
                                {c}
                            </button>
                        ))}
                    </div>

                    {/* Grid */}
                    <div className="max-w-6xl mx-auto px-3 pb-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                            {filtered.map((t, i) => (
                                <motion.div key={t.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
                                    className="bg-white/5 hover:bg-white/8 border border-white/5 hover:border-[hsl(var(--danger)/100%)]/20 rounded-lg p-3 cursor-pointer group transition-all hover:shadow-xl hover:shadow-[hsl(var(--danger)/5%)]"
                                    onClick={() => setSelected(t)}>
                                    <div className="text-xl text-[hsl(var(--danger))]/30 font-bold leading-none mb-3">&quot;</div>
                                    <p className="text-[13px] text-[hsl(var(--text-secondary))] leading-relaxed line-clamp-4 mb-5 group-hover:text-white transition-colors">
                                        {t.content}
                                    </p>
                                    <div className="flex items-center gap-3">
                                        <div className="size-10 rounded-md bg-gradient-to-br to-[hsl(var(--danger)/20%)] to-[hsl(var(--domain-pink)/20%)] flex items-center justify-center text-[hsl(var(--danger))] text-sm font-semibold shrink-0">
                                            <User size={16} />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-[12px] font-bold text-white truncate">{t.author?.username || 'Anónimo'}</p>
                                        </div>
                                        <div className="flex flex-col items-end gap-1">
                                            <span className="text-[9px] px-2 py-0.5 rounded-full bg-[hsl(var(--danger))]/20 text-[hsl(var(--danger))] font-bold uppercase tracking-wide">{t.emotion || 'General'}</span>
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
                    <div className="space-y-3 mt-4">
                        <div className="text-xl text-[hsl(var(--danger))]/30 font-bold leading-none">&quot;</div>
                        <p className="text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] text-sm leading-relaxed">{selected.content}</p>
                        <div className="flex items-center gap-4">
                            <div className="size-7 rounded-lg bg-gradient-to-br to-[hsl(var(--danger)/20%)] to-[hsl(var(--domain-pink)/20%)] flex items-center justify-center text-[hsl(var(--danger))]">
                                <User size={24} />
                            </div>
                            <div>
                                <p className="font-bold text-[hsl(var(--text-primary))] dark:text-white text-base">{selected.author?.username || 'Anónimo'}</p>
                                <span className="text-[9px] px-2 py-0.5 rounded-full bg-danger-soft dark:bg-[hsl(var(--danger))]/20 text-danger-text dark:text-[hsl(var(--danger))] font-bold uppercase tracking-wide mt-1 inline-block">{selected.emotion || 'General'}</span>
                            </div>
                        </div>
                    </div>
                )}
            </WorkspaceDrawer>
        </main>
    );
}
