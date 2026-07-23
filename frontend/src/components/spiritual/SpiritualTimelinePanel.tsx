"use client";

import React, { useEffect, useState } from 'react';
import {
    Heart, Waves, Zap, CheckCircle2, Star, Shield, Users, Lock, Loader2
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { motion } from 'framer-motion';
import clsx from 'clsx';

interface Milestone {
    milestone_id: number;
    type: string;
    event_date: string;
    notes?: string;
}

const MILESTONE_DEFS: Record<string, { label: string; icon: any; color: string; bg: string; border: string }> = {
    Decision_Fe:       { label: 'Decisión de Fe',        icon: Zap,    color: 'text-warning-text',  bg: 'bg-warning-soft dark:bg-[hsl(var(--warning))]/20',    border: 'border-[hsl(var(--warning)/25%)] dark:border-[hsl(var(--warning)/100%)]/20' },
    Bautismo_Aguas:    { label: 'Bautismo en Aguas',      icon: Waves,  color: 'text-[hsl(var(--domain-cyan)/90%)]',   bg: 'bg-[hsl(var(--domain-cyan)/10%)] dark:bg-[hsl(var(--domain-cyan)/20%)]',      border: 'border-[hsl(var(--domain-cyan)/30%)] dark:border-[hsl(var(--domain-cyan)/20%)]'   },
    Bautismo_Espiritu: { label: 'Bautismo del Espíritu',  icon: Star,   color: 'text-[hsl(var(--primary))]', bg: 'bg-info-soft dark:bg-[hsl(var(--info))]/20',  border: 'border-[hsl(var(--info)/25%)] dark:border-[hsl(var(--info)/100%)]/20'},
    Persona_Oficial:   { label: 'Participación Oficial',      icon: Shield, color: 'text-success-text',bg: 'bg-success-soft dark:bg-[hsl(var(--success))]/20', border: 'border-[hsl(var(--success)/25%)] dark:border-[hsl(var(--success)/100%)]/20'},
    Liderazgo:         { label: 'Llamado al Liderazgo',   icon: Users,  color: 'text-[hsl(var(--primary))]',   bg: 'bg-info-soft dark:bg-[hsl(var(--info))]/20',      border: 'border-[hsl(var(--info)/25%)] dark:border-[hsl(var(--info)/100%)]/20'  },
};

export default function SpiritualTimelinePanel() {
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

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center h-40 gap-3">
                <Loader2 className="animate-spin text-[hsl(var(--primary))]" size={24} />
                <p className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Cargando cronograma...</p>
            </div>
        );
    }

    return (
        <div className="space-y-3 p-3">
            <div className="relative">
                {/* Vertical line with glow */}
                <div className="absolute left-[21px] top-3 bottom-6 w-[2px] bg-[hsl(var(--surface-3))] dark:bg-white/[0.04]">
                    <div className="absolute inset-0 bg-[hsl(var(--primary))] blur-[2px] opacity-20" />
                </div>

                <div className="space-y-3">
                    {milestones.length === 0 ? (
                        <div className="text-center py-1.5 bg-[hsl(var(--surface-1))] dark:bg-white/[0.02] rounded-lg border border-dashed border-[hsl(var(--border))] dark:border-white/10">
                            <Heart className="mx-auto text-[hsl(var(--text-secondary))] dark:text-white/10 mb-4 animate-pulse" size={48} />
                            <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Caminando hacia la meta...</p>
                        </div>
                    ) : milestones.map((m) => {
                        const def = MILESTONE_DEFS[m.type] ?? {
                            label: m.type,
                            icon: CheckCircle2,
                            color: 'text-[hsl(var(--text-secondary))]',
                            bg: 'bg-[hsl(var(--surface-1))] dark:bg-white/5',
                            border: 'border-[hsl(var(--border))] dark:border-white/10',
                        };
                        const Icon = def.icon;
                        return (
                            <motion.div
                                key={m.milestone_id}
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: 0.1, type: 'spring', damping: 20 }}
                                className="flex items-start gap-3 group"
                            >
                                <div className={clsx(
                                    'size-6 rounded-lg flex items-center justify-center shrink-0 border-2 relative z-10 transition-all group-hover:scale-110 shadow-lg',
                                    def.bg, def.border
                                )}>
                                    <Icon size={18} className={clsx('transition-all', def.color)} />
                                </div>

                                <div className="flex-1 bg-[hsl(var(--bg-primary))] dark:bg-white/[0.03] border border-[hsl(var(--border))] dark:border-white/[0.05] rounded-lg p-3 shadow-sm group-hover:shadow-xl group-hover:shadow-[hsl(var(--info))]/[0.03] transition-all group-hover:border-[hsl(var(--info)/100%)]/20">
                                    <div className="flex items-start justify-between gap-4">
                                        <div className="flex-1 min-w-0">
                                            <p className="font-semibold text-[hsl(var(--text-primary))] dark:text-white leading-tight uppercase tracking-tight">{def.label}</p>
                                            {m.notes && <p className="text-[11px] font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mt-1 leading-relaxed italic">&quot;{m.notes}&quot;</p>}
                                        </div>
                                        <div className="shrink-0 flex flex-col items-end gap-1">
                                            <span className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] opacity-60">
                                                {new Date(m.event_date).toLocaleDateString('es-ES', { day: '2-digit', month: 'short' })}
                                            </span>
                                            <Zap size={10} className="text-[hsl(var(--primary))] opacity-0 group-hover:opacity-100 transition-opacity" />
                                        </div>
                                    </div>
                                </div>
                            </motion.div>
                        );
                    })}
                </div>
            </div>

            {/* Upcoming preview */}
            <div className="pt-8 border-t border-[hsl(var(--border))] dark:border-white/[0.04]">
                <h2 className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-5 ml-2">Próximos Desafíos</h2>
                <div className="grid grid-cols-1 gap-3">
                    {Object.entries(MILESTONE_DEFS)
                        .filter(([key]) => !milestones.some(m => m.type === key))
                        .map(([key, def]) => (
                            <motion.div 
                                key={key}
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 0.5 }}
                                whileHover={{ opacity: 1, scale: 1.02 }}
                                className="flex items-center gap-4 px-3 py-1.5 bg-[hsl(var(--surface-1))] dark:bg-white/[0.02] rounded-lg border border-[hsl(var(--border))] dark:border-white/[0.04] grayscale hover:grayscale-0 transition-all cursor-default"
                            >
                                <div className={clsx("size-8 rounded-md flex items-center justify-center border", def.bg, def.border)}>
                                    <def.icon size={14} className={def.color} />
                                </div>
                                <p className="font-semibold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] flex-1 uppercase tracking-tight">{def.label}</p>
                                <Lock size={12} className="text-[hsl(var(--text-secondary))] dark:text-white/10" />
                            </motion.div>
                        ))}
                </div>
            </div>
        </div>
    );
}
