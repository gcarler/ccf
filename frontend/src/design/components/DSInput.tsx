"use client";

import React from 'react';
import clsx from 'clsx';
import type { AppIcon } from '@/types/icons';

interface DSInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
    label?: string;
    error?: string;
    helperText?: string;
    icon?: AppIcon;
    loading?: boolean;
}

export const DSInput = React.forwardRef<HTMLInputElement, DSInputProps>(
    ({
        label,
        error,
        helperText,
        icon: Icon,
        loading,
        className,
        id,
        ...props
    }, ref) => {
        const autoId = React.useId();
        const inputId = id || (label ? `${autoId}-${label.toLowerCase().replace(/\s+/g, '-')}` : autoId);
        const errorId = `${inputId}-error`;
        const helperId = `${inputId}-helper`;
        const describedBy = error ? errorId : helperText ? helperId : undefined;

        return (
            <div className="flex flex-col gap-1.5">
                {label && (
                <label
                    htmlFor={inputId}
                    className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] font-sans"
                >
                        {label}
                    </label>
                )}
                <div className="relative">
                    {Icon && (
                        <div className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]">
                            <Icon className="size-3.5" />
                        </div>
                    )}
                    <input
                        ref={ref}
                        id={inputId}
                    className={clsx(
                        'w-full px-2.5 py-1.5 text-xs bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))]',
                        'border border-[hsl(var(--border))] dark:border-[hsl(var(--border))]',
                        'text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-primary))]',
                        'placeholder:text-[hsl(var(--text-secondary))]/50',
                        'focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))] focus:border-[hsl(var(--primary))]',
                        'disabled:opacity-50 disabled:cursor-not-allowed',
                        'transition-colors',
                        'rounded-md font-sans',
                        Icon && 'pl-8',
                        error && 'border-[hsl(var(--danger))] focus:ring-[hsl(var(--danger))]',
                        className
                    )}
                        disabled={loading || props.disabled}
                        aria-invalid={error ? 'true' : undefined}
                        aria-describedby={describedBy}
                        {...props}
                    />
                    {loading && (
                        <div className="absolute right-2.5 top-1/2 -translate-y-1/2">
                            <div className="size-3 border-2 border-[hsl(var(--text-secondary))]/30 border-t-[hsl(var(--text-secondary))] rounded-full animate-spin" />
                        </div>
                    )}
                </div>
                {error && (
                    <p id={errorId} className="text-2xs text-[hsl(var(--danger))]" role="alert">
                        {error}
                    </p>
                )}
                {!error && helperText && (
                    <p id={helperId} className="text-2xs text-[hsl(var(--text-secondary))]">
                        {helperText}
                    </p>
                )}
            </div>
        );
    }
);
DSInput.displayName = 'DSInput';
