"use client";

import React, { useEffect, useState, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ViewType } from '@/components/ViewSwitcher';
import { apiFetch } from '@/lib/http';
import {
    Users,
    Calendar,
    BookOpen,
    GraduationCap,
    Settings,
    Search,
    FileText,
    MoreHorizontal,
    ArrowLeft,
    XCircle,
    Clock
} from 'lucide-react';
import { toast } from 'sonner';
import clsx from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';

interface Student {
    id: string;
    username: string;
    email: string;
    enrollment_id: string;
    progress: number;
    status: string;
    attendance_count: number;
    average_grade: number;
}

interface CourseDetails {
    id: string;
    title: string;
    code: string;
    modality: string;
    cohort_name: string;
    lessons_count: number;
    students_count: number;
}

export default function CourseManagementPage() {
    const params = useParams();
    const id = params ? (params.id as string) : null;
    const router = useRouter();
    const { token, user, isAuthenticated } = useAuth();

    const [course, setCourse] = useState<CourseDetails | null>(null);
    const [students, setStudents] = useState<Student[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [activeTab, setActiveTab] = useState<'students' | 'attendance' | 'content'>('students');
    const [viewType, setViewType] = useState<ViewType>('grid');

    const isStaff = useMemo(() => {
        const role = (user?.role || '').toLowerCase();
        return ['admin', 'coordinador', 'docente', 'staff'].includes(role);
    }, [user?.role]);

    useEffect(() => {
        if (!token || !isAuthenticated) return;
        const ctrl = new AbortController();
        const loadData = async () => {
            try {
                setLoading(true);
                const courseReq = apiFetch<CourseDetails>(`/academy/courses/${id}`, { token, signal: ctrl.signal }).catch(() => null);
                const studentsReq = apiFetch<Student[]>(`/academy/admin/courses/${id}/students`, { token, signal: ctrl.signal }).catch(() => []);
                const [courseData, studentsData] = await Promise.all([courseReq, studentsReq]);
                setCourse(courseData);
                setStudents(Array.isArray(studentsData) ? studentsData : []);
            } catch (err) {
                console.error(err);
                toast.error('Error al cargar datos del curso');
            } finally {
                setLoading(false);
            }
        };
        loadData();
        return () => ctrl.abort();
    }, [id, token, isAuthenticated]);

    const filteredStudents = useMemo(() => {
        return students.filter(s =>
            s.username.toLowerCase().includes(search.toLowerCase()) ||
            s.email.toLowerCase().includes(search.toLowerCase())
        );
    }, [students, search]);

    if (!isStaff) {
        return (
            <div className="flex flex-col items-center justify-center h-full p-4 text-center space-y-3 bg-[hsl(var(--bg-primary))]">
                <motion.div
                    initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
                    className="size-10 bg-[hsl(var(--destructive)/0.1)] rounded-lg flex items-center justify-center text-[hsl(var(--destructive))] shadow-inner"
                >
                    <XCircle size={48} strokeWidth={2.5} />
                </motion.div>
                <div className="space-y-2">
                    <h2 className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight">Acceso Restringido</h2>
                    <p className="text-[hsl(var(--text-secondary))] max-w-sm font-medium">Esta consola de gestion esta reservada para personal autorizado. Contacta a coordinacion academica.</p>
                </div>
                <button onClick={() => router.back()} className="px-3 py-1.5 bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--bg-primary))] text-white dark:text-[hsl(var(--text-primary))] rounded-lg font-semibold uppercase tracking-wide text-[10px] shadow-2xl transition-all active:scale-95">Volver a puerto</button>
            </div>
        );
    }

    const containerVariants = {
        hidden: { opacity: 0 },
        show: { opacity: 1, transition: { staggerChildren: 0.05 } }
    };

    const itemVariants = {
        hidden: { opacity: 0, scale: 0.95, y: 10 },
        show: { opacity: 1, scale: 1, y: 0 }
    };

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] overflow-hidden relative">
            <div className="absolute top-0 left-0 w-full h-48 bg-gradient-to-b to-[hsl(var(--info)/5%)] to-transparent pointer-events-none" />

            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Academia', icon: GraduationCap, href: '/plataforma/academy' },
                    { label: 'Gestion Operativa', icon: Settings },
                ]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={['grid', 'list', 'table']}
                leftActions={
                    <button onClick={() => router.back()} className="p-2.5 hover:bg-[hsl(var(--bg-primary))] dark:hover:bg-white/5 rounded-lg transition-all border border-transparent hover:border-[hsl(var(--border))] dark:hover:border-white/10 shadow-sm">
                        <ArrowLeft size={18} className="text-[hsl(var(--text-secondary))]" />
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-4 relative z-10">
                {viewType === 'list' && (
                    <div className="space-y-4">
                        {filteredStudents.map((student) => (
                            <article key={student.id} className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-3 dark:border-white/10 dark:bg-white/5">
                                <div className="flex items-center justify-between gap-4">
                                    <div>
                                        <h3 className="font-bold text-[hsl(var(--text-primary))] dark:text-white">{student.username}</h3>
                                        <p className="mt-1 text-sm text-[hsl(var(--text-secondary))]">{student.email}</p>
                                    </div>
                                    <span className="text-sm font-semibold text-[hsl(var(--primary))]">{Math.round(student.progress)}%</span>
                                </div>
                            </article>
                        ))}
                    </div>
                )}

                {viewType === 'table' && (
                    <div className="overflow-x-auto rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] dark:border-white/10 dark:bg-white/5">
                        <table className="w-full min-w-[480px] text-left">
                            <thead className="bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                <tr><th className="px-4 py-1.5">Estudiante</th><th className="px-4 py-1.5">Correo</th><th className="px-4 py-1.5">Progreso</th><th className="px-4 py-1.5">Nota</th></tr>
                            </thead>
                            <tbody>
                                {filteredStudents.map((student) => (
                                    <tr key={student.id} className="border-t border-[hsl(var(--border))] dark:border-white/5">
                                        <td className="px-4 py-1.5 font-bold text-[hsl(var(--text-primary))] dark:text-white">{student.username}</td>
                                        <td className="px-4 py-1.5 text-[hsl(var(--text-secondary))]">{student.email}</td>
                                        <td className="px-4 py-1.5 text-[hsl(var(--text-secondary))]">{Math.round(student.progress)}%</td>
                                        <td className="px-4 py-1.5 text-[hsl(var(--text-secondary))]">{student.average_grade.toFixed(1)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {viewType === 'grid' && (
                <motion.div
                    variants={containerVariants} initial="hidden" animate="show"
                    className="w-full space-y-4"
                >
                    <motion.section variants={itemVariants} className="bg-white/70 dark:bg-[hsl(var(--bg-primary))]/70 backdrop-blur-3xl rounded-lg border border-white dark:border-white/5 p-4 lg:p-4 shadow-2xl shadow-black/10/50 dark:shadow-none flex flex-col md:flex-row md:items-center justify-between gap-4 relative overflow-hidden group">
                        <div className="absolute top-[-20%] right-[-5%] w-64 h-48 bg-[hsl(var(--info))]/10 rounded-full blur-[80px] group-hover:bg-[hsl(var(--info))]/20 transition-all duration-1000" />

                        <div className="space-y-3 relative z-10">
                            <div className="flex items-center gap-3">
                                <div className="px-3 py-1.5 bg-[hsl(var(--primary))] text-white rounded-full text-[9px] font-semibold uppercase tracking-wide shadow-lg shadow-[hsl(var(--info)/20%)]">
                                    {course?.modality === 'formal' ? 'Ruta Ministerial' : 'Capacitacion'}
                                </div>
                                <div className="px-3 py-1.5 bg-[hsl(var(--surface-2))] dark:bg-white/10 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] rounded-full text-[9px] font-semibold uppercase tracking-wide">
                                    {course?.code || '---'}
                                </div>
                            </div>
                            <div>
                                <h1 className="text-lg lg:text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tighter leading-none mb-3">
                                    {course ? course.title : (loading ? 'Sincronizando...' : 'Datos del Curso (No Disponible)')}
                                </h1>
                                <div className="flex items-center gap-4 text-[hsl(var(--text-secondary))] font-bold text-sm">
                                    <span className="flex items-center gap-2"><Users size={16} className="text-[hsl(var(--primary))]" /> {course?.students_count ?? 0} Alumnos</span>
                                    <span className="flex items-center gap-2"><Clock size={16} className="text-[hsl(var(--primary))]" /> {course?.cohort_name || 'Cohorte 2026-I'}</span>
                                </div>
                            </div>
                        </div>

                        <div className="flex items-center gap-4 relative z-10">
                            <button className="px-3 py-1.5 bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--bg-primary))] text-white dark:text-[hsl(var(--text-primary))] rounded-lg font-black text-xs uppercase tracking-wide hover:scale-105 active:scale-95 transition-all shadow-2xl">
                                Registrar Asistencia
                            </button>
                            <button className="size-8 bg-[hsl(var(--bg-primary))] dark:bg-[#1c1f26] text-[hsl(var(--text-primary))] dark:text-white border border-[hsl(var(--border))] dark:border-white/10 rounded-lg flex items-center justify-center hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-all shadow-lg">
                                <Settings size={22} />
                            </button>
                        </div>
                    </motion.section>

                    <div className="flex items-center gap-2 p-1.5 bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-lg w-fit mx-auto lg:mx-0">
                        {[
                            { id: 'students', label: 'Estudiantes', icon: Users },
                            { id: 'attendance', label: 'Asistencia', icon: Calendar },
                            { id: 'content', label: 'Curriculo', icon: BookOpen },
                        ].map(tab => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id as any)}
                                className={clsx(
                                    "flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-[10px] font-semibold uppercase tracking-wide transition-all",
                                    activeTab === tab.id
                                        ? "bg-[hsl(var(--bg-primary))] dark:bg-[#1c1f26] text-[hsl(var(--primary))] shadow-xl shadow-black/10/50 dark:shadow-none"
                                        : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))]"
                                )}
                            >
                                <tab.icon size={14} strokeWidth={3} />
                                {tab.label}
                            </button>
                        ))}
                    </div>

                    <AnimatePresence mode="wait">
                        {activeTab === 'students' && (
                            <motion.div
                                key="students" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
                                className="space-y-3"
                            >
                                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 px-4">
                                    <div className="relative flex-1 max-w-xl group">
                                        <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))] group-focus-within:text-[hsl(var(--primary))] transition-colors" size={18} />
                                        <input
                                            type="text"
                                            placeholder="Filtrar por nombre, ID o correo..."
                                            value={search}
                                            onChange={(e) => setSearch(e.target.value)}
                                            className="w-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border))] dark:border-white/5 rounded-lg pl-14 pr-6 py-1.5 text-sm font-bold outline-none focus:ring-4 focus:ring-[hsl(var(--primary))]/10 transition-all shadow-sm"
                                        />
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <button className="flex items-center gap-2 px-3 py-1.5 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border))] dark:border-white/5 rounded-lg text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] transition-all">
                                            <FileText size={16} /> Exportar Acta
                                        </button>
                                    </div>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                    {loading ? (
                                        Array(6).fill(0).map((_, i) => (
                                            <div key={i} className="h-48 bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-lg animate-pulse" />
                                        ))
                                    ) : filteredStudents.length > 0 ? (
                                        filteredStudents.map(student => (
                                            <div key={student.id} className="bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border))] dark:border-white/5 rounded-lg p-3 shadow-sm hover:shadow-2xl hover:shadow-black/10/50 dark:hover:shadow-none transition-all duration-500 group relative overflow-hidden">
                                                <div className="absolute top-0 right-0 p-4 opacity-[0.02] group-hover:opacity-[0.05] transition-opacity">
                                                    <Users size={80} />
                                                </div>

                                                <div className="flex items-start justify-between relative z-10">
                                                    <div className="size-8 rounded-lg bg-gradient-to-br from-[hsl(var(--surface-1))] to-[hsl(var(--surface-2))] dark:from-white/5 dark:to-white/10 flex items-center justify-center text-[hsl(var(--text-secondary))] font-black text-lg shadow-inner border border-white dark:border-white/5">
                                                        {student.username[0].toUpperCase()}
                                                    </div>
                                                    <div className="flex flex-col items-end gap-2">
                                                        <span className={clsx(
                                                            "px-3 py-1 rounded-full text-[8px] font-semibold uppercase tracking-wide",
                                                            student.status === 'active' ? "bg-[hsl(var(--success)/0.1)] text-[hsl(var(--success))]" : "bg-[hsl(var(--destructive)/0.1)] text-[hsl(var(--destructive))]"
                                                        )}>
                                                            {student.status}
                                                        </span>
                                                        <button className="p-2 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] transition-colors"><MoreHorizontal size={20} /></button>
                                                    </div>
                                                </div>

                                                <div className="mt-3 space-y-1 relative z-10">
                                                    <h4 className="text-base font-bold text-[hsl(var(--text-primary))] dark:text-white truncate tracking-tight">{student.username}</h4>
                                                    <p className="text-[11px] font-bold text-[hsl(var(--text-secondary))] truncate tracking-wide">{student.email}</p>
                                                </div>

                                                <div className="mt-3 pt-3 border-t border-[hsl(var(--border))] dark:border-white/5 grid grid-cols-2 gap-4 relative z-10">
                                                    <div className="space-y-3">
                                                        <div className="flex items-center justify-between">
                                                            <p className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Progreso</p>
                                                            <span className="font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{student.progress}%</span>
                                                        </div>
                                                        <div className="h-2 bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-full overflow-hidden p-0.5">
                                                            <div className="h-full bg-[hsl(var(--primary))] rounded-full shadow-lg shadow-[hsl(var(--info)/20%)]" style={{ width: `${student.progress}%` }} />
                                                        </div>
                                                    </div>
                                                    <div className="text-right">
                                                        <p className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1">Nota Promedio</p>
                                                        <p className={clsx("text-xl font-bold tracking-tighter", student.average_grade >= 70 ? "text-[hsl(var(--success))]" : "text-[hsl(var(--destructive))]")}>
                                                            {student.average_grade.toFixed(1)}
                                                        </p>
                                                    </div>
                                                </div>

                                                <button className="w-full mt-3 py-1.5 bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-lg text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] group-hover:bg-[hsl(var(--primary))] group-hover:text-white group-hover:shadow-xl group-hover:shadow-[hsl(var(--info)/20%)] transition-all">Perfil Academico</button>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="col-span-full py-1.5 text-center space-y-3">
                                            <div className="size-10 bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-lg flex items-center justify-center mx-auto text-[hsl(var(--text-secondary))] shadow-inner">
                                                <Search size={48} strokeWidth={1.5} />
                                            </div>
                                            <div className="space-y-2">
                                                <p className="text-base font-bold text-[hsl(var(--text-primary))] dark:text-white">Cero coincidencias</p>
                                                <p className="text-[hsl(var(--text-secondary))] font-medium">Prueba con otros terminos de busqueda.</p>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </motion.div>
                        )}

                        {activeTab === 'attendance' && (
                            <motion.div
                                key="attendance" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }}
                                className="bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border))] dark:border-white/5 rounded-lg p-4 lg:p-4 text-center space-y-4 shadow-2xl shadow-black/10/50 dark:shadow-none"
                            >
                                <div className="size-10 bg-info-soft dark:bg-[hsl(var(--info))]/10 rounded-lg flex items-center justify-center mx-auto text-[hsl(var(--primary))] shadow-inner">
                                    <Calendar size={56} strokeWidth={1.5} />
                                </div>
                                <div className="max-w-xl mx-auto space-y-3">
                                    <h3 className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tighter leading-none">Control de Asistencia</h3>
                                    <p className="text-[hsl(var(--text-secondary))] text-sm font-medium leading-relaxed">Inicia el registro para la sesion de hoy. Recuerda que el 75% de asistencia es requisito para la certificacion formal.</p>
                                    <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
                                        <button className="w-full sm:w-auto px-3 py-1.5 bg-[hsl(var(--primary))] text-white rounded-lg font-black text-xs uppercase tracking-wide shadow-2xl shadow-[hsl(var(--info)/30%)] hover:scale-105 active:scale-95 transition-all">
                                            Iniciar Sesion Hoy
                                        </button>
                                        <button className="w-full sm:w-auto px-3 py-1.5 bg-transparent border-2 border-[hsl(var(--border))] dark:border-white/5 text-[hsl(var(--text-secondary))] rounded-lg font-black text-xs uppercase tracking-wide hover:bg-[hsl(var(--surface-1))] transition-all">
                                            Ver Historial
                                        </button>
                                    </div>
                                </div>
                            </motion.div>
                        )}

                        {activeTab === 'content' && (
                             <motion.div
                                key="content" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}
                                className="bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border))] dark:border-white/5 rounded-lg p-4 lg:p-4 text-center space-y-4"
                            >
                                <div className="size-10 bg-info-soft dark:bg-[hsl(var(--info))]/10 rounded-lg flex items-center justify-center mx-auto text-info-text shadow-inner">
                                    <BookOpen size={56} strokeWidth={1.5} />
                                </div>
                                <div className="max-w-xl mx-auto space-y-3">
                                    <h3 className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tighter">Gestion Curricular</h3>
                                    <p className="text-[hsl(var(--text-secondary))] text-sm font-medium">Ajusta el contenido de las lecciones, actualiza recursos descargables y configura los criterios de evaluacion del programa.</p>
                                    <button className="px-3 py-1.5 bg-[hsl(var(--info))] text-white rounded-lg font-black text-xs uppercase tracking-wide shadow-2xl shadow-[hsl(var(--info)/30%)] hover:scale-105 transition-all">
                                        Abrir Editor Curricular
                                    </button>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </motion.div>
                )}
            </main>
        </div>
    );
}
