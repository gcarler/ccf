"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { toast } from 'sonner';
import { SITE_KEY } from '@/lib/site-config';
import {
    listCmsPostsByCategory,
    patchCmsPostByCategory,
    postToAnnouncement,
    type V1AnnouncementShape,
} from '@/lib/cms/v2';
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
    Archive,
    Search
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ViewType } from '@/components/ViewSwitcher';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import type { CSSAuraProperties } from '@/types/admin';

const ANNOUNCEMENT_VIEWS: ViewType[] = ['grid', 'list', 'table', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];

interface Announcement {
    id: string;
    slug: string;
    title: string;
    content: string;
    category: string;
    featured: boolean;
    date: string;
    status: 'draft' | 'published' | 'archived';
}

const STATUS_LABELS: Record<Announcement['status'], string> = {
    draft: 'Borrador',
    published: 'Publicado',
    archived: 'Archivado'
};

const normalizeAnnouncement = (item: V1AnnouncementShape): Announcement => ({
    id: item.id,
    slug: item.slug,
    title: item.title || 'Comunicado',
    content: item.content || '',
    category: item.category || 'General',
    featured: Boolean(item.is_featured),
    date: item.published_at || item.created_at || new Date().toISOString(),
    status: (item.status === 'archived' ? 'archived' : item.status === 'published' || item.is_active ? 'published' : 'draft') as Announcement['status'],
});

