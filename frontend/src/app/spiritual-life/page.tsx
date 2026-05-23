"use client";

import React, { useState, useEffect } from 'react';
import {
    Heart, Zap, Waves, Star, Shield, Award, ChevronRight,
    Calendar, BookOpen, TrendingUp, Users,
    Sparkles, CheckCircle2, Circle, Lock
} from 'lucide-react';
import { motion } from 'framer-motion';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import Link from 'next/link';
import clsx from 'clsx';

// ── Types
interface AcademyProgress {
    completed_courses: number;
    total_courses: number;
    level: string;
}

// ── Milestone definitions
const MILESTONE_DEFS = [
    { key: 'Decision_Fe',      label: 'Decisión de Fe',         icon: Zap,    color: 'text-amber-500',  bg: 'bg-amber-50 dark:bg-amber-900/20',  border: 'border-amber-200 dark:border-amber-500/20' },
    { key: 'Bautismo_Aguas',   label: 'Bautismo en Aguas',      icon: Waves,  color: 'text-cyan-600',   bg: 'bg-cyan-50 dark:bg-cyan-900/20',    border: 'border-cyan-200 dark:border-cyan-500/20' },
    { key: 'Bautismo_Espiritu',label: 'Bautismo del Espíritu',  icon: Star,   color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-900/20',border: 'border-blue-200 dark:border-blue-500/20' },
    { key: 'Miembro_Oficial',  label: 'Membresía Oficial',      icon: Shield, color: 'text-emerald-600',bg: 'bg-emerald-50 dark:bg-emerald-900/20',border: 'border-emerald-200 dark:border-emerald-500/20' },
    { key: 'Liderazgo',        label: 'Llamado al Liderazgo',   icon: Users,  color: 'text-blue-600',   bg: 'bg-blue-50 dark:bg-blue-900/20',    border: 'border-blue-200 dark:border-blue-500/20' },
];

// ── Discipleship steps
const DISCIPULADO_STEPS = [
    { id: 1, label: 'Descubriendo a Jesús',     desc: 'Las bases del evangelio y la salvación', done: true  },
    { id: 2, label: 'Vida Nueva',               desc: 'Fundamentos de la vida cristiana',        done: true  },
    { id: 3, label: 'Creciendo en Cristo',       desc: 'Hábitos espirituales y comunidad',        done: false },
    { id: 4, label: 'Sirviendo con Propósito',  desc: 'Identificación y activación de dones',     done: false },
    { id: 5, label: 'Multiplicando Vidas',      desc: 'Discipulado y reproducción ministerial',   done: false },
];

export default function SpiritualLifePage() {
    const { token } = useAuth();
    const [milestones, setMilestones] = useState<string[]>([]);
    const [academyProgress, setAcademyProgress] = useState<AcademyProgress | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const load = async () => {
            if (!token) return;
            try {
                // Try to get milestones from user profile
                const profile = await apiFetch<any>('/academy/me/profile', { token }).catch(() => null);
                if (profile?.spiritual_milestones) {
                    setMilestones(profile.spiritual_milestones);
                } else {
                    // Fallback demo data
                    setMilestones(['Decision_Fe', 'Bautismo_Aguas']);
                }

                // Try to get academy progress
                const courses = await apiFetch<any>('/academy/enrollments', { token }).catch(() => null);
                if (courses) {
                    const completed = Array.isArray(courses) ? courses.filter((c: any) => c.completed).length : 0;
                    const total = Array.isArray(courses) ? courses.length : 0;
                    setAcademyProgress({ completed_courses: completed, total_courses: total, level: 'Fundamentos' });
                } else {
                    setAcademyProgress({ completed_courses: 2, total_courses: 5, level: 'Fundamentos' });
                }
            } finally {
            }
        };
        load();
    }, [token]);

    const nextMilestone = MILESTONE_DEFS.find(m => !milestones.includes(m.key));
    const progressPct = Math.round((milestones.length / MILESTONE_DEFS.length) * 100);
    const discipuladoDone = DISCIPULADO_STEPS.filter(s => s.done).length;

    const sidebarSections = [
        {
            title: 'Mi Caminar',
            items: [
                { id: 'spiritual-home',  label: 'Panel Espiritual',  href: '/spiritual-life',              icon: Heart },
                { id: 'spiritual-tl',    label: 'Línea de Tiempo',   href: '/spiritual-life/timeline',     icon: Calendar },
                { id: 'spiritual-certs', label: 'Mis Certificados',  href: '/spiritual-life/certificates', icon: Award },
            ]
        },
        {
            title: 'Formación',
            items: [
                { id: 'academy-link',    label: 'Academia CCF',      href: '/academy',                     icon: BookOpen },
            ]
        }
    ];
    void loading;
    void setLoading;
    void sidebarSections;

    return (
        <div className="flex flex-col h-full bg-slate-50 dark:bg-[#111213] overflow-y-auto font-display">
                <div className="max-w-6xl mx-auto w-full p-4 space-y-3 pb-4">

                    {/* ── HERO HEADER ─────────────────────────────────────────────── */}
                    <div className="flex items-start justify-between">
                        <div>
                            <div className="flex items-center gap-2 mb-2">
                                <div className="size-8 rounded-md bg-rose-100 dark:bg-rose-900/30 flex items-center justify-center">
                                    <Heart size={16} className="text-rose-600" fill="currentColor" />
                                </div>
                                <span className="text-[10px] font-semibold uppercase tracking-wide text-rose-600">Vida Espiritual</span>
                            </div>
                            <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white leading-none">
                                Tu Caminar con Cristo
                            </h1>
                            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 font-medium">
                                Registra y celebra cada hito de tu vida espiritual en CCF.
                            </p>
                        </div>

                        <Link href="/spiritual-life/timeline">
                            <motion.button
                                whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                                className="flex items-center gap-2 px-3 py-2.5 bg-blue-600 text-white rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/25"
                            >
                                <Calendar size={14} /> Ver Línea de Tiempo
                            </motion.button>
                        </Link>
                    </div>

                    {/* ── KPI CARDS ──────────────────────────────────────────────── */}
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                        {[
                            { label: 'Hitos Espirituales', value: `${milestones.length}/${MILESTONE_DEFS.length}`, icon: Zap, color: 'text-amber-600', bg: 'bg-amber-50 dark:bg-amber-900/20' },
                            { label: 'Progreso Espiritual', value: `${progressPct}%`, icon: TrendingUp, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-900/20' },
                            { label: 'Cursos en Academia', value: `${academyProgress?.completed_courses ?? '–'}/${academyProgress?.total_courses ?? '–'}`, icon: BookOpen, color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-900/20' },
                            { label: 'Nivel de Discipulado', value: `${discipuladoDone}/5`, icon: Star, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-900/20' },
                        ].map((kpi, i) => (
                            <motion.div key={i}
                                initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07 }}
                                className="bg-white dark:bg-[#1a1b1e] border border-slate-200 dark:border-white/7 rounded-lg p-3 shadow-sm hover:shadow-md transition-all"
                            >
                                <div className={clsx("size-9 rounded-md flex items-center justify-center mb-3", kpi.bg)}>
                                    <kpi.icon size={17} className={kpi.color} />
                                </div>
                                <div className="text-lg font-bold text-slate-900 dark:text-white tracking-tight">{kpi.value}</div>
                                <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mt-0.5">{kpi.label}</div>
                            </motion.div>
                        ))}
                    </div>

                    {/* ── MAIN GRID ──────────────────────────────────────────────── */}
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">

                        {/* Left: Milestones journey ── */}
                        <div className="lg:col-span-2 space-y-4">
                            <div className="flex items-center justify-between mb-1">
                                <h2 className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Hitos Espirituales</h2>
                                <span className="text-[10px] font-bold text-blue-600 bg-blue-50 dark:bg-blue-900/20 px-2 py-0.5 rounded-full">
                                    {milestones.length} alcanzados
                                </span>
                            </div>

                            <div className="bg-white dark:bg-[#1a1b1e] border border-slate-200 dark:border-white/7 rounded-lg overflow-hidden shadow-sm">
                                {MILESTONE_DEFS.map((m, i) => {
                                    const reached = milestones.includes(m.key);
                                    const isNext = !reached && m.key === nextMilestone?.key;
                                    return (
                                        <motion.div key={m.key}
                                            initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.06 }}
                                            className={clsx(
                                                "flex items-center gap-4 px-3 py-1.5 border-b border-slate-100 dark:border-white/5 last:border-0 transition-all",
                                                reached ? "opacity-100" : isNext ? "opacity-90" : "opacity-40"
                                            )}
                                        >
                                            {/* Icon */}
                                            <div className={clsx("size-10 rounded-md flex items-center justify-center border shrink-0", m.bg, m.border)}>
                                                <m.icon size={18} className={m.color} />
                                            </div>

                                            {/* Text */}
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2">
                                                    <p className="text-[13px] font-bold text-slate-800 dark:text-white truncate">{m.label}</p>
                                                    {isNext && (
                                                        <span className="px-2 py-0.5 bg-blue-50 dark:bg-blue-900/30 text-blue-600 text-[9px] font-semibold uppercase tracking-wide rounded-full">
                                                            Siguiente
                                                        </span>
                                                    )}
                                                </div>
                                            </div>

                                            {/* Status */}
                                            {reached ? (
                                                <CheckCircle2 size={18} className="text-emerald-500 shrink-0" />
                                            ) : isNext ? (
                                                <Circle size={18} className="text-blue-400 shrink-0 animate-pulse" />
                                            ) : (
                                                <Lock size={15} className="text-slate-300 dark:text-slate-600 shrink-0" />
                                            )}
                                        </motion.div>
                                    );
                                })}
                            </div>

                            {/* Spiritual progress bar */}
                            <div className="bg-white dark:bg-[#1a1b1e] border border-slate-200 dark:border-white/7 rounded-lg p-3 shadow-sm">
                                <div className="flex items-center justify-between mb-3">
                                    <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Progreso espiritual</span>
                                    <span className="font-semibold text-blue-600">{progressPct}%</span>
                                </div>
                                <div className="h-2.5 bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
                                    <motion.div
                                        className="h-full bg-gradient-to-r from-blue-500 to-blue-600 rounded-full"
                                        initial={{ width: 0 }}
                                        animate={{ width: `${progressPct}%` }}
                                        transition={{ duration: 1.2, ease: 'easeOut' }}
                                    />
                                </div>
                                <p className="text-[11px] text-slate-400 mt-2">
                                    {nextMilestone
                                        ? `Próximo hito: ${nextMilestone.label}`
                                        : '¡Has completado todos los hitos! 🎉'
                                    }
                                </p>
                            </div>
                        </div>

                        {/* Right column ── */}
                        <div className="space-y-4">

                            {/* Discipleship path */}
                            <div className="bg-white dark:bg-[#1a1b1e] border border-slate-200 dark:border-white/7 rounded-lg overflow-hidden shadow-sm">
                                <div className="px-3 py-1.5 border-b border-slate-100 dark:border-white/5 flex items-center justify-between">
                                    <h3 className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Ruta de Discipulado</h3>
                                    <span className="font-semibold text-slate-400">{discipuladoDone}/5</span>
                                </div>
                                <div className="divide-y divide-slate-100 dark:divide-white/5">
                                    {DISCIPULADO_STEPS.map(step => (
                                        <div key={step.id} className={clsx(
                                            "flex items-start gap-3 px-3 py-3 transition-all",
                                            !step.done && "opacity-50"
                                        )}>
                                            <div className={clsx(
                                                "size-5 rounded-full shrink-0 flex items-center justify-center mt-0.5",
                                                step.done
                                                    ? "bg-emerald-100 dark:bg-emerald-900/30"
                                                    : "bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10"
                                            )}>
                                                {step.done
                                                    ? <CheckCircle2 size={12} className="text-emerald-600" />
                                                    : <span className="font-semibold text-slate-400">{step.id}</span>
                                                }
                                            </div>
                                            <div>
                                                <p className="text-[12px] font-bold text-slate-700 dark:text-slate-200">{step.label}</p>
                                                <p className="text-[10px] text-slate-400 leading-snug">{step.desc}</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Quick links */}
                            <div className="space-y-2">
                                <Link href="/spiritual-life/timeline">
                                    <div className="flex items-center gap-3 p-4 bg-white dark:bg-[#1a1b1e] border border-slate-200 dark:border-white/7 rounded-lg shadow-sm hover:shadow-md hover:border-blue-200 dark:hover:border-white/15 transition-all cursor-pointer group">
                                        <div className="size-9 rounded-md bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center">
                                            <Calendar size={16} className="text-blue-600" />
                                        </div>
                                        <div className="flex-1">
                                            <p className="text-[13px] font-bold text-slate-800 dark:text-white">Línea de Tiempo</p>
                                            <p className="text-[10px] text-slate-400">Todos tus hitos cronológicos</p>
                                        </div>
                                        <ChevronRight size={14} className="text-slate-300 group-hover:translate-x-1 transition-transform" />
                                    </div>
                                </Link>

                                <Link href="/spiritual-life/certificates">
                                    <div className="flex items-center gap-3 p-4 bg-white dark:bg-[#1a1b1e] border border-slate-200 dark:border-white/7 rounded-lg shadow-sm hover:shadow-md hover:border-blue-200 dark:hover:border-white/15 transition-all cursor-pointer group">
                                        <div className="size-9 rounded-md bg-cyan-50 dark:bg-cyan-900/20 flex items-center justify-center">
                                            <Award size={16} className="text-cyan-600" />
                                        </div>
                                        <div className="flex-1">
                                            <p className="text-[13px] font-bold text-slate-800 dark:text-white">Mis Certificados</p>
                                            <p className="text-[10px] text-slate-400">Descarga tus actas y diplomas</p>
                                        </div>
                                        <ChevronRight size={14} className="text-slate-300 group-hover:translate-x-1 transition-transform" />
                                    </div>
                                </Link>

                                <Link href="/academy">
                                    <div className="flex items-center gap-3 p-4 bg-gradient-to-r from-blue-600 to-blue-600 rounded-lg shadow-lg shadow-blue-500/20 hover:shadow-blue-500/30 transition-all cursor-pointer group">
                                        <div className="size-9 rounded-md bg-white/20 flex items-center justify-center">
                                            <Sparkles size={16} className="text-white" />
                                        </div>
                                        <div className="flex-1">
                                            <p className="text-[13px] font-bold text-white">Academia CCF</p>
                                            <p className="text-[10px] text-white/70">Continúa tu formación ministerial</p>
                                        </div>
                                        <ChevronRight size={14} className="text-white/60 group-hover:translate-x-1 transition-transform" />
                                    </div>
                                </Link>
                            </div>
                        </div>
                    </div>
                </div>
        </div>
    );
}

