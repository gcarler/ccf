"use client";

import React, { useEffect, useState } from 'react';
import {
    Heart, Waves, Zap, CheckCircle2, Calendar, Star, Shield, Users, Lock, Plus
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import EmptyState from '@/components/ui/EmptyState';
import Skeleton from '@/components/ui/Skeleton';

interface Milestone {
    milestone_id: number;
    type: string;
    event_date: string;
    notes?: string;
}

const MILESTONE_DEFS: Record<string, { label: string; icon: any; color: string; bg: string; border: string }> = {
    Decision_Fe:       { label: 'Decisión de Fe',        icon: Zap,    color: 'text-amber-600',  bg: 'bg-amber-50 dark:bg-amber-900/20',    border: 'border-amber-200 dark:border-amber-500/20' },
    Bautismo_Aguas:    { label: 'Bautismo en Aguas',      icon: Waves,  color: 'text-cyan-600',   bg: 'bg-cyan-50 dark:bg-cyan-900/20',      border: 'border-cyan-200 dark:border-cyan-500/20'   },
    Bautismo_Espiritu: { label: 'Bautismo del Espíritu',  icon: Star,   color: 'text-violet-600', bg: 'bg-violet-50 dark:bg-violet-900/20',  border: 'border-violet-200 dark:border-violet-500/20'},
    Miembro_Oficial:   { label: 'Membresía Oficial',      icon: Shield, color: 'text-emerald-600',bg: 'bg-emerald-50 dark:bg-emerald-900/20', border: 'border-emerald-200 dark:border-emerald-500/20'},
    Liderazgo:         { label: 'Llamado al Liderazgo',   icon: Users,  color: 'text-blue-600',   bg: 'bg-blue-50 dark:bg-blue-900/20',      border: 'border-blue-200 dark:border-blue-500/20'  },
};

export default function SpiritualTimelinePage() {
    const { token, user } = useAuth();
    const [milestones, setMilestones] = useState<Milestone[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !user?.id) { setLoading(false); return; }
        apiFetch<Milestone[]>(`/spiritual-life/milestones/${user.id}`, { token })
            .then(data => setMilestones(Array.isArray(data) ? data : []))
            .catch(() => setMilestones([]))
            .finally(() => setLoading(false));
    }, [token, user]);

    return (
        <div className="flex flex-col h-full bg-slate-50 dark:bg-[#0f1012] overflow-y-auto font-display">
            <div className="max-w-4xl mx-auto w-full p-6 space-y-6 pb-20">

                {/* Sub-header */}
                <div className="flex items-center justify-between">
                    <div>
                        <div className="flex items-center gap-2 mb-1">
                            <div className="size-7 rounded-lg bg-violet-50 dark:bg-violet-900/30 flex items-center justify-center">
                                <Calendar size={14} className="text-violet-600" />
                            </div>
                            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-violet-600">Línea de Tiempo</span>
                        </div>
                        <h1 className="text-xl font-black tracking-tight text-slate-900 dark:text-white leading-none">
                            Mi Ruta de Victoria
                        </h1>
                        <p className="text-[12px] text-slate-500 dark:text-slate-400 mt-0.5 font-medium">
                            Cada hito de tu caminar con Cristo, registrado y celebrado.
                        </p>
                    </div>
                    <button className="flex items-center gap-2 px-4 py-1.5 bg-blue-600 text-white rounded-lg text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all">
                        <Plus size={13} /> Registrar Hito
                    </button>
                </div>

                {/* Timeline */}
                {loading ? (
                    <div className="space-y-4">
                        {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-20 rounded-2xl" />)}
                    </div>
                ) : milestones.length === 0 ? (
                    <EmptyState
                        icon={Heart}
                        title="Aún no hay hitos registrados"
                        description="Cuando el equipo pastoral registre tus hitos espirituales, aparecerán aquí en tu línea de tiempo."
                    />
                ) : (
                    <div className="relative">
                        {/* Vertical line */}
                        <div className="absolute left-[22px] top-4 bottom-4 w-px bg-slate-200 dark:bg-white/10" />

                        <div className="space-y-4">
                            {milestones.map((m, i) => {
                                const def = MILESTONE_DEFS[m.type] ?? {
                                    label: m.type,
                                    icon: CheckCircle2,
                                    color: 'text-slate-400',
                                    bg: 'bg-slate-50 dark:bg-white/5',
                                    border: 'border-slate-200 dark:border-white/10',
                                };
                                const Icon = def.icon;
                                return (
                                    <motion.div
                                        key={m.milestone_id}
                                        initial={{ opacity: 0, x: -12 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ delay: i * 0.06 }}
                                        className="flex items-start gap-4"
                                    >
                                        {/* Dot */}
                                        <div className={clsx(
                                            'size-11 rounded-2xl flex items-center justify-center shrink-0 border relative z-10',
                                            def.bg, def.border
                                        )}>
                                            <Icon size={18} className={def.color} />
                                        </div>

                                        {/* Card */}
                                        <div className="flex-1 bg-white dark:bg-[#1a1b1e] border border-slate-200 dark:border-white/[0.06] rounded-2xl p-4 shadow-sm hover:shadow-md hover:border-slate-300 dark:hover:border-white/15 transition-all">
                                            <div className="flex items-start justify-between gap-3">
                                                <div>
                                                    <p className="text-[13px] font-bold text-slate-800 dark:text-white">{def.label}</p>
                                                    {m.notes && (
                                                        <p className="text-[12px] text-slate-500 dark:text-slate-400 mt-0.5">{m.notes}</p>
                                                    )}
                                                </div>
                                                <span className="shrink-0 text-[10px] font-black uppercase tracking-widest text-slate-400">
                                                    {new Date(m.event_date).toLocaleDateString('es-ES', { year: 'numeric', month: 'short', day: 'numeric' })}
                                                </span>
                                            </div>
                                        </div>
                                    </motion.div>
                                );
                            })}
                        </div>
                    </div>
                )}

                {/* Upcoming milestones preview */}
                {!loading && (
                    <section>
                        <h2 className="text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 mb-3">Próximos Hitos</h2>
                        <div className="bg-white dark:bg-[#1a1b1e] border border-slate-200 dark:border-white/[0.06] rounded-2xl overflow-hidden shadow-sm divide-y divide-slate-100 dark:divide-white/5">
                            {Object.entries(MILESTONE_DEFS)
                                .filter(([key]) => !milestones.some(m => m.type === key))
                                .map(([key, def]) => {
                                    const Icon = def.icon;
                                    return (
                                        <div key={key} className="flex items-center gap-3 px-4 py-3 opacity-50">
                                            <div className={clsx('size-8 rounded-xl flex items-center justify-center border shrink-0', def.bg, def.border)}>
                                                <Icon size={14} className={def.color} />
                                            </div>
                                            <p className="text-[12px] font-bold text-slate-700 dark:text-slate-300 flex-1">{def.label}</p>
                                            <Lock size={13} className="text-slate-300 dark:text-slate-600" />
                                        </div>
                                    );
                                })}
                        </div>
                    </section>
                )}
            </div>
        </div>
    );
}
