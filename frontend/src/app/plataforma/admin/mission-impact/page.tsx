"use client";

import React, { useState, useEffect } from 'react';
import { 
    Target, 
    Zap, 
    Heart, 
    Globe, 
    Plus, 
    TrendingUp,
    MapPin,
    Sparkles,
    History,
    ArrowUpRight,
    FileText
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ViewType } from '@/components/ViewSwitcher';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import { motion } from 'framer-motion';
import clsx from 'clsx';

const MISSION_VIEWS: ViewType[] = ['grid', 'list', 'table', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];

const IMPACT_ITEMS = [
    { id: 1, title: 'Misión Amazonas 2026', place: 'Leticia, Colombia', metric: '150 Biblias entregadas', date: '2026-05-12', status: 'Activo', tone: 'blue', progress: 70 },
    { id: 2, title: 'Comedor Comunitario Sur', place: 'Barrio El Sol', metric: '200 Almuerzos servidos', date: '2026-05-13', status: 'En seguimiento', tone: 'emerald', progress: 85 },
    { id: 3, title: 'Brigada de Salud Integral', place: 'Vereda La Unión', metric: '80 Atenciones médicas', date: '2026-05-07', status: 'Completado', tone: 'sky', progress: 100 },
];

interface MissionImpactSummary {
    total_personas: number;
    total_familias: number;
    total_donaciones_cop: number;
    total_matriculas: number;
    distribucion: Array<{ label: string; pct: number; desc: string }>;
}

