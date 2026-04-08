"use client";

import React, { useState, useEffect } from 'react';
import { 
    Users, TrendingUp, UserPlus, Heart, 
    ArrowUpRight, ArrowDownRight, Calendar, 
    Filter, Download, Share2, Sparkles,
    Activity, ShieldCheck, Target, BarChart3,
    Clock, MousePointer2, ChevronRight
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import { ViewType, getStoredView } from '@/components/ViewSwitcher';
import CrmViewPlaceholder from '@/components/crm/CrmViewPlaceholder';

const KPI_ROWS = [
    { label: 'Nuevos Miembros', value: '128', trend: '+14.2%' },
    { label: 'Retención', value: '94.5%', trend: '+2.1%' },
    { label: 'Conversión', value: '18.2%', trend: '-3.5%' },
    { label: 'Servidores Activos', value: '245', trend: '+8.0%' },
];

export default function CrmAnalyticsPage() {
    const { token } = useAuth();
    const [loading, setLoading] = useState(true);
    const [timeframe, setTimeframe] = useState('Este Mes');
    const ALL_VIEWS: ViewType[] = ['table', 'list', 'grid', 'board', 'kanban', 'gantt', 'calendar', 'wiki'];
    const [viewType, setViewType] = useState<ViewType>(() => getStoredView('crm_analytics_view', 'grid'));
    const [wikiNotes, setWikiNotes] = useState('');

    useEffect(() => {
        // Simular carga de datos masivos
        const timer = setTimeout(() => setLoading(false), 800);
        return () => clearTimeout(timer);
    }, []);

    useEffect(() => {
        const saved = localStorage.getItem('crm_analytics_wiki_notes');
        if (saved) setWikiNotes(saved);
    }, []);

    useEffect(() => {
        localStorage.setItem('crm_analytics_wiki_notes', wikiNotes);
    }, [wikiNotes]);

    const containerVariants = {
        hidden: { opacity: 0 },
        show: { opacity: 1, transition: { staggerChildren: 0.1 } }
    };

    const itemVariants = {
        hidden: { opacity: 0, y: 20 },
        show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 300, damping: 24 } }
    };

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CRM Pastoral', icon: Users },
                { label: 'Analítica Avanzada', icon: BarChart3 }
            ]}
            viewOptions={ALL_VIEWS}
            viewType={viewType}
            onViewChange={setViewType}
            rightActions={
                <div className="flex items-center gap-3">
                    <button className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-[11px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-300 hover:bg-slate-50 transition-all">
                        <Download size={14} /> Exportar PDF
                    </button>
                    <button className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-xl text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 active:scale-95 transition-all">
                        <Share2 size={14} /> Compartir Reporte
                    </button>
                </div>
            }
        >
            {viewType === 'list' && (
                <div className="space-y-3">
                    {KPI_ROWS.map((kpi) => (
                        <div key={kpi.label} className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-4 flex items-center justify-between">
                            <div>
                                <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">{kpi.label}</p>
                                <p className="text-xl font-black text-slate-800 dark:text-slate-100">{kpi.value}</p>
                            </div>
                            <span className={clsx("text-[10px] font-black uppercase tracking-widest", kpi.trend.startsWith('-') ? 'text-rose-500' : 'text-emerald-500')}>{kpi.trend}</span>
                        </div>
                    ))}
                </div>
            )}

            {viewType === 'table' && (
                <div className="rounded-2xl border border-slate-200 dark:border-white/10 overflow-hidden bg-white dark:bg-white/5">
                    <table className="w-full text-left">
                        <thead className="bg-slate-50 dark:bg-white/5">
                            <tr>
                                <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Métrica</th>
                                <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Valor</th>
                                <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Tendencia</th>
                            </tr>
                        </thead>
                        <tbody>
                            {KPI_ROWS.map((kpi) => (
                                <tr key={kpi.label} className="border-t border-slate-100 dark:border-white/5">
                                    <td className="px-4 py-3 text-sm font-bold text-slate-800 dark:text-slate-100">{kpi.label}</td>
                                    <td className="px-4 py-3 text-xs text-slate-500">{kpi.value}</td>
                                    <td className={clsx("px-4 py-3 text-xs font-black uppercase", kpi.trend.startsWith('-') ? 'text-rose-500' : 'text-emerald-500')}>{kpi.trend}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {(viewType === 'board' || viewType === 'kanban') && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    {[
                        { title: 'Crecimiento', items: KPI_ROWS.slice(0, 1) },
                        { title: 'Retención', items: KPI_ROWS.slice(1, 2) },
                        { title: 'Compromiso', items: KPI_ROWS.slice(2) },
                    ].map((col) => (
                        <div key={col.title} className="rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/[0.03] p-3">
                            <p className="mb-3 text-[10px] font-black uppercase tracking-widest text-slate-500">{col.title}</p>
                            <div className="space-y-2">
                                {col.items.map((item) => (
                                    <div key={item.label} className="rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-3">
                                        <p className="text-xs font-black text-slate-800 dark:text-slate-100">{item.label}</p>
                                        <p className="text-[10px] text-slate-400">{item.value} · {item.trend}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {viewType === 'calendar' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'].map((day, idx) => (
                        <div key={day} className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-4">
                            <p className="mb-2 text-[10px] font-black uppercase tracking-widest text-slate-500">{day}</p>
                            <p className="text-sm font-black text-slate-800 dark:text-slate-100">Actividad estimada: {Math.max(10, 85 - idx * 8)}%</p>
                        </div>
                    ))}
                </div>
            )}

            {viewType === 'gantt' && (
                <div className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-4 space-y-3">
                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">Roadmap de objetivos trimestrales</p>
                    {[
                        { name: 'Consolidación nuevos', progress: 72 },
                        { name: 'Retención líderes', progress: 58 },
                        { name: 'Activación servidores', progress: 81 },
                    ].map((row) => (
                        <div key={row.name} className="space-y-1">
                            <div className="flex items-center justify-between text-[11px]"><span className="font-bold text-slate-700 dark:text-slate-300">{row.name}</span><span className="font-black text-slate-400">{row.progress}%</span></div>
                            <div className="h-2 rounded-full bg-slate-100 dark:bg-white/10 overflow-hidden"><div className="h-full bg-blue-600" style={{ width: `${row.progress}%` }} /></div>
                        </div>
                    ))}
                </div>
            )}

            {viewType === 'wiki' && (
                <div className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-4 space-y-3">
                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">Wiki analítica CRM</p>
                    <textarea
                        value={wikiNotes}
                        onChange={(e) => setWikiNotes(e.target.value)}
                        placeholder="Documenta definiciones de métricas, fuentes de datos, supuestos y acuerdos de interpretación para liderazgo pastoral..."
                        className="w-full min-h-[320px] rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 p-4 text-sm font-medium text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20"
                    />
                </div>
            )}

            {!['table', 'list', 'grid', 'board', 'kanban', 'gantt', 'calendar', 'wiki'].includes(viewType) && (
                <CrmViewPlaceholder moduleName="Analitica CRM" viewType={viewType} />
            )}

            {viewType === 'grid' && (
            <div className="space-y-10 pb-20 font-sans relative">
                
                {/* 1. Header & Quick Filters */}
                <motion.div variants={itemVariants} initial="hidden" animate="show" className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                    <div className="space-y-2">
                        <h1 className="text-4xl font-black text-slate-800 dark:text-white tracking-tighter">
                            Salud <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">Congregacional.</span>
                        </h1>
                        <p className="text-slate-500 dark:text-slate-400 font-medium">Análisis de crecimiento, retención y compromiso espiritual.</p>
                    </div>
                    
                    <div className="flex bg-white dark:bg-white/5 p-1.5 rounded-2xl border border-slate-200 dark:border-white/10 shadow-sm">
                        {['7 Días', 'Este Mes', 'Trimestre', '2026'].map((t) => (
                            <button 
                                key={t} 
                                onClick={() => setTimeframe(t)}
                                className={clsx(
                                    "px-5 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all",
                                    timeframe === t ? "bg-blue-600 text-white shadow-lg" : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                                )}
                            >
                                {t}
                            </button>
                        ))}
                    </div>
                </motion.div>

                {/* 2. Key Performance Indicators (Custom SVG Mini Charts) */}
                <motion.div variants={containerVariants} initial="hidden" animate="show" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    <AnalyticsKpi 
                        label="Nuevos Miembros" value="128" trend="+14.2%" 
                        chartData={[20, 40, 35, 50, 45, 70, 65]} color="blue" 
                    />
                    <AnalyticsKpi 
                        label="Retención" value="94.5%" trend="+2.1%" 
                        chartData={[80, 85, 82, 90, 88, 92, 94]} color="emerald" 
                    />
                    <AnalyticsKpi 
                        label="Conversión" value="18.2%" trend="-3.5%" 
                        chartData={[25, 22, 28, 20, 18, 15, 18]} color="amber" isDown 
                    />
                    <AnalyticsKpi 
                        label="Servidores Activos" value="245" trend="+8.0%" 
                        chartData={[180, 190, 210, 205, 230, 240, 245]} color="indigo" 
                    />
                </motion.div>

                {/* 3. Main Analytics Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                    
                    {/* Growth Curve (Main Chart Area) */}
                    <motion.div variants={itemVariants} initial="hidden" animate="show" className="lg:col-span-8 bg-white dark:bg-[#15171c] rounded-[3rem] border border-slate-100 dark:border-white/5 p-10 shadow-xl shadow-slate-200/20 dark:shadow-none relative overflow-hidden group">
                        <div className="absolute top-0 right-0 p-10 opacity-5 group-hover:opacity-10 transition-opacity"><TrendingUp size={120} className="text-blue-600" /></div>
                        
                        <div className="relative z-10 flex flex-col h-full">
                            <div className="flex items-center justify-between mb-12">
                                <div>
                                    <h3 className="text-xl font-black text-slate-800 dark:text-white tracking-tight uppercase">Curva de Crecimiento</h3>
                                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] mt-1">Comparativa Miembros vs Visitantes</p>
                                </div>
                                <div className="flex items-center gap-6">
                                    <div className="flex items-center gap-2">
                                        <div className="size-2 rounded-full bg-blue-600" />
                                        <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Miembros</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <div className="size-2 rounded-full bg-indigo-300" />
                                        <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Visitantes</span>
                                    </div>
                                </div>
                            </div>

                            {/* Large Line Chart SVG */}
                            <div className="flex-1 w-full min-h-[300px] relative mt-4">
                                <svg viewBox="0 0 800 300" className="w-full h-full overflow-visible">
                                    <defs>
                                        <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="0%" stopColor="rgb(37, 99, 235)" stopOpacity="0.2" />
                                            <stop offset="100%" stopColor="rgb(37, 99, 235)" stopOpacity="0" />
                                        </linearGradient>
                                    </defs>
                                    {/* Grid Lines */}
                                    {[0, 1, 2, 3].map(i => (
                                        <line key={i} x1="0" y1={i * 100} x2="800" y2={i * 100} stroke="currentColor" strokeOpacity="0.05" />
                                    ))}
                                    {/* Area */}
                                    <path d="M0,250 Q100,200 200,220 T400,150 T600,100 T800,80 L800,300 L0,300 Z" fill="url(#chartGradient)" />
                                    {/* Main Line */}
                                    <motion.path 
                                        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 2, ease: "easeInOut" }}
                                        d="M0,250 Q100,200 200,220 T400,150 T600,100 T800,80" 
                                        fill="none" stroke="rgb(37, 99, 235)" strokeWidth="4" strokeLinecap="round" 
                                    />
                                    {/* Secondary Line */}
                                    <motion.path 
                                        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 2, delay: 0.5, ease: "easeInOut" }}
                                        d="M0,280 Q100,260 200,270 T400,220 T600,180 T800,160" 
                                        fill="none" stroke="rgb(165, 180, 252)" strokeWidth="3" strokeDasharray="8 8" strokeLinecap="round" 
                                    />
                                    {/* Points */}
                                    <circle cx="400" cy="150" r="6" fill="white" stroke="rgb(37, 99, 235)" strokeWidth="3" className="drop-shadow-lg" />
                                    <circle cx="800" cy="80" r="6" fill="white" stroke="rgb(37, 99, 235)" strokeWidth="3" className="drop-shadow-lg" />
                                </svg>
                                
                                {/* X-Axis Labels */}
                                <div className="flex justify-between mt-6 px-2">
                                    {['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul'].map(m => (
                                        <span key={m} className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{m}</span>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </motion.div>

                    {/* Funnel Section (Sidebar Style) */}
                    <motion.aside variants={itemVariants} initial="hidden" animate="show" className="lg:col-span-4 space-y-8">
                        
                        {/* Pipeline Funnel Visualization */}
                        <div className="p-8 bg-white dark:bg-[#15171c] rounded-[3rem] border border-slate-100 dark:border-white/5 shadow-xl space-y-8">
                            <h3 className="text-[11px] font-black text-slate-400 uppercase tracking-[0.3em] flex items-center gap-2">
                                <Target size={16} className="text-blue-600" /> Embudo de Integración
                            </h3>
                            
                            <div className="space-y-4">
                                <FunnelStep label="Visitantes" value="1,240" percent={100} color="bg-blue-600" />
                                <FunnelStep label="Seguimiento" value="845" percent={68} color="bg-blue-500" />
                                <FunnelStep label="En Casas" value="420" percent={34} color="bg-indigo-500" />
                                <FunnelStep label="Comprometidos" value="156" percent={12} color="bg-emerald-500" />
                            </div>

                            <div className="pt-6 border-t border-slate-50 dark:border-white/5">
                                <button className="w-full py-4 bg-slate-50 dark:bg-white/5 rounded-2xl text-[10px] font-black uppercase tracking-widest text-slate-500 hover:text-blue-600 transition-all flex items-center justify-center gap-2 group">
                                    Ver Optimización IA <Sparkles size={14} className="group-hover:animate-pulse" />
                                </button>
                            </div>
                        </div>

                        {/* MESH AI Prediction */}
                        <div className="p-8 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-[3rem] text-white shadow-2xl relative overflow-hidden group">
                            <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')] opacity-10" />
                            <div className="relative z-10 space-y-6">
                                <div className="flex items-center gap-3">
                                    <div className="size-10 rounded-2xl bg-white/20 backdrop-blur-md flex items-center justify-center border border-white/20 shadow-inner">
                                        <Sparkles size={20} />
                                    </div>
                                    <h4 className="text-lg font-black tracking-tight leading-none uppercase">MESH Forecast</h4>
                                </div>
                                <p className="text-sm font-medium text-blue-100 leading-relaxed">
                                    Basado en la tendencia actual de Casas de Gloria, se proyecta un incremento del <span className="font-black text-white">15% en membresía activa</span> para el próximo trimestre.
                                </p>
                                <button className="w-full py-4 bg-white text-blue-900 rounded-2xl font-black text-[10px] uppercase tracking-[0.2em] shadow-xl hover:scale-[1.02] active:scale-95 transition-all">
                                    Expandir Análisis
                                </button>
                            </div>
                        </div>
                    </motion.aside>
                </div>

                {/* 4. Secondary Row: Activity Heatmap & Top Zones */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    
                    <div className="lg:col-span-2 p-10 bg-white dark:bg-[#15171c] rounded-[3rem] border border-slate-100 dark:border-white/5 shadow-xl flex flex-col justify-between group">
                        <div className="flex items-center justify-between mb-8">
                            <h3 className="text-[11px] font-black text-slate-400 uppercase tracking-[0.3em] flex items-center gap-2">
                                <Activity size={16} className="text-emerald-500" /> Mapa de Calor de Actividad
                            </h3>
                            <button className="p-2 text-slate-300 hover:text-slate-600 transition-colors"><ChevronRight size={20} /></button>
                        </div>
                        
                        {/* Fake Heatmap Grid */}
                        <div className="grid grid-cols-12 gap-2 h-48">
                            {[...Array(60)].map((_, i) => {
                                const intensity = Math.random();
                                return (
                                    <div 
                                        key={i} 
                                        className={clsx(
                                            "rounded-md transition-all duration-500 hover:scale-110 cursor-pointer",
                                            intensity > 0.8 ? "bg-blue-600" : intensity > 0.5 ? "bg-blue-400" : intensity > 0.2 ? "bg-blue-200" : "bg-slate-50 dark:bg-white/5"
                                        )}
                                    />
                                );
                            })}
                        </div>
                        
                        <div className="mt-8 flex items-center justify-between text-[9px] font-black uppercase tracking-widest text-slate-400">
                            <span>Baja Actividad</span>
                            <div className="flex gap-1">
                                <div className="size-2 rounded bg-slate-50 dark:bg-white/5" />
                                <div className="size-2 rounded bg-blue-200" />
                                <div className="size-2 rounded bg-blue-400" />
                                <div className="size-2 rounded bg-blue-600" />
                            </div>
                            <span>Alta Frecuencia</span>
                        </div>
                    </div>

                    <div className="p-10 bg-white dark:bg-[#15171c] rounded-[3rem] border border-slate-100 dark:border-white/5 shadow-xl space-y-8">
                        <h3 className="text-[11px] font-black text-slate-400 uppercase tracking-[0.3em] flex items-center gap-2">
                            <ShieldCheck size={16} className="text-blue-600" /> Top Zonas de Impacto
                        </h3>
                        
                        <div className="space-y-6">
                            <ZoneRow name="Norte / El Olivar" value="45%" color="bg-blue-600" />
                            <ZoneRow name="Sur / Urbanización" value="32%" color="bg-indigo-500" />
                            <ZoneRow name="Centro / Casco Viejo" value="18%" color="bg-purple-500" />
                            <ZoneRow name="Este / Expansión" value="5%" color="bg-slate-200" />
                        </div>
                    </div>

                </div>
            </div>
            )}
        </CrmShell>
    );
}

function AnalyticsKpi({ label, value, trend, chartData, color, isDown = false }: any) {
    const strokeColor = isDown ? 'rgb(244, 63, 94)' : color === 'blue' ? 'rgb(37, 99, 235)' : color === 'emerald' ? 'rgb(16, 185, 129)' : color === 'indigo' ? 'rgb(79, 70, 229)' : 'rgb(37, 99, 235)';
    const bgColor = isDown ? 'rgba(244, 63, 94, 0.1)' : color === 'blue' ? 'rgba(37, 99, 235, 0.1)' : color === 'emerald' ? 'rgba(16, 185, 129, 0.1)' : color === 'indigo' ? 'rgba(79, 70, 229, 0.1)' : 'rgba(37, 99, 235, 0.1)';

    return (
        <motion.div variants={{ hidden: { opacity: 0, scale: 0.95 }, show: { opacity: 1, scale: 1 } }} className="p-8 bg-white dark:bg-[#15171c] rounded-[2.5rem] border border-slate-100 dark:border-white/5 shadow-xl shadow-slate-200/20 dark:shadow-none hover:-translate-y-1 transition-all duration-300 group">
            <div className="flex items-center justify-between mb-4">
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">{label}</p>
                <div className={clsx(
                    "flex items-center gap-1 px-2 py-1 rounded-lg text-[9px] font-bold",
                    isDown ? "bg-rose-50 text-rose-600" : "bg-emerald-50 text-emerald-600"
                )}>
                    {isDown ? <ArrowDownRight size={10} strokeWidth={3} /> : <ArrowUpRight size={10} strokeWidth={3} />} {trend}
                </div>
            </div>
            
            <div className="flex items-end justify-between">
                <span className="text-3xl font-black text-slate-800 dark:text-white tracking-tighter">{value}</span>
                
                {/* Mini Chart SVG */}
                <div className="w-20 h-10 overflow-visible">
                    <svg viewBox="0 0 100 40" className="w-full h-full">
                        <motion.path 
                            initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.5 }}
                            d={`M 0,${40 - chartData[0]} ${chartData.map((d: number, i: number) => `L ${(i / (chartData.length - 1)) * 100},${40 - d}`).join(' ')}`}
                            fill="none" stroke={strokeColor} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" 
                        />
                    </svg>
                </div>
            </div>
        </motion.div>
    );
}

function FunnelStep({ label, value, percent, color }: any) {
    return (
        <div className="space-y-2 group cursor-pointer">
            <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-slate-500">
                <span>{label}</span>
                <span className="text-slate-800 dark:text-white font-black">{value}</span>
            </div>
            <div className="h-2 w-full bg-slate-50 dark:bg-white/5 rounded-full overflow-hidden shadow-inner">
                <motion.div 
                    initial={{ width: 0 }} animate={{ width: `${percent}%` }} transition={{ duration: 1.5, delay: 0.5 }}
                    className={clsx("h-full rounded-full transition-all group-hover:brightness-110 relative", color)} 
                >
                    <div className="absolute inset-0 bg-white/20 animate-[shimmer_2s_infinite]" />
                </motion.div>
            </div>
        </div>
    );
}

function ZoneRow({ name, value, color }: any) {
    return (
        <div className="space-y-2 group cursor-pointer">
            <div className="flex items-center justify-between mb-1">
                <span className="text-[11px] font-bold text-slate-700 dark:text-slate-200 group-hover:text-blue-600 transition-colors">{name}</span>
                <span className="text-[11px] font-black text-slate-800 dark:text-white">{value}</span>
            </div>
            <div className="h-1.5 w-full bg-slate-50 dark:bg-white/5 rounded-full overflow-hidden">
                <motion.div 
                    initial={{ width: 0 }} animate={{ width: value }} transition={{ duration: 1 }}
                    className={clsx("h-full rounded-full", color)} 
                />
            </div>
        </div>
    );
}
