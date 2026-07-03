"use client";

import React from 'react';
import * as TooltipPrimitive from '@radix-ui/react-tooltip';

interface TooltipProps {
    children: React.ReactNode;
    content: string;
    side?: 'top' | 'right' | 'bottom' | 'left';
}

export default function Tooltip({ children, content, side = 'top' }: TooltipProps) {
    return (
        <TooltipPrimitive.Provider delayDuration={300}>
            <TooltipPrimitive.Root>
                <TooltipPrimitive.Trigger asChild>
                    {children}
                </TooltipPrimitive.Trigger>
                <TooltipPrimitive.Portal>
                    <TooltipPrimitive.Content
                        side={side}
                        sideOffset={5}
                        className="z-[10000] select-none rounded-lg bg-[hsl(var(--bg-muted))] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-primary))] dark:text-white shadow-xl border border-white/10 animate-in fade-in zoom-in-95 duration-200"
                    >
                        {content}
                        <TooltipPrimitive.Arrow className="fill-[hsl(var(--bg-muted))]" />
                    </TooltipPrimitive.Content>
                </TooltipPrimitive.Portal>
            </TooltipPrimitive.Root>
        </TooltipPrimitive.Provider>
    );
}
