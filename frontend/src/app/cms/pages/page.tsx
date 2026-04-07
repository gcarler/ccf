"use client";

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    FileText, Search, Plus, MoreVertical, 
    Edit2, Trash2, Globe, Lock, ChevronRight,
    Zap, Calendar
} from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import SidePanel from '@/components/ui/SidePanel';
import clsx from 'clsx';

interface PageItem {
    id: number;
    page_key: string;
    title: string;
    updated_at: string;
}

export default function CmsPagesManagement() {
    const { token } = useAuth();
    const [pages, setPages] = useState<PageItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [isQuickAddOpen, setIsQuickAddOpen] = useState(false);
    const [newTitle, setNewTitle] = useState("");
    const [selectedPage, setSelectedPage] = useState<PageItem | null>(null);

    useEffect(() => {
        fetchPages();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [token]);

    const fetchPages = async () => {
        if (!token) return;
        try {
            const data = await apiFetch<PageItem[]>('/cms/pages', { token });
            setPages(Array.isArray(data) ? data : []);
        } catch (error) {
            console.error("Error fetching pages:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleCreatePage = async (e?: React.FormEvent) => {
        if (e) e.preventDefault();
        if (!newTitle.trim() || !token) return;

        try {
            const page_key = newTitle.toLowerCase().replace(/ /g, "-").replace(/[^\w-]+/g, "");
            await apiFetch('/cms/pages', {
                method: 'POST',
                token,
                body: JSON.stringify({
                    title: newTitle,
                    page_key,
                    content: "# " + newTitle + "\n\nNueva página creada."
                })
            });
            setNewTitle("");
            setIsQuickAddOpen(false);
            fetchPages();
        } catch (error) {
            console.error("Error creating page:", error);
        }
    };

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#141517]">
            {/* TOOLBAR */}
            <header className="h-14 border-b border-slate-100 dark:border-white/5 flex items-center px-6 gap-4 shrink-0">
                <div className="flex items-center gap-2 flex-1">
                    <FileText size={16} className="text-blue-600" />
                    <h2 className="text-[11px] font-black uppercase tracking-widest text-slate-400">
                        GESTIÓN DE PÁGINAS
                    </h2>
                </div>
                
                <div className="flex items-center gap-2">
                    <div className="relative">
                        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                        <input 
                            type="text" 
                            placeholder="Buscar páginas..."
                            className="pl-9 pr-4 py-1.5 bg-slate-100 dark:bg-white/5 border-none rounded-lg text-[12px] focus:ring-2 focus:ring-blue-500/20 w-64 transition-all"
                        />
                    </div>
                    <button 
                        onClick={() => setIsQuickAddOpen(!isQuickAddOpen)}
                        className="bg-blue-600 text-white px-4 py-1.5 rounded-lg text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all flex items-center gap-2"
                    >
                        <Plus size={14} />
                        Nueva Página
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
                        className="bg-violet-50 dark:bg-violet-900/10 border-b-2 border-violet-300 dark:border-violet-500/30 overflow-hidden shrink-0"
                    >
                        <form 
                            onSubmit={handleCreatePage}
                            className="px-6 py-4 flex items-center gap-4"
                        >
                            <div className="size-8 rounded-lg bg-violet-600 text-white flex items-center justify-center shrink-0">
                                <Zap size={16} />
                            </div>
                            <input 
                                autoFocus
                                value={newTitle}
                                onChange={(e) => setNewTitle(e.target.value)}
                                onKeyDown={(e) => e.key === 'Escape' && setIsQuickAddOpen(false)}
                                placeholder="Título de la nueva página (Presiona Enter para guardar...)"
                                className="flex-1 bg-transparent border-none text-[15px] font-bold text-violet-900 dark:text-violet-200 placeholder:text-violet-400 focus:ring-0"
                            />
                            <div className="flex items-center gap-2">
                                <span className="text-[10px] font-bold text-violet-400 uppercase tracking-widest">
                                    ENTER PARA GUARDAR
                                </span>
                                <button 
                                    type="button"
                                    onClick={() => setIsQuickAddOpen(false)}
                                    className="p-1.5 hover:bg-violet-200 dark:hover:bg-violet-800/30 rounded-lg text-violet-500 transition-all"
                                >
                                    <Trash2 size={14} />
                                </button>
                            </div>
                        </form>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* LIST AREA */}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
                {loading ? (
                    <div className="space-y-4">
                        {[1, 2, 3].map(i => (
                            <div key={i} className="h-20 bg-slate-50 dark:bg-white/5 rounded-2xl animate-pulse" />
                        ))}
                    </div>
                ) : pages.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-center space-y-4 opacity-50">
                        <div className="size-16 rounded-[2rem] bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400">
                            <FileText size={32} />
                        </div>
                        <div>
                            <p className="font-bold text-slate-900 dark:text-white">No hay páginas creadas</p>
                            <p className="text-sm text-slate-500">Usa la barra superior para crear tu primera página.</p>
                        </div>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 gap-3">
                        {pages.map((page, index) => (
                            <motion.div
                                key={page.id}
                                initial={{ opacity: 0, y: 16 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: index * 0.04 }}
                                onClick={() => setSelectedPage(page)}
                                className="group bg-white dark:bg-[#252528] rounded-2xl border border-slate-200/70 dark:border-white/5 p-4 shadow-sm hover:shadow-xl hover:border-blue-500/30 transition-all duration-300 cursor-pointer active:scale-[0.99] flex items-center gap-4"
                            >
                                <div className="size-12 rounded-xl bg-blue-50 dark:bg-blue-500/10 text-blue-600 flex items-center justify-center shrink-0 group-hover:bg-blue-600 group-hover:text-white transition-all">
                                    <FileText size={20} />
                                </div>
                                
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-0.5">
                                        <h3 className="text-[13px] font-semibold text-slate-900 dark:text-white truncate">
                                            {page.title}
                                        </h3>
                                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-700">
                                            PUBLICADO
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <div className="flex items-center gap-1 text-[11px] text-slate-400">
                                            <Globe size={12} />
                                            <span>/{page.page_key}</span>
                                        </div>
                                        <div className="size-1 bg-slate-200 dark:bg-white/10 rounded-full" />
                                        <div className="flex items-center gap-1 text-[11px] text-slate-400">
                                            <Calendar size={12} />
                                            <span>Actualizado {(() => { try { const d = new Date((page.updated_at || '').replace(' ', 'T')); return isNaN(d.getTime()) ? '—' : d.toLocaleDateString('es-CO', { day: 'numeric', month: 'short', year: 'numeric' }); } catch { return '—'; } })()}</span>
                                        </div>
                                    </div>
                                </div>

                                <div className="opacity-0 group-hover:opacity-100 transition-all flex items-center gap-1">
                                    <button className="p-2 hover:bg-slate-100 dark:hover:bg-white/5 rounded-xl text-slate-400 hover:text-blue-600 transition-all">
                                        <Edit2 size={16} />
                                    </button>
                                    <button className="p-2 hover:bg-slate-100 dark:hover:bg-white/5 rounded-xl text-slate-400 hover:text-rose-600 transition-all">
                                        <Trash2 size={16} />
                                    </button>
                                </div>
                                <ChevronRight size={16} className="text-slate-300" />
                            </motion.div>
                        ))}
                    </div>
                )}
            </div>

            {/* SIDE PANEL DETAILS */}
            <SidePanel
                isOpen={!!selectedPage}
                onClose={() => setSelectedPage(null)}
                title={selectedPage?.title || ""}
                subtitle={`Slug: /${selectedPage?.page_key}`}
                fullViewHref={selectedPage ? `/cms/pages/${selectedPage.page_key}` : undefined}
            >
                <div className="space-y-6">
                    <section className="space-y-3">
                        <label className="text-[10px] font-black uppercase tracking-[0.15em] text-slate-400">
                            CONFIGURACIÓN GENERAL
                        </label>
                        <div className="space-y-4">
                            <div className="space-y-1.5">
                                <span className="text-[12px] font-medium text-slate-700 dark:text-slate-300">Título de la página</span>
                                <input 
                                    type="text"
                                    value={selectedPage?.title || ""}
                                    className="w-full px-3 py-2 text-[13px] bg-white dark:bg-[#252528] border border-slate-200 dark:border-white/10 rounded-xl focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 transition-all"
                                />
                            </div>
                            <div className="space-y-1.5">
                                <span className="text-[12px] font-medium text-slate-700 dark:text-slate-300">Ruta (Slug)</span>
                                <div className="flex items-center gap-2">
                                    <span className="text-slate-400 text-sm">/</span>
                                    <input 
                                        type="text"
                                        value={selectedPage?.page_key || ""}
                                        className="flex-1 px-3 py-2 text-[13px] bg-white dark:bg-[#252528] border border-slate-200 dark:border-white/10 rounded-xl focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 transition-all"
                                    />
                                </div>
                            </div>
                        </div>
                    </section>

                    <section className="pt-6 border-t border-slate-100 dark:border-white/5 space-y-3">
                        <label className="text-[10px] font-black uppercase tracking-[0.15em] text-slate-400">
                            VISIBILIDAD Y ESTADO
                        </label>
                        <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-white/5 rounded-2xl">
                            <div className="flex items-center gap-3">
                                <div className="size-10 rounded-xl bg-emerald-100 text-emerald-600 flex items-center justify-center">
                                    <Globe size={18} />
                                </div>
                                <div>
                                    <p className="text-[13px] font-semibold text-slate-900 dark:text-white">Página Pública</p>
                                    <p className="text-[11px] text-slate-500">Visible para todos los visitantes</p>
                                </div>
                            </div>
                            <div className="size-5 rounded-full border-2 border-blue-600 flex items-center justify-center">
                                <div className="size-2.5 bg-blue-600 rounded-full" />
                            </div>
                        </div>
                    </section>

                    <div className="pt-8">
                        <button className="w-full bg-blue-600 text-white py-3 rounded-xl text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all">
                            GUARDAR CAMBIOS
                        </button>
                    </div>
                </div>
            </SidePanel>
        </div>
    );
}