export default function AnnouncementsAdmin() {
    const router = useRouter();
    const { token, isAuthenticated } = useAuth();
    const [announcements, setAnnouncements] = useState<Announcement[]>([]);
    const [loading, setLoading] = useState(true);
    const [viewType, setViewType] = useState<ViewType>('grid');
    const [searchQuery, setSearchQuery] = useState('');
    const [pendingArchive, setPendingArchive] = useState<Announcement | null>(null);

    const fetchAnnouncements = useCallback(async (_signal?: AbortSignal) => {
        if (!token) return;
        setLoading(true);
        try {
            const data = (await listCmsPostsByCategory(SITE_KEY, "announcements", { include_archived: true }, token)).map(postToAnnouncement);
            setAnnouncements(Array.isArray(data) ? data.map(normalizeAnnouncement) : []);
        } catch (err) {
            console.error(err);
            toast.error("Error al sincronizar comunicados");
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        if (!isAuthenticated) return;
        const controller = new AbortController();
        fetchAnnouncements(controller.signal);
        return () => controller.abort();
    }, [isAuthenticated, fetchAnnouncements]);

    const handleStatusChange = async (ann: Announcement, status: Announcement['status']) => {
        if (!token) return;
        if (status === 'archived') {
            setPendingArchive(ann);
            return;
        }
        try {
            const v2Status = status === 'published' ? 'published' : status === 'draft' ? 'draft' : 'archived';
            const updated = postToAnnouncement(await patchCmsPostByCategory(SITE_KEY, ann.slug, "announcements", { status: v2Status }, token));
            setAnnouncements((items) => items.map((item) => item.id === ann.id ? normalizeAnnouncement(updated) : item));
            toast.success(`Comunicado marcado como ${STATUS_LABELS[status].toLowerCase()}`);
        } catch (err) {
            console.error(err);
            toast.error("Error al actualizar el comunicado");
        }
    };

    const confirmArchive = async () => {
        if (!token || !pendingArchive) return;
        try {
            const updated = postToAnnouncement(await patchCmsPostByCategory(SITE_KEY, pendingArchive.slug, "announcements", { status: "archived" }, token));
            setAnnouncements((items) => items.map((item) => item.id === pendingArchive.id ? normalizeAnnouncement(updated) : item));
            toast.success("Comunicado archivado");
        } catch (err) {
            toast.error("Error al archivar");
        } finally {
            setPendingArchive(null);
        }
    };

    const featuredAnn = announcements.find(a => a.featured && a.status === 'published') || announcements.find(a => a.status === 'published') || announcements[0];
    const normalAnnouncements = announcements.filter(a => a.id !== featuredAnn?.id && (a.title.toLowerCase().includes(searchQuery.toLowerCase()) || a.content.toLowerCase().includes(searchQuery.toLowerCase())));
    const groupedAnnouncements = [
        { id: 'published', label: 'Publicados', items: announcements.filter((ann) => ann.status === 'published') },
        { id: 'draft', label: 'Borradores', items: announcements.filter((ann) => ann.status === 'draft') },
        { id: 'archived', label: 'Archivados', items: announcements.filter((ann) => ann.status === 'archived') },
    ];
    const calendarEvents = announcements.map((ann) => ({
        id: ann.id,
        title: ann.title,
        date: (ann.date || new Date().toISOString()).split('T')[0],
        color: ann.featured ? 'blue' as const : 'sky' as const,
        location: ann.category,
    }));
    const ganttItems = announcements.map((ann) => ({
        id: ann.id,
        title: ann.title,
        subtitle: ann.category,
        start_date: ann.date || new Date().toISOString(),
        end_date: ann.date || new Date().toISOString(),
        color: ann.featured ? 'blue' as const : 'sky' as const,
        progress: ann.status === 'published' ? 100 : ann.status === 'draft' ? 40 : 15,
    }));

    const renderList = () => (
        <div className="space-y-4">
            {announcements.map((ann) => (
                <div key={ann.id} className="bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5 rounded-lg p-3 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                    <div>
                        <div className="flex items-center gap-2 mb-2">
                            <span className="text-[hsl(var(--primary))] text-2xs font-semibold uppercase tracking-wide">{ann.category}</span>
                            {ann.featured && <span className="px-2 py-0.5 rounded-full bg-info-soft text-[hsl(var(--primary))] text-2xs font-semibold uppercase">Destacado</span>}
                            <span className={clsx(
                                "px-2 py-0.5 rounded-full text-2xs font-semibold uppercase",
                                ann.status === 'published' ? "bg-[hsl(var(--success-muted))] text-[hsl(var(--success))]" : ann.status === 'draft' ? "bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning))]" : "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]"
                            )}>{STATUS_LABELS[ann.status]}</span>
                        </div>
                        <h3 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tight">{ann.title}</h3>
                        <p className="mt-2 text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] line-clamp-2">{ann.content}</p>
                    </div>
                    <div className="self-start md:self-center flex items-center gap-2">
                        {ann.status !== 'published' && (
                            <button onClick={() => handleStatusChange(ann, 'published')} className="p-3 bg-[hsl(var(--success-muted))] text-[hsl(var(--success))] rounded-md transition-all" title="Publicar">
                                <CheckCircle2 size={16} />
                            </button>
                        )}
                        {ann.status !== 'archived' && (
                            <button onClick={() => handleStatusChange(ann, 'archived')} className="p-3 bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[hsl(var(--text-secondary))] hover:text-danger-text rounded-md transition-all" title="Archivar">
                                <Archive size={16} />
                            </button>
                        )}
                        <button className="p-3 bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] rounded-md transition-all"><Edit3 size={16} /></button>
                    </div>
                </div>
            ))}
        </div>
    );

    const renderTable = () => (
        <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 overflow-x-auto bg-[hsl(var(--bg-primary))] dark:bg-white/5">
            <table className="w-full min-w-[480px] text-left">
                <thead className="bg-[hsl(var(--surface-1))] dark:bg-white/5">
                    <tr>
                        <th className="px-3 py-1.5 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Comunicado</th>
                        <th className="px-3 py-1.5 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hidden md:table-cell">Categoría</th>
                        <th className="px-3 py-1.5 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hidden lg:table-cell">Fecha</th>
                        <th className="px-3 py-1.5 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Estado</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-[hsl(var(--border))] dark:divide-white/5">
                    {announcements.map((ann) => (
                        <tr key={ann.id} className="hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.03]">
                            <td className="px-3 py-1.5 text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{ann.title}</td>
                            <td className="px-3 py-1.5 hidden md:table-cell text-xs text-[hsl(var(--text-secondary))]">{ann.category}</td>
                            <td className="px-3 py-1.5 hidden lg:table-cell text-xs text-[hsl(var(--text-secondary))]">{new Date(ann.date).toLocaleDateString('es-ES')}</td>
                            <td className="px-3 py-1.5">
                                <span className={clsx(
                                    "px-2 py-0.5 rounded-full text-2xs font-semibold uppercase",
                                    ann.status === 'published' ? "bg-[hsl(var(--success-muted))] text-[hsl(var(--success))]" : ann.status === 'draft' ? "bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning))]" : "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]"
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
                <section key={group.id} className="rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/[0.03] border border-[hsl(var(--border))] dark:border-white/10 p-3">
                    <div className="flex items-center justify-between mb-5">
                        <span className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{group.label}</span>
                        <span className="font-semibold text-[hsl(var(--text-secondary))]">{group.items.length}</span>
                    </div>
                    <div className="space-y-4">
                        {group.items.map((ann) => (
                            <div key={ann.id} className="bg-[hsl(var(--bg-primary))] dark:bg-white/[0.05] border border-[hsl(var(--border))] dark:border-white/5 rounded-lg p-3">
                                <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tight">{ann.title}</p>
                                <p className="mt-2 text-2xs font-bold text-[hsl(var(--primary))] uppercase tracking-wide">{ann.category} · {STATUS_LABELS[ann.status]}</p>
                                <p className="mt-4 text-xs text-[hsl(var(--text-secondary))] line-clamp-3">{ann.content}</p>
                            </div>
                        ))}
                    </div>
                </section>
            ))}
        </div>
    );

    if (!isAuthenticated) return null;

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] font-display overflow-hidden">
            <style jsx global>{`
                .ann-aura {
                    position: relative;
                }
                .ann-aura::after {
                    content: '';
                    position: absolute;
                    inset: -1px;
                    background: linear-gradient(45deg, var(--aura-color, hsl(var(--info)/0.1)), transparent 60%);
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
                        onClick={() => router.push('/plataforma/cms/announcements/new')}
                        className="flex items-center gap-3 px-4 py-3 bg-[hsl(var(--primary))] text-white rounded-lg text-xs font-semibold uppercase tracking-wide shadow-xl shadow-[hsl(var(--info)/20%)] active:scale-95 transition-all hover:bg-[hsl(var(--primary))]"
                    >
                        <Plus size={18} /> Nuevo Comunicado
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-4 relative pb-4">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_hsl(var(--info)/0.05)_0%,_transparent_50%)] pointer-events-none" />

 <div className="w-full space-y-3 relative z-10">

                    {/* Header Cinematic */}
                    <header className="space-y-4 text-center md:text-left">
                        <motion.div
                            initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
                            className="inline-flex items-center gap-2 px-4 py-1.5 bg-[hsl(var(--info))]/10 text-[hsl(var(--primary))] rounded-full text-2xs font-semibold uppercase tracking-wide border border-[hsl(var(--info)/100%)]/20"
                        >
                            <Sparkles size={12} className="animate-pulse" /> Difusión de Visión CCF
                        </motion.div>
                        <h1 className="text-xl lg:text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tighter leading-none">
                            El latido de la <br/> <span className="text-[hsl(var(--primary))] italic text-transparent bg-clip-text bg-gradient-to-r from-[hsl(var(--info))] to-[hsl(var(--info))]">Comunidad.</span>
                        </h1>
                    </header>

                    {loading ? (
                        <div className="py-1.5 flex flex-col items-center justify-center gap-3 text-[hsl(var(--text-secondary))] font-semibold uppercase tracking-wide animate-pulse">
                            <Loader2 className="animate-spin text-[hsl(var(--primary))]" size={48} strokeWidth={1.5} /> Sincronizando Noticias...
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
                                        className="absolute inset-0 bg-gradient-to-br from-[hsl(var(--admin-bg-tertiary))] via-[hsl(var(--surface-2))] to-[hsl(var(--admin-bg-deep))] dark:from-[hsl(var(--admin-bg-secondary))] dark:via-[hsl(var(--admin-bg-tertiary))] dark:to-black transition-transform duration-1000 group-hover:scale-105"
                                        style={{ backgroundImage: `linear-gradient(to top, rgba(10, 15, 22, 0.95) 0%, rgba(10, 15, 22, 0.4) 50%, transparent 100%), radial-gradient(circle at 80% 20%, hsl(var(--primary) / 0.18) 0%, transparent 60%)` }}
                                    />
                                    <div className="absolute inset-0 bg-[hsl(var(--info))]/5 mix-blend-overlay" />

                                    <div className="absolute bottom-0 left-0 right-0 p-4 lg:p-4 flex flex-col items-start gap-3 relative z-10">
                                        <div className="flex items-center gap-4">
                                            <span className="px-3 py-2 bg-[hsl(var(--primary))] text-white text-2xs font-semibold uppercase tracking-wide rounded-full shadow-2xl shadow-[hsl(var(--info)/40%)]">Noticia Destacada</span>
                                            <span className="px-3 py-2 bg-white/10 backdrop-blur-xl text-white text-2xs font-semibold uppercase tracking-wide rounded-full border border-white/10">{featuredAnn.category}</span>
                                        </div>
                                        <h2 className="text-white text-lg lg:text-xl font-bold leading-tight tracking-tighter uppercase max-w-4xl">{featuredAnn.title}</h2>
                                        <p className="text-[hsl(var(--text-secondary))] text-lg font-medium line-clamp-2 max-w-2xl leading-relaxed italic">&ldquo;{featuredAnn.content.substring(0, 150)}...&rdquo;</p>
                                        <button className="mt-4 px-4 py-2 bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))] rounded-lg font-black text-xs uppercase tracking-wide shadow-2xl hover:translate-y-[-4px] active:scale-95 transition-all flex items-center gap-3 group/btn">
                                            Editar Reporte <Edit3 size={18} className="group-hover/btn:rotate-12 transition-transform" />
                                        </button>
                                    </div>
                                </motion.section>
                            )}

                            {/* Feed Grid */}
                            <section className="space-y-4">
                                <div className="flex flex-col md:flex-row items-center justify-between px-4 gap-4">
                                    <h3 className="text-[hsl(var(--text-primary))] dark:text-white text-xl font-bold tracking-wide uppercase flex items-center gap-3 shrink-0">
                                        <Megaphone size={20} className="text-[hsl(var(--primary))]" /> Últimas Actualizaciones
                                    </h3>
                                    <div className="flex items-center gap-4 w-full md:w-auto flex-1 justify-end">
                                        <div className="relative w-full md:max-w-xs">
                                            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
                                            <input
                                                type="text"
                                                placeholder="Buscar por título o contenido..."
                                                value={searchQuery}
                                                onChange={e => setSearchQuery(e.target.value)}
                                                className="w-full pl-9 pr-4 py-2 bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg text-sm focus:border-[hsl(var(--primary))] outline-none transition-colors"
                                            />
                                        </div>
                                        <span className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide hidden lg:block">
                                            {announcements.filter((ann) => ann.status === 'published').length} Publicados
                                        </span>
                                    </div>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    <AnimatePresence>
                                        {normalAnnouncements.map((ann, i) => (
                                            <motion.div
                                                key={ann.id}
                                                initial={{ opacity: 0, y: 30 }}
                                                animate={{ opacity: 1, y: 0 }}
                                                transition={{ delay: i * 0.05 }}
                                                className="ann-aura group bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5 p-4 rounded-lg flex flex-col gap-3 shadow-sm hover:shadow-2xl transition-all duration-500 overflow-hidden"
                                                style={{ '--aura-color': 'rgba(59, 130, 246, 0.1)' } as CSSAuraProperties}
                                            >
                                                <div className="flex justify-between items-start">
                                                    <div className="flex flex-col gap-2">
                                                        <span className="text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] text-2xs font-semibold uppercase tracking-wide">{ann.category}</span>
                                                        <h4 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tighter uppercase leading-none group-hover:text-[hsl(var(--primary))] transition-colors">{ann.title}</h4>
                                                    </div>
                                                    <div className="size-7 rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--primary))] transition-all">
                                                        <Megaphone size={20} />
                                                    </div>
                                                </div>

                                                <p className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] text-sm font-medium leading-relaxed line-clamp-3 italic">
                                                    {ann.content}
                                                </p>

                                                <div className="flex items-center justify-between pt-8 border-t border-[hsl(var(--border))] dark:border-white/5">
                                                    <div className="flex items-center gap-2 text-[hsl(var(--text-secondary))]">
                                                        <Calendar size={14} />
                                                        <span className="text-2xs font-semibold uppercase tracking-wide">{new Date(ann.date).toLocaleDateString('es-ES', { month: 'short', day: 'numeric' })}</span>
                                                    </div>
                                                    <div className="flex gap-2">
                                                        {ann.status !== 'published' && (
                                                            <button onClick={() => handleStatusChange(ann, 'published')} className="p-3 bg-[hsl(var(--success-muted))] text-[hsl(var(--success))] rounded-md transition-all" title="Publicar">
                                                                <CheckCircle2 size={16} />
                                                            </button>
                                                        )}
                                                        <button className="p-3 bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] rounded-md transition-all"><Edit3 size={16} /></button>
                                                        <button onClick={() => handleStatusChange(ann, 'archived')} className="p-3 bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[hsl(var(--text-secondary))] hover:text-danger-text rounded-md transition-all" title="Archivar"><X size={16} /></button>
                                                    </div>
                                                </div>
                                            </motion.div>
                                        ))}
                                    </AnimatePresence>

                                    {/* Empty State / Add Card */}
                                    <div
                                        onClick={() => router.push('/plataforma/cms/announcements/new')}
                                        className="bg-[hsl(var(--surface-1))]/50 dark:bg-white/5 border-2 border-dashed border-[hsl(var(--border))] dark:border-white/10 rounded-lg p-4 flex flex-col items-center justify-center text-center space-y-3 hover:border-[hsl(var(--info)/100%)]/50 hover:bg-info-soft/50 transition-all cursor-pointer group"
                                    >
                                        <div className="size-8 rounded-lg bg-[hsl(var(--bg-primary))] shadow-xl flex items-center justify-center text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--primary))] group-hover:scale-110 group-hover:rotate-90 transition-all duration-500">
                                            <Plus size={40} strokeWidth={1.5} />
                                        </div>
                                        <div>
                                            <p className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tight">Nuevo Mensaje</p>
                                            <p className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide mt-1">Impactar a toda la congregación</p>
                                        </div>
                                    </div>
                                </div>
                            </section>
                        </div>
                    )}
                </div>
            </main>
            <AnimatePresence>
                {pendingArchive && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            className="w-full max-w-sm rounded-xl bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] p-5 shadow-2xl border border-[hsl(var(--border))] dark:border-white/10"
                        >
                            <h3 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white mb-2">¿Archivar comunicado?</h3>
                            <p className="text-sm text-[hsl(var(--text-secondary))] mb-6">
                                El comunicado dejará de estar visible inmediatamente.
                            </p>
                            <div className="flex gap-3 justify-end">
                                <button
                                    onClick={() => setPendingArchive(null)}
                                    className="px-4 py-2 rounded-lg text-sm font-semibold text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors"
                                >
                                    Cancelar
                                </button>
                                <button
                                    onClick={confirmArchive}
                                    className="px-4 py-2 rounded-lg text-sm font-semibold bg-warning-soft text-warning-text hover:bg-[hsl(var(--warning-muted))] transition-colors"
                                >
                                    Archivar
                                </button>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </div>
    );
}
