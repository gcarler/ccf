'use client';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { AlertTriangle, ArrowLeft } from 'lucide-react';
import { apiFetch, ApiError } from '@/lib/http';
import { toast } from 'sonner';
import ProgressBar from './ProgressBar';
import QuestionRenderer from './QuestionRenderer';
import SectionPager from './SectionPager';
import ThankYouScreen from './ThankYouScreen';
import {
  SurveyFileUploadResult,
  SurveyPublicDefinition,
  SurveyQuestion,
  SurveyQuestionType,
  SurveySubmitResponse,
} from './types';
import {
  QuestionValues,
  answersEqual,
  buildSectionsFromQuestions,
  buildSubmitPayload,
  initValues,
  missingRequiredInSection,
  missingRequiredQuestions,
  resolveNextSection,
  surveyProgress,
} from './surveyHelpers';

type RendererState = 'loading' | 'ready' | 'submitted' | 'not_available' | 'auth_required' | 'error';

interface SurveyPublicRendererProps {
  /** Identificador canónico de la encuesta (UUID o slug). */
  surveyId: string;
}

/**
 * Respondente público de encuestas (paridad Google Forms).
 *
 * Orquesta: carga de la definición pública, paginación fluida por secciones,
 * saltos condicionales, barra de progreso, validación de obligatoriedad,
 * upload de archivos y envío canónico al backend.
 */
