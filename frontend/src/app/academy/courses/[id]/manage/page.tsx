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
import { motion, AnimatePresence } from 'framer-motion';

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
    const params = useParams();
    const id = params ? (params.id as string) : null;
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
                // Allow independent failure
                const courseReq = apiFetch<CourseDetails>(`/academy/courses/${id}`, { token }).catch(() => null);
                // Dummy endpoint, wait for backend Implementation
                const studentsReq = apiFetch<Student[]>(`/academy/admin/courses/${id}/students`, { token }).catch(() => []);
                
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
    }, [id, token, isAuthenticated]);

    const filteredStudents = useMemo(() => {
        return students.filter(s => 
            s.username.toLowerCase().includes(search.toLowerCase()) || 
            s.email.toLowerCase().includes(search.toLowerCase())
        );
    }, [students, search]);

    if (!isStaff) {
        return (
            <div className="flex flex-col items-center justify-center h-full p-10 text-center space-y-6 bg-[#f8fafc] dark:bg-[#0b0d11]">
                <motion.div 
                    initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
                    className="size-24 bg-rose-500/10 rounded-[2rem] flex items-center justify-center text-rose-500 shadow-inner"
                >
                    <XCircle size={48} strokeWidth={2.5} />
                </motion.div>
                <div className="space-y-2">
                    <h2 className="text-3xl font-black text-slate-800 dark:text-white tracking-tight">Acceso Restringido</h2>
                    <p className="text-slate-500 max-w-sm font-medium">Esta consola de gestión está reservada para personal autorizado. Contacta a coordinación académica.</p>
                </div>
                <button onClick={() => router.back()} className="px-8 py-4 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-2xl font-black uppercase tracking-[0.2em] text-[10px] shadow-2xl transition-all active:scale-95">Volver a puerto</button>
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
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden relative">
            {/* Background decorative elements */}
            <div className="absolute top-0 left-0 w-full h-64 bg-gradient-to-b from-blue-600/5 to-transparent pointer-events-none" />
            
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Academia', icon: GraduationCap, href: '/academy' },
                    { label: 'Gestión Operativa', icon: Settings },
                ]}
                viewType="grid"
                setViewType={() => {}}
                leftActions={
                    <button onClick={() => router.back()} className="p-2.5 hover:bg-white dark:hover:bg-white/5 rounded-xl transition-all border border-transparent hover:border-slate-200 dark:hover:border-white/10 shadow-sm">
                        <ArrowLeft size={18} className="text-slate-500" />
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-6 lg:p-10 relative z-10">
                <motion.div 
                    variants={containerVariants} initial="hidden" animate="show"
                    className="max-w-[1400px] mx-auto space-y-10"
                >
                    {/* Course Header Glassmorphism */}
                    <motion.section variants={itemVariants} className="bg-white/70 dark:bg-[#15171c]/70 backdrop-blur-3xl rounded-[3rem] border border-white dark:border-white/5 p-8 lg:p-12 shadow-2xl shadow-slate-200/50 dark:shadow-none flex flex-col md:flex-row md:items-center justify-between gap-8 relative overflow-hidden group">
                        <div className="absolute top-[-20%] right-[-5%] w-64 h-64 bg-blue-600/10 rounded-full blur-[80px] group-hover:bg-blue-600/20 transition-all duration-1000" />
                        
                        <div className="space-y-6 relative z-10">
                            <div className="flex items-center gap-3">
                                <div className="px-4 py-1.5 bg-blue-600 text-white rounded-full text-[9px] font-black uppercase tracking-[0.2em] shadow-lg shadow-blue-500/20">
                                    {course?.modality === 'formal' ? 'Ruta Ministerial' : 'Capacitación'}
                                </div>
                                <div className="px-4 py-1.5 bg-slate-100 dark:bg-white/10 text-slate-500 dark:text-slate-400 rounded-full text-[9px] font-black uppercase tracking-[0.2em]">
                                    {course?.code || '---'}
                                </div>
                            </div>
                            <div>
                                <h1 className="text-4xl lg:text-5xl font-black text-slate-900 dark:text-white tracking-tighter leading-none mb-3">
                                    {course ? course.title : (loading ? 'Sincronizando...' : 'Datos del Curso (No Disponible)')}
                                </h1>
                                <div className="flex items-center gap-6 text-slate-500 font-bold text-sm">
                                    <span className="flex items-center gap-2"><Users size={16} className="text-blue-500" /> {course?.students_count ?? 0} Alumnos</span>
                                    <span className="flex items-center gap-2"><Clock size={16} className="text-blue-500" /> {course?.cohort_name || 'Cohorte 2026-I'}</span>
                                </div>
                            </div>
                        </div>

                        <div className="flex items-center gap-4 relative z-10">
                            <button className="px-8 py-5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-[2rem] font-black text-xs uppercase tracking-[0.2em] hover:scale-105 active:scale-95 transition-all shadow-2xl">
                                Registrar Asistencia
                            </button>
                            <button className="size-16 bg-white dark:bg-[#1c1f26] text-slate-700 dark:text-white border border-slate-200 dark:border-white/10 rounded-[1.5rem] flex items-center justify-center hover:bg-slate-50 dark:hover:bg-white/5 transition-all shadow-lg">
                                <Settings size={22} />
                            </button>
                        </div>
                    </motion.section>

                    {/* Navigation Tabs */}
                    <div className="flex items-center gap-2 p-1.5 bg-slate-100 dark:bg-white/5 rounded-[2rem] w-fit mx-auto lg:mx-0">
                        {[
                            { id: 'students', label: 'Estudiantes', icon: Users },
                            { id: 'attendance', label: 'Asistencia', icon: Calendar },
                            { id: 'content', label: 'Currículo', icon: BookOpen },
                        ].map(tab => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id as any)}
                                className={clsx(
                                    "flex items-center gap-2.5 px-8 py-3.5 rounded-[1.5rem] text-[10px] font-black uppercase tracking-[0.2em] transition-all",
                                    activeTab === tab.id 
                                        ? "bg-white dark:bg-[#1c1f26] text-blue-600 shadow-xl shadow-slate-200/50 dark:shadow-none" 
                                        : "text-slate-400 hover:text-slate-600"
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
                                className="space-y-8"
                            >
                                {/* Search & Action Row */}
                                <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 px-4">
                                    <div className="relative flex-1 max-w-xl group">
                                        <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-500 transition-colors" size={18} />
                                        <input 
                                            type="text" 
                                            placeholder="Filtrar por nombre, ID o correo..." 
                                            value={search}
                                            onChange={(e) => setSearch(e.target.value)}
                                            className="w-full bg-white dark:bg-[#15171c] border border-slate-200 dark:border-white/5 rounded-[1.5rem] pl-14 pr-6 py-4 text-sm font-bold outline-none focus:ring-4 focus:ring-blue-500/10 transition-all shadow-sm"
                                        />
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <button className="flex items-center gap-2 px-6 py-4 bg-white dark:bg-[#15171c] border border-slate-200 dark:border-white/5 rounded-2xl text-[10px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-300 hover:bg-slate-50 transition-all">
                                            <FileText size={16} /> Exportar Acta
                                        </button>
                                    </div>
                                </div>

                                {/* Students Grid */}
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                                    {loading ? (
                                        Array(6).fill(0).map((_, i) => (
                                            <div key={i} className="h-64 bg-slate-100 dark:bg-white/5 rounded-[3rem] animate-pulse" />
                                        ))
                                    ) : filteredStudents.length > 0 ? (
                                        filteredStudents.map(student => (
                                            <div key={student.id} className="bg-white dark:bg-[#15171c] border border-slate-200 dark:border-white/5 rounded-[3rem] p-8 shadow-sm hover:shadow-2xl hover:shadow-slate-200/50 dark:hover:shadow-none transition-all duration-500 group relative overflow-hidden">
                                                <div className="absolute top-0 right-0 p-8 opacity-[0.02] group-hover:opacity-[0.05] transition-opacity">
                                                    <Users size={80} />
                                                </div>
                                                
                                                <div className="flex items-start justify-between relative z-10">
                                                    <div className="size-16 rounded-[1.5rem] bg-gradient-to-br from-slate-50 to-slate-100 dark:from-white/5 dark:to-white/10 flex items-center justify-center text-slate-400 font-black text-2xl shadow-inner border border-white dark:border-white/5">
                                                        {student.username[0].toUpperCase()}
                                                    </div>
                                                    <div className="flex flex-col items-end gap-2">
                                                        <span className={clsx(
                                                            "px-3 py-1 rounded-full text-[8px] font-black uppercase tracking-widest",
                                                            student.status === 'active' ? "bg-emerald-500/10 text-emerald-500" : "bg-rose-500/10 text-rose-500"
                                                        )}>
                                                            {student.status}
                                                        </span>
                                                        <button className="p-2 text-slate-300 hover:text-slate-600 transition-colors"><MoreHorizontal size={20} /></button>
                                                    </div>
                                                </div>

                                                <div className="mt-6 space-y-1 relative z-10">
                                                    <h4 className="text-xl font-black text-slate-800 dark:text-white truncate tracking-tight">{student.username}</h4>
                                                    <p className="text-[11px] font-bold text-slate-400 truncate tracking-wide">{student.email}</p>
                                                </div>
                                                
                                                <div className="mt-8 pt-8 border-t border-slate-50 dark:border-white/5 grid grid-cols-2 gap-8 relative z-10">
                                                    <div className="space-y-3">
                                                        <div className="flex items-center justify-between">
                                                            <p className="text-[9px] font-black uppercase tracking-widest text-slate-400">Progreso</p>
                                                            <span className="text-[10px] font-black text-slate-700 dark:text-slate-300">{student.progress}%</span>
                                                        </div>
                                                        <div className="h-2 bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden p-0.5">
                                                            <div className="h-full bg-blue-500 rounded-full shadow-lg shadow-blue-500/20" style={{ width: `${student.progress}%` }} />
                                                        </div>
                                                    </div>
                                                    <div className="text-right">
                                                        <p className="text-[9px] font-black uppercase tracking-widest text-slate-400 mb-1">Nota Promedio</p>
                                                        <p className={clsx("text-3xl font-black tracking-tighter", student.average_grade >= 70 ? "text-emerald-500" : "text-rose-500")}>
                                                            {student.average_grade.toFixed(1)}
                                                        </p>
                                                    </div>
                                                </div>

                                                <button className="w-full mt-8 py-4 bg-slate-50 dark:bg-white/5 rounded-2xl text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 group-hover:bg-blue-600 group-hover:text-white group-hover:shadow-xl group-hover:shadow-blue-500/20 transition-all">Perfil Académico</button>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="col-span-full py-32 text-center space-y-6">
                                            <div className="size-24 bg-slate-100 dark:bg-white/5 rounded-[2rem] flex items-center justify-center mx-auto text-slate-300 shadow-inner">
                                                <Search size={48} strokeWidth={1.5} />
                                            </div>
                                            <div className="space-y-2">
                                                <p className="text-xl font-black text-slate-800 dark:text-white">Cero coincidencias</p>
                                                <p className="text-slate-500 font-medium">Prueba con otros términos de búsqueda.</p>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </motion.div>
                        )}

                        {activeTab === 'attendance' && (
                            <motion.div 
                                key="attendance" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }}
                                className="bg-white dark:bg-[#15171c] border border-slate-200 dark:border-white/5 rounded-[4rem] p-16 lg:p-24 text-center space-y-10 shadow-2xl shadow-slate-200/50 dark:shadow-none"
                            >
                                <div className="size-28 bg-blue-50 dark:bg-blue-500/10 rounded-[2.5rem] flex items-center justify-center mx-auto text-blue-600 shadow-inner">
                                    <Calendar size={56} strokeWidth={1.5} />
                                </div>
                                <div className="max-w-xl mx-auto space-y-6">
                                    <h3 className="text-4xl font-black text-slate-900 dark:text-white tracking-tighter leading-none">Control de Asistencia</h3>
                                    <p className="text-slate-500 text-lg font-medium leading-relaxed">Inicia el registro para la sesión de hoy. Recuerda que el 75% de asistencia es requisito para la certificación formal.</p>
                                    <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
                                        <button className="w-full sm:w-auto px-10 py-5 bg-blue-600 text-white rounded-[2rem] font-black text-xs uppercase tracking-[0.2em] shadow-2xl shadow-blue-500/30 hover:scale-105 active:scale-95 transition-all">
                                            Iniciar Sesión Hoy
                                        </button>
                                        <button className="w-full sm:w-auto px-10 py-5 bg-transparent border-2 border-slate-100 dark:border-white/5 text-slate-500 rounded-[2rem] font-black text-xs uppercase tracking-[0.2em] hover:bg-slate-50 transition-all">
                                            Ver Historial
                                        </button>
                                    </div>
                                </div>
                            </motion.div>
                        )}

                        {activeTab === 'content' && (
                             <motion.div 
                                key="content" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}
                                className="bg-white dark:bg-[#15171c] border border-slate-200 dark:border-white/5 rounded-[4rem] p-16 lg:p-24 text-center space-y-10"
                            >
                                <div className="size-28 bg-purple-50 dark:bg-purple-500/10 rounded-[2.5rem] flex items-center justify-center mx-auto text-purple-600 shadow-inner">
                                    <BookOpen size={56} strokeWidth={1.5} />
                                </div>
                                <div className="max-w-xl mx-auto space-y-6">
                                    <h3 className="text-4xl font-black text-slate-900 dark:text-white tracking-tighter">Gestión Curricular</h3>
                                    <p className="text-slate-500 text-lg font-medium">Ajusta el contenido de las lecciones, actualiza recursos descargables y configura los criterios de evaluación del programa.</p>
                                    <button className="px-10 py-5 bg-purple-600 text-white rounded-[2rem] font-black text-xs uppercase tracking-[0.2em] shadow-2xl shadow-purple-500/30 hover:scale-105 transition-all">
                                        Abrir Editor Curricular
                                    </button>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </motion.div>
            </main>
        </div>
    );
}
