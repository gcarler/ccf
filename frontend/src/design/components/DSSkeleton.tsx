"use client";

import React from 'react';
import clsx from 'clsx';

interface DSSkeletonProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'style'> {
    rounded?: 'sm' | 'md' | 'lg' | 'xl' | 'pill' | 'none';
}

const roundedClasses: Record<NonNullable<DSSkeletonProps['rounded']>, string> = {
    sm: 'rounded',
    md: 'rounded-md',
    lg: 'rounded-lg',
    xl: 'rounded-xl',
    pill: 'rounded-full',
    none: '',
};

export function DSSkeleton({ rounded = 'md', className, ...props }: DSSkeletonProps) {
    return (
        <div
            className={clsx(
                'relative overflow-hidden bg-[hsl(var(--surface-3))] dark:bg-[hsl(var(--surface-2))]',
                roundedClasses[rounded],
                className
            )}
            {...props}
        >
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 dark:via-white/10 to-transparent animate-[shimmer_1.8s_infinite] motion-reduce:animate-none" aria-hidden="true" />
        </div>
    );
}
