"use client";

import React, { useRef } from 'react';
import clsx from 'clsx';
import { X } from 'lucide-react';
import { useFocusTrap } from '@/hooks/useFocusTrap';

interface DSModalProps {
    open: boolean;
    onClose: () => void;
    title?: string;
    children: React.ReactNode;
    size?: 'sm' | 'md' | 'lg';
    showClose?: boolean;
}

const sizeClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
};

export function DSModal({
    open,
    onClose,
    title,
    children,
    size = 'md',
    showClose = true,
}: DSModalProps) {
    const modalRef = useRef<HTMLDivElement>(null);

    useFocusTrap(modalRef, {
        active: open,
        onEscape: onClose,
        lockBodyScroll: true,
    });

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/50 backdrop-blur-sm"
                onClick={onClose}
                aria-hidden="true"
            />

            {/* Modal */}
            <div
                ref={modalRef}
                tabIndex={-1}
                className={clsx(
                    'relative w-full mx-4 bg-[hsl(var(--bg-primary))] rounded-lg',
                    'border border-[hsl(var(--border))] dark:border-white/10',
                    'shadow-2xl',
                    sizeClasses[size]
                )}
                role="dialog"
                aria-modal="true"
                aria-labelledby={title ? 'modal-title' : undefined}
            >
                {/* Header */}
                {(title || showClose) && (
                    <div className="flex items-center justify-between px-4 py-3 border-b border-[hsl(var(--border))] dark:border-white/5">
                        {title && (
                            <h2
                                id="modal-title"
                                className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white"
                            >
                                {title}
                            </h2>
                        )}
                        {showClose && (
                            <button
                                onClick={onClose}
                                className="p-1 rounded-md text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] hover:text-[hsl(var(--text-primary))] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--primary))]"
                                aria-label="Cerrar"
                            >
                                <X size={14} />
                            </button>
                        )}
                    </div>
                )}

                {/* Content */}
                <div className="px-4 py-3">
                    {children}
                </div>
            </div>
        </div>
    );
}
