"use client";

import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { BackendNotification, UiNotification, toUiNotification } from '@/lib/notifications';

export function useNotifications(limit = 50) {
    const { token, isAuthenticated } = useAuth();
    const [notifications, setNotifications] = useState<UiNotification[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const refresh = useCallback(async () => {
        if (!token) {
            setNotifications([]);
            setLoading(false);
            return;
        }

        setLoading(true);
        setError(null);
        try {
            const data = await apiFetch<BackendNotification[]>('/messaging/notifications', {
                token,
                cache: 'no-store',
                query: { limit },
            });
            setNotifications(Array.isArray(data) ? data.map(toUiNotification) : []);
        } catch (err) {
            console.error(err);
            setNotifications([]);
            setError('No se pudieron cargar las notificaciones.');
        } finally {
            setLoading(false);
        }
    }, [limit, token]);

    useEffect(() => {
        if (!isAuthenticated) {
            setLoading(false);
            return;
        }
        void refresh();
    }, [isAuthenticated, refresh]);

    const markRead = useCallback(async (id: number) => {
        if (!token) return;
        const current = notifications.find((item) => item.id === id);
        if (!current || current.read) return;

        setNotifications((items) => items.map((item) => item.id === id ? { ...item, read: true } : item));
        try {
            await apiFetch(`/messaging/notifications/${id}`, {
                method: 'PATCH',
                token,
            });
        } catch (err) {
            console.error(err);
            setNotifications((items) => items.map((item) => item.id === id ? { ...item, read: false } : item));
            setError('No se pudo marcar la notificacion como leida.');
        }
    }, [notifications, token]);

    const markAllRead = useCallback(async () => {
        if (!token) return;
        const previous = notifications;
        setNotifications((items) => items.map((item) => ({ ...item, read: true })));
        try {
            await apiFetch('/messaging/notifications/mark-all-read', {
                method: 'POST',
                token,
            });
        } catch (err) {
            console.error(err);
            setNotifications(previous);
            setError('No se pudieron marcar todas las notificaciones.');
        }
    }, [notifications, token]);

    return {
        notifications,
        loading,
        error,
        refresh,
        markRead,
        markAllRead,
    };
}
