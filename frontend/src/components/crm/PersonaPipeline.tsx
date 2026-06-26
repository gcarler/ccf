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
            className="p-4 bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] rounded-lg border border-slate-200 dark:border-white/5 shadow-sm hover:shadow-xl hover:border-blue-500/30 transition-all cursor-grab active:cursor-grabbing group"
        >
            <div className="flex items-start gap-3">
                <div className="size-8 rounded-md bg-[hsl(var(--primary))] flex items-center justify-center text-white font-bold shadow-lg shadow-blue-500/20">
                    {persona.name.substring(0, 1)}
                </div>
                <div className="flex-1 min-w-0">
                    <h4 className="text-xs font-bold text-slate-800 dark:text-slate-100 truncate tracking-tight">{persona.name}</h4>
                    <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wide">{persona.group}</p>
                </div>
            </div>
            
            <div className="mt-4 pt-3 border-t border-slate-50 dark:border-white/5 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <div className="size-5 rounded-lg bg-slate-50 dark:bg-white/5 flex items-center justify-center text-slate-400">
                        <MessageSquare size={12} />
                    </div>
                    <span className="text-[10px] font-bold text-slate-400">2</span>
                </div>
                <div className="flex items-center gap-1.5 px-2 py-0.5 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 rounded-md text-[9px] font-bold uppercase">
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
                    <span className="text-[11px] font-bold uppercase tracking-wide text-slate-500">{title}</span>
                    <span className="text-[10px] font-bold bg-slate-100 dark:bg-white/5 px-2 py-0.5 rounded-full text-slate-400">{personas.length}</span>
                </div>
                <MoreHorizontal size={14} className="text-slate-300 cursor-pointer" />
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
