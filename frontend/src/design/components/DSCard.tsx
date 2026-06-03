"use client";

import React from 'react';
import clsx from 'clsx';
import { radii, shadows } from '../tokens';

interface DSCardProps extends React.HTMLAttributes<HTMLDivElement> {
    tone?: 'light' | 'dark' | 'glass';
    padding?: 'sm' | 'md';
}

export function DSCard({ tone = 'light', padding = 'md', className, children, ...props }: DSCardProps) {
    const toneClass =
        tone === 'dark'
            ? 'bg-[#0f1116] border border-white/5'
            : tone === 'light'
            ? 'bg-[hsl(var(--bg-primary))] border border-slate-100'
            : 'bg-white/10 backdrop-blur-xl border border-white/10';

    const paddingClass = padding === 'md' ? 'p-3' : 'p-2';

    return (
        <div
            className={clsx('rounded-lg shadow-sm', toneClass, paddingClass, className)}
            style={{ borderRadius: radii.lg, boxShadow: shadows.card }}
            {...props}
        >
            {children}
        </div>
    );
}
