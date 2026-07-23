"use client";

import React, { useEffect, useState } from 'react';
import {
    ShieldCheck, Heart, Target, BarChart3, ArrowRight, Loader2, Users, Home,
    TrendingUp, TrendingDown, HeartHandshake
} from 'lucide-react';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';

interface ImpactData {
    total_personas: number;
    total_familias: number;
    total_donaciones_cop: number;
    distribucion: { label: string; pct: number; desc: string }[];
}

function fmt(n: number) {
    return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(n);
}

export default function TransparencyPage() {
    const [data, setData] = useState<ImpactData | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const ctrl = new AbortController();
        apiFetch<ImpactData>('/finance/impact', { cache: 'no-store', signal: ctrl.signal })
            .then(d => setData(d))
            .catch(e => { if (e.name !== 'AbortError') { console.error(e); toast.error('Error al cargar datos'); } })
            .finally(() => setLoading(false));
        return () => ctrl.abort();
    }, []);

    const stats = data ? [
        { label: 'Personas Beneficiadas', value: data.total_personas.toLocaleString('es-CO'), icon: Users, color: 'text-[hsl(var(--primary))]' },
        { label: 'Familias Beneficiadas', value: data.total_familias.toLocaleString('es-CO'), icon: Home, color: 'text-[hsl(var(--danger))]' },
        { label: 'Total Donaciones', value: fmt(data.total_donaciones_cop), icon: Heart, color: 'text-[hsl(var(--success))]' },
    ] : [
        { label: 'Personas Beneficiadas', value: '—', icon: Users, color: 'text-[hsl(var(--primary))]' },
        { label: 'Familias Beneficiadas', value: '—', icon: Home, color: 'text-[hsl(var(--danger))]' },
        { label: 'Total Donaciones', value: '—', icon: Heart, color: 'text-[hsl(var(--success))]' },
    ];

    const sidebarSections = [
        {
            title: 'Finanzas',
            items: [
                { id: 'finances-dashboard', label: 'Dashboard Financiero', href: '/plataforma/finances', icon: BarChart3 },
                { id: 'finances-ingresos', label: 'Ingresos', href: '/plataforma/finances/ingresos', icon: TrendingUp },
                { id: 'finances-egresos', label: 'Egresos', href: '/plataforma/finances/egresos', icon: TrendingDown },
                { id: 'finances-transparency', label: 'Transparencia', href: '/plataforma/finances/transparency', icon: HeartHandshake },
            ]
        }
    ];

    return (
        <WorkspaceLayout sidebarTitle="Finanzas" sidebarSections={sidebarSections}>
            <div className="p-3 space-y-3 animate-in fade-in duration-500 overflow-y-auto h-full">
            <div className="space-y-1 max-w-3xl">
                <div className="flex items-center gap-2 mb-1">
                    <div className="size-7 rounded-lg bg-success-soft dark:bg-[hsl(var(--success))]/30 flex items-center justify-center">
                        <ShieldCheck size={14} className="text-success-text" />
                    </div>
                    <span className="text-[10px] font-semibold uppercase tracking-wide text-success-text">Mayordomía Transparente</span>
                </div>
                <h1 className="text-xl font-bold tracking-tight text-[hsl(var(--text-primary))] dark:text-white leading-none">
                    Impacto y Transparencia
                </h1>
                <p className="text-[12px] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-medium">
                    En CCF creemos en la rendición de cuentas. Aquí puedes ver cómo tus ofrendas se transforman en impacto real para el Reino de Dios.
                </p>
                {data && (
                    <div className="flex items-center justify-center gap-3 pt-2">
                        <div className="text-center">
                            <p className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white">{data.total_personas.toLocaleString()}</p>
                            <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide flex items-center gap-1 justify-center"><Users size={10}/> Personas</p>
                        </div>
                        <div className="w-px h-8 bg-[hsl(var(--surface-3))] dark:bg-white/10" />
                        <div className="text-center">
                            <p className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white">{data.total_familias.toLocaleString()}</p>
                            <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide flex items-center gap-1 justify-center"><Home size={10}/> Familias</p>
                        </div>
                        <div className="w-px h-8 bg-[hsl(var(--surface-3))] dark:bg-white/10" />
                        <div className="text-center">
                            <p className="text-lg font-bold text-success-text">{fmt(data.total_donaciones_cop)}</p>
                            <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Total Histórico</p>
                        </div>
                    </div>
                )}
            </div>

            {loading ? (
                <div className="flex items-center justify-center py-1.5">
                    <Loader2 size={32} className="animate-spin text-[hsl(var(--success))]" />
                </div>
            ) : (
                <>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        {stats.map((stat, i) => (
                            <div key={i} className="bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] dark:border-white/5 p-4 rounded-lg text-center space-y-4 group hover:border-[hsl(var(--success)/100%)]/30 transition-all shadow-sm">
                                <div className={`w-16 h-8 mx-auto bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-lg flex items-center justify-center ${stat.color} group-hover:scale-110 transition-transform`}>
                                    <stat.icon size={32} />
                                </div>
                                <div>
                                    <div className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white italic tracking-tighter">{stat.value}</div>
                                    <div className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide mt-1">{stat.label}</div>
                                </div>
                            </div>
                        ))}
                    </div>

                    <div className="bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] dark:border-white/5 rounded-lg overflow-hidden shadow-sm">
                        <div className="grid grid-cols-1 lg:grid-cols-2">
                            <div className="p-4 space-y-3">
                                <h2 className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight uppercase italic">
                                    ¿Donde se invierte tu <span className="text-[hsl(var(--success))]">semilla?</span>
                                </h2>
                                <div className="space-y-3">
                                    {(data?.distribucion ?? []).map((item, i) => (
                                        <div key={i} className="flex gap-3 group">
                                            <div className="text-lg font-bold text-[hsl(var(--success))]/30 dark:text-[hsl(var(--success))]/20 group-hover:text-[hsl(var(--success))] transition-colors">{item.pct}%</div>
                                            <div className="space-y-1">
                                                <div className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white uppercase">{item.label}</div>
                                                <p className="text-xs text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">{item.desc}</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <div className="bg-[hsl(var(--success))]/10 p-4 flex items-center justify-center relative overflow-hidden border-t lg:border-t-0 lg:border-l border-[hsl(var(--border))] dark:border-white/5">
                                <div className="absolute top-0 right-0 p-4 opacity-10">
                                    <Target size={300} className="text-[hsl(var(--success))]" />
                                </div>
                                <div className="relative z-10 text-center space-y-3">
                                    <div className="w-24 h-24 bg-[hsl(var(--success))] text-white rounded-full flex items-center justify-center mx-auto shadow-2xl shadow-[hsl(var(--success)/30%)]">
                                        <BarChart3 size={48} />
                                    </div>
                                    <div className="space-y-2">
                                        <h3 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white uppercase italic">Auditoría Externa</h3>
                                        <p className="text-sm text-success-text dark:text-[hsl(var(--success))] font-medium">
                                            Nuestros estados financieros son revisados trimestralmente por un comité de transparencia.
                                        </p>
                                    </div>
                                    <button className="px-4 py-1.5 bg-[hsl(var(--success))] hover:bg-[hsl(var(--success))] text-white text-xs font-semibold uppercase tracking-wide rounded-lg transition-all flex items-center gap-2 mx-auto shadow-lg shadow-[hsl(var(--success)/20%)]">
                                        Ver Reporte Anual <ArrowRight size={16} />
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </>
            )}
        </div>
        </WorkspaceLayout>
    );
}
