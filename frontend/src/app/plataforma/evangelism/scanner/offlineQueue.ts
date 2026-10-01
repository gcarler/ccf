/**
 * Cola offline de check-ins para el Scanner QR (Gatekeeper).
 *
 * TKT-EVANGELISM-OFFLINE-SYNC-01: cuando el dispositivo no tiene conexión
 * (`navigator.onLine === false` o fallo de red con `ApiError.status === 0`),
 * los registros de check-in se acumulan en `localStorage` y se sincronizan en
 * lote contra `POST /evangelism/events/{id}/sessions/{date}/checkin-batch` al
 * recuperar conectividad. La deduplicación por hash de identidad evita encolar
 * dos veces la misma credencial, incluso entre sesiones del navegador.
 *
 * Contrato de tres capas contra duplicados (espejo del backend):
 *   1. Cola local (este módulo, hash de identidad).
 *   2. Schema `CheckinBatchPayload` (dedupe dentro del lote).
 *   3. Endpoint idempotente contra `EventAttendance` existente.
 */

import { ApiError, apiFetch } from '@/lib/http';

const STORAGE_KEY = 'ccf_scanner_offline_queue_v1';

/** Tamaño máximo de lote aceptado por `CheckinBatchPayload`. */
const BATCH_CHUNK = 200;

export interface StoredCheckin {
  /** Identificador de la entrada en cola (UUIDv4 con fallback). */
  id: string;
  /** UUID del evento resuelto al momento del escaneo. */
  eventId: string;
  /** Fecha de sesión YYYY-MM-DD resuelta al momento del escaneo. */
  sessionDate: string;
  /** Token QR canonizado (CCF-EVT- / CCF-PER-), si aplica. */
  qrToken?: string;
  /** UUID de persona para constatación manual, si aplica. */
  personaId?: string;
  /** Hash de identidad para dedupe (SHA-256 con fallback determinístico). */
  identityKey: string;
  /** Instante ISO del escaneo original en puerta. */
  scannedAt: string;
  /** Número de intentos de sincronización fallidos. */
  attempts: number;
}

export interface SyncResult {
  /** Items enviados al servidor en este ciclo. */
  attempted: number;
  synced: number;
  duplicates: number;
  errors: number;
  /** Items saltados por falta de evento/fecha resoluble. */
  skipped: number;
  /** Tamaño de la cola tras la sincronización. */
  remaining: number;
  /** true si algún lote falló por red (la cola se conserva intacta). */
  networkError: boolean;
}

export interface EnqueueInput {
  eventId: string;
  sessionDate: string;
  qrToken?: string;
  personaId?: string;
  scannedAt?: string;
}

export interface EnqueueResult {
  accepted: boolean;
  queueSize: number;
}

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

function newQueueId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `q-${Date.now().toString(16)}-${Math.random().toString(16).slice(2, 10)}`;
}

function isUuidLike(value: unknown): value is string {
  return typeof value === 'string' && UUID_RE.test(value);
}

/**
 * Hash estable de la identidad del participante (token QR o UUID de persona)
 * usado como clave de dedupe de la cola.
 */
export async function identityHash(input: { qrToken?: string; personaId?: string }): Promise<string> {
  const canonical = input.qrToken ? `qr:${input.qrToken.trim()}` : `pid:${input.personaId ?? ''}`;
  try {
    if (typeof crypto !== 'undefined' && 'subtle' in crypto) {
      const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(canonical));
      return Array.from(new Uint8Array(digest))
        .map((b) => b.toString(16).padStart(2, '0'))
        .join('');
    }
  } catch {
    // crypto.subtle indisponible (contexto no seguro): cae al hash local.
  }
  let h1 = 0x811c9dc5;
  let h2 = 0x01000193;
  for (let i = 0; i < canonical.length; i++) {
    const ch = canonical.charCodeAt(i);
    h1 = ((h1 ^ ch) * 0x01000193) >>> 0;
    h2 = ((h2 + ch) * 0x85ebca6b) >>> 0;
  }
  return `fb-${h1.toString(16)}-${h2.toString(16)}`;
}

