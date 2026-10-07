"use client";

import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import ProjectsShell from '@/components/projects/ProjectsShell';
import ProjectsLoadError from '@/components/projects/ProjectsLoadError';
import type { ViewType } from '@/components/ViewSwitcher';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import type { ProjectCommentItem, ProjectRecord } from '@/types/projects';
import { Layout, MessageCircle } from 'lucide-react';
import { DSSkeleton } from '@/design';
import clsx from 'clsx';
import { toast } from 'sonner';
import { getAllProjects } from '@/lib/projects/api';

const COMMENT_VIEWS: ViewType[] = ['list', 'table', 'grid', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];

export default function ProjectsCommentsPage() {
    const { token, loading: authLoading } = useAuth();
    const [comments, setComments] = useState<ProjectCommentItem[]>([]);
    const [projects, setProjects] = useState<ProjectRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [loadFailed, setLoadFailed] = useState(false);
    const [loadAttempt, setLoadAttempt] = useState(0);
    const [saving, setSaving] = useState(false);
    const [projectId, setProjectId] = useState<string | ''>('');
    const [content, setContent] = useState('');
    const [viewType, setViewType] = useState<ViewType>('list');

    const loadData = async () => {
        if (!token) {
            setLoading(false);
            setComments([]);
            setProjects([]);
            setError('Debes iniciar sesión para ver los comentarios de proyectos.');
            setLoadFailed(false);
            return;
        }
        setLoading(true);
        try {
            setError(null);
            setLoadFailed(false);
            const [commentRows, projectRows] = await Promise.all([
                apiFetch<ProjectCommentItem[]>('/projects/comments?unresolved_only=true&limit=120', { token, cache: 'no-store' }),
                getAllProjects(token, { cache: 'no-store' }),
            ]);
            setComments(Array.isArray(commentRows) ? commentRows : []);
            const projectList = Array.isArray(projectRows) ? projectRows : [];
            setProjects(projectList);
            if (!projectId && projectList.length > 0) {
                setProjectId(projectList[0].id);
            }
        } catch (error) {
            setComments([]);
            setProjects([]);
            setError('No se pudieron cargar los comentarios de proyectos.');
            setLoadFailed(true);
            toast.error('Error al cargar comentarios');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (!authLoading) loadData();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [authLoading, token, loadAttempt]);

    const grouped = useMemo(() => {
        return comments.reduce<Record<string, ProjectCommentItem[]>>((acc, comment) => {
            if (!acc[comment.project_id]) acc[comment.project_id] = [];
            acc[comment.project_id].push(comment);
            return acc;
        }, {});
    }, [comments]);
    const calendarEvents = comments.map((comment) => ({ id: comment.id, title: comment.author_name, date: comment.created_at.split('T')[0], color: comment.is_resolved ? 'emerald' as const : 'blue' as const, location: comment.content }));
    const ganttItems = comments.map((comment) => ({ id: comment.id, title: comment.author_name, subtitle: comment.content, start_date: comment.created_at, end_date: comment.updated_at || comment.created_at, color: comment.is_resolved ? 'emerald' as const : 'blue' as const, progress: comment.is_resolved ? 100 : 35 }));

    const handleSubmit = async () => {
        if (!token || !projectId || !content.trim()) return;
        setSaving(true);
        try {
            const created = await apiFetch<ProjectCommentItem>(`/projects/${projectId}/comments`, {
                method: 'POST',
                token,
                body: { content: content.trim() },
            });
            setComments((prev) => [created, ...prev]);
            setContent('');
        } catch (error) {
            toast.error('Error al publicar comentario');
        } finally {
            setSaving(false);
        }
    };

    const resolveComment = async (comment: ProjectCommentItem) => {
        if (!token) return;
        try {
            const updated = await apiFetch<ProjectCommentItem>(`/projects/comments/${comment.id}`, {
                method: 'PATCH',
                token,
                body: { is_resolved: true },
            });
            setComments((prev) => prev.map((row) => (row.id === updated.id ? updated : row)));
        } catch (error) {
            toast.error('No se pudo resolver el comentario.');
        }
    };

    return (
        <ProjectsShell
            breadcrumbs={[{ label: 'Proyectos', icon: Layout }, { label: 'Comentarios asignados', icon: MessageCircle }]}
            viewType={viewType}
            onViewChange={setViewType}
            viewOptions={COMMENT_VIEWS}
        >
            {error && (
                <ProjectsLoadError
                    message={error}
                    onRetry={loadFailed ? () => setLoadAttempt((attempt) => attempt + 1) : undefined}
                    className="mx-4 mt-4"
                />
            )}
            <main className="flex-1 overflow-y-auto p-4 space-y-3">
                <section className="rounded-lg border border-[hsl(var(--border))] p-3 bg-[hsl(var(--surface-1))]">
                    <h2 className="text-sm font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))] mb-2">Nuevo comentario</h2>
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                        <label htmlFor="project-comment-project" className="sr-only">Proyecto del comentario</label>
                        <select
                            id="project-comment-project"
                            value={projectId}
                            onChange={(event) => setProjectId(event.target.value)}
                            className="md:col-span-1 rounded-md border border-[hsl(var(--border))] px-3 py-2 bg-[hsl(var(--surface-1))]"
                        >
                            {projects.map((project) => (
                                <option key={project.id} value={project.id}>{project.title}</option>
                            ))}
                        </select>
                        <label htmlFor="project-comment-content" className="sr-only">Comentario</label>
                        <input
                            id="project-comment-content"
                            value={content}
                            onChange={(event) => setContent(event.target.value)}
                            placeholder="Escribe un comentario para el proyecto..."
                            className="md:col-span-2 rounded-md border border-[hsl(var(--border))] px-3 py-2 bg-[hsl(var(--surface-1))]"
                        />
                        <button
                            onClick={handleSubmit}
                            disabled={saving || !projectId || !content.trim()}
                            className="md:col-span-1 rounded-md bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-xs font-semibold uppercase tracking-wide disabled:opacity-50"
                        >
                            {saving ? 'Guardando...' : 'Publicar'}
                        </button>
                    </div>
                </section>

                {loading ? (
                    <div className="space-y-3">{[1, 2, 3, 4].map((idx) => <DSSkeleton key={idx} className="h-20 rounded-lg" />)}</div>
                ) : !error && comments.length === 0 ? (
                    <div className="rounded-lg border border-[hsl(var(--border))] p-4 text-center text-[hsl(var(--muted-foreground))]">Sin comentarios pendientes.</div>
                ) : viewType === 'table' ? (
                    <div className="rounded-lg border border-[hsl(var(--border))] overflow-x-auto"><table className="w-full min-w-[480px] text-left"><thead className="bg-[hsl(var(--surface-2))]"><tr><th className="px-3 py-2 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">Autor</th><th className="px-3 py-2 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))] hidden md:table-cell">Comentario</th><th className="px-3 py-2 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">Estado</th></tr></thead><tbody className="divide-y divide-[hsl(var(--border))]">{comments.map((item) => <tr key={item.id}><td className="px-3 py-2 text-sm font-medium">{item.author_name}</td><td className="px-3 py-2 hidden md:table-cell text-xs text-[hsl(var(--muted-foreground))]">{item.content}</td><td className="px-3 py-2"><span className={clsx("px-2 py-0.5 rounded-full text-2xs font-bold uppercase", item.is_resolved ? "bg-[hsl(var(--success)/0.15)] text-[hsl(var(--success,var(--primary)))]" : "bg-[hsl(var(--primary)/0.15)] text-[hsl(var(--primary))]")}>{item.is_resolved ? 'Resuelto' : 'Pendiente'}</span></td></tr>)}</tbody></table></div>
                ) : viewType === 'grid' ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">{comments.map((item) => <article key={item.id} className="rounded-lg border border-[hsl(var(--border))] p-3 bg-[hsl(var(--surface-1))]"><p className="text-xs font-bold text-[hsl(var(--muted-foreground))] uppercase tracking-wide">{item.author_name}</p><p className="text-sm mt-1">{item.content}</p></article>)}</div>
                ) : viewType === 'board' || viewType === 'kanban' ? (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">{[false, true].map((resolved) => <section key={String(resolved)} className="rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] p-3"><div className="flex justify-between mb-3"><span className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">{resolved ? 'Resueltos' : 'Pendientes'}</span><span className="text-2xs font-bold text-[hsl(var(--muted-foreground))]">{comments.filter((item) => item.is_resolved === resolved).length}</span></div><div className="space-y-2">{comments.filter((item) => item.is_resolved === resolved).map((item) => <div key={item.id} className="rounded-md bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] p-2 text-sm">{item.content}</div>)}</div></section>)}</div>
                ) : viewType === 'calendar' ? (
                    <UniversalCalendarView events={calendarEvents} title="Calendario de comentarios" />
                ) : viewType === 'gantt' ? (
                    <UniversalGanttView items={ganttItems} moduleName="Comentarios de proyectos" />
                ) : viewType === 'wiki' ? (
                    <UniversalWikiView moduleName="Comentarios de proyectos" storageKey="wiki_projects_comments" />
                ) : (
                    <div className="space-y-3">
                        {Object.entries(grouped).map(([pid, rows]) => {
                            const project = projects.find((p) => p.id === pid);
                            return (
                                <section key={pid} className="space-y-2">
                                    <h3 className="text-xs font-bold uppercase tracking-wide text-[hsl(var(--primary))]">{project?.title || `Proyecto #${pid}`}</h3>
                                    {rows.map((item) => (
                                        <article key={item.id} className="rounded-lg border border-[hsl(var(--border))] p-3 bg-[hsl(var(--surface-1))]">
                                            <p className="font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wide">{item.author_name}</p>
                                            <p className="text-sm text-[hsl(var(--foreground))] mt-2">{item.content}</p>
                                            <div className="mt-3 flex items-center justify-between">
                                                <span className="text-2xs text-[hsl(var(--muted-foreground))]">{new Date(item.created_at).toLocaleString('es-PE')}</span>
                                                <button
                                                    onClick={() => resolveComment(item)}
                                                    disabled={item.is_resolved}
                                                    className="px-3 py-1 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-2xs font-semibold uppercase tracking-wide disabled:opacity-50"
                                                >
                                                    {item.is_resolved ? 'Resuelto' : 'Resolver'}
                                                </button>
                                            </div>
                                        </article>
                                    ))}
                                </section>
                            );
                        })}
                    </div>
                )}
            </main>
        </ProjectsShell>
    );
}
