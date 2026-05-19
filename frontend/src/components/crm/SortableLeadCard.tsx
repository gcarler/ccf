"use client";

import React from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { 
    ChevronRight, 
    Phone, 
    MessageCircle, 
    Clock
} from 'lucide-react';
import clsx from 'clsx';
import { SOURCES, STAGE_PROGRESS } from '@/app/crm/pipeline/constants';

interface SortableLeadCardProps {
    lead: any;
    stage: any;
    onClick: () => void;
    isDragging?: boolean;
}

export function SortableLeadCard({ lead, stage, onClick, isDragging: isOverlayDragging }: SortableLeadCardProps) {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging: isSortableDragging
    } = useSortable({ id: lead.id.toString() });

    const isDragging = isOverlayDragging || isSortableDragging;

    const style = {
        transform: CSS.Translate.toString(transform),
        transition,
        opacity: isDragging ? 0.3 : 1,
        zIndex: isDragging ? 50 : 'auto',
    };

    const daysSince = lead.created_at
        ? Math.floor((Date.now() - new Date(lead.created_at).getTime()) / (1000 * 60 * 60 * 24))
        : null;

    const progress = STAGE_PROGRESS[lead.stage] || 0;
    const radius = 18;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (progress / 100) * circumference;

    const isSlaOverdue = daysSince !== null && daysSince > 7 && lead.stage !== 'consolidated';

    // Premium Color Logic
    const glowColor = stage.color.replace('bg-', 'shadow-');

    return (
        <div
            ref={setNodeRef}
            style={style}
            {...attributes}
            {...listeners}
            onClick={onClick}
            className={clsx(
                "group relative p-4 mb-3 rounded-[1.8rem] transition-all cursor-grab active:cursor-grabbing",
                "bg-white dark:bg-[#1e1f21] border border-slate-200/50 dark:border-white/5",
                "hover:border-blue-500/30 hover:shadow-[0_20px_40px_-15px_rgba(0,0,0,0.05)] dark:hover:shadow-[0_20px_40px_-15px_rgba(0,0,0,0.3)]",
                "hover:-translate-y-1 active:scale-[0.98]",
                isDragging && "opacity-0",
                isOverlayDragging && "opacity-100 scale-105 shadow-2xl ring-2 ring-blue-500/30",
                isSlaOverdue && "ring-1 ring-amber-500/20 shadow-[0_0_20px_rgba(245,158,11,0.05)]"
            )}
        >
            {/* SLA Overdue Pulse */}
            {isSlaOverdue && (
                <div className="absolute inset-0 rounded-[1.8rem] ring-2 ring-amber-500/10 animate-pulse pointer-events-none" />
            )}
            {/* Top Glow Accent */}
            <div className={clsx("absolute top-0 left-6 right-6 h-[1.5px] opacity-20 blur-[1px]", stage.color)} />

            {/* Header: Avatar + Info */}
            <div className="flex items-start gap-4 mb-4 relative">
                <div className="relative shrink-0">
                    {/* Progress Circle SVG */}
                    <svg className="size-11 -rotate-90 absolute -top-0.5 -left-0.5 pointer-events-none">
                        <circle
                            cx="22" cy="22" r={radius}
                            fill="transparent"
                            stroke="currentColor"
                            strokeWidth="2.5"
                            className="text-slate-100 dark:text-white/5"
                        />
                        <circle
                            cx="22" cy="22" r={radius}
                            fill="transparent"
                            stroke="currentColor"
                            strokeWidth="2.5"
                            strokeDasharray={circumference}
                            style={{ 
                                strokeDashoffset: offset,
                                transition: 'stroke-dashoffset 1s cubic-bezier(0.4, 0, 0.2, 1)'
                            }}
                            className={clsx(stage.text, "opacity-40")}
                        />
                    </svg>

                    <div className={clsx(
                        "size-10 rounded-2xl flex items-center justify-center text-white font-black text-xs shadow-lg relative z-10 transition-transform group-hover:scale-105",
                        stage.color,
                        glowColor
                    )}>
                        {lead.first_name?.[0] ?? ''}{lead.last_name?.[0] ?? ''}
                    </div>

                    {isSlaOverdue && (
                        <div className="absolute -top-1 -right-1 size-3 rounded-full bg-amber-500 border-2 border-white dark:border-[#1e1f21] z-20 animate-bounce" />
                    )}
                </div>
                
                <div className="flex-1 min-w-0 pt-0.5">
                    <div className="flex items-center justify-between gap-2">
                        <h4 className="font-black text-slate-900 dark:text-white text-[14px] leading-tight truncate group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                            {lead.first_name} {lead.last_name}
                        </h4>
                        <ChevronRight size={14} className="text-slate-300 group-hover:text-blue-500 group-hover:translate-x-1 transition-all" />
                    </div>
                    <p className="text-[11px] text-slate-400 font-bold flex items-center gap-1 mt-1">
                        <Phone size={10} strokeWidth={3} />
                        {lead.phone}
                    </p>
                </div>
            </div>

            {/* Quick Actions (Hover Reveal) */}
            <div className="absolute top-4 right-4 flex gap-1 opacity-0 group-hover:opacity-100 transition-all scale-90 group-hover:scale-100">
                <button 
                    onClick={(e) => { e.stopPropagation(); window.open(`tel:${lead.phone}`); }}
                    className="size-7 rounded-lg bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center hover:bg-blue-600 hover:text-white transition-all shadow-sm"
                >
                    <Phone size={12} />
                </button>
                <button 
                    onClick={(e) => { e.stopPropagation(); window.open(`https://wa.me/${lead.phone.replace(/[^0-9]/g, '')}`); }}
                    className="size-7 rounded-lg bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center hover:bg-emerald-600 hover:text-white transition-all shadow-sm"
                >
                    <MessageCircle size={12} />
                </button>
            </div>

            {/* Divider */}
            <div className="h-px w-full bg-slate-100 dark:bg-white/5 mb-3.5" />

            {/* Footer Metadata */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <div className="px-2 py-0.5 rounded-lg bg-slate-100 dark:bg-white/5 text-[9px] font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
                        <span className="text-[12px]">{SOURCES[lead.source] ?? '📌'}</span>
                        {lead.source}
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    {daysSince !== null && (
                        <div className={clsx(
                            "flex items-center gap-1 text-[10px] font-black",
                            daysSince > 14 ? 'text-rose-500' :
                            daysSince > 7 ? 'text-amber-500' :
                            'text-slate-400'
                        )}>
                            <Clock size={11} strokeWidth={3} />
                            {daysSince === 0 ? 'HOY' : `${daysSince}d`}
                        </div>
                    )}
                    {lead.notes && (
                        <div className="size-1.5 rounded-full bg-blue-500 animate-pulse shadow-[0_0_8px_rgba(59,130,246,0.6)]" title="Tiene notas" />
                    )}
                </div>
            </div>

            {/* Interaction Indicator */}
            <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 rounded-r-full bg-blue-500 opacity-0 group-hover:opacity-100 transition-all -ml-0.5" />
        </div>
    );
}
