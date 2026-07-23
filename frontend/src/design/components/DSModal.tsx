"use client";

import React, { useEffect, useRef } from 'react';
import clsx from 'clsx';
import { X } from 'lucide-react';

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

const FOCUSABLE_SELECTORS = [
    'a[href]',
    'button:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
].join(', ');

function getFocusableElements(container: HTMLElement | null): HTMLElement[] {
    if (!container) return [];
    return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTORS));
}

export function DSModal({
    open,
    onClose,
    title,
    children,
    size = 'md',
    showClose = true,
}: DSModalProps) {
    const modalRef = useRef<HTMLDivElement>(null);
    const triggerRef = useRef<HTMLElement | null>(null);
    const hasOpenedRef = useRef(false);

    useEffect(() => {
        const handleEscape = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
        };

        const handleTab = (e: KeyboardEvent) => {
            if (e.key !== 'Tab') return;
            const modal = modalRef.current;
            if (!modal) return;

            const focusable = getFocusableElements(modal);
            if (focusable.length === 0) {
                e.preventDefault();
                return;
            }

            const first = focusable[0];
            const last = focusable[focusable.length - 1];
            const active = document.activeElement as HTMLElement | null;

            if (e.shiftKey) {
                if (active === first || !modal.contains(active)) {
                    e.preventDefault();
                    last.focus();
                }
            } else {
                if (active === last || !modal.contains(active)) {
                    e.preventDefault();
                    first.focus();
                }
            }
        };

        if (open) {
            triggerRef.current = document.activeElement as HTMLElement | null;
            document.addEventListener('keydown', handleEscape);
            document.addEventListener('keydown', handleTab);

            if (openModalsCount === 0) {
                document.body.style.overflow = 'hidden';
            }
            openModalsCount++;
            hasOpenedRef.current = true;

            // Move focus to the first focusable element (close button or content)
            const firstFocusable = getFocusableElements(modalRef.current)[0];
            firstFocusable?.focus();
        }

        return () => {
            document.removeEventListener('keydown', handleEscape);
            document.removeEventListener('keydown', handleTab);

            if (hasOpenedRef.current) {
                openModalsCount--;
                hasOpenedRef.current = false;

                if (openModalsCount === 0) {
                    document.body.style.overflow = '';
                }
            }
        };
    }, [open, onClose]);

    // Restore focus when the modal is fully closed
    const previousOpenRef = React.useRef(open);
    useEffect(() => {
        if (previousOpenRef.current && !open) {
            triggerRef.current?.focus();
        }
        previousOpenRef.current = open;
    }, [open]);

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
