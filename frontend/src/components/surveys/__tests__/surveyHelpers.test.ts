/**
 * Tests unitarios de la lógica pura del respondente público de encuestas.
 * TKT-SURVEYS-PUBLIC-RENDERER-01.
 */

import { describe, expect, it } from 'vitest';
import { SurveyQuestionType } from '../types';
import { makeQuestion } from './factories';
import {
  answersEqual,
  buildSectionsFromQuestions,
  buildSubmitPayload,
  fileAllowed,
  fileExtension,
  getVisibleQuestions,
  initValues,
  isAnswerEmpty,
  missingRequiredInSection,
  normalizeAnswerItem,
  resolveNextSection,
  surveyProgress,
} from '../surveyHelpers';

describe('fileExtension', () => {
  it('extrae la extensión en minúsculas', () => {
    expect(fileExtension('Informe.PDF')).toBe('pdf');
    expect(fileExtension('foto.jpeg')).toBe('jpeg');
  });

  it('devuelve vacío sin extensión', () => {
    expect(fileExtension('sinextension')).toBe('');
    expect(fileExtension('')).toBe('');
  });
});

describe('fileAllowed', () => {
  const base = makeQuestion({ tipo_pregunta: SurveyQuestionType.SUBIR_ARCHIVO });

  it('permite todo cuando no hay reglas', () => {
    expect(fileAllowed(base, { name: 'a.exe', type: 'application/x-msdownload' })).toBe(true);
  });

  it('acepta mime exacto', () => {
    const q = makeQuestion({ archivo_tipos_permitidos: ['application/pdf'] });
    expect(fileAllowed(q, { name: 'a.pdf', type: 'application/pdf' })).toBe(true);
    expect(fileAllowed(q, { name: 'a.png', type: 'image/png' })).toBe(false);
  });

  it('acepta wildcard de mime', () => {
    const q = makeQuestion({ archivo_tipos_permitidos: ['image/*'] });
    expect(fileAllowed(q, { name: 'a.png', type: 'image/png' })).toBe(true);
    expect(fileAllowed(q, { name: 'a.pdf', type: 'application/pdf' })).toBe(false);
  });

  it('acepta extensión con punto y suelta', () => {
    const q1 = makeQuestion({ archivo_tipos_permitidos: ['.docx'] });
    const q2 = makeQuestion({ archivo_tipos_permitidos: ['docx'] });
    expect(fileAllowed(q1, { name: 't.docx', type: '' })).toBe(true);
    expect(fileAllowed(q2, { name: 't.DOCX', type: '' })).toBe(true);
    expect(fileAllowed(q1, { name: 't.pdf', type: '' })).toBe(false);
  });

  it('acepta cualquier archivo con */*', () => {
    const q = makeQuestion({ archivo_tipos_permitidos: ['*/*'] });
    expect(fileAllowed(q, { name: 'a.zip', type: 'application/zip' })).toBe(true);
  });
});

