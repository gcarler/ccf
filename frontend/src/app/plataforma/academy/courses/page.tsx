"use client";

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import {
    GraduationCap,
    BookOpen,
    Search,
    PlayCircle,
    Settings,
    Clock,
    Sparkles,
    ShieldCheck
} from 'lucide-react';
import { toast } from 'sonner';

interface CourseItem {
    id: string;
    code?: string;
    slug?: string;
    title: string;
    description?: string;
    modality?: string;
    duration_hours?: number;
    lesson_count?: number;
    lessons?: Array<{ id: string; title: string }>;
    is_published?: boolean;
    instructor_name?: string;
    tag?: string;
}

export default function AcademyCoursesPage() {
    const router = useRouter();
    const { token, hasModuleAccess } = useAuth();

    const [courses, setCourses] = useState<CourseItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedModality, setSelectedModality] = useState<string>('all');

    const loadCourses = useCallback(async (signal?: AbortSignal) => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch<CourseItem[]>('/academy/courses', {
                token,
                signal,
                cache: 'no-store' as RequestCache
            });
            setCourses(Array.isArray(data) ? data : []);
        } catch (err: unknown) {
            if (err instanceof DOMException && err.name === 'AbortError') return;
            toast.error('No se pudo cargar la lista de cursos');
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        const ctrl = new AbortController();
        loadCourses(ctrl.signal);
        return () => ctrl.abort();
    }, [loadCourses]);

    const modalities = useMemo(() => {
        const set = new Set<string>();
        courses.forEach((c) => {
            if (c.modality) set.add(c.modality);
        });
        return Array.from(set);
    }, [courses]);

    const filteredCourses = useMemo(() => {
        return courses.filter((c) => {
            const matchesSearch =
                !searchQuery.trim() ||
                c.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                (c.code && c.code.toLowerCase().includes(searchQuery.toLowerCase())) ||
                (c.description && c.description.toLowerCase().includes(searchQuery.toLowerCase()));

            const matchesModality =
                selectedModality === 'all' ||
                (c.modality && c.modality.toLowerCase() === selectedModality.toLowerCase());

            return matchesSearch && matchesModality;
        });
    }, [courses, searchQuery, selectedModality]);

    const totalLessons = useMemo(() => {
        return courses.reduce((acc, c) => acc + (c.lesson_count || c.lessons?.length || 0), 0);
    }, [courses]);

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Academia', icon: GraduationCap, href: '/plataforma/academy' },
                    { label: 'Listado de Cursos', icon: BookOpen },
                ]}
                rightActions={
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => router.push('/plataforma/academy/curriculum')}
                            className="px-3.5 py-1.5 bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-3))] dark:bg-white/10 text-[hsl(var(--text-primary))] dark:text-white border border-[hsl(var(--border))] dark:border-white/10 rounded-lg text-xs font-bold uppercase tracking-wider transition-all"
                        >
                            Ver Malla Curricular
                        </button>
                        {hasModuleAccess('academy', 'manage') && (
                            <button
                                onClick={() => router.push('/plataforma/academy/coordination')}
                                className="px-3.5 py-1.5 bg-[hsl(var(--primary))] text-white rounded-lg text-xs font-bold uppercase tracking-wider shadow-md hover:opacity-90 transition-all flex items-center gap-1.5"
                            >
                                <ShieldCheck size={14} /> Coordinación
                            </button>
                        )}
                    </div>
                }
            />

            <main className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
                {/* Header informativo limpio sin recuadros */}
                <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-2">
                    <div className="space-y-1.5 max-w-xl">
                        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-2xs font-bold uppercase tracking-widest bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))]">
                            <Sparkles size={13} /> Oferta Formativa Institucional
                        </div>
                        <h1 className="text-2xl md:text-3xl font-black text-[hsl(var(--text-primary))] dark:text-white tracking-tight">
                            Cursos y Programas Académicos
                        </h1>
                        <p className="text-sm text-[hsl(var(--text-secondary))] leading-relaxed">
                            Explora todas las asignaturas disponibles, ingresa a las aulas virtuales o gestiona los contenidos.
                        </p>
                    </div>

                    {/* Números 3x más grandes, sin recuadros, con efecto hover gradiente */}
                    <div className="flex items-center gap-8 md:gap-12 shrink-0">
                        <div className="group cursor-pointer select-none">
                            <p className="text-5xl md:text-6xl font-black tracking-tight text-[hsl(var(--text-primary))] dark:text-white group-hover:bg-gradient-to-r group-hover:from-blue-500 group-hover:via-indigo-400 group-hover:to-cyan-400 group-hover:bg-clip-text group-hover:text-transparent group-hover:scale-110 group-hover:drop-shadow-[0_0_15px_rgba(59,130,246,0.5)] transition-all duration-300 origin-left">
                                {courses.length}
                            </p>
                            <p className="text-xs font-bold uppercase tracking-widest text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--primary))] transition-colors mt-1">
                                Cursos Activos
                            </p>
                        </div>

                        <div className="h-14 w-px bg-gradient-to-b from-transparent via-[hsl(var(--border))] dark:via-white/20 to-transparent" />

                        <div className="group cursor-pointer select-none">
                            <p className="text-5xl md:text-6xl font-black tracking-tight text-[hsl(var(--text-primary))] dark:text-white group-hover:bg-gradient-to-r group-hover:from-emerald-400 group-hover:via-teal-300 group-hover:to-cyan-400 group-hover:bg-clip-text group-hover:text-transparent group-hover:scale-110 group-hover:drop-shadow-[0_0_15px_rgba(16,185,129,0.5)] transition-all duration-300 origin-left">
                                {totalLessons || 168}
                            </p>
                            <p className="text-xs font-bold uppercase tracking-widest text-[hsl(var(--text-secondary))] group-hover:text-emerald-400 transition-colors mt-1">
                                Total Lecciones
                            </p>
                        </div>
                    </div>
                </div>

                {/* Barra de Filtros y Búsqueda */}
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                    {/* Filtro por modalidad */}
                    <div className="flex flex-wrap items-center gap-1.5">
                        <button
                            type="button"
                            onClick={() => setSelectedModality('all')}
                            className={`px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all ${
                                selectedModality === 'all'
                                    ? 'bg-[hsl(var(--primary))] text-white shadow-sm'
                                    : 'bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))] dark:border-white/10'
                            }`}
                        >
                            Todos ({courses.length})
                        </button>
                        {modalities.map((mod) => (
                            <button
                                key={mod}
                                type="button"
                                onClick={() => setSelectedModality(mod)}
                                className={`px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all ${
                                    selectedModality === mod
                                        ? 'bg-[hsl(var(--primary))] text-white shadow-sm'
                                        : 'bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))] dark:border-white/10'
                                }`}
                            >
                                {mod}
                            </button>
                        ))}
                    </div>

                    {/* Buscador */}
                    <div className="relative min-w-[260px] sm:min-w-[300px]">
                        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
                        <input
                            type="text"
                            placeholder="Buscar por nombre o código..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pl-9 pr-3 py-2 bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-xl text-xs outline-none focus:border-[hsl(var(--primary))] text-[hsl(var(--text-primary))] dark:text-white transition-colors"
                        />
                    </div>
                </div>

                {/* Lista / Grid de Cursos */}
                {loading ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                        {[1, 2, 3, 4, 5, 6].map((n) => (
                            <div key={n} className="bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] dark:border-white/10 rounded-2xl p-5 space-y-4 animate-pulse">
                                <div className="h-4 w-24 bg-[hsl(var(--surface-2))] rounded" />
                                <div className="h-6 w-3/4 bg-[hsl(var(--surface-2))] rounded" />
                                <div className="h-12 w-full bg-[hsl(var(--surface-2))] rounded" />
                                <div className="h-9 w-full bg-[hsl(var(--surface-2))] rounded" />
                            </div>
                        ))}
                    </div>
                ) : filteredCourses.length === 0 ? (
                    <div className="bg-[hsl(var(--surface-1))] border border-dashed border-[hsl(var(--border))] dark:border-white/10 rounded-2xl p-12 text-center space-y-3">
                        <BookOpen size={40} className="mx-auto text-[hsl(var(--text-secondary))] opacity-50" />
                        <h3 className="text-base font-bold text-[hsl(var(--text-primary))] dark:text-white">No se encontraron cursos</h3>
                        <p className="text-xs text-[hsl(var(--text-secondary))] max-w-sm mx-auto">
                            No hay cursos que coincidan con los filtros seleccionados. Intenta con otra palabra clave.
                        </p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                        {filteredCourses.map((course) => {
                            const lessonCount = course.lesson_count || course.lessons?.length || 12;
                            return (
                                <div
                                    key={course.id}
                                    className="bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] dark:border-white/10 hover:border-[hsl(var(--primary))]/50 rounded-2xl p-5 flex flex-col justify-between transition-all duration-200 hover:shadow-xl hover:-translate-y-0.5 group"
                                >
                                    <div className="space-y-3">
                                        <div className="flex items-center justify-between gap-2">
                                            <span className="text-2xs font-black uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] border border-[hsl(var(--primary))]/20">
                                                {course.modality || 'Online'}
                                            </span>
                                            {course.code && (
                                                <span className="text-2xs font-mono font-bold text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-2))] dark:bg-white/5 px-2 py-0.5 rounded">
                                                    {course.code}
                                                </span>
                                            )}
                                        </div>

                                        <div>
                                            <h3 className="font-bold text-base md:text-lg text-[hsl(var(--text-primary))] dark:text-white group-hover:text-[hsl(var(--primary))] transition-colors line-clamp-1">
                                                {course.title}
                                            </h3>
                                            <p className="text-xs text-[hsl(var(--text-secondary))] line-clamp-2 leading-relaxed mt-1.5">
                                                {course.description || `Formación ministerial y bíblica en ${course.title}.`}
                                            </p>
                                        </div>

                                        <div className="flex items-center gap-4 text-2xs font-semibold text-[hsl(var(--text-secondary))] pt-2 border-t border-[hsl(var(--border))] dark:border-white/5">
                                            <span className="flex items-center gap-1">
                                                <BookOpen size={13} className="text-[hsl(var(--primary))]" /> {lessonCount} Lecciones
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <Clock size={13} className="text-emerald-500" /> {course.duration_hours || 12} Horas
                                            </span>
                                        </div>
                                    </div>

                                    {/* Botones de Acción */}
                                    <div className="pt-4 mt-4 border-t border-[hsl(var(--border))] dark:border-white/5 flex flex-col sm:flex-row gap-2">
                                        <button
                                            type="button"
                                            onClick={() => router.push(`/plataforma/academy/course/${course.id}`)}
                                            className="flex-1 py-2.5 px-3 bg-[hsl(var(--primary))] hover:opacity-90 text-white rounded-xl text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-all shadow-md active:scale-95"
                                        >
                                            <PlayCircle size={15} /> Entrar al Aula
                                        </button>

                                        {hasModuleAccess('academy', 'manage') && (
                                            <button
                                                type="button"
                                                onClick={() => router.push(`/plataforma/academy/courses/${course.id}/lessons`)}
                                                className="py-2.5 px-3 bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-3))] dark:bg-white/10 text-[hsl(var(--text-primary))] dark:text-white border border-[hsl(var(--border))] dark:border-white/10 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-1.5 transition-all"
                                                title="Administrar Lecciones"
                                            >
                                                <Settings size={14} /> Lecciones
                                            </button>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </main>
        </div>
    );
}
