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
    const { token } = useAuth();
    
    const [task, setTask] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !id) return;
        const loadTask = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<any>(`/crm/tasks/${id}`, { token }).catch(() => null);
                setTask(data || {
                    id,
                    title: 'Seguimiento de Consolidación',
                    description: 'Contactar al nuevo miembro para invitarlo al Faro en Casa de su sector.',
                    status: 'pending',
                    priority: 'high',
                    due_date: '2026-04-20',
                    assigned_to: 'Diácono Roberto',
                    category: 'Consolidación'
                });
            } catch (err) {
                toast.error('Error al cargar la tarea pastoral');
            } finally {
                setLoading(false);
            }
        };
        loadTask();
    }, [id, token]);

    if (loading) return <div className="p-20 text-center animate-pulse font-black uppercase tracking-widest text-slate-400">Cargando tarea pastoral...</div>;

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CRM', icon: LayoutDashboard, href: '/crm' },
                { label: 'Tareas de Consolidación', icon: CheckCircle2, href: '/crm/tasks' },
                { label: `TASK-${id}`, icon: CheckCircle2 },
            ]}
        >
            <main className="flex-1 overflow-y-auto p-4 lg:p-4">
                <div className="max-w-4xl mx-auto space-y-3">
                    <header className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                        <div className="space-y-4">
                            <div className="flex items-center gap-3">
                                <DSBadge tone="violet" label={task.category.toUpperCase()} />
                                <DSBadge tone={task.status === 'completed' ? 'emerald' : 'amber'} label={task.status.toUpperCase()} />
                            </div>
                            <h1 className="text-4xl font-black text-slate-900 dark:text-white tracking-tight uppercase leading-none">
                                {task.title}
                            </h1>
                        </div>
                    </header>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                        <div className="lg:col-span-2 space-y-3">
                            <DSCard>
                                <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-4">Detalle de la Actividad</h3>
                                <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                                    {task.description}
                                </p>
                            </DSCard>

                            <DSCard>
                                <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-4">Bitácora de Seguimiento</h3>
                                <div className="space-y-4">
                                    <div className="flex gap-4">
                                        <div className="size-8 rounded-full bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400">
                                            <History size={16} />
                                        </div>
                                        <div className="flex-1 space-y-1">
                                            <p className="text-xs font-bold text-slate-700 dark:text-slate-200">Tarea creada</p>
                                            <p className="text-[10px] text-slate-400 uppercase font-black">12 ABR 2026 · 10:30 AM</p>
                                        </div>
                                    </div>
                                    <div className="h-12 border-l-2 border-slate-100 dark:border-white/5 ml-4" />
                                    <div className="p-4 rounded-2xl bg-slate-50 dark:bg-white/5 border border-dashed border-slate-200 dark:border-white/10 text-center">
                                        <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Esperando actualizaciones...</p>
                                    </div>
                                </div>
                            </DSCard>
                        </div>

                        <aside className="space-y-3">
                            <DSCard>
                                <div className="space-y-3">
                                    <div className="space-y-2">
                                        <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Asignado a</p>
                                        <div className="flex items-center gap-2 p-2 rounded-xl bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5">
                                            <div className="size-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-black text-xs">
                                                {task.assigned_to?.charAt(0)}
                                            </div>
                                            <span className="text-xs font-bold">{task.assigned_to}</span>
                                        </div>
                                    </div>

                                    <div className="space-y-2">
                                        <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Prioridad</p>
                                        <div className={clsx(
                                            'flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-bold',
                                            task.priority === 'high' ? 'bg-rose-500/10 text-rose-600' : 'bg-amber-500/10 text-amber-600'
                                        )}>
                                            <Flag size={14} /> {task.priority.toUpperCase()}
                                        </div>
                                    </div>

                                    <div className="space-y-2">
                                        <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Vencimiento</p>
                                        <div className="flex items-center gap-2 text-xs font-bold text-slate-600 dark:text-slate-400">
                                            <Calendar size={14} /> {new Date(task.due_date).toLocaleDateString()}
                                        </div>
                                    </div>

                                    <button className="w-full py-1.5 bg-emerald-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-emerald-500/20 hover:scale-105 transition-all">
                                        Marcar como Completada
                                    </button>
                                </div>
                            </DSCard>

                            <div className="p-4 bg-slate-900 rounded-xl text-white space-y-4">
                                <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-emerald-400">
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
