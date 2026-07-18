"use client";

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
    Mail, Phone, MapPin, BookOpen, Award,
    Edit2, Camera, Calendar, ShieldCheck, GraduationCap, Star
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';

export default function AcademyAccountPage() {
    const { token, user } = useAuth();
    const [enrollments, setEnrollments] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token) return;
        const ctrl = new AbortController();
        apiFetch<any[]>('/academy/courses', { token, signal: ctrl.signal })
            .then(data => setEnrollments(Array.isArray(data) ? data.slice(0, 5) : []))
            .catch(() => { setEnrollments([]); toast.error('Error al cargar inscripciones'); })
            .finally(() => setLoading(false));
        return () => ctrl.abort();
    }, [token]);

    const stats = [
        { icon: BookOpen, label: 'Cursos Activos', value: enrollments.length, color: 'text-[hsl(var(--primary))]', bg: 'bg-blue-50 dark:bg-blue-500/10' },
        { icon: Award, label: 'Certificados', value: 2, color: 'text-amber-600', bg: 'bg-amber-50 dark:bg-amber-500/10' },
        { icon: Star, label: 'Promedio', value: '9.4', color: 'text-sky-600', bg: 'bg-sky-50 dark:bg-sky-500/10' },
        { icon: Calendar, label: 'Dias Activo', value: 47, color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-500/10' },
    ];

    return (
        <div className="min-h-full bg-[hsl(var(--surface-1))] dark:bg-[#1E1F21]">
            {/* Hero Header */}
            <div className="bg-gradient-to-br from-blue-600 to-sky-700 relative overflow-hidden">
                <div className="absolute inset-0 opacity-10"
                    style={{ backgroundImage: "radial-gradient(circle at 70% 50%, white 0%, transparent 60%)" }} />
                <div className="max-w-4xl mx-auto px-3 py-1.5 relative">
                    <div className="flex items-end gap-4">
                        <div className="relative">
                            <div className="size-10 rounded-lg bg-white/20 backdrop-blur border-2 border-white/30 flex items-center justify-center text-white text-xl font-bold shadow-2xl">
                                {(user as any)?.name?.[0] ?? 'E'}
                            </div>
                            <button className="absolute -bottom-2 -right-2 size-8 rounded-lg bg-[hsl(var(--bg-primary))] text-[hsl(var(--primary))] flex items-center justify-center shadow-lg hover:scale-110 transition-all">
                                <Camera size={14} />
                            </button>
                        </div>
                        <div className="pb-1">
                            <div className="flex items-center gap-2 mb-1">
                                <span className="px-2 py-0.5 rounded-full bg-white/20 text-white text-[9px] font-semibold uppercase tracking-wide">
                                    Estudiante
                                </span>
                                <span className="px-2 py-0.5 rounded-full bg-amber-400/30 text-amber-200 text-[9px] font-semibold uppercase tracking-wide">
                                    Destacado
                                </span>
                            </div>
                            <h1 className="text-lg font-bold text-white tracking-tight">
                                {(user as any)?.name ?? 'Estudiante CCF'}
                            </h1>
                            <p className="text-blue-200 text-sm font-medium">
                                {(user as any)?.email ?? 'usuario@ccf.com'}
                            </p>
                        </div>
                        <div className="ml-auto pb-1">
                            <button className="flex items-center gap-2 px-3 py-1.5 bg-white/20 hover:bg-white/30 backdrop-blur border border-white/20 text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide transition-all">
                                <Edit2 size={14} /> Editar Perfil
                            </button>
                        </div>
                    </div>
                </div>
            </div>

 <div className="w-full px-3 py-1.5 space-y-3">
                {/* Stats */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {stats.map((s, i) => (
                        <motion.div
                            key={s.label}
                            initial={{ opacity: 0, y: 12 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.05 }}
                            className="bg-[hsl(var(--bg-primary))] dark:bg-[#1a1d27] rounded-lg border border-[hsl(var(--border))]/60 dark:border-white/5 p-3 shadow-sm"
                        >
                            <div className={`size-8 rounded-lg ${s.bg} flex items-center justify-center mb-3`}>
                                <s.icon size={18} className={s.color} />
                            </div>
                            <p className={`text-lg font-bold ${s.color}`}>{s.value}</p>
                            <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide mt-0.5">{s.label}</p>
                        </motion.div>
                    ))}
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
                    {/* Personal Info */}
                    <motion.div
                        initial={{ opacity: 0, y: 12 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 }}
                        className="col-span-1 bg-[hsl(var(--bg-primary))] dark:bg-[#1a1d27] rounded-lg border border-[hsl(var(--border))]/60 dark:border-white/5 p-3 shadow-sm space-y-4"
                    >
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Informacion Personal</p>
                        {[
                            { icon: Mail, label: 'Email', value: (user as any)?.email ?? '—' },
                            { icon: Phone, label: 'Telefono', value: '+57 300 000 0000' },
                            { icon: MapPin, label: 'Ciudad', value: 'Mocoa, Putumayo' },
                            { icon: ShieldCheck, label: 'Rol', value: 'Persona Activo' },
                        ].map(row => (
                            <div key={row.label} className="flex items-start gap-3">
                                <div className="size-8 rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))] shrink-0">
                                    <row.icon size={14} />
                                </div>
                                <div>
                                    <p className="text-[9px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">{row.label}</p>
                                    <p className="text-[12px] font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] truncate">{row.value}</p>
                                </div>
                            </div>
                        ))}
                    </motion.div>

                    {/* Enrolled Courses */}
                    <motion.div
                        initial={{ opacity: 0, y: 12 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.25 }}
                        className="col-span-2 bg-[hsl(var(--bg-primary))] dark:bg-[#1a1d27] rounded-lg border border-[hsl(var(--border))]/60 dark:border-white/5 p-3 shadow-sm"
                    >
                        <div className="flex items-center justify-between mb-4">
                            <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Mis Cursos</p>
                            <GraduationCap size={16} className="text-[hsl(var(--text-secondary))]" />
                        </div>
                        {loading ? (
                            <div className="space-y-3">
                                {[1, 2, 3].map(i => (
                                    <div key={i} className="h-8 bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-lg animate-pulse" />
                                ))}
                            </div>
                        ) : enrollments.length === 0 ? (
                            <div className="py-1.5 text-center">
                                <BookOpen size={32} className="mx-auto text-[hsl(var(--text-secondary))] mb-3" />
                                <p className="text-sm font-bold text-[hsl(var(--text-secondary))]">Sin cursos inscritos aun</p>
                                <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">Explora el catalogo de cursos disponible</p>
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {enrollments.map((course: any, i) => (
                                    <div key={i} className="flex items-center gap-3 p-3 rounded-lg hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-all">
                                        <div className="size-8 rounded-lg bg-gradient-to-br from-blue-500 to-sky-600 flex items-center justify-center text-white text-sm font-semibold shrink-0">
                                            {course.title?.[0] ?? 'C'}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-[12px] font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] truncate">{course.title ?? `Curso ${i + 1}`}</p>
                                            <div className="w-full bg-[hsl(var(--surface-2))] dark:bg-white/10 rounded-full h-1.5 mt-1.5">
                                                <div className="bg-[hsl(var(--primary))] h-1.5 rounded-full" style={{ width: `${30 + i * 15}%` }} />
                                            </div>
                                        </div>
                                        <span className="font-semibold text-[hsl(var(--text-secondary))]">{30 + i * 15}%</span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </motion.div>
                </div>
            </div>
        </div>
    );
}
