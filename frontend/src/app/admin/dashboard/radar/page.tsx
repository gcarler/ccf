"use client";

import React, { useEffect, useState } from 'react';
import { 
    Users, 
    Waves, 
    BookOpen, 
    DollarSign, 
    TrendingUp, 
    Target,
    Shield
} from 'lucide-react';
import { api } from '@/services/apiService';
import { StatCard } from '@/components/StatCard';

interface RadarData {
    membresia_viva: number;
    bautismos_este_anio: number;
    estudiantes_activos: number;
    recaudacion_mes: number;
}

export default function PastorRadarPage() {
    const [data, setData] = useState<RadarData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        api.get<RadarData>('/analytics/radar')
            .then(setData)
            .catch(err => setError(err.message))
            .finally(() => setLoading(false));
    }, []);

    if (loading) return (
        <div className="p-8 h-full flex items-center justify-center">
            <div className="animate-pulse text-primary font-black tracking-[0.5em] uppercase italic">Iniciando Radar Ministerial...</div>
        </div>
    );

    if (error) return (
        <div className="p-8 text-rose-500 font-bold bg-rose-500/10 border border-rose-500/20 rounded-2xl">
            Error de conexión: {error}
        </div>
    );

    return (
        <div className="p-8 space-y-8 animate-in fade-in duration-700">
            <div className="flex flex-col gap-2">
                <div className="inline-flex items-center gap-2 px-3 py-1 bg-primary/10 text-primary rounded-full text-[10px] font-black uppercase tracking-[0.2em] w-fit">
                    <Shield size={12} /> Inteligencia Ministerial v3.9
                </div>
                <h1 className="text-4xl font-black tracking-tighter text-white uppercase italic">
                    Radar del <span className="text-primary">Pastor</span>
                </h1>
                <p className="text-muted-foreground text-sm max-w-2xl">
                    Monitoreo en tiempo real del impacto espiritual y financiero de la congregación basado en datos consolidados.
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard 
                    label="Membresía Viva" 
                    value={data?.membresia_viva || 0} 
                    icon={Users} color="text-blue-500" bg="bg-blue-500/10" 
                    desc="Miembros activos" trend="+5%" 
                />
                <StatCard 
                    label="Bautismos" 
                    value={data?.bautismos_este_anio || 0} 
                    icon={Waves} color="text-cyan-500" bg="bg-cyan-500/10" 
                    desc="Hitos este año" trend="+12%" 
                />
                <StatCard 
                    label="Estudiantes" 
                    value={data?.estudiantes_activos || 0} 
                    icon={BookOpen} color="text-emerald-500" bg="bg-emerald-500/10" 
                    desc="Inscripciones activas" trend="+8" 
                />
                <StatCard 
                    label="Recaudación" 
                    value={`$${(data?.recaudacion_mes || 0).toLocaleString()}`} 
                    icon={DollarSign} color="text-amber-500" bg="bg-amber-500/10" 
                    desc="Últimos 30 días" trend="+15%" 
                />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div className="bg-[#1e1f21] border border-white/5 p-8 rounded-3xl space-y-6">
                    <div className="flex items-center justify-between">
                        <h2 className="text-xl font-black text-white tracking-tight uppercase italic flex items-center gap-2">
                            <TrendingUp className="text-primary" /> Tendencias de Crecimiento
                        </h2>
                        <span className="text-[10px] text-primary font-bold tracking-widest bg-primary/10 px-2 py-1 rounded">MÉTRICAS MES A MES</span>
                    </div>
                    <div className="h-64 flex items-end justify-between gap-2 pt-8">
                        {[40, 65, 45, 90, 80, 100].map((h, i) => (
                            <div key={i} className="flex-1 flex flex-col items-center gap-2 group">
                                <div 
                                    className="w-full bg-primary/20 rounded-t-lg group-hover:bg-primary/40 transition-all duration-500 relative"
                                    style={{ height: `${h}%` }}
                                >
                                    <div className="absolute -top-8 left-1/2 -translate-x-1/2 text-[10px] font-bold text-white opacity-0 group-hover:opacity-100 transition-opacity font-mono">
                                        {h}%
                                    </div>
                                </div>
                                <div className="text-[10px] font-black text-muted-foreground uppercase tracking-tighter">Mes {i+1}</div>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="bg-[#1e1f21] border border-white/5 p-8 rounded-3xl space-y-6">
                    <h2 className="text-xl font-black text-white tracking-tight uppercase italic flex items-center gap-2">
                        <Target className="text-primary" /> Objetivos Trimestrales
                    </h2>
                    <div className="space-y-6">
                        {[
                            { label: 'Bautismos Meta', target: 50, current: data?.bautismos_este_anio || 0, color: 'bg-blue-500' },
                            { label: 'Nuevos Miembros', target: 200, current: 35, color: 'bg-emerald-500' },
                            { label: 'Estudiantes Liderazgo', target: 80, current: 12, color: 'bg-amber-500' },
                        ].map((goal, i) => {
                            const pct = Math.min(100, (goal.current / goal.target) * 100);
                            return (
                                <div key={i} className="space-y-2">
                                    <div className="flex justify-between text-[10px] font-bold uppercase tracking-widest">
                                        <span className="text-white">{goal.label}</span>
                                        <span className="text-muted-foreground font-mono">{goal.current} / {goal.target}</span>
                                    </div>
                                    <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                                        <div 
                                            className={`h-full ${goal.color} transition-all duration-1000 ease-out shadow-[0_0_10px_rgba(0,0,0,0.5)]`}
                                            style={{ width: `${pct}%` }}
                                        />
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
}
