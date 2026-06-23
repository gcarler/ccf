export type NotificationKind = 'mention' | 'comment' | 'task' | 'system' | 'ai' | 'reminder';

export interface BackendNotification {
    id: number;
    persona_id?: string;
    title: string;
    content?: string | null;
    is_read: boolean;
    created_at: string;
}

export interface UiNotification {
    id: number;
    title: string;
    body: string;
    read: boolean;
    createdAt: string;
    kind: NotificationKind;
    module: string;
}

const KIND_MODULE: Record<NotificationKind, string> = {
    mention: 'Colaboracion',
    comment: 'Comentarios',
    task: 'Tareas',
    system: 'Sistema',
    ai: 'MESH AI',
    reminder: 'Agenda',
};

export function inferNotificationKind(title: string, content = ''): NotificationKind {
    const haystack = `${title} ${content}`.toLowerCase();
    if (haystack.includes('optimus') || haystack.includes('mesh') || haystack.includes('insight')) return 'ai';
    if (haystack.includes('mencion') || haystack.includes('@')) return 'mention';
    if (haystack.includes('comentario')) return 'comment';
    if (haystack.includes('tarea') || haystack.includes('task') || haystack.includes('asignad')) return 'task';
    if (haystack.includes('recordatorio') || haystack.includes('reunion') || haystack.includes('evento')) return 'reminder';
    return 'system';
}

export function toUiNotification(notification: BackendNotification): UiNotification {
    const kind = inferNotificationKind(notification.title, notification.content || '');
    return {
        id: notification.id,
        title: notification.title,
        body: notification.content || '',
        read: notification.is_read,
        createdAt: notification.created_at,
        kind,
        module: KIND_MODULE[kind],
    };
}

export function isRecentNotification(createdAt: string, now = Date.now()) {
    const timestamp = new Date(createdAt).getTime();
    if (Number.isNaN(timestamp)) return false;
    return now - timestamp < 24 * 60 * 60 * 1000;
}

export function formatNotificationTime(createdAt: string, now = Date.now()) {
    const timestamp = new Date(createdAt).getTime();
    if (Number.isNaN(timestamp)) return 'Sin fecha';

    const diffMinutes = Math.max(0, Math.round((now - timestamp) / 60000));
    if (diffMinutes < 1) return 'Ahora';
    if (diffMinutes < 60) return `Hace ${diffMinutes} min`;

    const diffHours = Math.round(diffMinutes / 60);
    if (diffHours < 24) return `Hace ${diffHours} h`;
    if (diffHours < 48) return 'Ayer';

    return new Intl.DateTimeFormat('es-CO', {
        day: '2-digit',
        month: 'short',
    }).format(new Date(timestamp));
}
