"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { 
    Wrench, 
    AlertCircle, 
    CheckCircle2, 
    Plus, 
    Clock, 
    Shield,
    History,
    Zap,
    Loader2,
    Database,
    ShieldCheck
} from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ViewType } from '@/components/ViewSwitcher';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';

const MAINTENANCE_VIEWS: ViewType[] = ['grid', 'list', 'table', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];


interface MaintenanceTask {
    id: string | number;
    item?: string;
    task?: string;
    date?: string;
    priority?: string;
    status?: string;
}

export default function AdminMaintenancePage() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const [tasks, setTasks] = useState<MaintenanceTask[]>([]);
    const [loading, setLoading] = useState(true);
    const [stats] = useState({ operative: 85, healthy: 105, review: 12, out: 7 });
    const [viewType, setViewType] = useState<ViewType>('grid');

    const fetchData = useCallback(async (signal?: AbortSignal) => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch<MaintenanceTask[]>('/assets/maintenance-tasks', { token, cache: 'no-store', signal });
            setTasks(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error(err);
            addToast("Error al sincronizar agenda técnica", "error");
        } finally {
            setLoading(false);
        }
    }, [token, addToast]);

    useEffect(() => {
        if (!isAuthenticated) return;
        const controller = new AbortController();
        fetchData(controller.signal);
        return () => controller.abort();
    }, [isAuthenticated, fetchData]);

    if (!isAuthenticated) return null;

    const visibleTasks = tasks.length > 0 ? tasks : [
        { id: 'sample-1', item: 'Sistema de sonido principal', task: 'Revisión preventiva', date: '2026-05-16', priority: 'Media' },
        { id: 'sample-2', item: 'Red administrativa', task: 'Auditoría de conectividad', date: '2026-05-18', priority: 'Alta' },
        { id: 'sample-3', item: 'Base de datos', task: 'Backup y verificación', date: '2026-05-20', priority: 'Media' },
    ];

    const groupedTasks = [
        { id: 'high', label: 'Alta', items: visibleTasks.filter(row => row.priority === 'Alta') },
        { id: 'medium', label: 'Media', items: visibleTasks.filter(row => row.priority !== 'Alta') },
    ];

    const calendarEvents = visibleTasks.map((row, index) => ({
        id: row.id || index,
        title: row.item || row.task || 'Mantenimiento',
        date: (row.date || new Date().toISOString()).split('T')[0],
        color: row.priority === 'Alta' ? 'rose' as const : 'amber' as const,
        location: row.task,
    }));

    const ganttItems = visibleTasks.map((row, index) => ({
        id: row.id || index,
        title: row.item || 'Activo',
        subtitle: row.task || 'Mantenimiento',
        start_date: row.date || new Date().toISOString(),
        end_date: row.date || new Date().toISOString(),
        color: row.priority === 'Alta' ? 'rose' as const : 'amber' as const,
        progress: row.priority === 'Alta' ? 35 : 65,
    }));

    const renderList = () => (
        <div className="space-y-4">
            {visibleTasks.map((row, index) => (
                <div key={row.id || index} className="bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5 rounded-lg p-3 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                    <div className="flex items-center gap-3">
                        <div className={clsx("size-7 rounded-lg flex items-center justify-center", row.priority === 'Alta' ? "bg-rose-50 text-rose-500" : "bg-amber-50 text-amber-500")}>
                            <AlertCircle size={24} />
                        </div>
                        <div>
                            <h3 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tight">{row.item}</h3>
                            <p className="text-[10px] text-[hsl(var(--text-secondary))] font-bold uppercase tracking-wide">{row.task}</p>
                        </div>
                    </div>
                    <span className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{new Date(row.date).toLocaleDateString('es-ES')}</span>
                </div>
            ))}
        </div>
    );

    const renderTable = () => (
        <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 overflow-x-auto bg-[hsl(var(--bg-primary))] dark:bg-white/5">
            <table className="w-full min-w-[480px] text-left">
                <thead className="bg-[hsl(var(--surface-1))] dark:bg-white/5">
                    <tr>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Activo</th>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hidden md:table-cell">Tarea</th>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hidden lg:table-cell">Fecha</th>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Prioridad</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-[hsl(var(--border))] dark:divide-white/5">
                    {visibleTasks.map((row, index) => (
                        <tr key={row.id || index} className="hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.03]">
                            <td className="px-3 py-1.5 text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{row.item}</td>
                            <td className="px-3 py-1.5 hidden md:table-cell text-[11px] text-[hsl(var(--text-secondary))]">{row.task}</td>
                            <td className="px-3 py-1.5 hidden lg:table-cell text-[11px] text-[hsl(var(--text-secondary))]">{new Date(row.date).toLocaleDateString('es-ES')}</td>
                            <td className="px-3 py-1.5"><span className={clsx("px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase", row.priority === 'Alta' ? "bg-rose-50 text-rose-600" : "bg-amber-50 text-amber-600")}>{row.priority}</span></td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );

    const renderBoard = () => (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {groupedTasks.map((group) => (
                <section key={group.id} className="rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/[0.03] border border-[hsl(var(--border))] dark:border-white/10 p-3">
                    <div className="flex items-center justify-between mb-5">
                        <span className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Prioridad {group.label}</span>
                        <span className="font-semibold text-[hsl(var(--text-secondary))]">{group.items.length}</span>
                    </div>
                    <div className="space-y-4">
                        {group.items.map((row, index) => (
                            <div key={row.id || index} className="bg-[hsl(var(--bg-primary))] dark:bg-white/[0.05] border border-[hsl(var(--border))] dark:border-white/5 rounded-lg p-3">
                                <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tight">{row.item}</p>
                                <p className="mt-2 text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">{row.task}</p>
                            </div>
                        ))}
                    </div>
                </section>
            ))}
        </div>
    );

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] overflow-hidden animate-fade-in font-display">
            <style jsx global>{`
                .aura-tech {
                    position: relative;
                }
                .aura-tech::after {
                    content: '';
                    position: absolute;
                    inset: -1px;
                    background: linear-gradient(45deg, rgba(245, 158, 11, 0.1), transparent 60%);
                    z-index: -1;
                    border-radius: inherit;
                    opacity: 0;
                    transition: opacity 0.5s ease;
                }
                .aura-tech:hover::after {
                    opacity: 1;
                }
                .shimmer-health {
                    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
                    background-size: 200% 100%;
                    animation: shimmer-h 3s infinite linear;
                }
                @keyframes shimmer-h {
                    0% { background-position: -200% 0; }
                    100% { background-position: 200% 0; }
                }
            `}</style>

            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'Admin', icon: Shield }, { label: 'Mantenimiento Técnico', icon: Wrench }]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={MAINTENANCE_VIEWS}
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-4 relative">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#f59e0b05_0%,_transparent_50%)] pointer-events-none" />

 <div className="w-full space-y-3 relative z-10">
                    {/* Cinematic Header */}
                    <div className="flex flex-col md:flex-row md:items-end justify-between gap-3">
                        <div className="space-y-4">
                            <motion.div 
                                initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
                                className="inline-flex items-center gap-2 px-4 py-1.5 bg-amber-500/10 text-amber-600 dark:text-amber-500 rounded-full text-[10px] font-semibold uppercase tracking-wide border border-amber-500/20"
                            >
                                <Zap size={12} className="animate-pulse" /> Protocolo de Salud Activa
                            </motion.div>
                            <h1 className="text-xl lg:text-xl font-bold tracking-tighter text-[hsl(var(--text-primary))] dark:text-white uppercase leading-none italic">
                                Agenda de <span className="text-amber-500">Mantenimiento</span>
                            </h1>
                            <p className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] text-lg font-medium max-w-xl leading-relaxed">
                                Supervisión técnica en tiempo real. Asegura la disponibilidad del 100% de la infraestructura ministerial.
                            </p>
                        </div>

                        <motion.button 
                            whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                            className="px-4 py-1.5 bg-amber-500 hover:bg-amber-600 text-[hsl(var(--text-primary))] text-[11px] font-semibold uppercase tracking-wide rounded-lg transition-all shadow-2xl shadow-amber-500/20 flex items-center gap-3 group"
                        >
                            <Plus size={18} className="group-hover:rotate-90 transition-transform duration-500" /> Programar Revisión
                        </motion.button>
                    </div>

                    {viewType === 'list' ? (
                        renderList()
                    ) : viewType === 'table' ? (
                        renderTable()
                    ) : viewType === 'board' || viewType === 'kanban' ? (
                        renderBoard()
                    ) : viewType === 'calendar' ? (
                        <UniversalCalendarView events={calendarEvents} title="Calendario de mantenimiento" />
                    ) : viewType === 'gantt' ? (
                        <UniversalGanttView items={ganttItems} moduleName="Mantenimiento técnico" />
                    ) : viewType === 'wiki' ? (
                        <UniversalWikiView moduleName="Mantenimiento técnico" storageKey="wiki_admin_maintenance" />
                    ) : (
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
                        {/* Task List Cinematic */}
                        <div className="lg:col-span-8 space-y-3">
                            <div className="bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5 rounded-lg overflow-hidden shadow-sm shadow-black/10/50">
                                <div className="p-4 border-b border-[hsl(var(--border))] dark:border-white/5 bg-[hsl(var(--surface-1))]/50 dark:bg-white/5 flex items-center justify-between">
                                    <h3 className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide flex items-center gap-3">
                                        <History size={16} className="text-amber-500" /> Tareas de Seguimiento Técnico
                                    </h3>
                                    <span className="px-4 py-1 bg-rose-50 dark:bg-rose-900/20 text-rose-600 font-semibold rounded-full border border-rose-100 dark:border-rose-800 uppercase tracking-wide">Estado Crítico: {stats. review}</span>
                                </div>
                                <div className="divide-y divide-[hsl(var(--border))] dark:divide-white/5">
                                    {loading ? (
                                        <div className="p-4 flex flex-col items-center gap-4">
                                            <Loader2 className="animate-spin text-amber-500" size={32} />
                                            <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Sincronizando con Servidor...</p>
                                        </div>
                                    ) : tasks.length > 0 ? tasks.map((row, i) => (
                                        <motion.div 
                                            initial={{ opacity: 0, y: 10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: i * 0.05 }}
                                            key={i} 
                                            className="p-4 hover:bg-[hsl(var(--surface-1))]/50 dark:hover:bg-white/5 transition-all flex items-center justify-between group cursor-pointer"
                                        >
                                            <div className="flex items-center gap-3">
                                                <div className={clsx(
                                                    "size-7 rounded-lg flex items-center justify-center shadow-inner transition-transform group-hover:scale-110 duration-500",
                                                    row.priority === 'Alta' ? "bg-rose-50 dark:bg-rose-900/20 text-rose-500" : "bg-amber-50 dark:bg-amber-900/20 text-amber-500"
                                                )}>
                                                    <AlertCircle size={28} />
                                                </div>
                                                <div>
                                                    <div className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] uppercase tracking-tight group-hover:text-amber-600 transition-colors leading-none mb-2">{row.item}</div>
                                                    <div className="text-[10px] text-[hsl(var(--text-secondary))] font-bold uppercase tracking-wide">{row.task}</div>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <div className="text-right">
                                                    <div className="font-semibold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-wide flex items-center gap-2 justify-end mb-1">
                                                        <Clock size={12} className="text-[hsl(var(--text-secondary))]" /> {new Date(row.date).toLocaleDateString('es-ES', { month: 'short', day: 'numeric' })}
                                                    </div>
                                                    <div className={clsx("text-[9px] font-semibold uppercase tracking-wide", row.priority === 'Alta' ? 'text-rose-500' : 'text-[hsl(var(--text-secondary))]')}>Prioridad {row.priority}</div>
                                                </div>
                                                <button className="size-7 bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg flex items-center justify-center text-[hsl(var(--text-secondary))] hover:bg-emerald-500 hover:text-white hover:border-emerald-500 hover:shadow-xl hover:shadow-emerald-500/20 transition-all duration-500">
                                                    <CheckCircle2 size={20} />
                                                </button>
                                            </div>
                                        </motion.div>
                                    )) : (
                                        <div className="p-4 text-center space-y-4">
                                            <div className="size-8 bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-lg flex items-center justify-center mx-auto text-[hsl(var(--text-secondary))]"><Wrench size={40} strokeWidth={1} /></div>
                                            <p className="text-xs font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">No hay revisiones programadas</p>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Health Radar Sidebar */}
                        <div className="lg:col-span-4 space-y-3">
                            <motion.div 
                                initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}
                                className="bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5 p-4 rounded-lg shadow-sm space-y-3 aura-tech"
                            >
                                <h3 className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide flex items-center gap-3">
                                    <ShieldCheck size={16} className="text-amber-500" /> Salud de Activos
                                </h3>
                                <div className="flex flex-col items-center justify-center py-2 gap-3">
                                    <div className="relative size-10 p-4 rounded-full border-2 border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-center shadow-inner">
                                        <div className="size-full rounded-full bg-gradient-to-tr from-amber-500/5 to-amber-500/20 animate-pulse" />
                                        <div className="absolute inset-0 flex flex-col items-center justify-center">
                                            <span className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white italic tracking-tighter">{stats.operative}%</span>
                                            <span className="font-semibold text-emerald-500 uppercase tracking-wide mt-1">Óptimo</span>
                                        </div>
                                        {/* Circular Progress Simulated */}
                                        <svg className="absolute inset-0 size-full -rotate-90">
                                            <circle cx="88" cy="88" r="84" fill="none" stroke="currentColor" strokeWidth="8" className="text-amber-500/10" />
                                            <circle cx="88" cy="88" r="84" fill="none" stroke="currentColor" strokeWidth="8" strokeDasharray="527" strokeDashoffset={527 - (527 * stats.operative) / 100} strokeLinecap="round" className="text-amber-500 shadow-[0_0_15px_rgba(245,158,11,0.5)]" />
                                        </svg>
                                    </div>
                                </div>
                                <div className="space-y-4 pt-4">
                                    <HealthRow label="Equipos al día" value={stats.healthy} color="emerald" />
                                    <HealthRow label="En revisión" value={stats.review} color="amber" />
                                    <HealthRow label="Fuera de servicio" value={stats.out} color="rose" />
                                </div>
                            </motion.div>

                            <div className="bg-[hsl(var(--bg-muted))] p-4 rounded-lg text-white space-y-3 relative overflow-hidden group shadow-2xl">
                                <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:rotate-12 transition-transform duration-1000"><Database size={80} /></div>
                                <h3 className="text-xs font-semibold uppercase tracking-wide relative z-10">Data Integrity</h3>
                                <p className="text-[13px] text-[hsl(var(--text-secondary))] font-medium leading-relaxed relative z-10 italic">
                                    &quot;El mantenimiento preventivo ahorra un 40% en costos de reposición anual.&quot;
                                </p>
                                <button className="w-full py-1.5 bg-white/5 hover:bg-white/10 text-white text-[10px] font-semibold uppercase tracking-wide rounded-lg transition-all border border-white/10 relative z-10">
                                    Descargar Reporte Anual
                                </button>
                            </div>
                        </div>
                    </div>
                    )}
                </div>
            </main>
        </div>
    );
}

function HealthRow({ label, value, color }: { label: string, value: number, color: 'emerald' | 'amber' | 'rose' }) {
    const tones = {
        emerald: 'text-emerald-500 bg-emerald-50 dark:bg-emerald-900/20',
        amber: 'text-amber-500 bg-amber-50 dark:bg-amber-900/20',
        rose: 'text-rose-500 bg-rose-50 dark:bg-rose-900/20'
    };
    return (
        <div className="flex justify-between items-center p-4 bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-lg border border-[hsl(var(--border))] dark:border-white/5">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">{label}</span>
            <span className={clsx("px-3 py-1 rounded-lg text-xs font-semibold", tones[color])}>{value}</span>
        </div>
    );
}

