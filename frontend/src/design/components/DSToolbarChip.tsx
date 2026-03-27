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

const baseStyle = 'inline-flex items-center justify-center font-black uppercase tracking-[0.28em] transition-all active:scale-95 whitespace-nowrap gap-2';

const variantClasses: Record<Variant, string> = {
    solid: 'text-white border border-transparent shadow-[0_10px_25px_rgba(79,70,229,0.3)]',
    soft: 'text-slate-600 border border-slate-200 bg-white/70 dark:bg-white/5 dark:text-white/70',
    outline: 'text-slate-500 border border-white/20 bg-transparent',
};

const sizeClasses = {
    sm: 'px-4 py-1.5 text-[9px]',
    md: 'px-5 py-2 text-[10px]',
};

export function DSToolbarChip({ label, active, variant = 'soft', size = 'md', icon: Icon, tone = 'neutral', className, ...props }: DSToolbarChipProps) {
    const styleVariant = active ? 'solid' : variant;
    return (
        <button
            className={clsx(baseStyle, variantClasses[styleVariant], sizeClasses[size], className)}
            style={{
                borderRadius: radii.pill,
                backgroundColor: active ? colors.primary[600] : undefined,
                color: tone === 'dark' ? '#fff' : undefined,
                transitionDuration: motion.duration.base,
            }}
            {...props}
        >
            {Icon && <Icon size={size === 'sm' ? 12 : 14} className={clsx('transition-colors', active ? 'text-white' : 'text-slate-400')} />}
            <span>{label}</span>
        </button>
    );
}
