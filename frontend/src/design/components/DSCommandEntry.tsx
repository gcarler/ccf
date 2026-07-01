"use client";

import React from 'react';
import clsx from 'clsx';
import type { LucideIcon } from 'lucide-react';
import { CornerDownLeft } from 'lucide-react';

interface DSCommandEntryProps extends React.HTMLAttributes<HTMLDivElement> {
    label: string;
    description?: string;
    shortcut?: string;
    icon?: LucideIcon;
    active?: boolean;
}

export function DSCommandEntry({
    label,
    description,
    shortcut,
    icon: Icon,
    active = false,
    className,
    ...props
}: DSCommandEntryProps) {
    return (
        <div
            className={clsx(
                "flex items-center gap-2 rounded-md border px-2.5 py-1.5 transition-all cursor-pointer",
                active
                    ? "border-blue-500/40 bg-[hsl(var(--primary))] text-white shadow-sm"
                    : "border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))] hover:border-blue-300 hover:bg-blue-50",
                className
            )}
            {...props}
        >
            <div
                className={clsx(
                    "flex h-6 w-6 shrink-0 items-center justify-center rounded-md",
                    active ? "bg-white/20 text-white" : "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]",
                )}
            >
                {Icon ? <Icon size={13} /> : <CornerDownLeft size={13} />}
            </div>
            <div className="min-w-0 flex-1">
                <p className="truncate text-xs font-semibold tracking-tight">{label}</p>
                {description ? (
                    <p className={clsx("truncate text-[10px]", active ? "text-white/80" : "text-[hsl(var(--text-secondary))]")}>
                        {description}
                    </p>
                ) : null}
            </div>
            {shortcut ? (
                <span
                    className={clsx(
                        "rounded-md px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide",
                        active ? "bg-white/20 text-white" : "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]",
                    )}
                >
                    {shortcut}
                </span>
            ) : null}
        </div>
    );
}
