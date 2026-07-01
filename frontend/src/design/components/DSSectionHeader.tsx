"use client";

import React from 'react';
import clsx from 'clsx';
import { typography } from '../tokens';

interface DSSectionHeaderProps {
    eyebrow?: string;
    title: string;
    description?: string;
    actions?: React.ReactNode;
    align?: 'left' | 'center';
}

export function DSSectionHeader({ eyebrow, title, description, actions, align = 'left' }: DSSectionHeaderProps) {
    return (
        <div className={clsx('flex flex-col gap-2 md:flex-row md:items-center', align === 'center' && 'text-center md:text-center md:flex-col')}
            style={{ fontFamily: typography.family }}
        >
            <div className={clsx('flex-1 space-y-1', align === 'center' && 'md:items-center')}>
                {eyebrow && (
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                        {eyebrow}
                    </p>
                )}
                <h3 className="text-base font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight">{title}</h3>
                {description && <p className="text-xs text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] max-w-2xl">{description}</p>}
            </div>
            {actions && (
                <div className={clsx('mt-2 md:mt-0 flex items-center gap-2', align === 'center' && 'justify-center')}>
                    {actions}
                </div>
            )}
        </div>
    );
}
