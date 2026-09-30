/**
 * Fábrica de preguntas de prueba para los tests de encuestas.
 * Vive fuera de un archivo ``*.test.*`` para que vitest no la ejecute
 * como suite al importarla desde otros tests.
 */

import { SurveyQuestion } from '../types';

let seq = 0;

export function makeQuestion(overrides: Partial<SurveyQuestion> = {}): SurveyQuestion {
  seq += 1;
  return {
    id: `q_${seq}`,
    formulario_id: 'form_1',
    titulo: `Pregunta ${seq}`,
    descripcion: null,
    tipo_pregunta: 'TEXTO_CORTO',
    orden: seq,
    es_requerida: false,
    opciones: [],
    filas: [],
    columnas: [],
    escala_min: 1,
    escala_max: 5,
    escala_min_etiqueta: null,
    escala_max_etiqueta: null,
    archivo_tipos_permitidos: [],
    archivo_max_mb: 10,
    archivo_max_archivos: 1,
    configuracion: {},
    created_at: '2026-09-30T00:00:00Z',
    updated_at: '2026-09-30T00:00:00Z',
    ...overrides,
  };
}
