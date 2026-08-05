"use client";

import React from 'react';
import clsx from 'clsx';
import type { AppIcon } from '@/types/icons';

type Variant = 'solid' | 'soft' | 'outline';
type Tone = 'neutral' | 'dark';

interface DSToolbarChipProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    label: string;
    active?: boolean;
    variant?: Variant;
    size?: 'sm' | 'md';
    icon?: AppIcon;
    tone?: Tone;
}

const baseStyle = 'inline-flex items-center justify-center font-semibold uppercase tracking-wide transition-all duration-150 active:scale-95 whitespace-nowrap gap-1.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--primary))]';

const variantClasses: Record<Variant, string> = {
    solid: 'text-[hsl(var(--primary-foreground))] border-transparent shadow-sm',
    soft: 'text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-3))]',
    outline: 'text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))] bg-transparent hover:bg-[hsl(var(--surface-2))]',
};

const sizeClasses = {
    sm: 'px-2 py-1 text-2xs rounded-md',
    md: 'px-2.5 py-1 text-2xs rounded-md',
};

export function DSToolbarChip({ label, active, variant = 'soft', size = 'md', icon: Icon, tone = 'neutral', type = 'button', className, ...props }: DSToolbarChipProps) {
    const styleVariant = active ? 'solid' : variant;
    return (
        <button
            type={type}
            className={clsx(
                baseStyle,
                variantClasses[styleVariant],
                sizeClasses[size],
                active && 'bg-[hsl(var(--primary))]',
                tone === 'dark' && 'text-[hsl(var(--text-primary))]',
                className
            )}
            {...props}
        >
            {Icon && <Icon size={size === 'sm' ? 11 : 12} className={clsx('transition-colors', active ? 'text-[hsl(var(--primary-foreground))]' : 'text-[hsl(var(--text-secondary))]')} />}
            <span>{label}</span>
        </button>
    );
}