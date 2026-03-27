"use client";

import React, { useState } from 'react';
import { 
    Target, 
    Zap, 
    Heart, 
    Globe, 
    Plus, 
    TrendingUp,
    ChevronRight,
    MapPin
} from 'lucide-react';

export default function AdminMissionImpactPage() {
    return (
        <div className="p-8 space-y-8 animate-in fade-in duration-700">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                <div className="space-y-2">
                    <div className="inline-flex items-center gap-2 px-3 py-1 bg-blue-500/10 text-blue-500 rounded-full text-[10px] font-black uppercase tracking-[0.2em] w-fit">
                        <Target size={12} /> Metricas de Impacto del Reino
                    </div>
                    <h1 className="text-4xl font-black tracking-tighter text-white uppercase italic">
                        Impacto <span className="text-blue-500">Misionero</span>
                    </h1>
                    <p className="text-muted-foreground text-sm max-w-xl">
                        Registro y monitoreo de metas alcanzadas en misiones rurales, urbanas y accion social.
                    </p>
                </div>

                <button className="px-6 py-3 bg-blue-500 hover:bg-blue-600 text-black text-[10px] font-black uppercase tracking-widest rounded-2xl transition-all shadow-2xl flex items-center gap-2">
                    <Plus size={16} /> Registrar Impacto
                </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2 space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {[
                            { label: 'Proyectos Activos', value: '8', icon: Globe, color: 'text-blue-400' },
                            { label: 'Familias Alcanzadas', value: '450', icon: Heart, color: 'text-rose-400' },
                        ].map((stat, i) => (
                            <div key={i} className="bg-[#1e1f21] border border-white/5 p-8 rounded-3xl flex items-center gap-6 group hover:border-blue-500/30 transition-all">
                                <div className="w-16 h-16 bg-white/5 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
                                    <stat.icon size={32} className={stat.color} />
                                </div>
                                <div>
                                    <div className="text-3xl font-black text-white italic tracking-tighter">{stat.value}</div>
                                    <div className="text-[10px] font-black text-muted-foreground uppercase tracking-widest">{stat.label}</div>
                                </div>
                            </div>
                        ))}
                    </div>

                    <div className="bg-[#1e1f21] border border-white/5 rounded-[2.5rem] overflow-hidden">
                        <div className="p-6 border-b border-white/5 bg-white/[0.02]">
                            <h3 className="text-xs font-black text-white uppercase tracking-widest">Bitacora de Misiones</h3>
                        </div>
                        <div className="p-2">
                            {[
                                { title: 'Mision Amazonas 2026', place: 'Leticia, Colombia', metric: '150 Biblias entregadas', date: 'Hace 2 dias' },
                                { title: 'Comedor Comunitario Sur', place: 'Barrio El Sol', metric: '200 Almuerzos servidos', date: 'Ayer' },
                                { title: 'Brigada de Salud Integral', place: 'Vereda La Union', metric: '80 Atenciones medicas', date: 'Hace 1 semana' },
                            ].map((item, i) => (
                                <div key={i} className="p-6 hover:bg-white/[0.02] rounded-2xl transition-all flex items-center justify-between group">
                                    <div className="flex items-center gap-4">
                                        <div className="w-12 h-12 bg-white/5 rounded-xl flex items-center justify-center text-blue-500">
                                            <MapPin size={24} />
                                        </div>
                                        <div>
                                            <h4 className="text-sm font-bold text-white uppercase group-hover:text-blue-400 transition-colors">{item.title}</h4>
                                            <div className="text-[10px] text-muted-foreground font-bold uppercase tracking-tighter flex items-center gap-2">
                                                {item.place} <span className="opacity-20">•</span> {item.date}
                                            </div>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-6">
                                        <div className="text-right">
                                            <div className="text-xs font-black text-primary italic">{item.metric}</div>
                                            <div className="text-[8px] text-muted-foreground font-black uppercase tracking-widest">METRICA CLAVE</div>
                                        </div>
                                        <ChevronRight size={18} className="text-white/10 group-hover:text-blue-500 transition-all" />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="space-y-6">
                    <div className="bg-gradient-to-br from-blue-500/20 to-primary/20 border border-blue-500/20 p-8 rounded-[2.5rem] space-y-6">
                        <h3 className="text-xl font-black text-white tracking-tighter uppercase italic flex items-center gap-2">
                            <TrendingUp size={20} className="text-blue-500" /> Metas Globales
                        </h3>
                        <div className="space-y-6">
                            {[
                                { label: 'Almas para Cristo', current: 850, target: 1000, color: 'bg-blue-500' },
                                { label: 'Impacto Social', current: 12000, target: 20000, color: 'bg-primary' },
                                { label: 'Nuevas Plantaciones', current: 3, target: 5, color: 'bg-emerald-500' },
                            ].map((goal, i) => (
                                <div key={i} className="space-y-2">
                                    <div className="flex justify-between text-[10px] font-black uppercase tracking-widest">
                                        <span className="text-white/60">{goal.label}</span>
                                        <span className="text-white">{Math.round((goal.current/goal.target)*100)}%</span>
                                    </div>
                                    <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                                        <div className={`h-full ${goal.color} transition-all duration-1000`} style={{ width: `${(goal.current/goal.target)*100}%` }} />
                                    </div>
                                    <div className="text-[8px] text-muted-foreground font-bold text-right uppercase">{goal.current} de {goal.target}</div>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="bg-[#1e1f21] border border-white/5 p-8 rounded-[2.5rem] space-y-4">
                        <h3 className="text-xs font-black text-white uppercase tracking-widest">Analisis de Impacto</h3>
                        <p className="text-[11px] text-muted-foreground leading-relaxed">
                            Los datos de impacto son utilizados para generar los reportes de transparencia ministerial y motivar a la congregacion.
                        </p>
                        <button className="w-full py-3 bg-white/5 hover:bg-white/10 text-white text-[10px] font-black uppercase tracking-widest rounded-xl transition-all border border-white/5">
                            Generar Reporte PDF
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
