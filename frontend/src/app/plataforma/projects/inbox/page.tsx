"use client";

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import ProjectsShell from '@/components/projects/ProjectsShell';
import type { ViewType } from '@/components/ViewSwitcher';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import type { ProjectInboxItem } from '@/types/projects';
import { useRouter } from 'next/navigation';
import {
    Inbox, AtSign, Layout,
    MessageCircle
} from 'lucide-react';
import { toast } from 'sonner';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import Skeleton from '@/components/ui/Skeleton';

export default function ProjectsInboxPage() {
    const { token, loading: authLoading } = useAuth();
    const router = useRouter();
    const [messages, setMessages] = useState<ProjectInboxItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [resolvingId, setResolvingId] = useState<string | null>(null);
    const [filter, setFilter] = useState<'all' | 'mentions' | 'unread'>('all');
    const [viewType, setViewType] = useState<ViewType>('list');

    useEffect(() => {
        const fetchInbox = async () => {
            if (!token) {
                setLoading(false);
                setMessages([]);
                setError('Debes iniciar sesión para ver el inbox de proyectos.');
                return;
            }
            try {
                setError(null);
                const data = await apiFetch<ProjectInboxItem[]>('/projects/inbox', { token, cache: 'no-store' });
                setMessages(Array.isArray(data) ? data : []);
            } catch (err) {
                setMessages([]);
                setError('No se pudo cargar el inbox de proyectos.');
                toast.error("Error inesperado");
                toast.error('Error al cargar inbox');
            }
            finally { setLoading(false); }
        };
        if (!authLoading) fetchInbox();
    }, [authLoading, token]);

    const filteredMessages = messages.filter((msg) => {
        if (filter === 'unread') return !msg.is_read;
        if (filter === 'mentions') return msg.type === 'mention';
        return true;
    });
    const groupedMessages = [
        { id: 'mentions', label: 'Menciones', rows: filteredMessages.filter((msg) => msg.type === 'mention') },
        { id: 'comments', label: 'Comentarios', rows: filteredMessages.filter((msg) => msg.type !== 'mention') },
    ];
    const calendarEvents = filteredMessages.map((msg) => ({ id: msg.id, title: msg.user, date: msg.created_at.split('T')[0], color: msg.type === 'mention' ? 'amber' as const : 'blue' as const, location: msg.project }));
    const ganttItems = filteredMessages.map((msg) => ({ id: msg.id, title: msg.user, subtitle: msg.content, start_date: msg.created_at, end_date: msg.created_at, color: msg.type === 'mention' ? 'amber' as const : 'blue' as const, progress: msg.is_read ? 100 : 35 }));

    const handleResolve = async (msg: ProjectInboxItem) => {
        if (!token) return;
        setResolvingId(msg.id);
        try {
            if (msg.type === 'task_assigned' && msg.task_id) {
                await apiFetch(`/projects/tasks/${msg.task_id}`, {
                    method: 'PATCH',
                    token,
                    body: { status: 'completed' }
                });
            }
            await apiFetch(`/projects/inbox/${msg.id}/read`, {
                method: 'POST',
                token,
                body: { is_read: true }
            });
            setMessages((prev) => prev.map((row) => (row.id === msg.id ? { ...row, is_read: true } : row)));
        } catch (err) {
            toast.error("Error inesperado");
            toast.error('Error al resolver elemento');
        } finally {
            setResolvingId(null);
        }
    };

    const handleRespond = (msg: ProjectInboxItem) => {
        if (msg.project_id) {
            router.push(`/plataforma/projects/${msg.project_id}?view=list`);
        }
    };

    return (
        <ProjectsShell
            breadcrumbs={[{ label: 'Proyectos', icon: Layout }, { label: 'Inbox / Respuestas', icon: Inbox }]}
            viewType={viewType}
            onViewChange={setViewType}
            viewOptions={['list', 'table', 'grid', 'board', 'kanban', 'calendar', 'gantt', 'wiki']}
        >
            {error && (
                <div className="mx-4 mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-amber-900 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-200">
                    <p className="text-[11px] font-bold uppercase tracking-wide">{error}</p>
                </div>
            )}
            <div className="flex px-3 py-1.5 border-b border-[hsl(var(--border))] dark:border-white/5 bg-[hsl(var(--surface-1))]/50 dark:bg-white/5 shrink-0">
                <Tab active={filter === 'all'} onClick={() => setFilter('all')} label="Todo" />
                <Tab active={filter === 'unread'} onClick={() => setFilter('unread')} label="No leídos" />
                <Tab active={filter === 'mentions'} onClick={() => setFilter('mentions')} label="Menciones" />
            </div>

            <main className="flex-1 overflow-y-auto scrollbar-thin">
                {loading ? (
                    <div className="p-4 space-y-3">
                        {[1,2,3].map(i => <Skeleton key={i} className="h-20 w-full rounded-lg" />)}
                    </div>
                ) : !error && filteredMessages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-16 text-center p-4">
                        <div className="size-12 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center mb-4">
                            <Inbox size={28} className="text-[hsl(var(--text-secondary))]" />
                        </div>
                        <h3 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">Inbox vacío</h3>
                        <p className="text-sm text-[hsl(var(--text-secondary))] mt-1 max-w-md">No hay mensajes ni notificaciones pendientes en esta vista.</p>
                    </div>
                ) : viewType === 'table' ? (
                    <div className="p-3"><div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 overflow-x-auto"><table className="w-full min-w-[480px] text-left"><thead className="bg-[hsl(var(--surface-1))] dark:bg-white/5"><tr><th className="px-3 py-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Usuario</th><th className="px-3 py-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] hidden md:table-cell">Proyecto</th><th className="px-3 py-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Estado</th></tr></thead><tbody className="divide-y divide-[hsl(var(--border))] dark:divide-white/5">{filteredMessages.map((msg) => <tr key={msg.id}><td className="px-3 py-2 text-sm font-medium">{msg.user}</td><td className="px-3 py-2 hidden md:table-cell text-[11px] text-[hsl(var(--text-secondary))]">{msg.project}</td><td className="px-3 py-2 text-[11px] text-[hsl(var(--text-secondary))]">{msg.is_read ? 'Leído' : 'Pendiente'}</td></tr>)}</tbody></table></div></div>
                ) : viewType === 'grid' ? (
                    <div className="p-3 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">{filteredMessages.map((msg) => <article key={msg.id} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--bg-primary))] dark:bg-white/5"><p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--primary))]">{msg.project}</p><h3 className="font-bold mt-1">{msg.user}</h3><p className="text-sm mt-1 line-clamp-3">{msg.content}</p></article>)}</div>
                ) : viewType === 'board' || viewType === 'kanban' ? (
                    <div className="p-3 grid grid-cols-1 lg:grid-cols-2 gap-3">{groupedMessages.map((group) => <section key={group.id} className="rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/[0.03] border border-[hsl(var(--border))] dark:border-white/10 p-3"><div className="flex justify-between mb-3"><span className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{group.label}</span><span className="text-[10px] font-bold text-[hsl(var(--text-secondary))]">{group.rows.length}</span></div><div className="space-y-2">{group.rows.map((msg) => <div key={msg.id} className="rounded-md bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5 p-2 text-sm">{msg.content}</div>)}</div></section>)}</div>
                ) : viewType === 'calendar' ? (
                    <div className="p-3"><UniversalCalendarView events={calendarEvents} title="Calendario de inbox" /></div>
                ) : viewType === 'gantt' ? (
                    <div className="p-3"><UniversalGanttView items={ganttItems} moduleName="Inbox de proyectos" /></div>
                ) : viewType === 'wiki' ? (
                    <div className="p-3"><UniversalWikiView moduleName="Inbox de proyectos" storageKey="wiki_projects_inbox" /></div>
                ) : (
                    <div className="divide-y divide-[hsl(var(--border))] dark:divide-white/5">
                        {filteredMessages.map((msg, idx) => (
                            <motion.div 
                                key={msg.id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: idx * 0.05 }}
                                className={clsx(
                                    "p-4 flex gap-4 hover:bg-blue-50/30 dark:hover:bg-blue-500/5 transition-all cursor-pointer group relative",
                                    !msg.is_read && "bg-blue-50/50 dark:bg-blue-500/5"
                                )}
                            >
                                    <div className="shrink-0 pt-1">
                                        <div className={clsx(
                                            "size-8 rounded-lg flex items-center justify-center shadow-sm",
                                            msg.type === 'mention' ? "bg-amber-100 dark:bg-amber-900/30 text-amber-600" : "bg-blue-100 dark:bg-blue-900/30 text-[hsl(var(--primary))]"
                                        )}>
                                            {msg.type === 'mention' ? <AtSign size={20} /> : <MessageCircle size={20} />}
                                        </div>
                                </div>
                                <div className="flex-1 space-y-1">
                                    <div className="flex justify-between items-center">
                                        <div className="flex items-center gap-2">
                                            <span className="font-semibold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tight">{msg.user}</span>
                                            <div className="size-1 rounded-full bg-[hsl(var(--surface-2))]" />
                                            <span className="font-semibold text-[hsl(var(--primary))] uppercase tracking-wide">{msg.project}</span>
                                        </div>
                                        <span className="text-[10px] font-bold text-[hsl(var(--text-secondary))]">{formatRelative(msg.created_at)}</span>
                                    </div>
                                    <p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] leading-relaxed font-medium">{msg.content}</p>
                                    <div className="pt-3 flex items-center gap-3 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button
                                            onClick={() => handleRespond(msg)}
                                            className="px-3 py-1 bg-[hsl(var(--bg-primary))] dark:bg-white/10 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg text-[10px] font-semibold uppercase text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]"
                                        >
                                            Responder
                                        </button>
                                        <button
                                            onClick={() => handleResolve(msg)}
                                            disabled={resolvingId === msg.id}
                                            className="px-3 py-1 bg-[hsl(var(--primary))] text-white rounded-lg text-[10px] font-semibold uppercase shadow-lg disabled:opacity-50"
                                        >
                                            {resolvingId === msg.id ? 'Resolviendo...' : 'Resolver'}
                                        </button>
                                    </div>
                                </div>
                                {!msg.is_read && <div className="absolute right-6 top-1/2 -translate-y-1/2 size-2 bg-[hsl(var(--primary))] rounded-full shadow-[0_0_8px_rgba(37,99,235,0.5)]" />}
                            </motion.div>
                        ))}
                    </div>
                )}
            </main>
        </ProjectsShell>
    );
}

function formatRelative(rawDate: string) {
    const date = new Date(rawDate);
    if (Number.isNaN(date.getTime())) return 'Reciente';
    const diffMs = Date.now() - date.getTime();
    const diffMinutes = Math.floor(diffMs / 60000);
    if (diffMinutes < 1) return 'Ahora';
    if (diffMinutes < 60) return `Hace ${diffMinutes}m`;
    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) return `Hace ${diffHours}h`;
    const diffDays = Math.floor(diffHours / 24);
    return diffDays === 1 ? 'Ayer' : `Hace ${diffDays}d`;
}

function Tab({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) {
    return (
        <button onClick={onClick} className={clsx("px-3 py-1.5 text-[11px] font-bold uppercase tracking-wide transition-all border-b-2", active ? "text-[hsl(var(--primary))] border-blue-600" : "text-[hsl(var(--text-secondary))] border-transparent hover:text-[hsl(var(--text-secondary))]")}>{label}</button>
    );
}
