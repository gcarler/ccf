"use client";

import React from 'react';
import clsx from 'clsx';
import { shadows, radii } from '../tokens';

interface DSSkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
    rounded?: 'pill' | 'xl' | 'none';
}

export function DSSkeleton({ rounded = 'xl', className, style, ...props }: DSSkeletonProps) {
    return (
        <div
            className={clsx('relative overflow-hidden bg-slate-200 dark:bg-white/10', className)}
            style={{
                borderRadius: rounded === 'pill' ? radii.pill : rounded === 'xl' ? radii.xl : undefined,
                boxShadow: shadows.inner,
                ...style,
            }}
            {...props}
        >
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 dark:via-white/10 to-transparent animate-[shimmer_1.8s_infinite]" />
        </div>
    );
}
