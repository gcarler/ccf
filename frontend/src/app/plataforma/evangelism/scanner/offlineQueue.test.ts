import { beforeEach, describe, expect, it, vi } from 'vitest';

// Mock de @/lib/http para capturar las llamadas al endpoint batch.
vi.mock('@/lib/http', () => {
  class ApiError extends Error {
    status: number;
    detail?: unknown;
    constructor(message: string, status: number, detail?: unknown) {
      super(message);
      this.status = status;
      this.detail = detail;
    }
  }
  return { apiFetch: vi.fn(), ApiError };
});

import { ApiError, apiFetch } from '@/lib/http';
import {
  clearOfflineQueue,
  enqueueOfflineCheckin,
  getPendingCheckins,
  identityHash,
  syncOfflineQueue,
} from './offlineQueue';

const apiFetchMock = vi.mocked(apiFetch);

const EVENT_A = '11111111-1111-4111-8111-111111111111';
const EVENT_B = '22222222-2222-4222-8222-222222222222';
const TOKEN_A = 'CCF-EVT-33333333-3333-4333-8333-333333333333-deadbeef';
const TOKEN_B = 'CCF-PER-44444444-4444-4444-8444-444444444444-cafebabe';
const PERSONA_A = '55555555-5555-4555-8555-555555555555';

