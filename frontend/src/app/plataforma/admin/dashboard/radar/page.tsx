"use client";

import React, { useEffect, useState, useCallback } from 'react';
import { 
    Users, 
    Waves, 
    BookOpen, 
    DollarSign, 
    Target,
    Shield,
    Zap,
    Sparkles,
    BarChart3,
    Loader2
} from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { motion } from 'framer-motion';
import clsx from 'clsx';

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
    const { token, isAuthenticated } = useAuth();

    const fetchRadar = useCallback(async (signal?: AbortSignal) => {
        if (!token) return;
        setLoading(true);
        try {
            // Sincronizado con el endpoint real del backend CRM
            const res = await apiFetch<RadarData>('/crm/radar', { token, signal });
            setData(res);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Error al cargar radar');
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        if (!isAuthenticated) return;
        const controller = new AbortController();
        fetchRadar(controller.signal);
        return () => controller.abort();
    }, [isAuthenticated, fetchRadar]);

    if (!isAuthenticated) return null;

    return (
 <div className="p-4 lg:p-4 space-y-3 w-full font-display overflow-y-auto scrollbar-thin relative">
            <style jsx global>{`
                .radar-aura {
                    position: relative;
                }
                .radar-aura::after {
                    content: '';
                    position: absolute;
                    inset: -1px;
                    background: linear-gradient(45deg, var(--aura-color, hsl(var(--info)/0.2)), transparent 60%);
                    z-index: -1;
                    border-radius: inherit;
                    opacity: 0;
                    transition: opacity 0.6s ease;
                }
                .radar-aura:hover::after {
                    opacity: 1;
                }
                .shimmer-bar {
                    position: relative;
                    overflow: hidden;
                }
                .shimmer-bar::after {
                    content: '';
                    position: absolute;
                    top: 0; left: -100%; width: 50%; height: 100%;
                    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
                    animation: shimmer-radar 3s infinite;
                }
                @keyframes shimmer-radar {
                    0% { left: -100%; }
                    100% { left: 200%; }
                }
                .glass-card {
                    background: rgba(255, 255, 255, 0.03);
                    backdrop-filter: blur(20px);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                }
            `}</style>

            {/* Background cinematic glow */}
            <div className="absolute top-0 right-0 size-[600px] bg-[hsl(var(--info))]/5 blur-[120px] rounded-full -mr-40 -mt-40 pointer-events-none" />

            <header className="flex flex-col gap-4 relative z-10">
                <motion.div 
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="inline-flex items-center gap-2 px-4 py-1.5 bg-[hsl(var(--info))]/10 text-[hsl(var(--primary))] rounded-full text-[10px] font-semibold uppercase tracking-wide w-fit border border-[hsl(var(--info)/100%)]/20"
                >
                    <Shield size={12} className="animate-pulse" /> Inteligencia Ministerial Optimus v3.9
                </motion.div>
                <motion.h1 
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-xl lg:text-xl font-bold tracking-tighter text-[hsl(var(--text-primary))] dark:text-white uppercase leading-none"
                >
                    Radar <span className="italic text-transparent bg-clip-text bg-gradient-to-r from-[hsl(var(--info))] to-[hsl(var(--info))]">Pastoral</span>
                </motion.h1>
                <motion.p 
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.2 }}
                    className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] text-lg font-medium max-w-2xl leading-relaxed"
                >
                    Consola de mando ejecutiva. Análisis dinámico de participación, formación académica e impacto financiero consolidado.
                </motion.p>
            </header>

            {loading ? (
                <div className="py-1.5 flex flex-col items-center justify-center gap-3">
                    <Loader2 className="animate-spin text-[hsl(var(--primary))]" size={64} strokeWidth={1.5} />
                    <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide animate-pulse">Iniciando Red Neuronal...</p>
                </div>
            ) : error ? (
                <div className="p-4 bg-danger-soft dark:bg-[hsl(var(--danger))]/10 border border-[hsl(var(--danger)/20%)] dark:border-[hsl(var(--danger)/30%)] rounded-lg text-danger-text text-center space-y-4">
                    <Zap size={40} className="mx-auto" />
                    <p className="font-semibold uppercase tracking-wide">Error de Sincronización: {error}</p>
                    <button onClick={() => fetchRadar()} className="px-4 py-3 bg-[hsl(var(--danger))] text-white rounded-lg text-[10px] font-semibold uppercase tracking-wide shadow-xl">Reintentar</button>
                </div>
            ) : (
                <>
                <motion.div 
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3"
                >
                    <RadarStat label="Participación Viva" value={data?.membresia_viva || 0} icon={Users} color="blue" trend="+5.2%" auraColor="rgba(37,99,235,0.15)" />
                    <RadarStat label="Bautismos" value={data?.bautismos_este_anio || 0} icon={Waves} color="cyan" trend="+12%" auraColor="rgba(6,182,212,0.15)" />
                    <RadarStat label="Estudiantes" value={data?.estudiantes_activos || 0} icon={BookOpen} color="emerald" trend="+8" auraColor="rgba(16,185,129,0.15)" />
                    <RadarStat label="Recaudación" value={`$${(data?.recaudacion_mes || 0).toLocaleString()}`} icon={DollarSign} color="amber" trend="+15%" auraColor="rgba(245,158,11,0.15)" />
                </motion.div>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 relative z-10">
                    <motion.div 
                        initial={{ opacity: 0, x: -30 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.3 }}
                        className="lg:col-span-7 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] dark:border-white/5 p-4 rounded-lg shadow-xl space-y-3 group"
                    >
                        <div className="flex items-center justify-between">
                            <div className="space-y-1">
                                <h2 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tighter uppercase flex items-center gap-3">
                                    <BarChart3 className="text-[hsl(var(--primary))]" /> Crecimiento Orgánico
                                </h2>
                                <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Métricas consolidadas semestrales</p>
                            </div>
                            <span className="font-semibold text-[hsl(var(--primary))] bg-info-soft px-4 py-1.5 rounded-full tracking-wide border border-[hsl(var(--info)/20%)] uppercase">Live BI</span>
                        </div>
                        
                        <div className="h-48 flex items-end justify-between gap-4 pt-10 px-4">
                            {[45, 70, 55, 90, 85, 100].map((h, i) => (
                                <div key={i} className="flex-1 flex flex-col items-center gap-4 group/bar">
                                    <div 
                                        className={clsx(
                                            "w-full rounded-t-2xl transition-all duration-700 relative shimmer-bar",
                                            i === 5 ? "bg-gradient-to-t from-[hsl(var(--info))] to-[hsl(var(--info))] shadow-[0_0_30px_rgba(37,99,235,0.3)]" : "bg-[hsl(var(--surface-2))] dark:bg-white/5 group-hover/bar:bg-[hsl(var(--surface-3))]"
                                        )}
                                        style={{ height: `${h}%` }}
                                    >
                                        <div className="absolute -top-10 left-1/2 -translate-x-1/2 opacity-0 group-hover/bar:opacity-100 transition-all transform scale-90 group-hover/bar:scale-100 bg-[hsl(var(--bg-muted))] text-white px-3 py-1.5 rounded-md font-semibold shadow-2xl">
                                            {h}%
                                        </div>
                                    </div>
                                    <span className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">M0{i+1}</span>
                                </div>
                            ))}
                        </div>
                    </motion.div>

                    <motion.div 
                        initial={{ opacity: 0, x: 30 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.4 }}
                        className="lg:col-span-5 glass-card p-4 rounded-lg shadow-2xl space-y-3 relative overflow-hidden"
                    >
                        <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:rotate-12 transition-transform duration-1000"><Sparkles size={120} /></div>
                        
                        <h2 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tighter uppercase flex items-center gap-3">
                            <Target className="text-[hsl(var(--primary))]" /> Metas Trimestrales
                        </h2>
                        <div className="space-y-3">
                            <GoalItem label="Bautismos Meta" target={50} current={data?.bautismos_este_anio || 0} color="bg-[hsl(var(--primary))]" />
                            <GoalItem label="Nuevos Personas" target={200} current={35} color="bg-[hsl(var(--success))]" />
                            <GoalItem label="Estudiantes Liderazgo" target={80} current={12} color="bg-[hsl(var(--warning))]" />
                        </div>

                        <div className="pt-8 border-t border-white/5 space-y-3">
                            <div className="flex items-center gap-4">
                                <div className="size-7 rounded-lg bg-[hsl(var(--primary))] flex items-center justify-center text-white shadow-xl shadow-[hsl(var(--primary)/0.2)]"><Zap size={24} fill="currentColor" /></div>
                                <div>
                                    <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Sugerencia IA</p>
                                    <p className="text-[13px] font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] leading-tight">Potenciar el ministerio de Hospitalidad para el próximo servicio.</p>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                </div>
                </>
            )}
        </div>
    );
}

