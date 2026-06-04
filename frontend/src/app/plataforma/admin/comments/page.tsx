"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import {
    Bell,
    MessageSquare,
    Trash2,
    Search,
    CheckCircle2,
    Loader2,
    Sparkles,
    Zap,
    Layout,
    Globe,
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import type { ViewType } from '@/components/ViewSwitcher';

const COMMENT_VIEWS: ViewType[] = ['list', 'table', 'grid', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];

interface Comment {
    id: number;
    author: string;
    context: string;
    text: string;
    type: string;
    created_at: string;
}

export default function CommentModeration() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const [comments, setComments] = useState<Comment[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeFilter, setActiveFilter] = useState('Todos');
    const [searchQuery, setSearchQuery] = useState('');
    const [viewType, setViewType] = useState<ViewType>('list');

    const fetchComments = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch<Comment[]>('/admin/comments', { token, cache: 'no-store' });
            setComments(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error(err);
            addToast("Error al sincronizar moderación", "error");
        } finally {
            setLoading(false);
        }
    }, [token, addToast]);

    useEffect(() => {
        if (isAuthenticated) fetchComments();
    }, [isAuthenticated, fetchComments]);

    const handleDelete = async (id: number) => {
        try {
            await apiFetch(`/admin/comments/${id}`, { method: 'DELETE', token });
            addToast("Comentario eliminado", "success");
            setComments(prev => prev.filter(c => c.id !== id));
        } catch {
            addToast("Error al eliminar", "error");
        }
    };

    const filteredComments = comments.filter(c => {
        const matchesFilter = activeFilter === 'Todos' || c.type.includes(activeFilter);
        const matchesSearch = c.text.toLowerCase().includes(searchQuery.toLowerCase()) || 
                             c.author.toLowerCase().includes(searchQuery.toLowerCase());
        return matchesFilter && matchesSearch;
    });
    const groupedComments = useMemo(() => {
        const types = ['Foro', 'Prédicas', 'Cursos', 'General'];
        return types.map((type) => ({
            type,
            items: filteredComments.filter((comment) => comment.type.includes(type) || (type === 'General' && !comment.type)),
        })).filter((column) => column.items.length > 0 || ['Foro', 'Cursos'].includes(column.type));
    }, [filteredComments]);
    const calendarEvents = useMemo(() => filteredComments.map((comment) => ({
        id: comment.id,
        title: `${comment.author}: ${comment.context}`,
        date: (comment.created_at || new Date().toISOString()).slice(0, 10),
        color: comment.type.includes('Cursos') ? 'sky' as const : comment.type.includes('Foro') ? 'blue' as const : 'amber' as const,
        location: comment.type,
    })), [filteredComments]);
    const ganttItems = useMemo(() => filteredComments.map((comment) => ({
        id: comment.id,
        title: comment.author,
        subtitle: comment.context,
        start_date: (comment.created_at || new Date().toISOString()).slice(0, 10),
        end_date: (comment.created_at || new Date().toISOString()).slice(0, 10),
        color: comment.type.includes('Cursos') ? 'sky' as const : comment.type.includes('Foro') ? 'blue' as const : 'amber' as const,
        progress: 50,
    })), [filteredComments]);

    if (!isAuthenticated) return null;

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[#0a0f16] font-display overflow-hidden">
            <style jsx global>{`
                .comment-aura {
                    position: relative;
                }
                .comment-aura::after {
                    content: '';
                    position: absolute;
                    inset: -1px;
                    background: linear-gradient(45deg, rgba(59, 130, 246, 0.1), transparent 60%);
                    z-index: -1;
                    border-radius: inherit;
                    opacity: 0;
                    transition: opacity 0.5s ease;
                }
                .comment-aura:hover::after {
                    opacity: 1;
                }
            `}</style>

            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'Admin', icon: Layout }, { label: 'Moderación de Comunidad', icon: MessageSquare }]}
                viewType={viewType} setViewType={setViewType} availableViews={COMMENT_VIEWS}
                rightActions={
                    <button className="p-3 bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-md text-[hsl(var(--primary))] relative active:scale-95 transition-all">
                        <Bell size={20} />
                        <span className="absolute top-2 right-2 size-2 bg-rose-500 rounded-full ring-2 ring-white dark:ring-[#0a0f16]"></span>
                    </button>
                }
            />

            <div className="flex px-4 border-b border-slate-100 dark:border-white/5 bg-slate-50/50 dark:bg-white/5 shrink-0 overflow-x-auto no-scrollbar">
                {['Todos', 'Foro', 'Prédicas', 'Cursos'].map((f) => (
                    <button 
                        key={f} onClick={() => setActiveFilter(f)}
                        className={clsx(
                            "px-4 py-2 text-[11px] font-semibold uppercase tracking-wide transition-all relative border-b-2 shrink-0",
                            activeFilter === f ? "text-[hsl(var(--primary))] border-blue-600" : "text-slate-400 border-transparent hover:text-slate-600"
                        )}
                    >
                        {f}
                        {activeFilter === f && <motion.div layoutId="mod-tab" className="absolute bottom-[-2px] left-0 right-0 h-1 bg-[hsl(var(--primary))] rounded-t-full shadow-[0_0_15px_rgba(37,99,235,0.4)]" />}
                    </button>
                ))}
            </div>

            <main className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-4 relative pb-4">
 <div className="w-full space-y-3 relative z-10">
                    
                    {/* Header Cinematic */}
                    <div className="flex flex-col md:flex-row md:items-end justify-between gap-3 mb-4">
                        <div className="space-y-4">
                            <motion.div 
                                initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
                                className="inline-flex items-center gap-2 px-4 py-1.5 bg-blue-500/10 text-[hsl(var(--primary))] rounded-full text-[10px] font-semibold uppercase tracking-wide border border-blue-500/20"
                            >
                                <Zap size={12} className="animate-pulse" /> Protocolo de Moderación Activo
                            </motion.div>
                            <h1 className="text-xl lg:text-xl font-bold text-slate-900 dark:text-white tracking-tighter leading-none">
                                Centro de <span className="text-[hsl(var(--primary))] italic">Interacción.</span>
                            </h1>
                        </div>
                        <div className="relative group w-full md:w-72">
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[hsl(var(--primary))] transition-colors" size={18} />
                            <input 
                                value={searchQuery}
                                onChange={e => setSearchQuery(e.target.value)}
                                className="w-full pl-12 pr-4 py-1.5 bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-xs font-bold outline-none focus:ring-4 focus:ring-blue-500/10 transition-all shadow-sm"
                                placeholder="Filtrar por autor o contenido..."
                            />
                        </div>
                    </div>

                    <AnimatePresence mode="wait">
                        {loading ? (
                            <div className="py-1.5 flex flex-col items-center justify-center gap-3 text-slate-400 font-semibold uppercase tracking-wide animate-pulse">
                                <Loader2 className="animate-spin text-[hsl(var(--primary))]" size={48} strokeWidth={1.5} /> Sincronizando Comentarios...
                            </div>
                        ) : viewType === 'table' ? (
                            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="overflow-hidden rounded-lg border border-slate-200 bg-[hsl(var(--bg-primary))] dark:border-white/10 dark:bg-white/5">
                                <table className="w-full text-left text-sm">
                                    <thead className="border-b border-slate-100 text-[10px] font-semibold uppercase tracking-wide text-slate-400 dark:border-white/10">
                                        <tr><th className="px-3 py-3">Autor</th><th className="px-3 py-3">Contexto</th><th className="px-3 py-3">Tipo</th><th className="px-3 py-3">Fecha</th><th className="px-3 py-3" /></tr>
                                    </thead>
                                    <tbody>
                                        {filteredComments.map((comment) => (
                                            <tr key={comment.id} className="border-b border-slate-50 dark:border-white/5">
                                                <td className="px-3 py-1.5 font-bold text-slate-900 dark:text-white">{comment.author}</td>
                                                <td className="px-3 py-1.5 text-slate-500">{comment.context}</td>
                                                <td className="px-3 py-1.5 text-slate-500">{comment.type}</td>
                                                <td className="px-3 py-1.5 text-slate-400">{new Date(comment.created_at).toLocaleDateString()}</td>
                                                <td className="px-3 py-1.5 text-right"><button onClick={() => handleDelete(comment.id)} className="rounded-md bg-rose-50 p-2 text-rose-500"><Trash2 size={16} /></button></td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </motion.div>
                        ) : viewType === 'grid' ? (
                            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="grid grid-cols-1 gap-4 md:grid-cols-2">
                                {filteredComments.map((comment) => (
                                    <article key={comment.id} className="rounded-lg border border-slate-200 bg-[hsl(var(--bg-primary))] p-3 dark:border-white/10 dark:bg-white/5">
                                        <p className="text-sm font-semibold text-slate-900 dark:text-white">{comment.author}</p>
                                        <p className="mt-2 line-clamp-3 text-sm font-medium text-slate-500">{comment.text}</p>
                                        <p className="mt-4 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))]">{comment.type}</p>
                                    </article>
                                ))}
                            </motion.div>
                        ) : viewType === 'board' || viewType === 'kanban' ? (
                            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-4 overflow-x-auto">
                                {groupedComments.map((column) => (
                                    <section key={column.type} className="w-80 shrink-0 rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-white/10 dark:bg-white/[0.03]">
                                        <div className="mb-3 flex items-center justify-between px-1">
                                            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{column.type}</p>
                                            <span className="font-semibold text-slate-400">{column.items.length}</span>
                                        </div>
                                        <div className="space-y-2">
                                            {column.items.map((comment) => (
                                                <article key={comment.id} className="rounded-md border border-slate-200 bg-[hsl(var(--bg-primary))] p-3 dark:border-white/10 dark:bg-white/5">
                                                    <p className="text-xs font-semibold text-slate-900 dark:text-white">{comment.author}</p>
                                                    <p className="mt-2 line-clamp-2 text-[11px] font-medium text-slate-500">{comment.text}</p>
                                                </article>
                                            ))}
                                        </div>
                                    </section>
                                ))}
                            </motion.div>
                        ) : viewType === 'calendar' ? (
                            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-[720px]">
                                <UniversalCalendarView events={calendarEvents} title="Calendario de moderación" />
                            </motion.div>
                        ) : viewType === 'gantt' ? (
                            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-[720px]">
                                <UniversalGanttView items={ganttItems} moduleName="Moderación" />
                            </motion.div>
                        ) : viewType === 'wiki' ? (
                            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                                <UniversalWikiView moduleName="Moderación" storageKey="wiki_admin_comments" />
                            </motion.div>
                        ) : filteredComments.length > 0 ? (
                            <motion.div 
                                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                                className="grid grid-cols-1 gap-3"
                            >
                                {filteredComments.map((comment, i) => (
                                    <motion.div 
                                        key={comment.id}
                                        initial={{ opacity: 0, x: -20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ delay: i * 0.05 }}
                                        className="comment-aura group bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-slate-100 dark:border-white/5 p-4 rounded-lg shadow-sm hover:shadow-2xl transition-all duration-500 flex flex-col space-y-3"
                                    >
                                        <div className="flex items-start gap-3">
                                            <div className="relative shrink-0">
                                                <div className="size-8 rounded-full bg-gradient-to-tr from-slate-100 to-white dark:from-white/10 dark:to-white/5 flex items-center justify-center text-[hsl(var(--primary))] font-black text-xl border-4 border-white dark:border-[#0a0f16] shadow-xl group-hover:rotate-6 transition-transform duration-500">
                                                    {comment.author.charAt(0)}
                                                </div>
                                                <div className="absolute -bottom-1 -right-1 size-7 rounded-full bg-[hsl(var(--primary))] text-white flex items-center justify-center shadow-lg border-2 border-white dark:border-[#0a0f16]">
                                                    <MessageSquare size={14} fill="currentColor" />
                                                </div>
                                            </div>
                                            <div className="flex-1 space-y-4">
                                                <div className="flex justify-between items-center">
                                                    <div>
                                                        <h4 className="text-xl font-bold text-slate-900 dark:text-white uppercase tracking-tight leading-none group-hover:text-[hsl(var(--primary))] transition-colors">{comment.author}</h4>
                                                        <p className="font-semibold text-[hsl(var(--primary))] uppercase tracking-wide mt-2 flex items-center gap-2">
                                                            <Globe size={10} /> En: <span className="text-slate-400 italic">&quot;{comment.context}&quot;</span>
                                                        </p>
                                                    </div>
                                                    <span className="font-semibold text-slate-400 uppercase tracking-wide">{new Date(comment.created_at).toLocaleDateString('es-ES', { month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                                                </div>
                                                <p className="text-base text-slate-600 dark:text-slate-300 font-medium leading-relaxed italic">
                                                    &ldquo;{comment.text}&rdquo;
                                                </p>
                                            </div>
                                        </div>

                                        <div className="flex gap-4 pt-8 border-t border-slate-100 dark:border-white/5">
                                            <button className="flex-1 py-1.5 bg-[hsl(var(--primary))] text-white text-[10px] font-semibold uppercase tracking-wide rounded-lg shadow-xl shadow-blue-500/20 hover:bg-[hsl(var(--primary))] transition-all active:scale-95 flex items-center justify-center gap-3">
                                                <CheckCircle2 size={16} /> Aprobar Registro
                                            </button>
                                            <button className="px-4 py-1.5 bg-slate-100 dark:bg-white/5 text-slate-500 dark:text-slate-400 text-[10px] font-semibold uppercase tracking-wide rounded-lg hover:bg-slate-200 transition-all active:scale-95">
                                                Responder
                                            </button>
                                            <button 
                                                onClick={() => handleDelete(comment.id)}
                                                className="size-7 bg-rose-50 dark:bg-rose-900/20 text-rose-500 rounded-lg border border-rose-100 dark:border-rose-900/30 flex items-center justify-center hover:bg-rose-600 hover:text-white transition-all duration-500 shadow-sm hover:shadow-rose-500/20 active:scale-90"
                                            >
                                                <Trash2 size={20} />
                                            </button>
                                        </div>
                                    </motion.div>
                                ))}
                            </motion.div>
                        ) : (
                            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="py-1.5 text-center space-y-3">
                                <div className="size-10 rounded-lg bg-slate-50 dark:bg-white/5 border-2 border-dashed border-slate-200 dark:border-white/10 flex items-center justify-center mx-auto text-slate-200">
                                    <Sparkles size={48} strokeWidth={1} />
                                </div>
                                <div className="space-y-2">
                                    <p className="text-xl font-bold text-slate-800 dark:text-white uppercase tracking-tight">Comunidad Limpia</p>
                                    <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wide">No hay interacciones pendientes de moderación.</p>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </main>
        </div>
    );
}

