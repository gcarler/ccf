"use client";

import React from 'react';
import clsx from 'clsx';
import { DSBadge } from './DSBadge';

interface DSMetricProps {
    label: string;
    value: string;
    trend?: string;
    tone?: 'blue' | 'emerald' | 'amber' | 'violet';
}

export function DSMetric({ label, value, trend, tone = 'blue' }: DSMetricProps) {
    const gradients: Record<typeof tone, string> = {
        blue: 'from-blue-500/80 to-indigo-600/80',
        emerald: 'from-emerald-500/80 to-teal-500/80',
        amber: 'from-amber-500/80 to-orange-500/80',
        violet: 'from-violet-500/80 to-purple-600/80',
    } as const;

    return (
        <div className={clsx('rounded-[2rem] p-4 text-white shadow-xl border border-white/10 bg-gradient-to-br', gradients[tone])}>
            <p className="text-[10px] font-black uppercase tracking-[0.35em] opacity-90">{label}</p>
            <p className="text-3xl font-black mt-2 leading-tight">{value}</p>
            {trend && (
                <div className="mt-3">
                    <DSBadge tone="slate" label={trend} />
                </div>
            )}
        </div>
    );
}