describe('initValues e isAnswerEmpty', () => {
  it('inicializa cada tipo canónico con su valor vacío', () => {
    const qs = [
      makeQuestion({ tipo_pregunta: SurveyQuestionType.TEXTO_CORTO }),
      makeQuestion({ tipo_pregunta: SurveyQuestionType.PARRAFO }),
      makeQuestion({ tipo_pregunta: SurveyQuestionType.OPCION_MULTIPLE, opciones: [{ id: '1', label: 'A', salto_seccion_id: null, es_otro: false }] }),
      makeQuestion({ tipo_pregunta: SurveyQuestionType.CASILLAS }),
      makeQuestion({ tipo_pregunta: SurveyQuestionType.DESPLEGABLE }),
      makeQuestion({ tipo_pregunta: SurveyQuestionType.ESCALA_LINEAL }),
      makeQuestion({ tipo_pregunta: SurveyQuestionType.CUADRICULA_RADIO, filas: [{ id: 'f1', label: 'Fila' }], columnas: [{ id: 'c1', label: 'Col' }] }),
      makeQuestion({ tipo_pregunta: SurveyQuestionType.CUADRICULA_CASILLAS, filas: [{ id: 'f1', label: 'Fila' }], columnas: [{ id: 'c1', label: 'Col' }] }),
      makeQuestion({ tipo_pregunta: SurveyQuestionType.FECHA }),
      makeQuestion({ tipo_pregunta: SurveyQuestionType.HORA }),
      makeQuestion({ tipo_pregunta: SurveyQuestionType.SUBIR_ARCHIVO }),
    ];
    const values = initValues(qs);
    expect(values[qs[0].id]).toEqual({ kind: 'text', text: '' });
    expect(values[qs[2].id]).toEqual({ kind: 'choice', optionId: null });
    expect(values[qs[3].id]).toEqual({ kind: 'multi', optionIds: [] });
    expect(values[qs[5].id]).toEqual({ kind: 'scale', value: null });
    expect(values[qs[6].id]).toEqual({ kind: 'grid', radio: {}, checks: {} });
    expect(values[qs[8].id]).toEqual({ kind: 'date', date: '' });
    expect(values[qs[9].id]).toEqual({ kind: 'time', time: '' });
    expect(values[qs[10].id]).toEqual({ kind: 'files', files: [] });
    for (const q of qs) expect(isAnswerEmpty(values[q.id])).toBe(true);
  });

  it('isAnswerEmpty detecta contenido real', () => {
    expect(isAnswerEmpty({ kind: 'text', text: '  ' })).toBe(true);
    expect(isAnswerEmpty({ kind: 'text', text: 'hola' })).toBe(false);
    expect(isAnswerEmpty({ kind: 'scale', value: 3 })).toBe(false);
    expect(isAnswerEmpty({ kind: 'grid', radio: { f1: 'c1' }, checks: {} })).toBe(false);
    expect(isAnswerEmpty({ kind: 'grid', radio: {}, checks: { f1: ['c1'] } })).toBe(false);
    expect(isAnswerEmpty({ kind: 'files', files: [{ url: 'u', filename: 'f', size: 1, mime_type: 'm' }] })).toBe(false);
  });
});

describe('answersEqual', () => {
  it('compara textos y opciones', () => {
    expect(answersEqual({ kind: 'text', text: 'a' }, { kind: 'text', text: 'a' })).toBe(true);
    expect(answersEqual({ kind: 'text', text: 'a' }, { kind: 'text', text: 'b' })).toBe(false);
    expect(answersEqual({ kind: 'choice', optionId: '1' }, { kind: 'choice', optionId: '1' })).toBe(true);
    expect(answersEqual({ kind: 'choice', optionId: '1' }, { kind: 'choice', optionId: '2' })).toBe(false);
    expect(answersEqual({ kind: 'choice', optionId: '1' }, { kind: 'text', text: '1' })).toBe(false);
  });

  it('compara multi sin importar el orden', () => {
    expect(answersEqual({ kind: 'multi', optionIds: ['1', '2'] }, { kind: 'multi', optionIds: ['2', '1'] })).toBe(true);
    expect(answersEqual({ kind: 'multi', optionIds: ['1'] }, { kind: 'multi', optionIds: ['1', '2'] })).toBe(false);
  });

  it('compara cuadrículas completas', () => {
    const a = { kind: 'grid' as const, radio: { f1: 'c1' }, checks: { f2: ['c2'] } };
    const b = { kind: 'grid' as const, radio: { f1: 'c1' }, checks: { f2: ['c2'] } };
    const c = { kind: 'grid' as const, radio: { f1: 'c2' }, checks: { f2: ['c2'] } };
    expect(answersEqual(a, b)).toBe(true);
    expect(answersEqual(a, c)).toBe(false);
  });

  it('compara listas de archivos por url', () => {
    const f1 = { url: 'u1', filename: 'a', size: 1, mime_type: 'm' };
    const f2 = { url: 'u2', filename: 'b', size: 2, mime_type: 'm' };
    expect(answersEqual({ kind: 'files', files: [f1] }, { kind: 'files', files: [f1] })).toBe(true);
    expect(answersEqual({ kind: 'files', files: [f1] }, { kind: 'files', files: [f2] })).toBe(false);
  });
});

