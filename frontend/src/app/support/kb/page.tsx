"use client";

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Book, Search, ChevronRight, Star, TrendingUp, BookOpen, Zap, Users, Layout, FileText } from 'lucide-react';
import clsx from 'clsx';

const CATEGORIES = [
    { id: 'getting-started', label: 'Primeros Pasos', icon: Zap, color: 'text-amber-500 bg-amber-50 dark:bg-amber-500/10', count: 12 },
    { id: 'crm', label: 'CRM Pastoral', icon: Users, color: 'text-blue-500 bg-blue-50 dark:bg-blue-500/10', count: 18 },
    { id: 'academy', label: 'Academia CCF', icon: BookOpen, color: 'text-purple-500 bg-purple-50 dark:bg-purple-500/10', count: 9 },
    { id: 'projects', label: 'Proyectos', icon: Layout, color: 'text-emerald-500 bg-emerald-50 dark:bg-emerald-500/10', count: 7 },
    { id: 'finances', label: 'Finanzas', icon: TrendingUp, color: 'text-rose-500 bg-rose-50 dark:bg-rose-500/10', count: 5 },
    { id: 'admin', label: 'Configuración', icon: FileText, color: 'text-slate-500 bg-slate-100 dark:bg-white/5', count: 14 },
];

const POPULAR_ARTICLES = [
    { id: 1, title: '¿Cómo registrar un nuevo miembro en el CRM?', category: 'CRM Pastoral', views: 342, helpful: 98 },
    { id: 2, title: 'Configurar tu primer pipeline de consolidación', category: 'CRM Pastoral', views: 289, helpful: 95 },
    { id: 3, title: 'Crear y publicar un curso en Academia CCF', category: 'Academia CCF', views: 201, helpful: 91 },
    { id: 4, title: 'Gestionar permisos y roles de usuario', category: 'Configuración', views: 178, helpful: 88 },
    { id: 5, title: 'Exportar reportes de asistencia en formato Excel', category: 'CRM Pastoral', views: 156, helpful: 85 },
];

export default function SupportKBPage() {
    const [search, setSearch] = useState('');
    const [selectedCat, setSelectedCat] = useState<string | null>(null);

    return (
        <div className="h-full flex flex-col bg-slate-50 dark:bg-[#0f1117]">
            {/* Hero Search */}
            <div className="bg-gradient-to-br from-blue-600 to-indigo-700 p-12 text-center relative overflow-hidden">
                <div className="absolute inset-0 opacity-10" style={{ backgroundImage: "radial-gradient(circle at 50% 0%, white 0%, transparent 60%)" }} />
                <div className="relative">
                    <Book size={32} className="text-white/60 mx-auto mb-4" />
                    <h1 className="text-2xl font-black text-white mb-2">Base de Conocimientos</h1>
                    <p className="text-blue-200 text-sm mb-6">Encuentra respuestas a todas tus preguntas sobre la plataforma CCF</p>
                    <div className="max-w-lg mx-auto relative">
                        <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                        <input
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            placeholder="Buscar artículos, guías, tutoriales..."
                            className="w-full pl-12 pr-5 py-4 rounded-2xl bg-white shadow-2xl text-[14px] text-slate-700 outline-none focus:ring-2 focus:ring-blue-400/40 font-medium"
                        />
                    </div>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto p-8">
                <div className="max-w-5xl mx-auto space-y-10">
                    {/* Categories */}
                    <section>
                        <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-5">Explorar por Categoría</p>
                        <div className="grid grid-cols-3 gap-4">
                            {CATEGORIES.map((cat, i) => (
                                <motion.button
                                    key={cat.id}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: i * 0.04 }}
                                    onClick={() => setSelectedCat(selectedCat === cat.id ? null : cat.id)}
                                    className={clsx(
                                        "flex items-center gap-4 p-5 rounded-2xl border transition-all text-left shadow-sm group",
                                        selectedCat === cat.id
                                            ? "border-blue-500 bg-blue-50 dark:bg-blue-500/10"
                                            : "border-slate-200/60 dark:border-white/5 bg-white dark:bg-[#1a1d27] hover:shadow-md"
                                    )}
                                >
                                    <div className={clsx("size-11 rounded-xl flex items-center justify-center shrink-0", cat.color)}>
                                        <cat.icon size={20} />
                                    </div>
                                    <div>
                                        <p className="text-[13px] font-bold text-slate-700 dark:text-slate-200">{cat.label}</p>
                                        <p className="text-[10px] text-slate-400">{cat.count} artículos</p>
                                    </div>
                                </motion.button>
                            ))}
                        </div>
                    </section>

                    {/* Popular Articles */}
                    <section>
                        <div className="flex items-center gap-2 mb-5">
                            <Star size={14} className="text-amber-500" />
                            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Artículos más Populares</p>
                        </div>
                        <div className="bg-white dark:bg-[#1a1d27] rounded-2xl border border-slate-200/60 dark:border-white/5 shadow-sm divide-y divide-slate-100 dark:divide-white/5 overflow-hidden">
                            {POPULAR_ARTICLES.map((article, i) => (
                                <motion.div
                                    key={article.id}
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    transition={{ delay: 0.2 + i * 0.04 }}
                                    className="flex items-center gap-4 px-5 py-4 hover:bg-slate-50 dark:hover:bg-white/5 transition-all cursor-pointer group"
                                >
                                    <div className="size-8 rounded-lg bg-slate-100 dark:bg-white/5 flex items-center justify-center text-[13px] font-black text-slate-400">
                                        {i + 1}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-[13px] font-semibold text-slate-700 dark:text-slate-200 truncate group-hover:text-blue-600 transition-colors">
                                            {article.title}
                                        </p>
                                        <div className="flex items-center gap-3 mt-0.5">
                                            <span className="text-[10px] text-slate-400">{article.category}</span>
                                            <span className="text-[10px] text-slate-300">·</span>
                                            <span className="text-[10px] text-slate-400">{article.views} vistas</span>
                                            <span className="text-[10px] text-emerald-500 font-bold">{article.helpful}% útil</span>
                                        </div>
                                    </div>
                                    <ChevronRight size={14} className="text-slate-300 group-hover:text-blue-500 transition-colors shrink-0" />
                                </motion.div>
                            ))}
                        </div>
                    </section>
                </div>
            </div>
        </div>
    );
}