function canonicalKeyOf(item: Pick<StoredCheckin, 'qrToken' | 'personaId'>): string {
  return item.qrToken ? `qr:${item.qrToken.trim()}` : `pid:${item.personaId ?? ''}`;
}

/**
 * Normaliza y filtra registros leídos de localStorage: cualquier item corrupto
 * (sin identidad, sin evento/fecha válidos o con fechas NaN) se descarta en
 * lugar de romper la sincronización completa de la puerta.
 */
function normalizeStoredCheckin(raw: unknown): StoredCheckin | null {
  if (!raw || typeof raw !== 'object') return null;
  const rec = raw as Record<string, unknown>;
  const qrToken =
    typeof rec.qrToken === 'string' && rec.qrToken.trim() ? rec.qrToken.trim() : undefined;
  const personaId = isUuidLike(rec.personaId) ? rec.personaId : undefined;
  const eventId = isUuidLike(rec.eventId) ? rec.eventId : undefined;
  const sessionDate =
    typeof rec.sessionDate === 'string' && DATE_RE.test(rec.sessionDate) ? rec.sessionDate : undefined;
  if (!qrToken && !personaId) return null;
  if (!eventId || !sessionDate) return null;
  const scannedAtMs = Date.parse(typeof rec.scannedAt === 'string' ? rec.scannedAt : '');
  const attempts =
    typeof rec.attempts === 'number' && Number.isFinite(rec.attempts)
      ? Math.max(0, Math.floor(rec.attempts))
      : 0;
  const identityKey =
    typeof rec.identityKey === 'string' && rec.identityKey
      ? rec.identityKey
      : canonicalKeyOf({ qrToken, personaId });
  return {
    id: typeof rec.id === 'string' && rec.id ? rec.id : newQueueId(),
    eventId,
    sessionDate,
    qrToken,
    personaId,
    identityKey,
    scannedAt: Number.isFinite(scannedAtMs) ? new Date(scannedAtMs).toISOString() : new Date(0).toISOString(),
    attempts,
  };
}

function readQueue(): StoredCheckin[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map(normalizeStoredCheckin)
      .filter((item): item is StoredCheckin => item !== null);
  } catch {
    return [];
  }
}

function writeQueue(queue: StoredCheckin[]): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(queue));
  } catch {
    // Cuota agotada o storage bloqueado: la cola se reintentará en el próximo
    // escaneo; el flujo de puerta nunca se interrumpe por storage.
  }
}

/** Snapshot inmutable de los check-ins pendientes de sincronizar. */
export function getPendingCheckins(): StoredCheckin[] {
  return readQueue();
}

/** Descarta toda la cola local (acción explícita del operador). */
export function clearOfflineQueue(): void {
  writeQueue([]);
}

/**
 * Encola un check-in si su identidad no está ya pendiente en la cola.
 * Dedupe por hash de identidad: el mismo QR o persona escaneado dos veces
 * offline (o en sesiones distintas) nunca genera dos entradas.
 */
export async function enqueueOfflineCheckin(input: EnqueueInput): Promise<EnqueueResult> {
  const qrToken = input.qrToken?.trim() || undefined;
  const personaId = input.personaId?.trim() || undefined;
  const queue = readQueue();
  if (!qrToken && !personaId) {
    return { accepted: false, queueSize: queue.length };
  }
  const key = await identityHash({ qrToken, personaId });
  if (
    queue.some(
      (item) => item.identityKey === key || canonicalKeyOf(item) === canonicalKeyOf({ qrToken, personaId }),
    )
  ) {
    return { accepted: false, queueSize: queue.length };
  }
  queue.push({
    id: newQueueId(),
    eventId: input.eventId,
    sessionDate: input.sessionDate,
    qrToken,
    personaId,
    identityKey: key,
    scannedAt: input.scannedAt || new Date().toISOString(),
    attempts: 0,
  });
  writeQueue(queue);
  return { accepted: true, queueSize: queue.length };
}

interface BatchApiResponse {
  status?: string;
  synced?: number;
  duplicates?: number;
  errors?: number;
  results?: Array<{ index?: number; status?: string }>;
}

