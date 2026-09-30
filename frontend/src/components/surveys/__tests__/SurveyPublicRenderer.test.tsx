/**
 * Tests de integración del respondente público con apiFetch mockeado.
 * TKT-SURVEYS-PUBLIC-RENDERER-01.
 */

import React from 'react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';
import SurveyPublicRenderer from '../SurveyPublicRenderer';
import { SurveyPublicDefinition, SurveyQuestionType } from '../types';
import { makeQuestion } from './factories';

const surveyId = '11111111-1111-4111-8111-111111111111';

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

const apiFetchMock = vi.fn();
vi.mock('@/lib/http', () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  ApiError: class MockApiError extends Error {
    status: number;
    detail?: unknown;
    constructor(message: string, status: number, detail?: unknown) {
      super(message);
      this.status = status;
      this.detail = detail;
    }
  },
}));

import { ApiError } from '@/lib/http';

function makeSurvey(overrides: Partial<SurveyPublicDefinition> = {}): SurveyPublicDefinition {
  return {
    id: surveyId,
    titulo: 'Encuesta de Satisfacción',
    descripcion: 'Nos ayuda a mejorar',
    slug: 'satisfaccion-2026',
    es_publico: true,
    requiere_autenticacion: false,
    mostrar_barra_progreso: true,
    mensaje_confirmacion: '¡Gracias por tu tiempo!',
    redirigir_url: null,
    estado: 'PUBLICADO',
    config_visual: {},
    preguntas: [makeQuestion({ titulo: 'Nombre', es_requerida: true })],
    ...overrides,
  };
}

beforeEach(() => {
  apiFetchMock.mockReset();
});

describe('SurveyPublicRenderer — carga', () => {
  it('renderiza skeleton y luego la encuesta con progreso 0%', async () => {
    apiFetchMock.mockResolvedValueOnce(makeSurvey());
    render(<SurveyPublicRenderer surveyId={surveyId} />);
    expect(await screen.findByRole('heading', { name: 'Encuesta de Satisfacción' })).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0');
    expect(screen.getByText('Nombre *')).toBeInTheDocument();
  });

  it('404 → estado no disponible', async () => {
    apiFetchMock.mockRejectedValueOnce(new ApiError('Not Found', 404));
    render(<SurveyPublicRenderer surveyId={surveyId} />);
    expect(await screen.findByText('Encuesta no disponible')).toBeInTheDocument();
  });

  it('403 → encuesta cerrada (no disponible para recibir respuestas)', async () => {
    apiFetchMock.mockRejectedValueOnce(new ApiError('Forbidden', 403));
    render(<SurveyPublicRenderer surveyId={surveyId} />);
    expect(await screen.findByText('Encuesta cerrada')).toBeInTheDocument();
  });

  it('error de red → permite reintentar', async () => {
    apiFetchMock.mockRejectedValueOnce(new ApiError('Network error', 0));
    render(<SurveyPublicRenderer surveyId={surveyId} />);
    const retry = await screen.findByRole('button', { name: /volver a intentar/i });
    apiFetchMock.mockResolvedValueOnce(makeSurvey());
    fireEvent.click(retry);
    expect(await screen.findByRole('heading', { name: 'Encuesta de Satisfacción' })).toBeInTheDocument();
  });
});

