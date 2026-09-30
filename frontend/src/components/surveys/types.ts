/**
 * Tipos canónicos del módulo de Encuestas (Google Forms Parity).
 *
 * Espejo exacto de ``backend/schemas/surveys.py``:
 * - ``TipoPregunta`` (11 tipos + SECCION_SALTO)
 * - ``EncuestaFormularioPublicResponse`` (GET /api/public/surveys/{id})
 * - ``EncuestaSubmitRequest`` / ``EncuestaSubmitResponse`` (POST .../submit)
 *
 * Prohibido divergir de los nombres de campo del backend (contrato de API).
 */

export enum SurveyQuestionType {
  TEXTO_CORTO = 'TEXTO_CORTO',
  PARRAFO = 'PARRAFO',
  OPCION_MULTIPLE = 'OPCION_MULTIPLE',
  CASILLAS = 'CASILLAS',
  DESPLEGABLE = 'DESPLEGABLE',
  ESCALA_LINEAL = 'ESCALA_LINEAL',
  CUADRICULA_RADIO = 'CUADRICULA_RADIO',
  CUADRICULA_CASILLAS = 'CUADRICULA_CASILLAS',
  FECHA = 'FECHA',
  HORA = 'HORA',
  SUBIR_ARCHIVO = 'SUBIR_ARCHIVO',
  SECCION_SALTO = 'SECCION_SALTO',
}

export type SurveyQuestionTypeValues = `${SurveyQuestionType}`;

export const SURVEY_SECTION_BREAK = SurveyQuestionType.SECCION_SALTO as SurveyQuestionTypeValues;

export interface SurveyOption {
  id: string;
  label: string;
  salto_seccion_id: string | null;
  es_otro: boolean;
}

export interface SurveyRowColumn {
  id: string;
  label: string;
}

export interface SurveyQuestion {
  id: string;
  formulario_id: string;
  titulo: string;
  descripcion: string | null;
  tipo_pregunta: SurveyQuestionTypeValues;
  orden: number;
  es_requerida: boolean;
  opciones: Array<Record<string, unknown>>;
  filas: Array<Record<string, unknown>>;
  columnas: Array<Record<string, unknown>>;
  escala_min: number;
  escala_max: number;
  escala_min_etiqueta: string | null;
  escala_max_etiqueta: string | null;
  archivo_tipos_permitidos: string[];
  archivo_max_mb: number;
  archivo_max_archivos: number;
  configuracion: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface SurveyPublicDefinition {
  id: string;
  titulo: string;
  descripcion: string | null;
  slug: string | null;
  es_publico: boolean;
  requiere_autenticacion: boolean;
  mostrar_barra_progreso: boolean;
  mensaje_confirmacion: string | null;
  redirigir_url: string | null;
  estado: string;
  config_visual: Record<string, unknown>;
  preguntas: SurveyQuestion[];
}

export interface SurveyAnswerItem {
  pregunta_id: string;
  valor_texto: string | null;
  valor_numero: number | null;
  valor_fecha: string | null;
  valor_hora: string | null;
  valor_json: unknown;
}

export interface SurveySubmitPayload {
  respuestas: SurveyAnswerItem[];
  email_respondente: string | null;
  nombre_respondente: string | null;
  metadatos: Record<string, unknown>;
}

export interface SurveySubmitResponse {
  status: string;
  envio_id: string;
  mensaje_confirmacion: string;
  redirigir_url: string | null;
}

export interface SurveyFileUploadResult {
  url: string;
  filename: string;
  size: number;
  mime_type: string;
}
