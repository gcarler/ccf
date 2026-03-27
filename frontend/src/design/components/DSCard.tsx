"use client";

import React from 'react';
import clsx from 'clsx';
import { radii, shadows } from '../tokens';

interface DSCardProps extends React.HTMLAttributes<HTMLDivElement> {
    tone?: 'light' | 'dark' | 'glass';
    padding?: 'md' | 'lg';
}

export function DSCard({ tone = 'glass', padding = 'lg', className, children, ...props }: DSCardProps) {
    const toneClass =
        tone === 'dark'
            ? 'bg-[#0f1116] border border-white/5'
            : tone === 'light'
            ? 'bg-white border border-slate-100'
            : 'bg-white/10 backdrop-blur-xl border border-white/10';

    const paddingClass = padding === 'lg' ? 'p-6' : 'p-4';

    return (
        <div
            className={clsx('rounded-[2.5rem] shadow-xl', toneClass, paddingClass, className)}
            style={{ borderRadius: radii.bubble, boxShadow: shadows.soft }}
            {...props}
        >
            {children}
        </div>
    );
}
