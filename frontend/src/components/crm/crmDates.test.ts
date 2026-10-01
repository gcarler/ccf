import { describe, expect, it } from 'vitest';
import {
    formatCrmCalendarDate,
    formatCrmLeadCalendarDate,
    parseCrmDateKey,
    parseCrmLeadDateKey,
} from './crmDates';

describe('crmDates utility functions', () => {
    describe('parseCrmDateKey', () => {
        it('parses valid ISO string dates safely', () => {
            expect(parseCrmDateKey('2026-10-01T15:30:00.000Z')).toBe('2026-10-01');
            expect(parseCrmDateKey('2026-05-12T00:00:00Z')).toBe('2026-05-12');
        });

        it('parses YYYY-MM-DD date strings safely', () => {
            expect(parseCrmDateKey('2026-10-01')).toBe('2026-10-01');
            expect(parseCrmDateKey('2026-12-31')).toBe('2026-12-31');
        });

        it('parses Date instances safely', () => {
            const date = new Date(Date.UTC(2026, 9, 1));
            expect(parseCrmDateKey(date)).toBe('2026-10-01');
        });

        it('returns null and does not throw RangeError on invalid or nullish dates', () => {
            expect(() => parseCrmDateKey('not-a-real-date')).not.toThrow();
            expect(parseCrmDateKey('not-a-real-date')).toBeNull();
            expect(parseCrmDateKey('')).toBeNull();
            expect(parseCrmDateKey(null)).toBeNull();
            expect(parseCrmDateKey(undefined)).toBeNull();
            expect(parseCrmDateKey({})).toBeNull();
            expect(parseCrmDateKey('2026-99-99')).toBeNull();
        });
    });

    describe('formatCrmCalendarDate', () => {
        it('formats valid dateKey without timezone shift', () => {
            const formatted = formatCrmCalendarDate('2026-10-01');
            expect(formatted).toBeTruthy();
            expect(typeof formatted).toBe('string');
            // The formatted date should contain '1' or '01' and '2026' or month representation
            expect(formatted).toMatch(/1/);
            expect(formatted).toMatch(/2026/);
        });

        it('handles invalid dateKey gracefully without throwing', () => {
            expect(() => formatCrmCalendarDate('invalid-key')).not.toThrow();
            expect(formatCrmCalendarDate('invalid-key')).toBe('invalid-key');
        });
    });

    describe('parseCrmLeadDateKey & formatCrmLeadCalendarDate', () => {
        it('returns valid date key or "unknown" for leads', () => {
            expect(parseCrmLeadDateKey('2026-10-01T12:00:00Z')).toBe('2026-10-01');
            expect(parseCrmLeadDateKey(null)).toBe('unknown');
            expect(parseCrmLeadDateKey('invalid')).toBe('unknown');
            expect(parseCrmLeadDateKey('')).toBe('unknown');
        });

        it('formats "unknown" as "Sin fecha"', () => {
            expect(formatCrmLeadCalendarDate('unknown')).toBe('Sin fecha');
        });

        it('formats valid dateKey in es-CO format without timezone offset regression', () => {
            const formatted = formatCrmLeadCalendarDate('2026-10-01');
            expect(formatted).toBeTruthy();
            expect(formatted.toLowerCase()).toMatch(/octubre|10|01/);
        });
    });
});
