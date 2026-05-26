"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import {
    Plus,
    Calendar,
    Megaphone,
    Sparkles,
    Layout,
    Loader2,
    Edit3,
    X,
    CheckCircle2,
    Archive
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ViewType } from '@/components/ViewSwitcher';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

const ANNOUNCEMENT_VIEWS: ViewType[] = ['grid', 'list', 'table', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];

interface Announcement {
    id: number;
    title: string;
    content: string;
    category: string;
    featured: boolean;
    date: string;
    status: 'draft' | 'published' | 'archived';
}

interface RawAnnouncement {
    id: number;
    title?: string;
    content?: string;
    category?: string;
    is_featured?: boolean;
    featured?: boolean;
    published_at?: string;
    created_at?: string;
    status?: 'draft' | 'published' | 'archived';
}

const STATUS_LABELS: Record<Announcement['status'], string> = {
    draft: 'Borrador',
    published: 'Publicado',
    archived: 'Archivado'
};

const normalizeAnnouncement = (item: RawAnnouncement): Announcement => ({
    id: item.id,
    title: item.title || 'Comunicado',
    content: item.content || '',
    category: item.category || 'General',
    featured: Boolean(item.is_featured ?? item.featured),
    date: item.published_at || item.created_at || new Date().toISOString(),
    status: item.status || 'published',
});

