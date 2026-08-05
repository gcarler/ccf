"use client";

import React from 'react';
import clsx from 'clsx';
import type { AppIcon } from '@/types/icons';
import { CornerDownLeft } from 'lucide-react';

interface DSCommandEntryProps extends React.HTMLAttributes<HTMLDivElement> {
    label: string;
    description?: string;
    shortcut?: string;
    icon?: AppIcon;
    active?: boolean;
    onSelect?: () => void;
}

export const DSCommandEntry = React.forwardRef<HTMLDivElement, DSCommandEntryProps>(
    ({
        label,
        description,
        shortcut,
        icon: Icon,
        active = false,
        onSelect,
        className,
        onClick,
        ...props
    }, ref) => {
        const handleClick = (e: React.MouseEvent<HTMLDivElement>) => {
            onClick?.(e);
            if (!e.defaultPrevented) onSelect?.();
        };
        const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onSelect?.();
            }
        };

        const accessibleName = [label, description, shortcut].filter(Boolean).join('. ');

        return (
            <div
                ref={ref}
                role="button"
                aria-pressed={active}
                aria-label={accessibleName}
                tabIndex={0}
                onClick={handleClick}
                onKeyDown={handleKeyDown}
                className={clsx(
                    "flex items-center gap-2 rounded-md border px-2.5 py-1.5 transition-all cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--primary))]",
                    active
                        ? "border-[hsl(var(--primary))]/40 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-sm"
                        : "border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))] hover:border-[hsl(var(--primary))]/50 hover:bg-[hsl(var(--primary))]/5",
                    className
                )}
                {...props}
            >
                <div
                    className={clsx(
                        "flex h-6 w-6 shrink-0 items-center justify-center rounded-md",
                        active ? "bg-[hsl(var(--primary-foreground))]/20 text-[hsl(var(--primary-foreground))]" : "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]",
                    )}
                >
                    {Icon ? <Icon size={13} /> : <CornerDownLeft size={13} />}
                </div>
                <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-semibold tracking-tight">{label}</p>
                    {description ? (
                        <p className={clsx("truncate text-2xs", active ? "text-[hsl(var(--primary-foreground))]/80" : "text-[hsl(var(--text-secondary))]")}>
                            {description}
                        </p>
                    ) : null}
                </div>
                {shortcut ? (
                    <span
                        className={clsx(
                            "rounded-md px-1.5 py-0.5 text-2xs font-semibold uppercase tracking-wide",
                            active ? "bg-[hsl(var(--primary-foreground))]/20 text-[hsl(var(--primary-foreground))]" : "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]",
                        )}
                    >
                        {shortcut}
                    </span>
                ) : null}
            </div>
        );
    }
);
DSCommandEntry.displayName = 'DSCommandEntry';
