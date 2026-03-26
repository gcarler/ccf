"use client";

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import AdminShell from '@/components/admin/AdminShell';
import AdminHero from '@/components/admin/AdminHero';
import {
    TrendingUp,
    PieChart,
    DollarSign,
    ArrowUpRight,
    Download,
    Link2,
    Bell,
    Users,
    GraduationCap,
    BookOpen,
    Target,
    Filter,
    Calendar,
    ChevronDown,
    Activity,
    Zap,
    BrainCircuit,
    Layers
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

type ReportTab = 'academic' | 'financial' | 'operational';

export default function AdvancedBIReports() {
    const { isAuthenticated, token } = useAuth();
    const [activeTab, setActiveTab] = useState<ReportTab>('academic');
    const [analytics, setAnalytics] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchAnalytics = async () => {
            if (!token) return;
            setLoading(true);
            try {
                // Simulamos carga de datos complejos de BI
                const data = await apiFetch('/analytics/events/summary', { token });
                setAnalytics(data);
            } catch (e) {
                console.error('BI Analytics fetch failed', e);
            } finally {
                setLoading(false);
            }
        };
        fetchAnalytics();
    }, [token, activeTab]);

    if (!isAuthenticated) return null;

    const tabs = [
        { id: 'academic', label: 'Académico', icon: GraduationCap },
        { id: 'financial', label: 'Financiero', icon: DollarSign },
        { id: 'operational', label: 'Operativo', icon: Activity },
    ];

    return (
        <AdminShell
            breadcrumbs={[
                { label: 'Gestión Central', icon: Bell },
                { label: 'Inteligencia de Negocios', icon: BrainCircuit }
            ]}
        >
            <AdminHero
                eyebrow="Business Intelligence"
                title="Centro de Análisis Avanzado"
                description="Visualiza el impacto real de la plataforma a través de métricas cruzadas. Optimus BI analiza tendencias de retención, ingresos y efectividad académica."
                tags={['BI Core', 'Machine Learning', 'Real-time']}
                watchers={['Dirección General', 'Comité Académico']}
                primaryAction={{ label: 'Exportar Reporte Full', icon: Download, onClick: () => {} }}
                secondaryAction={{ label: 'Configurar Alertas', icon: Zap, onClick: () => {} }}
            />

            {/* Sub-navigation Tabs */}
            <div className="flex flex-wrap items-center gap-4 mb-10 bg-slate-100/50 dark:bg-white/5 p-2 rounded-[2rem] w-fit border border-slate-200 dark:border-white/10">
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id as ReportTab)}
                        className={clsx(
                            "flex items-center gap-3 px-8 py-3.5 rounded-[1.5rem] text-[11px] font-black uppercase tracking-widest transition-all active:scale-95",
                            activeTab === tab.id 
                                ? "bg-white dark:bg-blue-600 text-blue-600 dark:text-white shadow-xl shadow-blue-500/10" 
                                : "text-slate-500 hover:bg-white/50 dark:hover:bg-white/5"
                        )}
                    >
                        <tab.icon size={16} />
                        {tab.label}
                    </button>
                ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                {/* Main Insight Card */}
                <div className="lg:col-span-8 space-y-8">
                    <section className="relative overflow-hidden rounded-[3rem] bg-slate-900 border border-white/5 p-10 text-white shadow-2xl group min-h-[400px] flex flex-col justify-between">
                        <div className="absolute top-0 right-0 -mr-24 -mt-24 size-96 bg-blue-600/20 rounded-full blur-[100px] group-hover:bg-blue-600/30 transition-all duration-1000" />
                        
                        <div className="relative z-10 flex justify-between items-start">
                            <div>
                                <div className="flex items-center gap-3 mb-4">
                                    <div className="px-3 py-1 bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded-full text-[9px] font-black uppercase tracking-widest flex items-center gap-2">
                                        <Layers size={12} /> Perspectiva de {activeTab}
                                    </div>
                                    <span className="text-slate-500 text-[10px] font-bold uppercase tracking-widest">Actulizado hace 2 min</span>
                                </div>
                                <h3 className="text-4xl font-black tracking-tighter leading-none mb-2">Indicador de Eficacia</h3>
                                <p className="text-slate-400 text-sm font-medium max-w-md">Análisis predictivo basado en el comportamiento del último trimestre.</p>
                            </div>
                            <div className="flex flex-col items-end gap-2">
                                <span className="text-5xl font-black text-white tracking-tighter">84.2%</span>
                                <div className="flex items-center gap-1.5 text-emerald-500 text-[10px] font-black uppercase tracking-widest">
                                    <TrendingUp size={14} /> +5.4% este mes
                                </div>
                            </div>
                        </div>

                        {/* Custom Chart Illustration */}
                        <div className="relative z-10 h-48 flex items-end gap-4 mt-8">
                            {[65, 40, 80, 55, 90, 70, 85, 60, 100, 75, 95, 80].map((h, i) => (
                                <div key={i} className="flex-1 flex flex-col items-center gap-3 group/bar">
                                    <div 
                                        style={{ height: `${h}%` }} 
                                        className={clsx(
                                            "w-full rounded-t-2xl transition-all duration-700 relative",
                                            i === 8 ? "bg-blue-500 shadow-[0_0_30px_rgba(59,130,246,0.5)]" : "bg-white/10 opacity-30 group-hover/bar:opacity-60"
                                        )}
                                    >
                                        {i === 8 && <div className="absolute -top-10 left-1/2 -translate-x-1/2 bg-white text-slate-900 px-3 py-1.5 rounded-lg text-[10px] font-black shadow-xl whitespace-nowrap">Pico de Actividad</div>}
                                    </div>
                                    <span className="text-[9px] font-black text-slate-500 uppercase">{['E','F','M','A','M','J','J','A','S','O','N','D'][i]}</span>
                                </div>
                            ))}
                        </div>
                    </section>

                    {/* Secondary Metrics Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[2.5rem] p-8 space-y-6 shadow-xl">
                            <div className="flex justify-between items-center">
                                <div className="size-12 rounded-2xl bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 flex items-center justify-center">
                                    <Users size={24} />
                                </div>
                                <button className="p-2 hover:bg-slate-100 rounded-lg transition-colors"><ChevronDown size={18} /></button>
                            </div>
                            <div>
                                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">Retención de Cohortes</p>
                                <h4 className="text-2xl font-black tracking-tight">76% Finalización</h4>
                            </div>
                            <div className="space-y-3">
                                <div className="flex justify-between text-[10px] font-black uppercase tracking-widest text-slate-400">
                                    <span>Formal</span>
                                    <span>92%</span>
                                </div>
                                <div className="h-2 w-full bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
                                    <div className="h-full bg-indigo-500 w-[92%]" />
                                </div>
                                <div className="flex justify-between text-[10px] font-black uppercase tracking-widest text-slate-400">
                                    <span>No Formal</span>
                                    <span>64%</span>
                                </div>
                                <div className="h-2 w-full bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
                                    <div className="h-full bg-slate-400 w-[64%]" />
                                </div>
                            </div>
                        </div>

                        <div className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[2.5rem] p-8 space-y-6 shadow-xl">
                            <div className="flex justify-between items-center">
                                <div className="size-12 rounded-2xl bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 flex items-center justify-center">
                                    <Target size={24} />
                                </div>
                                <button className="p-2 hover:bg-slate-100 rounded-lg transition-colors"><Filter size={18} /></button>
                            </div>
                            <div>
                                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">Costo por Estudiante</p>
                                <h4 className="text-2xl font-black tracking-tight">$12.50 / mes</h4>
                            </div>
                            <div className="p-4 bg-emerald-50 dark:bg-emerald-900/20 rounded-2xl border border-emerald-100 dark:border-emerald-500/20">
                                <p className="text-[10px] font-bold text-emerald-700 dark:text-emerald-400 leading-relaxed uppercase tracking-wider">
                                    Optimus AI: "Reducción del 15% en costos operativos mediante automatización de actas."
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Sidebar BI Tools */}
                <aside className="lg:col-span-4 space-y-8">
                    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-[3rem] p-8 shadow-2xl space-y-8">
                        <div className="flex items-center gap-3">
                            <BrainCircuit size={20} className="text-blue-600" />
                            <h4 className="text-lg font-black uppercase tracking-widest tracking-tighter">Acciones BI</h4>
                        </div>
                        
                        <div className="space-y-4">
                            <button className="w-full flex items-center justify-between p-5 bg-slate-50 dark:bg-white/5 rounded-2xl border border-transparent hover:border-blue-500/30 transition-all group">
                                <div className="flex items-center gap-4 text-left">
                                    <div className="size-10 rounded-xl bg-white dark:bg-white/10 flex items-center justify-center text-slate-500 shadow-sm group-hover:scale-110 transition-transform">
                                        <Calendar size={18} />
                                    </div>
                                    <div>
                                        <p className="text-[11px] font-black uppercase tracking-widest text-slate-800 dark:text-white">Filtro Temporal</p>
                                        <p className="text-[10px] font-bold text-slate-500">Últimos 6 meses</p>
                                    </div>
                                </div>
                                <ArrowUpRight size={16} className="text-slate-400" />
                            </button>

                            <button className="w-full flex items-center justify-between p-5 bg-slate-50 dark:bg-white/5 rounded-2xl border border-transparent hover:border-blue-500/30 transition-all group">
                                <div className="flex items-center gap-4 text-left">
                                    <div className="size-10 rounded-xl bg-white dark:bg-white/10 flex items-center justify-center text-slate-500 shadow-sm group-hover:scale-110 transition-transform">
                                        <BookOpen size={18} />
                                    </div>
                                    <div>
                                        <p className="text-[11px] font-black uppercase tracking-widest text-slate-800 dark:text-white">Segmento</p>
                                        <p className="text-[10px] font-bold text-slate-500">Modalidad Formal</p>
                                    </div>
                                </div>
                                <ArrowUpRight size={16} className="text-slate-400" />
                            </button>
                        </div>

                        <div className="pt-8 border-t border-slate-100 dark:border-white/5">
                            <div className="flex items-center justify-between mb-6">
                                <h5 className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Distribución de Ingresos</h5>
                                <PieChart size={14} className="text-slate-400" />
                            </div>
                            <div className="relative size-48 mx-auto mb-8">
                                <svg className="size-full -rotate-90 drop-shadow-2xl" viewBox="0 0 36 36">
                                    <circle cx="18" cy="18" r="15.9" fill="transparent" stroke="rgba(59,130,246,0.1)" strokeWidth="4" />
                                    <circle cx="18" cy="18" r="15.9" fill="transparent" stroke="#3b82f6" strokeWidth="4" strokeDasharray="65 100" />
                                    <circle cx="18" cy="18" r="15.9" fill="transparent" stroke="#1e293b" strokeWidth="4" strokeDasharray="35 100" strokeDashoffset="-65" />
                                </svg>
                                <div className="absolute inset-0 flex flex-col items-center justify-center">
                                    <span className="text-3xl font-black text-slate-900 dark:text-white tracking-tighter">$45K</span>
                                    <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest">Total USD</span>
                                </div>
                            </div>
                            <div className="space-y-3">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <div className="size-2 rounded-full bg-blue-500" />
                                        <span className="text-[11px] font-bold text-slate-600 dark:text-slate-400">Educativo</span>
                                    </div>
                                    <span className="text-[11px] font-black text-slate-900 dark:text-white">65%</span>
                                </div>
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <div className="size-2 rounded-full bg-slate-800" />
                                        <span className="text-[11px] font-bold text-slate-600 dark:text-slate-400">Donaciones</span>
                                    </div>
                                    <span className="text-[11px] font-black text-slate-900 dark:text-white">35%</span>
                                </div>
                            </div>
                        </div>

                        <button className="w-full py-5 bg-blue-600 text-white rounded-2xl text-[11px] font-black uppercase tracking-[0.2em] shadow-xl shadow-blue-500/20 active:scale-95 transition-all">
                            Generar PDF Inteligente
                        </button>
                    </div>
                </aside>
            </div>
        </AdminShell>
    );
}
