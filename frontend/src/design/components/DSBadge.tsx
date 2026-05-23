"use client";

import React from 'react';
import clsx from 'clsx';
import { radii, typography } from '../tokens';

type Tone = 'slate' | 'blue' | 'emerald' | 'amber' | 'violet';

const toneStyles: Record<Tone, string> = {
    slate: 'bg-slate-900/70 text-slate-100',
    blue: 'bg-blue-500/15 text-blue-400',
    emerald: 'bg-emerald-500/15 text-emerald-400',
    amber: 'bg-amber-500/15 text-amber-400',
    violet: 'bg-blue-500/15 text-blue-300',
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
