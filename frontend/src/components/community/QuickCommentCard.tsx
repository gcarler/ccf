"use client";

import React from 'react';
import { LucideIcon, Paperclip, Image, Link2, Smile, Mic, Plus } from 'lucide-react';

interface QuickCommentCardProps {
    title?: string;
    description?: string;
    attachments?: LucideIcon[];
    actionLabel?: string;
}

const defaultIcons: LucideIcon[] = [Paperclip, Image, Link2, Smile, Mic];

export default function QuickCommentCard({
    title = 'Menciona @Brain para crear, encontrar o preguntar.',
    description = 'Deja instrucciones rápidas sin salir de la vista.',
    attachments = defaultIcons,
    actionLabel = 'Registrar'
}: QuickCommentCardProps) {
    return (
        <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] shadow-sm p-4 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div className="flex items-center gap-3 flex-1">
                    <button className="size-10 rounded-full border border-[hsl(var(--border))] flex items-center justify-center text-[hsl(var(--primary))] bg-[hsl(var(--surface-2))]">
                        <Plus size={16} />
                    </button>
                    <div>
                        <p className="text-sm font-semibold text-[hsl(var(--text-primary))]">{title}</p>
                        <p className="text-[11px] text-[hsl(var(--text-secondary))]">{description}</p>
                    </div>
                </div>
                <select className="h-9 rounded-full border border-[hsl(var(--border))] px-4 text-[12px] text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-1))]">
                    <option>Comentario</option>
                    <option>Nota</option>
                    <option>Checklist</option>
                </select>
            </div>
            <div className="flex items-center justify-between text-[12px] text-[hsl(var(--text-secondary))]">
                <div className="flex items-center gap-2">
                    {attachments.map((Icon, index) => (
                        <button key={index} className="p-2 rounded-full border border-[hsl(var(--border))] hover:text-[hsl(var(--primary))]">
                            <Icon size={14} />
                        </button>
                    ))}
                </div>
                <button className="px-4 h-9 rounded-full bg-[hsl(var(--primary))] text-white text-[11px] font-semibold uppercase tracking-wide">
                    {actionLabel}
                </button>
            </div>
        </div>
    );
}
