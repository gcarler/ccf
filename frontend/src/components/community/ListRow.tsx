"use client";

import React from 'react';
import clsx from 'clsx';
import { Calendar, MessageCircle } from 'lucide-react';
import { getInitials, parseCommentCount } from '@/lib/community/utils';

export interface CommunityListItem {
    id: string;
    name: string;
    owner: string;
    due: string;
    priority: 'Alta' | 'Media' | 'Baja';
    status: string;
    comments: string;
    stage: string;
}

interface CommunityListRowProps {
    index: number;
    item: CommunityListItem;
    accentClass: string;
    priorityClass: string;
    statusClass: string;
    className?: string;
    onClick?: () => void;
}

export default function CommunityListRow({
    index,
    item,
    accentClass,
    priorityClass,
    statusClass,
    className,
    onClick
}: CommunityListRowProps) {
    const commentCount = parseCommentCount(item.comments);

    return (
        <div
            onClick={onClick}
            className={clsx(
                'grid grid-cols-[32px_minmax(0,2.4fr)_1.4fr_1.1fr_0.9fr_1fr_0.9fr] items-center gap-4 px-3 py-1.5 border-t border-[hsl(var(--border))] text-sm text-[hsl(var(--text-secondary))] bg-[hsl(var(--bg-primary))] transition-colors',
                onClick ? 'hover:bg-[hsl(var(--surface-2))] cursor-pointer' : '',
                className
            )}
        >
            <div className="text-[11px] text-[hsl(var(--text-secondary))]">#{index + 1}</div>
            <div className="space-y-1 text-[hsl(var(--text-primary))]">
                <div className="flex items-center gap-2 font-semibold">
                    <span className={`size-6 rounded-full border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] flex items-center justify-center text-[10px] text-[hsl(var(--text-secondary))]`}>
                        {item.name.slice(0, 1)}
                    </span>
                    {item.name}
                </div>
                <p className="text-[10px] uppercase tracking-wide text-[hsl(var(--text-secondary))] flex items-center gap-2">
                    <span className={`size-2 rounded-full ${accentClass}`}></span>
                    {item.stage}
                </p>
            </div>
            <div className="flex items-center gap-2 text-[hsl(var(--text-primary))]">
                <div className="size-8 rounded-full bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] font-semibold text-[11px] flex items-center justify-center">
                    {getInitials(item.owner)}
                </div>
                <span className="text-[12px] font-medium">{item.owner}</span>
            </div>
            <div className="flex items-center gap-2 text-[12px] text-[hsl(var(--text-secondary))]">
                <Calendar size={14} /> {item.due}
            </div>
            <div className="flex items-center">
                <span className={`px-3 py-1 rounded-full text-[10px] font-semibold uppercase tracking-wide ${priorityClass}`}>{item.priority}</span>
            </div>
            <div className="flex items-center">
                <span className={`px-3 py-1 rounded-full text-[10px] font-semibold uppercase tracking-wide ${statusClass}`}>{item.status}</span>
            </div>
            <div className="flex items-center justify-end gap-1 text-[12px] text-[hsl(var(--text-secondary))]">
                <MessageCircle size={14} />
                <span>{commentCount}</span>
            </div>
        </div>
    );
}
