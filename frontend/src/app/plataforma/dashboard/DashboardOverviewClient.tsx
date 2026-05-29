"use client";

import React from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
    Users, BookOpen, Home, PiggyBank, Calendar, FileText,
    FolderKanban, Shield, ArrowRight, LayoutDashboard,
    LucideIcon,
} from 'lucide-react';
import { DSCard } from '@/design/components/DSCard';
import { MODULE_CONFIG } from '@/components/DashboardShell';

const MODULES = [
    { key: 'crm', icon: Users, desc: 'Personas, casos, pipelines, SLAs e interacciones' },
    { key: 'academy', icon: BookOpen, desc: 'Cursos, matrículas, progreso, evaluaciones y certificaciones' },
    { key: 'evangelism', icon: Home, desc: 'Grupos, asistencia, embudo, geografía y seguimientos' },
    { key: 'finance', icon: PiggyBank, desc: 'Donaciones, ingresos por categoría, tendencias mensuales' },
    { key: 'agenda', icon: Calendar, desc: 'Eventos, recursos, participación y reservas' },
    { key: 'cms', icon: FileText, desc: 'Páginas, versiones, publicaciones y contenido' },
    { key: 'projects', icon: FolderKanban, desc: 'Proyectos, tareas, carga de trabajo, hitos' },
    { key: 'admin', icon: Shield, desc: 'Usuarios, sesiones, roles y salud del sistema' },
];

export default function DashboardOverviewClient() {
    return (
        <div className="flex flex-col h-full bg-slate-50 dark:bg-transparent overflow-y-auto p-4 font-sans">
            <div className="mb-6">
                <div className="flex items-center gap-3 mb-1">
                    <div className="size-10 rounded-xl bg-indigo-50 dark:bg-indigo-500/10 flex items-center justify-center">
                        <LayoutDashboard size={20} className="text-indigo-600 dark:text-indigo-400" />
                    </div>
                    <div>
                        <h1 className="text-lg font-bold text-slate-800 dark:text-white tracking-tight">
                            Centro de Dashboards
                        </h1>
                        <p className="text-xs text-slate-500">
                            Métricas en vivo para cada módulo de la plataforma
                        </p>
                    </div>
                </div>
            </div>

            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
            >
                {MODULES.map((mod, i) => {
                    const cfg = MODULE_CONFIG[mod.key];
                    const Icon = mod.icon;
                    return (
                        <motion.div
                            key={mod.key}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.05 }}
                        >
                            <Link href={`/plataforma/dashboard/${mod.key}`} className="block group">
                                <DSCard padding="md" className="hover:shadow-md hover:-translate-y-0.5 transition-all duration-200">
                                    <div className="flex items-start gap-3">
                                        <div
                                            className="size-10 rounded-lg flex items-center justify-center shrink-0"
                                            style={{ backgroundColor: `${cfg?.color || '#6366f1'}15` }}
                                        >
                                            <Icon
                                                size={18}
                                                style={{ color: cfg?.color || '#6366f1' }}
                                            />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <h3 className="text-[13px] font-bold text-slate-800 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                                                {cfg?.label || mod.key}
                                            </h3>
                                            <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">
                                                {mod.desc}
                                            </p>
                                        </div>
                                        <ArrowRight size={14} className="text-slate-300 group-hover:text-indigo-500 transition-colors shrink-0 mt-1" />
                                    </div>
                                </DSCard>
                            </Link>
                        </motion.div>
                    );
                })}
            </motion.div>
        </div>
    );
}
