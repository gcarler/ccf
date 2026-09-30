/**
 * Normalización y validación de respuestas de encuestas públicas.
 *
 * Lógica pura sin dependencias de React para poder testearse de forma
 * aislada. Espeja las columnas tipadas del backend
 * (``models_surveys.EncuestaRespuestaDetalle``): valor_texto, valor_numero,
 * valor_fecha, valor_hora, valor_json.
 */

import { SurveyAnswerItem, SurveyOption, SurveyQuestion, SurveyQuestionType } from './types';

/** Valor editable para una pregunta, inicializado según su tipo canónico. */
export type QuestionValue =
  | { kind: 'text'; text: string }
  | { kind: 'choice'; optionId: string | null }
  | { kind: 'multi'; optionIds: string[] }
  | { kind: 'scale'; value: number | null }
  | { kind: 'grid'; radio: Record<string, string>; checks: Record<string, string[]> }
  | { kind: 'date'; date: string }
  | { kind: 'time'; time: string }
  | { kind: 'files'; files: Array<{ url: string; filename: string; size: number; mime_type: string }> };

export type QuestionValues = Record<string, QuestionValue>;

/** Extensión inferida de un nombre de archivo (``reporte.pdf`` → ``pdf``). */
export function fileExtension(filename: string): string {
  const dot = filename.lastIndexOf('.');
  return dot === -1 ? '' : filename.slice(dot + 1).toLowerCase();
}

/**
 * True si el archivo cumple ``archivo_tipos_permitidos``.
 * Soporta: mimes exactos (``application/pdf``), wildcards por tipo
 * (``image/` + asterisco`), comodín universal, extensiones con punto
 * (``.pdf``) y extensiones sueltas (``pdf``).
 */
export function fileAllowed(question: SurveyQuestion, file: { name: string; type: string }): boolean {
  const allowed = (question.archivo_tipos_permitidos || []).filter(Boolean);
  if (allowed.length === 0) return true;
  const ext = fileExtension(file.name);
  const mime = (file.type || 'application/octet-stream').toLowerCase();
  return allowed.some((rule) => {
    const r = rule.trim().toLowerCase();
    if (!r) return false;
    if (r === '*/*') return true;
    if (r.startsWith('.')) return ext !== '' && `.${ext}` === r;
    if (r.includes('/')) {
      if (r.endsWith('/*')) return mime.startsWith(r.slice(0, -1));
      return mime === r;
    }
    return ext === r;
  });
}

/** Cast defensivo de opciones/filas/columnas JSONB hacia su interfaz tipada. */
export function parseOption(raw: Record<string, unknown>): SurveyOption {
  return {
    id: typeof raw.id === 'string' ? raw.id : String(raw.id ?? ''),
    label: typeof raw.label === 'string' ? raw.label : String(raw.label ?? ''),
    salto_seccion_id: typeof raw.salto_seccion_id === 'string' ? raw.salto_seccion_id : null,
    es_otro: raw.es_otro === true,
  };
}

export function parseRowCol(raw: Record<string, unknown>): { id: string; label: string } {
  return {
    id: typeof raw.id === 'string' ? raw.id : String(raw.id ?? ''),
    label: typeof raw.label === 'string' ? raw.label : String(raw.label ?? ''),
  };
}

/** Valor inicial para una pregunta según su tipo. */
export function initAnswerFor(question: SurveyQuestion): QuestionValue {
  switch (question.tipo_pregunta) {
    case SurveyQuestionType.OPCION_MULTIPLE:
    case SurveyQuestionType.DESPLEGABLE:
      return { kind: 'choice', optionId: null };
    case SurveyQuestionType.CASILLAS:
      return { kind: 'multi', optionIds: [] };
    case SurveyQuestionType.ESCALA_LINEAL:
      return { kind: 'scale', value: null };
    case SurveyQuestionType.CUADRICULA_RADIO:
      return { kind: 'grid', radio: {}, checks: {} };
    case SurveyQuestionType.CUADRICULA_CASILLAS:
      return { kind: 'grid', radio: {}, checks: {} };
    case SurveyQuestionType.FECHA:
      return { kind: 'date', date: '' };
    case SurveyQuestionType.HORA:
      return { kind: 'time', time: '' };
    case SurveyQuestionType.SUBIR_ARCHIVO:
      return { kind: 'files', files: [] };
    case SurveyQuestionType.TEXTO_CORTO:
    case SurveyQuestionType.PARRAFO:
    default:
      return { kind: 'text', text: '' };
  }
}

/** Valores iniciales para todas las preguntas del formulario. */
export function initValues(questions: SurveyQuestion[]): QuestionValues {
  const values: QuestionValues = {};
  for (const q of questions) values[q.id] = initAnswerFor(q);
  return values;
}

