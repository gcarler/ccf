"use client";

import React from 'react';
import clsx from 'clsx';

interface DSMetricProps {
    label: string;
    value: string;
    trend?: string;
    tone?: 'blue' | 'emerald' | 'amber';
    icon?: React.ComponentType<{ className?: string }>;
    onClick?: () => void;
    href?: string;
}

export function DSMetric({ label, value, trend, tone = 'blue', icon: Icon, onClick, href }: DSMetricProps) {
    const tones: Record<typeof tone, { bg: string; text: string; iconBg: string }> = {
        blue: { bg: 'bg-[hsl(var(--info-muted))]', text: 'text-[hsl(var(--info))]', iconBg: 'bg-[hsl(var(--info-muted))]' },
        emerald: { bg: 'bg-[hsl(var(--success-muted))]', text: 'text-[hsl(var(--success-text))]', iconBg: 'bg-[hsl(var(--success-muted))]' },
        amber: { bg: 'bg-[hsl(var(--warning-muted))]', text: 'text-[hsl(var(--warning-text))]', iconBg: 'bg-[hsl(var(--warning-muted))]' },
    };

    const Tag = href ? 'a' : 'div';
    const extraProps = href ? { href } : onClick ? { onClick, role: 'button' as const } : {};

    return (
        <Tag className={clsx("bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border))] dark:border-white/5 rounded-lg p-3 shadow-sm hover:shadow-md transition-all flex flex-col justify-between", onClick && "cursor-pointer hover:border-[hsl(var(--primary))]/30")} {...extraProps}>
            <div className="flex items-center justify-between gap-2">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">{label}</p>
                {Icon && <Icon className={clsx("size-4", tones[tone].text)} />}
            </div>
            <p className="text-xl font-bold mt-1.5 text-[hsl(var(--text-primary))] dark:text-white leading-tight">{value}</p>
            {trend && (
                <div className="mt-2">
                    <span className={clsx("inline-flex items-center px-1.5 py-0.5 rounded-md text-[9px] font-semibold uppercase tracking-wide", tones[tone].bg, tones[tone].text)}>
                        {trend}
                    </span>
                </div>
            )}
        </Tag>
    );
}
