"use client";

import React from 'react';
import clsx from 'clsx';
import { LucideIcon } from 'lucide-react';
import { colors, radii, motion } from '../tokens';

type Variant = 'solid' | 'soft' | 'outline';
type Tone = 'neutral' | 'dark';

interface DSToolbarChipProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    label: string;
    active?: boolean;
    variant?: Variant;
    size?: 'sm' | 'md';
    icon?: LucideIcon;
    tone?: Tone;
}

const baseStyle = 'inline-flex items-center justify-center font-semibold uppercase tracking-wide transition-all active:scale-95 whitespace-nowrap gap-1.5';

const variantClasses: Record<Variant, string> = {
    solid: 'text-white border border-transparent shadow-sm',
    soft: 'text-slate-600 border border-slate-200 bg-white/70 dark:bg-white/5 dark:text-white/70',
    outline: 'text-slate-500 border border-white/20 bg-transparent',
};

const sizeClasses = {
    sm: 'px-2 py-1 text-[9px] rounded-md',
    md: 'px-2.5 py-1 text-[9px] rounded-md',
};

export function DSToolbarChip({ label, active, variant = 'soft', size = 'md', icon: Icon, tone = 'neutral', className, ...props }: DSToolbarChipProps) {
    const styleVariant = active ? 'solid' : variant;
    return (
        <button
            className={clsx(baseStyle, variantClasses[styleVariant], sizeClasses[size], className)}
            style={{
                borderRadius: radii.md,
                backgroundColor: active ? colors.primary[600] : undefined,
                color: tone === 'dark' ? '#fff' : undefined,
                transitionDuration: motion.duration.base,
            }}
            {...props}
        >
            {Icon && <Icon size={size === 'sm' ? 11 : 12} className={clsx('transition-colors', active ? 'text-white' : 'text-slate-400')} />}
            <span>{label}</span>
        </button>
    );
}
