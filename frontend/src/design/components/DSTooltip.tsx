"use client";

import React from 'react';
import clsx from 'clsx';
import * as TooltipPrimitive from '@radix-ui/react-tooltip';

interface DSTooltipProps {
    children: React.ReactNode;
    content: string;
    side?: 'top' | 'right' | 'bottom' | 'left';
    sideOffset?: number;
}

export function DSTooltip({
    children,
    content,
    side = 'top',
    sideOffset = 5,
}: DSTooltipProps) {
    return (
        <TooltipPrimitive.Provider delayDuration={300}>
            <TooltipPrimitive.Root>
                <TooltipPrimitive.Trigger asChild>
                    {children}
                </TooltipPrimitive.Trigger>
                <TooltipPrimitive.Portal>
                    <TooltipPrimitive.Content
                        side={side}
                        sideOffset={sideOffset}
                        className={clsx(
                            'z-[10000] select-none px-2.5 py-1.5 rounded font-sans',
                            'bg-[hsl(var(--bg-muted))]',
                            'text-2xs font-semibold uppercase tracking-wide',
                            'text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-primary))]',
                            'border border-[hsl(var(--border))]',
                            'shadow-xl',
                            'animate-in fade-in zoom-in-95 duration-200'
                        )}
                    >
                        {content}
                        <TooltipPrimitive.Arrow className="fill-[hsl(var(--bg-muted))]" />
                    </TooltipPrimitive.Content>
                </TooltipPrimitive.Portal>
            </TooltipPrimitive.Root>
        </TooltipPrimitive.Provider>
    );
}
