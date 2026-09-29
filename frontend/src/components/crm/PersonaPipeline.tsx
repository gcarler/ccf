"use client";

import React from 'react';
import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy, useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { MessageSquare, MoreHorizontal, Star } from 'lucide-react';
import clsx from 'clsx';

interface PersonaCardProps {
    persona: any;
    onClick: (persona: any) => void;
}

function SortablePersonaCard({ persona, onClick }: PersonaCardProps) {
    const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: persona.id });
    const style = { transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.5 : 1 };

    return (
        <div
            ref={setNodeRef} style={style} {...attributes} {...listeners}
            onClick={() => onClick(persona)}
            className="p-4 bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] shadow-sm hover:shadow-xl hover:border-[hsl(var(--primary)/0.3)] transition-all cursor-grab active:cursor-grabbing group"
        >
            <div className="flex items-start gap-3">
                <div className="size-8 rounded-md bg-[hsl(var(--primary))] flex items-center justify-center text-[hsl(var(--primary-foreground))] font-bold shadow-lg shadow-[hsl(var(--primary)/0.2)]">
                    {persona.name.substring(0, 1)}
                </div>
                <div className="flex-1 min-w-0">
                    <h4 className="text-xs font-bold text-[hsl(var(--foreground))] truncate tracking-tight">{persona.name}</h4>
                    <p className="text-2xs text-[hsl(var(--muted-foreground))] font-bold uppercase tracking-wide">{persona.group}</p>
                </div>
            </div>

            <div className="mt-4 pt-3 border-t border-[hsl(var(--border))] flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <div className="size-5 rounded-lg bg-[hsl(var(--surface-2))] flex items-center justify-center text-[hsl(var(--muted-foreground))]">
                        <MessageSquare size={12} />
                    </div>
                    <span className="text-2xs font-bold text-[hsl(var(--muted-foreground))]">2</span>
                </div>
                <div className="flex items-center gap-1.5 px-2 py-0.5 bg-[hsl(var(--success)/0.1)] text-[hsl(var(--success))] rounded-md text-2xs font-bold uppercase">
                    <Star size={10} /> VIP
                </div>
            </div>
        </div>
    );
}

export function PersonaPipelineColumn({ id, title, color, personas, onOpenPersona }: any) {
    const { setNodeRef } = useDroppable({ id });

    return (
        <div className="min-w-[320px] w-[320px] flex flex-col shrink-0 gap-4">
            <div className="flex items-center justify-between px-2">
                <div className="flex items-center gap-2">
                    <div className={clsx("size-2 rounded-full", color)} />
                    <span className="text-xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">{title}</span>
                    <span className="text-2xs font-bold bg-[hsl(var(--surface-2))] px-2 py-0.5 rounded-full text-[hsl(var(--muted-foreground))]">{personas.length}</span>
                </div>
                <MoreHorizontal size={14} className="text-[hsl(var(--muted-foreground))] cursor-pointer" />
            </div>

            <div ref={setNodeRef} className="flex flex-col gap-3 min-h-48">
                <SortableContext id={id} items={personas.map((m: any) => m.id)} strategy={verticalListSortingStrategy}>
                    {personas.map((persona: any) => (
                        <SortablePersonaCard key={persona.id} persona={persona} onClick={onOpenPersona} />
                    ))}
                </SortableContext>
            </div>
        </div>
    );
}
