"use client";

import React from 'react';
import clsx from 'clsx';

interface DSMetricProps {
    label: string;
    value: string;
    trend?: string;
    tone?: 'blue' | 'emerald' | 'amber' | 'violet';
}

export function DSMetric({ label, value, trend, tone = 'blue' }: DSMetricProps) {
    const tones: Record<typeof tone, { bg: string; text: string; iconBg: string }> = {
        blue: { bg: 'bg-blue-50 dark:bg-blue-900/20', text: 'text-blue-600 dark:text-blue-400', iconBg: 'bg-blue-100 dark:bg-blue-500/20' },
        emerald: { bg: 'bg-emerald-50 dark:bg-emerald-900/20', text: 'text-emerald-600 dark:text-emerald-400', iconBg: 'bg-emerald-100 dark:bg-emerald-500/20' },
        amber: { bg: 'bg-amber-50 dark:bg-amber-900/20', text: 'text-amber-600 dark:text-amber-400', iconBg: 'bg-amber-100 dark:bg-amber-500/20' },
        violet: { bg: 'bg-violet-50 dark:bg-violet-900/20', text: 'text-violet-600 dark:text-violet-400', iconBg: 'bg-violet-100 dark:bg-violet-500/20' },
    };

    return (
        <div className="bg-white dark:bg-[#1a1b1e] border border-slate-200 dark:border-white/5 rounded-[2rem] p-6 shadow-sm hover:shadow-lg transition-all flex flex-col justify-between">
            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 dark:text-slate-400">{label}</p>
            <p className="text-4xl font-black mt-3 text-slate-800 dark:text-white leading-none">{value}</p>
            {trend && (
                <div className="mt-4">
                    <span className={clsx("inline-flex items-center px-2.5 py-1 rounded-xl text-[10px] font-black uppercase tracking-widest", tones[tone].bg, tones[tone].text)}>
                        {trend}
                    </span>
                </div>
            )}
        </div>
    );
}
