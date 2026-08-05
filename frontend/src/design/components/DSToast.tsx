"use client";

import React, { useEffect, useState } from 'react';
import clsx from 'clsx';
import type { AppIcon } from '@/types/icons';
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from 'lucide-react';

type ToastType = 'success' | 'error' | 'warning' | 'info';

interface DSToastProps {
    type: ToastType;
    message: string;
    onClose?: () => void;
    action?: {
        label: string;
        onClick: () => void;
    };
}

const typeConfig: Record<ToastType, {
    icon: AppIcon;
    bgColor: string;
    borderColor: string;
    iconColor: string;
    role: 'alert' | 'status';
}> = {
    success: {
        icon: CheckCircle,
        bgColor: 'bg-[hsl(var(--success-muted))]',
        borderColor: 'border-[hsl(var(--success))]/30',
        iconColor: 'text-[hsl(var(--success))]',
        role: 'status',
    },
    error: {
        icon: AlertCircle,
        bgColor: 'bg-[hsl(var(--danger-muted))]',
        borderColor: 'border-[hsl(var(--danger))]/30',
        iconColor: 'text-[hsl(var(--danger))]',
        role: 'alert',
    },
    warning: {
        icon: AlertTriangle,
        bgColor: 'bg-[hsl(var(--warning-muted))]',
        borderColor: 'border-[hsl(var(--warning))]/30',
        iconColor: 'text-[hsl(var(--warning))]',
        role: 'status',
    },
    info: {
        icon: Info,
        bgColor: 'bg-[hsl(var(--info-muted))]',
        borderColor: 'border-[hsl(var(--info))]/30',
        iconColor: 'text-[hsl(var(--info))]',
        role: 'status',
    },
};

export function DSToast({
    type,
    message,
    onClose,
    action,
}: DSToastProps) {
    const config = typeConfig[type];
    const Icon = config.icon;

    return (
        <div
            className={clsx(
                'flex items-start gap-3 p-3 min-w-[280px] max-w-[400px] w-[calc(100vw-2rem)]',
                'rounded-md font-sans',
                'border',
                config.bgColor,
                config.borderColor,
                'shadow-lg'
            )}
            role={config.role}
            aria-live={config.role === 'alert' ? 'assertive' : 'polite'}
        >
            <Icon className={clsx('size-4 mt-0.5 shrink-0', config.iconColor)} />

            <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-primary))]">
                    {message}
                </p>
                {action && (
                    <button
                        onClick={action.onClick}
                        className="mt-1 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--primary))] hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--primary))]"
                    >
                        {action.label}
                    </button>
                )}
            </div>

            {onClose && (
                <button
                    onClick={onClose}
                    className="p-0.5 rounded text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--primary))]"
                    aria-label="Cerrar"
                >
                    <X size={12} />
                </button>
            )}
        </div>
    );
}

// ── Programmatic toast API ─────────────────────────────────────────────────────

interface ToastItem {
    id: number;
    type: ToastType;
    message: string;
    onClose?: () => void;
}

let toastId = 0;

let toasts: ToastItem[] = [];
let listeners: Array<(toasts: ToastItem[]) => void> = [];

function emit() {
    const snapshot = [...toasts];
    listeners.forEach((l) => l(snapshot));
}

const notify = (type: ToastType, message: string, duration = 5000) => {
    if (typeof window === 'undefined') return -1;
    const id = ++toastId;
    const remove = () => {
        toasts = toasts.filter((t) => t.id !== id);
        emit();
    };
    const toast: ToastItem = {
        id,
        type,
        message,
        onClose: remove,
    };

    toasts = [...toasts, toast];
    emit();

    if (duration > 0) {
        setTimeout(remove, duration);
    }

    return id;
};

export const toast = {
    success: (message: string, duration?: number) => notify('success', message, duration),
    error: (message: string, duration?: number) => notify('error', message, duration),
    warning: (message: string, duration?: number) => notify('warning', message, duration),
    info: (message: string, duration?: number) => notify('info', message, duration),
    dismiss: (id: number) => {
        if (typeof window === 'undefined') return;
        toasts = toasts.filter((t) => t.id !== id);
        emit();
    },
    subscribe: (listener: (toasts: ToastItem[]) => void) => {
        if (typeof window === 'undefined') return () => {};
        listeners.push(listener);
        return () => {
            listeners = listeners.filter((l) => l !== listener);
        };
    },
    getToasts: () => (typeof window === 'undefined' ? [] : [...toasts]),
};

export function useToasts(): ToastItem[] {
    const [items, setItems] = useState<ToastItem[]>(() => toast.getToasts());
    useEffect(() => {
        const unsubscribe = toast.subscribe(setItems);
        setItems(toast.getToasts());
        return unsubscribe;
    }, []);
    return items;
}