export default function AdminMissionImpactPage() {
    const { isAuthenticated } = useAuth();
    const [stats, setStats] = useState({
        projects: IMPACT_ITEMS.filter((item) => item.status !== 'Completado').length,
        families: 0,
        members: 0,
    });
    const [viewType, setViewType] = useState<ViewType>('grid');

    useEffect(() => {
        let alive = true;
        const loadImpact = async () => {
            try {
                const data = await apiFetch<MissionImpactSummary>('/finance/impact', { cache: 'no-store' });
                if (!alive) return;
                setStats((current) => ({
                    ...current,
                    families: data.total_familias,
                    members: data.total_personas,
                }));
            } catch (err) {
                console.error(err);
            }
        };

        loadImpact();
        return () => {
            alive = false;
        };
    }, []);

    if (!isAuthenticated) return null;

    const calendarEvents = IMPACT_ITEMS.map((item) => ({
        id: item.id,
        title: item.title,
        date: item.date,
        color: item.status === 'Completado' ? 'emerald' as const : item.status === 'En seguimiento' ? 'amber' as const : 'blue' as const,
        location: item.place,
    }));

    const ganttItems = IMPACT_ITEMS.map((item) => ({
        id: item.id,
        title: item.title,
        subtitle: `${item.place} · ${item.metric}`,
        start_date: item.date,
        end_date: item.date,
        color: item.status === 'Completado' ? 'emerald' as const : item.status === 'En seguimiento' ? 'amber' as const : 'blue' as const,
        progress: item.progress,
    }));

    const groupedItems = [
        { id: 'active', label: 'Activo', items: IMPACT_ITEMS.filter(item => item.status === 'Activo') },
        { id: 'tracking', label: 'En seguimiento', items: IMPACT_ITEMS.filter(item => item.status === 'En seguimiento') },
        { id: 'done', label: 'Completado', items: IMPACT_ITEMS.filter(item => item.status === 'Completado') },
    ];

    const renderList = () => (
        <div className="space-y-4">
            {IMPACT_ITEMS.map((item) => (
                <div key={item.id} className="bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-lg p-3 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                    <div className="flex items-center gap-3">
                        <div className="size-7 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-[hsl(var(--primary))] flex items-center justify-center">
                            <MapPin size={24} />
                        </div>
                        <div>
                            <h3 className="text-lg font-bold text-slate-900 dark:text-white uppercase tracking-tight">{item.title}</h3>
                            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wide">{item.place} · {item.date}</p>
                        </div>
                    </div>
                    <div className="text-sm font-semibold text-[hsl(var(--primary))] italic">{item.metric}</div>
                </div>
            ))}
        </div>
    );

    const renderTable = () => (
        <div className="rounded-lg border border-slate-200 dark:border-white/10 overflow-x-auto bg-[hsl(var(--bg-primary))] dark:bg-white/5">
            <table className="w-full min-w-[480px] text-left">
                <thead className="bg-slate-50 dark:bg-white/5">
                    <tr>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">Hito</th>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400 hidden md:table-cell">Lugar</th>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400 hidden lg:table-cell">Métrica</th>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">Estado</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                    {IMPACT_ITEMS.map((item) => (
                        <tr key={item.id} className="hover:bg-slate-50 dark:hover:bg-white/[0.03]">
                            <td className="px-3 py-1.5 text-sm font-bold text-slate-800 dark:text-slate-100">{item.title}</td>
                            <td className="px-3 py-1.5 hidden md:table-cell text-[11px] text-slate-500">{item.place}</td>
                            <td className="px-3 py-1.5 hidden lg:table-cell text-[11px] text-[hsl(var(--primary))] font-bold">{item.metric}</td>
                            <td className="px-3 py-1.5"><span className="px-2 py-0.5 rounded-full bg-blue-50 text-[hsl(var(--primary))] text-[9px] font-semibold uppercase">{item.status}</span></td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );

    const renderBoard = () => (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
            {groupedItems.map((group) => (
                <section key={group.id} className="rounded-lg bg-slate-50 dark:bg-white/[0.03] border border-slate-200 dark:border-white/10 p-3">
                    <div className="flex items-center justify-between mb-5">
                        <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{group.label}</span>
                        <span className="font-semibold text-slate-400">{group.items.length}</span>
                    </div>
                    <div className="space-y-4">
                        {group.items.map((item) => (
                            <div key={item.id} className="bg-[hsl(var(--bg-primary))] dark:bg-white/[0.05] border border-slate-100 dark:border-white/5 rounded-lg p-3">
                                <p className="text-sm font-semibold text-slate-900 dark:text-white uppercase tracking-tight">{item.title}</p>
                                <p className="mt-2 text-[10px] font-bold text-slate-400 uppercase tracking-wide">{item.place}</p>
                                <p className="mt-4 text-xs font-semibold text-[hsl(var(--primary))] italic">{item.metric}</p>
                            </div>
                        ))}
                    </div>
                </section>
            ))}
        </div>
    );

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[#0a0f16] font-display overflow-hidden">
            <style jsx global>{`
                .impact-aura {
                    position: relative;
                }
                .impact-aura::after {
                    content: '';
                    position: absolute;
                    inset: -1px;
                    background: linear-gradient(45deg, rgba(59, 130, 246, 0.1), transparent 60%);
                    z-index: -1;
                    border-radius: inherit;
                    opacity: 0;
                    transition: opacity 0.5s ease;
                }
                .impact-aura:hover::after {
                    opacity: 1;
                }
            `}</style>

            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'Admin', icon: Globe }, { label: 'Impacto Misionero', icon: Target }]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={MISSION_VIEWS}
                rightActions={
                    <button className="flex items-center gap-2 px-3 py-2 bg-[hsl(var(--primary))] text-white rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 active:scale-95 transition-all">
                        <Plus size={14} /> Registrar Hito
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-4 relative pb-4">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#3b82f605_0%,_transparent_50%)] pointer-events-none" />

 <div className="w-full space-y-3 relative z-10">
                    
                    {/* Header Cinematic */}
                    <div className="flex flex-col md:flex-row md:items-end justify-between gap-3">
                        <div className="space-y-4">
                            <motion.div 
                                initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
                                className="inline-flex items-center gap-2 px-4 py-1.5 bg-blue-500/10 text-[hsl(var(--primary))] rounded-full text-[10px] font-semibold uppercase tracking-wide border border-blue-500/20"
                            >
                                <Sparkles size={12} className="animate-pulse" /> Expansión del Reino 2026
                            </motion.div>
                            <h1 className="text-xl lg:text-xl font-bold text-slate-900 dark:text-white tracking-tighter leading-none uppercase italic">
                                Alcance <br/> <span className="text-[hsl(var(--primary))]">Misionero.</span>
                            </h1>
                            <p className="text-lg text-slate-500 dark:text-slate-400 font-medium max-w-xl leading-relaxed">
                                Monitoreo de impacto espiritual y social con métricas operativas reales y bitácoras editoriales de misión.
                            </p>
                        </div>
                    </div>

                    {viewType === 'list' ? (
                        renderList()
                    ) : viewType === 'table' ? (
                        renderTable()
                    ) : viewType === 'board' || viewType === 'kanban' ? (
                        renderBoard()
                    ) : viewType === 'calendar' ? (
                        <UniversalCalendarView events={calendarEvents} title="Calendario de impacto misionero" />
                    ) : viewType === 'gantt' ? (
                        <UniversalGanttView items={ganttItems} moduleName="Impacto misionero" />
                    ) : viewType === 'wiki' ? (
                        <UniversalWikiView moduleName="Impacto misionero" storageKey="wiki_admin_mission_impact" />
                    ) : (
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
                        {/* Stats & Log */}
                        <div className="lg:col-span-8 space-y-3">
                            <section className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                <ImpactStat label="Proyectos Activos" value={stats.projects} icon={Globe} color="blue" />
                                <ImpactStat label="Familias Registradas" value={stats.families} icon={Heart} color="rose" />
                            </section>

                            {/* Activity Log Cinematic */}
                            <section className="bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-lg overflow-hidden shadow-sm hover:shadow-2xl transition-all duration-700">
                                <div className="p-4 border-b border-slate-100 dark:border-white/5 bg-slate-50/50 dark:bg-black/20 flex items-center justify-between">
                                    <h3 className="font-semibold text-slate-400 uppercase tracking-wide flex items-center gap-3">
                                        <History size={16} className="text-[hsl(var(--primary))]" /> Bitácora de Impacto Real
                                    </h3>
                                    <span className="font-semibold text-[hsl(var(--primary))] bg-blue-50 px-3 py-1 rounded-full uppercase tracking-wide border border-blue-100">Hitos editoriales</span>
                                </div>
                                <div className="divide-y divide-slate-50 dark:divide-white/5">
                                    {[
                                        { title: 'Misión Amazonas 2026', place: 'Leticia, Colombia', metric: '150 Biblias entregadas', date: 'Hace 2 días', tone: 'blue' },
                                        { title: 'Comedor Comunitario Sur', place: 'Barrio El Sol', metric: '200 Almuerzos servidos', date: 'Ayer', tone: 'emerald' },
                                        { title: 'Brigada de Salud Integral', place: 'Vereda La Unión', metric: '80 Atenciones médicas', date: 'Hace 1 semana', tone: 'sky' },
                                    ].map((item, i) => (
                                        <motion.div 
                                            key={i} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.1 }}
                                            className="p-4 hover:bg-slate-50/50 dark:hover:bg-white/5 transition-all flex items-center justify-between group cursor-pointer"
                                        >
                                            <div className="flex items-center gap-3">
                                                <div className="size-7 rounded-lg bg-slate-100 dark:bg-white/10 flex items-center justify-center text-slate-400 group-hover:bg-[hsl(var(--primary))] group-hover:text-white transition-all duration-500 shadow-inner">
                                                    <MapPin size={28} />
                                                </div>
                                                <div>
                                                    <h4 className="text-lg font-bold text-slate-800 dark:text-slate-100 uppercase tracking-tight leading-none mb-2">{item.title}</h4>
                                                    <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wide flex items-center gap-2">
                                                        {item.place} • {item.date}
                                                    </p>
                                                </div>
                                            </div>
                                            <div className="text-right">
                                                <p className="text-sm font-semibold text-[hsl(var(--primary))] italic tracking-tight">{item.metric}</p>
                                                <p className="font-semibold text-slate-400 uppercase tracking-wide mt-1">Métrica de Impacto</p>
                                            </div>
                                        </motion.div>
                                    ))}
                                </div>
                            </section>
                        </div>

                        {/* Goals & Predictions Sidebar */}
                        <aside className="lg:col-span-4 space-y-3">
                            <motion.div 
                                initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
                                className="bg-slate-900 p-4 rounded-lg text-white space-y-3 relative overflow-hidden shadow-2xl group"
                            >
                                <div className="absolute top-0 right-0 -mr-16 -mt-16 size-10 bg-blue-600/20 rounded-full blur-3xl group-hover:bg-blue-600/30 transition-all duration-1000" />
                                
                                <h3 className="text-xl font-bold tracking-tight uppercase italic flex items-center gap-3 relative z-10">
                                    <TrendingUp size={20} className="text-[hsl(var(--primary))]" /> Metas Globales
                                </h3>
                                
                                <div className="space-y-3 relative z-10">
                                    <GoalProgress label="Personas registrados" current={stats.members} target={1000} color="bg-[hsl(var(--primary))]" />
                                    <GoalProgress label="Impacto Social" current={12000} target={20000} color="bg-[hsl(var(--primary))]" />
                                    <GoalProgress label="Nuevas Sedes" current={3} target={5} color="bg-emerald-500" />
                                </div>

                                <div className="pt-10 border-t border-white/10 relative z-10">
                                    <div className="p-3 bg-white/5 rounded-lg border border-white/10 flex items-start gap-4">
                                        <Zap size={20} className="text-amber-400 animate-pulse shrink-0" fill="currentColor" />
                                        <p className="text-[11px] font-bold text-slate-400 leading-relaxed uppercase tracking-wider">
                                            Optimus AI: &ldquo;El crecimiento en familias alcanzadas proyecta un cumplimiento de meta del 100% para el tercer trimestre.&rdquo;
                                        </p>
                                    </div>
                                </div>
                            </motion.div>

                            <div className="bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-slate-200 dark:border-white/10 p-4 rounded-lg shadow-sm space-y-3">
                                <h3 className="text-xs font-semibold uppercase tracking-wide dark:text-white">Acciones de Misión</h3>
                                <button className="w-full py-1.5 bg-slate-100 dark:bg-white/5 hover:bg-slate-200 text-slate-600 dark:text-white text-[10px] font-semibold uppercase tracking-wide rounded-lg transition-all border border-slate-200 dark:border-white/10 flex items-center justify-center gap-3 active:scale-95">
                                    <FileText size={16} /> Generar Reporte PDF
                                </button>
                                <button className="w-full py-1.5 bg-[hsl(var(--bg-primary))] dark:bg-transparent text-[hsl(var(--primary))] text-[10px] font-semibold uppercase tracking-wide rounded-lg transition-all border border-blue-100 dark:border-blue-900/30 flex items-center justify-center gap-3 hover:bg-blue-50">
                                    <ArrowUpRight size={16} /> Compartir Avance
                                </button>
                            </div>
                        </aside>
                    </div>
                    )}
                </div>
            </main>
        </div>
    );
}

