"use client";

import React from 'react';
import clsx from 'clsx';
import { LucideIcon } from 'lucide-react';

type Tone = 'primary' | 'neutral' | 'dark';
type Variant = 'outline' | 'solid' | 'dashed';
type Size = 'sm' | 'md';

interface CommunityToolbarChipProps {
    label: string;
    icon?: LucideIcon;
    active?: boolean;
    variant?: Variant;
    tone?: Tone;
    size?: Size;
    className?: string;
    onClick?: () => void;
    title?: string;
}

const toneClasses: Record<Tone, string> = {
    primary: 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] border-[hsl(var(--border))]',
    neutral: 'text-[hsl(var(--text-secondary))] border-[hsl(var(--border))] hover:text-[hsl(var(--text-primary))]',
    dark: 'text-white border-slate-900 bg-slate-900'
};

export default function CommunityToolbarChip({
    label,
    icon: Icon,
    active = false,
    variant = 'outline',
    tone = 'primary',
    size = 'md',
    className,
    onClick,
    title
}: CommunityToolbarChipProps) {
    const sizeClasses = size === 'sm' ? 'h-8 px-3 text-[10px]' : 'h-9 px-4 text-[10px]';
    const baseClasses = 'rounded-full uppercase tracking-[0.25em] flex items-center gap-1.5 transition-colors';
    const variantClasses = {
        outline: `${toneClasses[tone]} bg-white`,
        dashed: `${toneClasses[tone]} bg-white border-dashed`,
        solid: tone === 'dark'
            ? 'bg-slate-900 text-white border-slate-900'
            : 'bg-[hsl(var(--text-primary))] text-[hsl(var(--surface-1))] border-[hsl(var(--text-primary))]'
    }[variant];

    const activeClasses = active && variant === 'outline'
        ? 'bg-[hsl(var(--text-primary))] text-[hsl(var(--surface-1))] border-[hsl(var(--text-primary))]'
        : '';

    return (
        <button
            type="button"
            onClick={onClick}
            title={title || label}
            className={clsx(sizeClasses, baseClasses, variantClasses, activeClasses, className)}
        >
            {Icon && <Icon size={12} />}
            <span>{label}</span>
        </button>
    );
}
