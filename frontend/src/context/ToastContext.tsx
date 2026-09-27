"use client";

import React, { createContext, useContext } from 'react';
import { X, CheckCircle, AlertCircle, Bell } from 'lucide-react';
import { useToastStore, type ToastInput } from '@/stores/toastStore';

type ToastType = 'success' | 'error' | 'info' | 'warning';

interface ToastContextType {
    addToast: (input: ToastInput, type?: ToastType) => void;
    removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
    const toasts = useToastStore((s) => s.toasts);
    const addToast = useToastStore((s) => s.addToast);
    const removeToast = useToastStore((s) => s.removeToast);

    return (
        <ToastContext.Provider value={{ addToast, removeToast }}>
            {children}
            <div className="fixed bottom-6 right-6 z-[9999] flex flex-col gap-3 pointer-events-none">
                {toasts.map((toast) => (
                    <div
                        key={toast.id}
                        role="status"
                        aria-live="polite"
                        className={`pointer-events-auto flex items-start gap-3 p-4 rounded-lg border shadow-2xl glass-card animate-in slide-in-from-right-10 fade-in duration-300 min-w-[300px] max-w-md ${toast.type === 'success' ? 'bg-success-soft/90 border-[hsl(var(--success)/20%)] text-success-text' :
                                toast.type === 'error' ? 'bg-danger-soft/90 border-[hsl(var(--danger)/20%)] text-danger-text' :
                                    toast.type === 'warning' ? 'bg-warning-soft/90 border-[hsl(var(--warning)/20%)] text-warning-text' :
                                        'bg-info-soft/90 border-[hsl(var(--info)/20%)] text-info-text'
                            }`}
                    >
                        <div className={`p-2 rounded-md ${toast.type === 'success' ? 'bg-[hsl(var(--success))] text-[hsl(var(--success-foreground))]' :
                                toast.type === 'error' ? 'bg-[hsl(var(--danger))] text-[hsl(var(--danger-foreground))]' :
                                    toast.type === 'warning' ? 'bg-[hsl(var(--warning))] text-[hsl(var(--warning-foreground))]' :
                                        'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]'
                            }`} aria-hidden="true">
                            {toast.type === 'success' && <CheckCircle size={18} />}
                            {toast.type === 'error' && <AlertCircle size={18} />}
                            {toast.type === 'warning' && <AlertCircle size={18} />}
                            {toast.type === 'info' && <Bell size={18} />}
                        </div>
                        <div className="flex-1">
                            <p className="text-sm font-bold leading-tight">{toast.message}</p>
                            {toast.description && (
                                <p className="text-xs text-[hsl(var(--text-secondary))] mt-0.5 leading-snug">
                                    {toast.description}
                                </p>
                            )}
                        </div>
                        <button
                            onClick={() => removeToast(toast.id)}
                            aria-label="Cerrar notificación"
                            className="p-1 hover:bg-black/5 rounded-lg transition-colors"
                        >
                            <X size={16} />
                        </button>
                    </div>
                ))}
            </div>
        </ToastContext.Provider>
    );
}

export function useToast() {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error('useToast must be used within a ToastProvider');
    }
    return context;
}
