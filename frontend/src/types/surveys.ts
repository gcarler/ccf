/**
 * Tipos TypeScript estrictos para el módulo de Encuestas Dinámicas (Google Forms Parity).
 */

export type TipoPregunta =
    | "TEXTO_CORTO"
    | "PARRAFO"
    | "OPCION_MULTIPLE"
    | "CASILLAS"
    | "DESPLEGABLE"
    | "ESCALA_LINEAL"
    | "CUADRICULA_RADIO"
    | "CUADRICULA_CASILLAS"
    | "FECHA"
    | "HORA"
    | "SUBIR_ARCHIVO"
    | "SECCION_SALTO";

export type EstadoFormulario = "BORRADOR" | "PUBLICADO" | "CERRADO" | "ARCHIVADO";

export interface PreguntaOpcion {
    id: string;
    label: string;
    salto_seccion_id?: string | null;
    es_otro?: boolean;
}

export interface PreguntaMatrizItem {
    id: string;
    label: string;
}

export interface ConfigVisual {
    tema: string;
    color_primario: string;
    banner_url?: string | null;
    logo_url?: string | null;
    fuente: string;
}

export interface EncuestaPregunta {
    id: string;
    formulario_id?: string;
    titulo: string;
    descripcion?: string | null;
    tipo_pregunta: TipoPregunta;
    orden: number;
    es_requerida: boolean;
    opciones: PreguntaOpcion[];
    filas: PreguntaMatrizItem[];
    columnas: PreguntaMatrizItem[];
    escala_min: number;
    escala_max: number;
    escala_min_etiqueta?: string | null;
    escala_max_etiqueta?: string | null;
    archivo_tipos_permitidos: string[];
    archivo_max_mb: number;
    archivo_max_archivos: number;
    configuracion: Record<string, unknown>;
    created_at?: string;
    updated_at?: string;
}

export interface EncuestaFormulario {
    id: string;
    sede_id?: string | null;
    titulo: string;
    descripcion?: string | null;
    slug?: string | null;
    es_publico: boolean;
    requiere_autenticacion: boolean;
    limitar_una_respuesta: boolean;
    permitir_editar_respuesta: boolean;
    mostrar_barra_progreso: boolean;
    mensaje_confirmacion?: string | null;
    redirigir_url?: string | null;
    fecha_apertura?: string | null;
    fecha_cierre?: string | null;
    max_respuestas?: number | null;
    total_respuestas: number;
    estado: EstadoFormulario;
    config_visual: ConfigVisual;
    ajustes: Record<string, unknown>;
    creado_por_id?: string | null;
    is_active: boolean;
    created_at: string;
    updated_at: string;
    preguntas: EncuestaPregunta[];
}

export interface PreguntaAnalyticsSummary {
    pregunta_id: string;
    titulo: string;
    tipo_pregunta: TipoPregunta;
    total_respuestas: number;
    distribucion_opciones: Record<string, number>;
    promedio?: number | null;
    minimo?: number | null;
    maximo?: number | null;
    respuestas_recientes: string[];
}

export interface EncuestaAnalyticsSummary {
    formulario_id: string;
    titulo: string;
    total_respuestas: number;
    primera_respuesta?: string | null;
    ultima_respuesta?: string | null;
    preguntas: PreguntaAnalyticsSummary[];
}

export interface EncuestaRespuestasTableResponse {
    total: number;
    skip: number;
    limit: number;
    columnas: { key: string; label: string }[];
    filas: Record<string, unknown>[];
}

export interface EncuestaRespuestaDetalle {
    id: string;
    pregunta_id: string;
    valor_texto?: string | null;
    valor_numero?: number | null;
    valor_fecha?: string | null;
    valor_hora?: string | null;
    valor_json?: unknown;
}

export interface EncuestaRespuestaIndividual {
    id: string;
    formulario_id: string;
    persona_id?: string | null;
    usuario_id?: string | null;
    email_respondente?: string | null;
    nombre_respondente?: string | null;
    metadatos: Record<string, unknown>;
    created_at: string;
    detalles: EncuestaRespuestaDetalle[];
}