describe('offlineQueue (TKT-EVANGELISM-OFFLINE-SYNC-01)', () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.clearAllMocks();
  });

  describe('identityHash', () => {
    it('es determinístico para la misma identidad', async () => {
      const a = await identityHash({ qrToken: TOKEN_A });
      const b = await identityHash({ qrToken: TOKEN_A });
      expect(a).toBe(b);
      expect(a).not.toBe('');
    });

    it('distingue token QR de persona_id', async () => {
      const byQr = await identityHash({ qrToken: TOKEN_A });
      const byPersona = await identityHash({ personaId: PERSONA_A });
      expect(byQr).not.toBe(byPersona);
    });
  });

  describe('enqueueOfflineCheckin', () => {
    it('encola un check-in offline y lo persiste en localStorage', async () => {
      const result = await enqueueOfflineCheckin({
        eventId: EVENT_A,
        sessionDate: '2026-10-01',
        qrToken: TOKEN_A,
      });
      expect(result.accepted).toBe(true);
      const queue = getPendingCheckins();
      expect(queue).toHaveLength(1);
      expect(queue[0].eventId).toBe(EVENT_A);
      expect(queue[0].sessionDate).toBe('2026-10-01');
      expect(queue[0].qrToken).toBe(TOKEN_A);
      expect(queue[0].identityKey).not.toBe('');
    });

    it('deduplica por identidad: el mismo QR no se encola dos veces', async () => {
      const first = await enqueueOfflineCheckin({
        eventId: EVENT_A,
        sessionDate: '2026-10-01',
        qrToken: TOKEN_A,
      });
      const second = await enqueueOfflineCheckin({
        eventId: EVENT_A,
        sessionDate: '2026-10-01',
        qrToken: TOKEN_A,
      });
      expect(first.accepted).toBe(true);
      expect(second.accepted).toBe(false);
      expect(getPendingCheckins()).toHaveLength(1);
    });

    it('acepta constatación manual por persona_id', async () => {
      const result = await enqueueOfflineCheckin({
        eventId: EVENT_A,
        sessionDate: '2026-10-01',
        personaId: PERSONA_A,
      });
      expect(result.accepted).toBe(true);
      expect(getPendingCheckins()[0].personaId).toBe(PERSONA_A);
    });

    it('rechaza items sin identidad', async () => {
      const result = await enqueueOfflineCheckin({
        eventId: EVENT_A,
        sessionDate: '2026-10-01',
      });
      expect(result.accepted).toBe(false);
      expect(getPendingCheckins()).toHaveLength(0);
    });
  });

  describe('syncOfflineQueue', () => {
    it('agrupa por evento/sesión, envía el lote y vacía la cola', async () => {
      await enqueueOfflineCheckin({ eventId: EVENT_A, sessionDate: '2026-10-01', qrToken: TOKEN_A });
      await enqueueOfflineCheckin({ eventId: EVENT_A, sessionDate: '2026-10-01', qrToken: TOKEN_B });

      apiFetchMock.mockResolvedValueOnce({
        status: 'success',
        synced: 1,
        duplicates: 1,
        errors: 0,
        results: [
          { index: 0, status: 'synced' },
          { index: 1, status: 'duplicate' },
        ],
      });

      const result = await syncOfflineQueue({ authToken: 'token-test' });
      expect(apiFetchMock).toHaveBeenCalledTimes(1);
      const [path] = apiFetchMock.mock.calls[0];
      expect(String(path)).toContain(`/evangelism/events/${EVENT_A}/sessions/2026-10-01/checkin-batch`);
      expect(result.synced).toBe(1);
      expect(result.duplicates).toBe(1);
      expect(result.remaining).toBe(0);
      expect(getPendingCheckins()).toHaveLength(0);
    });

    it('envía lotes separados por evento distinto', async () => {
      await enqueueOfflineCheckin({ eventId: EVENT_A, sessionDate: '2026-10-01', qrToken: TOKEN_A });
      await enqueueOfflineCheckin({ eventId: EVENT_B, sessionDate: '2026-10-01', qrToken: TOKEN_B });

      apiFetchMock.mockResolvedValue({
        status: 'success',
        synced: 1,
        duplicates: 0,
        errors: 0,
        results: [{ index: 0, status: 'synced' }],
      });

      const result = await syncOfflineQueue({});
      expect(apiFetchMock).toHaveBeenCalledTimes(2);
      expect(result.synced).toBe(2);
      expect(result.remaining).toBe(0);
    });

    it('conserva la cola y marca networkError cuando la red falla', async () => {
      await enqueueOfflineCheckin({ eventId: EVENT_A, sessionDate: '2026-10-01', qrToken: TOKEN_A });

      apiFetchMock.mockRejectedValueOnce(new ApiError('Network error', 0));

      const result = await syncOfflineQueue({});
      expect(result.networkError).toBe(true);
      expect(result.remaining).toBe(1);
      expect(getPendingCheckins()).toHaveLength(1);
      expect(getPendingCheckins()[0].attempts).toBe(1);
    });

    it('reporta errores por-item sin abortar el resto del lote', async () => {
      await enqueueOfflineCheckin({ eventId: EVENT_A, sessionDate: '2026-10-01', qrToken: TOKEN_A });
      await enqueueOfflineCheckin({ eventId: EVENT_A, sessionDate: '2026-10-01', qrToken: TOKEN_B });

      apiFetchMock.mockResolvedValueOnce({
        status: 'success',
        synced: 1,
        duplicates: 0,
        errors: 1,
        results: [
          { index: 0, status: 'synced' },
          { index: 1, status: 'error' },
        ],
      });

      const result = await syncOfflineQueue({});
      expect(result.synced).toBe(1);
      expect(result.errors).toBe(1);
      expect(result.remaining).toBe(1);
      const remaining = getPendingCheckins();
      expect(remaining).toHaveLength(1);
      expect(remaining[0].qrToken).toBe(TOKEN_B);
    });

    it('deduplica la re-sincronización: items ya confirmados no vuelven a enviarse', async () => {
      await enqueueOfflineCheckin({ eventId: EVENT_A, sessionDate: '2026-10-01', qrToken: TOKEN_A });
      apiFetchMock.mockResolvedValueOnce({
        status: 'success',
        synced: 1,
        duplicates: 0,
        errors: 0,
        results: [{ index: 0, status: 'synced' }],
      });
      await syncOfflineQueue({});

      // Segunda corrida sin nuevos escaneos: no debe llamar al endpoint.
      await syncOfflineQueue({});
      expect(apiFetchMock).toHaveBeenCalledTimes(1);
    });
  });

  describe('clearOfflineQueue', () => {
    it('descarta toda la cola', async () => {
      await enqueueOfflineCheckin({ eventId: EVENT_A, sessionDate: '2026-10-01', qrToken: TOKEN_A });
      expect(getPendingCheckins()).toHaveLength(1);
      clearOfflineQueue();
      expect(getPendingCheckins()).toHaveLength(0);
    });
  });
});
