"use client";

import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import Skeleton from '@/components/ui/Skeleton';
import type { ProjectInboxItem } from '@/types/projects';
import { useRouter } from 'next/navigation';
import { Inbox, Layout } from 'lucide-react';

export default function ProjectsResponsesPage() {
    const { token } = useAuth();
    const router = useRouter();
    const [items, setItems] = useState<ProjectInboxItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [resolvingId, setResolvingId] = useState<string | null>(null);

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
                viewType="list"
                setViewType={() => {}}
            />

            <main className="flex-1 overflow-y-auto p-6 lg:p-8">
                {loading ? (
                    <div className="space-y-3">{[1, 2, 3].map((idx) => <Skeleton key={idx} className="h-20 rounded-2xl" />)}</div>
                ) : unread.length === 0 ? (
                    <div className="rounded-3xl border border-slate-200 dark:border-white/10 p-8 text-center text-slate-500">No hay respuestas pendientes.</div>
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
