"use client";

import React from 'react';
import { LucideIcon, ArrowUpRight, Bot } from 'lucide-react';
import CommunityToolbarChip from '@/components/community/ToolbarChip';
import { getInitials } from '@/lib/community/utils';

type HeroAction = {
    label: string;
    icon?: LucideIcon;
    onClick?: () => void;
    variant?: 'primary' | 'secondary';
};

type CommandShortcut = {
    label: string;
    command: string;
};

type CommandBar = {
    title: string;
    description: string;
    ctaLabel: string;
    shortcuts: CommandShortcut[];
};

interface AdminHeroProps {
    eyebrow?: string;
    title: string;
    description: string;
    tags?: string[];
    watchers?: string[];
    primaryAction?: HeroAction;
    secondaryAction?: HeroAction;
    commandBar?: CommandBar;
}

export default function AdminHero({
    eyebrow = 'Mando central',
    title,
    description,
    tags,
    watchers,
    primaryAction,
    secondaryAction,
    commandBar
}: AdminHeroProps) {
    return (
        <section className="relative overflow-hidden rounded-lg border border-[hsl(var(--border))] bg-gradient-to-br from-white via-[hsl(var(--surface-1))] to-[hsl(var(--surface-2))] dark:from-[#1e1f21] dark:via-[#18191c] dark:to-[#0f1012] p-4 space-y-3">
            <div className="absolute inset-y-0 right-8 w-72 bg-gradient-to-br to-[hsl(var(--info)/20%)] via-[hsl(var(--info)/10%)] to-transparent blur-3xl pointer-events-none" />
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3 relative z-10">
                <div className="space-y-3 max-w-3xl">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))]">{eyebrow}</p>
                    <h1 className="text-xl md:text-xl font-semibold text-[hsl(var(--text-primary))] leading-tight">{title}</h1>
                    <p className="text-[13px] md:text-sm text-[hsl(var(--text-secondary))]">{description}</p>
                    {tags && (
                        <div className="flex flex-wrap gap-2">
                            {tags.map((pill) => (
                                <CommunityToolbarChip key={pill} label={pill} size="sm" />
                            ))}
                        </div>
                    )}
                </div>
                <div className="flex flex-col gap-3 w-full max-w-xs relative z-10">
                    {watchers && watchers.length > 0 && (
                        <div className="flex -space-x-3">
                            {watchers.map((person, index) => (
                                <div
                                    key={person}
                                    className="size-6 rounded-full border-2 border-white bg-[hsl(var(--surface-2))] flex items-center justify-center text-[11px] font-semibold text-[hsl(var(--text-primary))]"
                                    style={{ zIndex: watchers.length - index }}
                                >
                                    {getInitials(person)}
                                </div>
                            ))}
                        </div>
                    )}
                    {primaryAction && (
                        <button
                            type="button"
                            onClick={primaryAction.onClick}
                            className="px-3 h-8 rounded-lg bg-[hsl(var(--text-primary))] text-white text-[10px] font-semibold uppercase tracking-wide flex items-center justify-center gap-2 shadow-lg shadow-black/20"
                        >
                            {primaryAction.label}
                            {primaryAction.icon ? <primaryAction.icon size={16} /> : <ArrowUpRight size={16} />}
                        </button>
                    )}
                    {secondaryAction && (
                        <button
                            type="button"
                            onClick={secondaryAction.onClick}
                            className="px-3 h-8 rounded-lg border border-[hsl(var(--border))] text-[10px] font-semibold uppercase tracking-wide flex items-center justify-center gap-2"
                        >
                            {secondaryAction.label}
                            {secondaryAction.icon && <secondaryAction.icon size={14} />}
                        </button>
                    )}
                </div>
            </div>
            {commandBar && (
                <div className="rounded-lg border border-[hsl(var(--border))] bg-white/80 dark:bg-white/5 px-3 py-1.5 space-y-3 shadow-[0_20px_70px_rgba(15,23,42,0.15)] relative z-10">
                    <div className="flex items-center gap-3">
                        <div className="size-9 rounded-md bg-[hsl(var(--bg-muted))] text-white flex items-center justify-center">
                            <Bot size={16} />
                        </div>
                        <div className="flex-1">
                            <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{commandBar.title}</p>
                            <p className="text-sm text-[hsl(var(--text-primary))] dark:text-white font-semibold">{commandBar.description}</p>
                        </div>
                        <button className="px-4 h-9 rounded-full bg-[hsl(var(--bg-muted))] text-white text-[10px] font-semibold uppercase tracking-wide">
                            {commandBar.ctaLabel}
                        </button>
                    </div>
                    {commandBar.shortcuts && commandBar.shortcuts.length > 0 && (
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[11px] text-[hsl(var(--text-secondary))]">
                            {commandBar.shortcuts.map((shortcut) => (
                                <div key={shortcut.label} className="rounded-md border border-dashed border-[hsl(var(--border))] px-4 py-3 bg-white/70 dark:bg-white/5">
                                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1">{shortcut.label}</p>
                                    <p className="text-sm text-[hsl(var(--text-primary))] dark:text-white font-semibold">{shortcut.command}</p>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </section>
    );
}
