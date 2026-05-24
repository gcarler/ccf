"use client";

import React, { useEffect, useState } from 'react';
import {
    ShieldCheck, Globe, Heart, Zap, Target, BarChart3, ArrowRight, Loader2, Users, Home
} from 'lucide-react';
import { apiFetch } from '@/lib/http';

interface ImpactData {
    total_miembros: number;
    total_familias: number;
    total_donaciones_cop: number;
    biblias_entregadas: number;
    misiones_rurales: number;
    raciones_comida: number;
    distribucion: { label: string; pct: number; desc: string }[];
}

function fmt(n: number) {
    return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(n);
}

export default function TransparencyPage() {
    const [data, setData] = useState<ImpactData | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        apiFetch<ImpactData>('/finance/impact', { cache: 'no-store' })
            .then(d => setData(d))
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    const stats = data ? [
        { label: 'Biblias Entregadas',  value: data.biblias_entregadas.toLocaleString('es-CO'), icon: Zap,    color: 'text-blue-500' },
        { label: 'Raciones de Comida',  value: data.raciones_comida.toLocaleString('es-CO') + '+', icon: Heart, color: 'text-rose-500' },
        { label: 'Misiones Rurales',    value: String(data.misiones_rurales), icon: Globe, color: 'text-blue-500' },
    ] : [
        { label: 'Biblias Entregadas', value: '—', icon: Zap,   color: 'text-blue-500' },
        { label: 'Raciones de Comida', value: '—', icon: Heart, color: 'text-rose-500' },
        { label: 'Misiones Rurales',   value: '—', icon: Globe, color: 'text-blue-500' },
    ];

    return (
        <div className="p-3 space-y-3 animate-in fade-in duration-500 overflow-y-auto h-full">
            <div className="space-y-1 max-w-3xl">
                <div className="flex items-center gap-2 mb-1">
                    <div className="size-7 rounded-lg bg-emerald-50 dark:bg-emerald-900/30 flex items-center justify-center">
                        <ShieldCheck size={14} className="text-emerald-600" />
                    </div>
                    <span className="text-[10px] font-semibold uppercase tracking-wide text-emerald-600">Mayordomía Transparente</span>
                </div>
                <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white leading-none">
                    Impacto y Transparencia
                </h1>
                <p className="text-[12px] text-slate-500 dark:text-slate-400 font-medium">
                    En CCF creemos en la rendición de cuentas. Aquí puedes ver cómo tus ofrendas se transforman en impacto real para el Reino de Dios.
                </p>
                {data && (
                    <div className="flex items-center justify-center gap-3 pt-2">
                        <div className="text-center">
                            <p className="text-lg font-bold text-slate-900 dark:text-white">{data.total_miembros.toLocaleString()}</p>
                            <p className="font-semibold text-slate-400 uppercase tracking-wide flex items-center gap-1 justify-center"><Users size={10}/> Miembros</p>
                        </div>
                        <div className="w-px h-8 bg-slate-200 dark:bg-white/10" />
                        <div className="text-center">
                            <p className="text-lg font-bold text-slate-900 dark:text-white">{data.total_familias.toLocaleString()}</p>
                            <p className="font-semibold text-slate-400 uppercase tracking-wide flex items-center gap-1 justify-center"><Home size={10}/> Familias</p>
                        </div>
                        <div className="w-px h-8 bg-slate-200 dark:bg-white/10" />
                        <div className="text-center">
                            <p className="text-lg font-bold text-emerald-600">{fmt(data.total_donaciones_cop)}</p>
                            <p className="font-semibold text-slate-400 uppercase tracking-wide">Total Histórico</p>
                        </div>
                    </div>
                )}
            </div>

            {loading ? (
                <div className="flex items-center justify-center py-1.5">
                    <Loader2 size={32} className="animate-spin text-emerald-500" />
                </div>
            ) : (
                <>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        {stats.map((stat, i) => (
                            <div key={i} className="bg-white dark:bg-[#1e1f21] border border-slate-100 dark:border-white/5 p-4 rounded-lg text-center space-y-4 group hover:border-emerald-500/30 transition-all shadow-sm">
                                <div className={`w-16 h-8 mx-auto bg-slate-50 dark:bg-white/5 rounded-lg flex items-center justify-center ${stat.color} group-hover:scale-110 transition-transform`}>
                                    <stat.icon size={32} />
                                </div>
                                <div>
                                    <div className="text-lg font-bold text-slate-900 dark:text-white italic tracking-tighter">{stat.value}</div>
                                    <div className="font-semibold text-slate-400 uppercase tracking-wide mt-1">{stat.label}</div>
                                </div>
                            </div>
                        ))}
                    </div>

                    <div className="bg-white dark:bg-[#1e1f21] border border-slate-100 dark:border-white/5 rounded-lg overflow-hidden shadow-sm">
                        <div className="grid grid-cols-1 lg:grid-cols-2">
                            <div className="p-4 space-y-3">
                                <h2 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight uppercase italic">
                                    ¿Donde se invierte tu <span className="text-emerald-500">semilla?</span>
                                </h2>
                                <div className="space-y-3">
                                    {(data?.distribucion ?? []).map((item, i) => (
                                        <div key={i} className="flex gap-3 group">
                                            <div className="text-lg font-bold text-emerald-500/30 dark:text-emerald-500/20 group-hover:text-emerald-500 transition-colors">{item.pct}%</div>
                                            <div className="space-y-1">
                                                <div className="text-sm font-bold text-slate-800 dark:text-white uppercase">{item.label}</div>
                                                <p className="text-xs text-slate-500 dark:text-slate-400">{item.desc}</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <div className="bg-emerald-500/10 p-4 flex items-center justify-center relative overflow-hidden border-t lg:border-t-0 lg:border-l border-slate-100 dark:border-white/5">
                                <div className="absolute top-0 right-0 p-4 opacity-10">
                                    <Target size={300} className="text-emerald-500" />
                                </div>
                                <div className="relative z-10 text-center space-y-3">
                                    <div className="w-24 h-24 bg-emerald-500 text-white rounded-full flex items-center justify-center mx-auto shadow-2xl shadow-emerald-500/30">
                                        <BarChart3 size={48} />
                                    </div>
                                    <div className="space-y-2">
                                        <h3 className="text-lg font-bold text-slate-900 dark:text-white uppercase italic">Auditoría Externa</h3>
                                        <p className="text-sm text-emerald-600 dark:text-emerald-400 font-medium">
                                            Nuestros estados financieros son revisados trimestralmente por un comité de transparencia.
                                        </p>
                                    </div>
                                    <button className="px-4 py-1.5 bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-semibold uppercase tracking-wide rounded-lg transition-all flex items-center gap-2 mx-auto shadow-lg shadow-emerald-500/20">
                                        Ver Reporte Anual <ArrowRight size={16} />
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}

