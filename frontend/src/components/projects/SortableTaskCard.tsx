"use client";

import React from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { CalendarDays, MessageSquare, Flag, GripVertical } from 'lucide-react';
import clsx from 'clsx';
import { format, isPast, isToday } from 'date-fns';
import { es } from 'date-fns/locale';

interface Props {
    task: any;
    onOpen: (task: any) => void;
}

const PRIORITY_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
    urgent: { label: 'Urgente', color: 'text-red-500',    bg: 'bg-red-50 dark:bg-red-900/20'    },
    high:   { label: 'Alta',    color: 'text-orange-500', bg: 'bg-orange-50 dark:bg-orange-900/20' },
    normal: { label: 'Normal',  color: 'text-blue-500',   bg: 'bg-blue-50 dark:bg-blue-900/20'  },
    low:    { label: 'Baja',    color: 'text-slate-400',  bg: 'bg-slate-50 dark:bg-white/5'     },
};

export function SortableTaskCard({ task, onOpen }: Props) {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging
    } = useSortable({ id: task.id });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.4 : 1,
        zIndex: isDragging ? 999 : 'auto',
    };

    const priority = PRIORITY_CONFIG[task.priority?.toLowerCase()] || PRIORITY_CONFIG.normal;

    const dueDateStr = task.due_date || task.dueDate;
    const dueDate    = dueDateStr ? new Date(dueDateStr) : null;
    const isOverdue  = dueDate && isPast(dueDate) && !isToday(dueDate);
    const isDueToday = dueDate && isToday(dueDate);

    // Initials from assignee name
    const assigneeInitials = task.assignee_name
        ? task.assignee_name.split(' ').map((n: string) => n[0]).join('').slice(0, 2).toUpperCase()
        : task.assignee?.substring(0, 2).toUpperCase() || '?';

    const commentCount = task.comments_count ?? task.comments?.length ?? 0;

    return (
        <div
            ref={setNodeRef}
            style={style}
            onClick={() => onOpen(task)}
            className={clsx(
                'bg-white dark:bg-[#25262b] rounded-xl shadow-sm border cursor-pointer',
                'hover:shadow-md hover:border-blue-400/50 dark:hover:border-blue-500/40',
                'transition-all duration-150 group/card relative overflow-hidden',
                isDragging
                    ? 'shadow-2xl border-blue-500'
                    : 'border-slate-200 dark:border-white/8'
            )}
        >
            {/* Priority accent line */}
            <div className={clsx('h-[3px] w-full', priority.color.replace('text-', 'bg-'))} />

            <div className="p-3.5 space-y-3">
                {/* Drag handle + Title */}
                <div className="flex items-start gap-2">
                    <div
                        {...attributes}
                        {...listeners}
                        className="mt-0.5 opacity-0 group-hover/card:opacity-40 hover:opacity-100 cursor-grab active:cursor-grabbing transition-opacity shrink-0"
                        onClick={e => e.stopPropagation()}
                    >
                        <GripVertical size={14} className="text-slate-400" />
                    </div>
                    <p className="text-[13px] font-semibold text-slate-800 dark:text-slate-100 leading-snug flex-1 line-clamp-2">
                        {task.title}
                    </p>
                </div>

                {/* Metadata row */}
                <div className="flex items-center justify-between gap-2">
                    {/* Left: date + priority */}
                    <div className="flex items-center gap-2 flex-wrap">
                        {dueDate && (
                            <span className={clsx(
                                'flex items-center gap-1 text-[10px] font-bold rounded-full px-2 py-0.5',
                                isOverdue
                                    ? 'text-red-600 bg-red-50 dark:bg-red-900/30'
                                    : isDueToday
                                    ? 'text-amber-600 bg-amber-50 dark:bg-amber-900/30'
                                    : 'text-slate-500 bg-slate-100 dark:bg-white/8'
                            )}>
                                <CalendarDays size={10} />
                                {format(dueDate, 'd MMM', { locale: es })}
                            </span>
                        )}
                        <span className={clsx(
                            'flex items-center gap-1 text-[10px] font-bold rounded-full px-2 py-0.5',
                            priority.color, priority.bg
                        )}>
                            <Flag size={9} fill="currentColor" />
                            {priority.label}
                        </span>
                    </div>

                    {/* Right: comments + assignee avatar */}
                    <div className="flex items-center gap-2 shrink-0">
                        {commentCount > 0 && (
                            <span className="flex items-center gap-1 text-[10px] font-bold text-slate-400">
                                <MessageSquare size={11} />
                                {commentCount}
                            </span>
                        )}
                        <div
                            className="size-6 rounded-full bg-gradient-to-br from-slate-700 to-slate-900 dark:from-blue-600 dark:to-indigo-700 flex items-center justify-center text-[9px] font-black text-white shadow ring-2 ring-white dark:ring-[#25262b]"
                            title={task.assignee_name || 'Sin asignar'}
                        >
                            {assigneeInitials}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
