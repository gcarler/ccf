/**
 * Utilidades de parseo y formateo seguro de fechas para el módulo CRM.
 * Evita RangeError ante entradas inválidas y previene desfases de día
 * causados por interpretaciones de zona horaria con 'T00:00:00'.
 */

export function parseCrmDateKey(value: unknown): string | null {
    if (!value || (typeof value !== 'string' && typeof value !== 'number' && !(value instanceof Date))) {
        return null;
    }

    if (typeof value === 'string') {
        const trimmed = value.trim();
        const ymdMatch = trimmed.match(/^(\d{4})-(\d{2})-(\d{2})/);
        if (ymdMatch) {
            const year = parseInt(ymdMatch[1], 10);
            const month = parseInt(ymdMatch[2], 10);
            const day = parseInt(ymdMatch[3], 10);
            if (year > 1000 && month >= 1 && month <= 12 && day >= 1 && day <= 31) {
                return `${ymdMatch[1]}-${ymdMatch[2]}-${ymdMatch[3]}`;
            }
        }
    }

    const d = new Date(value as string | number | Date);
    if (Number.isNaN(d.getTime())) return null;

    try {
        return d.toISOString().slice(0, 10);
    } catch {
        return null;
    }
}

export function formatCrmCalendarDate(dateKey: string, options?: Intl.DateTimeFormatOptions): string {
    const parts = dateKey.split('-').map(Number);
    if (parts.length === 3 && parts.every(n => !Number.isNaN(n))) {
        const [year, month, day] = parts;
        const d = new Date(year, month - 1, day);
        if (!Number.isNaN(d.getTime())) {
            return d.toLocaleDateString(undefined, options);
        }
    }
    const d = new Date(dateKey);
    if (!Number.isNaN(d.getTime())) {
        return d.toLocaleDateString(undefined, options);
    }
    return dateKey;
}

export function parseCrmLeadDateKey(value: unknown): string {
    return parseCrmDateKey(value) ?? 'unknown';
}

export function formatCrmLeadCalendarDate(dateKey: string, options?: Intl.DateTimeFormatOptions): string {
    if (dateKey === 'unknown') return 'Sin fecha';
    const opts = options ?? { day: '2-digit', month: 'long', year: 'numeric' };
    const parts = dateKey.split('-').map(Number);
    if (parts.length === 3 && parts.every(n => !Number.isNaN(n))) {
        const [year, month, day] = parts;
        const d = new Date(year, month - 1, day);
        if (!Number.isNaN(d.getTime())) {
            return d.toLocaleDateString('es-CO', opts);
        }
    }
    const d = new Date(dateKey);
    if (!Number.isNaN(d.getTime())) {
        return d.toLocaleDateString('es-CO', opts);
    }
    return dateKey;
}
