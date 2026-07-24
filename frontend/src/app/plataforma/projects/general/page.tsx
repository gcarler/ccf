"use client";

import React, { useEffect, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import ProjectsShell from '@/components/projects/ProjectsShell';
import type { ViewType } from '@/components/ViewSwitcher';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import type { ProjectActivityItem, ProjectRecord } from '@/types/projects';
import { Hash, Layout } from 'lucide-react';
import { DSSkeleton } from '@/design';
import { toast } from 'sonner';

const GENERAL_VIEWS: ViewType[] = ['list', 'table', 'grid', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];

export default function ProjectsGeneralPage() {
    const { token, loading: authLoading } = useAuth();
    const [activities, setActivities] = useState<ProjectActivityItem[]>([]);
    const [projects, setProjects] = useState<ProjectRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [projectId, setProjectId] = useState<string | ''>('');
    const [content, setContent] = useState('');
    const [saving, setSaving] = useState(false);
    const [viewType, setViewType] = useState<ViewType>('list');

    const load = async () => {
        if (!token) {
            setLoading(false);
            setActivities([]);
            setProjects([]);
            setError('Debes iniciar sesión para ver el canal general de proyectos.');
            return;
        }
        try {
            setError(null);
            const [activityRows, projectRows] = await Promise.all([
                apiFetch<ProjectActivityItem[]>('/projects/activities?limit=20', { token, cache: 'no-store' }),
                apiFetch<ProjectRecord[]>('/projects?limit=100', { token, cache: 'no-store' }),
            ]);
            setActivities(Array.isArray(activityRows) ? activityRows : []);
            const projectsList = Array.isArray(projectRows) ? projectRows : [];
            setProjects(projectsList);
            if (!projectId && projectsList.length > 0) setProjectId(projectsList[0].id);
        } catch (error) {
            setActivities([]);
            setProjects([]);
            setError('No se pudo cargar el canal general de proyectos.');
            toast.error("Error inesperado");
            toast.error('Error al cargar el canal general');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (!authLoading) load();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [authLoading, token]);

    const postMessage = async () => {
        if (!token || !projectId || !content.trim()) return;
        setSaving(true);
        try {
            await apiFetch(`/projects/${projectId}/comments`, {
                method: 'POST',
                token,
                body: { content: content.trim() },
            });
            setContent('');
            await load();
        } catch (error) {
            toast.error("Error inesperado");
            toast.error('Error al publicar en el canal');
        } finally {
            setSaving(false);
        }
    };
    const groupedActivities = activities.reduce<Record<string, ProjectActivityItem[]>>((acc, activity) => {
        if (!acc[activity.project_title]) acc[activity.project_title] = [];
        acc[activity.project_title].push(activity);
        return acc;
    }, {});
    const calendarEvents = activities.map((activity) => ({ id: activity.id, title: activity.task_title || activity.project_title, date: activity.created_at.split('T')[0], color: 'blue' as const, location: activity.project_title }));
    const ganttItems = activities.map((activity) => ({ id: activity.id, title: activity.task_title || activity.project_title, subtitle: activity.description, start_date: activity.created_at, end_date: activity.created_at, color: 'blue' as const, progress: 65 }));

    return (
        <ProjectsShell
            breadcrumbs={[{ label: 'Proyectos', icon: Layout }, { label: 'Canal General', icon: Hash }]}
            viewType={viewType}
            onViewChange={setViewType}
            viewOptions={GENERAL_VIEWS}
        >
            {error && (
                <div className="mx-4 mt-4 rounded-md border border-[hsl(var(--warning)/25%)] bg-warning-soft p-3 text-warning-text dark:border-[hsl(var(--warning)/100%)]/20 dark:bg-[hsl(var(--warning))]/10 dark:text-[hsl(var(--warning))]">
                    <p className="text-[11px] font-bold uppercase tracking-wide">{error}</p>
                </div>
            )}
            <main className="flex-1 overflow-y-auto p-4">
                <section className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))] dark:bg-white/5 mb-3">
                    <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2">Publicar en canal</p>
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
                        <select
                            value={projectId}
                            onChange={(event) => setProjectId(event.target.value)}
                            className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-3 py-2 bg-[hsl(var(--bg-primary))] dark:bg-black/20"
                        >
                            {projects.map((project) => (
                                <option key={project.id} value={project.id}>{project.title}</option>
                            ))}
                        </select>
                        <input
                            value={content}
                            onChange={(event) => setContent(event.target.value)}
                            placeholder="Escribe una actualización para el canal general..."
                            className="md:col-span-2 rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-3 py-2 bg-[hsl(var(--bg-primary))] dark:bg-black/20"
                        />
                        <button
                            onClick={postMessage}
                            disabled={saving || !projectId || !content.trim()}
                            className="rounded-md bg-[hsl(var(--primary))] text-white text-[10px] font-semibold uppercase tracking-wide disabled:opacity-50"
                        >
                            {saving ? 'Publicando...' : 'Publicar'}
                        </button>
                    </div>
                </section>
                {loading ? (
                    <div className="space-y-3">{[1, 2, 3, 4].map((idx) => <DSSkeleton key={idx} className="h-20 rounded-lg" />)}</div>
                ) : !error && viewType === 'table' ? (
                    <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 overflow-x-auto"><table className="w-full min-w-[480px] text-left"><thead className="bg-[hsl(var(--surface-1))] dark:bg-white/5"><tr><th className="px-3 py-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Proyecto</th><th className="px-3 py-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] hidden md:table-cell">Actividad</th></tr></thead><tbody className="divide-y divide-[hsl(var(--border))] dark:divide-white/5">{activities.map((activity) => <tr key={activity.id}><td className="px-3 py-2 text-sm font-medium">{activity.project_title}</td><td className="px-3 py-2 hidden md:table-cell text-[11px] text-[hsl(var(--text-secondary))]">{activity.description}</td></tr>)}</tbody></table></div>
                ) : !error && viewType === 'grid' ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">{activities.map((activity) => <article key={activity.id} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))] dark:bg-white/5"><p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--primary))]">{activity.project_title}</p><h3 className="font-bold mt-1">{activity.task_title || 'Actividad'}</h3><p className="text-sm mt-1">{activity.description}</p></article>)}</div>
                ) : !error && (viewType === 'board' || viewType === 'kanban') ? (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">{Object.entries(groupedActivities).map(([project, rows]) => <section key={project} className="rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/[0.03] border border-[hsl(var(--border))] dark:border-white/10 p-3"><div className="flex justify-between mb-3"><span className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{project}</span><span className="text-[10px] font-bold text-[hsl(var(--text-secondary))]">{rows.length}</span></div><div className="space-y-2">{rows.map((row) => <div key={row.id} className="rounded-md bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5 p-2 text-sm">{row.description}</div>)}</div></section>)}</div>
                ) : !error && viewType === 'calendar' ? (
                    <UniversalCalendarView events={calendarEvents} title="Calendario del canal general" />
                ) : !error && viewType === 'gantt' ? (
                    <UniversalGanttView items={ganttItems} moduleName="Canal general" />
                ) : !error && viewType === 'wiki' ? (
                    <UniversalWikiView moduleName="Canal general" storageKey="wiki_projects_general" />
                ) : !error ? (
                    <div className="space-y-3">
                        {activities.map((activity) => (
                            <article key={activity.id} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))] dark:bg-white/5">
                                <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--primary))]">{activity.project_title}</p>
                                <h3 className="font-bold text-[hsl(var(--text-primary))] dark:text-white mt-1">{activity.task_title || 'Actividad'}</h3>
                                <p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mt-1">{activity.description}</p>
                            </article>
                        ))}
                        {activities.length === 0 && (
                            <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-4 text-center text-[hsl(var(--text-secondary))]">Sin novedades para mostrar.</div>
                        )}
                    </div>
                ) : null}
            </main>
        </ProjectsShell>
    );
}
