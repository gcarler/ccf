"use client";

import React, { useState, useEffect } from 'react';
import { 
    MessageSquare, 
    Search, 
    Filter, 
    Plus, 
    ChevronRight, 
    ThumbsUp, 
    Clock, 
    User, 
    MoreHorizontal,
    Bot,
    Sparkles,
    CheckCircle2,
    BookOpen,
    Star,
    Zap,
    Trophy,
    TrendingUp,
    LayoutGrid,
    List as ListIcon
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

export default function AcademyForumPage() {
    const { token } = useAuth();
    const [threads, setThreads] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [viewMode, setViewType] = useState<'grid' | 'list'>('list');
    const [activeCategory, setActiveCategory] = useState('Todos');

    useEffect(() => {
        const fetchThreads = async () => {
            if (!token) return;
            try {
                // Actual API logic here
                const data = await apiFetch('/academy/forum/threads', { token });
                setThreads(Array.isArray(data) ? data : []);
            } catch (err) {
                // Quality Mock Data
                setThreads([
                    { id: 1, title: 'Interpretación de Romanos 8:28', author: 'Pastor Carlos', replies: 12, category: 'Teología', upvotes: 45, is_resolved: true, last_activity: 'Hace 2 horas' },
                    { id: 2, title: '¿Cómo mejorar la alabanza en grupos pequeños?', author: 'Elena R.', replies: 8, category: 'Liderazgo', upvotes: 22, is_resolved: false, last_activity: 'Hace 5 min' },
                    { id: 3, title: 'Duda sobre el examen de Historia de la Iglesia', author: 'Marcos L.', replies: 3, category: 'Académico', upvotes: 5, is_resolved: false, last_activity: 'Ayer' },
                ]);
            } finally {
                setLoading(false);
            }
        };
        fetchThreads();
    }, [token]);

    const categories = ['Todos', 'Teología', 'Liderazgo', 'Académico', 'Misiones', 'Testimonios'];

    return (
        <div className="flex flex-col h-full bg-slate-50/50 dark:bg-[#1e1f21] overflow-hidden font-display">
            <WorkspaceToolbar 
                breadcrumbs={[
                    { label: 'Academia', icon: BookOpen },
                    { label: 'Foros de Discusión', icon: MessageSquare }
                ]}
                viewType={viewMode} setViewType={(v: any) => setViewType(v)}
                rightActions={
                    <button className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-xl text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 active:scale-95 transition-all">
                        <Plus size={14} /> Iniciar Debate
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-8 lg:p-12">
                <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-10">
                    
                    {/* Left Column: Categories & IA */}
                    <aside className="lg:col-span-3 space-y-8">
                        <section className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[2.5rem] p-8 shadow-xl space-y-6">
                            <h3 className="text-[11px] font-black text-slate-400 uppercase tracking-[0.3em] px-2">Categorías</h3>
                            <div className="space-y-1">
                                {categories.map(cat => (
                                    <button 
                                        key={cat} onClick={() => setActiveCategory(cat)}
                                        className={clsx(
                                            "w-full flex items-center justify-between p-4 rounded-2xl text-[12px] font-bold transition-all",
                                            activeCategory === cat ? "bg-blue-50 dark:bg-blue-600/10 text-blue-600" : "text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5"
                                        )}
                                    >
                                        {cat}
                                        {activeCategory === cat && <div className="size-1.5 rounded-full bg-blue-600 shadow-[0_0_8px_#2563eb]" />}
                                    </button>
                                ))}
                            </div>
                        </section>

                        <section className="p-8 bg-blue-600 rounded-[3rem] text-white shadow-2xl space-y-6 relative overflow-hidden group">
                            <div className="absolute top-0 right-0 -mr-10 -mt-10 size-40 bg-white/10 rounded-full blur-3xl group-hover:bg-white/20 transition-all duration-1000" />
                            <div className="relative z-10 space-y-4">
                                <div className="flex items-center gap-3">
                                    <Bot size={20} fill="currentColor" />
                                    <h4 className="text-[11px] font-black uppercase tracking-widest">IA Moderator</h4>
                                </div>
                                <p className="text-[13px] font-medium leading-relaxed italic text-blue-50">
                                    &ldquo;Optimus sugiere: El debate sobre Interpretación Bíblica es el más activo hoy. ¡Únete a la conversación!&rdquo;
                                </p>
                            </div>
                        </section>
                    </aside>

                    {/* Main Feed */}
                    <div className="lg:col-span-9 space-y-8 pb-20">
                        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 px-4">
                            <h2 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white uppercase">Debates Populares</h2>
                            <div className="relative w-full md:w-80">
                                <input placeholder="Buscar temas..." className="w-full bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl py-3 px-12 text-sm font-bold outline-none focus:ring-4 focus:ring-blue-500/10 transition-all" />
                                <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                            </div>
                        </div>

                        <div className="space-y-4">
                            {!loading && threads.length === 0 && (
                                <div className="py-20 text-center space-y-4 bg-white/50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[2.5rem]">
                                    <MessageSquare className="w-16 h-16 mx-auto text-slate-300 dark:text-slate-600" />
                                    <div className="space-y-1">
                                        <h3 className="text-xl font-black text-slate-900 dark:text-white">Aún no hay debates</h3>
                                        <p className="text-slate-500 font-medium">Sé el primero en iniciar una conversación en esta categoría.</p>
                                    </div>
                                </div>
                            )}
                            {threads.map((thread) => (
                                <motion.div 
                                    key={thread.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                                    className="p-8 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[2.5rem] shadow-sm hover:shadow-xl hover:border-blue-500/20 transition-all group cursor-pointer"
                                >
                                    <div className="flex flex-col md:flex-row gap-8 items-start md:items-center">
                                        <div className="flex flex-col items-center gap-1 shrink-0 p-3 bg-slate-50 dark:bg-white/5 rounded-2xl border border-slate-100 dark:border-white/5">
                                            <ThumbsUp size={18} className="text-slate-400 group-hover:text-blue-600 transition-colors" />
                                            <span className="text-[12px] font-black text-slate-700 dark:text-slate-200">{thread.upvotes}</span>
                                        </div>
                                        <div className="flex-1 space-y-3">
                                            <div className="flex items-center gap-3">
                                                <span className="px-3 py-1 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded-full text-[9px] font-black uppercase tracking-widest">{thread.category}</span>
                                                {thread.is_resolved && <span className="flex items-center gap-1.5 px-3 py-1 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 rounded-full text-[9px] font-black uppercase tracking-widest"><CheckCircle2 size={12} /> Resuelto</span>}
                                            </div>
                                            <h4 className="text-xl font-black text-slate-900 dark:text-white group-hover:text-blue-600 transition-colors tracking-tight leading-tight">{thread.title}</h4>
                                            <div className="flex items-center gap-4 text-slate-400">
                                                <div className="flex items-center gap-1.5"><User size={14} /><span className="text-[11px] font-bold">{thread.author}</span></div>
                                                <div className="size-1 rounded-full bg-slate-300" />
                                                <div className="flex items-center gap-1.5"><Clock size={14} /><span className="text-[11px] font-bold">{thread.last_activity}</span></div>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-6 shrink-0 md:border-l border-slate-100 dark:border-white/5 md:pl-8">
                                            <div className="text-center">
                                                <p className="text-lg font-black text-slate-900 dark:text-white">{thread.replies}</p>
                                                <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Respuestas</p>
                                            </div>
                                            <ChevronRight size={24} className="text-slate-200 group-hover:text-blue-600 group-hover:translate-x-1 transition-all" />
                                        </div>
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
