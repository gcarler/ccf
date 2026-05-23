"use client";

import React, { useState, useRef } from 'react';
import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { SortableTaskCard } from './SortableTaskCard';
import { Plus, X } from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import type { ProjectTaskRecord } from '@/types/projects';

interface Props {
    id: string;
    name: string;
    color: string;
    tasks: ProjectTaskRecord[];
    onOpenTask: (task: ProjectTaskRecord) => void;
    onAddTask: () => void;
    projectId?: string | number;
    onTaskCreated?: (task: ProjectTaskRecord) => void;
}

export function KanbanColumn({ id, name, color, tasks, onOpenTask, onAddTask, projectId, onTaskCreated }: Props) {
    const { setNodeRef, isOver } = useDroppable({ id });
    const { token } = useAuth();
    const [isAdding, setIsAdding] = useState(false);
    const [title, setTitle] = useState('');
    const [saving, setSaving] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    const completedCount = tasks.filter(t => t.status === 'done').length;
    const progress = tasks.length > 0 ? Math.round((completedCount / tasks.length) * 100) : 0;

    const handleStartAdd = () => {
        setIsAdding(true);
        setTimeout(() => inputRef.current?.focus(), 60);
    };

    const handleSave = async () => {
        if (!title.trim()) { setIsAdding(false); return; }
        if (projectId && onTaskCreated) {
            setSaving(true);
            try {
                const newTask = await apiFetch<ProjectTaskRecord>(`/projects/${projectId}/tasks`, {
                    method: 'POST',
                    token,
                    body: { title: title.trim(), status: id, priority: 'normal' }
                });
                onTaskCreated(newTask);
            } catch { /* silent */ }
            setSaving(false);
        } else {
            onAddTask();
        }
        setTitle('');
        setIsAdding(false);
    };

    const handleCancel = () => { setTitle(''); setIsAdding(false); };

    return (
        <div className="min-w-[280px] w-[280px] flex flex-col shrink-0 gap-2">
            {/* Column Header */}
            <div className="flex items-center justify-between px-1 pb-1">
                <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full shadow-sm shrink-0" style={{ backgroundColor: color }} />
                    <span className="font-semibold tracking-wide text-slate-500 dark:text-slate-400 uppercase">
                        {name}
                    </span>
                    <span className="text-[10px] text-slate-400 font-bold bg-slate-200 dark:bg-white/10 px-1.5 py-0.5 rounded-md">
                        {tasks.length}
                    </span>
                </div>
                <button
                    onClick={handleStartAdd}
                    className="size-6 rounded-md flex items-center justify-center text-slate-400 hover:text-white hover:bg-blue-500 transition-all"
                    title="Nuevo"
                >
                    <Plus size={13} />
                </button>
            </div>

            {/* Progress bar */}
            {tasks.length > 0 && (
                <div className="px-1">
                    <div className="h-1 w-full rounded-full bg-slate-100 dark:bg-white/5 overflow-hidden">
                        <div
                            className="h-full rounded-full transition-all duration-500"
                            style={{ width: `${progress}%`, backgroundColor: color }}
                        />
                    </div>
                </div>
            )}

            {/* Drop zone */}
            <div
                ref={setNodeRef}
                className={clsx(
                    'flex flex-col gap-2.5 min-h-12 p-2 rounded-md transition-all duration-150',
                    isOver ? 'bg-blue-50/80 dark:bg-blue-500/10 ring-2 ring-blue-400/30' : 'bg-slate-50/40 dark:bg-white/[0.02]'
                )}
            >
                <SortableContext id={id} items={tasks.map(t => t.id)} strategy={verticalListSortingStrategy}>
                    {tasks.map(task => (
                        <SortableTaskCard key={task.id} task={task} onOpen={onOpenTask} />
                    ))}
                </SortableContext>

                {/* Empty drop hint */}
                {tasks.length === 0 && !isAdding && (
                    <div className={clsx(
                        'flex-1 flex items-center justify-center py-2 rounded-lg border-2 border-dashed transition-all',
                        isOver ? 'border-blue-400 bg-blue-50/50' : 'border-slate-200 dark:border-white/10'
                    )}>
                        <p className="text-[11px] text-slate-400 font-medium">Suelta aquí</p>
                    </div>
                )}

                {/* Quick-add inline */}
                <AnimatePresence>
                    {isAdding && (
                        <motion.div
                            initial={{ opacity: 0, y: -8 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -8 }}
                            transition={{ duration: 0.15 }}
                            className="bg-white dark:bg-[#25262b] rounded-md border border-blue-300 dark:border-blue-500/40 shadow-md p-3 flex flex-col gap-2"
                        >
                            <input
                                ref={inputRef}
                                type="text"
                                value={title}
                                onChange={e => setTitle(e.target.value)}
                                onKeyDown={e => {
                                    if (e.key === 'Enter') handleSave();
                                    if (e.key === 'Escape') handleCancel();
                                }}
                                placeholder="Nombre de la tarea..."
                                className="w-full text-[13px] font-medium bg-transparent outline-none text-slate-800 dark:text-slate-200 placeholder:text-slate-400"
                            />
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={handleSave}
                                    disabled={saving || !title.trim()}
                                    className="flex-1 py-1.5 bg-blue-600 text-white text-[11px] font-bold rounded-lg hover:bg-blue-700 disabled:opacity-40 transition-colors"
                                >
                                    {saving ? 'Guardando…' : 'Guardar'}
                                </button>
                                <button
                                    onClick={handleCancel}
                                    className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5 rounded-lg transition-all"
                                >
                                    <X size={13} />
                                </button>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* Add button footer */}
            {!isAdding && (
                <button
                    onClick={handleStartAdd}
                    className="w-full flex items-center gap-2 py-2 px-3 text-slate-400 hover:text-blue-500 hover:bg-white dark:hover:bg-white/5 rounded-lg border border-dashed border-slate-200 dark:border-white/10 transition-all text-[12px] font-bold"
                >
                    <Plus size={13} /> Nuevo
                </button>
            )}
        </div>
    );
}
