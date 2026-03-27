"use client";

import React, { useState } from 'react';
import { 
    Wrench, 
    Calendar, 
    AlertCircle, 
    CheckCircle2, 
    Plus, 
    Clock, 
    ChevronRight,
    Shield
} from 'lucide-react';

export default function AdminMaintenancePage() {
    return (
        <div className="p-8 space-y-8 animate-in fade-in duration-700">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                <div className="space-y-2">
                    <div className="inline-flex items-center gap-2 px-3 py-1 bg-amber-500/10 text-amber-500 rounded-full text-[10px] font-black uppercase tracking-[0.2em] w-fit">
                        <Wrench size={12} /> Gestion Tecnica de Activos
                    </div>
                    <h1 className="text-4xl font-black tracking-tighter text-white uppercase italic">
                        Agenda de <span className="text-amber-500">Mantenimiento</span>
                    </h1>
                    <p className="text-muted-foreground text-sm max-w-xl">
                        Asegura la operatividad de los equipos ministeriales mediante revisiones preventivas y correctivas programadas.
                    </p>
                </div>

                <button className="px-6 py-3 bg-amber-500 hover:bg-amber-600 text-black text-[10px] font-black uppercase tracking-widest rounded-2xl transition-all shadow-2xl flex items-center gap-2">
                    <Plus size={16} /> Programar Revision
                </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2 space-y-6">
                    <div className="bg-[#1e1f21] border border-white/5 rounded-[2.5rem] overflow-hidden">
                        <div className="p-6 border-b border-white/5 bg-white/[0.02] flex items-center justify-between">
                            <h3 className="text-xs font-black text-white uppercase tracking-widest">Tareas Pendientes</h3>
                            <span className="px-2 py-1 bg-rose-500/10 text-rose-500 text-[8px] font-black rounded uppercase">3 URGENTES</span>
                        </div>
                        <div className="divide-y divide-white/5">
                            {[
                                { item: 'Proyector Epson 4K', task: 'Limpieza de filtros y lentes', priority: 'Media', date: 'Mañana', icon: AlertCircle, color: 'text-amber-500' },
                                { item: 'Aire Acondicionado Auditorio', task: 'Recarga de gas refrigerante', priority: 'Alta', date: 'Hoy', icon: AlertCircle, color: 'text-rose-500' },
                                { item: 'Consola Behringer X32', task: 'Actualizacion de firmware', priority: 'Baja', date: 'Viernes', icon: Clock, color: 'text-blue-500' },
                            ].map((row, i) => (
                                <div key={i} className="p-6 hover:bg-white/[0.02] transition-all flex items-center justify-between group">
                                    <div className="flex items-center gap-4">
                                        <div className={`w-12 h-12 bg-white/5 rounded-xl flex items-center justify-center ${row.color}`}>
                                            <row.icon size={24} />
                                        </div>
                                        <div>
                                            <div className="text-sm font-bold text-white uppercase tracking-tight group-hover:text-amber-500 transition-colors">{row.item}</div>
                                            <div className="text-[10px] text-muted-foreground font-bold uppercase tracking-tighter">{row.task}</div>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-8">
                                        <div className="text-right">
                                            <div className="text-[10px] font-black text-white uppercase tracking-widest">{row.date}</div>
                                            <div className={`text-[8px] font-black uppercase ${row.priority === 'Alta' ? 'text-rose-500' : 'text-muted-foreground'}`}>{row.priority} PRIORIDAD</div>
                                        </div>
                                        <button className="p-2 bg-white/5 rounded-lg hover:bg-emerald-500 hover:text-black transition-all">
                                            <CheckCircle2 size={18} />
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="space-y-6">
                    <div className="bg-[#1e1f21] border border-white/5 p-8 rounded-[2.5rem] space-y-6">
                        <h3 className="text-xs font-black text-white uppercase tracking-widest flex items-center gap-2">
                            <Shield size={14} className="text-amber-500" /> Estado de Salud General
                        </h3>
                        <div className="flex items-center justify-center py-8">
                            <div className="relative w-32 h-32">
                                <svg className="w-full h-full" viewBox="0 0 36 36">
                                    <path className="text-white/5" stroke="currentColor" strokeWidth="3" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                                    <path className="text-amber-500" stroke="currentColor" strokeWidth="3" strokeDasharray="85, 100" strokeLinecap="round" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                                </svg>
                                <div className="absolute inset-0 flex flex-col items-center justify-center">
                                    <span className="text-2xl font-black text-white italic">85%</span>
                                    <span className="text-[8px] font-black text-muted-foreground uppercase">OPERATIVO</span>
                                </div>
                            </div>
                        </div>
                        <div className="space-y-3">
                            <div className="flex justify-between text-[10px] font-bold uppercase tracking-widest">
                                <span className="text-white/60">Equipos al dia</span>
                                <span className="text-emerald-500">105</span>
                            </div>
                            <div className="flex justify-between text-[10px] font-bold uppercase tracking-widest">
                                <span className="text-white/60">En revision</span>
                                <span className="text-amber-500">12</span>
                            </div>
                            <div className="flex justify-between text-[10px] font-bold uppercase tracking-widest">
                                <span className="text-white/60">Fuera de servicio</span>
                                <span className="text-rose-500">7</span>
                            </div>
                        </div>
                    </div>

                    <div className="bg-[#1e1f21] border border-white/5 p-8 rounded-[2.5rem] space-y-4">
                        <h3 className="text-xs font-black text-white uppercase tracking-widest">Historial</h3>
                        <p className="text-[11px] text-muted-foreground leading-relaxed">
                            Accede al registro historico de reparaciones y costos de mantenimiento por cada activo.
                        </p>
                        <button className="w-full py-3 bg-white/5 hover:bg-white/10 text-white text-[10px] font-black uppercase tracking-widest rounded-xl transition-all border border-white/5">
                            Descargar Log Completo
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
