import { describe, expect, it } from 'vitest';
import {
    formatNotificationTime,
    inferNotificationKind,
    isRecentNotification,
    toUiNotification,
} from '../src/lib/notifications';

describe('notification helpers', () => {
    it('classifies backend notifications into usable UI kinds', () => {
        expect(inferNotificationKind('Tarea asignada')).toBe('task');
        expect(inferNotificationKind('Optimus detecto un insight')).toBe('ai');
        expect(inferNotificationKind('Te mencionaron', '@admin revisa esto')).toBe('mention');
    });

    it('normalizes backend notifications for the UI', () => {
        expect(toUiNotification({
            id: 7,
            persona_id: '00000000-0000-0000-0000-000000000001',
            title: 'Nuevo comentario',
            content: 'Hay una respuesta nueva',
            is_read: false,
            created_at: '2026-05-17T10:00:00Z',
        })).toMatchObject({
            id: 7,
            kind: 'comment',
            module: 'Comentarios',
            read: false,
        });
    });

    it('formats recency labels consistently', () => {
        const now = new Date('2026-05-17T12:00:00Z').getTime();
        expect(formatNotificationTime('2026-05-17T11:45:00Z', now)).toBe('Hace 15 min');
        expect(isRecentNotification('2026-05-17T11:45:00Z', now)).toBe(true);
        expect(isRecentNotification('2026-05-15T11:45:00Z', now)).toBe(false);
    });
});
