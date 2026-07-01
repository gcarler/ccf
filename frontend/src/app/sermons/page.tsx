"use client";

import React, { useState } from 'react';
import Navbar from '@/components/Navbar';
import { motion } from 'framer-motion';
import { Play, Search, Clock, Calendar, Mic, ChevronRight, Filter } from 'lucide-react';

const CATEGORIES = ['Todos', 'Salvación', 'Familia', 'Liderazgo', 'Profecía', 'Adoración', 'Discipulado'];
const SERIES = [
    { id: 1, category: 'Liderazgo', title: 'Levántate y Brilla', thumb: 'from-blue-600 to-sky-700', count: 6 },
    { id: 2, category: 'Familia', title: 'Fundamentos del Hogar', thumb: 'from-rose-500 to-pink-600', count: 8 },
    { id: 3, category: 'Salvación', title: 'El Camino de Regreso', thumb: 'from-amber-500 to-orange-600', count: 4 },
];
const SERMONS = [
    { id: 1, title: 'La Fe que Mueve Montañas', speaker: 'Pastor Samuel Torres', date: '2026-04-06', duration: '45 min', category: 'Fe', views: 1203, series: 'Levántate y Brilla' },
    { id: 2, title: 'Construyendo sobre la Roca', speaker: 'Pastora Ana Gómez', date: '2026-03-30', duration: '52 min', category: 'Familia', views: 890, series: 'Fundamentos del Hogar' },
    { id: 3, title: 'El Poder de la Oración Persistente', speaker: 'Pastor Samuel Torres', date: '2026-03-23', duration: '38 min', category: 'Oración', views: 756, series: null },
    { id: 4, title: 'Identidad en Cristo: Quién eres realmente', speaker: 'Lider Marcos Ruiz', date: '2026-03-16', duration: '41 min', category: 'Identidad', views: 643, series: null },
    { id: 5, title: 'Gracia que Transforma', speaker: 'Pastor Samuel Torres', date: '2026-03-09', duration: '50 min', category: 'Salvación', views: 512, series: 'El Camino de Regreso' },
    { id: 6, title: 'El Espíritu Santo como Guía', speaker: 'Pastora Ana Gómez', date: '2026-03-02', duration: '47 min', category: 'Discipulado', views: 489, series: null },
];

export default function SermonsPage() {
    const [search, setSearch] = useState('');
    const [cat, setCat] = useState('Todos');

    const filtered = SERMONS.filter(s =>
        (cat === 'Todos' || s.category === cat) &&
        s.title.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <main className="min-h-screen bg-[hsl(var(--bg-muted))]">
            <Navbar />
            <div className="pt-28" />

            {/* Hero */}
            <section className="relative py-1.5 px-3 overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-b from-blue-600/10 to-transparent" />
                <div className="max-w-6xl mx-auto relative text-center">
                    <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-blue-500/20 text-[hsl(var(--primary))] text-[11px] font-bold uppercase tracking-wide mb-3">
                        <Mic size={11} /> Prédicas & Mensajes
                    </span>
                    <h1 className="text-xl font-bold text-white mb-3 tracking-tight">
                        La Palabra que<br /><span className="text-[hsl(var(--primary))]">Transforma Vidas</span>
                    </h1>
                    <p className="text-[hsl(var(--text-secondary))] text-lg mb-3 max-w-xl mx-auto">
                        Accede a todas nuestras prédicas, series y mensajes pastorales. Disponibles cuando los necesitas.
                    </p>
                    <div className="max-w-lg mx-auto relative">
                        <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
                        <input value={search} onChange={e => setSearch(e.target.value)}
                            placeholder="Buscar prédica..."
                            className="w-full pl-12 pr-5 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white placeholder:text-[hsl(var(--text-secondary))] text-sm outline-none focus:ring-2 focus:ring-blue-500/30 backdrop-blur" />
                    </div>
                </div>
            </section>

            {/* Series */}
            <section className="max-w-6xl mx-auto px-3 py-1.5">
                <p className="text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Series Destacadas</p>
                <div className="grid grid-cols-3 gap-3 mb-3">
                    {SERIES.map((s, i) => (
                        <motion.div key={s.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }}
                            className={`h-44 rounded-lg bg-gradient-to-br ${s.thumb} relative overflow-hidden cursor-pointer group hover:scale-[1.02] transition-all shadow-2xl`}>
                            <div className="absolute inset-0 bg-black/30" />
                            <div className="absolute inset-0 p-4 flex flex-col justify-end">
                                <span className="text-white/60 text-[10px] font-bold uppercase tracking-wide">{s.category} · {s.count} episodios</span>
                                <p className="text-white font-bold text-lg">{s.title}</p>
                            </div>
                            <div className="absolute top-4 right-4 size-10 rounded-full bg-white/20 backdrop-blur flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all">
                                <ChevronRight size={16} className="text-white" />
                            </div>
                        </motion.div>
                    ))}
                </div>

                {/* Category Filter */}
                <div className="flex items-center gap-2 mb-3 overflow-x-auto pb-2">
                    <Filter size={12} className="text-[hsl(var(--text-secondary))] shrink-0" />
                    {CATEGORIES.map(c => (
                        <button key={c} onClick={() => setCat(c)}
                            className={`px-4 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wide transition-all whitespace-nowrap ${cat === c ? 'bg-[hsl(var(--primary))] text-white' : 'bg-white/5 text-[hsl(var(--text-secondary))] hover:text-white hover:bg-white/10'}`}>
                            {c}
                        </button>
                    ))}
                </div>

                {/* Sermons Grid */}
                <div className="space-y-3">
                    {filtered.map((s, i) => (
                        <motion.div key={s.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.04 }}
                            className="bg-white/5 hover:bg-white/8 border border-white/5 hover:border-white/10 rounded-lg p-3 flex items-center gap-4 cursor-pointer group transition-all">
                            <div className="size-7 rounded-lg bg-blue-600/20 flex items-center justify-center text-[hsl(var(--primary))] shrink-0 group-hover:bg-[hsl(var(--primary))] group-hover:text-white transition-all">
                                <Play size={22} className="ml-0.5" />
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-[13px] font-bold text-white truncate group-hover:text-[hsl(var(--primary))] transition-colors">{s.title}</p>
                                <div className="flex items-center gap-3 mt-1">
                                    <span className="text-[11px] text-[hsl(var(--text-secondary))]">{s.speaker}</span>
                                    <span className="text-[hsl(var(--text-secondary))]">·</span>
                                    <span className="flex items-center gap-1 text-[10px] text-[hsl(var(--text-secondary))]"><Calendar size={9} /> {s.date}</span>
                                    <span className="flex items-center gap-1 text-[10px] text-[hsl(var(--text-secondary))]"><Clock size={9} /> {s.duration}</span>
                                </div>
                                {s.series && <span className="text-[9px] text-blue-500/70 font-bold mt-0.5 block">Serie: {s.series}</span>}
                            </div>
                            <div className="shrink-0 text-right">
                                <p className="text-[10px] text-[hsl(var(--text-secondary))]">{s.views.toLocaleString()} vistas</p>
                                <span className="px-2 py-0.5 mt-1 rounded-full bg-white/5 text-[9px] text-[hsl(var(--text-secondary))] font-bold block">{s.category}</span>
                            </div>
                        </motion.div>
                    ))}
                </div>
            </section>

            <div className="pb-4" />
        </main>
    );
}

