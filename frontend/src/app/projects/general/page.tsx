"use client";

import React, { useEffect, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ProjectActivityItem, ProjectRecord } from '@/types/projects';
import { Hash, Layout } from 'lucide-react';
import Skeleton from '@/components/ui/Skeleton';

export default function ProjectsGeneralPage() {
    const { token } = useAuth();
    const [activities, setActivities] = useState<ProjectActivityItem[]>([]);
    const [projects, setProjects] = useState<ProjectRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const [projectId, setProjectId] = useState<number | ''>('');
    const [content, setContent] = useState('');
    const [saving, setSaving] = useState(false);

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

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in font-display">
            <WorkspaceToolbar
                breadcrumbs={[{ label: 'Proyectos', icon: Layout }, { label: 'Canal General', icon: Hash }]}
                viewType="list"
                setViewType={() => {}}
            />
            <main className="flex-1 overflow-y-auto p-6 lg:p-8">
                <section className="rounded-2xl border border-slate-200 dark:border-white/10 p-4 bg-slate-50 dark:bg-white/5 mb-5">
                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2">Publicar en canal</p>
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
                        <select
                            value={projectId}
                            onChange={(event) => setProjectId(Number(event.target.value))}
                            className="rounded-xl border border-slate-200 dark:border-white/10 px-3 py-2 bg-white dark:bg-black/20"
                        >
                            {projects.map((project) => (
                                <option key={project.id} value={project.id}>{project.title}</option>
                            ))}
                        </select>
                        <input
                            value={content}
                            onChange={(event) => setContent(event.target.value)}
                            placeholder="Escribe una actualización para el canal general..."
                            className="md:col-span-2 rounded-xl border border-slate-200 dark:border-white/10 px-3 py-2 bg-white dark:bg-black/20"
                        />
                        <button
                            onClick={postMessage}
                            disabled={saving || !projectId || !content.trim()}
                            className="rounded-xl bg-blue-600 text-white text-[10px] font-black uppercase tracking-widest disabled:opacity-50"
                        >
                            {saving ? 'Publicando...' : 'Publicar'}
                        </button>
                    </div>
                </section>
                {loading ? (
                    <div className="space-y-3">{[1, 2, 3, 4].map((idx) => <Skeleton key={idx} className="h-20 rounded-2xl" />)}</div>
                ) : (
                    <div className="space-y-3">
                        {activities.map((activity) => (
                            <article key={activity.id} className="rounded-2xl border border-slate-200 dark:border-white/10 p-4 bg-slate-50 dark:bg-white/5">
                                <p className="text-[10px] font-black uppercase tracking-widest text-blue-600">{activity.project_title}</p>
                                <h3 className="font-black text-slate-800 dark:text-white mt-1">{activity.task_title || 'Actividad'}</h3>
                                <p className="text-sm text-slate-600 dark:text-slate-300 mt-2">{activity.description}</p>
                            </article>
                        ))}
                        {activities.length === 0 && (
                            <div className="rounded-3xl border border-slate-200 dark:border-white/10 p-8 text-center text-slate-500">Sin novedades para mostrar.</div>
                        )}
                    </div>
                )}
            </main>
        </div>
    );
}

