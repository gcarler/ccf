"use client";

import React, { useState } from 'react';
import {
    Bot, Bell, Clock, ShieldAlert, ToggleLeft, ToggleRight,
    ArrowRight, Sparkles, Plus
} from 'lucide-react';
import { motion } from 'framer-motion';
import clsx from 'clsx';

const INITIAL_RULES = [
    { id: 1, name: 'Alerta de Sobrecarga',        trigger: 'Carga > 8 tareas activas',   active: true,  icon: ShieldAlert, color: 'text-rose-500',  bg: 'bg-rose-50 dark:bg-rose-900/20' },
    { id: 2, name: 'Recordatorio 24h',              trigger: 'Tarea cerca de su deadline',  active: true,  icon: Bell,        color: 'text-blue-500', bg: 'bg-blue-50 dark:bg-blue-900/20' },
    { id: 3, name: 'Detector de Estancamiento',     trigger: 'Sin cambios por 3 días',      active: false, icon: Clock,       color: 'text-amber-500',bg: 'bg-amber-50 dark:bg-amber-900/20'},
    { id: 4, name: 'Resumen Semanal MESH',          trigger: 'Cada lunes a las 08:00 AM',   active: true,  icon: Bot,         color: 'text-blue-500',bg: 'bg-blue-50 dark:bg-blue-900/20'},
];

export default function AutomationsPage() {
    const [rules, setRules] = useState(INITIAL_RULES);

    const toggleRule = (id: number) => {
        setRules(prev => prev.map(r => r.id === id ? { ...r, active: !r.active } : r));
    };

    return (
        <div className="flex flex-col h-full bg-slate-50 dark:bg-[#0f1012] overflow-y-auto font-display">
            <div className="w-full mx-auto p-3 space-y-3 pb-4">

                {/* Sub-header */}
                <div className="flex items-center justify-between">
                    <div>
                        <div className="flex items-center gap-2 mb-1">
                            <div className="size-7 rounded-lg bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center">
                                <Sparkles size={14} className="text-blue-600" />
                            </div>
                            <span className="text-[10px] font-semibold uppercase tracking-wide text-blue-600">Motor Optimus 3.0</span>
                        </div>
                        <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white leading-none">
                            Automatizaciones
                        </h1>
                        <p className="text-[12px] text-slate-500 dark:text-slate-400 mt-0.5 font-medium">
                            Configura cómo el sistema reacciona a los desafíos de tu ministerio.
                        </p>
                    </div>
                    <button className="flex items-center gap-2 px-4 py-1.5 bg-blue-600 text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all">
                        <Plus size={13} /> Nueva Regla
                    </button>
                </div>

                {/* Active count */}
                <div className="flex items-center gap-3">
                    <span className="px-2.5 py-1 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 rounded-full text-[10px] font-semibold uppercase tracking-wide border border-emerald-200 dark:border-emerald-500/20">
                        {rules.filter(r => r.active).length} activas
                    </span>
                    <span className="px-2.5 py-1 bg-slate-100 dark:bg-white/5 text-slate-400 rounded-full text-[10px] font-semibold uppercase tracking-wide border border-slate-200 dark:border-white/10">
                        {rules.filter(r => !r.active).length} inactivas
                    </span>
                </div>

                {/* Rules Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {rules.map((rule, idx) => {
                        const Icon = rule.icon;
                        return (
                            <motion.div
                                key={rule.id}
                                initial={{ opacity: 0, y: 16 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: idx * 0.07 }}
                                className={clsx(
                                    "group p-3 rounded-lg border transition-all",
                                    rule.active
                                        ? "bg-white dark:bg-[#1a1b1e] border-slate-200 dark:border-white/[0.06] shadow-sm hover:shadow-lg hover:border-blue-200 dark:hover:border-blue-500/20"
                                        : "bg-slate-50 dark:bg-white/[0.02] border-slate-200 dark:border-white/[0.04] opacity-60"
                                )}
                            >
                                <div className="flex items-start justify-between mb-4">
                                    <div className={clsx("size-10 rounded-md flex items-center justify-center border shrink-0", rule.bg,
                                        rule.color.replace('text-', 'border-').replace('500', '200') + ' dark:border-opacity-20'
                                    )}>
                                        <Icon size={18} className={rule.color} />
                                    </div>
                                    <button
                                        onClick={() => toggleRule(rule.id)}
                                        className="transition-transform active:scale-90 shrink-0"
                                        aria-label={rule.active ? 'Desactivar regla' : 'Activar regla'}
                                    >
                                        {rule.active
                                            ? <ToggleRight size={32} className="text-blue-600" />
                                            : <ToggleLeft size={32} className="text-slate-300 dark:text-slate-600" />
                                        }
                                    </button>
                                </div>

                                <div className="space-y-1 mb-4">
                                    <h3 className="text-sm font-bold text-slate-900 dark:text-white leading-tight">{rule.name}</h3>
                                    <p className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">{rule.trigger}</p>
                                </div>

                                <div className="pt-3 border-t border-slate-100 dark:border-white/5 flex items-center justify-between">
                                    <button className="text-[10px] font-semibold uppercase text-blue-600 tracking-wide flex items-center gap-1.5 hover:underline">
                                        Configurar lógica <ArrowRight size={11} />
                                    </button>
                                    {!rule.active && (
                                        <span className="px-2 py-0.5 bg-slate-100 dark:bg-white/5 text-slate-400 rounded-md text-[9px] font-semibold uppercase tracking-wide">
                                            Inactivo
                                        </span>
                                    )}
                                </div>
                            </motion.div>
                        );
                    })}

                    {/* Add new rule card */}
                    <motion.div
                        initial={{ opacity: 0, y: 16 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: rules.length * 0.07 }}
                        className="flex flex-col items-center justify-center p-3 rounded-lg border-2 border-dashed border-slate-200 dark:border-white/10 text-center gap-2 group cursor-pointer hover:border-blue-400 dark:hover:border-blue-500/40 hover:bg-blue-50/50 dark:hover:bg-blue-900/10 transition-all min-h-[100px]"
                    >
                        <div className="size-10 rounded-md bg-white dark:bg-white/5 shadow-sm border border-slate-200 dark:border-white/10 flex items-center justify-center text-slate-400 group-hover:text-blue-600 group-hover:border-blue-200 dark:group-hover:border-blue-500/30 transition-all">
                            <Plus size={18} />
                        </div>
                        <div>
                            <h4 className="text-[13px] font-bold text-slate-700 dark:text-slate-300 group-hover:text-blue-600 transition-colors">Crear Regla</h4>
                            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide mt-0.5">Expandir Inteligencia</p>
                        </div>
                    </motion.div>
                </div>
            </div>
        </div>
    );
}

