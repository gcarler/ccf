"use client";

import React, { useEffect, useState } from 'react';
import { BookOpen, CheckSquare, AlertTriangle, Loader2, ShieldCheck, History, ChevronRight, School, Shield, FileText, Zap, Download, Eye } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { useToast } from '@/context/ToastContext';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import type { ViewType } from '@/components/ViewSwitcher';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
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
const ACTA_VIEWS: ViewType[] = ['grid', 'list', 'table', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];

export default function ActaManagementPage() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const [courses, setCourses] = useState<Course[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);
    const [lastActa, setLastActa] = useState<FormalActa | null>(null);
    const [closing, setClosing] = useState(false);
    const [minGrade, setMinGrade] = useState(70);
    const [minAttendance, setMinAttendance] = useState(80);
    const [viewType, setViewType] = useState<ViewType>('grid');

    useEffect(() => {
        const controller = new AbortController();
        const fetchFormalCourses = async () => {
            if (!token) return;
            try {
                const response = await apiFetch<Course[]>('/academy/courses/', {
                    token,
                    query: { modality: 'formal' },
                    cache: 'no-store',
                    signal: controller.signal
                });
                setCourses(Array.isArray(response) ? response : []);
            } catch (error) {
                console.error(error);
            } finally {
                setLoading(false);
            }
        };
        fetchFormalCourses();
        return () => controller.abort();
    }, [token]);

    useEffect(() => {
        const fetchCourseData = async () => {
            if (!selectedCourse || !token) return;
            try {
                const actaData = await apiFetch<FormalActa>(`/academy/courses/${selectedCourse.id}/formal/last-acta`, {
                    token,
                    cache: 'no-store'
                });
                setLastActa(actaData);
            } catch {
                setLastActa(null);
            }
        };
        fetchCourseData();
    }, [selectedCourse, token]);

    const handleCloseActa = async () => {
        if (!selectedCourse) return;
        setClosing(true);
        try {
            const data = await apiFetch(`/academy/courses/${selectedCourse.id}/formal/close-acta`, {
                method: 'POST',
                token,
                body: { min_grade: minGrade, min_attendance: minAttendance }
            });
            addToast('Acta cerrada y procesada con éxito', 'success');
            setLastActa(data as FormalActa);
        } catch (error: unknown) {
            addToast(error?.detail?.message || 'Error operativo', 'error');
        } finally {
            setClosing(false);
        }
    };

    const groupedCourses = [
        { id: 'selected', label: 'Seleccionado', rows: courses.filter(course => course.id === selectedCourse?.id) },
        { id: 'pending', label: 'Pendientes', rows: courses.filter(course => course.id !== selectedCourse?.id) },
    ];

    const calendarEvents = courses.map((course, index) => ({
        id: course.id,
        title: course.title,
        date: new Date(Date.now() + index * 86400000).toISOString().split('T')[0],
        color: course.id === selectedCourse?.id ? 'emerald' as const : 'blue' as const,
        location: course.code,
    }));

    const ganttItems = courses.map((course, index) => {
        const date = new Date(Date.now() + index * 86400000).toISOString();
        return {
            id: course.id,
            title: course.title,
            subtitle: course.code,
            start_date: date,
            end_date: date,
            color: course.id === selectedCourse?.id ? 'emerald' as const : 'blue' as const,
            progress: course.id === selectedCourse?.id ? 100 : 50,
        };
    });

    const renderCourseList = () => (
        <div className="space-y-4">
            {courses.map((course) => (
                <button key={course.id} onClick={() => setSelectedCourse(course)} className="w-full text-left bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5 rounded-lg p-3 flex items-center justify-between hover:border-blue-300 transition-all">
                    <div>
                        <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tight">{course.title}</h3>
                        <p className="mt-1 text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">{course.code} · {course.modality}</p>
                    </div>
                    <ChevronRight size={18} className="text-[hsl(var(--text-secondary))]" />
                </button>
            ))}
        </div>
    );

    const renderCourseTable = () => (
        <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 overflow-x-auto bg-[hsl(var(--bg-primary))] dark:bg-white/5">
            <table className="w-full text-left min-w-[560px]">
                <thead className="bg-[hsl(var(--surface-1))] dark:bg-white/5">
                    <tr>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Curso</th>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hidden md:table-cell">Código</th>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Estado</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-[hsl(var(--border))] dark:divide-white/5">
                    {courses.map((course) => (
                        <tr key={course.id} onClick={() => setSelectedCourse(course)} className="hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.03] cursor-pointer">
                            <td className="px-3 py-1.5 text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{course.title}</td>
                            <td className="px-3 py-1.5 hidden md:table-cell text-[11px] text-[hsl(var(--text-secondary))]">{course.code}</td>
                            <td className="px-3 py-1.5"><span className={clsx("px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase", course.id === selectedCourse?.id ? "bg-emerald-50 text-emerald-600" : "bg-blue-50 text-[hsl(var(--primary))]")}>{course.id === selectedCourse?.id ? 'Seleccionado' : 'Disponible'}</span></td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );

    const renderCourseBoard = () => (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {groupedCourses.map((group) => (
                <section key={group.id} className="rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/[0.03] border border-[hsl(var(--border))] dark:border-white/10 p-3">
                    <div className="flex items-center justify-between mb-5">
                        <span className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{group.label}</span>
                        <span className="font-semibold text-[hsl(var(--text-secondary))]">{group.rows.length}</span>
                    </div>
                    <div className="space-y-3">
                        {group.rows.map((course) => (
                            <button key={course.id} onClick={() => setSelectedCourse(course)} className="w-full text-left bg-[hsl(var(--bg-primary))] dark:bg-white/[0.05] border border-[hsl(var(--border))] dark:border-white/5 rounded-lg p-4 hover:border-blue-300 transition-all">
                                <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tight">{course.title}</p>
                                <p className="mt-2 text-[10px] font-bold text-[hsl(var(--text-secondary))]">{course.code}</p>
                            </button>
                        ))}
                    </div>
                </section>
            ))}
        </div>
    );

    return (
        <WorkspaceLayout sidebarTitle="Academia / Gobernanza">
            <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] overflow-hidden animate-fade-in font-display">
                <WorkspaceToolbar
                    breadcrumbs={[{ label: 'Administración', icon: Shield }, { label: 'Actas y Certificación', icon: CheckSquare }]}
                    viewType={viewType}
                    setViewType={setViewType}
                    availableViews={ACTA_VIEWS}
                    rightActions={
                        <button className="flex items-center gap-2 px-4 py-1.5 bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--bg-primary))] text-white dark:text-[hsl(var(--text-primary))] rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-xl active:scale-95 transition-all">
                            <Download size={14} /> Historial Global
                        </button>
                    }
                />

                {viewType === 'list' ? (
                    <main className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-4">{renderCourseList()}</main>
                ) : viewType === 'table' ? (
                    <main className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-4">{renderCourseTable()}</main>
                ) : viewType === 'board' || viewType === 'kanban' ? (
                    <main className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-4">{renderCourseBoard()}</main>
                ) : viewType === 'calendar' ? (
                    <main className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-4">
                        <UniversalCalendarView
                            events={calendarEvents}
                            title="Calendario de actas"
                            onEventClick={(event) => {
                                const course = courses.find((item) => item.id === event.id);
                                if (course) setSelectedCourse(course);
                            }}
                        />
                    </main>
                ) : viewType === 'gantt' ? (
                    <main className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-4">
                        <UniversalGanttView
                            items={ganttItems}
                            moduleName="Actas académicas"
                            onItemClick={(item) => {
                                const course = courses.find((entry) => entry.id === item.id);
                                if (course) setSelectedCourse(course);
                            }}
                        />
                    </main>
                ) : viewType === 'wiki' ? (
                    <main className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-4">
                        <UniversalWikiView moduleName="Actas académicas" storageKey="wiki_admin_actas" />
                    </main>
                ) : (
                <div className="flex-1 flex overflow-hidden">
                    <aside className="w-80 lg:w-96 border-r border-[hsl(var(--border))] dark:border-white/5 bg-[hsl(var(--surface-1))]/30 dark:bg-black/10 flex flex-col shrink-0">
                        <div className="p-3 border-b border-[hsl(var(--border))] dark:border-white/5">
                            <h3 className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Ruta Formal Academia</h3>
                        </div>
                        <div className="flex-1 overflow-y-auto scrollbar-thin p-4 space-y-1">
                            {loading ? (
                                [1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-8 w-full rounded-lg" />)
                            ) : courses.map((course) => (
                                <button
                                    key={course.id}
                                    onClick={() => setSelectedCourse(course)}
                                    className={clsx(
                                        'w-full text-left px-3 py-1.5 rounded-lg transition-all group flex items-center justify-between relative overflow-hidden',
                                        selectedCourse?.id === course.id
                                            ? 'bg-[hsl(var(--bg-primary))] dark:bg-white/5 shadow-[var(--shadow-premium)] border border-[hsl(var(--border))] dark:border-white/10'
                                            : 'hover:bg-white/50 dark:hover:bg-white/5'
                                    )}
                                >
                                    {selectedCourse?.id === course.id && <div className="absolute left-0 top-4 bottom-4 w-1 bg-[hsl(var(--primary))] rounded-full" />}
                                    <div className="min-w-0">
                                        <p className={clsx('font-semibold leading-tight mb-1 truncate', selectedCourse?.id === course.id ? 'text-[hsl(var(--primary))] dark:text-white' : 'text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]')}>{course.title}</p>
                                        <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">{course.code}</p>
                                    </div>
                                    <ChevronRight size={16} className={clsx('transition-transform', selectedCourse?.id === course.id ? 'text-[hsl(var(--primary))] translate-x-0' : 'text-[hsl(var(--text-secondary))] -translate-x-2 opacity-0 group-hover:opacity-100 group-hover:translate-x-0')} />
                                </button>
                            ))}
                        </div>
                    </aside>

                    <main className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-4 relative bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21]">
                        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#1973f003_0%,_transparent_50%)] pointer-events-none" />
 <div className="w-full space-y-3 relative z-10">
                            <AnimatePresence mode="wait">
                                {selectedCourse ? (
                                    <motion.div
                                        key={selectedCourse.id}
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0, y: -10 }}
                                        className="space-y-3"
                                    >
                                        <header className="flex items-start justify-between gap-3">
                                            <div className="space-y-4">
                                                <div className="flex items-center gap-3">
                                                    <div className="size-7 rounded-lg bg-[hsl(var(--primary))] flex items-center justify-center text-white shadow-xl shadow-blue-500/20">
                                                        <School size={24} />
                                                    </div>
                                                    <div>
                                                        <h2 className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tighter leading-none">{selectedCourse.title}</h2>
                                                        <p className="text-sm font-medium text-[hsl(var(--text-secondary))] mt-1">Gestión de Cierre Académico y Certificación.</p>
                                                    </div>
                                                </div>
                                            </div>
                                            {lastActa && (
                                                <div className="px-4 py-2 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 rounded-md text-[10px] font-semibold uppercase tracking-wide border border-emerald-100 dark:border-emerald-900/30 flex items-center gap-2 shadow-sm">
                                                    <ShieldCheck size={14} /> Acta Vigente
                                                </div>
                                            )}
                                        </header>

                                        <section className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                            <div className="p-4 bg-[hsl(var(--surface-1))] dark:bg-black/20 rounded-lg border border-[hsl(var(--border))] dark:border-white/5 space-y-3">
                                                <h4 className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide flex items-center gap-2"><Zap size={14} className="text-[hsl(var(--primary))]" /> Requisitos de Aprobación</h4>
                                                <div className="space-y-3">
                                                    <div className="space-y-2">
                                                        <label className="text-[10px] font-semibold uppercase text-[hsl(var(--text-secondary))] ml-2">Nota Mínima</label>
                                                        <div className="relative">
                                                            <input type="number" value={minGrade} onChange={(e) => setMinGrade(Number(e.target.value))} className="w-full bg-[hsl(var(--bg-primary))] dark:bg-black/40 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg p-4 font-semibold focus:ring-4 focus:ring-blue-500/10 transition-all outline-none" />
                                                            <span className="font-semibold">%</span>
                                                        </div>
                                                    </div>
                                                    <div className="space-y-2">
                                                        <label className="text-[10px] font-semibold uppercase text-[hsl(var(--text-secondary))] ml-2">Asistencia Mínima</label>
                                                        <div className="relative">
                                                            <input type="number" value={minAttendance} onChange={(e) => setMinAttendance(Number(e.target.value))} className="w-full bg-[hsl(var(--bg-primary))] dark:bg-black/40 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg p-4 font-semibold focus:ring-4 focus:ring-blue-500/10 transition-all outline-none" />
                                                            <span className="font-semibold">%</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>

                                            <div className="p-4 bg-[hsl(var(--primary))] rounded-lg text-white shadow-2xl shadow-blue-500/30 relative overflow-hidden group">
                                                <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:scale-110 transition-transform">
                                                    <FileText size={64} />
                                                </div>
                                                <div className="relative z-10 h-full flex flex-col justify-between">
                                                    <div className="space-y-2">
                                                        <h4 className="text-[11px] font-semibold uppercase tracking-wide text-white/60">Simulación de Cierre</h4>
                                                        <p className="text-lg font-bold tracking-tight">12 Alumnos</p>
                                                        <p className="text-sm font-medium text-blue-100/80">Listos para recibir certificación según los criterios actuales.</p>
                                                    </div>
                                                    <button className="w-full py-1.5 mt-3 bg-[hsl(var(--bg-primary))] text-[hsl(var(--primary))] rounded-lg font-black text-[10px] uppercase tracking-wide shadow-xl active:scale-95 transition-all">Ver Alumnos Calificados</button>
                                                </div>
                                            </div>
                                        </section>

                                        <section className="space-y-3">
                                            <div className="p-4 bg-amber-50 dark:bg-amber-900/10 rounded-lg border border-amber-100 dark:border-amber-900/30 flex items-start gap-3">
                                                <div className="size-7 rounded-lg bg-[hsl(var(--bg-primary))] dark:bg-white/5 flex items-center justify-center text-amber-500 shadow-sm shrink-0">
                                                    <AlertTriangle size={24} />
                                                </div>
                                                <div className="space-y-1">
                                                    <h4 className="font-semibold text-amber-700 dark:text-amber-400 uppercase tracking-wide">Acción Crítica</h4>
                                                    <p className="text-sm text-amber-600/80 dark:text-amber-500/60 font-medium leading-relaxed">Al cerrar el acta, se emitirán certificados PDF con firma digital para todos los aprobados. Esta acción no se puede deshacer de forma masiva.</p>
                                                </div>
                                            </div>
                                            <button
                                                onClick={handleCloseActa}
                                                disabled={closing}
                                                className="w-full py-2 bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--bg-primary))] text-white dark:text-[hsl(var(--text-primary))] rounded-lg font-black text-[12px] uppercase tracking-wide shadow-2xl active:scale-95 transition-all disabled:opacity-50 flex items-center justify-center gap-4 group"
                                            >
                                                {closing ? <Loader2 className="animate-spin" /> : <ShieldCheck size={20} className="group-hover:scale-110 transition-transform" />}
                                                {closing ? 'PROCESANDO PROTOCOLO...' : 'CERRAR ACTA Y CERTIFICAR'}
                                            </button>
                                        </section>

                                        {lastActa && (
                                            <section className="space-y-3">
                                                <div className="flex items-center justify-between px-4">
                                                    <h4 className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide flex items-center gap-2"><History size={14} /> Historial de Decisiones</h4>
                                                    <button className="text-[10px] font-bold text-[hsl(var(--primary))] flex items-center gap-1">Ver todos <ChevronRight size={12} /></button>
                                                </div>
                                                <div className="bg-[hsl(var(--bg-primary))] dark:bg-white/5 rounded-lg border border-[hsl(var(--border))] dark:border-white/5 overflow-hidden">
                                                    <div className="p-3 flex items-center justify-between hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-all group">
                                                        <div className="flex items-center gap-4">
                                                            <div className="size-10 rounded-md bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))]"><FileText size={18} /></div>
                                                            <div>
                                                                <p className="text-[13px] font-bold text-[hsl(var(--text-primary))] dark:text-white">Acta Académica #{lastActa.id}</p>
                                                                <p className="text-[10px] text-[hsl(var(--text-secondary))] font-semibold uppercase tracking-wide">{new Date(lastActa.created_at).toLocaleString()}</p>
                                                            </div>
                                                        </div>
                                                        <button className="p-2 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-all opacity-0 group-hover:opacity-100"><Eye size={18} /></button>
                                                    </div>
                                                </div>
                                            </section>
                                        )}
                                    </motion.div>
                                ) : (
                                    <motion.div
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        className="h-[600px] flex flex-col items-center justify-center text-center space-y-3"
                                    >
                                        <div className="size-10 rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-primary))] shadow-inner">
                                            <BookOpen size={64} strokeWidth={1} />
                                        </div>
                                        <div className="space-y-2">
                                            <h3 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tighter">Selecciona un Curso Formal</h3>
                                            <p className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-medium max-w-xs mx-auto leading-relaxed">Elige un curso del currículo de la Escuela de Líderes para gestionar su cierre oficial.</p>
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                    </main>
                </div>
                )}
            </div>
        </WorkspaceLayout>
    );
}
