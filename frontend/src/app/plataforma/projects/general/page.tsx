"use client";

import React, { useEffect, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ViewType } from '@/components/ViewSwitcher';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import type { ProjectActivityItem, ProjectRecord } from '@/types/projects';
import { Hash, Layout } from 'lucide-react';
import Skeleton from '@/components/ui/Skeleton';

const GENERAL_VIEWS: ViewType[] = ['list', 'table', 'grid', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];

export default function ProjectsGeneralPage() {
    const { token } = useAuth();
    const [activities, setActivities] = useState<ProjectActivityItem[]>([]);
    const [projects, setProjects] = useState<ProjectRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const [projectId, setProjectId] = useState<string | ''>('');
    const [content, setContent] = useState('');
    const [saving, setSaving] = useState(false);
    const [viewType, setViewType] = useState<ViewType>('list');

    const load = async () => {
        if (!token) return;
        try {
            const [activityRows, projectRows] = await Promise.all([
                apiFetch<ProjectActivityItem[]>('/projects/activities?limit=20', { token, cache: 'no-store' }),
                apiFetch<ProjectRecord[]>('/projects?limit=100', { token, cache: 'no-store' }),
            ]);
            setActivities(Array.isArray(activityRows) ? activityRows : []);
            const projectsList = Array.isArray(projectRows) ? projectRows : [];
            setProjects(projectsList);
            if (!projectId && projectsList.length > 0) setProjectId(projectsList[0].id);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        load();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [token]);

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
            console.error(error);
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
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] overflow-hidden animate-fade-in font-display">
            <WorkspaceToolbar
                breadcrumbs={[{ label: 'Proyectos', icon: Layout }, { label: 'Canal General', icon: Hash }]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={GENERAL_VIEWS}
            />
            <main className="flex-1 overflow-y-auto p-4">
                <section className="rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50 dark:bg-white/5 mb-3">
                    <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500 mb-2">Publicar en canal</p>
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
                        <select
                            value={projectId}
                            onChange={(event) => setProjectId(event.target.value)}
                            className="rounded-md border border-slate-200 dark:border-white/10 px-3 py-2 bg-[hsl(var(--bg-primary))] dark:bg-black/20"
                        >
                            {projects.map((project) => (
                                <option key={project.id} value={project.id}>{project.title}</option>
                            ))}
                        </select>
                        <input
                            value={content}
                            onChange={(event) => setContent(event.target.value)}
                            placeholder="Escribe una actualización para el canal general..."
                            className="md:col-span-2 rounded-md border border-slate-200 dark:border-white/10 px-3 py-2 bg-[hsl(var(--bg-primary))] dark:bg-black/20"
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
                    <div className="space-y-3">{[1, 2, 3, 4].map((idx) => <Skeleton key={idx} className="h-20 rounded-lg" />)}</div>
                ) : viewType === 'table' ? (
                    <div className="rounded-lg border border-slate-200 dark:border-white/10 overflow-hidden"><table className="w-full text-left"><thead className="bg-slate-50 dark:bg-white/5"><tr><th className="px-3 py-2 text-[10px] font-bold uppercase tracking-wide text-slate-400">Proyecto</th><th className="px-3 py-2 text-[10px] font-bold uppercase tracking-wide text-slate-400 hidden md:table-cell">Actividad</th></tr></thead><tbody className="divide-y divide-slate-100 dark:divide-white/5">{activities.map((activity) => <tr key={activity.id}><td className="px-3 py-2 text-sm font-medium">{activity.project_title}</td><td className="px-3 py-2 hidden md:table-cell text-[11px] text-slate-500">{activity.description}</td></tr>)}</tbody></table></div>
                ) : viewType === 'grid' ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">{activities.map((activity) => <article key={activity.id} className="rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50 dark:bg-white/5"><p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--primary))]">{activity.project_title}</p><h3 className="font-bold mt-1">{activity.task_title || 'Actividad'}</h3><p className="text-sm mt-1">{activity.description}</p></article>)}</div>
                ) : viewType === 'board' || viewType === 'kanban' ? (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">{Object.entries(groupedActivities).map(([project, rows]) => <section key={project} className="rounded-lg bg-slate-50 dark:bg-white/[0.03] border border-slate-200 dark:border-white/10 p-3"><div className="flex justify-between mb-3"><span className="text-[10px] font-bold uppercase tracking-wide text-slate-500">{project}</span><span className="text-[10px] font-bold text-slate-400">{rows.length}</span></div><div className="space-y-2">{rows.map((row) => <div key={row.id} className="rounded-md bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-slate-100 dark:border-white/5 p-2 text-sm">{row.description}</div>)}</div></section>)}</div>
                ) : viewType === 'calendar' ? (
                    <UniversalCalendarView events={calendarEvents} title="Calendario del canal general" />
                ) : viewType === 'gantt' ? (
                    <UniversalGanttView items={ganttItems} moduleName="Canal general" />
                ) : viewType === 'wiki' ? (
                    <UniversalWikiView moduleName="Canal general" storageKey="wiki_projects_general" />
                ) : (
                    <div className="space-y-3">
                        {activities.map((activity) => (
                            <article key={activity.id} className="rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50 dark:bg-white/5">
                                <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--primary))]">{activity.project_title}</p>
                                <h3 className="font-bold text-slate-800 dark:text-white mt-1">{activity.task_title || 'Actividad'}</h3>
                                <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">{activity.description}</p>
                            </article>
                        ))}
                        {activities.length === 0 && (
                            <div className="rounded-lg border border-slate-200 dark:border-white/10 p-4 text-center text-slate-500">Sin novedades para mostrar.</div>
                        )}
                    </div>
                )}
            </main>
        </div>
    );
}
