"use client";

import React from 'react';
import clsx from 'clsx';
import { colors, radii, shadows } from '../tokens';

type Variant = 'primary' | 'secondary' | 'ghost';

interface DSButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: Variant;
    loading?: boolean;
}

const variantClasses: Record<Variant, string> = {
    primary: 'text-white shadow-sm hover:opacity-90',
    secondary: 'text-white border border-white/20 hover:bg-white/15',
    ghost: 'text-white border border-white/30 hover:bg-white/10',
};

const variantStyles: Record<Variant, React.CSSProperties> = {
    primary: { backgroundColor: colors.primary[600], boxShadow: shadows.card },
    secondary: { backgroundColor: 'rgba(255,255,255,0.08)', boxShadow: shadows.card },
    ghost: { backgroundColor: 'transparent' },
};

export function DSButton({ variant = 'primary', loading, className, children, ...props }: DSButtonProps) {
    return (
        <button
            className={clsx(
                'px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide transition-all active:scale-95 disabled:opacity-50 rounded-md',
                variantClasses[variant],
                className
            )}
            style={{ borderRadius: radii.md, ...variantStyles[variant] }}
            disabled={loading || props.disabled}
            {...props}
        >
            {loading ? 'Cargando...' : children}
        </button>
    );
}
