'use client';

import React, { useState, useEffect } from 'react';
import { BarChart3, Calendar, Filter, Users, TrendingUp, Award } from 'lucide-react';
import EvangelismShell from '@/components/evangelism/EvangelismShell';
import AdminHero from '@/components/admin/AdminHero';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import { useAuth } from '@/context/AuthContext';
import type { GlobalEventAnalyticsData } from '@/app/plataforma/evangelism/types';

export default function GlobalEventAnalyticsPage() {
    const { token } = useAuth();
    const [period, setPeriod] = useState<string>('MONTH');
    const [eventType, setEventType] = useState<string>('ALL');
    
    const [loading, setLoading] = useState(true);
    const [data, setData] = useState<GlobalEventAnalyticsData | null>(null);

    useEffect(() => {
        if (!token) return;
        
        const loadAnalytics = async () => {
            setLoading(true);
            try {
                const res = await apiFetch<GlobalEventAnalyticsData>(`/evangelism/events/analytics/global?period=${period}&event_type=${eventType}`, {
                    token
                });
                setData(res);
            } catch (error) {
                console.error(error);
                toast.error("Error al cargar la analítica");
            } finally {
                setLoading(false);
            }
        };

        loadAnalytics();
    }, [period, eventType, token]);

    const periodOptions = [
        { value: 'WEEK', label: 'Semanal' },
        { value: 'MONTH', label: 'Mensual' },
        { value: 'TRIMESTER', label: 'Trimestral' },
        { value: 'SEMESTER', label: 'Semestral' },
        { value: 'YEAR', label: 'Anual' }
    ];

    const typeOptions = [
        { value: 'ALL', label: 'Todos los Eventos' },
        { value: 'PERMANENT', label: 'Servicios Fijos' },
        { value: 'SPECIAL', label: 'Especiales' },
        { value: 'FARO', label: 'Faro en Casa' }
    ];

    return (
        <EvangelismShell
            breadcrumbs={[
                { label: 'Evangelismo', icon: Users },
                { label: 'Eventos', href: '/plataforma/evangelism/events', icon: Calendar },
                { label: 'Dashboard Eventos', icon: BarChart3 }
            ]}
        >
            <AdminHero
                eyebrow="Analítica"
                title="Dashboard Global de Evangelismo"
                description="Cruza los datos de asistencia de la iglesia entera. Filtra por tiempo y tipo de evento para identificar tendencias."
                tags={['Data Science', 'Crecimiento', 'Asistencia']}
                watchers={['Sistema Optimus', 'Módulo Analítico']}
            />
            
 <div className="p-4 lg:p-3 space-y-3 w-full">
                
                {/* FILTROS */}
                <div className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-md p-4 shadow-sm flex flex-col md:flex-row gap-4 items-center">
                    <div className="flex items-center gap-3 text-slate-800 dark:text-white font-semibold uppercase tracking-wide text-xs">
                        <Filter size={18} className="text-blue-500" /> Filtros Activos
                    </div>
                    <div className="h-10 w-px bg-slate-200 dark:bg-white/10 hidden md:block"></div>
                    
                    <div className="flex-1 w-full grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2 block">Agrupación de Tiempo</label>
                            <select 
                                value={period}
                                onChange={e => setPeriod(e.target.value)}
                                className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg py-1.5 px-4 text-sm font-bold text-slate-800 dark:text-white outline-none focus:ring-2 focus:ring-blue-500 appearance-none"
                            >
                                {periodOptions.map(o => <option key={o.value} value={o.value} className="dark:bg-slate-900">{o.label}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2 block">Tipo de Evento</label>
                            <select 
                                value={eventType}
                                onChange={e => setEventType(e.target.value)}
                                className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg py-1.5 px-4 text-sm font-bold text-slate-800 dark:text-white outline-none focus:ring-2 focus:ring-blue-500 appearance-none"
                            >
                                {typeOptions.map(o => <option key={o.value} value={o.value} className="dark:bg-slate-900">{o.label}</option>)}
                            </select>
                        </div>
                    </div>
                </div>

                {loading ? (
                    <div className="py-1.5 text-center">
                        <div className="size-8 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mx-auto mb-4"></div>
                        <p className="text-sm font-semibold uppercase tracking-wide text-slate-400 animate-pulse">Procesando cubos de datos...</p>
                    </div>
                ) : !data ? (
                    <div className="text-center py-1.5 text-slate-500">Error al cargar datos.</div>
                ) : (
                    <div className="space-y-3 animate-in fade-in slide-in-from-bottom-4 duration-700">
                        {/* KPIs */}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                            <div className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-md p-4 shadow-sm flex flex-col justify-between">
                                <div className="size-9 rounded-lg bg-blue-500/10 text-blue-500 flex items-center justify-center mb-3">
                                    <Users size={24} />
                                </div>
                                <div>
                                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Asistencia Total</p>
                                    <p className="text-xl font-bold text-slate-900 dark:text-white mt-1">{data.kpis.total_attendance}</p>
                                </div>
                            </div>

                            <div className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-md p-4 shadow-sm flex flex-col justify-between">
                                <div className="size-9 rounded-lg bg-indigo-500/10 text-indigo-500 flex items-center justify-center mb-3">
                                    <TrendingUp size={24} />
                                </div>
                                <div>
                                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Promedio por Sesión</p>
                                    <p className="text-xl font-bold text-slate-900 dark:text-white mt-1">{data.kpis.avg_per_session}</p>
                                </div>
                            </div>

                            <div className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-md p-4 shadow-sm flex flex-col justify-between">
                                <div className="size-9 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center mb-3">
                                    <Award size={24} />
                                </div>
                                <div>
                                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Período Pico</p>
                                    <p className="text-base font-bold text-slate-900 dark:text-white mt-1">{data.kpis.peak_period?.label}</p>
                                    <p className="text-xs text-emerald-500 font-bold mt-1">{data.kpis.peak_period?.total} asistencias</p>
                                </div>
                            </div>

                            <div className="bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/5 rounded-md p-4 shadow-sm flex flex-col justify-between relative overflow-hidden group">
                                <div className={`absolute top-0 inset-x-0 h-1 ${data.kpis.trend_percentage >= 0 ? 'bg-emerald-500' : 'bg-red-500'}`}></div>
                                <div className={`size-9 rounded-lg flex items-center justify-center mb-3 ${data.kpis.trend_percentage >= 0 ? 'bg-emerald-500/10 text-emerald-500' : 'bg-red-500/10 text-red-500'}`}>
                                    <TrendingUp size={24} className={data.kpis.trend_percentage < 0 ? 'rotate-180' : ''} />
                                </div>
                                <div>
                                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Crecimiento Cierre</p>
                                    <div className="flex items-end gap-2 mt-1">
                                        <p className="text-xl font-bold text-slate-900 dark:text-white">
                                            {data.kpis.trend_percentage > 0 ? '+' : ''}{data.kpis.trend_percentage}%
                                        </p>
                                    </div>
                                    <p className="text-xs text-slate-500 mt-1 font-medium">Último vs anterior</p>
                                </div>
                            </div>
                        </div>

                        {/* GRÁFICO MOTOR CSS */}
                        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-md p-4 shadow-sm">
                            <h3 className="text-[11px] font-semibold uppercase tracking-wide text-slate-400 mb-3 flex items-center gap-2">
                                <BarChart3 size={16} /> Tendencia en el Tiempo
                            </h3>
                            
                            {data.series.length === 0 ? (
                                <div className="text-center py-1.5 text-slate-400 text-sm font-bold">No hay datos de asistencia para mostrar en este filtro.</div>
                            ) : (
                                <div className="flex items-end gap-3 h-80 mt-4 w-full overflow-x-auto pb-6 scrollbar-thin">
                                    {data.series.map((d) => {
                                        // Maximo para normalizar alturas
                                        const maxTotal = data.kpis.peak_period?.total || 1;
                                        const heightPct = Math.max(5, Math.round((d.total / maxTotal) * 100));
                                        
                                        return (
                                            <div key={d.key} className="flex-1 min-w-[60px] max-w-[100px] flex flex-col items-center justify-end group relative h-full">
                                                {/* Tooltip */}
                                                <div className="opacity-0 group-hover:opacity-100 transition-opacity absolute -top-4 bg-slate-800 text-white text-[10px] font-bold px-3 py-2 rounded-md whitespace-nowrap z-10 flex flex-col items-center shadow-xl">
                                                    <span className="text-blue-400 mb-1">{d.label}</span>
                                                    <span>{d.total} Asistentes</span>
                                                    <span className="text-slate-400 text-[8px]">{d.sessions} sesiones</span>
                                                </div>
                                                
                                                {/* Barra */}
                                                <div 
                                                    className="w-full bg-gradient-to-t from-blue-600/20 to-blue-500/80 hover:from-blue-500 hover:to-blue-400 rounded-t-xl transition-all duration-500 border-t border-blue-400/50" 
                                                    style={{ height: `${heightPct}%` }}
                                                ></div>
                                                
                                                {/* Label Eje X */}
                                                <div className="mt-4 text-[9px] font-semibold uppercase tracking-wide text-slate-500 rotate-[-45deg] origin-top-left translate-y-2 translate-x-2 whitespace-nowrap">
                                                    {d.label}
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>

                    </div>
                )}
            </div>
        </EvangelismShell>
    );
}
