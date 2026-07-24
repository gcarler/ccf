"use client";

import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import ProjectsShell from '@/components/projects/ProjectsShell';
import type { ViewType } from '@/components/ViewSwitcher';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import { DSSkeleton } from '@/design';
import type { ProjectInboxItem } from '@/types/projects';
import { useRouter } from 'next/navigation';
import { Inbox, Layout } from 'lucide-react';
import clsx from 'clsx';
import { toast } from 'sonner';

const RESPONSE_VIEWS: ViewType[] = ['list', 'table', 'grid', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];

export default function ProjectsResponsesPage() {
    const { token, loading: authLoading } = useAuth();
    const router = useRouter();
    const [items, setItems] = useState<ProjectInboxItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [resolvingId, setResolvingId] = useState<string | null>(null);
    const [viewType, setViewType] = useState<ViewType>('list');

    useEffect(() => {
        const load = async () => {
            if (!token) {
                setLoading(false);
                setItems([]);
                setError('Debes iniciar sesión para ver las respuestas de proyectos.');
                return;
            }
            try {
                setError(null);
                const data = await apiFetch<ProjectInboxItem[]>('/projects/inbox?unread_only=true', { token, cache: 'no-store' });
                setItems(Array.isArray(data) ? data : []);
            } catch (error) {
                setItems([]);
                setError('No se pudieron cargar las respuestas de proyectos.');
                toast.error("Error inesperado");
                toast.error('Error al cargar respuestas');
            } finally {
                setLoading(false);
            }
        };
        if (!authLoading) load();
    }, [authLoading, token]);

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
            if (item.type === 'task_assigned' && item.task_id) {
                await apiFetch(`/projects/tasks/${item.task_id}`, {
                    method: 'PATCH',
                    token,
                    body: { status: 'completed' },
                });
            }
            await apiFetch(`/projects/inbox/${item.id}/read`, {
                method: 'POST',
                token,
                body: { is_read: true },
            });
            setItems((prev) => prev.map((row) => (row.id === item.id ? { ...row, is_read: true } : row)));
        } catch (error) {
            toast.error("Error inesperado");
            toast.error('Error al resolver respuesta');
        } finally {
            setResolvingId(null);
        }
    };

    return (
        <ProjectsShell
            breadcrumbs={[{ label: 'Proyectos', icon: Layout }, { label: 'Respuestas', icon: Inbox }]}
            viewType={viewType}
            onViewChange={setViewType}
            viewOptions={RESPONSE_VIEWS}
        >

            <main className="flex-1 overflow-y-auto p-4">
                {error && (
                    <div className="mb-3 rounded-lg border border-[hsl(var(--warning)/25%)] bg-warning-soft p-3 text-warning-text dark:border-[hsl(var(--warning)/100%)]/20 dark:bg-[hsl(var(--warning))]/10 dark:text-[hsl(var(--warning))]">
                        <p className="text-[11px] font-bold uppercase tracking-wide">{error}</p>
                    </div>
                )}
                {loading ? (
                    <div className="space-y-3">{[1, 2, 3].map((idx) => <DSSkeleton key={idx} className="h-20 rounded-lg" />)}</div>
                ) : !error && unread.length === 0 ? (
                    <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-4 text-center text-[hsl(var(--text-secondary))]">No hay respuestas pendientes.</div>
                ) : viewType === 'table' ? (
                    <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 overflow-x-auto"><table className="w-full min-w-[480px] text-left"><thead className="bg-[hsl(var(--surface-1))] dark:bg-white/5"><tr><th className="px-3 py-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Respuesta</th><th className="px-3 py-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] hidden md:table-cell">Proyecto</th><th className="px-3 py-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Tipo</th></tr></thead><tbody className="divide-y divide-[hsl(var(--border))] dark:divide-white/5">{unread.map((item) => <tr key={item.id}><td className="px-3 py-2 text-sm font-medium">{item.task_title || 'Actualización'}</td><td className="px-3 py-2 hidden md:table-cell text-[11px] text-[hsl(var(--text-secondary))]">{item.project}</td><td className="px-3 py-2 text-[11px] text-[hsl(var(--text-secondary))]">{item.type}</td></tr>)}</tbody></table></div>
                ) : viewType === 'grid' ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">{unread.map((item) => <article key={item.id} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/60 dark:bg-white/5"><p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--primary))]">{item.project}</p><h3 className="text-sm font-bold mt-1">{item.task_title || 'Actualización'}</h3><p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mt-1 line-clamp-3">{item.content}</p></article>)}</div>
                ) : viewType === 'board' || viewType === 'kanban' ? (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">{grouped.map((group) => <section key={group.id} className="rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/[0.03] border border-[hsl(var(--border))] dark:border-white/10 p-3"><div className="flex justify-between mb-3"><span className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{group.label}</span><span className="text-[10px] font-bold text-[hsl(var(--text-secondary))]">{group.rows.length}</span></div><div className="space-y-2">{group.rows.map((item) => <div key={item.id} className={clsx("rounded-md border p-2 bg-[hsl(var(--bg-primary))] dark:bg-white/5", item.type === 'mention' ? "border-[hsl(var(--warning)/25%)]" : "border-[hsl(var(--border))] dark:border-white/5")}><p className="text-sm font-medium">{item.task_title || item.project}</p></div>)}</div></section>)}</div>
                ) : viewType === 'calendar' ? (
                    <UniversalCalendarView events={calendarEvents} title="Calendario de respuestas" />
                ) : viewType === 'gantt' ? (
                    <UniversalGanttView items={ganttItems} moduleName="Respuestas de proyectos" />
                ) : viewType === 'wiki' ? (
                    <UniversalWikiView moduleName="Respuestas de proyectos" storageKey="wiki_projects_responses" />
                ) : (
                    <div className="space-y-3">
                        {unread.map((item) => (
                            <article key={item.id} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/60 dark:bg-white/5">
                                <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--primary))]">{item.project}</p>
                                <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white mt-1">{item.task_title || 'Actualizacion'}</h3>
                                <p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mt-1">{item.content}</p>
                                <div className="mt-3 flex items-center gap-2">
                                    <button
                                        onClick={() => router.push(`/plataforma/projects/${item.project_id}?view=list`)}
                                        className="px-3 py-1 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]"
                                    >
                                        Ver proyecto
                                    </button>
                                    <button
                                        onClick={() => resolveItem(item)}
                                        disabled={resolvingId === item.id}
                                        className="px-3 py-1 rounded-lg bg-[hsl(var(--primary))] text-white text-[10px] font-semibold uppercase tracking-wide disabled:opacity-50"
                                    >
                                        {resolvingId === item.id ? 'Resolviendo...' : 'Resolver'}
                                    </button>
                                </div>
                            </article>
                        ))}
                    </div>
                )}
            </main>
        </ProjectsShell>
    );
}