export default function SurveyPublicRenderer({ surveyId }: SurveyPublicRendererProps) {
  const [state, setState] = useState<RendererState>('loading');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [survey, setSurvey] = useState<SurveyPublicDefinition | null>(null);

  const [sectionIndex, setSectionIndex] = useState(0);
  const [values, setValues] = useState<QuestionValues>({});
  const [attemptedAdvance, setAttemptedAdvance] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState<SurveySubmitResponse | null>(null);

  const topRef = useRef<HTMLDivElement>(null);

  const loadSurvey = useCallback(async () => {
    setState('loading');
    setErrorMessage(null);
    try {
      const data = await apiFetch<SurveyPublicDefinition>(`/public/surveys/${encodeURIComponent(surveyId)}`, {
        silent: true,
      });
      setSurvey(data);
      setValues(initValues(data.preguntas || []));
      setSectionIndex(0);
      setAttemptedAdvance(false);
      setState('ready');
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 403) {
          setState('auth_required');
          return;
        }
        if (err.status === 404) {
          setState('not_available');
          return;
        }
        setErrorMessage(err.message);
      } else {
        setErrorMessage('No se pudo cargar la encuesta.');
      }
      setState('error');
    }
  }, [surveyId]);

  useEffect(() => {
    void loadSurvey();
  }, [loadSurvey]);

  const questions = useMemo<SurveyQuestion[]>(() => survey?.preguntas ?? [], [survey]);
  const sections = useMemo<SurveyQuestion[][]>(() => buildSectionsFromQuestions(questions), [questions]);
  const currentSection = useMemo<SurveyQuestion[]>(() => sections[sectionIndex] ?? [], [sections, sectionIndex]);
  const progress = useMemo(() => surveyProgress(questions, values), [questions, values]);
  const missingInSection = useMemo(
    () => missingRequiredInSection(currentSection, values),
    [currentSection, values],
  );
  const missingTotal = useMemo(() => missingRequiredQuestions(questions, values), [questions, values]);
  const isLastSection = sectionIndex >= sections.length - 1;
  const submitBlocked = missingTotal.length > 0;

  /** Scroll suave al inicio de la página en cada cambio de sección. */
  useEffect(() => {
    if (state === 'ready' && typeof topRef.current?.scrollIntoView === 'function') {
      topRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [sectionIndex, state]);

  const setValue = (questionId: string, next: QuestionValues[string]) => {
    setValues((prev) => {
      const previous = prev[questionId];
      if (answersEqual(previous, next)) return prev;
      return { ...prev, [questionId]: next };
    });
  };

  const goToSection = (target: number) => {
    const bounded = Math.max(0, Math.min(target, Math.max(sections.length - 1, 0)));
    setSectionIndex(bounded);
    setAttemptedAdvance(false);
  };

  const handleNext = () => {
    if (missingInSection.length > 0) {
      setAttemptedAdvance(true);
      toast.error('Completa las preguntas obligatorias para continuar.');
      return;
    }
    goToSection(resolveNextSection(sections, sectionIndex, values));
  };

  const handleUpload = async (_question: SurveyQuestion, file: File): Promise<SurveyFileUploadResult> => {
    const form = new FormData();
    form.append('file', file);
    return apiFetch<SurveyFileUploadResult>(`/public/surveys/${encodeURIComponent(surveyId)}/upload-file`, {
      method: 'POST',
      body: form,
    });
  };

  const handleSubmit = async () => {
    if (submitBlocked) {
      setAttemptedAdvance(true);
      toast.error('Faltan preguntas obligatorias por responder.');
      return;
    }
    setIsSubmitting(true);
    try {
      const payload = buildSubmitPayload(questions, values, { email: null, nombre: null });
      const result = await apiFetch<SurveySubmitResponse>(
        `/public/surveys/${encodeURIComponent(surveyId)}/submit`,
        { method: 'POST', body: payload },
      );
      setSubmitResult(result);
      setState('submitted');
      toast.success('Respuesta enviada con éxito.');
    } catch (err) {
      if (err instanceof ApiError) {
        const detail =
          err.detail && typeof err.detail === 'object' && 'detail' in (err.detail as Record<string, unknown>)
            ? String((err.detail as Record<string, unknown>).detail)
            : err.message;
        toast.error(detail || 'No se pudo enviar la respuesta.');
        if (err.status === 403 || err.status === 404) {
          // La encuesta se cerró o despublicó mientras se respondía.
          void loadSurvey();
        }
      } else {
        toast.error('No se pudo enviar la respuesta.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRespondAgain = () => {
    if (!survey) return;
    setValues(initValues(survey.preguntas || []));
    setSectionIndex(0);
    setAttemptedAdvance(false);
    setSubmitResult(null);
    setState('ready');
  };

  if (state === 'loading') {
    return <SurveySkeleton />;
  }

  if (state === 'not_available' || state === 'error') {
    return (
      <SurveyShell>
        <StatusCard
          icon={<AlertTriangle className="h-10 w-10 text-[hsl(var(--destructive))]" aria-hidden="true" />}
          title="Encuesta no disponible"
          description={
            errorMessage ||
            'La encuesta solicitada no existe o no se encuentra disponible en este momento.'
          }
          actionLabel="Volver a intentar"
          onAction={() => void loadSurvey()}
        />
      </SurveyShell>
    );
  }

  if (state === 'auth_required') {
    return (
      <SurveyShell>
        <StatusCard
          icon={<AlertTriangle className="h-10 w-10 text-[hsl(var(--destructive))]" aria-hidden="true" />}
          title="Encuesta cerrada"
          description="Esta encuesta no está recibiendo respuestas actualmente."
        />
      </SurveyShell>
    );
  }

  if (state === 'submitted') {
    return (
      <SurveyShell>
        <ThankYouScreen
          message={submitResult?.mensaje_confirmacion || survey?.mensaje_confirmacion || ''}
          redirectUrl={submitResult?.redirigir_url ?? survey?.redirigir_url ?? null}
          canRespondAgain={true}
          onRespondAgain={handleRespondAgain}
        />
      </SurveyShell>
    );
  }

  if (!survey) return <SurveySkeleton />;

  return (
    <SurveyShell>
      <div ref={topRef} />
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-[hsl(var(--text-primary))]">{survey.titulo}</h1>
        {survey.descripcion ? (
          <p className="mt-2 text-sm text-[hsl(var(--text-secondary))]">{survey.descripcion}</p>
        ) : null}
      </header>

      {survey.mostrar_barra_progreso ? (
        <div className="mb-6">
          <ProgressBar value={progress} />
        </div>
      ) : null}

      <form
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          if (isLastSection) void handleSubmit();
          else handleNext();
        }}
        className="flex flex-col gap-4"
        aria-label={survey.titulo}
      >
        {sections.length > 1 && sectionIndex > 0 ? (
          <p className="text-xs font-medium uppercase tracking-wide text-[hsl(var(--text-secondary))]">
            {`Sección ${sectionIndex + 1} de ${sections.length}`}
          </p>
        ) : null}

        {currentSection.map((question) =>
          question.tipo_pregunta === SurveyQuestionType.SECCION_SALTO ? (
            <QuestionRenderer
              key={question.id}
              question={question}
              value={undefined}
              onChange={() => undefined}
              highlightMissing={false}
              onUpload={handleUpload}
            />
          ) : (
            <QuestionRenderer
              key={question.id}
              question={question}
              value={values[question.id]}
              onChange={(next) => setValue(question.id, next)}
              highlightMissing={attemptedAdvance}
              onUpload={handleUpload}
            />
          ),
        )}

        <SectionPager
          currentIndex={sectionIndex}
          totalSections={sections.length}
          blocked={isLastSection ? submitBlocked : missingInSection.length > 0}
          blockedMessage={
            (isLastSection ? submitBlocked : missingInSection.length > 0) && attemptedAdvance
              ? `Faltan ${isLastSection ? missingTotal.length : missingInSection.length} pregunta(s) obligatoria(s).`
              : null
          }
          isSubmitting={isSubmitting}
          onPrevious={() => goToSection(sectionIndex - 1)}
          onNext={handleNext}
          onSubmit={() => void handleSubmit()}
        />
      </form>
    </SurveyShell>
  );
}

function SurveyShell({ children }: { children: React.ReactNode }) {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-2xl flex-col px-4 py-8">
      <div className="mb-4">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm font-medium text-[hsl(var(--text-secondary))] transition-colors hover:text-[hsl(var(--text-primary))]"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Inicio
        </Link>
      </div>
      {children}
    </main>
  );
}

function StatusCard({
  icon,
  title,
  description,
  actionLabel,
  onAction,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-10 text-center">
      {icon}
      <h2 className="text-lg font-semibold text-[hsl(var(--text-primary))]">{title}</h2>
      <p className="max-w-sm text-sm text-[hsl(var(--text-secondary))]">{description}</p>
      {actionLabel && onAction ? (
        <button
          type="button"
          onClick={onAction}
          className="mt-1 rounded-lg border border-[hsl(var(--border))] px-4 py-2 text-sm font-medium text-[hsl(var(--text-primary))] transition-colors hover:bg-[hsl(var(--surface-2))]"
        >
          {actionLabel}
        </button>
      ) : null}
    </div>
  );
}

function SurveySkeleton() {
  return (
    <SurveyShell>
      <div className="animate-pulse">
        <div className="h-7 w-3/4 rounded bg-[hsl(var(--surface-3))]" />
        <div className="mt-3 h-4 w-1/2 rounded bg-[hsl(var(--surface-3))]" />
        <div className="mt-8 h-2 w-full rounded-full bg-[hsl(var(--surface-3))]" />
        <div className="mt-8 space-y-4">
          <div className="h-32 w-full rounded-xl bg-[hsl(var(--surface-3))]" />
          <div className="h-32 w-full rounded-xl bg-[hsl(var(--surface-3))]" />
          <div className="h-10 w-40 rounded-lg bg-[hsl(var(--surface-3))]" />
        </div>
      </div>
    </SurveyShell>
  );
}
