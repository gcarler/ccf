"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { 
    FileText, 
    Download, 
    CheckCircle2, 
    Clock, 
    User, 
    BookOpen, 
    Search,
    Loader2,
    ExternalLink,
    AlertCircle,
    X
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiUrl } from '@/lib/api';
import { apiFetch } from '@/lib/http';
import { useToast } from '@/context/ToastContext';

interface Submission {
    id: number;
    student_name: string;
    lesson_title: string;
    file_url: string;
    comment: string | null;
    grade: number | null;
    teacher_feedback: string | null;
    submitted_at: string;
}

export default function SubmissionsPage() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const [submissions, setSubmissions] = useState<Submission[]>([]);
    const [loading, setLoading] = useState(true);
    const [gradingId, setGradingId] = useState<number | null>(null);
    const [grade, setGrade] = useState<number>(0);
    const [feedback, setFeedback] = useState<string>('');

    const fetchSubmissions = useCallback(async () => {
        try {
            const response = await apiFetch<Submission[]>('/admin/submissions', {
                token,
                cache: 'no-store'
            });
            setSubmissions(Array.isArray(response) ? response : []);
        } catch (error) {
            addToast("Error al cargar entregas", "error");
        } finally {
            setLoading(false);
        }
    }, [token, addToast]);

    useEffect(() => {
        if (token) fetchSubmissions();
    }, [token, fetchSubmissions]);

    const handleGrade = async (id: number) => {
        try {
            await apiFetch(`/admin/submissions/${id}/grade`, {
                method: "PATCH",
                token,
                query: {
                    grade,
                    feedback,
                }
            });
            addToast("Calificación guardada", "success");
            setGradingId(null);
            fetchSubmissions();
        } catch (error) {
            addToast("Error de conexión", "error");
        }
    };

    if (loading) return <div className="flex justify-center py-20"><Loader2 className="animate-spin text-primary w-8 h-8" /></div>;

    return (
        <div className="space-y-6 animate-in fade-in duration-500 max-w-5xl mx-auto">
            <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                <div>
                    <h1 className="flex items-center gap-3 text-3xl font-black text-slate-900 dark:text-white tracking-tight">
                        <FileText className="text-primary" size={32} /> Calificar Trabajos
                    </h1>
                    <p className="text-slate-500 font-medium mt-1">Revisa y califica las evidencias enviadas por los estudiantes.</p>
                </div>
            </header>

            <div className="grid grid-cols-1 gap-6">
                {submissions.length > 0 ? (
                    submissions.map(sub => (
                        <div key={sub.id} className="glass dark:bg-slate-800/40 rounded-[2rem] p-6 shadow-sm flex flex-col md:flex-row justify-between gap-6 border border-slate-200 dark:border-white/5 transition-transform hover:shadow-md">
                            <div className="flex flex-col md:flex-row justify-between gap-6 w-full">
                                <div className="flex-1 space-y-4">
                                    <div className="flex items-center gap-4">
                                        <div className="size-14 rounded-2xl bg-primary/10 flex items-center justify-center text-primary border border-primary/20">
                                            <User size={24} />
                                        </div>
                                        <div>
                                            <p className="font-black text-slate-900 dark:text-white text-base leading-none mb-1">{sub.student_name}</p>
                                            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-1">
                                                <Clock size={10} /> {new Date(sub.submitted_at).toLocaleString()}
                                            </p>
                                        </div>
                                    </div>

                                    <div className="space-y-2">
                                        <p className="text-xs font-black uppercase tracking-widest text-primary flex items-center gap-1">
                                            <BookOpen size={14} /> {sub.lesson_title}
                                        </p>
                                        {sub.comment && (
                                            <p className="text-sm text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-900/50 p-4 rounded-2xl italic font-medium border border-slate-100 dark:border-white/5">
                                                &quot;{sub.comment}&quot;
                                            </p>
                                        )}
                                    </div>

                                    <a 
                                        href={`${apiUrl('')}${sub.file_url}`} 
                                        target="_blank" 
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center gap-2 px-6 py-3 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 rounded-xl text-xs font-bold hover:bg-emerald-500/20 transition-colors border border-emerald-500/20"
                                    >
                                        <Download size={16} /> Descargar Documento <ExternalLink size={14} />
                                    </a>
                                </div>

                                <div className="w-full md:w-80 bg-slate-50 dark:bg-slate-900/50 rounded-3xl p-6 border border-slate-100 dark:border-white/5 flex flex-col justify-center">
                                    {gradingId === sub.id ? (
                                        <div className="space-y-4 animate-in zoom-in-95 duration-200">
                                            <div>
                                                <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 block">Nota (0-100)</label>
                                                <input 
                                                    type="number" 
                                                    value={grade}
                                                    onChange={(e) => setGrade(Number(e.target.value))}
                                                    className="w-full px-4 py-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-white/10 rounded-xl focus:ring-2 focus:ring-primary/50 outline-none font-bold text-slate-900 dark:text-white transition-all shadow-sm"
                                                />
                                            </div>
                                            <div>
                                                <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 block">Retroalimentación</label>
                                                <textarea 
                                                    value={feedback}
                                                    onChange={(e) => setFeedback(e.target.value)}
                                                    placeholder="Buen trabajo..."
                                                    className="w-full px-4 py-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-white/10 rounded-xl focus:ring-2 focus:ring-primary/50 outline-none text-sm h-24 resize-none text-slate-900 dark:text-white transition-all shadow-sm"
                                                />
                                            </div>
                                            <div className="flex gap-2 pt-2">
                                                <button 
                                                    onClick={() => handleGrade(sub.id)}
                                                    className="flex-1 py-3 bg-primary text-white rounded-xl text-xs font-bold uppercase tracking-widest hover:bg-primary/90 transition-all shadow-lg shadow-primary/20 active:scale-95"
                                                >
                                                    Guardar
                                                </button>
                                                <button 
                                                    onClick={() => setGradingId(null)}
                                                    className="px-4 py-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-white/10 text-slate-500 rounded-xl text-xs font-bold hover:text-slate-700 dark:hover:text-white transition-all active:scale-95 shadow-sm"
                                                >
                                                    <X size={16} />
                                                </button>
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="text-center space-y-4">
                                            {sub.grade !== null ? (
                                                <div className="flex flex-col items-center gap-3">
                                                    <div className="p-4 bg-emerald-500/10 text-emerald-500 dark:text-emerald-400 rounded-3xl border border-emerald-500/20 shadow-sm">
                                                        <p className="text-[10px] font-black uppercase tracking-[0.2em] mb-1">Calificación</p>
                                                        <p className="text-4xl font-black leading-none">{sub.grade}</p>
                                                    </div>
                                                    {sub.teacher_feedback && (
                                                        <p className="text-xs text-slate-500 font-medium italic px-2 bg-white/50 dark:bg-white/5 p-3 rounded-xl border border-slate-200 dark:border-white/5 w-full">&ldquo;{sub.teacher_feedback}&rdquo;</p>
                                                    )}
                                                    <button 
                                                        onClick={() => {
                                                            setGradingId(sub.id);
                                                            setGrade(sub.grade || 0);
                                                            setFeedback(sub.teacher_feedback || '');
                                                        }}
                                                        className="w-full py-3 text-[10px] font-bold text-primary uppercase tracking-widest hover:bg-primary/5 rounded-xl transition-all border border-transparent hover:border-primary/10"
                                                    >
                                                        Modificar Nota
                                                    </button>
                                                </div>
                                            ) : (
                                                <div className="flex flex-col items-center justify-center h-full gap-4">
                                                    <div className="p-4 bg-amber-500/10 text-amber-500 rounded-full border border-amber-500/20 shadow-sm">
                                                        <AlertCircle size={32} />
                                                    </div>
                                                    <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">Pendiente de Revisión</p>
                                                    <button 
                                                        onClick={() => {
                                                            setGradingId(sub.id);
                                                            setGrade(0);
                                                            setFeedback('');
                                                        }}
                                                        className="w-full py-4 mt-2 bg-primary text-white rounded-2xl text-xs font-bold uppercase tracking-[0.2em] shadow-lg shadow-primary/30 hover:bg-primary/90 transition-all active:scale-95"
                                                    >
                                                        Calificar
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))
                ) : (
                    <div className="bg-slate-50 dark:bg-slate-900/30 border border-dashed border-slate-200 dark:border-white/10 rounded-[3rem] py-24 text-center flex flex-col items-center">
                        <div className="size-20 bg-white dark:bg-slate-800 rounded-full shadow-sm flex items-center justify-center text-slate-300 mb-6 border border-slate-100 dark:border-white/5">
                            <FileText size={40} />
                        </div>
                        <h3 className="text-xl font-bold text-slate-700 dark:text-slate-200 mb-2">Todo al día</h3>
                        <p className="text-sm text-slate-500 font-medium">No hay entregas pendientes por revisar en este momento.</p>
                    </div>
                )}
            </div>
        </div>
    );
}
