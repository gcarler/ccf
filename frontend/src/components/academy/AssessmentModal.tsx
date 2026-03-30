"use client";

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    X, CheckCircle2, AlertCircle, Loader2, 
    ArrowRight, ArrowLeft, Trophy, Sparkles,
    ShieldCheck, HelpCircle
} from 'lucide-react';
import { apiFetch } from '@/lib/http';
import clsx from 'clsx';

interface Option {
    id: number;
    option_text: str;
}

interface Question {
    id: number;
    question_text: string;
    question_type: string;
    points: number;
    options: Option[];
}

interface Assessment {
    id: number;
    title: string;
    min_score: number;
    questions: Question[];
}

interface AssessmentModalProps {
    assessmentId: number;
    enrollmentId: number;
    token: string;
    onClose: () => void;
    onSuccess: (score: number) => void;
}

export default function AssessmentModal({ assessmentId, enrollmentId, token, onClose, onSuccess }: AssessmentModalProps) {
    const [assessment, setAssessment] = useState<Assessment | null>(null);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [currentStep, setCurrentStep] = useState(0); // 0: Welcome, 1..N: Questions, N+1: Result
    const [answers, setAnswers] = useState<Record<number, number>>({});
    const [result, setResult] = useState<{ passed: boolean, score: number } | null>(null);

    useEffect(() => {
        const fetchAssessment = async () => {
            try {
                const data = await apiFetch<Assessment>(`/academy/assessments/${assessmentId}`, { token });
                setAssessment(data);
            } catch (err) {
                console.error("Error fetching assessment", err);
            } finally {
                setLoading(false);
            }
        };
        fetchAssessment();
    }, [assessmentId, token]);

    const handleSelectOption = (questionId: number, optionId: number) => {
        setAnswers(prev => ({ ...prev, [questionId]: optionId }));
    };

    const handleSubmit = async () => {
        setSubmitting(true);
        try {
            const formattedAnswers = Object.entries(answers).map(([qId, oId]) => ({
                question_id: parseInt(qId),
                selected_option_id: oId
            }));

            const res = await apiFetch<any>(`/academy/assessments/${assessmentId}/submit`, {
                method: 'POST',
                token,
                body: {
                    enrollment_id: enrollmentId,
                    answers: formattedAnswers
                }
            });

            setResult({ passed: res.passed, score: res.score });
            if (res.passed) {
                onSuccess(res.score);
            }
        } catch (err) {
            console.error("Error submitting assessment", err);
        } finally {
            setSubmitting(false);
        }
    };

    const nextStep = () => {
        if (assessment && currentStep <= assessment.questions.length) {
            setCurrentStep(currentStep + 1);
        }
    };

    const prevStep = () => {
        if (currentStep > 0) {
            setCurrentStep(currentStep - 1);
        }
    };

    if (loading) return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-slate-950/80 backdrop-blur-xl">
            <Loader2 className="w-10 h-10 animate-spin text-blue-500" />
        </div>
    );

    if (!assessment) return null;

    const questions = assessment.questions || [];
    const isLastQuestion = currentStep === questions.length;
    const isWelcome = currentStep === 0;
    const isResult = result !== null;

    return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 lg:p-10 bg-slate-950/90 backdrop-blur-2xl overflow-hidden font-sans">
            <div className="absolute inset-0 z-0">
                <div className="absolute top-0 right-0 size-[600px] bg-blue-600/10 rounded-full blur-[120px]" />
                <div className="absolute bottom-0 left-0 size-[500px] bg-indigo-600/10 rounded-full blur-[100px]" />
            </div>

            <motion.div 
                initial={{ opacity: 0, scale: 0.9, y: 20 }} animate={{ opacity: 1, scale: 1, y: 0 }}
                className="relative z-10 w-full max-w-4xl bg-white dark:bg-[#15171c] rounded-[3.5rem] border border-slate-100 dark:border-white/10 shadow-2xl overflow-hidden flex flex-col h-full max-h-[800px]"
            >
                {/* Header */}
                <div className="p-8 border-b border-slate-50 dark:border-white/5 flex items-center justify-between shrink-0">
                    <div className="flex items-center gap-4">
                        <div className="size-12 rounded-2xl bg-blue-50 dark:bg-blue-500/10 flex items-center justify-center text-blue-600 shadow-inner">
                            <Sparkles size={24} />
                        </div>
                        <div>
                            <h2 className="text-xl font-black text-slate-800 dark:text-white tracking-tight">{assessment.title}</h2>
                            <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Validación Ministerial MESH</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-3 hover:bg-slate-100 dark:hover:bg-white/5 rounded-full transition-all text-slate-400"><X size={24} /></button>
                </div>

                {/* Progress Bar (if not welcome/result) */}
                {!isWelcome && !isResult && (
                    <div className="h-1.5 w-full bg-slate-100 dark:bg-white/5 shrink-0">
                        <motion.div 
                            initial={{ width: 0 }} animate={{ width: `${(currentStep / questions.length) * 100}%` }}
                            className="h-full bg-blue-600 shadow-[0_0_10px_rgba(37,99,235,0.5)]" 
                        />
                    </div>
                )}

                {/* Content */}
                <div className="flex-1 overflow-y-auto scrollbar-thin p-8 lg:p-12 relative">
                    <AnimatePresence mode="wait">
                        {isResult ? (
                            <motion.div key="result" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="flex flex-col items-center justify-center h-full text-center space-y-8">
                                <div className={clsx(
                                    "size-32 rounded-[2.5rem] flex items-center justify-center shadow-2xl relative",
                                    result.passed ? "bg-emerald-500 text-white shadow-emerald-500/30" : "bg-rose-500 text-white shadow-rose-500/30"
                                )}>
                                    {result.passed ? <Trophy size={64} /> : <AlertCircle size={64} />}
                                    <motion.div 
                                        animate={{ scale: [1, 1.2, 1] }} transition={{ repeat: Infinity, duration: 2 }}
                                        className="absolute -top-4 -right-4 size-12 bg-white dark:bg-[#15171c] rounded-2xl flex items-center justify-center text-slate-800 dark:text-white shadow-xl border border-slate-50 dark:border-white/10"
                                    >
                                        <span className="text-sm font-black">{result.score}%</span>
                                    </motion.div>
                                </div>
                                <div className="space-y-3">
                                    <h3 className="text-4xl font-black text-slate-800 dark:text-white tracking-tighter">
                                        {result.passed ? '¡Felicidades, Siervo!' : 'Sigue Intentándolo'}
                                    </h3>
                                    <p className="text-slate-500 dark:text-slate-400 font-medium max-w-md mx-auto text-lg leading-relaxed">
                                        {result.passed 
                                            ? `Has aprobado el examen con un puntaje de ${result.score}%. Tu certificado ministerial ha sido generado y está disponible en tu panel.`
                                            : `Tu puntaje de ${result.score}% no alcanzó el mínimo de ${assessment.min_score}%. Revisa el material de estudio y vuelve a intentarlo.`}
                                    </p>
                                </div>
                                <div className="flex gap-4 pt-6">
                                    {result.passed ? (
                                        <button onClick={onClose} className="px-10 py-5 bg-blue-600 text-white rounded-3xl font-black uppercase tracking-[0.2em] shadow-xl shadow-blue-600/20 active:scale-95 transition-all">Continuar a mi Panel</button>
                                    ) : (
                                        <>
                                            <button onClick={onClose} className="px-8 py-5 border-2 border-slate-200 dark:border-white/10 rounded-3xl text-slate-500 font-black uppercase tracking-[0.2em] hover:bg-slate-50 transition-all">Cerrar</button>
                                            <button onClick={() => { setResult(null); setCurrentStep(0); setAnswers({}); }} className="px-10 py-5 bg-blue-600 text-white rounded-3xl font-black uppercase tracking-[0.2em] shadow-xl shadow-blue-600/20 active:scale-95 transition-all">Reintentar</button>
                                        </>
                                    )}
                                </div>
                            </motion.div>
                        ) : isWelcome ? (
                            <motion.div key="welcome" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="flex flex-col items-center justify-center h-full text-center space-y-8">
                                <div className="size-24 rounded-[2rem] bg-blue-50 dark:bg-blue-500/10 flex items-center justify-center text-blue-600 shadow-inner">
                                    <ShieldCheck size={48} />
                                </div>
                                <div className="space-y-3">
                                    <h3 className="text-3xl font-black text-slate-800 dark:text-white tracking-tight uppercase">Instrucciones de Evaluación</h3>
                                    <p className="text-slate-500 dark:text-slate-400 font-medium max-w-lg mx-auto text-base">
                                        Este examen consta de <span className="font-black text-blue-600">{questions.length} preguntas</span>. 
                                        Para aprobar, necesitas una nota mínima de <span className="font-black text-blue-600">{assessment.min_score}%</span>. 
                                        Asegúrate de estar en un lugar tranquilo antes de iniciar.
                                    </p>
                                </div>
                                <button onClick={nextStep} className="px-12 py-6 bg-blue-600 text-white rounded-3xl font-black uppercase tracking-[0.3em] shadow-xl shadow-blue-600/20 active:scale-95 transition-all flex items-center gap-4 group">
                                    Iniciar Examen <ArrowRight className="group-hover:translate-x-1 transition-transform" />
                                </button>
                            </motion.div>
                        ) : (
                            <motion.div 
                                key={currentStep} initial={{ opacity: 0, x: 50 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -50 }}
                                className="space-y-10"
                            >
                                <div className="space-y-4">
                                    <span className="text-[10px] font-black text-blue-600 uppercase tracking-[0.4em] bg-blue-50 dark:bg-blue-500/10 px-3 py-1 rounded-lg">Pregunta {currentStep} de {questions.length}</span>
                                    <h3 className="text-2xl lg:text-3xl font-black text-slate-800 dark:text-white leading-tight">
                                        {questions[currentStep - 1].question_text}
                                    </h3>
                                </div>

                                <div className="grid grid-cols-1 gap-4">
                                    {questions[currentStep - 1].options.map((option) => (
                                        <button 
                                            key={option.id}
                                            onClick={() => handleSelectOption(questions[currentStep - 1].id, option.id)}
                                            className={clsx(
                                                "w-full text-left p-6 rounded-[2rem] border-2 transition-all group flex items-center gap-6",
                                                answers[questions[currentStep - 1].id] === option.id 
                                                    ? "bg-blue-600 border-blue-600 text-white shadow-xl shadow-blue-600/20" 
                                                    : "bg-slate-50 dark:bg-white/5 border-slate-100 dark:border-white/5 text-slate-700 dark:text-slate-300 hover:border-blue-500/30 hover:bg-white dark:hover:bg-white/10 shadow-sm"
                                            )}
                                        >
                                            <div className={clsx(
                                                "size-8 rounded-xl flex items-center justify-center shrink-0 shadow-inner border transition-colors",
                                                answers[questions[currentStep - 1].id] === option.id 
                                                    ? "bg-white/20 border-white/30 text-white" 
                                                    : "bg-white dark:bg-[#15171c] border-slate-200 dark:border-white/10 text-slate-400 group-hover:border-blue-500/50"
                                            )}>
                                                {answers[questions[currentStep - 1].id] === option.id ? <CheckCircle2 size={18} /> : <HelpCircle size={18} />}
                                            </div>
                                            <span className="text-base font-bold tracking-tight">{option.option_text}</span>
                                        </button>
                                    ))}
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>

                {/* Footer Actions (Quiz Navigation) */}
                {!isWelcome && !isResult && (
                    <div className="p-8 border-t border-slate-50 dark:border-white/5 flex items-center justify-between shrink-0 bg-slate-50/50 dark:bg-black/20">
                        <button onClick={prevStep} className="flex items-center gap-2 px-6 py-4 text-slate-400 hover:text-slate-600 dark:hover:text-white transition-all font-black uppercase text-[10px] tracking-widest">
                            <ArrowLeft size={16} /> Anterior
                        </button>
                        
                        {isLastQuestion ? (
                            <button 
                                onClick={handleSubmit}
                                disabled={submitting || !answers[questions[currentStep - 1].id]}
                                className="px-10 py-4 bg-blue-600 text-white rounded-2xl font-black uppercase tracking-[0.2em] shadow-xl shadow-blue-600/20 active:scale-95 transition-all disabled:opacity-50 flex items-center gap-3"
                            >
                                {submitting ? <Loader2 className="animate-spin" size={18} /> : <>Finalizar Examen <Trophy size={18} /></>}
                            </button>
                        ) : (
                            <button 
                                onClick={nextStep}
                                disabled={!answers[questions[currentStep - 1].id]}
                                className="px-10 py-4 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-2xl font-black uppercase tracking-[0.2em] shadow-xl active:scale-95 transition-all disabled:opacity-50 flex items-center gap-3 group"
                            >
                                Siguiente <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
                            </button>
                        )}
                    </div>
                )}
            </motion.div>
        </div>
    );
}
