"use client";

import React from 'react';
import {
    Users,
    UserPlus,
    CheckCircle2,
    Target,
    Search,
    TrendingUp,
    Zap,
    Filter
} from 'lucide-react';
import { motion } from 'framer-motion';
import clsx from 'clsx';

interface PipelineFiltersSidebarProps {
    stats: {
        total: number;
        new: number;
        consolidated: number;
        conversion: number;
    };
    search: string;
    onSearchChange: (val: string) => void;
}

export default function PipelineFiltersSidebar({ stats, search, onSearchChange }: PipelineFiltersSidebarProps) {
    return (
        <div className="flex flex-col h-full bg-[hsl(var(--surface-1))]">
            {/* Header Cinematic */}
            <div className="p-4 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shrink-0 relative overflow-hidden rounded-t-lg">
                <div className="absolute top-0 right-0 p-4 opacity-[0.03] pointer-events-none text-[hsl(var(--primary))]">
                    <Target size={160} />
                </div>

                <div className="flex items-center gap-4 relative z-10 p-2">
                    <div className="size-8 rounded-lg bg-[hsl(var(--primary))] flex items-center justify-center text-[hsl(var(--primary-foreground))] shadow-lg">
                        <Target size={28} />
                    </div>
                    <div>
                        <h2 className="text-lg font-bold text-[hsl(var(--foreground))] uppercase tracking-[-0.04em] leading-tight">
                            Pipeline<br/>
                            <span className="text-[hsl(var(--primary))]">Consolidación</span>
                        </h2>
                    </div>
                </div>

                {/* Glass Metric Cards */}
                <div className="grid grid-cols-2 gap-3 mt-3 relative z-10">
                    {[
                        { label: 'Total Leads', value: stats.total, color: 'text-[hsl(var(--foreground))]' },
                        { label: 'Conversión', value: `${stats.conversion}%`, color: 'text-[hsl(var(--primary))]', icon: TrendingUp }
                    ].map((s) => (
                        <div key={s.label} className="bg-[hsl(var(--surface-2))] p-4 rounded-md border border-[hsl(var(--border))] shadow-sm">
                            <p className="text-2xs font-bold text-[hsl(var(--muted-foreground))] uppercase tracking-wide mb-1.5">{s.label}</p>
                            <div className="flex items-center justify-between">
                                <p className={clsx("text-sm font-bold tracking-tighter leading-none", s.color)}>{s.value}</p>
                                {s.icon && <s.icon size={12} className={s.color} />}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Filters Section */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
                <section className="space-y-4">
                    <h3 className="text-2xs font-bold text-[hsl(var(--muted-foreground))] uppercase tracking-wide flex items-center gap-3">
                        <Filter size={14} className="text-[hsl(var(--primary))]" /> Segmentación
                    </h3>
                    <div className="space-y-2">
                        {[
                            { id: 'all', label: 'Todos los Prospectos', icon: Users, count: stats.total, color: 'text-[hsl(var(--primary))]', bg: 'bg-[hsl(var(--primary)/0.1)]' },
                            { id: 'new', label: 'Registros Nuevos', icon: UserPlus, count: stats.new, color: 'text-[hsl(var(--warning))]', bg: 'bg-[hsl(var(--warning)/0.1)]' },
                            { id: 'consolidated', label: 'Casos de Éxito', icon: CheckCircle2, count: stats.consolidated, color: 'text-[hsl(var(--success))]', bg: 'bg-[hsl(var(--success)/0.1)]' },
                        ].map((s) => (
                            <motion.button
                                key={s.id}
                                whileHover={{ x: 4 }}
                                className="w-full flex items-center gap-4 p-4 bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-md hover:bg-[hsl(var(--surface-2))] hover:border-[hsl(var(--primary)/0.3)] transition-all group"
                            >
                                <div className={clsx("size-8 rounded-lg flex items-center justify-center transition-all group-hover:scale-110", s.bg, s.color)}>
                                    <s.icon size={16} />
                                </div>
                                <span className="flex-1 text-left font-bold text-xs uppercase tracking-tight text-[hsl(var(--foreground))]">{s.label}</span>
                                <span className="text-2xs px-2.5 py-1 bg-[hsl(var(--surface-3))] rounded-lg font-bold text-[hsl(var(--muted-foreground))]">{s.count}</span>
                            </motion.button>
                        ))}
                    </div>
                </section>

                <section className="space-y-4">
                    <h3 className="text-2xs font-bold text-[hsl(var(--muted-foreground))] uppercase tracking-wide flex items-center gap-3">
                        <Search size={14} className="text-[hsl(var(--primary))]" /> Búsqueda Quick-Scan
                    </h3>
                    <div className="relative group">
                        <Search size={16} className="absolute left-5 top-1/2 -translate-y-1/2 text-[hsl(var(--muted-foreground))] group-focus-within:text-[hsl(var(--primary))] transition-colors" />
                        <input
                            value={search}
                            onChange={e => onSearchChange(e.target.value)}
                            placeholder="Nombre, teléfono o etiqueta..."
                            aria-label="Buscar prospectos"
                            className="w-full pl-12 pr-6 py-2 text-xs font-bold rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] outline-none focus:ring-4 focus:ring-[hsl(var(--primary)/0.1)] text-[hsl(var(--foreground))] transition-all placeholder:text-[hsl(var(--muted-foreground))]"
                        />
                    </div>
                </section>

                <section className="p-4 bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-md text-[hsl(var(--foreground))] shadow-md relative overflow-hidden group">
                    <div className="absolute top-0 right-0 p-4 opacity-10 text-[hsl(var(--primary))] group-hover:scale-110 transition-transform duration-700"><Zap size={80} /></div>
                    <div className="relative z-10">
                        <h4 className="text-sm font-bold uppercase tracking-tighter leading-tight mb-2">Asistente<br/>Optimus</h4>
                        <p className="text-2xs font-bold text-[hsl(var(--muted-foreground))] uppercase tracking-wide leading-relaxed">
                            Analizando tendencias de permanencia para optimizar el discipulado.
                        </p>
                    </div>
                </section>
            </div>
        </div>
    );
}
