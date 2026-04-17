"use client";

import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ProjectCommentItem, ProjectRecord } from '@/types/projects';
import { Layout, MessageCircle } from 'lucide-react';
import Skeleton from '@/components/ui/Skeleton';

export default function ProjectsCommentsPage() {
    const { token } = useAuth();
    const [comments, setComments] = useState<ProjectCommentItem[]>([]);
    const [projects, setProjects] = useState<ProjectRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [projectId, setProjectId] = useState<number | ''>('');
    const [content, setContent] = useState('');

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
                viewType="list"
                setViewType={() => {}}
            />
            <main className="flex-1 overflow-y-auto p-6 lg:p-8 space-y-6">
                <section className="rounded-3xl border border-slate-200 dark:border-white/10 p-5 bg-slate-50 dark:bg-white/5">
                    <h2 className="text-sm font-black uppercase tracking-widest text-slate-500 mb-3">Nuevo comentario</h2>
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                        <select
                            value={projectId}
                            onChange={(event) => setProjectId(Number(event.target.value))}
                            className="md:col-span-1 rounded-xl border border-slate-200 dark:border-white/10 px-3 py-2 bg-white dark:bg-black/20"
                        >
                            {projects.map((project) => (
                                <option key={project.id} value={project.id}>{project.title}</option>
                            ))}
                        </select>
                        <input
                            value={content}
                            onChange={(event) => setContent(event.target.value)}
                            placeholder="Escribe un comentario para el proyecto..."
                            className="md:col-span-2 rounded-xl border border-slate-200 dark:border-white/10 px-3 py-2 bg-white dark:bg-black/20"
                        />
                        <button
                            onClick={handleSubmit}
                            disabled={saving || !projectId || !content.trim()}
                            className="md:col-span-1 rounded-xl bg-blue-600 text-white text-[11px] font-black uppercase tracking-widest disabled:opacity-50"
                        >
                            {saving ? 'Guardando...' : 'Publicar'}
                        </button>
                    </div>
                </section>

                {loading ? (
                    <div className="space-y-3">{[1, 2, 3, 4].map((idx) => <Skeleton key={idx} className="h-20 rounded-2xl" />)}</div>
                ) : comments.length === 0 ? (
                    <div className="rounded-3xl border border-slate-200 dark:border-white/10 p-8 text-center text-slate-500">Sin comentarios pendientes.</div>
                ) : (
                    <div className="space-y-6">
                        {Object.entries(grouped).map(([pid, rows]) => {
                            const project = projects.find((p) => p.id === Number(pid));
                            return (
                                <section key={pid} className="space-y-3">
                                    <h3 className="text-xs font-black uppercase tracking-widest text-blue-600">{project?.title || `Proyecto #${pid}`}</h3>
                                    {rows.map((item) => (
                                        <article key={item.id} className="rounded-2xl border border-slate-200 dark:border-white/10 p-4 bg-white dark:bg-white/5">
                                            <p className="text-[11px] font-black text-slate-500 uppercase tracking-widest">{item.author_name}</p>
                                            <p className="text-sm text-slate-700 dark:text-slate-200 mt-2">{item.content}</p>
                                            <div className="mt-3 flex items-center justify-between">
                                                <span className="text-[10px] text-slate-400">{new Date(item.created_at).toLocaleString('es-PE')}</span>
                                                <button
                                                    onClick={() => resolveComment(item)}
                                                    disabled={item.is_resolved}
                                                    className="px-3 py-1 rounded-lg bg-blue-600 text-white text-[10px] font-black uppercase tracking-widest disabled:opacity-50"
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

