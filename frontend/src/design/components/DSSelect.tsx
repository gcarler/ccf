"use client";

import React from 'react';
import clsx from 'clsx';

interface SelectOption {
    value: string;
    label: string;
    disabled?: boolean;
}

interface DSSelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
    label?: string;
    options: SelectOption[];
    placeholder?: string;
    error?: string;
    helperText?: string;
    loading?: boolean;
}

export const DSSelect = React.forwardRef<HTMLSelectElement, DSSelectProps>(
    ({
        label,
        options,
        placeholder,
        error,
        helperText,
        loading,
        className,
        id,
        ...props
    }, ref) => {
        const autoId = React.useId();
        const selectId = id || (label ? `${autoId}-${label.toLowerCase().replace(/\s+/g, '-')}` : autoId);
        const errorId = `${selectId}-error`;
        const helperId = `${selectId}-helper`;
        const describedBy = error ? errorId : helperText ? helperId : undefined;

        return (
            <div className="flex flex-col gap-1.5">
                {label && (
                <label
                    htmlFor={selectId}
                    className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] font-sans"
                >
                        {label}
                    </label>
                )}
                <div className="relative">
                    <select
                        ref={ref}
                        id={selectId}
                    className={clsx(
                        'w-full px-2.5 py-1.5 text-xs appearance-none',
                        'bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))]',
                        'border border-[hsl(var(--border))] dark:border-[hsl(var(--border))]',
                        'text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-primary))]',
                        'focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))] focus:border-[hsl(var(--primary))]',
                        'disabled:opacity-50 disabled:cursor-not-allowed',
                        'transition-colors',
                        'rounded-md font-sans',
                        error && 'border-[hsl(var(--danger))] focus:ring-[hsl(var(--danger))]',
                        className
                    )}
                        disabled={loading || props.disabled}
                        aria-invalid={error ? 'true' : undefined}
                        aria-describedby={describedBy}
                        {...props}
                    >
                        {placeholder && (
                            <option value="" disabled>
                                {placeholder}
                            </option>
                        )}
                        {options.map((option) => (
                            <option key={option.value} value={option.value} disabled={option.disabled}>
                                {option.label}
                            </option>
                        ))}
                    </select>
                    <div className="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none text-[hsl(var(--text-secondary))]">
                        <svg className="size-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                    </div>
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
DSSelect.displayName = 'DSSelect';
