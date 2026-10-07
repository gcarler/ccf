"use client";

import { RightPanel } from '@/components/ui/RightPanel';
import { apiFetch } from '@/lib/http';
import clsx from 'clsx';
import { AnimatePresence, motion } from 'framer-motion';
import {
    AlertCircle,
    AlertTriangle,
    ArrowLeft,
    ArrowRight,
    CheckCircle2,
    Clock,
    HelpCircle,
    Loader2,
    RotateCcw,
    ShieldCheck,
    Trophy
} from 'lucide-react';
import { toast } from 'sonner';
import { useEffect, useState } from 'react';

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
    max_attempts?: number | null;
    cooldown_minutes?: number | null;
    questions: Question[];
}

interface AssessmentAttemptStatus {
    assessment_id: string;
    max_attempts: number | null;
    attempts_count: number;
    attempts_remaining: number | null;
    cooldown_minutes: number;
    in_cooldown: boolean;
    cooldown_remaining_seconds: number;
    cooldown_until: string | null;
    can_attempt: boolean;
    last_attempt_score: number | null;
    passed: boolean;
}

interface AssessmentAttemptResult {
    passed: boolean;
    score: number;
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
    const [attemptStatus, setAttemptStatus] = useState<AssessmentAttemptStatus | null>(null);
    const [submitError, setSubmitError] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [currentStep, setCurrentStep] = useState(0); // 0: Welcome, 1..N: Questions, N+1: Result
    const [answers, setAnswers] = useState<Record<string, string>>({});
    const [result, setResult] = useState<{ passed: boolean, score: number } | null>(null);

