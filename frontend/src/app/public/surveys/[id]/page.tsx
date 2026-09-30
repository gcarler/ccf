'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import SurveyPublicRenderer from '@/components/surveys/SurveyPublicRenderer';

/**
 * Respondente público de encuestas: /public/surveys/[id].
 *
 * ``[id]`` acepta el UUID canónico de la encuesta o su slug
 * (``GET /api/public/surveys/{identifier}`` resuelve ambos).
 */
export default function PublicSurveyPage() {
  const params = useParams<{ id: string }>();
  const surveyId = typeof params?.id === 'string' ? params.id : '';

  if (!surveyId) {
    return (
      <main className="mx-auto flex min-h-screen w-full max-w-2xl flex-col items-center justify-center px-4">
        <p className="text-sm text-[hsl(var(--text-secondary))]">
          Identificador de encuesta inválido.
        </p>
      </main>
    );
  }

  return <SurveyPublicRenderer surveyId={surveyId} />;
}
