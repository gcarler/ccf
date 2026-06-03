"use client";

import React, { createContext, useContext } from 'react';
import { X, CheckCircle, AlertCircle, Bell } from 'lucide-react';
import { useToastStore } from '@/stores/toastStore';

type ToastType = 'success' | 'error' | 'info' | 'warning';

interface ToastContextType {
    addToast: (message: string, type?: ToastType) => void;
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
                        className={`pointer-events-auto flex items-center gap-3 p-4 rounded-lg border shadow-2xl glass-card animate-in slide-in-from-right-10 fade-in duration-300 min-w-[300px] max-w-md ${toast.type === 'success' ? 'bg-emerald-50/90 border-emerald-100 text-emerald-800' :
                                toast.type === 'error' ? 'bg-rose-50/90 border-rose-100 text-rose-800' :
                                    toast.type === 'warning' ? 'bg-amber-50/90 border-amber-100 text-amber-800' :
                                        'bg-blue-50/90 border-blue-100 text-blue-800'
                            }`}
                    >
                        <div className={`p-2 rounded-md ${toast.type === 'success' ? 'bg-emerald-500 text-white' :
                                toast.type === 'error' ? 'bg-rose-500 text-white' :
                                    toast.type === 'warning' ? 'bg-amber-500 text-white' :
                                        'bg-[hsl(var(--primary))] text-white'
                            }`}>
                            {toast.type === 'success' && <CheckCircle size={18} />}
                            {toast.type === 'error' && <AlertCircle size={18} />}
                            {toast.type === 'warning' && <AlertCircle size={18} />}
                            {toast.type === 'info' && <Bell size={18} />}
                        </div>
                        <div className="flex-1">
                            <p className="text-sm font-bold leading-tight">{toast.message}</p>
                        </div>
                        <button
                            onClick={() => removeToast(toast.id)}
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
