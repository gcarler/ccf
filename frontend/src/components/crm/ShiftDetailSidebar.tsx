"use client";

import React from 'react';
import {
    X as CloseIcon,
    Calendar,
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
    'Alabanza': 'bg-[hsl(var(--primary))]',
    'Generación G': 'bg-[hsl(var(--primary))]',
    'Hospitalidad': 'bg-[hsl(var(--warning))]',
    'Oración': 'bg-[hsl(var(--primary))]',
    'Seguridad': 'bg-[hsl(var(--surface-2))]',
    'Media': 'bg-[hsl(var(--destructive))]'
};

interface ShiftDetailSidebarProps {
    shift: any;
    onClose?: () => void;
}

export default function ShiftDetailSidebar({ shift, onClose }: ShiftDetailSidebarProps) {
    const Icon = iconMap[shift.team_name] || Heart;
    const bgColor = colorMap[shift.team_name] || 'bg-[hsl(var(--primary))]';

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--surface-1))]">
            {/* Header */}
            <div className={clsx("p-4 shrink-0 relative overflow-hidden text-[hsl(var(--primary-foreground))] rounded-t-lg border-b border-[hsl(var(--border))]", bgColor)}>
                <div className="absolute top-0 right-0 p-4 opacity-10 pointer-events-none transform translate-x-1/4 -translate-y-1/4">
                    <Icon size={180} />
                </div>

                <div className="flex justify-between items-start mb-3 relative z-10">
                    <button
                        onClick={onClose}
                        className="p-2.5 bg-[hsl(var(--surface-1)/0.2)] hover:bg-[hsl(var(--surface-1)/0.3)] rounded-lg text-[hsl(var(--primary-foreground))] backdrop-blur-md transition-all active:scale-95 border border-[hsl(var(--border))]"
                        aria-label="Cerrar"
                    >
                        <CloseIcon size={20} />
                    </button>
                    <div className="flex gap-2">
                        <span className="px-4 py-1.5 bg-[hsl(var(--surface-1)/0.2)] backdrop-blur-md rounded-lg text-2xs font-bold uppercase tracking-wide border border-[hsl(var(--border))] text-[hsl(var(--primary-foreground))]">
                            {shift.status}
                        </span>
                    </div>
                </div>

                <div className="flex items-center gap-4 relative z-10">
                    <motion.div
                        whileHover={{ scale: 1.05 }}
                        className="size-10 rounded-lg bg-[hsl(var(--surface-1)/0.2)] flex items-center justify-center backdrop-blur-xl border-4 border-[hsl(var(--border))] shadow-2xl text-[hsl(var(--primary-foreground))]"
                    >
                        <Icon size={32} />
                    </motion.div>
                    <div className="flex-1 min-w-0">
                        <h2 className="text-lg font-bold uppercase tracking-[-0.04em] leading-[0.9] mb-1">
                            {shift.role_name}
                        </h2>
                        <p className="text-sm font-bold opacity-70 uppercase tracking-wide">{shift.team_name}</p>
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
                <section className="space-y-4">
                    <h3 className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide flex items-center gap-3">
                        <Calendar size={14} className="text-[hsl(var(--primary))]" /> Información Temporal
                    </h3>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="p-3 bg-[hsl(var(--surface-2))] rounded-md border border-[hsl(var(--border))] shadow-sm">
                            <p className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide mb-1.5 leading-none">Fecha de Turno</p>
                            <p className="text-xs font-bold text-[hsl(var(--text-primary))] uppercase tracking-tight">
                                {new Date(shift.shift_start).toLocaleDateString('es-ES', { day: '2-digit', month: 'short' })}
                            </p>
                        </div>
                        <div className="p-3 bg-[hsl(var(--surface-2))] rounded-md border border-[hsl(var(--border))] shadow-sm">
                            <p className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide mb-1.5 leading-none">Horario</p>
                            <p className="text-xs font-bold text-[hsl(var(--text-primary))] uppercase tracking-tight">{shift.time}</p>
                        </div>
                    </div>
                </section>

                <section className="space-y-4">
                    <h3 className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide flex items-center gap-3">
                        <MapPin size={14} className="text-[hsl(var(--primary))]" /> Ubicación
                    </h3>
                    <div className="p-4 bg-[hsl(var(--surface-2))] rounded-md relative overflow-hidden group border border-[hsl(var(--border))]">
                        <div className="absolute inset-0 opacity-20 pointer-events-none bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] to-[hsl(var(--primary)/0.2)] via-transparent to-transparent group-hover:scale-110 transition-transform duration-1000" />
                        <div className="relative z-10 flex items-center justify-between">
                            <div className="space-y-0.5">
                                <p className="text-sm font-bold text-[hsl(var(--text-primary))] uppercase tracking-tight">Auditorio Principal</p>
                                <p className="text-2xs font-bold text-[hsl(var(--primary))] uppercase tracking-wide">Campus Central CCF</p>
                            </div>
                            <div className="p-2.5 bg-[hsl(var(--primary)/0.1)] rounded-lg text-[hsl(var(--primary))] backdrop-blur-md">
                                <MapPin size={18} />
                            </div>
                        </div>
                    </div>
                </section>

                <section className="space-y-4">
                    <h3 className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide flex items-center gap-3">
                        <Users size={14} className="text-[hsl(var(--primary))]" /> Equipo Confirmado
                    </h3>
                    <div className="space-y-2.5">
                        {[1, 2, 3].map(i => (
                            <div key={i} className="flex items-center justify-between p-4 bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-md hover:bg-[hsl(var(--surface-2))] hover:border-[hsl(var(--primary)/0.4)] transition-all group">
                                <div className="flex items-center gap-4">
                                    <div className="size-8 rounded-lg bg-[hsl(var(--surface-2))] flex items-center justify-center text-xs font-bold text-[hsl(var(--text-secondary))] shadow-sm group-hover:scale-110 transition-transform">
                                        V{i}
                                    </div>
                                    <div>
                                        <p className="text-xs font-bold text-[hsl(var(--text-primary))] uppercase tracking-tight">Voluntario CCF {i}</p>
                                        <p className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Rol: {shift.role_name}</p>
                                    </div>
                                </div>
                                <div className="size-8 rounded-md bg-[hsl(var(--success))]/10 flex items-center justify-center text-[hsl(var(--success))]">
                                    <CheckCircle2 size={16} />
                                </div>
                            </div>
                        ))}
                    </div>
                </section>

                <div className="pt-4">
                    <button className="w-full py-2 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-md text-xs font-bold uppercase tracking-wide shadow-2xl shadow-[hsl(var(--primary)/0.2)] flex items-center justify-center gap-3 group transition-all hover:opacity-90 active:scale-95">
                        Registrar Asistencia <ChevronRight size={18} className="group-hover:translate-x-1.5 transition-all" />
                    </button>
                </div>
            </div>
        </div>
    );
}
