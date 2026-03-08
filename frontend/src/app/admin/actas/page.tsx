"use client";

import React, { useState, useEffect } from 'react';
import { 
    BookOpen, 
    CheckSquare, 
    AlertTriangle, 
    CheckCircle2, 
    Loader2, 
    ShieldCheck,
    History,
    ChevronRight,
    School
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiUrl } from '@/lib/api';
import { useToast } from '@/context/ToastContext';

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

export default function ActaManagement() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const [courses, setCourses] = useState<Course[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);
    const [closing, setClosing] = useState(false);
    const [lastActa, setLastActa] = useState<FormalActa | null>(null);
    
    // Acta Config
    const [minGrade, setMinGrade] = useState(70);
    const [minAttendance, setMinAttendance] = useState(80);

    useEffect(() => {
        const fetchFormalCourses = async () => {
            try {
                const response = await fetch(apiUrl('/courses/?modality=formal'), {
                    headers: { Authorization: `Bearer ${token}` }
                });
                if (response.ok) {
                    setCourses(await response.json());
                }
            } catch (error) {
                addToast("Error al cargar cursos", "error");
            } finally {
                setLoading(false);
            }
        };

        if (token) fetchFormalCourses();
    }, [token, addToast]);

    useEffect(() => {
        const fetchLastActa = async () => {
            if (!selectedCourse) return;
            try {
                const response = await fetch(apiUrl(`/courses/${selectedCourse.id}/formal/last-acta`), {
                    headers: { Authorization: `Bearer ${token}` }
                });
                if (response.ok) {
                    const data = await response.json();
                    setLastActa(data);
                }
            } catch (error) {
                setLastActa(null);
            }
        };

        if (selectedCourse) fetchLastActa();
    }, [selectedCourse, token]);

    const handleCloseActa = async () => {
        if (!selectedCourse) return;
        
        const confirm = window.confirm(`¿Estás seguro de cerrar el acta para ${selectedCourse.title}? Esto procesará calificaciones y certificados.`);
        if (!confirm) return;

        setClosing(true);
        try {
            const response = await fetch(apiUrl(`/courses/${selectedCourse.id}/formal/close-acta`), {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({
                    min_grade: minGrade,
                    min_attendance: minAttendance
                }),
            });

            if (response.ok) {
                addToast("Acta cerrada y procesada con éxito", "success");
                const data = await response.json();
                setLastActa(data);
            } else {
                const err = await response.json();
                addToast(err.detail || "Error al cerrar acta", "error");
            }
        } catch (error) {
            addToast("Error de conexión", "error");
        } finally {
            setClosing(false);
        }
    };

    if (loading) return <div className="flex justify-center py-20"><Loader2 className="animate-spin text-primary w-8 h-8" /></div>;

    return (
        <div className="space-y-6 animate-in fade-in duration-500 max-w-5xl mx-auto">
            <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                <div>
                    <h1 className="flex items-center gap-3 text-3xl font-black text-slate-900 dark:text-white tracking-tight">
                        <CheckSquare className="text-primary" size={32} /> Gestión de Actas
                    </h1>
                    <p className="text-slate-500 font-medium mt-1">Cierre de ciclos académicos y emisión masiva de certificados (Ruta Formal).</p>
                </div>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Course Selection List */}
                <div className="lg:col-span-1 space-y-4">
                    <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-2">Cursos Formales</h3>
                    <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-white/5 rounded-3xl overflow-hidden shadow-sm">
                        {courses.length > 0 ? (
                            <div className="divide-y divide-slate-100 dark:divide-white/5">
                                {courses.map(course => (
                                    <button 
                                        key={course.id}
                                        onClick={() => setSelectedCourse(course)}
                                        className={`w-full text-left p-5 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors flex items-center justify-between group ${selectedCourse?.id === course.id ? 'bg-primary/5 dark:bg-primary/10' : ''}`}
                                    >
                                        <div className="min-w-0">
                                            <p className={`font-black text-sm truncate leading-tight mb-1 ${selectedCourse?.id === course.id ? 'text-primary' : 'text-slate-900 dark:text-white group-hover:text-primary'}`}>{course.title}</p>
                                            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{course.code}</p>
                                        </div>
                                        <ChevronRight size={16} className={`transition-transform ${selectedCourse?.id === course.id ? 'text-primary translate-x-1' : 'text-slate-300 group-hover:text-primary'}`} />
                                    </button>
                                ))}
                            </div>
                        ) : (
                            <div className="p-8 text-center text-slate-400 text-sm font-medium italic">No hay cursos registrados</div>
                        )}
                    </div>
                </div>

                {/* Acta Action Panel */}
                <div className="lg:col-span-2 space-y-6">
                    {selectedCourse ? (
                        <>
                            <div className="glass dark:bg-slate-800/40 border border-slate-200 dark:border-white/5 rounded-[2.5rem] p-8 shadow-sm relative overflow-hidden">
                                {/* Decorative gradient */}
                                <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 pointer-events-none"></div>

                                <div className="relative z-10">
                                    <div className="flex items-start justify-between mb-8">
                                        <div className="flex items-center gap-4">
                                            <div className="size-16 bg-primary/10 rounded-2xl text-primary flex items-center justify-center border border-primary/20 shadow-inner">
                                                <School size={32} />
                                            </div>
                                            <div>
                                                <h2 className="text-2xl font-black text-slate-900 dark:text-white leading-tight mb-1">{selectedCourse.title}</h2>
                                                <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Configuración de Cierre</p>
                                            </div>
                                        </div>
                                        {lastActa && (
                                            <div className="bg-emerald-500/10 text-emerald-500 px-4 py-2 rounded-xl text-[10px] font-bold uppercase tracking-widest border border-emerald-500/20 flex items-center gap-2">
                                                <CheckCircle2 size={14} /> Acta Cerrada
                                            </div>
                                        )}
                                    </div>

                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                                        <div className="space-y-2">
                                            <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 ml-1">Nota Mínima (%)</label>
                                            <div className="relative">
                                                <input 
                                                    type="number" 
                                                    value={minGrade}
                                                    onChange={(e) => setMinGrade(Number(e.target.value))}
                                                    className="w-full pl-4 pr-10 py-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-xl focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all font-black text-slate-900 dark:text-white shadow-sm"
                                                />
                                                <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 font-bold">%</span>
                                            </div>
                                        </div>
                                        <div className="space-y-2">
                                            <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 ml-1">Asistencia Mínima (%)</label>
                                            <div className="relative">
                                                <input 
                                                    type="number" 
                                                    value={minAttendance}
                                                    onChange={(e) => setMinAttendance(Number(e.target.value))}
                                                    className="w-full pl-4 pr-10 py-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-xl focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all font-black text-slate-900 dark:text-white shadow-sm"
                                                />
                                                <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 font-bold">%</span>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="bg-amber-500/10 border border-amber-500/20 rounded-2xl p-5 flex items-start gap-4 mb-8">
                                        <AlertTriangle className="text-amber-500 shrink-0 mt-0.5" />
                                        <div className="text-sm">
                                            <p className="font-bold text-amber-600 mb-1">Impacto del Cierre</p>
                                            <p className="text-amber-600/80 leading-relaxed font-medium">
                                                El sistema evaluará a todos los inscritos. Aquellos que cumplan los requisitos serán marcados como <strong>Aprobados</strong> y se les generará su certificado automáticamente.
                                            </p>
                                        </div>
                                    </div>

                                    <button 
                                        onClick={handleCloseActa}
                                        disabled={closing}
                                        className="w-full py-4 bg-primary text-white rounded-2xl font-black uppercase tracking-[0.2em] text-xs hover:bg-primary/90 transition-all flex items-center justify-center gap-3 shadow-xl shadow-primary/30 disabled:opacity-70 active:scale-95"
                                    >
                                        {closing ? <Loader2 className="animate-spin" /> : <ShieldCheck size={20} />}
                                        {closing ? "Procesando Cierre..." : "Cerrar Acta y Certificar"}
                                    </button>
                                </div>
                            </div>

                            {lastActa && (
                                <div className="glass dark:bg-slate-800/40 border border-slate-200 dark:border-white/5 rounded-[2rem] p-6 shadow-sm">
                                    <div className="flex items-center gap-3 mb-6">
                                        <div className="p-2 bg-slate-100 dark:bg-white/5 rounded-xl text-slate-500">
                                            <History size={16} />
                                        </div>
                                        <h3 className="font-bold text-slate-900 dark:text-white">Historial Reciente</h3>
                                    </div>
                                    <div className="text-sm space-y-4">
                                        <div className="flex justify-between items-center py-3 border-b border-slate-100 dark:border-white/5">
                                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Fecha de Cierre</span>
                                            <span className="font-black text-slate-900 dark:text-white">{new Date(lastActa.created_at).toLocaleString()}</span>
                                        </div>
                                        <div className="flex justify-between items-center py-3 border-b border-slate-100 dark:border-white/5">
                                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Requisito Nota</span>
                                            <span className="font-black text-slate-900 dark:text-white bg-slate-100 dark:bg-white/5 px-3 py-1 rounded-lg">{lastActa.min_grade}%</span>
                                        </div>
                                        <div className="flex justify-between items-center py-3">
                                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Requisito Asistencia</span>
                                            <span className="font-black text-slate-900 dark:text-white bg-slate-100 dark:bg-white/5 px-3 py-1 rounded-lg">{lastActa.min_attendance}%</span>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </>
                    ) : (
                        <div className="bg-slate-50 dark:bg-slate-900/30 border border-dashed border-slate-200 dark:border-white/10 rounded-[3rem] h-[400px] flex flex-col items-center justify-center text-center p-8">
                            <div className="size-20 bg-white dark:bg-slate-800 rounded-full shadow-sm mb-6 text-slate-300 flex items-center justify-center border border-slate-100 dark:border-white/5">
                                <BookOpen size={40} />
                            </div>
                            <h3 className="text-xl font-bold text-slate-700 dark:text-slate-200 mb-2">Selecciona un Curso</h3>
                            <p className="text-sm text-slate-500 font-medium max-w-xs leading-relaxed">
                                Elige un curso de la lista para gestionar su acta de cierre y emisión de certificados.
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