/** True si la respuesta está vacía (independiente del tipo). */
export function isAnswerEmpty(value: QuestionValue | undefined): boolean {
  if (!value) return true;
  switch (value.kind) {
    case 'text':
      return value.text.trim() === '';
    case 'choice':
      return !value.optionId;
    case 'multi':
      return value.optionIds.length === 0;
    case 'scale':
      return value.value === null;
    case 'grid': {
      const radioHasAny = Object.values(value.radio).some((v) => v !== '' && v !== null && v !== undefined);
      const checksHaveAny = Object.values(value.checks).some((arr) => arr.length > 0);
      return !radioHasAny && !checksHaveAny;
    }
    case 'date':
      return value.date === '';
    case 'time':
      return value.time === '';
    case 'files':
      return value.files.length === 0;
    default:
      return true;
  }
}

/** Igualdad estructural (misma pregunta + mismos valores) para saltos estables. */
export function answersEqual(a: QuestionValue | undefined, b: QuestionValue | undefined): boolean {
  if (!a || !b) return a === b;
  if (a.kind !== b.kind) return false;
  switch (a.kind) {
    case 'text':
      return a.text === (b as typeof a).text;
    case 'choice':
      return a.optionId === (b as typeof a).optionId;
    case 'multi': {
      const bb = b as typeof a;
      if (a.optionIds.length !== bb.optionIds.length) return false;
      const setB = new Set(bb.optionIds);
      return a.optionIds.every((id) => setB.has(id));
    }
    case 'scale':
      return a.value === (b as typeof a).value;
    case 'grid': {
      const bb = b as typeof a;
      const radioKeys = new Set([...Object.keys(a.radio), ...Object.keys(bb.radio)]);
      for (const key of radioKeys) {
        if (a.radio[key] !== bb.radio[key]) return false;
      }
      const checkKeys = new Set([...Object.keys(a.checks), ...Object.keys(bb.checks)]);
      for (const key of checkKeys) {
        const av = a.checks[key] ?? [];
        const bv = bb.checks[key] ?? [];
        if (av.length !== bv.length) return false;
        const setBv = new Set(bv);
        if (!av.every((id) => setBv.has(id))) return false;
      }
      return true;
    }
    case 'date':
      return a.date === (b as typeof a).date;
    case 'time':
      return a.time === (b as typeof a).time;
    case 'files': {
      const bb = b as typeof a;
      if (a.files.length !== bb.files.length) return false;
      return a.files.every((f, i) => f.url === bb.files[i]?.url);
    }
    default:
      return false;
  }
}

/** Divide preguntas en secciones: un SECCION_SALTO abre una página nueva. */
export function buildSectionsFromQuestions(questions: SurveyQuestion[]): SurveyQuestion[][] {
  const sections: SurveyQuestion[][] = [];
  let current: SurveyQuestion[] = [];
  for (const q of questions) {
    if (q.tipo_pregunta === SurveyQuestionType.SECCION_SALTO) {
      if (current.length > 0) sections.push(current);
      current = [q];
    } else {
      current.push(q);
    }
  }
  if (current.length > 0) sections.push(current);
  return sections;
}

/**
 * Resolución de saltos condicionales (paridad Google Forms):
 * 1. La opción elegida con ``salto_seccion_id`` manda (salto por respuesta).
 * 2. El SECCION_SALTO que abre la sección siguiente gobierna la transición
 *    desde la sección actual: su ``salto_seccion_id`` indica a qué sección
 *    continuar (o ``__submit__`` para terminar). Sin salto configurado,
 *    continúa a la sección siguiente.
 * 3. Fallback: sección siguiente.
 */
export function resolveNextSection(
  sections: SurveyQuestion[][],
  currentIndex: number,
  values: QuestionValues,
): number {
  const current = sections[currentIndex];
  if (!current) return Math.min(currentIndex + 1, Math.max(sections.length - 1, 0));

  for (const question of current) {
    if (question.tipo_pregunta !== SurveyQuestionType.OPCION_MULTIPLE) continue;
    const value = values[question.id];
    if (!value || value.kind !== 'choice' || !value.optionId) continue;
    const chosen = (question.opciones || []).map(parseOption).find((opt) => opt.id === value.optionId);
    if (chosen?.salto_seccion_id) {
      const target = sections.findIndex((section) => section.some((q) => q.id === chosen.salto_seccion_id));
      if (target >= 0) return target;
      if (chosen.salto_seccion_id === '__submit__') return sections.length;
    }
  }

  const nextSection = sections[currentIndex + 1];
  if (nextSection && nextSection[0]?.tipo_pregunta === SurveyQuestionType.SECCION_SALTO) {
    const jumpRaw = (nextSection[0].opciones || [])[0];
    const targetId = jumpRaw && typeof jumpRaw.salto_seccion_id === 'string' ? jumpRaw.salto_seccion_id : null;
    if (targetId) {
      const target = sections.findIndex((section) => section.some((q) => q.id === targetId));
      if (target >= 0) return target;
      if (targetId === '__submit__') return sections.length;
    }
  }
  return Math.min(currentIndex + 1, Math.max(sections.length - 1, 0));
}

