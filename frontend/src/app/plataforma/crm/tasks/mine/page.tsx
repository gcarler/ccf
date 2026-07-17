"use client";

import React, { useMemo, useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { Search, Calendar, Plus, Users, CheckCircle2, Clock, AlertCircle, Loader2, MoreHorizontal } from 'lucide-react';
import CrmShell from '@/components/crm/CrmShell';
import AdminHero from '@/components/admin/AdminHero';
import CommunityQuickCommentCard from '@/components/community/QuickCommentCard';
import { formatDueLabel } from '@/lib/community/utils';
import { apiFetch } from '@/lib/http';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { CrmTask } from '@/types/crm';

const priorityTone: Record<string, string> = {
    'urgent': 'bg-rose-100 text-rose-600 border-rose-200 dark:bg-rose-900/20 dark:border-rose-800',
    'high': 'bg-orange-100 text-orange-600 border-orange-200 dark:bg-orange-900/20 dark:border-orange-800',
    'normal': 'bg-blue-100 text-[hsl(var(--primary))] border-blue-200 dark:bg-blue-900/20 dark:border-blue-800',
    'low': 'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] border-[hsl(var(--border))] dark:bg-[hsl(var(--surface-2))] dark:border-[hsl(var(--border))]'
};

const statusTone: Record<string, string> = {
    'todo': 'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] border-[hsl(var(--border))] dark:bg-[hsl(var(--surface-2))]',
    'done': 'bg-emerald-100 text-emerald-600 border-emerald-200 dark:bg-emerald-900/20 dark:border-emerald-800'
};

export default function MyTasks() {
    const { isAuthenticated, token, loading: authLoading } = useAuth();
    const { addToast } = useToast();
    const router = useRouter();
    const [activeTab, setActiveTab] = useState('pending');
    const [tasks, setTasks] = useState<CrmTask[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [reloadKey, setReloadKey] = useState(0);

    const fetchTasks = useCallback(async () => {
        if (!token) {
            setLoading(false);
            setError("Debes iniciar sesión para ver tus tareas.");
            return;
        }
        setLoading(true);
        try {
            setError(null);
            const data = await apiFetch<CrmTask[]>('/crm/tasks/mine', { token, cache: 'no-store' });
            setTasks(Array.isArray(data) ? data : []);
        } catch (err) {
            setTasks([]);
            setError("No se pudieron cargar tus tareas pastorales.");
            addToast("Error al cargar tareas pastorales", "error");
        } finally {
            setLoading(false);
        }
    }, [token, addToast]);

    useEffect(() => {
        if (!authLoading && isAuthenticated) fetchTasks();
    }, [authLoading, fetchTasks, isAuthenticated, reloadKey]);

    const filteredTasks = useMemo(() => {
        return tasks.filter(t => 
            activeTab === 'completed' ? t.status === 'done' : t.status !== 'done'
        );
    }, [activeTab, tasks]);

    const stats = useMemo(() => ({
        pending: tasks.filter(t => t.status !== 'done').length,
        overdue: tasks.filter(t => t.status !== 'done' && t.due_date && new Date(t.due_date) < new Date()).length
    }), [tasks]);

    if (authLoading) {
        return <div className="p-4 text-center animate-pulse font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Verificando sesión...</div>;
    }

    if (!isAuthenticated) return null;

    return (
        <CrmShell
            breadcrumbs={[{ label: 'CCF', icon: Calendar }, { label: 'Consolidación', icon: Users }, { label: 'Mis tareas', icon: Calendar }]}
            rightActions={
                <button className="flex size-8 items-center justify-center rounded-md bg-primary/10 text-primary hover:bg-primary/20 transition-all">
                    <Search size={20} />
                </button>
            }
        >
        {error && (
            <div className="mb-4 flex flex-col gap-3 rounded-md border border-amber-200 bg-amber-50 p-4 text-amber-900 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-200 md:flex-row md:items-center md:justify-between">
                <div>
                    <p className="text-[11px] font-bold uppercase tracking-wide">No se pudieron cargar las tareas</p>
                    <p className="text-xs">{error}</p>
                </div>
                <button
                    onClick={() => setReloadKey(key => key + 1)}
                    className="rounded-md border border-amber-300 px-3 py-1.5 text-[11px] font-bold uppercase tracking-wide hover:bg-amber-100 dark:border-amber-400/30 dark:hover:bg-amber-500/20"
                >
                    Reintentar
                </button>
            </div>
        )}
        <style jsx global>{`
            .task-aura {
                position: relative;
            }
            .task-aura::after {
                content: '';
                position: absolute;
                inset: -1px;
                background: linear-gradient(45deg, var(--aura-color, #3b82f620), transparent 60%);
                z-index: -1;
                border-radius: inherit;
                opacity: 0;
                transition: opacity 0.5s ease;
            }
            .task-aura:hover::after {
                opacity: 1;
            }
            .metal-shimmer-bar {
                position: relative;
                overflow: hidden;
            }
            .metal-shimmer-bar::after {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 50%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
                animation: shimmer-anim 3s infinite;
            }
            @keyframes shimmer-anim {
                0% { left: -100%; }
                100% { left: 200%; }
            }
        `}</style>

        <AdminHero
            eyebrow="Tareas de Consolidación"
            title="Mi Agenda de Seguimiento"
            description="Gestiona tus compromisos pastorales, visitas y llamadas con el respaldo de Optimus Brain."
            tags={['Enfoque', 'Consolidación', 'Fidelidad']}
            watchers={['Equipo de Consolidación', 'Optimus Brain']}
            primaryAction={{ label: 'Asignar nuevas', icon: Plus, onClick: () => router.push('/plataforma/crm/tasks/assign') }}
            secondaryAction={{ label: 'Refrescar', icon: Clock, onClick: fetchTasks }}
        />

        <div className="space-y-4">
            {/* Summary Cards Cinematic */}
            <section className="flex gap-4 overflow-x-auto hide-scrollbar">
                <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex-1 min-w-[240px] bg-gradient-to-br from-blue-600 to-sky-700 rounded-md p-4 text-white shadow-2xl shadow-blue-500/20 relative overflow-hidden group"
                >
                    <div className="absolute top-0 right-0 -mr-10 -mt-3 size-10 bg-white/10 rounded-full blur-3xl group-hover:bg-white/20 transition-all duration-700"></div>
                    <div className="flex items-center gap-3 mb-3 relative z-10">
                        <div className="p-2 bg-white/10 rounded-md backdrop-blur-md border border-white/10"><CheckCircle2 size={18} /></div>
                        <span className="text-[10px] font-bold uppercase tracking-wide text-blue-100">Tareas Pendientes</span>
                    </div>
                    <h3 className="text-xl font-bold mb-2 relative z-10 tracking-tighter">{stats.pending}</h3>
                    <p className="text-[10px] font-bold text-blue-100/60 uppercase tracking-wide relative z-10">Compromisos activos</p>
                </motion.div>

                <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="flex-1 min-w-[240px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5 rounded-md p-4 shadow-sm relative overflow-hidden group task-aura"
                    style={{ '--aura-color': 'rgba(244, 63, 94, 0.15)' } as any}
                >
                    <div className="flex items-center gap-3 mb-3">
                        <div className="p-2 bg-rose-50 dark:bg-rose-900/20 rounded-md text-rose-500 border border-rose-100 dark:border-rose-800"><AlertCircle size={18} /></div>
                        <span className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Vencidas</span>
                    </div>
                    <h3 className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white mb-2 tracking-tighter">{stats.overdue}</h3>
                    <p className="text-[10px] font-bold text-rose-500 uppercase tracking-wide">Requiere atención</p>
                </motion.div>
            </section>

            {/* List View Cinematic */}
            <section className="space-y-3 bg-[hsl(var(--surface-1))] dark:bg-[#1e1f21] rounded-lg p-4 shadow-2xl shadow-black/10/50 dark:shadow-none border border-[hsl(var(--border))] dark:border-white/5">
                <div className="flex flex-wrap items-center justify-between gap-4">
                    <div className="flex p-1 bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-lg">
                        {[
                            { id: 'pending', label: 'Pendientes' },
                            { id: 'completed', label: 'Completadas' }
                        ].map((tab) => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={clsx(
                                    "px-4 py-2 rounded-md text-[11px] font-bold uppercase tracking-wide transition-all",
                                    activeTab === tab.id ? "bg-[hsl(var(--surface-1))] dark:bg-[hsl(var(--surface-2))] text-[hsl(var(--primary))] shadow-sm" : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))]"
                                )}
                            >
                                {tab.label}
                            </button>
                        ))}
                    </div>
                    <div className="relative w-full md:w-64">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" size={16} />
                        <input className="w-full pl-11 pr-4 py-2.5 rounded-md border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 outline-none focus:ring-2 focus:ring-blue-500/20 transition-all text-xs font-bold" placeholder="Buscar en mi agenda..." />
                    </div>
                </div>

                <CommunityQuickCommentCard
                    title="Registra tus notas de seguimiento pastoral aquí."
                    description="Las notas se vinculan automáticamente a la Hoja de Vida del persona."
                />

                <div className="rounded-md border border-[hsl(var(--border))] dark:border-white/5 overflow-hidden bg-[hsl(var(--surface-1))]/30 dark:bg-transparent">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center py-1.5 gap-4">
                            <Loader2 className="animate-spin text-[hsl(var(--primary))]" size={32} />
                            <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Sincronizando tareas pastorales...</p>
                        </div>
                    ) : filteredTasks.length > 0 ? (
                        <div className="overflow-x-auto">
                            <table className="w-full text-left border-collapse">
                                <thead>
                                    <tr className="bg-[hsl(var(--surface-1))]/80 dark:bg-white/5 border-b border-[hsl(var(--border))] dark:border-white/5">
                                        <th className="px-3 py-2 text-[9px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Actividad</th>
                                        <th className="px-3 py-2 text-[9px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Contacto Vinc.</th>
                                        <th className="px-3 py-2 text-[9px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Límite</th>
                                        <th className="px-3 py-2 text-[9px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Prioridad</th>
                                        <th className="px-3 py-2 text-[9px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide text-right">Estado</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-[hsl(var(--border))] dark:divide-white/5 bg-[hsl(var(--surface-1))] dark:bg-transparent">
                                    <AnimatePresence mode="popLayout">
                                        {filteredTasks.map((task, idx) => (
                                            <motion.tr 
                                                layout
                                                initial={{ opacity: 0, x: -20 }}
                                                animate={{ opacity: 1, x: 0 }}
                                                transition={{ delay: idx * 0.05 }}
                                                key={task.id} 
                                                className="group hover:bg-[hsl(var(--surface-1))]/50 dark:hover:bg-white/5 transition-all cursor-pointer"
                                            >
                                                <td className="px-3 py-2">
                                                    <div className="flex items-center gap-4">
                                                        <div className="size-2 rounded-full bg-[hsl(var(--primary))] shadow-[0_0_8px_rgba(59,130,246,0.5)]"></div>
                                                        <div>
                                                            <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] tracking-tight uppercase">{task.title}</p>
                                                            <p className="text-[10px] text-[hsl(var(--text-secondary))] font-bold line-clamp-1">{task.description || 'Sin descripción adicional'}</p>
                                                        </div>
                                                    </div>
                                                </td>
                                                <td className="px-3 py-2">
                                                    <div className="flex items-center gap-2">
                                                        <div className="size-7 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))] group-hover:bg-[hsl(var(--primary))] group-hover:text-white transition-all duration-500">
                                                            <Users size={14} />
                                                        </div>
                                                        <span className="text-[11px] font-bold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] uppercase tracking-tight">{task.contact_name}</span>
                                                    </div>
                                                </td>
                                                <td className="px-3 py-2">
                                                    <span className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">{task.due_date ? formatDueLabel(task.due_date) : 'Abierto'}</span>
                                                </td>
                                                <td className="px-3 py-2">
                                                    <span className={clsx("px-3 py-1 rounded-lg text-[8px] font-bold uppercase tracking-wide border", priorityTone[task.priority.toLowerCase()] || priorityTone.normal)}>
                                                        {task.priority}
                                                    </span>
                                                </td>
                                                <td className="px-3 py-2 text-right">
                                                    <div className="flex items-center justify-end gap-3">
                                                        <span className={clsx("px-3 py-1 rounded-lg text-[8px] font-bold uppercase tracking-wide", statusTone[task.status] || statusTone.todo)}>
                                                            {task.status === 'done' ? 'Completada' : 'Pendiente'}
                                                        </span>
                                                        <button className="p-2 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 rounded-md text-[hsl(var(--text-secondary))] transition-all"><MoreHorizontal size={16} /></button>
                                                    </div>
                                                </td>
                                            </motion.tr>
                                        ))}
                                    </AnimatePresence>
                                </tbody>
                            </table>
                        </div>
                    ) : (
                        <div className="py-1.5 flex flex-col items-center justify-center text-center space-y-4">
                            <div className="size-8 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))]"><CheckCircle2 size={32} strokeWidth={1} /></div>
                            <div className="space-y-1">
                                <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] uppercase tracking-tight">Todo al día</p>
                                <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide leading-loose">No tienes tareas pendientes en esta categoría.</p>
                            </div>
                        </div>
                    )}
                </div>
            </section>
        </div>
        </CrmShell>
    );
}
