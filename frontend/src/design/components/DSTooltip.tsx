"use client";

import React from 'react';
import clsx from 'clsx';
import * as TooltipPrimitive from '@radix-ui/react-tooltip';
import { radii, typography } from '../tokens';

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
                            'z-[10000] select-none px-2.5 py-1.5',
                            'bg-[hsl(var(--bg-muted))]',
                            'text-[9px] font-semibold uppercase tracking-wide',
                            'text-white',
                            'border border-white/10',
                            'shadow-xl',
                            'animate-in fade-in zoom-in-95 duration-200'
                        )}
                        style={{ borderRadius: radii.sm, fontFamily: typography.family }}
                    >
                        {content}
                        <TooltipPrimitive.Arrow className="fill-[hsl(var(--bg-muted))]" />
                    </TooltipPrimitive.Content>
                </TooltipPrimitive.Portal>
            </TooltipPrimitive.Root>
        </TooltipPrimitive.Provider>
    );
}