/** Progreso de llenado (0-100) para la barra de progreso. */
export function surveyProgress(questions: SurveyQuestion[], values: QuestionValues): number {
  const answerable = questions.filter((q) => q.tipo_pregunta !== SurveyQuestionType.SECCION_SALTO);
  if (answerable.length === 0) return 0;
  const answered = answerable.filter((q) => !isAnswerEmpty(values[q.id])).length;
  return Math.round((answered / answerable.length) * 100);
}

/** Normaliza un valor editable al contrato de envío del backend. */
export function normalizeAnswerItem(question: SurveyQuestion, value: QuestionValue | undefined): SurveyAnswerItem {
  const base: SurveyAnswerItem = {
    pregunta_id: question.id,
    valor_texto: null,
    valor_numero: null,
    valor_fecha: null,
    valor_hora: null,
    valor_json: null,
  };
  if (!value) return base;
  switch (question.tipo_pregunta) {
    case SurveyQuestionType.TEXTO_CORTO:
    case SurveyQuestionType.PARRAFO:
      base.valor_texto = value.kind === 'text' && value.text.trim() !== '' ? value.text : null;
      break;
    case SurveyQuestionType.OPCION_MULTIPLE: {
      if (value.kind !== 'choice' || !value.optionId) break;
      const chosen = (question.opciones || []).map(parseOption).find((opt) => opt.id === value.optionId);
      if (chosen?.es_otro) {
        base.valor_texto = value.optionId;
      } else {
        base.valor_json = [value.optionId];
      }
      break;
    }
    case SurveyQuestionType.DESPLEGABLE:
      if (value.kind === 'choice' && value.optionId) base.valor_json = [value.optionId];
      break;
    case SurveyQuestionType.CASILLAS:
      if (value.kind === 'multi') base.valor_json = value.optionIds.length > 0 ? value.optionIds : null;
      break;
    case SurveyQuestionType.ESCALA_LINEAL:
      if (value.kind === 'scale' && value.value !== null) base.valor_numero = value.value;
      break;
    case SurveyQuestionType.CUADRICULA_RADIO: {
      if (value.kind !== 'grid') break;
      const filtered = Object.fromEntries(Object.entries(value.radio).filter(([, v]) => v !== '' && v != null));
      base.valor_json = Object.keys(filtered).length > 0 ? filtered : null;
      break;
    }
    case SurveyQuestionType.CUADRICULA_CASILLAS: {
      if (value.kind !== 'grid') break;
      const filtered = Object.fromEntries(
        Object.entries(value.checks)
          .map(([rowId, cols]) => [rowId, cols] as const)
          .filter(([, cols]) => cols.length > 0),
      );
      base.valor_json = Object.keys(filtered).length > 0 ? filtered : null;
      break;
    }
    case SurveyQuestionType.FECHA:
      base.valor_fecha = value.kind === 'date' && value.date !== '' ? value.date : null;
      break;
    case SurveyQuestionType.HORA:
      base.valor_hora = value.kind === 'time' && value.time !== '' ? value.time : null;
      break;
    case SurveyQuestionType.SUBIR_ARCHIVO:
      if (value.kind === 'files' && value.files.length > 0) {
        base.valor_json = value.files.map((f) => ({ url: f.url, filename: f.filename, size: f.size, mime_type: f.mime_type }));
      }
      break;
    case SurveyQuestionType.SECCION_SALTO:
    default:
      break;
  }
  return base;
}

/** Payload canónico completo para POST /surveys/{id}/submit. */
export function buildSubmitPayload(
  questions: SurveyQuestion[],
  values: QuestionValues,
  contact?: { email: string | null; nombre: string | null },
): SurveySubmitPayloadTypes {
  const respuestas = questions
    .filter((q) => q.tipo_pregunta !== SurveyQuestionType.SECCION_SALTO)
    .map((q) => normalizeAnswerItem(q, values[q.id]));
  return {
    respuestas,
    email_respondente: contact?.email?.trim() ? contact.email.trim() : null,
    nombre_respondente: contact?.nombre?.trim() ? contact.nombre.trim() : null,
    metadatos: {
      user_agent: typeof navigator !== 'undefined' ? navigator.userAgent : null,
      idioma: typeof navigator !== 'undefined' ? navigator.language : null,
    },
  };
}

// Alias para no importar el tipo desde types.ts en la firma (contrato estable).
type SurveySubmitPayloadTypes = import('./types').SurveySubmitPayload;

/** Preguntas obligatorias de una sección que están vacías (para bloquear avance). */
export function missingRequiredInSection(section: SurveyQuestion[], values: QuestionValues): SurveyQuestion[] {
  return section.filter(
    (q) => q.es_requerida && q.tipo_pregunta !== SurveyQuestionType.SECCION_SALTO && isAnswerEmpty(values[q.id]),
  );
}

/** Preguntas obligatorias de todo el formulario que están vacías. */
export function missingRequiredQuestions(questions: SurveyQuestion[], values: QuestionValues): SurveyQuestion[] {
  return questions.filter(
    (q) => q.es_requerida && q.tipo_pregunta !== SurveyQuestionType.SECCION_SALTO && isAnswerEmpty(values[q.id]),
  );
}
