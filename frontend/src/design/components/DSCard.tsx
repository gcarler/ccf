"use client";

import React from 'react';
import clsx from 'clsx';

interface DSCardProps extends React.HTMLAttributes<HTMLDivElement> {
    tone?: 'light' | 'dark' | 'glass';
    padding?: 'sm' | 'md';
}

export function DSCard({ tone = 'light', padding = 'md', className, children, ...props }: DSCardProps) {
    const toneClass =
        tone === 'dark'
            ? 'bg-[hsl(var(--bg-primary))]/5 border border-white/5'
            : tone === 'light'
            ? 'bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border))]'
            : 'bg-white/10 backdrop-blur-xl border border-white/10';

    const paddingClass = padding === 'md' ? 'p-3' : 'p-2';

    return (
        <div
            className={clsx('rounded-lg shadow-sm', toneClass, paddingClass, className)}
            {...props}
        >
            {children}
        </div>
    );
}
