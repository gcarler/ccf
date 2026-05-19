"use client";

import React from 'react';
import * as HoverCardPrimitive from '@radix-ui/react-hover-card';
import clsx from 'clsx';

interface HoverCardProps {
    trigger: React.ReactNode;
    children: React.ReactNode;
    className?: string;
}

export default function HoverCard({ trigger, children, className }: HoverCardProps) {
    return (
        <HoverCardPrimitive.Root openDelay={300} closeDelay={100}>
            <HoverCardPrimitive.Trigger asChild>
                <div className="inline-block cursor-help">
                    {trigger}
                </div>
            </HoverCardPrimitive.Trigger>
            
            <HoverCardPrimitive.Portal>
                <HoverCardPrimitive.Content
                    sideOffset={5}
                    align="start"
                    className={clsx(
                        "z-[10000] w-80 rounded-2xl bg-white dark:bg-[#1e1f21] p-5 shadow-2xl border border-slate-200 dark:border-white/10 animate-in fade-in zoom-in-95 duration-200",
                        className
                    )}
                >
                    {children}
                    <HoverCardPrimitive.Arrow className="fill-white dark:fill-[#1e1f21]" />
                </HoverCardPrimitive.Content>
            </HoverCardPrimitive.Portal>
        </HoverCardPrimitive.Root>
    );
}
