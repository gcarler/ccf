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
    GraduationCap,
    HelpCircle
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ViewType } from '@/components/ViewSwitcher';
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
    const [viewType, setViewType] = useState<ViewType>('grid');

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

    const handleAnswer = (questionId: number, update: any) => {
        setAnswers(prev => {
            const filtered = prev.filter(a => a.question_id !== questionId);
            return [...filtered, { question_id: questionId, ...update }];
        });
    };

    const handleSubmit = async () => {
        if (!token || !user?.id) return;
        setIsSubmitting(true);
        try {
            const enrollments = await apiFetch<Enrollment[]>(`/academy/users/${user.id}/enrollments`, { token });
            const enrollment = enrollments.find((e: Enrollment) => e.course.id === assessment.course_id);

            if (!enrollment) {
                alert("No estas inscrito en este curso.");
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
    if (!assessment) return <div className="p-3 text-center">Evaluacion no encontrada.</div>;

    if (result) {
        return (
            <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden">
                <WorkspaceToolbar
                    breadcrumbs={[
                        { label: 'Academia', icon: GraduationCap },
                        { label: 'Resultado', icon: Trophy }
                    ]}
                    viewType={viewType}
                    setViewType={setViewType}
                    availableViews={['grid', 'list', 'table']}
                />
                <main className="flex-1 overflow-y-auto flex items-center justify-center p-4">
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="max-w-md w-full text-center space-y-3 p-3 bg-slate-50 dark:bg-white/5 rounded-lg border border-slate-200 dark:border-white/5 shadow-xl"
                    >
                        <div className={clsx(
                            "size-10 rounded-full mx-auto flex items-center justify-center shadow-lg",
                            result.passed ? "bg-emerald-500 text-white shadow-emerald-500/20" : "bg-rose-500 text-white shadow-rose-500/20"
                        )}>
                            {result.passed ? <Trophy size={40} /> : <AlertCircle size={40} />}
                        </div>
                        <div>
                            <h2 className="text-xl font-bold mb-2">{result.passed ? '¡Felicitaciones!' : 'Sigue intentando'}</h2>
                            <p className="text-slate-500 dark:text-slate-400 font-medium">Has completado la evaluacion de {assessment.title}</p>
                        </div>
                        <div className="py-1.5 border-y border-slate-200 dark:border-white/5">
                            <p className="font-semibold text-slate-400 uppercase tracking-wide mb-1">Tu Puntaje</p>
                            <span className="text-xl font-bold tracking-tighter">{Math.round(result.submitted_score)}%</span>
                        </div>
                        <div className="space-y-3">
                            <button
                                onClick={() => router.push('/academy')}
                                className="w-full py-1.5 bg-blue-600 text-white rounded-lg font-black text-sm uppercase tracking-wide shadow-lg shadow-blue-500/20 active:scale-95 transition-all"
                            >
                                Volver a la Academia
                            </button>
                            {!result.passed && (
                                <button
                                    onClick={() => window.location.reload()}
                                    className="w-full py-1.5 text-slate-500 font-bold text-sm uppercase tracking-wide hover:text-slate-700 transition-colors"
                                >
                                    Reintentar Evaluacion
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
    const answeredQuestionIds = new Set(answers.map((answer) => answer.question_id));

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Academia', icon: GraduationCap },
                    { label: assessment.title, icon: HelpCircle }
                ]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={['grid', 'list', 'table']}
                rightActions={
                    <div className="flex items-center gap-3 px-3 py-1 bg-slate-100 dark:bg-white/5 rounded-full text-[11px] font-bold text-slate-500">
                        <Clock size={14} /> 45:00
                    </div>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-4">
                {viewType === 'list' && (
                    <div className="max-w-5xl mx-auto space-y-4">
                        {assessment.questions.map((question: any, index: number) => (
                            <button
                                key={question.id}
                                onClick={() => setCurrentStep(index)}
                                className={clsx(
                                    "w-full rounded-lg border p-4 text-left transition-all",
                                    currentStep === index
                                        ? "border-blue-500 bg-blue-50/70 dark:bg-blue-500/10"
                                        : "border-slate-200 bg-white hover:border-blue-200 dark:border-white/10 dark:bg-white/5"
                                )}
                            >
                                <div className="flex items-center justify-between gap-4">
                                    <div>
                                        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Pregunta {index + 1}</p>
                                        <h3 className="mt-2 text-base font-bold text-slate-900 dark:text-white">{question.question_text}</h3>
                                    </div>
                                    <span className={clsx(
                                        "rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-wide",
                                        answeredQuestionIds.has(question.id)
                                            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300"
                                            : "bg-slate-100 text-slate-500 dark:bg-white/10"
                                    )}>
                                        {answeredQuestionIds.has(question.id) ? 'Respondida' : 'Pendiente'}
                                    </span>
                                </div>
                            </button>
                        ))}
                    </div>
                )}

                {viewType === 'table' && (
                    <div className="max-w-5xl mx-auto overflow-hidden rounded-lg border border-slate-200 bg-white dark:border-white/10 dark:bg-white/5">
                        <table className="w-full text-left">
                            <thead className="bg-slate-50 text-[10px] font-semibold uppercase tracking-wide text-slate-400 dark:bg-white/5">
                                <tr>
                                    <th className="px-4 py-1.5">#</th>
                                    <th className="px-4 py-1.5">Pregunta</th>
                                    <th className="px-4 py-1.5">Opciones</th>
                                    <th className="px-4 py-1.5">Estado</th>
                                </tr>
                            </thead>
                            <tbody>
                                {assessment.questions.map((question: any, index: number) => (
                                    <tr key={question.id} className="border-t border-slate-100 dark:border-white/5">
                                        <td className="px-4 py-1.5 font-black text-slate-400">{index + 1}</td>
                                        <td className="px-4 py-1.5 font-bold text-slate-800 dark:text-white">{question.question_text}</td>
                                        <td className="px-4 py-1.5 text-slate-500">{question.options.length}</td>
                                        <td className="px-4 py-1.5">
                                            <button
                                                onClick={() => setCurrentStep(index)}
                                                className="text-xs font-semibold uppercase tracking-wide text-blue-600"
                                            >
                                                {answeredQuestionIds.has(question.id) ? 'Revisar' : 'Responder'}
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {viewType === 'grid' && (
                <div className="max-w-3xl mx-auto space-y-3">
                    {/* Progress Header */}
                    <div className="space-y-4">
                        <div className="flex justify-between items-end">
                            <div>
                                <p className="font-semibold text-blue-500 uppercase tracking-wide mb-1">Pregunta {currentStep + 1} de {assessment.questions.length}</p>
                                <h3 className="text-xl font-bold text-slate-800 dark:text-white tracking-tight leading-tight">
                                    {currentQuestion.question_text}
                                </h3>
                            </div>
                            <span className="font-semibold text-slate-400 shrink-0">{Math.round(((currentStep + 1) / assessment.questions.length) * 100)}%</span>
                        </div>
                        <div className="h-2 w-full bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
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
                                {currentQuestion.question_type !== 'text' ? (
                                    currentQuestion.options.map((option: any) => (
                                        <button
                                            key={option.id}
                                            onClick={() => handleAnswer(currentQuestion.id, { selected_option_id: option.id })}
                                            className={clsx(
                                                "w-full p-3 text-left rounded-lg border-2 transition-all group relative overflow-hidden",
                                                answers.find(a => a.selected_option_id === option.id)
                                                    ? "border-blue-600 bg-blue-600 text-white shadow-xl shadow-blue-500/20"
                                                    : "border-slate-100 dark:border-white/5 hover:border-blue-200 dark:hover:border-white/10 bg-white dark:bg-white/5"
                                            )}
                                        >
                                            <div className="flex items-center gap-4 relative z-10">
                                                <div className={clsx(
                                                    "size-7 rounded-full border-2 flex items-center justify-center shrink-0 transition-all",
                                                    answers.find(a => a.selected_option_id === option.id)
                                                        ? "border-white bg-white text-blue-600"
                                                        : "border-slate-200 dark:border-white/10"
                                                )}>
                                                    {answers.find(a => a.selected_option_id === option.id) && <CheckCircle2 size={16} />}
                                                </div>
                                                <span className="text-base font-bold">{option.option_text}</span>
                                            </div>
                                        </button>
                                    ))
                                ) : (
                                    <textarea
                                        value={answers.find(a => a.question_id === currentQuestion.id)?.text_response || ''}
                                        onChange={(e) => handleAnswer(currentQuestion.id, { text_response: e.target.value })}
                                        placeholder="Escribe tu respuesta aqui..."
                                        className="w-full bg-white dark:bg-white/5 border-2 border-slate-100 dark:border-white/5 rounded-lg p-3 text-base font-medium outline-none focus:border-blue-500 transition-all min-h-[200px]"
                                    />
                                )}
                            </motion.div>
                        </AnimatePresence>
                    </div>

                    {/* Navigation Actions */}
                    <div className="flex items-center justify-between pt-4 border-t border-slate-100 dark:border-white/5">
                        <button
                            disabled={currentStep === 0}
                            onClick={() => setCurrentStep(prev => prev - 1)}
                            className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wide text-slate-400 hover:text-slate-600 disabled:opacity-0 transition-all"
                        >
                            <ArrowLeft size={16} /> Anterior
                        </button>

                        {isLastStep ? (
                            <button
                                onClick={handleSubmit}
                                disabled={isSubmitting || answers.length < assessment.questions.length}
                                className="px-3 py-1.5 bg-blue-600 text-white rounded-lg font-black text-[10px] uppercase tracking-wide shadow-xl shadow-blue-500/20 active:scale-95 transition-all disabled:opacity-50"
                            >
                                {isSubmitting ? 'Enviando...' : 'Finalizar Evaluacion'}
                            </button>
                        ) : (
                            <button
                                onClick={() => setCurrentStep(prev => prev + 1)}
                                disabled={!answers.find(a => a.question_id === currentQuestion.id)}
                                className="px-3 py-1.5 bg-slate-900 text-white rounded-lg font-black text-[10px] uppercase tracking-wide shadow-xl active:scale-95 transition-all disabled:opacity-50 flex items-center gap-2"
                            >
                                Siguiente <ArrowRight size={16} />
                            </button>
                        )}
                    </div>
                </div>
                )}
            </main>
        </div>
    );
}
