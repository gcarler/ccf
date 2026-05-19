"use client";

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    BookOpen, Search, Plus, FileText, 
    ChevronRight,
    Zap, Bookmark, Clock
} from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import Link from 'next/link';

interface WikiDoc {
    id: number;
    page_key: string;
    title: string;
    updated_at: string;
}

export default function WikiHomePage() {
    const { token } = useAuth();
    const [docs, setDocs] = useState<WikiDoc[]>([]);
    const [loading, setLoading] = useState(true);
    const [isQuickAddOpen, setIsQuickAddOpen] = useState(false);
    const [newTitle, setNewTitle] = useState("");
    const [search, setSearch] = useState("");

    useEffect(() => {
        fetchDocs();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [token]);

    const fetchDocs = async () => {
        if (!token) return;
        try {
            const data = await apiFetch<WikiDoc[]>('/content', { token });
            setDocs(Array.isArray(data) ? data.filter((doc) => doc.page_key.includes('wiki')) : []);
        } catch (error) {
            console.error("Error fetching docs:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleCreateDoc = async (e?: React.FormEvent) => {
        if (e) e.preventDefault();
        if (!newTitle.trim() || !token) return;

        try {
            const page_key = `wiki_${newTitle.toLowerCase().replace(/ /g, "-").replace(/[^\w-]+/g, "")}`;
            await apiFetch(`/content/${page_key}`, {
                method: 'POST',
                token,
                body: {
                    title: newTitle,
                    content: "<h1>" + newTitle + "</h1><p>Comienza a escribir aqui...</p>"
                }
            });
            setNewTitle("");
            setIsQuickAddOpen(false);
            fetchDocs();
        } catch (error) {
            console.error("Error creating doc:", error);
        }
    };

    return (
        <div className="flex flex-col h-full bg-[#F8F9FB] dark:bg-[#1E1F21]">
            {/* TOOLBAR */}
            <header className="h-14 border-b border-slate-200/60 dark:border-white/5 flex items-center px-6 gap-4 shrink-0 bg-white dark:bg-[#1E1F21]">
                <div className="flex items-center gap-2 flex-1">
                    <BookOpen size={16} className="text-indigo-600" />
                    <h2 className="text-[11px] font-black uppercase tracking-widest text-slate-400">
                        BASE DE CONOCIMIENTO
                    </h2>
                </div>
                
                <div className="flex items-center gap-2">
                    <div className="relative">
                        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                        <input 
                            type="text" 
                            value={search}
                            onChange={(event) => setSearch(event.target.value)}
                            placeholder="Buscar en la wiki..."
                            className="pl-9 pr-4 py-1.5 bg-slate-100 dark:bg-white/5 border-none rounded-lg text-[12px] focus:ring-2 focus:ring-indigo-500/20 w-64 transition-all"
                        />
                    </div>
                    <button 
                        onClick={() => setIsQuickAddOpen(!isQuickAddOpen)}
                        className="bg-indigo-600 text-white px-4 py-1.5 rounded-lg text-[11px] font-black uppercase tracking-widest shadow-xl shadow-indigo-500/20 hover:bg-indigo-700 active:scale-95 transition-all flex items-center gap-2"
                    >
                        <Plus size={14} />
                        Nuevo Doc
                    </button>
                </div>
            </header>

            {/* QUICK ADD BAR (VIOLET) */}
            <AnimatePresence>
                {isQuickAddOpen && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="bg-blue-50 dark:bg-blue-900/10 border-b-2 border-blue-300 dark:border-blue-500/30 overflow-hidden shrink-0"
                    >
                        <form 
                            onSubmit={handleCreateDoc}
                            className="px-6 py-4 flex items-center gap-4"
                        >
                            <div className="size-8 rounded-lg bg-blue-600 text-white flex items-center justify-center shrink-0">
                                <Zap size={16} />
                            </div>
                            <input 
                                autoFocus
                                value={newTitle}
                                onChange={(e) => setNewTitle(e.target.value)}
                                placeholder="Nombre del documento (Enter para crear...)"
                                className="flex-1 bg-transparent border-none text-[15px] font-bold text-blue-900 dark:text-blue-200 placeholder:text-blue-400 focus:ring-0"
                            />
                        </form>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* CONTENT AREA */}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-8">
                <div className="max-w-7xl mx-auto space-y-8">
                    {/* Featured Section */}
                    <section>
                        <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 mb-6">
                            DOCUMENTOS RECIENTES
                        </p>
                        
                        {loading ? (
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                {[1, 2, 3].map(i => (
                                    <div key={i} className="h-48 bg-white dark:bg-[#252528] rounded-2xl animate-pulse border border-slate-200/70 dark:border-white/5" />
                                ))}
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-4 gap-6">
                                {docs
                                    .filter((doc) => doc.title.toLowerCase().includes(search.trim().toLowerCase()))
                                    .map((doc, index) => (
                                    <motion.div
                                        key={doc.id}
                                        initial={{ opacity: 0, y: 20 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: index * 0.05 }}
                                        className="group relative bg-white dark:bg-[#252528] rounded-2xl border border-slate-200/70 dark:border-white/5 p-6 shadow-sm hover:shadow-2xl transition-all duration-300 cursor-pointer overflow-hidden flex flex-col h-full"
                                    >
                                        {/* Acento de color top */}
                                        <div className="absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-blue-600 to-indigo-600" />
                                        
                                        <div className="flex-1 space-y-4">
                                            <div className="flex items-start justify-between">
                                                <div className="size-10 rounded-xl bg-slate-50 dark:bg-white/5 flex items-center justify-center text-slate-400 group-hover:text-indigo-600 transition-colors">
                                                    <FileText size={20} />
                                                </div>
                                                <button className="p-1 hover:bg-slate-100 dark:hover:bg-white/5 rounded-lg text-slate-400">
                                                    <Bookmark size={14} />
                                                </button>
                                            </div>
                                            
                                            <div>
                                                <h3 className="text-[15px] font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 transition-colors line-clamp-2">
                                                    {doc.title}
                                                </h3>
                                                <p className="text-[12px] text-slate-500 mt-2 line-clamp-3 leading-relaxed">
                                                    Última actualización por Equipo Pastoral. Visualización disponible para todos los roles.
                                                </p>
                                            </div>
                                        </div>

                                        <div className="mt-6 pt-4 border-t border-slate-100 dark:border-white/5 flex items-center justify-between">
                                            <div className="flex items-center gap-1.5 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                                                <Clock size={12} />
                                                <span>{new Date(doc.updated_at).toLocaleDateString()}</span>
                                            </div>
                                            <Link 
                                                href={`/wiki/docs/${doc.page_key}`}
                                                className="text-[10px] font-black uppercase tracking-widest text-indigo-600 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all"
                                            >
                                                EDITAR <ChevronRight size={12} />
                                            </Link>
                                        </div>
                                    </motion.div>
                                ))}
                            </div>
                        )}
                    </section>

                    {/* Empty State */}
                    {!loading && docs.length === 0 && (
                        <div className="py-24 flex flex-col items-center justify-center text-center space-y-4 opacity-50">
                            <div className="size-20 rounded-[2.5rem] bg-white dark:bg-white/5 flex items-center justify-center text-slate-300 shadow-xl">
                                <BookOpen size={40} />
                            </div>
                            <div className="max-w-sm">
                                <p className="font-bold text-lg text-slate-900 dark:text-white">Tu Base de Conocimiento está vacía</p>
                                <p className="text-sm text-slate-500">Crea guías pastorales, manuales de procesos o documentación técnica para tu equipo.</p>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