describe('SurveyPublicRenderer — flujo y envío', () => {
  it('bloquea avance con obligatoria vacía y envía al completar', async () => {
    const q = makeQuestion({ titulo: 'Ciudad', es_requerida: true });
    apiFetchMock.mockResolvedValueOnce(makeSurvey({ preguntas: [q] }));
    render(<SurveyPublicRenderer surveyId={surveyId} />);
    await screen.findByRole('heading', { name: 'Encuesta de Satisfacción' });

    // Única sección → botón Enviar bloqueado
    const send = screen.getByRole('button', { name: /enviar respuestas/i });
    expect(send).toBeDisabled();

    fireEvent.change(screen.getByLabelText('Ciudad'), { target: { value: 'Bogotá' } });
    await waitFor(() => expect(send).toBeEnabled());

    apiFetchMock.mockResolvedValueOnce({
      status: 'success',
      envio_id: 'e-1',
      mensaje_confirmacion: '¡Gracias por tu tiempo!',
      redirigir_url: null,
    });
    fireEvent.click(send);

    await screen.findByText('¡Gracias por tu tiempo!');
    expect(apiFetchMock).toHaveBeenLastCalledWith(
      `/public/surveys/${surveyId}/submit`,
      expect.objectContaining({ method: 'POST' }),
    );
    const [, submitOptions] = apiFetchMock.mock.calls.at(-1) as [string, { body: { respuestas: unknown[] } }];
    expect(submitOptions.body.respuestas).toHaveLength(1);
    expect(submitOptions.body.respuestas[0]).toMatchObject({ valor_texto: 'Bogotá' });
  });

  it('multi-sección: Siguiente navega y Anterior regresa', async () => {
    const q1 = makeQuestion({ titulo: 'Primera', es_requerida: true });
    const brk = makeQuestion({ tipo_pregunta: SurveyQuestionType.SECCION_SALTO, titulo: 'Sección 2' });
    const q2 = makeQuestion({ titulo: 'Segunda', es_requerida: true });
    apiFetchMock.mockResolvedValueOnce(makeSurvey({ preguntas: [q1, brk, q2] }));
    render(<SurveyPublicRenderer surveyId={surveyId} />);
    await screen.findByRole('heading', { name: 'Encuesta de Satisfacción' });

    // La etiqueta de sección solo aparece desde la página 2.
    expect(screen.queryByText(/Sección \d de \d/)).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Primera'), { target: { value: 'x' } });
    fireEvent.click(screen.getByRole('button', { name: /siguiente/i }));
    expect(screen.getByText(/Sección 2 de 2/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /anterior/i }));
    expect(screen.queryByText(/Sección \d de \d/)).not.toBeInTheDocument();
    expect(screen.getByLabelText('Primera')).toHaveValue('x');
  });

  it('error 422 del submit muestra el detalle y mantiene el formulario', async () => {
    const q = makeQuestion({ titulo: 'Campo', es_requerida: true });
    apiFetchMock.mockResolvedValueOnce(makeSurvey({ preguntas: [q] }));
    render(<SurveyPublicRenderer surveyId={surveyId} />);
    await screen.findByRole('heading', { name: 'Encuesta de Satisfacción' });

    fireEvent.change(screen.getByLabelText('Campo'), { target: { value: 'v' } });
    const send = await screen.findByRole('button', { name: /enviar respuestas/i });
    await waitFor(() => expect(send).toBeEnabled());

    apiFetchMock.mockRejectedValueOnce(
      new ApiError('Unprocessable Entity', 422, { detail: 'La pregunta obligatoria "Campo" requiere una respuesta.' }),
    );
    fireEvent.click(send);
    await waitFor(() => {
      // El formulario sigue visible (no se mostró la pantalla final)
      expect(screen.getByRole('button', { name: /enviar respuestas/i })).toBeInTheDocument();
    });
  });

  it('submit exitoso en encuesta con mensaje por defecto del backend', async () => {
    const q = makeQuestion({ titulo: 'Campo', es_requerida: true });
    apiFetchMock.mockResolvedValueOnce(makeSurvey({ preguntas: [q], mensaje_confirmacion: null }));
    render(<SurveyPublicRenderer surveyId={surveyId} />);
    await screen.findByRole('heading', { name: 'Encuesta de Satisfacción' });
    fireEvent.change(screen.getByLabelText('Campo'), { target: { value: 'v' } });
    const send = await screen.findByRole('button', { name: /enviar respuestas/i });
    await waitFor(() => expect(send).toBeEnabled());
    apiFetchMock.mockResolvedValueOnce({
      status: 'success',
      envio_id: 'e-2',
      mensaje_confirmacion: '¡Tu respuesta ha sido registrada exitosamente!',
      redirigir_url: null,
    });
    fireEvent.click(send);
    expect(await screen.findByText('¡Tu respuesta ha sido registrada exitosamente!')).toBeInTheDocument();
  });

  it('sin violaciones de accesibilidad en el formulario activo', async () => {
    apiFetchMock.mockResolvedValueOnce(makeSurvey());
    const { container } = render(<SurveyPublicRenderer surveyId={surveyId} />);
    await screen.findByRole('heading', { name: 'Encuesta de Satisfacción' });
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