describe('buildSectionsFromQuestions', () => {
  it('sin secciones devuelve una sola página', () => {
    const qs = [makeQuestion(), makeQuestion()];
    const sections = buildSectionsFromQuestions(qs);
    expect(sections).toHaveLength(1);
    expect(sections[0]).toHaveLength(2);
  });

  it('SECCION_SALTO abre página nueva', () => {
    const qs = [
      makeQuestion(),
      makeQuestion({ tipo_pregunta: SurveyQuestionType.SECCION_SALTO }),
      makeQuestion(),
    ];
    const sections = buildSectionsFromQuestions(qs);
    expect(sections).toHaveLength(2);
    expect(sections[1][0].tipo_pregunta).toBe(SurveyQuestionType.SECCION_SALTO);
  });

  it('SECCION_SALTO inicial abre la primera página', () => {
    const sections = buildSectionsFromQuestions([
      makeQuestion({ tipo_pregunta: SurveyQuestionType.SECCION_SALTO }),
      makeQuestion(),
    ]);
    expect(sections).toHaveLength(1);
  });
});

describe('lógica condicional de visibilidad', () => {
  it('evalúa respuestas seleccionadas y oculta dependencias encadenadas si su origen no está visible', () => {
    const source = makeQuestion({
      tipo_pregunta: SurveyQuestionType.OPCION_MULTIPLE,
      opciones: [{ id: 'yes', label: 'Sí', salto_seccion_id: null, es_otro: false }],
    });
    const dependent = makeQuestion({
      configuracion: { visible_if: { pregunta_id: source.id, operador: 'igual_a', opcion_id: 'yes' } },
    });
    const chained = makeQuestion({
      configuracion: { visible_if: { pregunta_id: dependent.id, operador: 'igual_a', opcion_id: 'yes' } },
    });
    const questions = [source, dependent, chained];
    const values = initValues(questions);

    expect(getVisibleQuestions(questions, values).map((question) => question.id)).toEqual([source.id]);
    values[source.id] = { kind: 'choice', optionId: 'yes' };
    expect(getVisibleQuestions(questions, values).map((question) => question.id)).toEqual([source.id, dependent.id]);
  });

  it('omite preguntas ocultas del payload de envío', () => {
    const source = makeQuestion({
      tipo_pregunta: SurveyQuestionType.OPCION_MULTIPLE,
      opciones: [{ id: 'yes', label: 'Sí', salto_seccion_id: null, es_otro: false }],
    });
    const dependent = makeQuestion({
      configuracion: { visible_if: { pregunta_id: source.id, operador: 'igual_a', opcion_id: 'yes' } },
    });
    const values = initValues([source, dependent]);
    const payload = buildSubmitPayload([source, dependent], values);
    expect(payload.respuestas.map((answer) => answer.pregunta_id)).toEqual([source.id]);
  });
});