function ImpactStat({ label, value, icon: Icon, color }: any) {
    const colors: any = {
        blue: 'text-[hsl(var(--primary))] bg-blue-50 dark:bg-blue-900/20 border-blue-100 dark:border-blue-800',
        rose: 'text-rose-600 bg-rose-50 dark:bg-rose-900/20 border-rose-100 dark:border-rose-800'
    };
    return (
        <div className="impact-aura bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] p-4 rounded-lg border border-slate-100 dark:border-white/5 flex items-center gap-3 shadow-sm hover:shadow-2xl transition-all duration-500 group overflow-hidden">
            <div className={clsx("size-8 rounded-lg flex items-center justify-center transition-transform group-hover:rotate-12 duration-500 shadow-inner border", colors[color])}>
                <Icon size={40} strokeWidth={1.5} />
            </div>
            <div>
                <div className="text-lg font-bold text-slate-900 dark:text-white italic tracking-tighter leading-none mb-1">{value}</div>
                <div className="font-semibold text-slate-400 uppercase tracking-wide">{label}</div>
            </div>
        </div>
    );
}

function GoalProgress({ label, current, target, color }: any) {
    const pct = Math.min(100, (current / target) * 100);
    return (
        <div className="space-y-3 group/goal">
            <div className="flex justify-between text-[10px] font-semibold uppercase tracking-wide">
                <span className="text-slate-400 group-hover/goal:text-[hsl(var(--primary))] transition-colors">{label}</span>
                <span className="text-white">{Math.round(pct)}%</span>
            </div>
            <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden shadow-inner">
                <motion.div 
                    initial={{ width: 0 }} animate={{ width: `${pct}%` }} 
                    transition={{ duration: 1.5, ease: "easeOut" }}
                    className={clsx("h-full relative", color)}
                >
                    <div className="absolute inset-0 bg-[linear-gradient(90deg,transparent,rgba(255,255,255,0.2),transparent)] animate-[shimmer_2s_infinite] -skew-x-12" />
                </motion.div>
            </div>
            <div className="text-[9px] font-bold text-slate-500 text-right uppercase tracking-wide">{current.toLocaleString()} / {target.toLocaleString()}</div>
        </div>
    );
}

