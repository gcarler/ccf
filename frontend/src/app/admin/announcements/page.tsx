"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import {
    Menu,
    Bell,
    Share2,
    Bookmark,
    ChevronRight,
    Plus,
    Calendar,
    Megaphone,
    Sparkles,
    Zap,
    Layout,
    Globe,
    Loader2,
    Image as ImageIcon,
    Check
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

interface Announcement {
    id: number;
    title: string;
    content: string;
    category: string;
    featured: boolean;
    date: string;
}

export default function AnnouncementsAdmin() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const router = useRouter();
    const [announcements, setAnnouncements] = useState<Announcement[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchAnnouncements = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch<Announcement[]>('/admin/announcements', { token, cache: 'no-store' });
            setAnnouncements(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error(err);
            addToast("Error al sincronizar comunicados", "error");
        } finally {
            setLoading(false);
        }
    }, [token, addToast]);

    useEffect(() => {
        if (isAuthenticated) fetchAnnouncements();
    }, [isAuthenticated, fetchAnnouncements]);

    const featuredAnn = announcements.find(a => a.featured) || announcements[0];
    const normalAnnouncements = announcements.filter(a => a.id !== featuredAnn?.id);

    if (!isAuthenticated) return null;

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#0a0f16] font-display overflow-hidden">
            <style jsx global>{`
                .ann-aura {
                    position: relative;
                }
                .ann-aura::after {
                    content: '';
                    position: absolute;
                    inset: -1px;
                    background: linear-gradient(45deg, var(--aura-color, #3b82f610), transparent 60%);
                    z-index: -1;
                    border-radius: inherit;
                    opacity: 0;
                    transition: opacity 0.5s ease;
                }
                .ann-aura:hover::after {
                    opacity: 1;
                }
            `}</style>

            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'Admin', icon: Layout }, { label: 'Comunicaciones Globales', icon: Megaphone }]}
                viewType="grid" setViewType={() => {}}
                rightActions={
                    <button 
                        onClick={() => router.push('/admin/announcements/new')}
                        className="flex items-center gap-3 px-8 py-3 bg-blue-600 text-white rounded-[1.5rem] text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 active:scale-95 transition-all hover:bg-blue-700"
                    >
                        <Plus size={18} /> Nuevo Comunicado
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-8 lg:p-12 relative pb-40">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#3b82f605_0%,_transparent_50%)] pointer-events-none" />

                <div className="max-w-6xl mx-auto space-y-16 relative z-10">
                    
                    {/* Header Cinematic */}
                    <header className="space-y-4 text-center md:text-left">
                        <motion.div 
                            initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
                            className="inline-flex items-center gap-2 px-4 py-1.5 bg-blue-500/10 text-blue-600 rounded-full text-[10px] font-black uppercase tracking-[0.3em] border border-blue-500/20"
                        >
                            <Sparkles size={12} className="animate-pulse" /> Difusión de Visión CCF
                        </motion.div>
                        <h1 className="text-5xl lg:text-7xl font-black text-slate-900 dark:text-white tracking-tighter leading-none">
                            El latido de la <br/> <span className="text-blue-600 italic text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-400">Comunidad.</span>
                        </h1>
                    </header>

                    {loading ? (
                        <div className="py-40 flex flex-col items-center justify-center gap-6 text-slate-400 font-black uppercase tracking-[0.5em] animate-pulse">
                            <Loader2 className="animate-spin text-blue-600" size={48} strokeWidth={1.5} /> Sincronizando Noticias...
                        </div>
                    ) : (
                        <div className="space-y-16">
                            {/* Featured Cinematic */}
                            {featuredAnn && (
                                <motion.section 
                                    initial={{ opacity: 0, scale: 0.98 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    className="relative group overflow-hidden rounded-[4rem] h-[500px] shadow-2xl border border-white/10"
                                >
                                    <div
                                        className="absolute inset-0 bg-cover bg-center transition-transform duration-1000 group-hover:scale-110"
                                        style={{ backgroundImage: `linear-gradient(to top, rgba(10, 15, 22, 0.95) 0%, rgba(10, 15, 22, 0.4) 50%, transparent 100%), url('https://images.unsplash.com/photo-1438232992991-995b7058bbb3?q=80&w=1200&auto=format&fit=crop')` }}
                                    />
                                    <div className="absolute inset-0 bg-blue-600/5 mix-blend-overlay" />
                                    
                                    <div className="absolute bottom-0 left-0 right-0 p-12 lg:p-16 flex flex-col items-start gap-6 relative z-10">
                                        <div className="flex items-center gap-4">
                                            <span className="px-5 py-2 bg-blue-600 text-white text-[10px] font-black uppercase tracking-[0.3em] rounded-full shadow-2xl shadow-blue-500/40">Noticia Destacada</span>
                                            <span className="px-5 py-2 bg-white/10 backdrop-blur-xl text-white text-[10px] font-black uppercase tracking-[0.3em] rounded-full border border-white/10">{featuredAnn.category}</span>
                                        </div>
                                        <h2 className="text-white text-4xl lg:text-6xl font-black leading-tight tracking-tighter uppercase max-w-4xl">{featuredAnn.title}</h2>
                                        <p className="text-slate-300 text-lg font-medium line-clamp-2 max-w-2xl leading-relaxed italic">&ldquo;{featuredAnn.content.substring(0, 150)}...&rdquo;</p>
                                        <button className="mt-4 px-10 py-5 bg-white text-slate-900 rounded-[2rem] font-black text-xs uppercase tracking-[0.2em] shadow-2xl hover:translate-y-[-4px] active:scale-95 transition-all flex items-center gap-3 group/btn">
                                            Editar Reporte <Edit3 size={18} className="group-hover/btn:rotate-12 transition-transform" />
                                        </button>
                                    </div>
                                </motion.section>
                            )}

                            {/* Feed Grid */}
                            <section className="space-y-10">
                                <div className="flex items-center justify-between px-4">
                                    <h3 className="text-slate-900 dark:text-white text-xl font-black tracking-[0.2em] uppercase flex items-center gap-3">
                                        <Megaphone size={20} className="text-blue-600" /> Últimas Actualizaciones
                                    </h3>
                                    <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{announcements.length} Comunicados Activos</span>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                    <AnimatePresence>
                                        {normalAnnouncements.map((ann, i) => (
                                            <motion.div 
                                                key={ann.id}
                                                initial={{ opacity: 0, y: 30 }}
                                                animate={{ opacity: 1, y: 0 }}
                                                transition={{ delay: i * 0.05 }}
                                                className="ann-aura group bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 p-10 rounded-[3.5rem] flex flex-col gap-8 shadow-sm hover:shadow-2xl transition-all duration-500 overflow-hidden"
                                                style={{ '--aura-color': 'rgba(59, 130, 246, 0.1)' } as any}
                                            >
                                                <div className="flex justify-between items-start">
                                                    <div className="flex flex-col gap-2">
                                                        <span className="text-blue-600 dark:text-blue-400 text-[10px] font-black uppercase tracking-[0.3em]">{ann.category}</span>
                                                        <h4 className="text-2xl font-black text-slate-900 dark:text-white tracking-tighter uppercase leading-none group-hover:text-blue-600 transition-colors">{ann.title}</h4>
                                                    </div>
                                                    <div className="size-12 rounded-2xl bg-slate-50 dark:bg-white/5 flex items-center justify-center text-slate-300 group-hover:text-blue-600 transition-all">
                                                        <Megaphone size={20} />
                                                    </div>
                                                </div>
                                                
                                                <p className="text-slate-500 dark:text-slate-400 text-sm font-medium leading-relaxed line-clamp-3 italic">
                                                    {ann.content}
                                                </p>

                                                <div className="flex items-center justify-between pt-8 border-t border-slate-50 dark:border-white/5">
                                                    <div className="flex items-center gap-2 text-slate-400">
                                                        <Calendar size={14} />
                                                        <span className="text-[10px] font-black uppercase tracking-widest">{new Date(ann.date).toLocaleDateString('es-ES', { month: 'short', day: 'numeric' })}</span>
                                                    </div>
                                                    <div className="flex gap-2">
                                                        <button className="p-3 bg-slate-50 dark:bg-white/5 text-slate-400 hover:text-blue-600 rounded-xl transition-all"><Edit3 size={16} /></button>
                                                        <button className="p-3 bg-slate-50 dark:bg-white/5 text-slate-400 hover:text-rose-600 rounded-xl transition-all"><X size={16} /></button>
                                                    </div>
                                                </div>
                                            </motion.div>
                                        ))}
                                    </AnimatePresence>

                                    {/* Empty State / Add Card */}
                                    <div 
                                        onClick={() => router.push('/admin/announcements/new')}
                                        className="bg-slate-50/50 dark:bg-white/5 border-2 border-dashed border-slate-200 dark:border-white/10 rounded-[3.5rem] p-10 flex flex-col items-center justify-center text-center space-y-6 hover:border-blue-500/50 hover:bg-blue-50/50 transition-all cursor-pointer group"
                                    >
                                        <div className="size-20 rounded-[2rem] bg-white dark:bg-[#0a0f16] shadow-xl flex items-center justify-center text-slate-300 group-hover:text-blue-600 group-hover:scale-110 group-hover:rotate-90 transition-all duration-500">
                                            <Plus size={40} strokeWidth={1.5} />
                                        </div>
                                        <div>
                                            <p className="text-xl font-black text-slate-800 dark:text-white uppercase tracking-tight">Nuevo Mensaje</p>
                                            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">Impactar a toda la congregación</p>
                                        </div>
                                    </div>
                                </div>
                            </section>
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
}
