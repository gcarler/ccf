"use client";

import React from 'react';
import {
    ShieldCheck,
    Globe,
    Heart,
    Zap,
    Target,
    BarChart3,
    ArrowRight
} from 'lucide-react';

export default function TransparencyPage() {
    return (
        <div className="p-8 space-y-12 animate-in fade-in duration-1000 overflow-y-auto h-full">
            <div className="text-center space-y-4 max-w-3xl mx-auto">
                <div className="inline-flex items-center gap-2 px-3 py-1 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 rounded-full text-[10px] font-black uppercase tracking-[0.2em] w-fit mx-auto border border-emerald-200 dark:border-emerald-800">
                    <ShieldCheck size={12} /> Mayordomia Transparente
                </div>
                <h1 className="text-5xl font-black tracking-tighter text-slate-900 dark:text-white uppercase italic">
                    Impacto y <span className="text-emerald-500">Transparencia</span>
                </h1>
                <p className="text-slate-500 dark:text-slate-400 text-sm">
                    En CCF creemos en la rendición de cuentas. Aquí puedes ver cómo tus ofrendas se transforman en impacto real para el Reino de Dios.
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                {[
                    { label: 'Biblias Entregadas', value: '1,250', icon: Zap, color: 'text-blue-500' },
                    { label: 'Raciones de Comida', value: '5,000+', icon: Heart, color: 'text-rose-500' },
                    { label: 'Misiones Rurales', value: '12', icon: Globe, color: 'text-blue-500' },
                ].map((stat, i) => (
                    <div key={i} className="bg-white dark:bg-[#1e1f21] border border-slate-100 dark:border-white/5 p-8 rounded-[2.5rem] text-center space-y-4 group hover:border-emerald-500/30 transition-all shadow-sm">
                        <div className={`w-16 h-16 mx-auto bg-slate-50 dark:bg-white/5 rounded-2xl flex items-center justify-center ${stat.color} group-hover:scale-110 transition-transform`}>
                            <stat.icon size={32} />
                        </div>
                        <div>
                            <div className="text-4xl font-black text-slate-900 dark:text-white italic tracking-tighter">{stat.value}</div>
                            <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest mt-1">{stat.label}</div>
                        </div>
                    </div>
                ))}
            </div>

            <div className="bg-white dark:bg-[#1e1f21] border border-slate-100 dark:border-white/5 rounded-[3rem] overflow-hidden shadow-sm">
                <div className="grid grid-cols-1 lg:grid-cols-2">
                    <div className="p-12 space-y-8">
                        <h2 className="text-3xl font-black text-slate-900 dark:text-white tracking-tight uppercase italic">
                            ¿Donde se invierte tu <span className="text-emerald-500">semilla?</span>
                        </h2>
                        <div className="space-y-6">
                            {[
                                { label: 'Evangelismo y Misiones', pct: '40%', desc: 'Alcance a nuevas ciudades y apoyo misionero.' },
                                { label: 'Acción Social', pct: '30%', desc: 'Comedores comunitarios y ayuda a familias.' },
                                { label: 'Operaciones', pct: '20%', desc: 'Mantenimiento de templos y servicios básicos.' },
                                { label: 'Educación', pct: '10%', desc: 'Becas para la academia ministerial.' },
                            ].map((item, i) => (
                                <div key={i} className="flex gap-6 group">
                                    <div className="text-2xl font-black text-emerald-500/30 dark:text-emerald-500/20 group-hover:text-emerald-500 transition-colors">{item.pct}</div>
                                    <div className="space-y-1">
                                        <div className="text-sm font-bold text-slate-800 dark:text-white uppercase">{item.label}</div>
                                        <p className="text-xs text-slate-500 dark:text-slate-400">{item.desc}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                    <div className="bg-emerald-500/10 p-12 flex items-center justify-center relative overflow-hidden border-t lg:border-t-0 lg:border-l border-slate-100 dark:border-white/5">
                        <div className="absolute top-0 right-0 p-8 opacity-10">
                            <Target size={300} className="text-emerald-500" />
                        </div>
                        <div className="relative z-10 text-center space-y-6">
                            <div className="w-24 h-24 bg-emerald-500 text-white rounded-full flex items-center justify-center mx-auto shadow-2xl shadow-emerald-500/30">
                                <BarChart3 size={48} />
                            </div>
                            <div className="space-y-2">
                                <h3 className="text-2xl font-black text-slate-900 dark:text-white uppercase italic">Auditoría Externa</h3>
                                <p className="text-sm text-emerald-600 dark:text-emerald-400 font-medium">
                                    Nuestros estados financieros son revisados trimestralmente por un comité de transparencia.
                                </p>
                            </div>
                            <button className="px-8 py-4 bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-black uppercase tracking-widest rounded-2xl transition-all flex items-center gap-2 mx-auto shadow-lg shadow-emerald-500/20">
                                Ver Reporte Anual <ArrowRight size={16} />
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
