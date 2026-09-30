/**
 * Tests unitarios de los componentes del respondente público de encuestas.
 * TKT-SURVEYS-PUBLIC-RENDERER-01.
 */

import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';
import QuestionRenderer from '../QuestionRenderer';
import ProgressBar from '../ProgressBar';
import SectionPager from '../SectionPager';
import ThankYouScreen from '../ThankYouScreen';
import { SurveyQuestionType } from '../types';
import { makeQuestion } from './factories';

const noopUpload = vi.fn(async () => ({ url: 'u', filename: 'f', size: 1, mime_type: 'm' }));

describe('ProgressBar', () => {
  it('muestra el porcentaje y respeta el rango', () => {
    render(<ProgressBar value={42} />);
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '42');
    expect(screen.getByText('42%')).toBeInTheDocument();
  });

  it('satura valores fuera de rango', () => {
    render(<ProgressBar value={150} />);
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '100');
  });

  it('no tiene violaciones de accesibilidad', async () => {
    const { container } = render(<ProgressBar value={30} />);
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});

describe('SectionPager', () => {
  it('primer paso: Anterior deshabilitado y botón Siguiente', () => {
    render(
      <SectionPager
        currentIndex={0}
        totalSections={3}
        blocked={false}
        isSubmitting={false}
        onPrevious={vi.fn()}
        onNext={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );
    expect(screen.getByRole('button', { name: /anterior/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /siguiente/i })).toBeEnabled();
  });

  it('último paso muestra Enviar y bloquea cuando hay pendientes', () => {
    const onSubmit = vi.fn();
    render(
      <SectionPager
        currentIndex={2}
        totalSections={3}
        blocked={true}
        blockedMessage="Faltan 2 pregunta(s) obligatoria(s)."
        isSubmitting={false}
        onPrevious={vi.fn()}
        onNext={vi.fn()}
        onSubmit={onSubmit}
      />,
    );
    const send = screen.getByRole('button', { name: /enviar respuestas/i });
    expect(send).toBeDisabled();
    expect(screen.getByRole('alert')).toHaveTextContent('Faltan 2 pregunta(s) obligatoria(s).');
    fireEvent.click(send);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('onNext se invoca al hacer clic', () => {
    const onNext = vi.fn();
    render(
      <SectionPager
        currentIndex={1}
        totalSections={3}
        blocked={false}
        isSubmitting={false}
        onPrevious={vi.fn()}
        onNext={onNext}
        onSubmit={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: /siguiente/i }));
    expect(onNext).toHaveBeenCalledTimes(1);
  });
});

describe('ThankYouScreen', () => {
  it('muestra el mensaje de confirmación configurado', () => {
    render(
      <ThankYouScreen message="¡Gracias por participar!" redirectUrl={null} canRespondAgain={false} onRespondAgain={vi.fn()} />,
    );
    expect(screen.getByText('¡Gracias por participar!')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /responder de nuevo/i })).not.toBeInTheDocument();
  });

  it('ofrece responder de nuevo y continuar con redirigir_url', () => {
    const onAgain = vi.fn();
    render(
      <ThankYouScreen
        message="Recibido"
        redirectUrl="https://ccf.co/gracias"
        canRespondAgain={true}
        onRespondAgain={onAgain}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: /responder de nuevo/i }));
    expect(onAgain).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('link', { name: /continuar/i })).toHaveAttribute('href', 'https://ccf.co/gracias');
  });
});

