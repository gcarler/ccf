"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { 
    Award, 
    Plus, 
    ChevronRight, 
    Zap,
    Heart,
    Star,
    Sparkles,
    Flame,
    Check
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ViewType } from '@/components/ViewSwitcher';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2 } from 'lucide-react';

const iconMap: Record<string, any> = {
    'zap': Zap,
    'flame': Flame,
    'star': Star,
    'award': Award,
    'sparkles': Sparkles,
    'heart': Heart
};
const MILESTONE_VIEWS: ViewType[] = ['grid', 'list', 'table', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];

export default function SpiritualMilestones() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const [milestones, setMilestones] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [viewType, setViewType] = useState<ViewType>('grid');

    const fetchMilestones = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch<any[]>('/admin/milestones', { token, cache: 'no-store' });
            setMilestones(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error(err);
            addToast("Error al sincronizar hitos", "error");
        } finally {
            setLoading(false);
        }
    }, [token, addToast]);

    useEffect(() => {
        if (isAuthenticated) fetchMilestones();
    }, [isAuthenticated, fetchMilestones]);

    if (!isAuthenticated) return null;

    const groupedMilestones = [
        { id: 'high', label: 'Alto alcance', rows: milestones.filter((m) => (m.count || 0) >= 100) },
        { id: 'growth', label: 'En crecimiento', rows: milestones.filter((m) => (m.count || 0) < 100) },
    ];

    const calendarEvents = milestones.map((m, index) => ({
        id: m.id,
        title: m.name,
        date: (m.created_at || new Date(Date.now() + index * 86400000).toISOString()).split('T')[0],
        color: (m.count || 0) >= 100 ? 'emerald' as const : 'blue' as const,
        location: `${m.count || 0} personas`,
    }));

    const ganttItems = milestones.map((m, index) => {
        const date = m.created_at || new Date(Date.now() + index * 86400000).toISOString();
        return {
            id: m.id,
            title: m.name,
            subtitle: `${m.xp || 0} XP · ${m.count || 0} personas`,
            start_date: date,
            end_date: date,
            color: (m.count || 0) >= 100 ? 'emerald' as const : 'blue' as const,
            progress: Math.min(100, Math.max(20, Number(m.count || 0))),
        };
    });

    const renderList = () => (
        <div className="space-y-4">
            {milestones.map((m) => {
                const Icon = iconMap[m.icon?.toLowerCase()] || Award;
                return (
                    <div key={m.id} className="bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-lg p-3 flex items-center justify-between gap-5">
                        <div className="flex items-center gap-5">
                            <div className="size-7 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-600 flex items-center justify-center"><Icon size={24} /></div>
                            <div>
                                <h3 className="text-sm font-semibold text-slate-900 dark:text-white uppercase tracking-tight">{m.name}</h3>
                                <p className="mt-1 text-[10px] font-bold text-slate-400 uppercase tracking-wide">{m.description || 'Hito ministerial'}</p>
                            </div>
                        </div>
                        <span className="font-semibold text-blue-600 uppercase tracking-wide">{m.count} personas</span>
                    </div>
                );
            })}
        </div>
    );

    const renderTable = () => (
        <div className="rounded-lg border border-slate-200 dark:border-white/10 overflow-hidden bg-white dark:bg-white/5">
            <table className="w-full text-left">
                <thead className="bg-slate-50 dark:bg-white/5">
                    <tr>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">Hito</th>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400 hidden md:table-cell">Descripción</th>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400 hidden lg:table-cell">XP</th>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">Alcance</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                    {milestones.map((m) => (
                        <tr key={m.id} className="hover:bg-slate-50 dark:hover:bg-white/[0.03]">
                            <td className="px-3 py-1.5 text-sm font-bold text-slate-800 dark:text-slate-100">{m.name}</td>
                            <td className="px-3 py-1.5 hidden md:table-cell text-[11px] text-slate-500">{m.description || '—'}</td>
                            <td className="px-3 py-1.5 hidden lg:table-cell text-[11px] text-blue-600 font-bold">{m.xp || 0}</td>
                            <td className="px-3 py-1.5 font-semibold text-slate-500">{m.count || 0}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );

    const renderBoard = () => (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {groupedMilestones.map((group) => (
                <section key={group.id} className="rounded-lg bg-slate-50 dark:bg-white/[0.03] border border-slate-200 dark:border-white/10 p-3">
                    <div className="flex items-center justify-between mb-5">
                        <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{group.label}</span>
                        <span className="font-semibold text-slate-400">{group.rows.length}</span>
                    </div>
                    <div className="space-y-3">
                        {group.rows.map((m) => (
                            <div key={m.id} className="bg-white dark:bg-white/[0.05] border border-slate-100 dark:border-white/5 rounded-lg p-4">
                                <p className="text-sm font-semibold text-slate-900 dark:text-white uppercase tracking-tight">{m.name}</p>
                                <p className="mt-2 text-[10px] font-bold text-slate-400">{m.count || 0} personas · {m.xp || 0} XP</p>
                            </div>
                        ))}
                    </div>
                </section>
            ))}
        </div>
    );

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#0a0f16] font-display overflow-hidden">
            <style jsx global>{`
                .milestone-aura {
                    position: relative;
                }
                .milestone-aura::after {
                    content: '';
                    position: absolute;
                    inset: -1px;
                    background: linear-gradient(45deg, var(--aura-color, #3b82f610), transparent 60%);
                    z-index: -1;
                    border-radius: inherit;
                    opacity: 0;
                    transition: opacity 0.5s ease;
                }
                .milestone-aura:hover::after {
                    opacity: 1;
                }
            `}</style>

            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'Vida Espiritual', icon: Heart }, { label: 'Insignias e Hitos', icon: Award }]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={MILESTONE_VIEWS}
                rightActions={
                    <button className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 active:scale-95 transition-all">
                        <Plus size={14} /> Nueva Insignia
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-4 relative pb-4">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#3b82f605_0%,_transparent_50%)] pointer-events-none" />

                <div className="max-w-6xl mx-auto space-y-3 relative z-10">
                    
                    {/* Header Cinematic */}
                    <header className="space-y-4">
                        <motion.div 
                            initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
                            className="inline-flex items-center gap-2 px-4 py-1.5 bg-blue-500/10 text-blue-600 rounded-full text-[10px] font-semibold uppercase tracking-wide border border-blue-500/20"
                        >
                            <Sparkles size={12} className="animate-pulse" /> Reconocimiento del Crecimiento
                        </motion.div>
                        <h1 className="text-xl lg:text-xl font-bold text-slate-900 dark:text-white tracking-tighter leading-none">
                            Consola de <br/> <span className="text-blue-600 italic">Hitos de Fe.</span>
                        </h1>
                    </header>

                    <AnimatePresence mode="wait">
                        {loading ? (
                            <div className="py-1.5 flex flex-col items-center justify-center gap-3 text-slate-400 font-semibold uppercase tracking-wide animate-pulse">
                                <Loader2 className="animate-spin text-blue-600" size={48} strokeWidth={1.5} /> Sincronizando Conquistas...
                            </div>
                        ) : viewType === 'list' ? (
                            renderList()
                        ) : viewType === 'table' ? (
                            renderTable()
                        ) : viewType === 'board' || viewType === 'kanban' ? (
                            renderBoard()
                        ) : viewType === 'calendar' ? (
                            <UniversalCalendarView events={calendarEvents} title="Calendario de hitos" />
                        ) : viewType === 'gantt' ? (
                            <UniversalGanttView items={ganttItems} moduleName="Hitos de fe" />
                        ) : viewType === 'wiki' ? (
                            <UniversalWikiView moduleName="Hitos de fe" storageKey="wiki_admin_milestones" />
                        ) : (
                            <div className="space-y-3">
                                {/* Milestone Summary Cards */}
                                <section className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                    {milestones.map((m, i) => {
                                        const Icon = iconMap[m.icon?.toLowerCase()] || Award;
                                        return (
                                            <motion.div 
                                                key={m.id}
                                                initial={{ opacity: 0, scale: 0.95 }}
                                                animate={{ opacity: 1, scale: 1 }}
                                                transition={{ delay: i * 0.05 }}
                                                className="milestone-aura group bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 p-4 rounded-lg shadow-sm hover:shadow-2xl transition-all duration-500 overflow-hidden"
                                                style={{ '--aura-color': 'rgba(59, 130, 246, 0.15)' } as any}
                                            >
                                                <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:scale-125 transition-transform duration-1000">
                                                    <Icon size={120} />
                                                </div>
                                                
                                                <div className="relative z-10 space-y-3">
                                                    <div className="size-8 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-600 flex items-center justify-center shadow-inner group-hover:rotate-12 transition-transform duration-500">
                                                        <Icon size={32} strokeWidth={1.5} />
                                                    </div>
                                                    <div>
                                                        <p className="font-semibold text-slate-400 uppercase tracking-wide mb-2">{m.description || 'Hito Ministerial'}</p>
                                                        <h3 className="text-xl font-bold text-slate-900 dark:text-white uppercase tracking-tighter leading-none mb-1">{m.name}</h3>
                                                        <p className="text-[11px] font-bold text-blue-500 uppercase tracking-wide">{m.count} Personas Alcanzadas</p>
                                                    </div>
                                                    <div className="pt-6 border-t border-slate-50 dark:border-white/5 flex items-center justify-between">
                                                        <span className="font-semibold text-slate-400 uppercase tracking-wide">+ {m.xp} XP Recompensa</span>
                                                        <button className="font-semibold text-blue-600 uppercase tracking-wide flex items-center gap-2 hover:scale-105 transition-transform">
                                                            Gestionar <ChevronRight size={14} />
                                                        </button>
                                                    </div>
                                                </div>
                                            </motion.div>
                                        );
                                    })}
                                </section>

                                {/* Bulk Action Area Cinematic */}
                                <section className="bg-slate-900 p-4 lg:p-4 rounded-lg text-white relative overflow-hidden group shadow-2xl">
                                    <div className="absolute top-0 right-0 -mr-20 -mt-20 size-96 bg-blue-600/20 rounded-full blur-[120px] group-hover:bg-blue-600/30 transition-all duration-1000" />
                                    
                                    <div className="relative z-10 grid grid-cols-1 lg:grid-cols-2 gap-3 items-center">
                                        <div className="space-y-3">
                                            <div className="space-y-4">
                                                <div className="flex items-center gap-3 text-blue-400 font-semibold uppercase tracking-wide text-[10px]">
                                                    <Zap size={16} fill="currentColor" /> Optimus Brain Processing
                                                </div>
                                                <h2 className="text-lg lg:text-xl font-bold tracking-tighter leading-none uppercase">Registro Masivo <br/> <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-400 italic">de Conquistas.</span></h2>
                                            </div>
                                            <p className="text-lg text-slate-400 font-medium leading-relaxed max-w-xl italic">
                                                &ldquo;Sube la nómina de vencedores y Optimus Brain se encargará de estampar los certificados digitales y actualizar las Hojas de Vida instantáneamente.&rdquo;
                                            </p>
                                            <div className="flex flex-wrap gap-4">
                                                <button className="px-4 py-2 bg-white text-slate-900 rounded-lg font-black text-xs uppercase tracking-wide shadow-2xl hover:translate-y-[-4px] active:scale-95 transition-all">Iniciar Protocolo</button>
                                                <button className="px-4 py-2 bg-white/5 backdrop-blur-md border border-white/10 text-white rounded-lg font-black text-xs uppercase tracking-wide hover:bg-white/10 transition-all">Ver Plantillas</button>
                                            </div>
                                        </div>
                                        <div className="hidden lg:flex justify-center relative">
                                            <div className="size-10 rounded-lg border-4 border-blue-500/20 flex items-center justify-center animate-pulse">
                                                <div className="size-10 rounded-lg bg-blue-600 flex items-center justify-center shadow-[0_0_50px_rgba(37,99,235,0.4)]">
                                                    <Check size={80} strokeWidth={3} className="text-white" />
                                                </div>
                                            </div>
                                            <div className="absolute -bottom-6 -right-6 p-3 bg-white rounded-lg shadow-2xl text-slate-900">
                                                <Award size={40} className="text-blue-600" />
                                            </div>
                                        </div>
                                    </div>
                                </section>
                            </div>
                        )}
                    </AnimatePresence>
                </div>
            </main>
        </div>
    );
}

