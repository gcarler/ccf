"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { 
    CheckCircle2, 
    AlertCircle, 
    ArrowRight, 
    ArrowLeft, 
    Loader2, 
    Trophy,
    Clock,
    Layout,
    GraduationCap,
    HelpCircle
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

interface Enrollment {
    id: number;
    course: { id: number };
}

export default function AssessmentPage() {
    const params = useParams();
    const id = (params?.id as string) ?? '';
    const { token, user } = useAuth();
    const router = useRouter();
    const [assessment, setAssessment] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [answers, setAnswers] = useState<any[]>([]);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [result, setResult] = useState<any>(null);
    const [currentStep, setCurrentStep] = useState(0);

    useEffect(() => {
        const fetchAssessment = async () => {
            if (!token || !id) return;
            try {
                const data = await apiFetch<any>(`/academy/assessments/${id}`, { token });
                setAssessment(data);
            } catch (err) {
                console.error("Error fetching assessment:", err);
            } finally {
                setLoading(false);
            }
        };
        fetchAssessment();
    }, [id, token]);

    const handleSelectOption = (questionId: number, optionId: number) => {
        setAnswers(prev => {
            const filtered = prev.filter(a => a.question_id !== questionId);
            return [...filtered, { question_id: questionId, selected_option_id: optionId }];
        });
    };

    const handleSubmit = async () => {
        if (!token || !user?.id) return;
        setIsSubmitting(true);
        try {
            const enrollments = await apiFetch<Enrollment[]>(`/users/${user.id}/enrollments`, { token });
            const enrollment = enrollments.find((e: Enrollment) => e.course.id === assessment.course_id);
            
            if (!enrollment) {
                alert("No estás inscrito en este curso.");
                return;
            }

            const data = await apiFetch<any>(`/academy/assessments/${id}/submit`, {
                method: 'POST',
                token,
                body: {
                    enrollment_id: enrollment.id,
                    answers: answers
                }
            });
            setResult(data);
        } catch (err) {
            console.error("Failed to submit assessment:", err);
        } finally {
            setIsSubmitting(false);
        }
    };

    if (loading) return <div className="h-full flex items-center justify-center"><Loader2 className="animate-spin text-blue-500" /></div>;
    if (!assessment) return <div className="p-10 text-center">Evaluación no encontrada.</div>;

    if (result) {
        return (
            <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden">
                <WorkspaceToolbar 
                    breadcrumbs={[
                        { label: 'Academia', icon: GraduationCap },
                        { label: 'Resultado', icon: Trophy }
                    ]}
                    viewType="grid"
                    setViewType={() => {}}
                />
                <main className="flex-1 overflow-y-auto flex items-center justify-center p-6">
                    <motion.div 
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="max-w-md w-full text-center space-y-8 p-10 bg-slate-50 dark:bg-white/5 rounded-3xl border border-slate-200 dark:border-white/5 shadow-xl"
                    >
                        <div className={clsx(
                            "size-20 rounded-full mx-auto flex items-center justify-center shadow-lg",
                            result.passed ? "bg-emerald-500 text-white shadow-emerald-500/20" : "bg-rose-500 text-white shadow-rose-500/20"
                        )}>
                            {result.passed ? <Trophy size={40} /> : <AlertCircle size={40} />}
                        </div>
                        <div>
                            <h2 className="text-3xl font-black mb-2">{result.passed ? '¡Felicitaciones!' : 'Sigue intentando'}</h2>
                            <p className="text-slate-500 dark:text-slate-400 font-medium">Has completado la evaluación de {assessment.title}</p>
                        </div>
                        <div className="py-6 border-y border-slate-200 dark:border-white/5">
                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Tu Puntaje</p>
                            <span className="text-5xl font-black tracking-tighter">{Math.round(result.submitted_score)}%</span>
                        </div>
                        <div className="space-y-3">
                            <button 
                                onClick={() => router.push('/academy')}
                                className="w-full py-4 bg-blue-600 text-white rounded-2xl font-black text-sm uppercase tracking-widest shadow-lg shadow-blue-500/20 active:scale-95 transition-all"
                            >
                                Volver a la Academia
                            </button>
                            {!result.passed && (
                                <button 
                                    onClick={() => window.location.reload()}
                                    className="w-full py-4 text-slate-500 font-bold text-sm uppercase tracking-widest hover:text-slate-700 transition-colors"
                                >
                                    Reintentar Evaluación
                                </button>
                            )}
                        </div>
                    </motion.div>
                </main>
            </div>
        );
    }

    const currentQuestion = assessment.questions[currentStep];
    const isLastStep = currentStep === assessment.questions.length - 1;

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden">
            <WorkspaceToolbar 
                breadcrumbs={[
                    { label: 'Academia', icon: GraduationCap },
                    { label: assessment.title, icon: HelpCircle }
                ]}
                viewType="grid"
                setViewType={() => {}}
                rightActions={
                    <div className="flex items-center gap-3 px-3 py-1 bg-slate-100 dark:bg-white/5 rounded-full text-[11px] font-bold text-slate-500">
                        <Clock size={14} /> 45:00
                    </div>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-6 lg:p-12">
                <div className="max-w-3xl mx-auto space-y-12">
                    {/* Progress Header */}
                    <div className="space-y-4">
                        <div className="flex justify-between items-end">
                            <div>
                                <p className="text-[10px] font-black text-blue-500 uppercase tracking-widest mb-1">Pregunta {currentStep + 1} de {assessment.questions.length}</p>
                                <h3 className="text-2xl font-black text-slate-800 dark:text-white tracking-tight leading-tight">
                                    {currentQuestion.question_text}
                                </h3>
                            </div>
                            <span className="text-[12px] font-black text-slate-400 shrink-0">{Math.round(((currentStep + 1) / assessment.questions.length) * 100)}%</span>
                        </div>
                        <div className="h-1.5 w-full bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
                            <motion.div 
                                className="h-full bg-blue-600"
                                initial={{ width: 0 }}
                                animate={{ width: `${((currentStep + 1) / assessment.questions.length) * 100}%` }}
                            />
                        </div>
                    </div>

                    {/* Options Grid */}
                    <div className="grid grid-cols-1 gap-4">
                        <AnimatePresence mode="wait">
                            <motion.div 
                                key={currentQuestion.id}
                                initial={{ x: 20, opacity: 0 }}
                                animate={{ x: 0, opacity: 1 }}
                                exit={{ x: -20, opacity: 0 }}
                                className="space-y-4"
                            >
                                {currentQuestion.options.map((option: any) => (
                                    <button
                                        key={option.id}
                                        onClick={() => handleSelectOption(currentQuestion.id, option.id)}
                                        className={clsx(
                                            "w-full p-6 text-left rounded-3xl border-2 transition-all group relative overflow-hidden",
                                            answers.find(a => a.selected_option_id === option.id)
                                                ? "border-blue-600 bg-blue-50/50 dark:bg-blue-500/10 shadow-lg shadow-blue-500/5"
                                                : "border-slate-100 dark:border-white/5 hover:border-blue-200 dark:hover:border-white/10 bg-white dark:bg-[#1e1f21]"
                                        )}
                                    >
                                        <div className="flex items-center gap-4 relative z-10">
                                            <div className={clsx(
                                                "size-6 rounded-full border-2 flex items-center justify-center shrink-0 transition-all",
                                                answers.find(a => a.selected_option_id === option.id)
                                                    ? "border-blue-600 bg-blue-600 text-white"
                                                    : "border-slate-200 dark:border-white/10"
                                            )}>
                                                {answers.find(a => a.selected_option_id === option.id) && <CheckCircle2 size={14} />}
                                            </div>
                                            <span className="text-[15px] font-bold text-slate-700 dark:text-slate-200">{option.option_text}</span>
                                        </div>
                                    </button>
                                ))}
                            </motion.div>
                        </AnimatePresence>
                    </div>

                    {/* Navigation Actions */}
                    <div className="flex items-center justify-between pt-12 border-t border-slate-100 dark:border-white/5">
                        <button 
                            disabled={currentStep === 0}
                            onClick={() => setCurrentStep(prev => prev - 1)}
                            className="flex items-center gap-2 text-[12px] font-black uppercase tracking-widest text-slate-400 hover:text-slate-600 disabled:opacity-0 transition-all"
                        >
                            <ArrowLeft size={16} /> Anterior
                        </button>

                        {isLastStep ? (
                            <button 
                                onClick={handleSubmit}
                                disabled={isSubmitting || answers.length < assessment.questions.length}
                                className="px-10 py-4 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-2xl font-black text-sm uppercase tracking-widest shadow-xl active:scale-95 transition-all disabled:opacity-50"
                            >
                                {isSubmitting ? 'Enviando...' : 'Finalizar Evaluación'}
                            </button>
                        ) : (
                            <button 
                                onClick={() => setCurrentStep(prev => prev + 1)}
                                disabled={!answers.find(a => a.question_id === currentQuestion.id)}
                                className="px-10 py-4 bg-blue-600 text-white rounded-2xl font-black text-sm uppercase tracking-widest shadow-lg shadow-blue-500/20 active:scale-95 transition-all disabled:opacity-50 flex items-center gap-2"
                            >
                                Siguiente <ArrowRight size={16} />
                            </button>
                        )}
                    </div>
                </div>
            </main>
        </div>
    );
}
