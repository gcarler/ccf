"use client";

import React from 'react';
import clsx from 'clsx';

interface DSMetricProps {
    label: string;
    value: string;
    trend?: string;
    tone?: 'blue' | 'emerald' | 'amber';
    icon?: React.ComponentType<{ className?: string }>;
}

export function DSMetric({ label, value, trend, tone = 'blue', icon: Icon }: DSMetricProps) {
    const tones: Record<typeof tone, { bg: string; text: string; iconBg: string }> = {
        blue: { bg: 'bg-blue-50 dark:bg-blue-900/20', text: 'text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]', iconBg: 'bg-blue-100 dark:bg-blue-500/20' },
        emerald: { bg: 'bg-emerald-50 dark:bg-emerald-900/20', text: 'text-emerald-600 dark:text-emerald-400', iconBg: 'bg-emerald-100 dark:bg-emerald-500/20' },
        amber: { bg: 'bg-amber-50 dark:bg-amber-900/20', text: 'text-amber-600 dark:text-amber-400', iconBg: 'bg-amber-100 dark:bg-amber-500/20' },
    };

    return (
        <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#1a1b1e] border border-slate-200 dark:border-white/5 rounded-lg p-3 shadow-sm hover:shadow-md transition-all flex flex-col justify-between">
            <div className="flex items-center justify-between gap-2">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</p>
                {Icon && <Icon className={clsx("size-4", tones[tone].text)} />}
            </div>
            <p className="text-xl font-bold mt-1.5 text-slate-800 dark:text-white leading-tight">{value}</p>
            {trend && (
                <div className="mt-2">
                    <span className={clsx("inline-flex items-center px-1.5 py-0.5 rounded-md text-[9px] font-semibold uppercase tracking-wide", tones[tone].bg, tones[tone].text)}>
                        {trend}
                    </span>
                </div>
            )}
        </div>
    );
}
