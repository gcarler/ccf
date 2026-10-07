"use client";

import React, { useEffect, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import ProjectsShell from '@/components/projects/ProjectsShell';
import ProjectsLoadError from '@/components/projects/ProjectsLoadError';
import type { ViewType } from '@/components/ViewSwitcher';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import type { ProjectActivityItem, ProjectRecord } from '@/types/projects';
import { Hash, Layout } from 'lucide-react';
import { DSSkeleton } from '@/design';
import { toast } from 'sonner';
import { getAllProjects } from '@/lib/projects/api';

const GENERAL_VIEWS: ViewType[] = ['list', 'table', 'grid', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];

export default function ProjectsGeneralPage() {
    const { token, loading: authLoading } = useAuth();
    const [activities, setActivities] = useState<ProjectActivityItem[]>([]);
    const [projects, setProjects] = useState<ProjectRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [loadFailed, setLoadFailed] = useState(false);
    const [loadAttempt, setLoadAttempt] = useState(0);
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
            setLoadFailed(false);
            return;
        }
        setLoading(true);
        try {
            setError(null);
            setLoadFailed(false);
            const [activityRows, projectRows] = await Promise.all([
                apiFetch<ProjectActivityItem[]>('/projects/activities?limit=20', { token, cache: 'no-store' }),
                getAllProjects(token, { cache: 'no-store' }),
            ]);
            setActivities(Array.isArray(activityRows) ? activityRows : []);
            const projectsList = Array.isArray(projectRows) ? projectRows : [];
            setProjects(projectsList);
            if (!projectId && projectsList.length > 0) setProjectId(projectsList[0].id);
        } catch (error) {
            setActivities([]);
            setProjects([]);
            setError('No se pudo cargar el canal general de proyectos.');
            setLoadFailed(true);
            toast.error('Error al cargar el canal general');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (!authLoading) load();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [authLoading, token, loadAttempt]);

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
                <ProjectsLoadError
                    message={error}
                    onRetry={loadFailed ? () => setLoadAttempt((attempt) => attempt + 1) : undefined}
                    className="mx-4 mt-4"
                />
            )}
            <main className="flex-1 overflow-y-auto p-4">
                <section className="rounded-lg border border-[hsl(var(--border))] p-3 bg-[hsl(var(--surface-1))] mb-3">
                    <p className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))] mb-2">Publicar en canal</p>
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
                        <label htmlFor="general-channel-project" className="sr-only">Proyecto del canal</label>
                        <select
                            id="general-channel-project"
                            value={projectId}
                            onChange={(event) => setProjectId(event.target.value)}
                            className="rounded-md border border-[hsl(var(--border))] px-3 py-2 bg-[hsl(var(--surface-1))]"
                        >
                            {projects.map((project) => (
                                <option key={project.id} value={project.id}>{project.title}</option>
                            ))}
                        </select>
                        <label htmlFor="general-channel-content" className="sr-only">Actualización para el canal</label>
                        <input
                            id="general-channel-content"
                            value={content}
                            onChange={(event) => setContent(event.target.value)}
                            placeholder="Escribe una actualización para el canal general..."
                            className="md:col-span-2 rounded-md border border-[hsl(var(--border))] px-3 py-2 bg-[hsl(var(--surface-1))]"
                        />
                        <button
                            onClick={postMessage}
                            disabled={saving || !projectId || !content.trim()}
                            className="rounded-md bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-2xs font-semibold uppercase tracking-wide disabled:opacity-50"
                        >
                            {saving ? 'Publicando...' : 'Publicar'}
                        </button>
                    </div>
                </section>
                {loading ? (
                    <div className="space-y-3">{[1, 2, 3, 4].map((idx) => <DSSkeleton key={idx} className="h-20 rounded-lg" />)}</div>
                ) : !error && viewType === 'table' ? (
                    <div className="rounded-lg border border-[hsl(var(--border))] overflow-x-auto"><table className="w-full min-w-[480px] text-left"><thead className="bg-[hsl(var(--surface-2))]"><tr><th className="px-3 py-2 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">Proyecto</th><th className="px-3 py-2 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))] hidden md:table-cell">Actividad</th></tr></thead><tbody className="divide-y divide-[hsl(var(--border))]">{activities.map((activity) => <tr key={activity.id}><td className="px-3 py-2 text-sm font-medium">{activity.project_title}</td><td className="px-3 py-2 hidden md:table-cell text-xs text-[hsl(var(--muted-foreground))]">{activity.description}</td></tr>)}</tbody></table></div>
                ) : !error && viewType === 'grid' ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">{activities.map((activity) => <article key={activity.id} className="rounded-lg border border-[hsl(var(--border))] p-3 bg-[hsl(var(--surface-1))]"><p className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--primary))]">{activity.project_title}</p><h3 className="font-bold mt-1">{activity.task_title || 'Actividad'}</h3><p className="text-sm mt-1">{activity.description}</p></article>)}</div>
                ) : !error && (viewType === 'board' || viewType === 'kanban') ? (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">{Object.entries(groupedActivities).map(([project, rows]) => <section key={project} className="rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] p-3"><div className="flex justify-between mb-3"><span className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">{project}</span><span className="text-2xs font-bold text-[hsl(var(--muted-foreground))]">{rows.length}</span></div><div className="space-y-2">{rows.map((row) => <div key={row.id} className="rounded-md bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] p-2 text-sm">{row.description}</div>)}</div></section>)}</div>
                ) : !error && viewType === 'calendar' ? (
                    <UniversalCalendarView events={calendarEvents} title="Calendario del canal general" />
                ) : !error && viewType === 'gantt' ? (
                    <UniversalGanttView items={ganttItems} moduleName="Canal general" />
                ) : !error && viewType === 'wiki' ? (
                    <UniversalWikiView moduleName="Canal general" storageKey="wiki_projects_general" />
                ) : !error ? (
                    <div className="space-y-3">
                        {activities.map((activity) => (
                            <article key={activity.id} className="rounded-lg border border-[hsl(var(--border))] p-3 bg-[hsl(var(--surface-1))]">
                                <p className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--primary))]">{activity.project_title}</p>
                                <h3 className="font-bold text-[hsl(var(--foreground))] mt-1">{activity.task_title || 'Actividad'}</h3>
                                <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">{activity.description}</p>
                            </article>
                        ))}
                        {activities.length === 0 && (
                            <div className="rounded-lg border border-[hsl(var(--border))] p-4 text-center text-[hsl(var(--muted-foreground))]">Sin novedades para mostrar.</div>
                        )}
                    </div>
                ) : null}
            </main>
        </ProjectsShell>
    );
}
