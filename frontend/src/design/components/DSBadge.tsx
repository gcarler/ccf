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
    violet: 'bg-violet-500/15 text-violet-300',
};

interface DSBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
    tone?: Tone;
    label: string;
}

export function DSBadge({ tone = 'slate', label, className, ...props }: DSBadgeProps) {
    return (
        <span
            className={clsx(
                'px-3 py-1 inline-flex items-center justify-center text-[10px] font-black uppercase tracking-[0.25em]',
                'border border-white/10 shadow-sm backdrop-blur',
                toneStyles[tone],
                className
            )}
            style={{ borderRadius: radii.pill, fontFamily: typography.family }}
            {...props}
        >
            {label}
        </span>
    );
}
