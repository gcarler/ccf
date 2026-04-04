"use client";

import React, { useEffect, useState, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { apiFetch } from '@/lib/http';
import { 
    Users, 
    Calendar, 
    BookOpen, 
    GraduationCap, 
    Settings, 
    ChevronRight, 
    Search,
    UserCheck,
    FileText,
    MoreHorizontal,
    ArrowLeft,
    CheckCircle2,
    XCircle,
    Clock
} from 'lucide-react';
import { toast } from 'sonner';
import clsx from 'clsx';

interface Student {
    id: number;
    username: string;
    email: string;
    enrollment_id: number;
    progress: number;
    status: string;
    attendance_count: number;
    average_grade: number;
}

interface CourseDetails {
    id: number;
    title: string;
    code: string;
    modality: string;
    cohort_name: string;
    lessons_count: number;
    students_count: number;
}

export default function CourseManagementPage() {
    const { id } = useParams();
    const router = useRouter();
    const { token, user, isAuthenticated } = useAuth();
    
    const [course, setCourse] = useState<CourseDetails | null>(null);
    const [students, setStudents] = useState<Student[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [activeTab, setActiveTab] = useState<'students' | 'attendance' | 'content'>('students');

    const isStaff = useMemo(() => {
        const role = (user?.role || '').toLowerCase();
        return ['admin', 'coordinador', 'docente', 'staff'].includes(role);
    }, [user?.role]);

    useEffect(() => {
        if (!token || !isAuthenticated) return;
        const loadData = async () => {
            try {
                setLoading(true);
                const [courseData, studentsData] = await Promise.all([
                    apiFetch<CourseDetails>(`/academy/courses/${id}`, { token }),
                    apiFetch<Student[]>(`/academy/admin/courses/${id}/students`, { token })
                ]);
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
    }, [id, token, isAuthenticated]);

    const filteredStudents = useMemo(() => {
        return students.filter(s => 
            s.username.toLowerCase().includes(search.toLowerCase()) || 
            s.email.toLowerCase().includes(search.toLowerCase())
        );
    }, [students, search]);

    if (!isStaff) {
        return (
            <div className="flex flex-col items-center justify-center h-full p-10 text-center space-y-4">
                <div className="size-20 bg-rose-500/10 rounded-full flex items-center justify-center text-rose-500">
                    <XCircle size={40} />
                </div>
                <h2 className="text-2xl font-black text-slate-800 dark:text-white">Acceso Denegado</h2>
                <p className="text-slate-500 max-w-md">No tienes permisos para gestionar este curso. Contacta a coordinación académica.</p>
                <button onClick={() => router.back()} className="px-6 py-3 bg-slate-900 text-white rounded-2xl font-black uppercase tracking-widest text-[10px]">Volver</button>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Academia', icon: GraduationCap, href: '/academy' },
                    { label: 'Gestión de Curso', icon: Settings },
                ]}
                viewType="grid"
                setViewType={() => {}}
                leftActions={
                    <button onClick={() => router.back()} className="p-2 hover:bg-slate-100 dark:hover:bg-white/5 rounded-xl transition-all">
                        <ArrowLeft size={18} className="text-slate-500" />
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto p-6 lg:p-10 space-y-8">
                {/* Course Header Card */}
                <section className="bg-white dark:bg-[#15171c] rounded-[3rem] border border-slate-200 dark:border-white/5 p-8 shadow-xl shadow-slate-200/20 dark:shadow-none flex flex-col md:flex-row md:items-center justify-between gap-6 relative overflow-hidden">
                    <div className="absolute top-0 right-0 p-8 opacity-[0.03] pointer-events-none">
                        <GraduationCap size={120} />
                    </div>
                    
                    <div className="space-y-4 relative z-10">
                        <div className="flex items-center gap-3">
                            <span className="px-3 py-1 bg-blue-500/10 text-blue-600 rounded-lg text-[10px] font-black uppercase tracking-widest">
                                {course?.modality === 'formal' ? 'Academia Formal' : 'Capacitación Continua'}
                            </span>
                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">
                                {course?.code}
                            </span>
                        </div>
                        <div>
                            <h1 className="text-3xl lg:text-4xl font-black text-slate-900 dark:text-white tracking-tighter">
                                {course?.title || 'Cargando curso...'}
                            </h1>
                            <p className="text-slate-500 font-medium flex items-center gap-2 mt-1">
                                <Users size={16} /> {course?.students_count} Estudiantes Inscritos • {course?.cohort_name || 'Cohorte General'}
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-3 relative z-10">
                        <button className="px-6 py-4 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-2xl font-black text-[10px] uppercase tracking-widest hover:scale-105 transition-all shadow-lg">
                            Tomar Asistencia
                        </button>
                        <button className="px-6 py-4 bg-white dark:bg-[#1c1f26] text-slate-700 dark:text-white border border-slate-200 dark:border-white/10 rounded-2xl font-black text-[10px] uppercase tracking-widest hover:bg-slate-50 dark:hover:bg-white/5 transition-all">
                            Cerrar Acta
                        </button>
                    </div>
                </section>

                {/* Tabs & Content */}
                <section className="space-y-6">
                    <div className="flex items-center gap-8 border-b border-slate-200 dark:border-white/10 px-4">
                        {[
                            { id: 'students', label: 'Estudiantes', icon: Users },
                            { id: 'attendance', label: 'Asistencia', icon: Calendar },
                            { id: 'content', label: 'Contenido y Tareas', icon: BookOpen },
                        ].map(tab => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id as any)}
                                className={clsx(
                                    "flex items-center gap-2 py-4 text-[11px] font-black uppercase tracking-[0.2em] border-b-2 transition-all",
                                    activeTab === tab.id 
                                        ? "border-blue-600 text-blue-600" 
                                        : "border-transparent text-slate-400 hover:text-slate-600 hover:border-slate-300"
                                )}
                            >
                                <tab.icon size={16} />
                                {tab.label}
                            </button>
                        ))}
                    </div>

                    {activeTab === 'students' && (
                        <div className="space-y-6">
                            {/* Filters */}
                            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                                <div className="relative flex-1 max-w-md">
                                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                                    <input 
                                        type="text" 
                                        placeholder="Buscar por nombre o correo..." 
                                        value={search}
                                        onChange={(e) => setSearch(e.target.value)}
                                        className="w-full bg-white dark:bg-[#15171c] border border-slate-200 dark:border-white/5 rounded-2xl pl-11 pr-4 py-3 text-sm outline-none focus:ring-2 focus:ring-blue-500/20"
                                    />
                                </div>
                                <div className="flex items-center gap-2">
                                    <button className="p-3 bg-white dark:bg-[#15171c] border border-slate-200 dark:border-white/5 rounded-xl text-slate-500 hover:text-slate-800 transition-all"><FileText size={18} /></button>
                                </div>
                            </div>

                            {/* Students Grid/Table */}
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                {loading ? (
                                    Array(6).fill(0).map((_, i) => (
                                        <div key={i} className="h-48 bg-slate-100 dark:bg-white/5 rounded-[2rem] animate-pulse" />
                                    ))
                                ) : filteredStudents.length > 0 ? (
                                    filteredStudents.map(student => (
                                        <div key={student.id} className="bg-white dark:bg-[#15171c] border border-slate-100 dark:border-white/5 rounded-[2.5rem] p-6 shadow-sm hover:shadow-xl hover:shadow-slate-200/20 dark:hover:shadow-none transition-all group">
                                            <div className="flex items-start justify-between">
                                                <div className="size-12 rounded-2xl bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400 font-black text-xl">
                                                    {student.username[0].toUpperCase()}
                                                </div>
                                                <button className="p-2 text-slate-300 hover:text-slate-600 rounded-lg"><MoreHorizontal size={18} /></button>
                                            </div>
                                            <div className="mt-4 space-y-1">
                                                <h4 className="text-lg font-bold text-slate-800 dark:text-white truncate">{student.username}</h4>
                                                <p className="text-[11px] font-medium text-slate-400 truncate">{student.email}</p>
                                            </div>
                                            
                                            <div className="mt-6 pt-6 border-t border-slate-50 dark:border-white/5 grid grid-cols-2 gap-4">
                                                <div>
                                                    <p className="text-[9px] font-black uppercase tracking-widest text-slate-400">Progreso</p>
                                                    <div className="flex items-center gap-2 mt-1">
                                                        <div className="flex-1 h-1.5 bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
                                                            <div className="h-full bg-blue-500 rounded-full" style={{ width: `${student.progress}%` }} />
                                                        </div>
                                                        <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300">{student.progress}%</span>
                                                    </div>
                                                </div>
                                                <div>
                                                    <p className="text-[9px] font-black uppercase tracking-widest text-slate-400">Promedio</p>
                                                    <p className={clsx("text-lg font-black tracking-tight mt-1", student.average_grade >= 70 ? "text-emerald-500" : "text-rose-500")}>
                                                        {student.average_grade.toFixed(1)}
                                                    </p>
                                                </div>
                                            </div>

                                            <button className="w-full mt-6 py-3 bg-slate-50 dark:bg-white/5 rounded-xl text-[10px] font-black uppercase tracking-widest text-slate-500 group-hover:bg-blue-600 group-hover:text-white transition-all">Ver Detalle</button>
                                        </div>
                                    ))
                                ) : (
                                    <div className="col-span-full py-20 text-center space-y-4">
                                        <div className="size-16 bg-slate-100 dark:bg-white/5 rounded-full flex items-center justify-center mx-auto text-slate-300">
                                            <Search size={32} />
                                        </div>
                                        <p className="text-slate-500 font-medium">No se encontraron estudiantes con esos criterios.</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {activeTab === 'attendance' && (
                        <div className="bg-white dark:bg-[#15171c] border border-slate-200 dark:border-white/5 rounded-[3rem] p-10 text-center space-y-6">
                            <div className="size-20 bg-blue-50 dark:bg-blue-500/10 rounded-full flex items-center justify-center mx-auto text-blue-600">
                                <Calendar size={40} />
                            </div>
                            <div className="max-w-md mx-auto space-y-4">
                                <h3 className="text-2xl font-black text-slate-900 dark:text-white">Registro de Asistencia</h3>
                                <p className="text-slate-500">Lleva el control de asistencia para validar la aprobación de tus estudiantes en programas formales.</p>
                                <button className="px-8 py-4 bg-blue-600 text-white rounded-[2rem] font-black text-xs uppercase tracking-[0.2em] shadow-xl shadow-blue-500/20 hover:scale-105 transition-all">
                                    Iniciar Nueva Sesión
                                </button>
                            </div>
                        </div>
                    )}

                    {activeTab === 'content' && (
                         <div className="bg-white dark:bg-[#15171c] border border-slate-200 dark:border-white/5 rounded-[3rem] p-10 text-center space-y-6">
                            <div className="size-20 bg-purple-50 dark:bg-purple-500/10 rounded-full flex items-center justify-center mx-auto text-purple-600">
                                <BookOpen size={40} />
                            </div>
                            <div className="max-w-md mx-auto space-y-4">
                                <h3 className="text-2xl font-black text-slate-900 dark:text-white">Gestión de Contenido</h3>
                                <p className="text-slate-500">Crea lecciones, sube recursos y gestiona las evaluaciones del curso.</p>
                                <button className="px-8 py-4 bg-purple-600 text-white rounded-[2rem] font-black text-xs uppercase tracking-[0.2em] shadow-xl shadow-purple-500/20 hover:scale-105 transition-all">
                                    Editar Contenido del Curso
                                </button>
                            </div>
                        </div>
                    )}
                </section>
            </main>
        </div>
    );
}
