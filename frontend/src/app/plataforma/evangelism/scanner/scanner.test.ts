import { describe, it, expect } from 'vitest';
import { sanitizeAndExtractQrToken } from './utils';

describe('sanitizeAndExtractQrToken', () => {
  it('extracts token from a full HTTP URL with token query parameter', () => {
    const url = 'https://comunidadccf.org/public/events/1a2b3c/qr?token=CCF-EVT-1a2b3c-uuid456';
    expect(sanitizeAndExtractQrToken(url)).toBe('CCF-EVT-1a2b3c-uuid456');
  });

  it('extracts token from a full URL with multiple query parameters', () => {
    const url = 'http://localhost:3000/public/events/1a2b3c/qr?source=gate&token=CCF-PER-person789&lang=es';
    expect(sanitizeAndExtractQrToken(url)).toBe('CCF-PER-person789');
  });

  it('decodes URI encoded tokens in URL parameters', () => {
    const url = 'https://ccf.church/qr?token=CCF-EVT-sample%20token%2D123';
    expect(sanitizeAndExtractQrToken(url)).toBe('CCF-EVT-sample token-123');
  });

  it('extracts CCF-EVT- prefix when embedded in text or barcode prefix', () => {
    const raw = 'SCAN:CCF-EVT-d0d5718a-9f5b-42e7-9d7a-d0b8f2d5041a:OK';
    expect(sanitizeAndExtractQrToken(raw)).toBe('CCF-EVT-d0d5718a-9f5b-42e7-9d7a-d0b8f2d5041a');
  });

  it('extracts CCF-PER- prefix when embedded in text', () => {
    const raw = 'USER/CCF-PER-e1e5718a-9f5b-42e7-9d7a-d0b8f2d5041b';
    expect(sanitizeAndExtractQrToken(raw)).toBe('CCF-PER-e1e5718a-9f5b-42e7-9d7a-d0b8f2d5041b');
  });

  it('returns clean token when passed directly without formatting', () => {
    const plainToken = 'CCF-EVT-a8b9c0d1-e2f3';
    expect(sanitizeAndExtractQrToken(plainToken)).toBe('CCF-EVT-a8b9c0d1-e2f3');
  });

  it('returns empty string for empty or whitespace-only inputs', () => {
    expect(sanitizeAndExtractQrToken('')).toBe('');
    expect(sanitizeAndExtractQrToken('   ')).toBe('');
  });
});
