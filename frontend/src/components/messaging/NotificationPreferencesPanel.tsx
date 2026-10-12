'use client';

/**
 * NotificationPreferencesPanel — Fase 1 (PLAN_NOTIFICACIONES_EMAIL_CCF.md).
 *
 * Panel de preferencias de notificación por canal (in_app / email) y tipo de
 * evento. Consume:
 *   GET  /messaging/notifications/preferences  → lista con defaults sembrados
 *   PATCH /messaging/notifications/preferences → toggle individual
 *
 * Reglas UI CCF: tokens semánticos exclusivamente, apiFetch, estados de
 * carga (Skeleton) y toasts (sonner vía ToastContext existente).
 */

import { useCallback, useEffect, useState } from 'react';
import { Bell, Mail, Monitor, Loader2 } from 'lucide-react';
import clsx from 'clsx';

import { apiFetch } from '@/lib/http';
import { useToast } from '@/context/ToastContext';

type NotificationChannel = 'in_app' | 'email';

interface NotificationPreference {
    id: string;
    persona_id?: string;
    channel: NotificationChannel;
    event_type: string;
    enabled: boolean;
    created_at: string;
    updated_at: string;
}

const EVENT_LABELS: Record<string, string> = {
    task_assigned: 'Tarea asignada',
    mention: 'Menciones (@tú)',
    event_reminder: 'Recordatorios de eventos',
    task_status_changed: 'Cambios de estado de tareas',
    comment_reply: 'Respuestas a comentarios',
    academy_course_update: 'Novedades de Academia',
    evangelism_followup: 'Seguimiento de evangelismo',
    survey_response: 'Respuestas de encuestas',
    crm_caso_update: 'Actualizaciones de casos CRM',
    broadcast: 'Anuncios generales',
};

export default function NotificationPreferencesPanel() {
    const { addToast } = useToast();
    const [preferences, setPreferences] = useState<NotificationPreference[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [togglingKey, setTogglingKey] = useState<string | null>(null);

    const loadPreferences = useCallback(async () => {
        setIsLoading(true);
        try {
            const data = await apiFetch<{ preferences: NotificationPreference[] }>(
                '/messaging/notifications/preferences',
                { cache: 'no-store' }
            );
            setPreferences(data?.preferences ?? []);
        } catch {
            addToast('Error al cargar preferencias de notificación', 'error');
        } finally {
            setIsLoading(false);
        }
    }, [addToast]);

    useEffect(() => {
        loadPreferences();
    }, [loadPreferences]);

    const handleToggle = async (pref: NotificationPreference) => {
        const key = `${pref.channel}:${pref.event_type}`;
        setTogglingKey(key);
        // Optimista: reflejar el cambio al instante.
        const previous = preferences;
        setPreferences(prefs =>
            prefs.map(p =>
                p.channel === pref.channel && p.event_type === pref.event_type
                    ? { ...p, enabled: !p.enabled }
                    : p
            )
        );
        try {
            const updated = await apiFetch<NotificationPreference>(
                '/messaging/notifications/preferences',
                {
                    method: 'PATCH',
                    body: {
                        channel: pref.channel,
                        event_type: pref.event_type,
                        enabled: !pref.enabled,
                    },
                }
            );
            setPreferences(prefs =>
                prefs.map(p =>
                    p.channel === updated.channel && p.event_type === updated.event_type
                        ? updated
                        : p
                )
            );
            addToast('Preferencia actualizada', 'success');
        } catch {
            // Rollback si la petición falla.
            setPreferences(previous);
            addToast('No se pudo actualizar la preferencia', 'error');
        } finally {
            setTogglingKey(null);
        }
    };

    if (isLoading) {
        return (
            <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 space-y-3" aria-busy="true">
                <div className="h-5 w-56 rounded bg-[hsl(var(--surface-3))] animate-pulse" />
                <div className="h-4 w-full rounded bg-[hsl(var(--surface-2))] animate-pulse" />
                <div className="h-4 w-3/4 rounded bg-[hsl(var(--surface-2))] animate-pulse" />
            </div>
        );
    }

    if (preferences.length === 0) {
        return (
            <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-6 text-center">
                <Bell size={24} className="mx-auto text-[hsl(var(--text-secondary))]" />
                <p className="mt-2 text-sm text-[hsl(var(--text-secondary))]">
                    No hay preferencias de notificación disponibles todavía.
                </p>
            </div>
        );
    }

    // Filas agrupadas por evento, con una columna por canal.
    const eventTypes = Array.from(new Set(preferences.map(p => p.event_type)));
    const prefMap = new Map(preferences.map(p => [`${p.channel}:${p.event_type}`, p]));

    return (
        <section className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4">
            <header className="flex items-center gap-2 mb-3">
                <Mail size={18} className="text-[hsl(var(--primary))]" />
                <h3 className="font-semibold text-[hsl(var(--text-primary))]">
                    Notificaciones por correo
                </h3>
                <p className="text-xs text-[hsl(var(--text-secondary))]">
                    Elige qué eventos también llegan a tu email.
                </p>
            </header>

            <div className="overflow-x-auto rounded-md border border-[hsl(var(--border))]">
                <table className="w-full min-w-[420px] text-left">
                    <thead className="bg-[hsl(var(--surface-2))] text-2xs font-medium uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                        <tr>
                            <th className="px-3 py-2">Evento</th>
                            <th className="px-3 py-2 text-center w-24">In-app</th>
                            <th className="px-3 py-2 text-center w-24">Email</th>
                        </tr>
                    </thead>
                    <tbody>
                        {eventTypes.map(eventType => {
                            const inApp = prefMap.get(`in_app:${eventType}`);
                            const email = prefMap.get(`email:${eventType}`);
                            return (
                                <tr key={eventType} className="border-t border-[hsl(var(--border))]">
                                    <td className="px-3 py-2 text-sm text-[hsl(var(--text-primary))]">
                                        {EVENT_LABELS[eventType] ?? eventType}
                                    </td>
                                    {([inApp, email] as const).map((pref, idx) => (
                                        <td key={idx} className="px-3 py-2 text-center">
                                            <ToggleSwitch
                                                checked={Boolean(pref?.enabled)}
                                                disabled={!pref || togglingKey === `${pref.channel}:${pref.event_type}`}
                                                onChange={() => pref && handleToggle(pref)}
                                                label={(idx === 0 ? 'In-app: ' : 'Email: ') + (EVENT_LABELS[eventType] ?? eventType)}
                                            />
                                        </td>
                                    ))}
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </section>
    );
}

function ToggleSwitch({
    checked,
    disabled,
    onChange,
    label,
}: {
    checked: boolean;
    disabled?: boolean;
    onChange: () => void;
    label: string;
}) {
    return (
        <button
            type="button"
            role="switch"
            aria-checked={checked}
            aria-label={label}
            disabled={disabled}
            onClick={onChange}
            className={clsx(
                'relative inline-flex h-5 w-9 items-center rounded-full transition-colors',
                'focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/40',
                checked
                    ? 'bg-[hsl(var(--primary))]'
                    : 'bg-[hsl(var(--surface-3))]',
                disabled && 'opacity-50 cursor-wait'
            )}
        >
            <span
                className={clsx(
                    'inline-block h-3.5 w-3.5 transform rounded-full bg-[hsl(var(--surface-1))] shadow transition-transform',
                    checked ? 'translate-x-[18px]' : 'translate-x-[3px]'
                )}
            />
            {disabled && (
                <Loader2 size={10} className="absolute right-1 animate-spin text-[hsl(var(--text-secondary))]" />
            )}
        </button>
    );
}
