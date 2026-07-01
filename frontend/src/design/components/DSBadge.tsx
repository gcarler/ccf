"use client";

import React from 'react';
import clsx from 'clsx';
import { radii, typography } from '../tokens';

type Tone = 'slate' | 'blue' | 'emerald' | 'amber';

const toneStyles: Record<Tone, string> = {
    slate: 'bg-[hsl(var(--bg-muted))]/70 text-[hsl(var(--text-secondary))]',
    blue: 'bg-blue-500/15 text-[hsl(var(--primary))]',
    emerald: 'bg-emerald-500/15 text-emerald-400',
    amber: 'bg-amber-500/15 text-amber-400',
};

interface DSBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
    tone?: Tone;
    label: string;
}

export function DSBadge({ tone = 'slate', label, className, ...props }: DSBadgeProps) {
    return (
        <span
            className={clsx(
                'px-1.5 py-0.5 inline-flex items-center justify-center text-[9px] font-semibold uppercase tracking-wide',
                'border border-white/10 shadow-sm backdrop-blur',
                toneStyles[tone],
                className
            )}
            style={{ borderRadius: radii.sm, fontFamily: typography.family }}
            {...props}
        >
            {label}
        </span>
    );
}
