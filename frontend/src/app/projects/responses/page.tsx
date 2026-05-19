"use client";

import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ViewType } from '@/components/ViewSwitcher';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import Skeleton from '@/components/ui/Skeleton';
import type { ProjectInboxItem } from '@/types/projects';
import { useRouter } from 'next/navigation';
import { Inbox, Layout } from 'lucide-react';
import clsx from 'clsx';

const RESPONSE_VIEWS: ViewType[] = ['list', 'table', 'grid', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];

export default function ProjectsResponsesPage() {
    const { token } = useAuth();
    const router = useRouter();
    const [items, setItems] = useState<ProjectInboxItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [resolvingId, setResolvingId] = useState<string | null>(null);
    const [viewType, setViewType] = useState<ViewType>('list');

    useEffect(() => {
        const load = async () => {
            if (!token) return;
            try {
                const data = await apiFetch<ProjectInboxItem[]>('/projects/inbox?unread_only=true', { token, cache: 'no-store' });
                setItems(Array.isArray(data) ? data : []);
            } catch (error) {
                console.error(error);
            } finally {
                setLoading(false);
            }
        };
        load();
    }, [token]);

    const unread = useMemo(() => items.filter((item) => !item.is_read), [items]);
    const grouped = [
        { id: 'mentions', label: 'Menciones', rows: unread.filter((item) => item.type === 'mention') },
        { id: 'updates', label: 'Actualizaciones', rows: unread.filter((item) => item.type !== 'mention') },
    ];
    const calendarEvents = unread.map((item) => ({ id: item.id, title: item.task_title || item.project, date: item.created_at.split('T')[0], color: item.type === 'mention' ? 'amber' as const : 'blue' as const, location: item.project }));
    const ganttItems = unread.map((item) => ({ id: item.id, title: item.task_title || item.project, subtitle: item.project, start_date: item.created_at, end_date: item.created_at, color: item.type === 'mention' ? 'amber' as const : 'blue' as const, progress: 50 }));

    const resolveItem = async (item: ProjectInboxItem) => {
        if (!token) return;
        setResolvingId(item.id);
        try {
            if (item.task_id) {
                await apiFetch(`/projects/tasks/${item.task_id}`, {
                    method: 'PATCH',
                    token,
                    body: { status: 'done' },
                });
            }
            await apiFetch(`/projects/inbox/${item.id}/read`, {
                method: 'POST',
                token,
                body: { is_read: true },
            });
            setItems((prev) => prev.map((row) => (row.id === item.id ? { ...row, is_read: true } : row)));
        } catch (error) {
            console.error(error);
        } finally {
            setResolvingId(null);
        }
    };

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in font-display">
            <WorkspaceToolbar
                breadcrumbs={[{ label: 'Proyectos', icon: Layout }, { label: 'Respuestas', icon: Inbox }]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={RESPONSE_VIEWS}
            />

            <main className="flex-1 overflow-y-auto p-4 lg:p-6">
                {loading ? (
                    <div className="space-y-3">{[1, 2, 3].map((idx) => <Skeleton key={idx} className="h-20 rounded-2xl" />)}</div>
                ) : unread.length === 0 ? (
                    <div className="rounded-3xl border border-slate-200 dark:border-white/10 p-8 text-center text-slate-500">No hay respuestas pendientes.</div>
                ) : viewType === 'table' ? (
                    <div className="rounded-2xl border border-slate-200 dark:border-white/10 overflow-hidden"><table className="w-full text-left"><thead className="bg-slate-50 dark:bg-white/5"><tr><th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Respuesta</th><th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400 hidden md:table-cell">Proyecto</th><th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Tipo</th></tr></thead><tbody className="divide-y divide-slate-100 dark:divide-white/5">{unread.map((item) => <tr key={item.id}><td className="px-4 py-3 text-sm font-bold">{item.task_title || 'Actualización'}</td><td className="px-4 py-3 hidden md:table-cell text-[11px] text-slate-500">{item.project}</td><td className="px-4 py-3 text-[11px] text-slate-500">{item.type}</td></tr>)}</tbody></table></div>
                ) : viewType === 'grid' ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">{unread.map((item) => <article key={item.id} className="rounded-2xl border border-slate-200 dark:border-white/10 p-4 bg-slate-50/60 dark:bg-white/5"><p className="text-[10px] font-black uppercase tracking-widest text-blue-600">{item.project}</p><h3 className="text-sm font-black mt-2">{item.task_title || 'Actualización'}</h3><p className="text-sm text-slate-600 dark:text-slate-300 mt-2 line-clamp-3">{item.content}</p></article>)}</div>
                ) : viewType === 'board' || viewType === 'kanban' ? (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">{grouped.map((group) => <section key={group.id} className="rounded-2xl bg-slate-50 dark:bg-white/[0.03] border border-slate-200 dark:border-white/10 p-4"><div className="flex justify-between mb-4"><span className="text-[10px] font-black uppercase tracking-widest text-slate-500">{group.label}</span><span className="text-[10px] font-black text-slate-400">{group.rows.length}</span></div><div className="space-y-3">{group.rows.map((item) => <div key={item.id} className={clsx("rounded-xl border p-3 bg-white dark:bg-white/5", item.type === 'mention' ? "border-amber-200" : "border-slate-100 dark:border-white/5")}><p className="text-sm font-bold">{item.task_title || item.project}</p></div>)}</div></section>)}</div>
                ) : viewType === 'calendar' ? (
                    <UniversalCalendarView events={calendarEvents} title="Calendario de respuestas" />
                ) : viewType === 'gantt' ? (
                    <UniversalGanttView items={ganttItems} moduleName="Respuestas de proyectos" />
                ) : viewType === 'wiki' ? (
                    <UniversalWikiView moduleName="Respuestas de proyectos" storageKey="wiki_projects_responses" />
                ) : (
                    <div className="space-y-3">
                        {unread.map((item) => (
                            <article key={item.id} className="rounded-2xl border border-slate-200 dark:border-white/10 p-4 bg-slate-50/60 dark:bg-white/5">
                                <p className="text-[10px] font-black uppercase tracking-widest text-blue-600">{item.project}</p>
                                <h3 className="text-sm font-black text-slate-800 dark:text-white mt-1">{item.task_title || 'Actualizacion'}</h3>
                                <p className="text-sm text-slate-600 dark:text-slate-300 mt-2">{item.content}</p>
                                <div className="mt-3 flex items-center gap-2">
                                    <button
                                        onClick={() => router.push(`/projects/${item.project_id}`)}
                                        className="px-3 py-1 rounded-lg border border-slate-200 dark:border-white/10 text-[10px] font-black uppercase tracking-widest text-slate-500"
                                    >
                                        Ver proyecto
                                    </button>
                                    <button
                                        onClick={() => resolveItem(item)}
                                        disabled={resolvingId === item.id}
                                        className="px-3 py-1 rounded-lg bg-blue-600 text-white text-[10px] font-black uppercase tracking-widest disabled:opacity-50"
                                    >
                                        {resolvingId === item.id ? 'Resolviendo...' : 'Resolver'}
                                    </button>
                                </div>
                            </article>
                        ))}
                    </div>
                )}
            </main>
        </div>
    );
}

