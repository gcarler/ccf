"use client";

import React, { useState } from 'react';
import { SITE_NAME } from '@/lib/site-config';
import { motion } from 'framer-motion';
import { FileText, Play, Clock, Star, Filter, Search, ChevronRight, Lock } from 'lucide-react';
import clsx from 'clsx';

const TUTORIALS = [
    { id: 1, title: `Primeros pasos en ${SITE_NAME}`, category: 'Inicio', duration: '5 min', level: 'Básico', views: 512, rating: 4.9, free: true, thumbnail: 'from-blue-500 to-sky-600' },
    { id: 2, title: 'Cómo usar el CRM Pastoral correctamente', category: 'CRM', duration: '12 min', level: 'Intermedio', views: 341, rating: 4.8, free: true, thumbnail: 'from-sky-500 to-pink-600' },
    { id: 3, title: 'Gestionar el pipeline de consolidación paso a paso', category: 'CRM', duration: '18 min', level: 'Intermedio', views: 289, rating: 4.7, free: false, thumbnail: 'from-emerald-500 to-teal-600' },
    { id: 4, title: 'Crear cursos y contenido en la Academia', category: 'Academia', duration: '22 min', level: 'Avanzado', views: 198, rating: 4.6, free: false, thumbnail: 'from-amber-500 to-orange-600' },
    { id: 5, title: 'Configurar finanzas y transparencia', category: 'Finanzas', duration: '15 min', level: 'Intermedio', views: 167, rating: 4.5, free: true, thumbnail: 'from-rose-500 to-red-600' },
    { id: 6, title: 'Administrar permisos y roles de usuario', category: 'Admin', duration: '10 min', level: 'Avanzado', views: 134, rating: 4.4, free: false, thumbnail: 'from-[hsl(var(--surface-3))] to-[hsl(var(--bg-muted))]' },
];

const LEVEL_COLOR: Record<string, string> = {
    'Básico': 'text-emerald-600 bg-emerald-50 dark:bg-emerald-500/10',
    'Intermedio': 'text-amber-600 bg-amber-50 dark:bg-amber-500/10',
    'Avanzado': 'text-rose-600 bg-rose-50 dark:bg-rose-500/10',
};

export default function SupportTutorialsPage() {
    const [search, setSearch] = useState('');
    const [selectedLevel, setSelectedLevel] = useState<string>('all');

    const filtered = TUTORIALS.filter(t =>
        (selectedLevel === 'all' || t.level === selectedLevel) &&
        t.title.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div className="h-full flex flex-col bg-[hsl(var(--surface-1))] dark:bg-[#0f1117]">
            <header className="h-8 border-b border-[hsl(var(--border))]/60 dark:border-white/5 flex items-center px-3 gap-4 shrink-0 bg-[hsl(var(--bg-primary))] dark:bg-[#1a1d27]">
                <FileText size={16} className="text-sky-500" />
                <h1 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] flex-1">Tutoriales de la Plataforma</h1>
                <div className="relative">
                    <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
                    <input value={search} onChange={e => setSearch(e.target.value)}
                        placeholder="Buscar tutorial..."
                        className="pl-9 pr-4 py-1.5 bg-[hsl(var(--surface-2))] dark:bg-white/5 border-none rounded-md text-[12px] focus:ring-2 focus:ring-sky-500/20 w-56 transition-all text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]" />
                </div>
            </header>

            {/* Level filter */}
            <div className="flex items-center gap-2 px-3 py-3 border-b border-[hsl(var(--border))]/60 dark:border-white/5 bg-[hsl(var(--bg-primary))] dark:bg-[#1a1d27] shrink-0">
                <Filter size={12} className="text-[hsl(var(--text-secondary))]" />
                {['all', 'Básico', 'Intermedio', 'Avanzado'].map(level => (
                    <button key={level} onClick={() => setSelectedLevel(level)}
                        className={clsx("px-3 py-1.5 rounded-md text-[10px] font-semibold uppercase tracking-wide transition-all",
                            selectedLevel === level ? "bg-sky-50 dark:bg-sky-500/10 text-sky-600" : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))]")}>
                        {level === 'all' ? 'Todos' : level}
                    </button>
                ))}
                <span className="ml-auto text-[10px] text-[hsl(var(--text-secondary))]">{filtered.length} tutoriales</span>
            </div>

            <div className="flex-1 overflow-y-auto p-3">
 <div className="w-full grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {filtered.map((t, i) => (
                        <motion.div
                            key={t.id}
                            initial={{ opacity: 0, y: 12 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.05 }}
                            className="bg-[hsl(var(--bg-primary))] dark:bg-[#1a1d27] rounded-lg border border-[hsl(var(--border))]/60 dark:border-white/5 overflow-hidden shadow-sm hover:shadow-xl transition-all cursor-pointer group"
                        >
                            {/* Thumbnail */}
                            <div className={`h-36 bg-gradient-to-br ${t.thumbnail} flex items-center justify-center relative`}>
                                <div className="size-7 rounded-lg bg-white/20 backdrop-blur flex items-center justify-center group-hover:scale-110 transition-all">
                                    <Play size={22} className="text-white ml-0.5" />
                                </div>
                                {!t.free && (
                                    <div className="absolute top-3 left-3 flex items-center gap-1 px-2 py-1 bg-black/40 backdrop-blur rounded-lg text-[9px] text-white font-semibold uppercase tracking-wide">
                                        <Lock size={9} /> Pro
                                    </div>
                                )}
                                <div className="absolute bottom-3 right-3 flex items-center gap-1 px-2 py-1 bg-black/40 backdrop-blur rounded-lg text-[9px] text-white font-bold">
                                    <Clock size={9} /> {t.duration}
                                </div>
                            </div>

                            <div className="p-4 space-y-3">
                                <div className="flex items-center gap-2">
                                    <span className={clsx("px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase tracking-wide", LEVEL_COLOR[t.level])}>
                                        {t.level}
                                    </span>
                                    <span className="text-[9px] text-[hsl(var(--text-secondary))] font-bold">{t.category}</span>
                                </div>
                                <p className="text-[13px] font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] leading-snug group-hover:text-sky-600 transition-colors">
                                    {t.title}
                                </p>
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-1">
                                        <Star size={11} className="text-amber-400 fill-amber-400" />
                                        <span className="text-[11px] font-bold text-[hsl(var(--text-secondary))]">{t.rating}</span>
                                        <span className="text-[10px] text-[hsl(var(--text-secondary))] ml-1">{t.views} vistas</span>
                                    </div>
                                    <ChevronRight size={14} className="text-[hsl(var(--text-secondary))] group-hover:text-sky-500 transition-colors" />
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </div>
            </div>
        </div>
    );
}
