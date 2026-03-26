"use client";

import React from 'react';
import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { SortableTaskCard } from './SortableTaskCard';
import { Plus } from 'lucide-react';

interface Props {
    id: string;
    name: string;
    color: string;
    tasks: any[];
    onOpenTask: (task: any) => void;
    onAddTask: () => void;
}

export function KanbanColumn({ id, name, color, tasks, onOpenTask, onAddTask }: Props) {
    const { setNodeRef } = useDroppable({ id });

    return (
        <div className="min-w-[300px] w-[300px] flex flex-col shrink-0 gap-3">
            <div className="flex items-center justify-between px-1">
                <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full shadow-sm" style={{ backgroundColor: color }} />
                    <span className="text-[11px] font-black tracking-widest text-slate-500 dark:text-slate-400 uppercase">{name}</span>
                    <span className="text-[10px] text-slate-400 font-bold bg-slate-200 dark:bg-white/10 px-1.5 rounded">{tasks.length}</span>
                </div>
            </div>

            <div ref={setNodeRef} className="flex flex-col gap-3 min-h-[200px]">
                <SortableContext id={id} items={tasks.map(t => t.id)} strategy={verticalListSortingStrategy}>
                    {tasks.map(task => (
                        <SortableTaskCard key={task.id} task={task} onOpen={onOpenTask} />
                    ))}
                </SortableContext>
                
                <button 
                    onClick={onAddTask}
                    className="w-full flex items-center gap-2 py-2 px-3 text-slate-400 hover:text-blue-500 hover:bg-white dark:hover:bg-white/5 rounded-lg border border-dashed border-slate-300 dark:border-white/10 transition-all text-[12px] font-bold mt-1"
                >
                    <Plus size={14} /> Añadir Tarea
                </button>
            </div>
        </div>
    );
}