    useEffect(() => {
        const ctrl = new AbortController();
        const fetchAssessment = async () => {
            try {
                const [data, statusData] = await Promise.all([
                    apiFetch<Assessment>(`/academy/assessments/${assessmentId}`, { token, signal: ctrl.signal }),
                    apiFetch<AssessmentAttemptStatus>(`/academy/assessments/${assessmentId}/attempt-status`, { token, signal: ctrl.signal }).catch(() => null),
                ]);
                setAssessment(data);
                if (statusData) setAttemptStatus(statusData);
            } catch (err: unknown) {
                if (err instanceof DOMException && err.name === 'AbortError') return;
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
        setSubmitError(null);
        try {
            const formattedAnswers = Object.entries(answers).map(([qId, oId]) => ({
                question_id: qId,
                selected_option_id: oId
            }));

            const res = await apiFetch<AssessmentAttemptResult>(`/academy/assessments/${assessmentId}/submit`, {
                method: 'POST',
                token,
                body: {
                    enrollment_id: enrollmentId,
                    answers: formattedAnswers
                }
            });

            setResult({ passed: res.passed, score: res.score });
            try {
                const updatedStatus = await apiFetch<AssessmentAttemptStatus>(`/academy/assessments/${assessmentId}/attempt-status`, { token });
                setAttemptStatus(updatedStatus);
            } catch {
                // ignore
            }
            if (res.passed) {
                onSuccess(res.score);
            }
        } catch (err: unknown) {
            const msg = (err as Error)?.message || 'Error al enviar la evaluación';
            setSubmitError(msg);
            toast.error(msg);
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

    const maxAttempts = attemptStatus?.max_attempts ?? assessment?.max_attempts;
    const cooldownMins = attemptStatus?.cooldown_minutes ?? assessment?.cooldown_minutes ?? 0;
    const attemptsExhausted = attemptStatus ? (attemptStatus.attempts_remaining !== null && attemptStatus.attempts_remaining <= 0) : false;
    const isInCooldown = attemptStatus?.in_cooldown ?? false;
    const isBlocked = attemptsExhausted || isInCooldown;

    const maxAttemptsLabel = maxAttempts
        ? (attemptStatus ? `${attemptStatus.attempts_count} / ${maxAttempts} intentos` : `Máx. ${maxAttempts} intentos`)
        : 'Intentos ilimitados';
    const cooldownLabel = cooldownMins > 0 ? `${cooldownMins} min de enfriamiento` : 'Sin enfriamiento';

    return (
        <RightPanel open={true} onClose={onClose} title={assessment?.title || 'Evaluación'} width={800}>
            <div
                role="dialog"
                aria-modal="true"
                aria-labelledby="assessment-drawer-title"
                className="flex flex-col h-full bg-[hsl(var(--surface-1))] font-sans"
            >
                <span id="assessment-drawer-title" className="sr-only">
                    {assessment?.title || 'Evaluación'}
                </span>
                {loading ? (
                    <div className="flex-1 flex items-center justify-center">
                        <Loader2 className="w-10 h-10 animate-spin text-[hsl(var(--primary))]" />
                    </div>
                ) : !assessment ? (
                    <div className="flex-1 flex items-center justify-center text-[hsl(var(--muted-foreground))]">No se pudo cargar la evaluación</div>
                ) : (
                    <>
                        {/* Progress Bar (if not welcome/result) */}
                        {!isWelcome && !isResult && (
                            <div className="h-1.5 w-full bg-[hsl(var(--surface-2))] shrink-0">
                                <motion.div
                                    role="progressbar"
                                    aria-valuenow={currentStep}
                                    aria-valuemin={0}
                                    aria-valuemax={questions.length}
                                    aria-label="Progreso de la evaluación"
                                    initial={{ width: 0 }} animate={{ width: `${(currentStep / questions.length) * 100}%` }}
                                    className="h-full bg-[hsl(var(--primary))] shadow-[0_0_10px_hsl(var(--primary)/50%)]"
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
                                            result.passed ? "bg-[hsl(var(--success))] text-[hsl(var(--primary-foreground))] shadow-[hsl(var(--success)/30%)]" : "bg-[hsl(var(--destructive))] text-[hsl(var(--primary-foreground))] shadow-[hsl(var(--destructive)/30%)]"
                                        )}>
                                            {result.passed ? <Trophy size={64} /> : <AlertCircle size={64} />}
                                            <motion.div
                                                animate={{ scale: [1, 1.2, 1] }} transition={{ repeat: Infinity, duration: 2 }}
                                                className="absolute -top-4 -right-4 size-7 bg-[hsl(var(--surface-2))] rounded-lg flex items-center justify-center text-[hsl(var(--foreground))] shadow-xl border border-[hsl(var(--border))]"
                                            >
                                                <span className="text-sm font-semibold">{result.score}%</span>
                                            </motion.div>
                                        </div>
                                        <div className="space-y-3">
                                            <h3 className="text-lg font-bold text-[hsl(var(--foreground))] tracking-tighter">
                                                {result.passed ? '¡Felicidades, Siervo!' : 'Sigue Intentándolo'}
                                            </h3>
                                            <p className="text-[hsl(var(--muted-foreground))] font-medium max-w-md mx-auto text-lg leading-relaxed">
                                                {result.passed
                                                    ? `Has aprobado el examen con un puntaje de ${result.score}%. Tu certificado ministerial ha sido generado y está disponible en tu panel.`
                                                    : `Tu puntaje de ${result.score}% no alcanzó el mínimo de ${assessment.min_score}%. Revisa el material de estudio y vuelve a intentarlo.`}
                                            </p>
                                        </div>
                                        <div className="flex gap-4 pt-6">
                                            {result.passed ? (
                                                <button onClick={onClose} className="px-4 py-2 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-lg font-semibold uppercase tracking-wide shadow-xl shadow-[hsl(var(--info)/20%)] active:scale-95 transition-all">Continuar a mi Panel</button>
                                            ) : (
                                                <>
                                                    <button onClick={onClose} className="px-4 py-2 border-2 border-[hsl(var(--border))] rounded-lg text-[hsl(var(--muted-foreground))] font-semibold uppercase tracking-wide hover:bg-[hsl(var(--surface-2))] transition-all">Cerrar</button>
                                                    <button
                                                        onClick={() => { setResult(null); setCurrentStep(0); setAnswers({}); setSubmitError(null); }}
                                                        disabled={isBlocked}
                                                        className="px-4 py-2 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-lg font-semibold uppercase tracking-wide shadow-xl shadow-[hsl(var(--info)/20%)] active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                                                    >
                                                        {isInCooldown ? 'Enfriamiento Activo' : attemptsExhausted ? 'Intentos Agotados' : 'Reintentar'}
                                                    </button>
                                                </>
                                            )}
                                        </div>
                                    </motion.div>
                                ) : isWelcome ? (
                                    <motion.div key="welcome" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="flex flex-col items-center justify-center h-full text-center space-y-4">
                                        <div className="size-12 rounded-lg bg-[hsl(var(--primary)/0.1)] flex items-center justify-center text-[hsl(var(--primary))] shadow-inner">
                                            <ShieldCheck size={48} />
                                        </div>
                                        <div className="space-y-3">
                                            <h3 className="text-xl font-bold text-[hsl(var(--foreground))] tracking-tight uppercase">Instrucciones de Evaluación</h3>
                                            <p className="text-[hsl(var(--muted-foreground))] font-medium max-w-lg mx-auto text-base">
                                                Este examen consta de <span className="font-semibold text-[hsl(var(--primary))]">{questions.length} preguntas</span>.
                                                Para aprobar, necesitas una nota mínima de <span className="font-semibold text-[hsl(var(--primary))]">{assessment.min_score}%</span>.
                                                Asegúrate de estar en un lugar tranquilo antes de iniciar.
                                            </p>

                                            <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
                                                <span className="px-3 py-1 bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-full text-xs font-semibold text-[hsl(var(--foreground))] flex items-center gap-1.5">
                                                    <RotateCcw size={12} className="text-[hsl(var(--primary))]" /> {maxAttemptsLabel}
                                                </span>
                                                <span className="px-3 py-1 bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-full text-xs font-semibold text-[hsl(var(--foreground))] flex items-center gap-1.5">
                                                    <Clock size={12} className="text-[hsl(var(--primary))]" /> {cooldownLabel}
                                                </span>
                                            </div>

                                            {isInCooldown && (
                                                <div className="max-w-md mx-auto p-3 rounded-lg bg-[hsl(var(--destructive)/0.1)] border border-[hsl(var(--destructive)/0.3)] text-[hsl(var(--destructive))] text-sm font-semibold flex items-center gap-2">
                                                    <Clock size={16} className="shrink-0" />
                                                    <span>Período de enfriamiento activo ({Math.ceil((attemptStatus?.cooldown_remaining_seconds || 60) / 60)} min restantes). Reintento bloqueado temporalmente.</span>
                                                </div>
                                            )}

                                            {attemptsExhausted && !isInCooldown && (
                                                <div className="max-w-md mx-auto p-3 rounded-lg bg-[hsl(var(--destructive)/0.1)] border border-[hsl(var(--destructive)/0.3)] text-[hsl(var(--destructive))] text-sm font-semibold flex items-center gap-2">
                                                    <AlertTriangle size={16} className="shrink-0" />
                                                    <span>Has alcanzado el límite máximo de {maxAttempts} intentos permitidos para esta evaluación.</span>
                                                </div>
                                            )}
                                        </div>

                                        <button
                                            onClick={nextStep}
                                            disabled={isBlocked}
                                            className="px-6 py-2.5 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-lg font-semibold uppercase tracking-wide shadow-xl shadow-[hsl(var(--info)/20%)] active:scale-95 transition-all flex items-center gap-4 group disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            {isInCooldown ? 'Enfriamiento Activo' : attemptsExhausted ? 'Intentos Agotados' : 'Iniciar Examen'}
                                            {!isBlocked && <ArrowRight className="group-hover:translate-x-1 transition-transform" />}
                                        </button>
                                    </motion.div>
                                ) : (
                                    <motion.div
                                        key={currentStep} initial={{ opacity: 0, x: 50 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -50 }}
                                        className="space-y-3"
                                    >
                                        {submitError && (
                                            <div className="p-3 rounded-lg bg-[hsl(var(--destructive)/0.1)] border border-[hsl(var(--destructive)/0.3)] text-[hsl(var(--destructive))] text-sm font-semibold flex items-center gap-2">
                                                <AlertCircle size={16} className="shrink-0" />
                                                <span>{submitError}</span>
                                            </div>
                                        )}
                                        <div className="space-y-4">
                                            <span className="font-semibold text-[hsl(var(--primary))] uppercase tracking-wide bg-[hsl(var(--primary)/0.1)] px-3 py-1 rounded-lg">Pregunta {currentStep} de {questions.length}</span>
                                            <h3 className="text-lg lg:text-xl font-bold text-[hsl(var(--foreground))] leading-tight">
                                                {questions[currentStep - 1].question_text}
                                            </h3>
                                        </div>

                                        <div
                                            role="radiogroup"
                                            aria-labelledby={`assessment-question-${currentStep}`}
                                            className="grid grid-cols-1 gap-4"
                                        >
                                            <span id={`assessment-question-${currentStep}`} className="sr-only">
                                                {questions[currentStep - 1].question_text}
                                            </span>
                                            {questions[currentStep - 1].options.map((option) => {
                                                const isSelected = answers[questions[currentStep - 1].id] === option.id;
                                                return (
                                                <button
                                                    key={option.id}
                                                    role="radio"
                                                    aria-checked={isSelected}
                                                    onClick={() => handleSelectOption(questions[currentStep - 1].id, option.id)}
                                                    className={clsx(
                                                        "w-full text-left p-3 rounded-lg border-2 transition-all group flex items-center gap-3",
                                                        isSelected
                                                            ? "bg-[hsl(var(--primary))] border-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-xl shadow-[hsl(var(--info)/20%)]"
                                                            : "bg-[hsl(var(--surface-1))] border-[hsl(var(--border))] text-[hsl(var(--foreground))] hover:border-[hsl(var(--primary)/40%)] hover:bg-[hsl(var(--surface-2))] shadow-sm"
                                                    )}
                                                >
                                                    <div className={clsx(
                                                        "size-8 rounded-md flex items-center justify-center shrink-0 shadow-inner border transition-colors",
                                                        answers[questions[currentStep - 1].id] === option.id
                                                            ? "bg-[hsl(var(--primary-foreground)/0.2)] border-[hsl(var(--primary-foreground)/0.3)] text-[hsl(var(--primary-foreground))]"
                                                            : "bg-[hsl(var(--surface-2))] border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))] group-hover:border-[hsl(var(--primary)/50%)]"
                                                    )}>
                                                        {answers[questions[currentStep - 1].id] === option.id ? <CheckCircle2 size={18} /> : <HelpCircle size={18} />}
                                                    </div>
                                                    <span className="text-base font-bold tracking-tight">{option.option_text}</span>
                                                </button>
                                                );
                                            })}
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>

                        {/* Footer Actions (Quiz Navigation) */}
                        {!isWelcome && !isResult && (
                            <div className="p-4 border-t border-[hsl(var(--border))] flex items-center justify-between shrink-0 bg-[hsl(var(--surface-2))]">
                                <button onClick={prevStep} className="flex items-center gap-2 px-3 py-1.5 text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] transition-all font-semibold uppercase text-2xs tracking-wide">
                                    <ArrowLeft size={16} /> Anterior
                                </button>

                                {isLastQuestion ? (
                                    <button
                                        onClick={handleSubmit}
                                        disabled={submitting || !answers[questions[currentStep - 1].id]}
                                        className="px-4 py-1.5 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-lg font-semibold uppercase tracking-wide shadow-xl shadow-[hsl(var(--info)/20%)] active:scale-95 transition-all disabled:opacity-50 flex items-center gap-3"
                                    >
                                        {submitting ? <Loader2 className="animate-spin" size={18} /> : <>Finalizar Examen <Trophy size={18} /></>}
                                    </button>
                                ) : (
                                    <button
                                        onClick={nextStep}
                                        disabled={!answers[questions[currentStep - 1].id]}
                                        className="px-4 py-1.5 bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--foreground))] rounded-lg border border-[hsl(var(--border))] font-semibold uppercase tracking-wide shadow-sm active:scale-95 transition-all disabled:opacity-50 flex items-center gap-3 group"
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