describe('resolveNextSection', () => {
  it('avanza a la sección siguiente por defecto', () => {
    const sections = buildSectionsFromQuestions([makeQuestion(), makeQuestion()]);
    expect(resolveNextSection(sections, 0, initValues(sections.flat()))).toBe(sections.length - 1);
  });

  it('la opción con salto_seccion_id manda', () => {
    const q0 = makeQuestion({
      tipo_pregunta: SurveyQuestionType.OPCION_MULTIPLE,
      opciones: [{ id: 'op_yes', label: 'Sí', salto_seccion_id: null, es_otro: false }],
    });
    const sectionBreak = makeQuestion({ tipo_pregunta: SurveyQuestionType.SECCION_SALTO });
    const q2 = makeQuestion();
    const sections = buildSectionsFromQuestions([q0, sectionBreak, q2]);
    // El id del salto de sección es el id del SECCION_SALTO (sectionBreak.id)
    const values = initValues(sections.flat());
    values[q0.id] = { kind: 'choice', optionId: 'op_yes' };
    // sin salto configurado → siguiente (1)
    expect(resolveNextSection(sections, 0, values)).toBe(1);
    // con salto configurado hacia la sección que contiene sectionBreak
    const q0b = {
      ...q0,
      opciones: [{ id: 'op_yes', label: 'Sí', salto_seccion_id: sectionBreak.id, es_otro: false }],
    };
    const sectionsB = buildSectionsFromQuestions([
      q0b,
      sectionBreak,
      q2,
    ]);
    expect(resolveNextSection(sectionsB, 0, values)).toBe(1);
    // salto directo al final (__submit__)
    const q0c = {
      ...q0,
      opciones: [{ id: 'op_yes', label: 'Sí', salto_seccion_id: '__submit__', es_otro: false }],
    };
    const sectionsC = buildSectionsFromQuestions([q0c, sectionBreak, q2]);
    expect(resolveNextSection(sectionsC, 0, values)).toBe(sectionsC.length);
  });

  it('el salto del SECCION_SALTO que abre la siguiente sección gobierna la transición', () => {
    const q1 = makeQuestion();
    const jump = makeQuestion({
      tipo_pregunta: SurveyQuestionType.SECCION_SALTO,
      opciones: [{ salto_seccion_id: '__submit__' }],
    });
    const q2 = makeQuestion();
    // El SECCION_SALTO abre la sección 1: su salto decide qué pasa tras la sección 0.
    const sections = buildSectionsFromQuestions([q1, jump, q2]);
    expect(sections).toHaveLength(2);
    expect(resolveNextSection(sections, 0, initValues(sections.flat()))).toBe(sections.length);
  });
});

describe('surveyProgress', () => {
  it('0% sin respuestas, 100% completas', () => {
    const qs = [makeQuestion(), makeQuestion()];
    const values = initValues(qs);
    expect(surveyProgress(qs, values)).toBe(0);
    values[qs[0].id] = { kind: 'text', text: 'x' };
    expect(surveyProgress(qs, values)).toBe(50);
    values[qs[1].id] = { kind: 'text', text: 'y' };
    expect(surveyProgress(qs, values)).toBe(100);
  });

  it('ignora SECCION_SALTO', () => {
    const qs = [makeQuestion(), makeQuestion({ tipo_pregunta: SurveyQuestionType.SECCION_SALTO })];
    const values = initValues(qs);
    values[qs[0].id] = { kind: 'text', text: 'x' };
    expect(surveyProgress(qs, values)).toBe(100);
  });
});

