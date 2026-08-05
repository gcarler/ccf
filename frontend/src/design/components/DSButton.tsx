"use client";

import React from 'react';
import clsx from 'clsx';

type Variant = 'primary' | 'secondary' | 'ghost';

interface DSButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: Variant;
    loading?: boolean;
}

const variantClasses: Record<Variant, string> = {
    primary: 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-sm hover:brightness-95 dark:hover:brightness-110',
    secondary: 'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-primary))] border border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-3))] shadow-sm',
    ghost: 'bg-transparent text-[hsl(var(--text-primary))] border border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-2))]',
};

export const DSButton = React.forwardRef<HTMLButtonElement, DSButtonProps>(
    ({ variant = 'primary', loading, type = 'button', className, children, ...props }, ref) => {
        return (
            <button
                ref={ref}
                type={type}
                className={clsx(
                    'px-3 py-1.5 text-2xs font-semibold uppercase tracking-wide transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed rounded-md',
                    'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--primary))]',
                    variantClasses[variant],
                    className
                )}
                disabled={loading || props.disabled}
                aria-busy={loading || undefined}
                {...props}
            >
                {loading ? (
                    <span className="inline-flex items-center gap-1.5">
                        <span
                            className="size-3 border-2 border-current/30 border-t-current rounded-full animate-spin motion-reduce:animate-none"
                            aria-hidden="true"
                        />
                        <span>Cargando…</span>
                    </span>
                ) : children}
            </button>
        );
    }
);
DSButton.displayName = 'DSButton';
