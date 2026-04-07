"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import {
    ArrowLeft,
    Bell,
    Check,
    MessageSquare,
    Trash2,
    CornerUpRight,
    Search,
    Filter,
    Shield,
    CheckCircle2,
    XCircle,
    Loader2,
    Sparkles,
    Zap,
    Layout,
    Globe,
    ExternalLink
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

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
    const router = useRouter();
    const [comments, setComments] = useState<Comment[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeFilter, setActiveFilter] = useState('Todos');
    const [searchQuery, setSearchQuery] = useState('');

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
        } catch (err) {
            addToast("Error al eliminar", "error");
        }
    };

    const filteredComments = comments.filter(c => {
        const matchesFilter = activeFilter === 'Todos' || c.type.includes(activeFilter);
        const matchesSearch = c.text.toLowerCase().includes(searchQuery.toLowerCase()) || 
                             c.author.toLowerCase().includes(searchQuery.toLowerCase());
        return matchesFilter && matchesSearch;
    });

    if (!isAuthenticated) return null;

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#0a0f16] font-display overflow-hidden">
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
                viewType="list" setViewType={() => {}}
                rightActions={
                    <button className="p-3 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-blue-600 relative active:scale-95 transition-all">
                        <Bell size={20} />
                        <span className="absolute top-2 right-2 size-2 bg-rose-500 rounded-full ring-2 ring-white dark:ring-[#0a0f16]"></span>
                    </button>
                }
            />

            <div className="flex px-10 border-b border-slate-100 dark:border-white/5 bg-slate-50/50 dark:bg-white/5 shrink-0 overflow-x-auto no-scrollbar">
                {['Todos', 'Foro', 'Prédicas', 'Cursos'].map((f) => (
                    <button 
                        key={f} onClick={() => setActiveFilter(f)}
                        className={clsx(
                            "px-8 py-6 text-[11px] font-black uppercase tracking-[0.3em] transition-all relative border-b-2 shrink-0",
                            activeFilter === f ? "text-blue-600 border-blue-600" : "text-slate-400 border-transparent hover:text-slate-600"
                        )}
                    >
                        {f}
                        {activeFilter === f && <motion.div layoutId="mod-tab" className="absolute bottom-[-2px] left-0 right-0 h-1 bg-blue-600 rounded-t-full shadow-[0_0_15px_rgba(37,99,235,0.4)]" />}
                    </button>
                ))}
            </div>

            <main className="flex-1 overflow-y-auto scrollbar-thin p-8 lg:p-12 relative pb-40">
                <div className="max-w-5xl mx-auto space-y-10 relative z-10">
                    
                    {/* Header Cinematic */}
                    <div className="flex flex-col md:flex-row md:items-end justify-between gap-8 mb-4">
                        <div className="space-y-4">
                            <motion.div 
                                initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
                                className="inline-flex items-center gap-2 px-4 py-1.5 bg-blue-500/10 text-blue-600 rounded-full text-[10px] font-black uppercase tracking-[0.3em] border border-blue-500/20"
                            >
                                <Zap size={12} className="animate-pulse" /> Protocolo de Moderación Activo
                            </motion.div>
                            <h1 className="text-5xl lg:text-6xl font-black text-slate-900 dark:text-white tracking-tighter leading-none">
                                Centro de <span className="text-blue-600 italic">Interacción.</span>
                            </h1>
                        </div>
                        <div className="relative group w-full md:w-72">
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-600 transition-colors" size={18} />
                            <input 
                                value={searchQuery}
                                onChange={e => setSearchQuery(e.target.value)}
                                className="w-full pl-12 pr-4 py-3.5 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl text-xs font-bold outline-none focus:ring-4 focus:ring-blue-500/10 transition-all shadow-sm"
                                placeholder="Filtrar por autor o contenido..."
                            />
                        </div>
                    </div>

                    <AnimatePresence mode="wait">
                        {loading ? (
                            <div className="py-40 flex flex-col items-center justify-center gap-6 text-slate-400 font-black uppercase tracking-[0.5em] animate-pulse">
                                <Loader2 className="animate-spin text-blue-600" size={48} strokeWidth={1.5} /> Sincronizando Comentarios...
                            </div>
                        ) : filteredComments.length > 0 ? (
                            <motion.div 
                                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                                className="grid grid-cols-1 gap-6"
                            >
                                {filteredComments.map((comment, i) => (
                                    <motion.div 
                                        key={comment.id}
                                        initial={{ opacity: 0, x: -20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ delay: i * 0.05 }}
                                        className="comment-aura group bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 p-10 rounded-[3rem] shadow-sm hover:shadow-2xl transition-all duration-500 flex flex-col space-y-8"
                                    >
                                        <div className="flex items-start gap-8">
                                            <div className="relative shrink-0">
                                                <div className="size-16 rounded-full bg-gradient-to-tr from-slate-100 to-white dark:from-white/10 dark:to-white/5 flex items-center justify-center text-blue-600 font-black text-xl border-4 border-white dark:border-[#0a0f16] shadow-xl group-hover:rotate-6 transition-transform duration-500">
                                                    {comment.author.charAt(0)}
                                                </div>
                                                <div className="absolute -bottom-1 -right-1 size-7 rounded-full bg-blue-600 text-white flex items-center justify-center shadow-lg border-2 border-white dark:border-[#0a0f16]">
                                                    <MessageSquare size={14} fill="currentColor" />
                                                </div>
                                            </div>
                                            <div className="flex-1 space-y-4">
                                                <div className="flex justify-between items-center">
                                                    <div>
                                                        <h4 className="text-xl font-black text-slate-900 dark:text-white uppercase tracking-tight leading-none group-hover:text-blue-600 transition-colors">{comment.author}</h4>
                                                        <p className="text-[10px] font-black text-blue-500 uppercase tracking-widest mt-2 flex items-center gap-2">
                                                            <Globe size={10} /> En: <span className="text-slate-400 italic">&quot;{comment.context}&quot;</span>
                                                        </p>
                                                    </div>
                                                    <span className="text-[9px] font-black text-slate-400 uppercase tracking-[0.2em]">{new Date(comment.created_at).toLocaleDateString('es-ES', { month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                                                </div>
                                                <p className="text-base text-slate-600 dark:text-slate-300 font-medium leading-relaxed italic">
                                                    &ldquo;{comment.text}&rdquo;
                                                </p>
                                            </div>
                                        </div>

                                        <div className="flex gap-4 pt-8 border-t border-slate-100 dark:border-white/5">
                                            <button className="flex-1 py-4 bg-blue-600 text-white text-[10px] font-black uppercase tracking-[0.2em] rounded-2xl shadow-xl shadow-blue-500/20 hover:bg-blue-700 transition-all active:scale-95 flex items-center justify-center gap-3">
                                                <CheckCircle2 size={16} /> Aprobar Registro
                                            </button>
                                            <button className="px-10 py-4 bg-slate-100 dark:bg-white/5 text-slate-500 dark:text-slate-400 text-[10px] font-black uppercase tracking-[0.2em] rounded-2xl hover:bg-slate-200 transition-all active:scale-95">
                                                Responder
                                            </button>
                                            <button 
                                                onClick={() => handleDelete(comment.id)}
                                                className="size-14 bg-rose-50 dark:bg-rose-900/20 text-rose-500 rounded-2xl border border-rose-100 dark:border-rose-900/30 flex items-center justify-center hover:bg-rose-600 hover:text-white transition-all duration-500 shadow-sm hover:shadow-rose-500/20 active:scale-90"
                                            >
                                                <Trash2 size={20} />
                                            </button>
                                        </div>
                                    </motion.div>
                                ))}
                            </motion.div>
                        ) : (
                            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="py-40 text-center space-y-6">
                                <div className="size-24 rounded-[3rem] bg-slate-50 dark:bg-white/5 border-2 border-dashed border-slate-200 dark:border-white/10 flex items-center justify-center mx-auto text-slate-200">
                                    <Sparkles size={48} strokeWidth={1} />
                                </div>
                                <div className="space-y-2">
                                    <p className="text-xl font-black text-slate-800 dark:text-white uppercase tracking-tight">Comunidad Limpia</p>
                                    <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">No hay interacciones pendientes de moderación.</p>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </main>
        </div>
    );
}
