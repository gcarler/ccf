"use client";

import { RightPanel } from '@/components/ui/RightPanel';
import { apiFetch } from '@/lib/http';
import clsx from 'clsx';
import { AnimatePresence,motion } from 'framer-motion';
import {
AlertCircle,
ArrowLeft,
ArrowRight,
CheckCircle2,
HelpCircle,
Loader2,
ShieldCheck,
Trophy
} from 'lucide-react';
import { useEffect,useState } from 'react';

interface Option {
    id: string;
    option_text: string;
}

interface Question {
    id: string;
    question_text: string;
    question_type: string;
    points: number;
    options: Option[];
}

interface Assessment {
    id: string;
    title: string;
    min_score: number;
    questions: Question[];
}

interface AssessmentDrawerProps {
    assessmentId: string;
    enrollmentId: string;
    token: string;
    onClose: () => void;
    onSuccess: (score: number) => void;
}

export default function AssessmentDrawer({ assessmentId, enrollmentId, token, onClose, onSuccess }: AssessmentDrawerProps) {
    const [assessment, setAssessment] = useState<Assessment | null>(null);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [currentStep, setCurrentStep] = useState(0); // 0: Welcome, 1..N: Questions, N+1: Result
    const [answers, setAnswers] = useState<Record<string, string>>({});
    const [result, setResult] = useState<{ passed: boolean, score: number } | null>(null);

    useEffect(() => {
        const ctrl = new AbortController();
        const fetchAssessment = async () => {
            try {
                const data = await apiFetch<Assessment>(`/academy/assessments/${assessmentId}`, { token, signal: ctrl.signal });
                setAssessment(data);
            } catch (err: any) {
                if (err?.name === 'AbortError') return;
                console.error("Error fetching assessment", err);
            } finally {
                setLoading(false);
            }
        };
        fetchAssessment();
        return () => ctrl.abort();
    }, [assessmentId, token]);

    const handleSelectOption = (questionId: string, optionId: string) => {
        setAnswers(prev => ({ ...prev, [questionId]: optionId }));
    };

    const handleSubmit = async () => {
        setSubmitting(true);
        try {
            const formattedAnswers = Object.entries(answers).map(([qId, oId]) => ({
                question_id: qId,
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

    const questions = assessment?.questions || [];
    const isLastQuestion = currentStep === questions.length;
    const isWelcome = currentStep === 0;
    const isResult = result !== null;

    return (
        <RightPanel open={true} onClose={onClose} title={assessment?.title || 'Evaluación'} width={800}>
            <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[#15171c] font-sans">
                {loading ? (
                    <div className="flex-1 flex items-center justify-center">
                        <Loader2 className="w-10 h-10 animate-spin text-[hsl(var(--primary))]" />
                    </div>
                ) : !assessment ? (
                    <div className="flex-1 flex items-center justify-center text-[hsl(var(--text-secondary))]">No se pudo cargar la evaluación</div>
                ) : (
                    <>
                        {/* Progress Bar (if not welcome/result) */}
                        {!isWelcome && !isResult && (
                            <div className="h-1.5 w-full bg-[hsl(var(--surface-2))] dark:bg-white/5 shrink-0">
                                <motion.div 
                                    initial={{ width: 0 }} animate={{ width: `${(currentStep / questions.length) * 100}%` }}
                                    className="h-full bg-[hsl(var(--primary))] shadow-[0_0_10px_rgba(37,99,235,0.5)]" 
                                />
                            </div>
                        )}

                        {/* Content */}
                        <div className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-4 relative">
                            <AnimatePresence mode="wait">
                                {isResult ? (
                                    <motion.div key="result" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="flex flex-col items-center justify-center h-full text-center space-y-3">
                                        <div className={clsx(
                                            "size-10 rounded-lg flex items-center justify-center shadow-2xl relative",
                                            result.passed ? "bg-emerald-500 text-white shadow-emerald-500/30" : "bg-rose-500 text-white shadow-rose-500/30"
                                        )}>
                                            {result.passed ? <Trophy size={64} /> : <AlertCircle size={64} />}
                                            <motion.div 
                                                animate={{ scale: [1, 1.2, 1] }} transition={{ repeat: Infinity, duration: 2 }}
                                                className="absolute -top-4 -right-4 size-7 bg-[hsl(var(--bg-primary))] dark:bg-[#15171c] rounded-lg flex items-center justify-center text-[hsl(var(--text-primary))] dark:text-white shadow-xl border border-[hsl(var(--border))] dark:border-white/10"
                                            >
                                                <span className="text-sm font-semibold">{result.score}%</span>
                                            </motion.div>
                                        </div>
                                        <div className="space-y-3">
                                            <h3 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tighter">
                                                {result.passed ? '¡Felicidades, Siervo!' : 'Sigue Intentándolo'}
                                            </h3>
                                            <p className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-medium max-w-md mx-auto text-lg leading-relaxed">
                                                {result.passed 
                                                    ? `Has aprobado el examen con un puntaje de ${result.score}%. Tu certificado ministerial ha sido generado y está disponible en tu panel.`
                                                    : `Tu puntaje de ${result.score}% no alcanzó el mínimo de ${assessment.min_score}%. Revisa el material de estudio y vuelve a intentarlo.`}
                                            </p>
                                        </div>
                                        <div className="flex gap-4 pt-6">
                                            {result.passed ? (
                                                <button onClick={onClose} className="px-4 py-2 bg-[hsl(var(--primary))] text-white rounded-lg font-semibold uppercase tracking-wide shadow-xl shadow-blue-600/20 active:scale-95 transition-all">Continuar a mi Panel</button>
                                            ) : (
                                                <>
                                                    <button onClick={onClose} className="px-4 py-2 border-2 border-[hsl(var(--border))] dark:border-white/10 rounded-lg text-[hsl(var(--text-secondary))] font-semibold uppercase tracking-wide hover:bg-[hsl(var(--surface-1))] transition-all">Cerrar</button>
                                                    <button onClick={() => { setResult(null); setCurrentStep(0); setAnswers({}); }} className="px-4 py-2 bg-[hsl(var(--primary))] text-white rounded-lg font-semibold uppercase tracking-wide shadow-xl shadow-blue-600/20 active:scale-95 transition-all">Reintentar</button>
                                                </>
                                            )}
                                        </div>
                                    </motion.div>
                                ) : isWelcome ? (
                                    <motion.div key="welcome" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="flex flex-col items-center justify-center h-full text-center space-y-3">
                                        <div className="size-10 rounded-lg bg-blue-50 dark:bg-blue-500/10 flex items-center justify-center text-[hsl(var(--primary))] shadow-inner">
                                            <ShieldCheck size={48} />
                                        </div>
                                        <div className="space-y-3">
                                            <h3 className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight uppercase">Instrucciones de Evaluación</h3>
                                            <p className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-medium max-w-lg mx-auto text-base">
                                                Este examen consta de <span className="font-semibold text-[hsl(var(--primary))]">{questions.length} preguntas</span>. 
                                                Para aprobar, necesitas una nota mínima de <span className="font-semibold text-[hsl(var(--primary))]">{assessment.min_score}%</span>. 
                                                Asegúrate de estar en un lugar tranquilo antes de iniciar.
                                            </p>
                                        </div>
                                        <button onClick={nextStep} className="px-4 py-2 bg-[hsl(var(--primary))] text-white rounded-lg font-semibold uppercase tracking-wide shadow-xl shadow-blue-600/20 active:scale-95 transition-all flex items-center gap-4 group">
                                            Iniciar Examen <ArrowRight className="group-hover:translate-x-1 transition-transform" />
                                        </button>
                                    </motion.div>
                                ) : (
                                    <motion.div 
                                        key={currentStep} initial={{ opacity: 0, x: 50 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -50 }}
                                        className="space-y-3"
                                    >
                                        <div className="space-y-4">
                                            <span className="font-semibold text-[hsl(var(--primary))] uppercase tracking-wide bg-blue-50 dark:bg-blue-500/10 px-3 py-1 rounded-lg">Pregunta {currentStep} de {questions.length}</span>
                                            <h3 className="text-lg lg:text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white leading-tight">
                                                {questions[currentStep - 1].question_text}
                                            </h3>
                                        </div>

                                        <div className="grid grid-cols-1 gap-4">
                                            {questions[currentStep - 1].options.map((option) => (
                                                <button 
                                                    key={option.id}
                                                    onClick={() => handleSelectOption(questions[currentStep - 1].id, option.id)}
                                                    className={clsx(
                                                        "w-full text-left p-3 rounded-lg border-2 transition-all group flex items-center gap-3",
                                                        answers[questions[currentStep - 1].id] === option.id 
                                                            ? "bg-[hsl(var(--primary))] border-blue-600 text-white shadow-xl shadow-blue-600/20" 
                                                            : "bg-[hsl(var(--surface-1))] dark:bg-white/5 border-[hsl(var(--border))] dark:border-white/5 text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] hover:border-blue-500/30 hover:bg-[hsl(var(--bg-primary))] dark:hover:bg-white/10 shadow-sm"
                                                    )}
                                                >
                                                    <div className={clsx(
                                                        "size-8 rounded-md flex items-center justify-center shrink-0 shadow-inner border transition-colors",
                                                        answers[questions[currentStep - 1].id] === option.id 
                                                            ? "bg-white/20 border-white/30 text-white" 
                                                            : "bg-[hsl(var(--bg-primary))] dark:bg-[#15171c] border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] group-hover:border-blue-500/50"
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
                            <div className="p-4 border-t border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-between shrink-0 bg-[hsl(var(--surface-1))]/50 dark:bg-black/20">
                                <button onClick={prevStep} className="flex items-center gap-2 px-3 py-1.5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-white transition-all font-semibold uppercase text-[10px] tracking-wide">
                                    <ArrowLeft size={16} /> Anterior
                                </button>
                                
                                {isLastQuestion ? (
                                    <button 
                                        onClick={handleSubmit}
                                        disabled={submitting || !answers[questions[currentStep - 1].id]}
                                        className="px-4 py-1.5 bg-[hsl(var(--primary))] text-white rounded-lg font-semibold uppercase tracking-wide shadow-xl shadow-blue-600/20 active:scale-95 transition-all disabled:opacity-50 flex items-center gap-3"
                                    >
                                        {submitting ? <Loader2 className="animate-spin" size={18} /> : <>Finalizar Examen <Trophy size={18} /></>}
                                    </button>
                                ) : (
                                    <button 
                                        onClick={nextStep}
                                        disabled={!answers[questions[currentStep - 1].id]}
                                        className="px-4 py-1.5 bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--bg-primary))] text-white dark:text-[hsl(var(--text-primary))] rounded-lg font-semibold uppercase tracking-wide shadow-xl active:scale-95 transition-all disabled:opacity-50 flex items-center gap-3 group"
                                    >
                                        Siguiente <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
                                    </button>
                                )}
                            </div>
                        )}
                    </>
                )}
            </div>
        </RightPanel>
    );
}
