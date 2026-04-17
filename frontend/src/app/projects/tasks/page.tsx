"use client";

import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ProjectTaskRecord } from '@/types/projects';
import { CheckCircle2, Layout } from 'lucide-react';
import clsx from 'clsx';
import Skeleton from '@/components/ui/Skeleton';

const STATUS_FLOW = ['todo', 'in_progress', 'review', 'done'];

export default function ProjectsTasksPage() {
    const { token } = useAuth();
    const [tasks, setTasks] = useState<ProjectTaskRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const [status, setStatus] = useState<'all' | 'todo' | 'in_progress' | 'review' | 'done'>('all');

    useEffect(() => {
        const load = async () => {
            if (!token) return;
            try {
                const data = await apiFetch<ProjectTaskRecord[]>('/projects/tasks', { token, cache: 'no-store' });
                setTasks(Array.isArray(data) ? data : []);
            } catch (error) {
                console.error(error);
            } finally {
                setLoading(false);
            }
        };
        load();
    }, [token]);

    const filtered = useMemo(() => {
        if (status === 'all') return tasks;
        return tasks.filter((task) => task.status === status);
    }, [tasks, status]);

    const moveForward = async (task: ProjectTaskRecord) => {
        const index = STATUS_FLOW.indexOf(task.status || 'todo');
        const nextStatus = STATUS_FLOW[Math.min(index + 1, STATUS_FLOW.length - 1)];
        if (!nextStatus || nextStatus === task.status) return;
        try {
            const updated = await apiFetch<ProjectTaskRecord>(`/projects/tasks/${task.id}`, {
                method: 'PATCH',
                token,
                body: { status: nextStatus },
            });
            setTasks((prev) => prev.map((row) => (row.id === task.id ? updated : row)));
        } catch (error) {
            console.error(error);
        }
    };

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in font-display">
            <WorkspaceToolbar
                breadcrumbs={[{ label: 'Proyectos', icon: Layout }, { label: 'Mis tareas', icon: CheckCircle2 }]}
                viewType="list"
                setViewType={() => {}}
            />

            <div className="px-6 py-3 border-b border-slate-200 dark:border-white/10 flex flex-wrap gap-2">
                {['all', 'todo', 'in_progress', 'review', 'done'].map((value) => (
                    <button
                        key={value}
                        onClick={() => setStatus(value as any)}
                        className={clsx(
                            'px-3 py-1 rounded-full text-[10px] uppercase tracking-widest font-black border',
                            status === value
                                ? 'bg-blue-600 text-white border-blue-600'
                                : 'border-slate-200 dark:border-white/10 text-slate-500'
                        )}
                    >
                        {value}
                    </button>
                ))}
            </div>

            <main className="flex-1 overflow-y-auto p-6 lg:p-8">
                {loading ? (
                    <div className="space-y-3">{[1, 2, 3, 4].map((idx) => <Skeleton key={idx} className="h-20 rounded-2xl" />)}</div>
                ) : filtered.length === 0 ? (
                    <div className="rounded-3xl border border-slate-200 dark:border-white/10 p-8 text-center text-slate-500">No hay tareas para este filtro.</div>
                ) : (
                    <div className="space-y-3">
                        {filtered.map((task) => (
                            <article key={task.id} className="rounded-2xl border border-slate-200 dark:border-white/10 p-4 bg-white dark:bg-white/5">
                                <div className="flex items-center justify-between gap-4">
                                    <div>
                                        <h3 className="font-black text-slate-800 dark:text-white">{task.title}</h3>
                                        <p className="text-xs text-slate-500 uppercase tracking-wider mt-1">Estado: {task.status} · Prioridad: {task.priority}</p>
                                    </div>
                                    <button
                                        onClick={() => moveForward(task)}
                                        className="px-3 py-1 rounded-lg bg-blue-600 text-white text-[10px] uppercase tracking-widest font-black"
                                    >
                                        Siguiente estado
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

