"use client";

import React, { useEffect, useRef } from 'react';
import clsx from 'clsx';
import { X } from 'lucide-react';
import { radii, shadows } from '../tokens';

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

let openModalsCount = 0;

export function DSModal({
    open,
    onClose,
    title,
    children,
    size = 'md',
    showClose = true,
}: DSModalProps) {
    const modalRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handleEscape = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
        };

        if (open) {
            document.addEventListener('keydown', handleEscape);

            if (openModalsCount === 0) {
                document.body.style.overflow = 'hidden';
            }
            openModalsCount++;
        }

        return () => {
            document.removeEventListener('keydown', handleEscape);
            openModalsCount--;

            if (openModalsCount === 0) {
                document.body.style.overflow = '';
            }
        };
    }, [open, onClose]);

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
                className={clsx(
                    'relative w-full mx-4 bg-[hsl(var(--bg-primary))] dark:bg-[#1a1b1e]',
                    'border border-[hsl(var(--border))] dark:border-white/10',
                    'shadow-2xl',
                    sizeClasses[size]
                )}
                style={{ borderRadius: radii.lg, boxShadow: shadows.dropdown }}
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
                                className="p-1 rounded-md text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] hover:text-[hsl(var(--text-primary))] transition-colors"
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