describe('normalizeAnswerItem', () => {
  it('TEXTO_CORTO mapea a valor_texto', () => {
    const q = makeQuestion({ tipo_pregunta: SurveyQuestionType.TEXTO_CORTO });
    const item = normalizeAnswerItem(q, { kind: 'text', text: '  Hola  ' });
    expect(item.valor_texto).toBe('  Hola  ');
    expect(item.valor_json).toBeNull();
  });

  it('OPCION_MULTIPLE normal emite valor_json con [optionId]', () => {
    const q = makeQuestion({
      tipo_pregunta: SurveyQuestionType.OPCION_MULTIPLE,
      opciones: [{ id: 'op1', label: 'A', salto_seccion_id: null, es_otro: false }],
    });
    const item = normalizeAnswerItem(q, { kind: 'choice', optionId: 'op1' });
    expect(item.valor_json).toEqual(['op1']);
  });

  it('OPCION_MULTIPLE "Otro" emite valor_texto (texto libre del backend)', () => {
    const q = makeQuestion({
      tipo_pregunta: SurveyQuestionType.OPCION_MULTIPLE,
      opciones: [{ id: 'otro', label: 'Otro', salto_seccion_id: null, es_otro: true }],
    });
    const item = normalizeAnswerItem(q, { kind: 'choice', optionId: 'otro' });
    expect(item.valor_texto).toBe('otro');
    expect(item.valor_json).toBeNull();
  });

  it('CASILLAS emite lista de ids', () => {
    const q = makeQuestion({ tipo_pregunta: SurveyQuestionType.CASILLAS });
    const item = normalizeAnswerItem(q, { kind: 'multi', optionIds: ['a', 'b'] });
    expect(item.valor_json).toEqual(['a', 'b']);
  });

  it('ESCALA_LINEAL emite valor_numero', () => {
    const q = makeQuestion({ tipo_pregunta: SurveyQuestionType.ESCALA_LINEAL, escala_min: 1, escala_max: 10 });
    const item = normalizeAnswerItem(q, { kind: 'scale', value: 7 });
    expect(item.valor_numero).toBe(7);
  });

  it('CUADRICULA_RADIO emite dict fila→columna', () => {
    const q = makeQuestion({ tipo_pregunta: SurveyQuestionType.CUADRICULA_RADIO });
    const item = normalizeAnswerItem(q, { kind: 'grid', radio: { f1: 'c1', f2: '' }, checks: {} });
    expect(item.valor_json).toEqual({ f1: 'c1' });
  });

  it('CUADRICULA_CASILLAS emite dict fila→[columnas]', () => {
    const q = makeQuestion({ tipo_pregunta: SurveyQuestionType.CUADRICULA_CASILLAS });
    const item = normalizeAnswerItem(q, { kind: 'grid', radio: {}, checks: { f1: ['c1', 'c2'], f2: [] } });
    expect(item.valor_json).toEqual({ f1: ['c1', 'c2'] });
  });

  it('FECHA y HORA emiten sus columnas tipadas', () => {
    const qd = makeQuestion({ tipo_pregunta: SurveyQuestionType.FECHA });
    const qh = makeQuestion({ tipo_pregunta: SurveyQuestionType.HORA });
    expect(normalizeAnswerItem(qd, { kind: 'date', date: '2026-09-30' }).valor_fecha).toBe('2026-09-30');
    expect(normalizeAnswerItem(qh, { kind: 'time', time: '14:30' }).valor_hora).toBe('14:30');
  });

  it('SUBIR_ARCHIVO emite la lista canónica de archivos', () => {
    const q = makeQuestion({ tipo_pregunta: SurveyQuestionType.SUBIR_ARCHIVO });
    const item = normalizeAnswerItem(q, {
      kind: 'files',
      files: [{ url: '/uploads/surveys/x.png', filename: 'x.png', size: 10, mime_type: 'image/png' }],
    });
    expect(item.valor_json).toEqual([
      { url: '/uploads/surveys/x.png', filename: 'x.png', size: 10, mime_type: 'image/png' },
    ]);
  });
});

describe('buildSubmitPayload', () => {
  it('construye el contrato canónico completo', () => {
    const qs = [
      makeQuestion({ tipo_pregunta: SurveyQuestionType.TEXTO_CORTO }),
      makeQuestion({ tipo_pregunta: SurveyQuestionType.SECCION_SALTO }),
      makeQuestion({ tipo_pregunta: SurveyQuestionType.ESCALA_LINEAL }),
    ];
    const values = initValues(qs);
    values[qs[0].id] = { kind: 'text', text: 'respuesta' };
    values[qs[2].id] = { kind: 'scale', value: 4 };
    const payload = buildSubmitPayload(qs, values, { email: ' a@b.co ', nombre: 'Ana' });
    expect(payload.respuestas).toHaveLength(2); // excluye SECCION_SALTO
    expect(payload.respuestas[0].valor_texto).toBe('respuesta');
    expect(payload.respuestas[1].valor_numero).toBe(4);
    expect(payload.email_respondente).toBe('a@b.co');
    expect(payload.nombre_respondente).toBe('Ana');
    expect(payload.metadatos).toHaveProperty('user_agent');
  });

  it('normaliza contacto vacío a null', () => {
    const qs = [makeQuestion()];
    const payload = buildSubmitPayload(qs, initValues(qs), { email: '   ', nombre: '' });
    expect(payload.email_respondente).toBeNull();
    expect(payload.nombre_respondente).toBeNull();
  });
});

describe('missingRequiredInSection', () => {
  it('reporta solo las requeridas vacías de la sección', () => {
    const q1 = makeQuestion({ es_requerida: true });
    const q2 = makeQuestion({ es_requerida: false });
    const section = [q1, q2];
    const values = initValues(section);
    expect(missingRequiredInSection(section, values)).toEqual([q1]);
    values[q1.id] = { kind: 'text', text: 'ok' };
    expect(missingRequiredInSection(section, values)).toEqual([]);
  });
});