/**
 * Sincroniza la cola offline en lote (agrupada por evento/sesión y troceada en
 * chunks de `BATCH_CHUNK`). No lanza: los lotes que fallan por red conservan
 * sus items (con `attempts` incrementado) y marcan `networkError`.
 *
 * El backend es idempotente: los items ya registrados vuelven como
 * `duplicate` y se eliminan de la cola sin duplicar asistencia.
 */
export async function syncOfflineQueue(options: {
  authToken?: string | null;
}): Promise<SyncResult> {
  const queue = readQueue();
  const result: SyncResult = {
    attempted: 0,
    synced: 0,
    duplicates: 0,
    errors: 0,
    skipped: 0,
    remaining: queue.length,
    networkError: false,
  };
  if (queue.length === 0) return result;

  // Agrupar por evento/sesión: el endpoint es por evento y fecha de sesión.
  const groups = new Map<string, StoredCheckin[]>();
  for (const item of queue) {
    if (!isUuidLike(item.eventId) || !DATE_RE.test(item.sessionDate)) {
      result.skipped += 1;
      continue;
    }
    const key = `${item.eventId}|${item.sessionDate}`;
    const group = groups.get(key);
    if (group) group.push(item);
    else groups.set(key, [item]);
  }

  const failed: StoredCheckin[] = [];

  for (const [, items] of groups) {
    const indexed = items.map((item, index) => ({ item, index }));
    for (let start = 0; start < indexed.length; start += BATCH_CHUNK) {
      const chunk = indexed.slice(start, start + BATCH_CHUNK);
      const payloadItems: Array<{ qr_token?: string; persona_id?: string }> = chunk.map(
        ({ item }) => (item.qrToken ? { qr_token: item.qrToken } : { persona_id: item.personaId ?? '' }),
      );
      const [eventId, sessionDate] = items[0] ? [items[0].eventId, items[0].sessionDate] : [''];
      if (!eventId || !sessionDate) {
        result.skipped += chunk.length;
        continue;
      }
      result.attempted += chunk.length;
      try {
        const response = await apiFetch<BatchApiResponse>(
          `/evangelism/events/${eventId}/sessions/${sessionDate}/checkin-batch`,
          {
            method: 'POST',
            body: { items: payloadItems },
            token: options.authToken ?? undefined,
            silent: true,
          },
        );
        const okLocal = new Set<number>();
        for (const r of response?.results ?? []) {
          if (typeof r?.index === 'number' && (r.status === 'synced' || r.status === 'duplicate')) {
            okLocal.add(r.index);
          }
        }
        let chunkOk = 0;
        chunk.forEach(({ item }, localIdx) => {
          if (okLocal.has(localIdx)) {
            chunkOk += 1;
          } else {
            item.attempts += 1;
            failed.push(item);
          }
        });
        if ((response?.results ?? []).length > 0) {
          result.synced += typeof response.synced === 'number' ? response.synced : chunkOk;
          result.duplicates += typeof response.duplicates === 'number' ? response.duplicates : 0;
          result.errors += chunk.length - chunkOk;
        } else if (response?.status === 'success') {
          // Respuesta sin detalle por-item: el lote completo fue aceptado.
          result.synced += chunk.length;
        } else {
          for (const { item } of chunk) {
            item.attempts += 1;
            failed.push(item);
          }
          result.errors += chunk.length;
        }
      } catch (err) {
        // Red caída u otro fallo transitorio: el chunk completo se reencola.
        result.networkError = true;
        if (err instanceof ApiError && err.status === 0) {
          for (const { item } of chunk) {
            item.attempts += 1;
            failed.push(item);
          }
        } else {
          // 4xx/5xx del lote completo (permisos/evento): reencolar para
          // reintento posterior; los items se reportan como errores.
          for (const { item } of chunk) {
            item.attempts += 1;
            failed.push(item);
          }
          result.errors += chunk.length;
        }
      }
    }
  }

  writeQueue(failed);
  result.remaining = failed.length;
  return result;
}
