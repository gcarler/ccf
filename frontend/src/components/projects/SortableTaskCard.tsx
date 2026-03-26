"use client";

import React from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { CalendarDays, MessageSquare, UserCircle, Edit3 } from 'lucide-react';
import { motion } from 'framer-motion';

interface Props {
    task: any;
    onOpen: (task: any) => void;
}

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
        opacity: isDragging ? 0.5 : 1,
    };

    return (
        <div
            ref={setNodeRef}
            style={style}
            {...attributes}
            {...listeners}
            onClick={() => onOpen(task)}
            className="bg-white dark:bg-[#1e1f21] p-4 rounded-xl shadow-sm border border-slate-200 dark:border-white/5 cursor-grab active:cursor-grabbing hover:border-blue-500 transition-colors group/card relative"
        >
            <div className="flex justify-between items-start mb-3">
                <p className="text-[13px] font-bold text-slate-700 dark:text-slate-200 leading-tight pr-4">{task.title}</p>
                <div className="opacity-0 group-hover/card:opacity-100 transition-opacity">
                    <Edit3 size={12} className="text-slate-400 hover:text-blue-500" />
                </div>
            </div>
            <div className="flex items-center justify-between border-t border-slate-50 dark:border-white/5 pt-3">
                <div className="flex items-center gap-3">
                    {task.dueDate && (
                        <div className="text-[10px] font-bold text-rose-500 flex items-center gap-1">
                            <CalendarDays size={10} /> {task.dueDate}
                        </div>
                    )}
                </div>
                <div className="w-6 h-6 rounded-full bg-slate-900 dark:bg-blue-600 flex items-center justify-center text-[9px] font-black text-white shadow-sm ring-2 ring-white dark:ring-[#1e1f21]">
                    {task.assignee || '??'}
                </div>
            </div>
        </div>
    );
}
