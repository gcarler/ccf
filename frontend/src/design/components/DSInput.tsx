"use client";

import React from 'react';
import clsx from 'clsx';

interface DSInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
    label?: string;
    error?: string;
    helperText?: string;
    icon?: React.ComponentType<{ className?: string }>;
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
        const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

        return (
            <div className="flex flex-col gap-1.5">
                {label && (
                <label
                    htmlFor={inputId}
                    className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] font-sans"
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
                        'w-full px-2.5 py-1.5 text-xs bg-[hsl(var(--bg-primary))] dark:bg-[#1a1b1e]',
                        'border border-[hsl(var(--border))] dark:border-white/10',
                        'text-[hsl(var(--text-primary))] dark:text-white',
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
                        aria-describedby={error ? `${inputId}-error` : helperText ? `${inputId}-helper` : undefined}
                        {...props}
                    />
                    {loading && (
                        <div className="absolute right-2.5 top-1/2 -translate-y-1/2">
                            <div className="size-3 border-2 border-[hsl(var(--text-secondary))]/30 border-t-[hsl(var(--text-secondary))] rounded-full animate-spin" />
                        </div>
                    )}
                </div>
                {error && (
                    <p id={`${inputId}-error`} className="text-[9px] text-[hsl(var(--danger))]" role="alert">
                        {error}
                    </p>
                )}
                {!error && helperText && (
                    <p id={`${inputId}-helper`} className="text-[9px] text-[hsl(var(--text-secondary))]">
                        {helperText}
                    </p>
                )}
            </div>
        );
    }
);
DSInput.displayName = 'DSInput';
