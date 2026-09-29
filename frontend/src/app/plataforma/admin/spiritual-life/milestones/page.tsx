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
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import { motion, AnimatePresence } from 'framer-motion';
import type { LucideIcon } from 'lucide-react';
import { Loader2 } from 'lucide-react';
import type { CSSAuraProperties } from '@/types/admin';

const iconMap: Record<string, LucideIcon> = {
    'zap': Zap,
    'flame': Flame,
    'star': Star,
    'award': Award,
    'sparkles': Sparkles,
    'heart': Heart
};
// Drift #3: una insignia (Medalla) es un catálogo, no un evento fechado.
// Las vistas calendar/gantt inventaban fechas con `Date.now()+index*86400000`
// que no corresponden a ningún dato real. Se eliminan ambas vistas; el
// catálogo se sigue sirviendo con grid/list/table/board/kanban/wiki.
const MILESTONE_VIEWS: ViewType[] = ['grid', 'list', 'table', 'board', 'kanban', 'wiki'];


interface Milestone {
    id: string | number;
    title: string;
    name: string;
    description?: string;
    icon?: string;
    xp?: number;
    count?: number;
    target_date?: string;
    status?: string;
    progress?: number;
    created_at?: string;
}

export default function SpiritualMilestones() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const [milestones, setMilestones] = useState<Milestone[]>([]);
    const [loading, setLoading] = useState(true);
    const [viewType, setViewType] = useState<ViewType>('grid');

    const fetchMilestones = useCallback(async (signal?: AbortSignal) => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch<{ items: Milestone[]; total: number }>('/admin/milestones', { token, cache: 'no-store', signal });
            setMilestones(data?.items ?? []);
        } catch (err) {
            console.error(err);
            addToast("Error al sincronizar hitos", "error");
        } finally {
            setLoading(false);
        }
    }, [token, addToast]);

    useEffect(() => {
        if (!isAuthenticated) return;
        const controller = new AbortController();
        fetchMilestones(controller.signal);
        return () => controller.abort();
    }, [isAuthenticated, fetchMilestones]);

    if (!isAuthenticated) return null;

    const groupedMilestones = [
        { id: 'high', label: 'Alto alcance', rows: milestones.filter((m) => (m.count || 0) >= 100) },
        { id: 'growth', label: 'En crecimiento', rows: milestones.filter((m) => (m.count || 0) < 100) },
    ];

    const renderList = () => (
        <div className="space-y-4">
            {milestones.map((m) => {
                const Icon = iconMap[m.icon?.toLowerCase() ?? ''] || Award;
                return (
                    <div key={m.id} className="bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-lg p-3 flex items-center justify-between gap-3">
                        <div className="flex items-center gap-3">
                            <div className="size-7 rounded-lg bg-[hsl(var(--primary)/0.15)] text-[hsl(var(--primary))] flex items-center justify-center"><Icon size={24} /></div>
                            <div>
                                <h3 className="text-sm font-semibold text-[hsl(var(--foreground))] uppercase tracking-tight">{m.name}</h3>
                                <p className="mt-1 text-2xs font-bold text-[hsl(var(--muted-foreground))] uppercase tracking-wide">{m.description || 'Hito ministerial'}</p>
                            </div>
                        </div>
                        <span className="font-semibold text-[hsl(var(--primary))] uppercase tracking-wide">{m.count} personas</span>
                    </div>
                );
            })}
        </div>
    );

    const renderTable = () => (
        <div className="rounded-lg border border-[hsl(var(--border))] overflow-x-auto bg-[hsl(var(--surface-1))]">
            <table className="w-full text-left min-w-[400px]">
                <thead className="bg-[hsl(var(--surface-2))]">
                    <tr>
                        <th className="px-3 py-1.5 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">Hito</th>
                        <th className="px-3 py-1.5 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))] hidden md:table-cell">Descripción</th>
                        <th className="px-3 py-1.5 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))] hidden lg:table-cell">XP</th>
                        <th className="px-3 py-1.5 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">Alcance</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-[hsl(var(--border))]">
                    {milestones.map((m) => (
                        <tr key={m.id} className="hover:bg-[hsl(var(--surface-2))]">
                            <td className="px-3 py-1.5 text-sm font-bold text-[hsl(var(--foreground))]">{m.name}</td>
                            <td className="px-3 py-1.5 hidden md:table-cell text-xs text-[hsl(var(--muted-foreground))]">{m.description || '—'}</td>
                            <td className="px-3 py-1.5 hidden lg:table-cell text-xs text-[hsl(var(--primary))] font-bold">{m.xp || 0}</td>
                            <td className="px-3 py-1.5 font-semibold text-[hsl(var(--muted-foreground))]">{m.count || 0}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );

    const renderBoard = () => (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {groupedMilestones.map((group) => (
                <section key={group.id} className="rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] p-3">
                    <div className="flex items-center justify-between mb-5">
                        <span className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">{group.label}</span>
                        <span className="font-semibold text-[hsl(var(--muted-foreground))]">{group.rows.length}</span>
                    </div>
                    <div className="space-y-3">
                        {group.rows.map((m) => (
                            <div key={m.id} className="bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-lg p-4">
                                <p className="text-sm font-semibold text-[hsl(var(--foreground))] uppercase tracking-tight">{m.name}</p>
                                <p className="mt-2 text-2xs font-bold text-[hsl(var(--muted-foreground))]">{m.count || 0} personas · {m.xp || 0} XP</p>
                            </div>
                        ))}
                    </div>
                </section>
            ))}
        </div>
    );

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--background))] font-display overflow-hidden">
            <style jsx global>{`
                .milestone-aura {
                    position: relative;
                }
                .milestone-aura::after {
                    content: '';
                    position: absolute;
                    inset: -1px;
                    background: linear-gradient(45deg, var(--aura-color, hsl(var(--primary)/0.1)), transparent 60%);
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
                    <button className="flex items-center gap-2 px-3 py-2 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-md text-xs font-semibold uppercase tracking-wide shadow-xl shadow-[hsl(var(--primary)/0.2)] active:scale-95 transition-all">
                        <Plus size={14} /> Nueva Insignia
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-4 relative pb-4">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_hsl(var(--primary)/0.05)_0%,_transparent_50%)] pointer-events-none" />

 <div className="w-full space-y-3 relative z-10">

                    {/* Header Cinematic */}
                    <header className="space-y-4">
                        <motion.div
                            initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
                            className="inline-flex items-center gap-2 px-4 py-1.5 bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] rounded-full text-2xs font-semibold uppercase tracking-wide border border-[hsl(var(--primary)/0.2)]"
                        >
                            <Sparkles size={12} className="animate-pulse" /> Reconocimiento del Crecimiento
                        </motion.div>
                        <h1 className="text-xl lg:text-xl font-bold text-[hsl(var(--foreground))] tracking-tighter leading-none">
                            Consola de <br/> <span className="text-[hsl(var(--primary))] italic">Hitos de Fe.</span>
                        </h1>
                    </header>

                    <AnimatePresence mode="wait">
                        {loading ? (
                            <div className="py-1.5 flex flex-col items-center justify-center gap-3 text-[hsl(var(--muted-foreground))] font-semibold uppercase tracking-wide animate-pulse">
                                <Loader2 className="animate-spin text-[hsl(var(--primary))]" size={48} strokeWidth={1.5} /> Sincronizando Conquistas...
                            </div>
                        ) : viewType === 'list' ? (
                            renderList()
                        ) : viewType === 'table' ? (
                            renderTable()
                        ) : viewType === 'board' || viewType === 'kanban' ? (
                            renderBoard()
                        ) : viewType === 'wiki' ? (
                            <UniversalWikiView moduleName="Hitos de fe" storageKey="wiki_admin_milestones" />
                        ) : (
                            <div className="space-y-3">
                                {/* Milestone Summary Cards */}
                                <section className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                    {milestones.map((m, i) => {
                                        const Icon = iconMap[m.icon?.toLowerCase() ?? ''] || Award;
                                        return (
                                            <motion.div
                                                key={m.id}
                                                initial={{ opacity: 0, scale: 0.95 }}
                                                animate={{ opacity: 1, scale: 1 }}
                                                transition={{ delay: i * 0.05 }}
                                                className="milestone-aura group bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] p-4 rounded-lg shadow-sm hover:shadow-2xl transition-all duration-500 overflow-hidden"
                                                style={{ '--aura-color': 'hsl(var(--primary)/0.15)' } as CSSAuraProperties}
                                            >
                                                <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:scale-125 transition-transform duration-1000">
                                                    <Icon size={120} />
                                                </div>

                                                <div className="relative z-10 space-y-3">
                                                    <div className="size-8 rounded-lg bg-[hsl(var(--primary)/0.15)] text-[hsl(var(--primary))] flex items-center justify-center shadow-inner group-hover:rotate-12 transition-transform duration-500">
                                                        <Icon size={32} strokeWidth={1.5} />
                                                    </div>
                                                    <div>
                                                        <p className="font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wide mb-2">{m.description || 'Hito Ministerial'}</p>
                                                        <h3 className="text-xl font-bold text-[hsl(var(--foreground))] uppercase tracking-tighter leading-none mb-1">{m.name}</h3>
                                                        <p className="text-xs font-bold text-[hsl(var(--primary))] uppercase tracking-wide">{m.count} Personas Alcanzadas</p>
                                                    </div>
                                                    <div className="pt-6 border-t border-[hsl(var(--border))] flex items-center justify-between">
                                                        <span className="font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wide">+ {m.xp} XP Recompensa</span>
                                                        <button className="font-semibold text-[hsl(var(--primary))] uppercase tracking-wide flex items-center gap-2 hover:scale-105 transition-transform">
                                                            Gestionar <ChevronRight size={14} />
                                                        </button>
                                                    </div>
                                                </div>
                                            </motion.div>
                                        );
                                    })}
                                </section>

                                {/* Bulk Action Area Cinematic */}
                                <section className="bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] p-4 lg:p-4 rounded-lg text-[hsl(var(--foreground))] relative overflow-hidden group shadow-2xl">
                                    <div className="absolute top-0 right-0 -mr-20 -mt-20 size-96 bg-[hsl(var(--primary)/0.1)] rounded-full blur-[120px] group-hover:bg-[hsl(var(--primary)/0.2)] transition-all duration-1000" />

                                    <div className="relative z-10 grid grid-cols-1 lg:grid-cols-2 gap-3 items-center">
                                        <div className="space-y-3">
                                            <div className="space-y-4">
                                                <div className="flex items-center gap-3 text-[hsl(var(--primary))] font-semibold uppercase tracking-wide text-2xs">
                                                    <Zap size={16} fill="currentColor" /> Optimus Brain Processing
                                                </div>
                                                <h2 className="text-lg lg:text-xl font-bold tracking-tighter leading-none uppercase">Registro Masivo <br/> <span className="text-transparent bg-clip-text bg-gradient-to-r from-[hsl(var(--primary))] to-[hsl(var(--primary)/0.7)] italic">de Conquistas.</span></h2>
                                            </div>
                                            <p className="text-lg text-[hsl(var(--muted-foreground))] font-medium leading-relaxed max-w-xl italic">
                                                &ldquo;Sube la nómina de vencedores y Optimus Brain se encargará de estampar los certificados digitales y actualizar las Hojas de Vida instantáneamente.&rdquo;
                                            </p>
                                            <div className="flex flex-wrap gap-4">
                                                <button className="px-4 py-2 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-lg font-black text-xs uppercase tracking-wide shadow-2xl hover:translate-y-[-4px] active:scale-95 transition-all">Iniciar Protocolo</button>
                                                <button className="px-4 py-2 bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-[hsl(var(--foreground))] rounded-lg font-black text-xs uppercase tracking-wide hover:bg-[hsl(var(--surface-3,var(--surface-2)))] transition-all">Ver Plantillas</button>
                                            </div>
                                        </div>
                                        <div className="hidden lg:flex justify-center relative">
                                            <div className="size-10 rounded-lg border-4 border-[hsl(var(--primary)/0.2)] flex items-center justify-center animate-pulse">
                                                <div className="size-10 rounded-lg bg-[hsl(var(--primary))] flex items-center justify-center shadow-lg shadow-[hsl(var(--primary)/0.3)]">
                                                    <Check size={80} strokeWidth={3} className="text-[hsl(var(--primary-foreground))]" />
                                                </div>
                                            </div>
                                            <div className="absolute -bottom-6 -right-6 p-3 bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-lg shadow-2xl text-[hsl(var(--foreground))]">
                                                <Award size={40} className="text-[hsl(var(--primary))]" />
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