describe('QuestionRenderer — 11 tipos canónicos', () => {
  it('TEXTO_CORTO escribe y notifica cambios', () => {
    const q = makeQuestion({ titulo: 'Nombre completo', es_requerida: true });
    const onChange = vi.fn();
    render(
      <QuestionRenderer question={q} value={{ kind: 'text', text: '' }} onChange={onChange} highlightMissing={true} onUpload={noopUpload} />,
    );
    fireEvent.change(screen.getByLabelText('Nombre completo'), { target: { value: 'Ana Pérez' } });
    expect(onChange).toHaveBeenCalledWith({ kind: 'text', text: 'Ana Pérez' });
    expect(screen.getByRole('alert')).toHaveTextContent('Esta pregunta es obligatoria');
  });

  it('PARRAFO renderiza textarea', () => {
    const q = makeQuestion({ tipo_pregunta: SurveyQuestionType.PARRAFO, titulo: 'Comentarios' });
    render(
      <QuestionRenderer question={q} value={{ kind: 'text', text: '' }} onChange={vi.fn()} highlightMissing={false} onUpload={noopUpload} />,
    );
    expect(screen.getByLabelText('Comentarios')).toHaveProperty('tagName', 'TEXTAREA');
  });

  it('OPCION_MULTIPLE selecciona una única opción', () => {
    const q = makeQuestion({
      tipo_pregunta: SurveyQuestionType.OPCION_MULTIPLE,
      titulo: 'Color',
      opciones: [
        { id: 'op1', label: 'Rojo', salto_seccion_id: null, es_otro: false },
        { id: 'op2', label: 'Azul', salto_seccion_id: null, es_otro: false },
      ],
    });
    const onChange = vi.fn();
    render(
      <QuestionRenderer question={q} value={{ kind: 'choice', optionId: null }} onChange={onChange} highlightMissing={false} onUpload={noopUpload} />,
    );
    fireEvent.click(screen.getByRole('radio', { name: 'Rojo' }));
    expect(onChange).toHaveBeenCalledWith({ kind: 'choice', optionId: 'op1' });
  });

  it('CASILLAS permite selección múltiple', () => {
    const q = makeQuestion({
      tipo_pregunta: SurveyQuestionType.CASILLAS,
      titulo: 'Días',
      opciones: [
        { id: 'l', label: 'Lunes', salto_seccion_id: null, es_otro: false },
        { id: 'm', label: 'Martes', salto_seccion_id: null, es_otro: false },
      ],
    });
    const onChange = vi.fn();
    render(
      <QuestionRenderer question={q} value={{ kind: 'multi', optionIds: [] }} onChange={onChange} highlightMissing={false} onUpload={noopUpload} />,
    );
    fireEvent.click(screen.getByRole('checkbox', { name: 'Lunes' }));
    expect(onChange).toHaveBeenCalledWith({ kind: 'multi', optionIds: ['l'] });
  });

  it('DESPLEGABLE renderiza select con opciones', () => {
    const q = makeQuestion({
      tipo_pregunta: SurveyQuestionType.DESPLEGABLE,
      titulo: 'Sede',
      opciones: [{ id: 's1', label: 'Bogotá', salto_seccion_id: null, es_otro: false }],
    });
    const onChange = vi.fn();
    render(
      <QuestionRenderer question={q} value={{ kind: 'choice', optionId: null }} onChange={onChange} highlightMissing={false} onUpload={noopUpload} />,
    );
    fireEvent.change(screen.getByLabelText('Sede'), { target: { value: 's1' } });
    expect(onChange).toHaveBeenCalledWith({ kind: 'choice', optionId: 's1' });
  });

  it('ESCALA_LINEAL renderiza min..max y notifica el valor', () => {
    const q = makeQuestion({
      tipo_pregunta: SurveyQuestionType.ESCALA_LINEAL,
      titulo: 'Satisfacción',
      escala_min: 1,
      escala_max: 5,
    });
    const onChange = vi.fn();
    render(
      <QuestionRenderer question={q} value={{ kind: 'scale', value: null }} onChange={onChange} highlightMissing={false} onUpload={noopUpload} />,
    );
    fireEvent.click(screen.getByRole('radio', { name: '4' }));
    expect(onChange).toHaveBeenCalledWith({ kind: 'scale', value: 4 });
  });

  it('CUADRICULA_RADIO selecciona por fila', () => {
    const q = makeQuestion({
      tipo_pregunta: SurveyQuestionType.CUADRICULA_RADIO,
      titulo: 'Calidad',
      filas: [{ id: 'f1', label: 'Puntualidad' }],
      columnas: [{ id: 'c1', label: 'Malo' }, { id: 'c2', label: 'Excelente' }],
    });
    const onChange = vi.fn();
    render(
      <QuestionRenderer question={q} value={{ kind: 'grid', radio: {}, checks: {} }} onChange={onChange} highlightMissing={false} onUpload={noopUpload} />,
    );
    fireEvent.click(screen.getByRole('radio', { name: 'Puntualidad: Excelente' }));
    expect(onChange).toHaveBeenCalledWith({ kind: 'grid', radio: { f1: 'c2' }, checks: {} });
  });

  it('CUADRICULA_CASILLAS alterna casillas por fila', () => {
    const q = makeQuestion({
      tipo_pregunta: SurveyQuestionType.CUADRICULA_CASILLAS,
      titulo: 'Servicios',
      filas: [{ id: 'f1', label: 'Transporte' }],
      columnas: [{ id: 'c1', label: 'Usado' }, { id: 'c2', label: 'Recomendaría' }],
    });
    const onChange = vi.fn();
    render(
      <QuestionRenderer question={q} value={{ kind: 'grid', radio: {}, checks: {} }} onChange={onChange} highlightMissing={false} onUpload={noopUpload} />,
    );
    fireEvent.click(screen.getByRole('checkbox', { name: 'Transporte: Usado' }));
    expect(onChange).toHaveBeenCalledWith({ kind: 'grid', radio: {}, checks: { f1: ['c1'] } });
  });

  it('FECHA y HORA notifican el valor crudo', () => {
    const qd = makeQuestion({ tipo_pregunta: SurveyQuestionType.FECHA, titulo: 'Fecha nacimiento' });
    const onChangeD = vi.fn();
    const { unmount } = render(
      <QuestionRenderer question={qd} value={{ kind: 'date', date: '' }} onChange={onChangeD} highlightMissing={false} onUpload={noopUpload} />,
    );
    fireEvent.change(screen.getByLabelText('Fecha nacimiento'), { target: { value: '2026-09-30' } });
    expect(onChangeD).toHaveBeenCalledWith({ kind: 'date', date: '2026-09-30' });
    unmount();

    const qh = makeQuestion({ tipo_pregunta: SurveyQuestionType.HORA, titulo: 'Hora llegada' });
    const onChangeH = vi.fn();
    render(
      <QuestionRenderer question={qh} value={{ kind: 'time', time: '' }} onChange={onChangeH} highlightMissing={false} onUpload={noopUpload} />,
    );
    fireEvent.change(screen.getByLabelText('Hora llegada'), { target: { value: '14:30' } });
    expect(onChangeH).toHaveBeenCalledWith({ kind: 'time', time: '14:30' });
  });

  it('SUBIR_ARCHIVO valida tamaño, tipo y máximo antes de subir', async () => {
    const q = makeQuestion({
      tipo_pregunta: SurveyQuestionType.SUBIR_ARCHIVO,
      titulo: 'Recibo',
      archivo_tipos_permitidos: ['application/pdf'],
      archivo_max_mb: 1,
      archivo_max_archivos: 1,
    });
    const onUpload = vi.fn(async () => ({ url: 'u', filename: 'ok.pdf', size: 1, mime_type: 'application/pdf' }));
    render(
      <QuestionRenderer question={q} value={{ kind: 'files', files: [] }} onChange={vi.fn()} highlightMissing={false} onUpload={onUpload} />,
    );
    const input = screen.getByLabelText('Recibo') as HTMLInputElement;

    // Archivo demasiado grande → no llama al endpoint
    const big = new File([new ArrayBuffer(2 * 1024 * 1024)], 'big.pdf', { type: 'application/pdf' });
    Object.defineProperty(big, 'size', { value: 2 * 1024 * 1024 });
    await waitFor(async () => {
      fireEvent.change(input, { target: { files: [big] } });
    });
    expect(onUpload).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toHaveTextContent(/excede el máximo/);
  });

  it('SUBIR_ARCHIVO sube y lista el archivo resultante', async () => {
    const q = makeQuestion({
      tipo_pregunta: SurveyQuestionType.SUBIR_ARCHIVO,
      titulo: 'Recibo OK',
      archivo_tipos_permitidos: ['application/pdf'],
    });
    const onChange = vi.fn();
    const onUpload = vi.fn(async () => ({ url: '/uploads/surveys/ok.pdf', filename: 'ok.pdf', size: 5, mime_type: 'application/pdf' }));
    render(
      <QuestionRenderer question={q} value={{ kind: 'files', files: [] }} onChange={onChange} highlightMissing={false} onUpload={onUpload} />,
    );
    const input = screen.getByLabelText('Recibo OK') as HTMLInputElement;
    const file = new File(['pdf'], 'ok.pdf', { type: 'application/pdf' });
    await waitFor(() => {
      fireEvent.change(input, { target: { files: [file] } });
    });
    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith({
        kind: 'files',
        files: [{ url: '/uploads/surveys/ok.pdf', filename: 'ok.pdf', size: 5, mime_type: 'application/pdf' }],
      });
    });
  });

  it('SECCION_SALTO renderiza el encabezado de sección', () => {
    const q = makeQuestion({ tipo_pregunta: SurveyQuestionType.SECCION_SALTO, titulo: 'Datos de contacto' });
    render(
      <QuestionRenderer question={q} value={undefined} onChange={vi.fn()} highlightMissing={false} onUpload={noopUpload} />,
    );
    expect(screen.getByRole('heading', { name: 'Datos de contacto' })).toBeInTheDocument();
  });

  it('sin violaciones de accesibilidad en pregunta requerida vacía', async () => {
    const q = makeQuestion({ titulo: 'Pregunta accesible', es_requerida: true });
    const { container } = render(
      <QuestionRenderer question={q} value={{ kind: 'text', text: '' }} onChange={vi.fn()} highlightMissing={true} onUpload={noopUpload} />,
    );
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
