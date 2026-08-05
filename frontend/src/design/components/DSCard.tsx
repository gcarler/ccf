"use client";

import React from 'react';
import clsx from 'clsx';

interface DSCardProps extends React.HTMLAttributes<HTMLDivElement> {
    tone?: 'light' | 'dark' | 'glass';
    padding?: 'sm' | 'md';
}

export const DSCard = React.forwardRef<HTMLDivElement, DSCardProps>(
    ({ tone = 'light', padding = 'md', className, children, ...props }, ref) => {
        const toneClass =
            tone === 'dark'
                ? 'bg-[hsl(var(--surface-2))]/10 border border-[hsl(var(--border))]/20'
                : tone === 'glass'
                    ? 'bg-[hsl(var(--surface-2))]/60 backdrop-blur-xl border border-[hsl(var(--border))]/60'
                    : 'bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border))]';

        const paddingClass = padding === 'md' ? 'p-3' : 'p-2';

        return (
            <div
                ref={ref}
                className={clsx('rounded-lg shadow-sm', toneClass, paddingClass, className)}
                {...props}
            >
                {children}
            </div>
        );
    }
);
DSCard.displayName = 'DSCard';