export default function AnnouncementsAdmin() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const router = useRouter();
    const [announcements, setAnnouncements] = useState<Announcement[]>([]);
    const [loading, setLoading] = useState(true);
    const [viewType, setViewType] = useState<ViewType>('grid');

    const fetchAnnouncements = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch<RawAnnouncement[]>('/admin/announcements', { token, cache: 'no-store' });
            setAnnouncements(Array.isArray(data) ? data.map(normalizeAnnouncement) : []);
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

    const handleStatusChange = async (ann: Announcement, status: Announcement['status']) => {
        if (!token) return;
        try {
            const updated = await apiFetch<RawAnnouncement>(`/admin/announcements/${ann.id}`, {
                method: 'PATCH',
                token,
                body: { status },
            });
            setAnnouncements((items) => items.map((item) => item.id === ann.id ? normalizeAnnouncement(updated) : item));
            addToast(`Comunicado marcado como ${STATUS_LABELS[status].toLowerCase()}`, "success");
        } catch (err) {
            console.error(err);
            addToast("Error al actualizar el comunicado", "error");
        }
    };

    const featuredAnn = announcements.find(a => a.featured && a.status === 'published') || announcements.find(a => a.status === 'published') || announcements[0];
    const normalAnnouncements = announcements.filter(a => a.id !== featuredAnn?.id);
    const groupedAnnouncements = [
        { id: 'published', label: 'Publicados', items: announcements.filter((ann) => ann.status === 'published') },
        { id: 'draft', label: 'Borradores', items: announcements.filter((ann) => ann.status === 'draft') },
        { id: 'archived', label: 'Archivados', items: announcements.filter((ann) => ann.status === 'archived') },
    ];
    const calendarEvents = announcements.map((ann) => ({
        id: ann.id,
        title: ann.title,
        date: (ann.date || new Date().toISOString()).split('T')[0],
        color: ann.featured ? 'blue' as const : 'indigo' as const,
        location: ann.category,
    }));
    const ganttItems = announcements.map((ann) => ({
        id: ann.id,
        title: ann.title,
        subtitle: ann.category,
        start_date: ann.date || new Date().toISOString(),
        end_date: ann.date || new Date().toISOString(),
        color: ann.featured ? 'blue' as const : 'indigo' as const,
        progress: ann.status === 'published' ? 100 : ann.status === 'draft' ? 40 : 15,
    }));

    const renderList = () => (
        <div className="space-y-4">
            {announcements.map((ann) => (
                <div key={ann.id} className="bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-lg p-3 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                    <div>
                        <div className="flex items-center gap-2 mb-2">
                            <span className="text-blue-600 text-[10px] font-semibold uppercase tracking-wide">{ann.category}</span>
                            {ann.featured && <span className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 text-[9px] font-semibold uppercase">Destacado</span>}
                            <span className={clsx(
                                "px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase",
                                ann.status === 'published' ? "bg-emerald-50 text-emerald-600" : ann.status === 'draft' ? "bg-amber-50 text-amber-600" : "bg-slate-100 text-slate-500"
                            )}>{STATUS_LABELS[ann.status]}</span>
                        </div>
                        <h3 className="text-lg font-bold text-slate-900 dark:text-white uppercase tracking-tight">{ann.title}</h3>
                        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400 line-clamp-2">{ann.content}</p>
                    </div>
                    <div className="self-start md:self-center flex items-center gap-2">
                        {ann.status !== 'published' && (
                            <button onClick={() => handleStatusChange(ann, 'published')} className="p-3 bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 rounded-md transition-all" title="Publicar">
                                <CheckCircle2 size={16} />
                            </button>
                        )}
                        {ann.status !== 'archived' && (
                            <button onClick={() => handleStatusChange(ann, 'archived')} className="p-3 bg-slate-50 dark:bg-white/5 text-slate-400 hover:text-rose-600 rounded-md transition-all" title="Archivar">
                                <Archive size={16} />
                            </button>
                        )}
                        <button className="p-3 bg-slate-50 dark:bg-white/5 text-slate-400 hover:text-blue-600 rounded-md transition-all"><Edit3 size={16} /></button>
                    </div>
                </div>
            ))}
        </div>
    );

    const renderTable = () => (
        <div className="rounded-lg border border-slate-200 dark:border-white/10 overflow-hidden bg-white dark:bg-white/5">
            <table className="w-full text-left">
                <thead className="bg-slate-50 dark:bg-white/5">
                    <tr>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">Comunicado</th>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400 hidden md:table-cell">Categoría</th>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400 hidden lg:table-cell">Fecha</th>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">Estado</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                    {announcements.map((ann) => (
                        <tr key={ann.id} className="hover:bg-slate-50 dark:hover:bg-white/[0.03]">
                            <td className="px-3 py-1.5 text-sm font-bold text-slate-800 dark:text-slate-100">{ann.title}</td>
                            <td className="px-3 py-1.5 hidden md:table-cell text-[11px] text-slate-500">{ann.category}</td>
                            <td className="px-3 py-1.5 hidden lg:table-cell text-[11px] text-slate-400">{new Date(ann.date).toLocaleDateString('es-ES')}</td>
                            <td className="px-3 py-1.5">
                                <span className={clsx(
                                    "px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase",
                                    ann.status === 'published' ? "bg-emerald-50 text-emerald-600" : ann.status === 'draft' ? "bg-amber-50 text-amber-600" : "bg-slate-100 text-slate-500"
                                )}>
                                    {STATUS_LABELS[ann.status]}
                                </span>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );

    const renderBoard = () => (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {groupedAnnouncements.map((group) => (
                <section key={group.id} className="rounded-lg bg-slate-50 dark:bg-white/[0.03] border border-slate-200 dark:border-white/10 p-3">
                    <div className="flex items-center justify-between mb-5">
                        <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{group.label}</span>
                        <span className="font-semibold text-slate-400">{group.items.length}</span>
                    </div>
                    <div className="space-y-4">
                        {group.items.map((ann) => (
                            <div key={ann.id} className="bg-white dark:bg-white/[0.05] border border-slate-100 dark:border-white/5 rounded-lg p-3">
                                <p className="text-sm font-semibold text-slate-900 dark:text-white uppercase tracking-tight">{ann.title}</p>
                                <p className="mt-2 text-[10px] font-bold text-blue-600 uppercase tracking-wide">{ann.category} · {STATUS_LABELS[ann.status]}</p>
                                <p className="mt-4 text-xs text-slate-500 line-clamp-3">{ann.content}</p>
                            </div>
                        ))}
                    </div>
                </section>
            ))}
        </div>
    );

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
                viewType={viewType}
                setViewType={setViewType}
                availableViews={ANNOUNCEMENT_VIEWS}
                rightActions={
                    <button 
                        onClick={() => router.push('/plataforma/admin/announcements/new')}
                        className="flex items-center gap-3 px-4 py-3 bg-blue-600 text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 active:scale-95 transition-all hover:bg-blue-700"
                    >
                        <Plus size={18} /> Nuevo Comunicado
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-4 relative pb-4">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#3b82f605_0%,_transparent_50%)] pointer-events-none" />

 <div className="w-full space-y-3 relative z-10">
                    
                    {/* Header Cinematic */}
                    <header className="space-y-4 text-center md:text-left">
                        <motion.div 
                            initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
                            className="inline-flex items-center gap-2 px-4 py-1.5 bg-blue-500/10 text-blue-600 rounded-full text-[10px] font-semibold uppercase tracking-wide border border-blue-500/20"
                        >
                            <Sparkles size={12} className="animate-pulse" /> Difusión de Visión CCF
                        </motion.div>
                        <h1 className="text-xl lg:text-xl font-bold text-slate-900 dark:text-white tracking-tighter leading-none">
                            El latido de la <br/> <span className="text-blue-600 italic text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-400">Comunidad.</span>
                        </h1>
                    </header>

                    {loading ? (
                        <div className="py-1.5 flex flex-col items-center justify-center gap-3 text-slate-400 font-semibold uppercase tracking-wide animate-pulse">
                            <Loader2 className="animate-spin text-blue-600" size={48} strokeWidth={1.5} /> Sincronizando Noticias...
                        </div>
                    ) : viewType === 'list' ? (
                        renderList()
                    ) : viewType === 'table' ? (
                        renderTable()
                    ) : viewType === 'board' || viewType === 'kanban' ? (
                        renderBoard()
                    ) : viewType === 'calendar' ? (
                        <UniversalCalendarView
                            events={calendarEvents}
                            title="Calendario de comunicados"
                        />
                    ) : viewType === 'gantt' ? (
                        <UniversalGanttView
                            items={ganttItems}
                            moduleName="Comunicaciones"
                        />
                    ) : viewType === 'wiki' ? (
                        <UniversalWikiView moduleName="Comunicaciones" storageKey="wiki_admin_announcements" />
                    ) : (
                        <div className="space-y-3">
                            {/* Featured Cinematic */}
                            {featuredAnn && (
                                <motion.section 
                                    initial={{ opacity: 0, scale: 0.98 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    className="relative group overflow-hidden rounded-lg h-48 shadow-2xl border border-white/10"
                                >
                                    <div
                                        className="absolute inset-0 bg-cover bg-center transition-transform duration-1000 group-hover:scale-110"
                                        style={{ backgroundImage: `linear-gradient(to top, rgba(10, 15, 22, 0.95) 0%, rgba(10, 15, 22, 0.4) 50%, transparent 100%), url('https://picsum.photos/seed/1438232992991-995b7058bbb3/800/600')` }}
                                    />
                                    <div className="absolute inset-0 bg-blue-600/5 mix-blend-overlay" />
                                    
                                    <div className="absolute bottom-0 left-0 right-0 p-4 lg:p-4 flex flex-col items-start gap-3 relative z-10">
                                        <div className="flex items-center gap-4">
                                            <span className="px-3 py-2 bg-blue-600 text-white text-[10px] font-semibold uppercase tracking-wide rounded-full shadow-2xl shadow-blue-500/40">Noticia Destacada</span>
                                            <span className="px-3 py-2 bg-white/10 backdrop-blur-xl text-white text-[10px] font-semibold uppercase tracking-wide rounded-full border border-white/10">{featuredAnn.category}</span>
                                        </div>
                                        <h2 className="text-white text-lg lg:text-xl font-bold leading-tight tracking-tighter uppercase max-w-4xl">{featuredAnn.title}</h2>
                                        <p className="text-slate-300 text-lg font-medium line-clamp-2 max-w-2xl leading-relaxed italic">&ldquo;{featuredAnn.content.substring(0, 150)}...&rdquo;</p>
                                        <button className="mt-4 px-4 py-2 bg-white text-slate-900 rounded-lg font-black text-xs uppercase tracking-wide shadow-2xl hover:translate-y-[-4px] active:scale-95 transition-all flex items-center gap-3 group/btn">
                                            Editar Reporte <Edit3 size={18} className="group-hover/btn:rotate-12 transition-transform" />
                                        </button>
                                    </div>
                                </motion.section>
                            )}

                            {/* Feed Grid */}
                            <section className="space-y-3">
                                <div className="flex items-center justify-between px-4">
                                    <h3 className="text-slate-900 dark:text-white text-xl font-bold tracking-wide uppercase flex items-center gap-3">
                                        <Megaphone size={20} className="text-blue-600" /> Últimas Actualizaciones
                                    </h3>
                                    <span className="font-semibold text-slate-400 uppercase tracking-wide">{announcements.filter((ann) => ann.status === 'published').length} Comunicados Publicados</span>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    <AnimatePresence>
                                        {normalAnnouncements.map((ann, i) => (
                                            <motion.div 
                                                key={ann.id}
                                                initial={{ opacity: 0, y: 30 }}
                                                animate={{ opacity: 1, y: 0 }}
                                                transition={{ delay: i * 0.05 }}
                                                className="ann-aura group bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 p-4 rounded-lg flex flex-col gap-3 shadow-sm hover:shadow-2xl transition-all duration-500 overflow-hidden"
                                                style={{ '--aura-color': 'rgba(59, 130, 246, 0.1)' } as any}
                                            >
                                                <div className="flex justify-between items-start">
                                                    <div className="flex flex-col gap-2">
                                                        <span className="text-blue-600 dark:text-blue-400 text-[10px] font-semibold uppercase tracking-wide">{ann.category}</span>
                                                        <h4 className="text-lg font-bold text-slate-900 dark:text-white tracking-tighter uppercase leading-none group-hover:text-blue-600 transition-colors">{ann.title}</h4>
                                                    </div>
                                                    <div className="size-7 rounded-lg bg-slate-50 dark:bg-white/5 flex items-center justify-center text-slate-300 group-hover:text-blue-600 transition-all">
                                                        <Megaphone size={20} />
                                                    </div>
                                                </div>
                                                
                                                <p className="text-slate-500 dark:text-slate-400 text-sm font-medium leading-relaxed line-clamp-3 italic">
                                                    {ann.content}
                                                </p>

                                                <div className="flex items-center justify-between pt-8 border-t border-slate-50 dark:border-white/5">
                                                    <div className="flex items-center gap-2 text-slate-400">
                                                        <Calendar size={14} />
                                                        <span className="text-[10px] font-semibold uppercase tracking-wide">{new Date(ann.date).toLocaleDateString('es-ES', { month: 'short', day: 'numeric' })}</span>
                                                    </div>
                                                    <div className="flex gap-2">
                                                        {ann.status !== 'published' && (
                                                            <button onClick={() => handleStatusChange(ann, 'published')} className="p-3 bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 rounded-md transition-all" title="Publicar">
                                                                <CheckCircle2 size={16} />
                                                            </button>
                                                        )}
                                                        <button className="p-3 bg-slate-50 dark:bg-white/5 text-slate-400 hover:text-blue-600 rounded-md transition-all"><Edit3 size={16} /></button>
                                                        <button onClick={() => handleStatusChange(ann, 'archived')} className="p-3 bg-slate-50 dark:bg-white/5 text-slate-400 hover:text-rose-600 rounded-md transition-all" title="Archivar"><X size={16} /></button>
                                                    </div>
                                                </div>
                                            </motion.div>
                                        ))}
                                    </AnimatePresence>

                                    {/* Empty State / Add Card */}
                                    <div 
                                        onClick={() => router.push('/plataforma/admin/announcements/new')}
                                        className="bg-slate-50/50 dark:bg-white/5 border-2 border-dashed border-slate-200 dark:border-white/10 rounded-lg p-4 flex flex-col items-center justify-center text-center space-y-3 hover:border-blue-500/50 hover:bg-blue-50/50 transition-all cursor-pointer group"
                                    >
                                        <div className="size-8 rounded-lg bg-white dark:bg-[#0a0f16] shadow-xl flex items-center justify-center text-slate-300 group-hover:text-blue-600 group-hover:scale-110 group-hover:rotate-90 transition-all duration-500">
                                            <Plus size={40} strokeWidth={1.5} />
                                        </div>
                                        <div>
                                            <p className="text-xl font-bold text-slate-800 dark:text-white uppercase tracking-tight">Nuevo Mensaje</p>
                                            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide mt-1">Impactar a toda la congregación</p>
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


