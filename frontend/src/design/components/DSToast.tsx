"use client";

import React from 'react';
import clsx from 'clsx';
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from 'lucide-react';
import { radii, typography } from '../tokens';

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
    icon: React.ComponentType<{ className?: string }>;
    bgColor: string;
    borderColor: string;
    iconColor: string;
}> = {
    success: {
        icon: CheckCircle,
        bgColor: 'bg-[hsl(var(--success-muted))]',
        borderColor: 'border-[hsl(var(--success))]/30',
        iconColor: 'text-[hsl(var(--success))]',
    },
    error: {
        icon: AlertCircle,
        bgColor: 'bg-[hsl(var(--danger-muted))]',
        borderColor: 'border-[hsl(var(--danger))]/30',
        iconColor: 'text-[hsl(var(--danger))]',
    },
    warning: {
        icon: AlertTriangle,
        bgColor: 'bg-[hsl(var(--warning-muted))]',
        borderColor: 'border-[hsl(var(--warning))]/30',
        iconColor: 'text-[hsl(var(--warning))]',
    },
    info: {
        icon: Info,
        bgColor: 'bg-[hsl(var(--info-muted))]',
        borderColor: 'border-[hsl(var(--info))]/30',
        iconColor: 'text-[hsl(var(--info))]',
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
                'flex items-start gap-3 p-3 min-w-[280px] max-w-[400px]',
                'border',
                config.bgColor,
                config.borderColor,
                'shadow-lg'
            )}
            style={{ borderRadius: radii.md, fontFamily: typography.family }}
            role="alert"
            aria-live="polite"
        >
            <Icon className={clsx('size-4 mt-0.5 shrink-0', config.iconColor)} />

            <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-[hsl(var(--text-primary))] dark:text-white">
                    {message}
                </p>
                {action && (
                    <button
                        onClick={action.onClick}
                        className="mt-1 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))] hover:underline"
                    >
                        {action.label}
                    </button>
                )}
            </div>

            {onClose && (
                <button
                    onClick={onClose}
                    className="p-0.5 rounded text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors"
                    aria-label="Cerrar"
                >
                    <X size={12} />
                </button>
            )}
        </div>
    );
}

// Toast container and functions for programmatic usage
let toastId = 0;

interface ToastItem {
    id: number;
    type: ToastType;
    message: string;
    onClose?: () => void;
}

let toasts: ToastItem[] = [];
let listeners: Array<(toasts: ToastItem[]) => void> = [];

const notify = (type: ToastType, message: string, duration = 5000) => {
    const id = ++toastId;
    const toast: ToastItem = {
        id,
        type,
        message,
        onClose: () => {
            toasts = toasts.filter((t) => t.id !== id);
            listeners.forEach((l) => l(toasts));
        },
    };

    toasts = [...toasts, toast];
    listeners.forEach((l) => l(toasts));

    if (duration > 0) {
        setTimeout(() => {
            toasts = toasts.filter((t) => t.id !== id);
            listeners.forEach((l) => l(toasts));
        }, duration);
    }

    return id;
};

export const toast = {
    success: (message: string, duration?: number) => notify('success', message, duration),
    error: (message: string, duration?: number) => notify('error', message, duration),
    warning: (message: string, duration?: number) => notify('warning', message, duration),
    info: (message: string, duration?: number) => notify('info', message, duration),
    dismiss: (id: number) => {
        toasts = toasts.filter((t) => t.id !== id);
        listeners.forEach((l) => l(toasts));
    },
    subscribe: (listener: (toasts: ToastItem[]) => void) => {
        listeners.push(listener);
        return () => {
            listeners = listeners.filter((l) => l !== listener);
        };
    },
    getToasts: () => toasts,
};
