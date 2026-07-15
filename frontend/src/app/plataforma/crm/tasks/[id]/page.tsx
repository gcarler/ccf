"use client";

import React, { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { 
    CheckCircle2, 
    Calendar, 
    LayoutDashboard,
    Flag,
    AlertCircle,
    History
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { DSCard } from '@/design/components/DSCard';
import { DSBadge } from '@/design/components/DSBadge';
import CrmShell from '@/components/crm/CrmShell';
import { toast } from 'sonner';
import clsx from 'clsx';

export default function CrmTaskDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const { token, loading: authLoading } = useAuth();
    
    const [task, setTask] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [reloadKey, setReloadKey] = useState(0);

    useEffect(() => {
        if (authLoading) return;
        if (!id) {
            setLoading(false);
            setError('No se encontró la tarea pastoral.');
            return;
        }
        if (!token) {
            setLoading(false);
            setError('Debes iniciar sesión para ver esta tarea pastoral.');
            return;
        }
        const loadTask = async () => {
            try {
                setError(null);
                setLoading(true);
                const data = await apiFetch<any>(`/crm/tasks/${id}`, { token });
                setTask(data);
            } catch (err) {
                console.error(err);
                setTask(null);
                setError('No se pudo cargar la tarea pastoral.');
                toast.error('Error al cargar la tarea pastoral');
            } finally {
                setLoading(false);
            }
        };
        loadTask();
    }, [authLoading, id, reloadKey, token]);

    if (authLoading) {
        return <div className="p-4 text-center animate-pulse font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Verificando sesión...</div>;
    }

    if (!token || error) {
        return (
            <div className="mx-auto flex max-w-xl flex-col items-center gap-3 p-4 text-center">
                <p className="font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                    {error ?? 'Debes iniciar sesión para ver esta tarea pastoral.'}
                </p>
                <button
                    onClick={() => setReloadKey(key => key + 1)}
                    className="rounded-md border border-[hsl(var(--border))] px-3 py-1.5 text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] transition-colors hover:bg-[hsl(var(--surface-1))] dark:border-white/10 dark:hover:bg-white/5"
                >
                    Reintentar
                </button>
            </div>
        );
    }

    if (loading) return <div className="p-4 text-center animate-pulse font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Cargando tarea pastoral...</div>;

    if (!task) {
        return (
            <div className="mx-auto flex max-w-xl flex-col items-center gap-3 p-4 text-center">
                <p className="font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">No se pudo cargar la tarea pastoral.</p>
                <button
                    onClick={() => setReloadKey(key => key + 1)}
                    className="rounded-md border border-[hsl(var(--border))] px-3 py-1.5 text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] transition-colors hover:bg-[hsl(var(--surface-1))] dark:border-white/10 dark:hover:bg-white/5"
                >
                    Reintentar
                </button>
            </div>
        );
    }

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CRM', icon: LayoutDashboard, href: '/plataforma/crm' },
                { label: 'Tareas de Consolidación', icon: CheckCircle2, href: '/plataforma/crm/tasks' },
                { label: `TASK-${id}`, icon: CheckCircle2 },
            ]}
        >
            <main className="flex-1 overflow-y-auto p-4 lg:p-4">
 <div className="w-full space-y-3">
                    <header className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                        <div className="space-y-4">
                            <div className="flex items-center gap-3">
                                <DSBadge tone="blue" label={String(task.category ?? 'general').toUpperCase()} />
                                <DSBadge tone={task.status === 'completed' ? 'emerald' : 'amber'} label={String(task.status ?? 'pending').toUpperCase()} />
                            </div>
                            <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight uppercase leading-none">
                                {task.title}
                            </h1>
                        </div>
                    </header>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                        <div className="lg:col-span-2 space-y-3">
                            <DSCard>
                                <h3 className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-4">Detalle de la Actividad</h3>
                                <p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] leading-relaxed">
                                    {task.description}
                                </p>
                            </DSCard>

                            <DSCard>
                                <h3 className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-4">Bitácora de Seguimiento</h3>
                                <div className="space-y-4">
                                    <div className="flex gap-4">
                                        <div className="size-8 rounded-full bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))]">
                                            <History size={16} />
                                        </div>
                                        <div className="flex-1 space-y-1">
                                            <p className="text-xs font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">Tarea creada</p>
                                            <p className="text-[10px] text-[hsl(var(--text-secondary))] uppercase font-bold">12 ABR 2026 · 10:30 AM</p>
                                        </div>
                                    </div>
                                    <div className="h-8 border-l-2 border-[hsl(var(--border))] dark:border-white/5 ml-4" />
                                    <div className="p-4 rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-dashed border-[hsl(var(--border))] dark:border-white/10 text-center">
                                        <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Esperando actualizaciones...</p>
                                    </div>
                                </div>
                            </DSCard>
                        </div>

                        <aside className="space-y-3">
                            <DSCard>
                                <div className="space-y-3">
                                    <div className="space-y-2">
                                        <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Asignado a</p>
                                        <div className="flex items-center gap-2 p-2 rounded-md bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5">
                                            <div className="size-8 rounded-lg bg-[hsl(var(--primary))] flex items-center justify-center text-white font-bold text-xs">
                                                {task.assigned_to?.charAt(0)}
                                            </div>
                                            <span className="text-xs font-bold">{task.assigned_to}</span>
                                        </div>
                                    </div>

                                    <div className="space-y-2">
                                        <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Prioridad</p>
                                        <div className={clsx(
                                            'flex items-center gap-2 px-3 py-2 rounded-md text-xs font-bold',
                                            task.priority === 'high' ? 'bg-rose-500/10 text-rose-600' : 'bg-amber-500/10 text-amber-600'
                                        )}>
                                            <Flag size={14} /> {String(task.priority ?? 'normal').toUpperCase()}
                                        </div>
                                    </div>

                                    <div className="space-y-2">
                                        <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Vencimiento</p>
                                        <div className="flex items-center gap-2 text-xs font-bold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
                                            <Calendar size={14} /> {new Date(task.due_date).toLocaleDateString()}
                                        </div>
                                    </div>

                                    <button className="w-full py-1.5 bg-[hsl(var(--secondary))] text-white rounded-md text-[10px] font-bold uppercase tracking-wide shadow-lg shadow-[hsl(var(--secondary))/20] hover:scale-105 transition-all">
                                        Marcar como Completada
                                    </button>
                                </div>
                            </DSCard>

                            <div className="p-4 bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] rounded-md border border-[hsl(var(--border-primary))] text-[hsl(var(--text-primary))] space-y-4">
                                <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--secondary))]">
                                    <AlertCircle size={14} /> Optimus Guard
                                </div>
                                <p className="text-[11px] font-bold leading-relaxed opacity-90 italic">
                                    &quot;Esta persona no ha sido contactada en los últimos 7 días. La tarea es prioritaria para evitar la deserción.&quot;
                                </p>
                            </div>
                        </aside>
                    </div>
                </div>
            </main>
        </CrmShell>
    );
}
