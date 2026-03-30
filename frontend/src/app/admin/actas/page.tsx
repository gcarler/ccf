"use client";

import React, { useState, useEffect, useMemo } from 'react';
import { 
    BookOpen, 
    CheckSquare, 
    AlertTriangle, 
    CheckCircle2, 
    Loader2, 
    ShieldCheck,
    History,
    ChevronRight,
    School,
    Layout,
    Shield,
    Users,
    FileText,
    Zap,
    Download,
    Eye
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { useToast } from '@/context/ToastContext';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import Skeleton from '@/components/ui/Skeleton';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

interface Course {
    id: number;
    code: string;
    title: string;
    modality: string;
}

interface FormalActa {
    id: number;
    course_id: number;
    created_at: string;
    min_grade: number;
    min_attendance: number;
}

interface Enrollment {
    id: number;
    user_id: number;
    student_name?: string;
    progress_percent: number;
}

export default function ActaManagementPage() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const [courses, setCourses] = useState<Course[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);
    const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
    const [closing, setClosing] = useState(false);
    const [lastActa, setLastActa] = useState<FormalActa | null>(null);
    const [minGrade, setMinGrade] = useState(70);
    const [minAttendance, setMinAttendance] = useState(80);
    const [showAttendanceModal, setShowAttendanceModal] = useState(false);
    const [attendanceData, setAttendanceData] = useState<Record<number, string>>({});
    const [savingAttendance, setSavingAttendance] = useState(false);

    useEffect(() => {
        const fetchFormalCourses = async () => {
            if (!token) return;
            try {
                const response = await apiFetch<Course[]>('/courses/', {
                    token, query: { modality: 'formal' }, cache: 'no-store'
                });
                setCourses(Array.isArray(response) ? response : []);
            } catch (error) {
                console.error(error);
            } finally {
                setLoading(false);
            }
        };
        fetchFormalCourses();
    }, [token]);

    useEffect(() => {
        const fetchCourseData = async () => {
            if (!selectedCourse || !token) return;
            try {
                const [actaData, enrolls] = await Promise.all([
                    apiFetch<FormalActa>(`/courses/${selectedCourse.id}/formal/last-acta`, { token, cache: 'no-store' }),
                    apiFetch<any[]>(`/courses/${selectedCourse.id}/lessons`, { token }).then(async () => {
                        // En un entorno real, tendríamos un endpoint específico para alumnos por curso.
                        // Usaremos un mock o buscaremos inscripciones si existe el endpoint.
                        try {
                            const res = await apiFetch<any[]>(`/admin/submissions`, { token });
                            return res.filter(s => s.course_id === selectedCourse.id);
                        } catch { return []; }
                    })
                ]);
                setLastActa(actaData);
                // setEnrollments(enrolls); // Implementación simplificada
            } catch (error) {
                setLastActa(null);
            }
        };
        fetchCourseData();
    }, [selectedCourse, token]);

    // Mock enrollments for the demo of attendance if real list fails
    const activeEnrollments = useMemo(() => {
        return [
            { id: 101, user_id: 5, student_name: "Ricardo Mendez", progress_percent: 85 },
            { id: 102, user_id: 8, student_name: "Elena Rodriguez", progress_percent: 100 },
            { id: 103, user_id: 12, student_name: "Julian Castro", progress_percent: 40 },
        ];
    }, [selectedCourse]);

    const handleSaveAttendance = async () => {
        if (!selectedCourse || !token) return;
        setSavingAttendance(true);
        try {
            const records = activeEnrollments.map(e => ({
                enrollment_id: e.id,
                status: attendanceData[e.id] || 'present'
            }));

            await apiFetch(`/courses/${selectedCourse.id}/attendance/bulk`, {
                method: "POST",
                token,
                body: {
                    session_date: new Date().toISOString(),
                    records
                }
            });
            addToast("Asistencia guardada correctamente", "success");
            setShowAttendanceModal(false);
        } catch (error) {
            addToast("Error al guardar asistencia", "error");
        } finally {
            setSavingAttendance(false);
        }
    };

    const handleCloseActa = async () => {
        if (!selectedCourse) return;
        setClosing(true);
        try {
            const data = await apiFetch(`/courses/${selectedCourse.id}/formal/close-acta`, {
                method: "POST",
                token,
                body: { min_grade: minGrade, min_attendance: minAttendance }
            });
            addToast("Acta cerrada y procesada con éxito", "success");
            setLastActa(data as FormalActa);
        } catch (error: any) {
            addToast(error?.detail?.message || "Error operativo", "error");
        } finally {
            setClosing(false);
        }
    };

    return (
        <WorkspaceLayout sidebarTitle="Academia / Gobernanza">
            <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in font-display">
                <WorkspaceToolbar 
                    breadcrumbs={[{ label: 'Administración', icon: Shield }, { label: 'Actas y Certificación', icon: CheckSquare }]}
                    viewType="grid" setViewType={() => {}}
                    rightActions={
                        <button className="flex items-center gap-2 px-4 py-1.5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-xl text-[11px] font-black uppercase tracking-widest shadow-xl active:scale-95 transition-all">
                            <Download size={14} /> Historial Global
                        </button>
                    }
                />

                <div className="flex-1 flex overflow-hidden">
                    {/* Sidebar: Formal Courses List */}
                    <aside className="w-80 lg:w-96 border-r border-slate-100 dark:border-white/5 bg-slate-50/30 dark:bg-black/10 flex flex-col shrink-0">
                        <div className="p-6 border-b border-slate-100 dark:border-white/5">
                            <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em]">Ruta Formal Academia</h3>
                        </div>
                        <div className="flex-1 overflow-y-auto scrollbar-thin p-4 space-y-1">
                            {loading ? (
                                [1,2,3,4].map(i => <Skeleton key={i} className="h-16 w-full rounded-2xl" />)
                            ) : courses.map(course => (
                                <button 
                                    key={course.id} onClick={() => setSelectedCourse(course)}
                                    className={clsx(
                                        "w-full text-left px-5 py-4 rounded-2xl transition-all group flex items-center justify-between relative overflow-hidden",
                                        selectedCourse?.id === course.id 
                                            ? "bg-white dark:bg-white/5 shadow-[var(--shadow-premium)] border border-slate-200 dark:border-white/10" 
                                            : "hover:bg-white/50 dark:hover:bg-white/5"
                                    )}
                                >
                                    {selectedCourse?.id === course.id && <div className="absolute left-0 top-4 bottom-4 w-1 bg-blue-600 rounded-full" />}
                                    <div className="min-w-0">
                                        <p className={clsx("text-[13px] font-black leading-tight mb-1 truncate", selectedCourse?.id === course.id ? "text-blue-600 dark:text-white" : "text-slate-700 dark:text-slate-300")}>{course.title}</p>
                                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{course.code}</p>
                                    </div>
                                    <ChevronRight size={16} className={clsx("transition-transform", selectedCourse?.id === course.id ? "text-blue-600 translate-x-0" : "text-slate-300 -translate-x-2 opacity-0 group-hover:opacity-100 group-hover:translate-x-0")} />
                                </button>
                            ))}
                        </div>
                    </aside>

                    {/* Main Content Area */}
                    <main className="flex-1 overflow-y-auto scrollbar-thin p-8 lg:p-16 relative bg-white dark:bg-[#1e1f21]">
                        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#1973f003_0%,_transparent_50%)] pointer-events-none" />
                        
                        <div className="max-w-4xl mx-auto space-y-12 relative z-10">
                            <AnimatePresence mode="wait">
                                {selectedCourse ? (
                                    <motion.div 
                                        key={selectedCourse.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
                                        className="space-y-10"
                                    >
                                        {/* Header Info */}
                                        <header className="flex items-start justify-between gap-6">
                                            <div className="space-y-4">
                                                <div className="flex items-center gap-3">
                                                    <div className="size-12 rounded-2xl bg-blue-600 flex items-center justify-center text-white shadow-xl shadow-blue-500/20"><School size={24} /></div>
                                                    <div>
                                                        <h2 className="text-3xl font-black text-slate-800 dark:text-white tracking-tighter leading-none">{selectedCourse.title}</h2>
                                                        <p className="text-sm font-medium text-slate-500 mt-1">Gestión de Cierre Académico y Certificación.</p>
                                                    </div>
                                                </div>
                                            </div>
                                            {lastActa && (
                                                <div className="px-4 py-2 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 rounded-xl text-[10px] font-black uppercase tracking-widest border border-emerald-100 dark:border-emerald-900/30 flex items-center gap-2 shadow-sm">
                                                    <ShieldCheck size={14} /> Acta Vigente
                                                </div>
                                            )}
                                        </header>

                                        {/* Configuration Grid */}
                                        <section className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                            <div className="p-8 bg-slate-50 dark:bg-black/20 rounded-[2.5rem] border border-slate-100 dark:border-white/5 space-y-6">
                                                <h4 className="text-[11px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-2"><Zap size={14} className="text-blue-500" /> Requisitos de Aprobación</h4>
                                                <div className="space-y-6">
                                                    <div className="space-y-2">
                                                        <label className="text-[10px] font-black uppercase text-slate-500 ml-2">Nota Mínima</label>
                                                        <div className="relative"><input type="number" value={minGrade} onChange={(e) => setMinGrade(Number(e.target.value))} className="w-full bg-white dark:bg-black/40 border border-slate-200 dark:border-white/10 rounded-2xl p-4 text-[16px] font-black focus:ring-4 focus:ring-blue-500/10 transition-all outline-none" /><span className="absolute right-6 top-1/2 -translate-y-1/2 text-slate-400 font-black">%</span></div>
                                                    </div>
                                                    <div className="space-y-2">
                                                        <label className="text-[10px] font-black uppercase text-slate-500 ml-2">Asistencia Mínima</label>
                                                        <div className="relative"><input type="number" value={minAttendance} onChange={(e) => setMinAttendance(Number(e.target.value))} className="w-full bg-white dark:bg-black/40 border border-slate-200 dark:border-white/10 rounded-2xl p-4 text-[16px] font-black focus:ring-4 focus:ring-blue-500/10 transition-all outline-none" /><span className="absolute right-6 top-1/2 -translate-y-1/2 text-slate-400 font-black">%</span></div>
                                                    </div>
                                                </div>
                                            </div>

                                            <div className="p-8 bg-blue-600 rounded-[2.5rem] text-white shadow-2xl shadow-blue-500/30 relative overflow-hidden group">
                                                <div className="absolute top-0 right-0 p-6 opacity-10 group-hover:scale-110 transition-transform"><FileText size={64} /></div>
                                                <div className="relative z-10 h-full flex flex-col justify-between">
                                                    <div className="space-y-2">
                                                        <h4 className="text-[11px] font-black uppercase tracking-[0.2em] text-white/60">Simulación de Cierre</h4>
                                                        <p className="text-2xl font-black tracking-tight">12 Alumnos</p>
                                                        <p className="text-sm font-medium text-blue-100/80">Listos para recibir certificación según los criterios actuales.</p>
                                                    </div>
                                                    <button className="w-full py-4 mt-6 bg-white text-blue-600 rounded-2xl font-black text-[10px] uppercase tracking-widest shadow-xl active:scale-95 transition-all">Ver Alumnos Calificados</button>
                                                </div>
                                            </div>
                                        </section>

                                        {/* Process Action */}
                                        <section className="space-y-6">
                                            <div className="p-8 bg-amber-50 dark:bg-amber-900/10 rounded-[2.5rem] border border-amber-100 dark:border-amber-900/30 flex items-start gap-6">
                                                <div className="size-12 rounded-2xl bg-white dark:bg-white/5 flex items-center justify-center text-amber-500 shadow-sm shrink-0"><AlertTriangle size={24} /></div>
                                                <div className="space-y-1">
                                                    <h4 className="text-[13px] font-black text-amber-700 dark:text-amber-400 uppercase tracking-widest">Acción Crítica</h4>
                                                    <p className="text-sm text-amber-600/80 dark:text-amber-500/60 font-medium leading-relaxed">Al cerrar el acta, se emitirán certificados PDF con firma digital para todos los aprobados. Esta acción no se puede deshacer de forma masiva.</p>
                                                </div>
                                            </div>
                                            <button 
                                                onClick={handleCloseActa} disabled={closing}
                                                className="w-full py-6 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-[2rem] font-black text-[12px] uppercase tracking-[0.4em] shadow-2xl active:scale-95 transition-all disabled:opacity-50 flex items-center justify-center gap-4 group"
                                            >
                                                {closing ? <Loader2 className="animate-spin" /> : <ShieldCheck size={20} className="group-hover:scale-110 transition-transform" />}
                                                {closing ? "PROCESANDO PROTOCOLO..." : "CERRAR ACTA Y CERTIFICAR"}
                                            </button>
                                        </section>

                                        {/* History Log */}
                                        {lastActa && (
                                            <section className="space-y-6">
                                                <div className="flex items-center justify-between px-4">
                                                    <h4 className="text-[11px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-2"><History size={14} /> Historial de Decisiones</h4>
                                                    <button className="text-[10px] font-bold text-blue-600 flex items-center gap-1">Ver todos <ChevronRight size={12} /></button>
                                                </div>
                                                <div className="bg-white dark:bg-white/5 rounded-[2.5rem] border border-slate-100 dark:border-white/5 overflow-hidden">
                                                    <div className="p-6 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-white/5 transition-all group">
                                                        <div className="flex items-center gap-4">
                                                            <div className="size-10 rounded-xl bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400"><FileText size={18} /></div>
                                                            <div>
                                                                <p className="text-[13px] font-bold text-slate-800 dark:text-white">Acta Académica #{lastActa.id}</p>
                                                                <p className="text-[10px] text-slate-400 font-black uppercase tracking-widest">{new Date(lastActa.created_at).toLocaleString()}</p>
                                                            </div>
                                                        </div>
                                                        <button className="p-2 text-slate-300 hover:text-blue-600 transition-all opacity-0 group-hover:opacity-100"><Eye size={18} /></button>
                                                    </div>
                                                </div>
                                            </section>
                                        )}
                                    </motion.div>
                                ) : (
                                    <motion.div 
                                        initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                                        className="h-[600px] flex flex-col items-center justify-center text-center space-y-8"
                                    >
                                        <div className="size-32 rounded-[3rem] bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5 flex items-center justify-center text-slate-200 dark:text-slate-800 shadow-inner">
                                            <BookOpen size={64} strokeWidth={1} />
                                        </div>
                                        <div className="space-y-2">
                                            <h3 className="text-2xl font-black text-slate-800 dark:text-white tracking-tighter">Selecciona un Curso Formal</h3>
                                            <p className="text-slate-500 dark:text-slate-400 font-medium max-w-xs mx-auto leading-relaxed">Elige un curso del currículo de la Escuela de Líderes para gestionar su cierre oficial.</p>
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                    </main>
                </div>
            </div>
        </WorkspaceLayout>
    );
}
