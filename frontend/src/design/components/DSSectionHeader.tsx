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
        <div className={clsx('flex flex-col gap-3 md:flex-row md:items-center', align === 'center' && 'text-center md:text-center md:flex-col')}
            style={{ fontFamily: typography.family }}
        >
            <div className={clsx('flex-1 space-y-2', align === 'center' && 'md:items-center')}>
                {eyebrow && (
                    <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">
                        {eyebrow}
                    </p>
                )}
                <h3 className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">{title}</h3>
                {description && <p className="text-sm text-slate-500 dark:text-slate-300 max-w-2xl">{description}</p>}
            </div>
            {actions && (
                <div className={clsx('mt-3 md:mt-0 flex items-center gap-3', align === 'center' && 'justify-center')}>
                    {actions}
                </div>
            )}
        </div>
    );
}
