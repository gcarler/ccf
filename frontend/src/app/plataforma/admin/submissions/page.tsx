"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { 
    FileText,
    Download,
    Clock,
    User,
    BookOpen,
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
            const response = await apiFetch<Submission[]>('/academy/admin/submissions?limit=100', {
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
            await apiFetch(`/academy/admin/submissions/${id}/grade?grade=${grade}&feedback=${encodeURIComponent(feedback)}`, {
                method: "PATCH",
                token,
            });
            addToast("Calificación guardada", "success");
            setGradingId(null);
            fetchSubmissions();
        } catch (error) {
            addToast("Error de conexión", "error");
        }
    };

    if (loading) return <div className="flex justify-center py-1.5"><Loader2 className="animate-spin text-primary w-8 h-8" /></div>;

    return (
 <div className="space-y-3 animate-in fade-in duration-500 w-full">
            <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-3">
                <div>
                    <h1 className="flex items-center gap-3 text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight">
                        <FileText className="text-primary" size={32} /> Calificar Trabajos
                    </h1>
                    <p className="text-[hsl(var(--text-secondary))] font-medium mt-1">Revisa y califica las evidencias enviadas por los participantes.</p>
                </div>
            </header>

            <div className="grid grid-cols-1 gap-3">
                {submissions.length > 0 ? (
                    submissions.map(sub => (
                        <div key={sub.id} className="glass dark:bg-[hsl(var(--surface-2))]/40 rounded-lg p-3 shadow-sm flex flex-col md:flex-row justify-between gap-3 border border-[hsl(var(--border))] dark:border-white/5 transition-transform hover:shadow-md">
                            <div className="flex flex-col md:flex-row justify-between gap-3 w-full">
                                <div className="flex-1 space-y-4">
                                    <div className="flex items-center gap-4">
                                        <div className="size-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary border border-primary/20">
                                            <User size={24} />
                                        </div>
                                        <div>
                                            <p className="font-semibold text-[hsl(var(--text-primary))] dark:text-white text-base leading-none mb-1">{sub.student_name}</p>
                                            <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide flex items-center gap-1">
                                                <Clock size={10} /> {new Date(sub.submitted_at).toLocaleString()}
                                            </p>
                                        </div>
                                    </div>

                                    <div className="space-y-2">
                                        <p className="text-xs font-semibold uppercase tracking-wide text-primary flex items-center gap-1">
                                            <BookOpen size={14} /> {sub.lesson_title}
                                        </p>
                                        {sub.comment && (
                                            <p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-1))] dark:bg-[hsl(var(--bg-muted))]/50 p-4 rounded-lg italic font-medium border border-[hsl(var(--border))] dark:border-white/5">
                                                &quot;{sub.comment}&quot;
                                            </p>
                                        )}
                                    </div>

                                    <a 
                                        href={`${apiUrl('')}${sub.file_url}`} 
                                        target="_blank" 
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center gap-2 px-3 py-3 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 rounded-md text-xs font-bold hover:bg-emerald-500/20 transition-colors border border-emerald-500/20"
                                    >
                                        <Download size={16} /> Descargar Documento <ExternalLink size={14} />
                                    </a>
                                </div>

                                <div className="w-full md:w-80 bg-[hsl(var(--surface-1))] dark:bg-[hsl(var(--bg-muted))]/50 rounded-lg p-3 border border-[hsl(var(--border))] dark:border-white/5 flex flex-col justify-center">
                                    {gradingId === sub.id ? (
                                        <div className="space-y-4 animate-in zoom-in-95 duration-200">
                                            <div>
                                                <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Nota (0-100)</label>
                                                <input 
                                                    type="number" 
                                                    value={grade}
                                                    onChange={(e) => setGrade(Number(e.target.value))}
                                                    className="w-full px-4 py-3 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] dark:border-white/10 rounded-md focus:ring-2 focus:ring-primary/50 outline-none font-bold text-[hsl(var(--text-primary))] dark:text-white transition-all shadow-sm"
                                                />
                                            </div>
                                            <div>
                                                <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Retroalimentación</label>
                                                <textarea 
                                                    value={feedback}
                                                    onChange={(e) => setFeedback(e.target.value)}
                                                    placeholder="Buen trabajo..."
                                                    className="w-full px-4 py-3 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] dark:border-white/10 rounded-md focus:ring-2 focus:ring-primary/50 outline-none text-sm h-24 resize-none text-[hsl(var(--text-primary))] dark:text-white transition-all shadow-sm"
                                                />
                                            </div>
                                            <div className="flex gap-2 pt-2">
                                                <button 
                                                    onClick={() => handleGrade(sub.id)}
                                                    className="flex-1 py-3 bg-primary text-white rounded-md text-xs font-bold uppercase tracking-wide hover:bg-primary/90 transition-all shadow-lg shadow-primary/20 active:scale-95"
                                                >
                                                    Guardar
                                                </button>
                                                <button 
                                                    onClick={() => setGradingId(null)}
                                                    className="px-4 py-3 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] rounded-md text-xs font-bold hover:text-[hsl(var(--text-primary))] dark:hover:text-white transition-all active:scale-95 shadow-sm"
                                                >
                                                    <X size={16} />
                                                </button>
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="text-center space-y-4">
                                            {sub.grade !== null ? (
                                                <div className="flex flex-col items-center gap-3">
                                                    <div className="p-4 bg-emerald-500/10 text-emerald-500 dark:text-emerald-400 rounded-lg border border-emerald-500/20 shadow-sm">
                                                        <p className="text-[10px] font-semibold uppercase tracking-wide mb-1">Calificación</p>
                                                        <p className="text-lg font-bold leading-none">{sub.grade}</p>
                                                    </div>
                                                    {sub.teacher_feedback && (
                                                        <p className="text-xs text-[hsl(var(--text-secondary))] font-medium italic px-2 bg-white/50 dark:bg-white/5 p-3 rounded-md border border-[hsl(var(--border))] dark:border-white/5 w-full">&ldquo;{sub.teacher_feedback}&rdquo;</p>
                                                    )}
                                                    <button 
                                                        onClick={() => {
                                                            setGradingId(sub.id);
                                                            setGrade(sub.grade || 0);
                                                            setFeedback(sub.teacher_feedback || '');
                                                        }}
                                                        className="w-full py-3 text-[10px] font-bold text-primary uppercase tracking-wide hover:bg-primary/5 rounded-md transition-all border border-transparent hover:border-primary/10"
                                                    >
                                                        Modificar Nota
                                                    </button>
                                                </div>
                                            ) : (
                                                <div className="flex flex-col items-center justify-center h-full gap-4">
                                                    <div className="p-4 bg-amber-500/10 text-amber-500 rounded-full border border-amber-500/20 shadow-sm">
                                                        <AlertCircle size={32} />
                                                    </div>
                                                    <p className="text-xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Pendiente de Revisión</p>
                                                    <button 
                                                        onClick={() => {
                                                            setGradingId(sub.id);
                                                            setGrade(0);
                                                            setFeedback('');
                                                        }}
                                                        className="w-full py-1.5 mt-2 bg-primary text-white rounded-lg text-xs font-bold uppercase tracking-wide shadow-lg shadow-primary/30 hover:bg-primary/90 transition-all active:scale-95"
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
                    <div className="bg-[hsl(var(--surface-1))] dark:bg-[hsl(var(--bg-muted))]/30 border border-dashed border-[hsl(var(--border))] dark:border-white/10 rounded-lg py-1.5 text-center flex flex-col items-center">
                        <div className="size-8 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] rounded-full shadow-sm flex items-center justify-center text-[hsl(var(--text-secondary))] mb-3 border border-[hsl(var(--border))] dark:border-white/5">
                            <FileText size={40} />
                        </div>
                        <h3 className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] mb-2">Todo al día</h3>
                        <p className="text-sm text-[hsl(var(--text-secondary))] font-medium">No hay entregas pendientes por revisar en este momento.</p>
                    </div>
                )}
            </div>
        </div>
    );
}

