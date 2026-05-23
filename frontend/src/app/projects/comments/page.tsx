"use client";

import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ViewType } from '@/components/ViewSwitcher';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import type { ProjectCommentItem, ProjectRecord } from '@/types/projects';
import { Layout, MessageCircle } from 'lucide-react';
import Skeleton from '@/components/ui/Skeleton';
import clsx from 'clsx';

const COMMENT_VIEWS: ViewType[] = ['list', 'table', 'grid', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];

export default function ProjectsCommentsPage() {
    const { token } = useAuth();
    const [comments, setComments] = useState<ProjectCommentItem[]>([]);
    const [projects, setProjects] = useState<ProjectRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [projectId, setProjectId] = useState<number | ''>('');
    const [content, setContent] = useState('');
    const [viewType, setViewType] = useState<ViewType>('list');

    const loadData = async () => {
        if (!token) return;
        try {
            const [commentRows, projectRows] = await Promise.all([
                apiFetch<ProjectCommentItem[]>('/projects/comments?unresolved_only=true&limit=120', { token, cache: 'no-store' }),
                apiFetch<ProjectRecord[]>('/projects?limit=200', { token, cache: 'no-store' }),
            ]);
            setComments(Array.isArray(commentRows) ? commentRows : []);
            const projectList = Array.isArray(projectRows) ? projectRows : [];
            setProjects(projectList);
            if (!projectId && projectList.length > 0) {
                setProjectId(projectList[0].id);
            }
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadData();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [token]);

    const grouped = useMemo(() => {
        return comments.reduce<Record<number, ProjectCommentItem[]>>((acc, comment) => {
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
            console.error(error);
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
            console.error(error);
        }
    };

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in font-display">
            <WorkspaceToolbar
                breadcrumbs={[{ label: 'Proyectos', icon: Layout }, { label: 'Comentarios asignados', icon: MessageCircle }]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={COMMENT_VIEWS}
            />
            <main className="flex-1 overflow-y-auto p-4 space-y-3">
                <section className="rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50 dark:bg-white/5">
                    <h2 className="text-sm font-bold uppercase tracking-wide text-slate-500 mb-2">Nuevo comentario</h2>
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                        <select
                            value={projectId}
                            onChange={(event) => setProjectId(Number(event.target.value))}
                            className="md:col-span-1 rounded-md border border-slate-200 dark:border-white/10 px-3 py-2 bg-white dark:bg-black/20"
                        >
                            {projects.map((project) => (
                                <option key={project.id} value={project.id}>{project.title}</option>
                            ))}
                        </select>
                        <input
                            value={content}
                            onChange={(event) => setContent(event.target.value)}
                            placeholder="Escribe un comentario para el proyecto..."
                            className="md:col-span-2 rounded-md border border-slate-200 dark:border-white/10 px-3 py-2 bg-white dark:bg-black/20"
                        />
                        <button
                            onClick={handleSubmit}
                            disabled={saving || !projectId || !content.trim()}
                            className="md:col-span-1 rounded-md bg-blue-600 text-white text-[11px] font-semibold uppercase tracking-wide disabled:opacity-50"
                        >
                            {saving ? 'Guardando...' : 'Publicar'}
                        </button>
                    </div>
                </section>

                {loading ? (
                    <div className="space-y-3">{[1, 2, 3, 4].map((idx) => <Skeleton key={idx} className="h-20 rounded-lg" />)}</div>
                ) : comments.length === 0 ? (
                    <div className="rounded-lg border border-slate-200 dark:border-white/10 p-4 text-center text-slate-500">Sin comentarios pendientes.</div>
                ) : viewType === 'table' ? (
                    <div className="rounded-lg border border-slate-200 dark:border-white/10 overflow-hidden"><table className="w-full text-left"><thead className="bg-slate-50 dark:bg-white/5"><tr><th className="px-3 py-2 text-[10px] font-bold uppercase tracking-wide text-slate-400">Autor</th><th className="px-3 py-2 text-[10px] font-bold uppercase tracking-wide text-slate-400 hidden md:table-cell">Comentario</th><th className="px-3 py-2 text-[10px] font-bold uppercase tracking-wide text-slate-400">Estado</th></tr></thead><tbody className="divide-y divide-slate-100 dark:divide-white/5">{comments.map((item) => <tr key={item.id}><td className="px-3 py-2 text-sm font-medium">{item.author_name}</td><td className="px-3 py-2 hidden md:table-cell text-[11px] text-slate-500">{item.content}</td><td className="px-3 py-2"><span className={clsx("px-2 py-0.5 rounded-full text-[9px] font-bold uppercase", item.is_resolved ? "bg-emerald-50 text-emerald-600" : "bg-blue-50 text-blue-600")}>{item.is_resolved ? 'Resuelto' : 'Pendiente'}</span></td></tr>)}</tbody></table></div>
                ) : viewType === 'grid' ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">{comments.map((item) => <article key={item.id} className="rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-white dark:bg-white/5"><p className="text-[11px] font-bold text-slate-500 uppercase tracking-wide">{item.author_name}</p><p className="text-sm mt-1">{item.content}</p></article>)}</div>
                ) : viewType === 'board' || viewType === 'kanban' ? (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">{[false, true].map((resolved) => <section key={String(resolved)} className="rounded-lg bg-slate-50 dark:bg-white/[0.03] border border-slate-200 dark:border-white/10 p-3"><div className="flex justify-between mb-3"><span className="text-[10px] font-bold uppercase tracking-wide text-slate-500">{resolved ? 'Resueltos' : 'Pendientes'}</span><span className="text-[10px] font-bold text-slate-400">{comments.filter((item) => item.is_resolved === resolved).length}</span></div><div className="space-y-2">{comments.filter((item) => item.is_resolved === resolved).map((item) => <div key={item.id} className="rounded-md bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 p-2 text-sm">{item.content}</div>)}</div></section>)}</div>
                ) : viewType === 'calendar' ? (
                    <UniversalCalendarView events={calendarEvents} title="Calendario de comentarios" />
                ) : viewType === 'gantt' ? (
                    <UniversalGanttView items={ganttItems} moduleName="Comentarios de proyectos" />
                ) : viewType === 'wiki' ? (
                    <UniversalWikiView moduleName="Comentarios de proyectos" storageKey="wiki_projects_comments" />
                ) : (
                    <div className="space-y-3">
                        {Object.entries(grouped).map(([pid, rows]) => {
                            const project = projects.find((p) => p.id === Number(pid));
                            return (
                                <section key={pid} className="space-y-2">
                                    <h3 className="text-xs font-bold uppercase tracking-wide text-blue-600">{project?.title || `Proyecto #${pid}`}</h3>
                                    {rows.map((item) => (
                                        <article key={item.id} className="rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-white dark:bg-white/5">
                                            <p className="font-semibold text-slate-500 uppercase tracking-wide">{item.author_name}</p>
                                            <p className="text-sm text-slate-700 dark:text-slate-200 mt-2">{item.content}</p>
                                            <div className="mt-3 flex items-center justify-between">
                                                <span className="text-[10px] text-slate-400">{new Date(item.created_at).toLocaleString('es-PE')}</span>
                                                <button
                                                    onClick={() => resolveComment(item)}
                                                    disabled={item.is_resolved}
                                                    className="px-3 py-1 rounded-lg bg-blue-600 text-white text-[10px] font-semibold uppercase tracking-wide disabled:opacity-50"
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
        </div>
    );
}

