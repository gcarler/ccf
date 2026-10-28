/**
 * TKT-PROJECTS-EVM-NA-PHASE1-20261028-01 — Presentación con flags de disponibilidad.
 *
 * Contrato con backend (`_DATA_QUALITY_LABELS` en
 * `backend/services/project_evm_service.py`): el backend NO inventa valores;
 * envía `*_available: false` + `data_quality` y conserva los placeholders
 * heredados. Este módulo es el ÚNICO punto donde el frontend traduce esos
 * estados; los componentes NUNCA deben renderizar índices con
 * `*_available === false` como si fueran medibles.
 */

/**
 * Etiquetas canónicas por código de calidad de datos.
 *
 * Códigos vigentes: espejo exacto de `DATA_QUALITY_LABELS` en
 * `backend/services/project_evm_service.py` (audit rev 1, hallazgo 1 — los
 * códigos ^no_transactions^/^baseline_not_active^/... nunca fueron emitidos por
 * el backend real). Los códigos antiguos se conservan al final solo por si algún
 * otro módulo todavía los emite.
 */
const DATA_QUALITY_LABELS: Record<string, string> = {
  sin_presupuesto: 'Sin presupuesto definido (BAC = 0)',
  sin_gastos: 'Sin gastos registrados (AC = 0)',
  sin_cronograma: 'Sin cronograma (sin fechas de inicio/fin válidas)',
  tareas_sin_fecha: 'Tareas sin fecha límite (PV no computable)',
  // Códigos anteriores — conservados solo por compatibilidad defensiva.
  no_transactions: 'Sin transacciones de costo registradas',
  baseline_not_active: 'Sin línea base autorizada',
  baseline_progress_not_available: 'Progreso de línea base no reportado',
  bac_zero: 'Presupuesto no definido (BAC = 0)',
  no_baseline: 'Sin línea base autorizada',
  unmeasurable: 'Indicador no calculable',
};

/** Texto legible para un código de calidad de datos (o el código tal cual). */
export function describeDataQuality(code: string): string {
  return DATA_QUALITY_LABELS[code] ?? code;
}

/** Etiquetas legibles para una lista de códigos de calidad de datos. */
export function describeDataQualityList(codes: string[] | undefined | null): string[] {
  if (!codes || codes.length === 0) return [];
  return codes.map(describeDataQuality);
}

export interface IndexDisplay {
  /** Texto a renderizar: el índice formateado o 'n/d'. */
  text: string;
  /** true cuando el índice NO es medible y debe presentarse como no disponible. */
  unavailable: boolean;
  /** Motivo(s) legible(s) de no disponibilidad (vacío si es medible). */
  reasons: string[];
}

/**
 * Formatea un índice (CPI/SPI/EAC) para presentación:
 * - disponible → `value.toFixed(2)`.
 * - no disponible → 'n/d' + motivos legibles. NUNCA muestra el placeholder.
 */
export function formatIndexOrNd(
  value: number,
  available: boolean | undefined,
  reasons: string[] | undefined | null,
): IndexDisplay {
  if (available === false) {
    return { text: 'n/d', unavailable: true, reasons: describeDataQualityList(reasons) };
  }
  return { text: value.toFixed(2), unavailable: false, reasons: [] };
}
