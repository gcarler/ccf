"use client";

import React from 'react';
import { 
    X as CloseIcon, 
    Calendar, 
    Clock, 
    Music, 
    Baby, 
    Coffee, 
    Zap, 
    Shield, 
    Camera, 
    Heart,
    CheckCircle2,
    MapPin,
    Users,
    ChevronRight
} from 'lucide-react';
import { motion } from 'framer-motion';
import clsx from 'clsx';

const iconMap: Record<string, any> = {
    'Alabanza': Music,
    'Generación G': Baby,
    'Niños': Baby,
    'Hospitalidad': Coffee,
    'Ujieres': Coffee,
    'Oración': Zap,
    'Seguridad': Shield,
    'Media': Camera,
};

const colorMap: Record<string, string> = {
    'Alabanza': 'bg-blue-600',
    'Generación G': 'bg-purple-600',
    'Hospitalidad': 'bg-amber-500',
    'Oración': 'bg-indigo-600',
    'Seguridad': 'bg-slate-800',
    'Media': 'bg-rose-600'
};

interface ShiftDetailSidebarProps {
    shift: any;
    onClose?: () => void;
}

export default function ShiftDetailSidebar({ shift, onClose }: ShiftDetailSidebarProps) {
    const Icon = iconMap[shift.team_name] || Heart;
    const bgColor = colorMap[shift.team_name] || 'bg-blue-600';

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#0f1113]">
            {/* Header */}
            <div className={clsx("p-8 shrink-0 relative overflow-hidden text-white rounded-t-[2.5rem] border-b border-white/[0.04]", bgColor)}>
                <div className="absolute top-0 right-0 p-12 opacity-10 pointer-events-none transform translate-x-1/4 -translate-y-1/4">
                    <Icon size={180} />
                </div>
                
                <div className="flex justify-between items-start mb-10 relative z-10">
                    <button 
                        onClick={onClose} 
                        className="p-2.5 bg-white/20 hover:bg-white/30 rounded-2xl text-white backdrop-blur-md transition-all active:scale-95 border border-white/10"
                    >
                        <CloseIcon size={20} />
                    </button>
                    <div className="flex gap-2">
                        <span className="px-4 py-1.5 bg-white/20 backdrop-blur-md rounded-2xl text-[10px] font-black uppercase tracking-[0.2em] border border-white/10">
                            {shift.status}
                        </span>
                    </div>
                </div>

                <div className="flex items-center gap-6 relative z-10">
                    <motion.div 
                        whileHover={{ scale: 1.05 }}
                        className="size-20 rounded-[2.2rem] bg-white/20 flex items-center justify-center backdrop-blur-xl border-4 border-white/20 shadow-2xl"
                    >
                        <Icon size={32} />
                    </motion.div>
                    <div className="flex-1 min-w-0">
                        <h2 className="text-2xl font-black uppercase tracking-[-0.04em] leading-[0.9] mb-1">
                            {shift.role_name}
                        </h2>
                        <p className="text-[12px] font-black opacity-70 uppercase tracking-[0.2em]">{shift.team_name}</p>
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-8 space-y-8 custom-scrollbar">
                <section className="space-y-4">
                    <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-3">
                        <Calendar size={14} className="text-blue-600 dark:text-blue-400" /> Información Temporal
                    </h3>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="p-5 bg-slate-50 dark:bg-white/[0.03] rounded-[2rem] border border-slate-100 dark:border-white/[0.05] shadow-sm">
                            <p className="text-[8px] font-black text-slate-400 uppercase tracking-[0.2em] mb-1.5 leading-none">Fecha de Turno</p>
                            <p className="text-[11px] font-black text-slate-900 dark:text-slate-100 uppercase tracking-tight">
                                {new Date(shift.shift_start).toLocaleDateString('es-ES', { day: '2-digit', month: 'short' })}
                            </p>
                        </div>
                        <div className="p-5 bg-slate-50 dark:bg-white/[0.03] rounded-[2rem] border border-slate-100 dark:border-white/[0.05] shadow-sm">
                            <p className="text-[8px] font-black text-slate-400 uppercase tracking-[0.2em] mb-1.5 leading-none">Horario</p>
                            <p className="text-[11px] font-black text-slate-900 dark:text-slate-100 uppercase tracking-tight">{shift.time}</p>
                        </div>
                    </div>
                </section>

                <section className="space-y-4">
                    <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-3">
                        <MapPin size={14} className="text-blue-600 dark:text-blue-400" /> Ubicación
                    </h3>
                    <div className="p-6 bg-slate-900 dark:bg-white/[0.03] rounded-[2.5rem] relative overflow-hidden group">
                        <div className="absolute inset-0 opacity-20 pointer-events-none bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-blue-500/20 via-transparent to-transparent group-hover:scale-110 transition-transform duration-1000" />
                        <div className="relative z-10 flex items-center justify-between">
                            <div className="space-y-0.5">
                                <p className="text-sm font-black text-white uppercase tracking-tight">Auditorio Principal</p>
                                <p className="text-[10px] font-bold text-blue-400 uppercase tracking-widest">Campus Central CCF</p>
                            </div>
                            <div className="p-2.5 bg-white/10 rounded-2xl text-blue-400 backdrop-blur-md">
                                <MapPin size={18} />
                            </div>
                        </div>
                    </div>
                </section>

                <section className="space-y-4">
                    <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-3">
                        <Users size={14} className="text-blue-600 dark:text-blue-400" /> Equipo Confirmado
                    </h3>
                    <div className="space-y-2.5">
                        {[1, 2, 3].map(i => (
                            <div key={i} className="flex items-center justify-between p-4 bg-white dark:bg-white/[0.02] border border-slate-100 dark:border-white/[0.05] rounded-[2rem] hover:bg-slate-50 dark:hover:bg-white/[0.05] hover:border-blue-500/20 transition-all group">
                                <div className="flex items-center gap-4">
                                    <div className="size-10 rounded-2xl bg-gradient-to-tr from-slate-100 to-slate-200 dark:from-white/5 dark:to-white/10 flex items-center justify-center text-[11px] font-black text-slate-500 shadow-sm group-hover:scale-110 transition-transform">
                                        V{i}
                                    </div>
                                    <div>
                                        <p className="text-xs font-black text-slate-800 dark:text-slate-200 uppercase tracking-tight">Voluntario CCF {i}</p>
                                        <p className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">Rol: {shift.role_name}</p>
                                    </div>
                                </div>
                                <div className="size-8 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-500">
                                    <CheckCircle2 size={16} />
                                </div>
                            </div>
                        ))}
                    </div>
                </section>

                <div className="pt-4">
                    <button className="w-full py-5 bg-slate-900 dark:bg-blue-600 text-white rounded-[2.5rem] text-[11px] font-black uppercase tracking-[0.2em] shadow-2xl shadow-blue-500/25 flex items-center justify-center gap-3 group transition-all active:scale-95">
                        Registrar Asistencia <ChevronRight size={18} className="group-hover:translate-x-1.5 transition-all" />
                    </button>
                </div>
            </div>
        </div>
    );
}