function RadarStat({ label, value, icon: Icon, color, trend, auraColor }: any) {
    const colorMap: any = {
        blue: 'text-[hsl(var(--primary))] bg-info-soft dark:bg-[hsl(var(--info))]/20 border-[hsl(var(--info)/20%)]',
        cyan: 'text-[hsl(var(--domain-cyan)/90%)] bg-[hsl(var(--domain-cyan)/10%)] dark:bg-[hsl(var(--domain-cyan)/20%)] border-[hsl(var(--domain-cyan)/30%)]',
        emerald: 'text-[hsl(var(--success))] bg-[hsl(var(--success-muted))] border-[hsl(var(--success)/0.3)]',
        amber: 'text-[hsl(var(--warning))] bg-[hsl(var(--warning-muted))] border-[hsl(var(--warning)/0.3)]'
    };
    return (
        <div 
            className="radar-aura p-4 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] dark:border-white/5 rounded-lg shadow-sm group hover:shadow-2xl transition-all duration-500 relative overflow-hidden"
            style={{ '--aura-color': auraColor } as any}
        >
            <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:scale-125 transition-transform duration-700"><Icon size={64} /></div>
            <div className="space-y-3 relative z-10">
                <div className="flex justify-between items-center">
                    <div className={clsx("size-7 rounded-lg flex items-center justify-center transition-transform group-hover:rotate-12", colorMap[color])}>
                        <Icon size={28} />
                    </div>
                    <span className="px-3 py-1 bg-white/50 dark:bg-white/5 rounded-lg font-semibold text-[hsl(var(--success))] border border-[hsl(var(--success)/0.3)] uppercase">{trend}</span>
                </div>
                <div>
                    <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide mb-1">{label}</p>
                    <h4 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tighter leading-none">{value}</h4>
                </div>
            </div>
        </div>
    );
}

function GoalItem({ label, target, current, color }: any) {
    const pct = Math.min(100, (current / target) * 100);
    return (
        <div className="space-y-3 group/goal">
            <div className="flex justify-between text-[10px] font-semibold uppercase tracking-wide">
                <span className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] group-hover/goal:text-[hsl(var(--primary))] transition-colors">{label}</span>
                <span className="text-[hsl(var(--text-primary))] dark:text-white">{current} / {target}</span>
            </div>
            <div className="h-2 w-full bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-full overflow-hidden shadow-inner">
                <motion.div 
                    initial={{ width: 0 }} 
                    animate={{ width: `${pct}%` }} 
                    transition={{ duration: 1.5, ease: "easeOut" }}
                    className={clsx("h-full shimmer-bar relative", color)} 
                />
            </div>
        </div>
    );
}

