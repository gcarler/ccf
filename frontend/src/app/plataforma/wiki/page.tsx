"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    BookOpen, Search, Plus, FileText, 
    ChevronRight,
    Zap, Bookmark, Clock, AlertCircle
} from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import Link from 'next/link';
import WorkspaceLayout from '@/components/WorkspaceLayout';

interface WikiDoc {
    id: string;
    page_key: string;
    title: string;
    content?: string;
    version?: number;
    updated_at: string;
}

export default function WikiHomePage() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const [docs, setDocs] = useState<WikiDoc[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [isQuickAddOpen, setIsQuickAddOpen] = useState(false);
    const [newTitle, setNewTitle] = useState("");
    const [search, setSearch] = useState("");

    const fetchDocs = useCallback(async (searchTerm?: string, signal?: AbortSignal) => {
        if (!token) {
            setLoading(false);
            return;
        }
        setError(null);
        try {
            const url = searchTerm ? `/wiki/pages?search=${encodeURIComponent(searchTerm)}` : '/wiki/pages';
            const data = await apiFetch<WikiDoc[]>(url, { token, signal });
            setDocs(Array.isArray(data) ? data : []);
        } catch (err: any) {
            if (err?.name === 'AbortError') return;
            console.error("Error fetching docs:", err);
            addToast('No se pudieron cargar los documentos. Intenta de nuevo.', 'error');
            setError("No se pudieron cargar los documentos. Intenta de nuevo.");
        } finally {
            setLoading(false);
        }
    }, [token, addToast]);

    useEffect(() => {
        const controller = new AbortController();
        fetchDocs(undefined, controller.signal);
        return () => controller.abort();
    }, [fetchDocs]);

    // Server-side search with debounce
    useEffect(() => {
        if (!token) return;
        const controller = new AbortController();
        const timer = setTimeout(() => {
            setLoading(true);
            fetchDocs(search || undefined, controller.signal);
        }, 400);
        return () => {
            clearTimeout(timer);
            controller.abort();
        };
    }, [search, token, fetchDocs]);

    const handleCreateDoc = async (e?: React.FormEvent) => {
        if (e) e.preventDefault();
        if (!newTitle.trim() || !token) return;

        try {
            const page_key = `wiki_${newTitle.toLowerCase().replace(/ /g, "-").replace(/[^\w-]+/g, "")}`;
            await apiFetch(`/wiki/pages/${page_key}`, {
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
            setError("No se pudo crear el documento. Intenta de nuevo.");
        }
    };

    const sidebarSections = [
        {
            title: 'Wiki',
            items: [
                { id: 'wiki-home', label: 'Inicio', href: '/plataforma/wiki', icon: BookOpen },
            ]
        }
    ];

    const filteredDocs = search.trim()
        ? docs.filter((doc) => doc.title.toLowerCase().includes(search.trim().toLowerCase()))
        : docs;

    return (
        <WorkspaceLayout sidebarTitle="Wiki" sidebarSections={sidebarSections}>
            <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))]">
            {/* TOOLBAR */}
            <header className="h-8 border-b border-[hsl(var(--border))]/60 dark:border-white/5 flex items-center px-3 gap-4 shrink-0 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))]">
                <div className="flex items-center gap-2 flex-1">
                    <BookOpen size={16} className="text-[hsl(var(--primary))]" />
                    <h2 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                        BASE DE CONOCIMIENTO
                    </h2>
                </div>
                
                <div className="flex items-center gap-2">
                    <div className="relative">
                        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
                        <input 
                            type="text" 
                            value={search}
                            onChange={(event) => setSearch(event.target.value)}
                            placeholder="Buscar en la wiki..."
                            className="pl-9 pr-4 py-1.5 bg-[hsl(var(--surface-2))] dark:bg-white/5 border-none rounded-lg text-[12px] focus:ring-2 focus:ring-[hsl(var(--primary))]/20 w-64 transition-all"
                        />
                    </div>
                    <button 
                        onClick={() => setIsQuickAddOpen(prev => !prev)}
                        className="bg-[hsl(var(--primary))] text-white px-4 py-1.5 rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-[hsl(var(--primary)/0.2)] hover:bg-[hsl(var(--primary)/0.85)] active:scale-95 transition-all flex items-center gap-2"
                    >
                        <Plus size={14} />
                        Nuevo Doc
                    </button>
                </div>
            </header>

            {/* QUICK ADD BAR */}
            <AnimatePresence>
                {isQuickAddOpen && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="bg-[hsl(var(--info-muted))] dark:bg-[hsl(var(--info)/0.1)] border-b-2 border-[hsl(var(--info)/0.3)] dark:border-[hsl(var(--info)/0.3)] overflow-hidden shrink-0"
                    >
                        <form 
                            onSubmit={handleCreateDoc}
                            className="px-3 py-1.5 flex items-center gap-4"
                        >
                            <div className="size-8 rounded-lg bg-[hsl(var(--primary))] text-white flex items-center justify-center shrink-0">
                                <Zap size={16} />
                            </div>
                            <input 
                                autoFocus
                                value={newTitle}
                                onChange={(e) => setNewTitle(e.target.value)}
                                placeholder="Nombre del documento (Enter para crear...)"
                                className="flex-1 bg-transparent border-none text-sm font-bold text-[hsl(var(--info))] dark:text-[hsl(var(--info))] placeholder:text-[hsl(var(--info))] focus:ring-0"
                            />
                        </form>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* CONTENT AREA */}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-4">
                <div className="w-full space-y-3">
                    <section>
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">
                            DOCUMENTOS RECIENTES
                        </p>
                        
                        {loading ? (
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                {[1, 2, 3].map(i => (
                                    <div key={i} className="h-48 bg-[hsl(var(--bg-primary))] dark:bg-[#252528] rounded-lg animate-pulse border border-[hsl(var(--border))]/70 dark:border-white/5" />
                                ))}
                            </div>
                        ) : error ? (
                            <div className="py-12 flex flex-col items-center justify-center text-center space-y-4">
                                <AlertCircle size={32} className="text-[hsl(var(--destructive))]" />
                                <p className="font-bold text-sm text-[hsl(var(--destructive))]">{error}</p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-4 gap-3">
                                {filteredDocs.length > 0 ? filteredDocs.map((doc, index) => (
                                    <motion.div
                                        key={doc.id}
                                        initial={{ opacity: 0, y: 20 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: index * 0.05 }}
                                        className="group relative bg-[hsl(var(--bg-primary))] dark:bg-[#252528] rounded-lg border border-[hsl(var(--border))]/70 dark:border-white/5 p-3 shadow-sm hover:shadow-2xl transition-all duration-300 cursor-pointer overflow-hidden flex flex-col h-full"
                                    >
                                        <div className="absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-[hsl(var(--primary))] to-[hsl(var(--primary))]" />
                                        
                                        <div className="flex-1 space-y-4">
                                            <div className="flex items-start justify-between">
                                                <div className="size-10 rounded-md bg-[hsl(var(--surface-1))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--primary))] transition-colors">
                                                    <FileText size={20} />
                                                </div>
                                                <button className="p-1 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-lg text-[hsl(var(--text-secondary))]">
                                                    <Bookmark size={14} />
                                                </button>
                                            </div>
                                            
                                            <div>
                                                <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white group-hover:text-[hsl(var(--primary))] transition-colors line-clamp-2">
                                                    {doc.title}
                                                </h3>
                                                <p className="text-[12px] text-[hsl(var(--text-secondary))] mt-2 line-clamp-3 leading-relaxed">
                                                    {doc.content ? doc.content.replace(/<[^>]+>/g, '').substring(0, 120) + '...' : 'Documento de la base de conocimiento.'}
                                                </p>
                                            </div>
                                        </div>

                                        <div className="mt-3 pt-4 border-t border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-between">
                                            <div className="flex items-center gap-1.5 text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
                                                <Clock size={12} />
                                                <span>{new Date(doc.updated_at).toLocaleDateString()}</span>
                                            </div>
                                            <Link 
                                                href={`/plataforma/wiki/docs/${doc.page_key}`}
                                                className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))] flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all"
                                            >
                                                EDITAR <ChevronRight size={12} />
                                            </Link>
                                        </div>
                                    </motion.div>
                                )) : (
                                    <div className="col-span-full py-12 flex flex-col items-center justify-center text-center space-y-4 opacity-60">
                                        <BookOpen size={40} className="text-[hsl(var(--text-secondary))]" />
                                        <p className="font-bold text-lg text-[hsl(var(--text-primary))] dark:text-white">
                                            {search ? `Sin resultados para "${search}"` : 'Tu Base de Conocimiento está vacía'}
                                        </p>
                                        <p className="text-sm text-[hsl(var(--text-secondary))]">
                                            {search ? 'Prueba con otros términos de búsqueda.' : 'Crea guías pastorales, manuales de procesos o documentación técnica para tu equipo.'}
                                        </p>
                                    </div>
                                )}
                            </div>
                        )}
                    </section>
                </div>
            </div>
        </div>
        </WorkspaceLayout>
    );
}
