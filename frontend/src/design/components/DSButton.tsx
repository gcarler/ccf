"use client";

import React from 'react';
import clsx from 'clsx';

type Variant = 'primary' | 'secondary' | 'ghost';

interface DSButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: Variant;
    loading?: boolean;
}

const variantClasses: Record<Variant, string> = {
    primary: 'bg-[hsl(var(--primary))] text-white shadow-sm hover:opacity-90',
    secondary: 'bg-white/10 text-white border border-white/20 hover:bg-white/15 shadow-sm',
    ghost: 'bg-transparent text-white border border-white/30 hover:bg-white/10',
};

export const DSButton = React.forwardRef<HTMLButtonElement, DSButtonProps>(
    ({ variant = 'primary', loading, type = 'button', className, children, ...props }, ref) => {
        return (
            <button
                ref={ref}
                type={type}
                className={clsx(
                    'px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide transition-all active:scale-95 disabled:opacity-50 rounded-md',
                    variantClasses[variant],
                    className
                )}
                disabled={loading || props.disabled}
                {...props}
            >
                {loading ? 'Cargando...' : children}
            </button>
        );
    }
);
DSButton.displayName = 'DSButton';
