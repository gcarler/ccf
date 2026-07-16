"use client";

import React, { useState } from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { MessageSquare, GripVertical, MoreHorizontal, Trash2, Eye } from 'lucide-react';
import { InlinePriorityPicker, InlineDatePicker, InlineUserPicker, InlineTextInput } from '@/components/ui/inline-editors';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import clsx from 'clsx';
import { PRIORITY_LABELS } from '@/lib/projects/constants';
import type { ProjectTaskRecord } from '@/types/projects';

interface Props {
    task: ProjectTaskRecord;
    onOpen: (task: ProjectTaskRecord) => void;
    onUpdate?: (taskId: string, patch: Partial<ProjectTaskRecord>) => void;
    onDelete?: (taskId: string) => void;
}

const PRIORITY_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
    urgent: { label: PRIORITY_LABELS.urgent, color: 'text-[hsl(var(--destructive))]',    bg: 'bg-red-50 dark:bg-red-900/20'    },
    high:   { label: PRIORITY_LABELS.high,   color: 'text-orange-500', bg: 'bg-orange-50 dark:bg-orange-900/20' },
    medium: { label: PRIORITY_LABELS.medium, color: 'text-[hsl(var(--primary))]',   bg: 'bg-blue-50 dark:bg-blue-900/20'  },
    low:    { label: PRIORITY_LABELS.low,    color: 'text-[hsl(var(--text-secondary))]',  bg: 'bg-[hsl(var(--surface-1))] dark:bg-white/5'     },
};

export function SortableTaskCard({ task, onOpen, onUpdate, onDelete }: Props) {
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

    const [menuOpen, setMenuOpen] = useState(false);
    const priority = PRIORITY_CONFIG[task.priority?.toLowerCase()] || PRIORITY_CONFIG.medium;

    const dueDateStr = task.due_date || undefined;
    const commentCount = task.comments_count ?? 0;

    const handleDelete = (e: React.MouseEvent) => {
        e.stopPropagation();
        if (window.confirm(`¿Eliminar la tarea "${task.title}"? Esta acción no se puede deshacer.`)) {
            onDelete?.(String(task.id));
        }
        setMenuOpen(false);
    };

    return (
        <div
            ref={setNodeRef}
            style={style}
            onClick={() => onOpen(task)}
            className={clsx(
                'bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-primary))] rounded-md shadow-sm border cursor-pointer',
                'hover:shadow-md hover:border-blue-400/50 dark:hover:border-blue-500/40',
                'transition-all duration-150 group/card relative overflow-hidden',
                isDragging
                    ? 'shadow-2xl border-blue-500'
                    : 'border-[hsl(var(--border))] dark:border-white/8'
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
                        <GripVertical size={14} className="text-[hsl(var(--text-secondary))]" />
                    </div>
                    <div
                        className="flex-1 min-w-0"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <InlineTextInput
                            value={task.title}
                            onChange={(v) => onUpdate?.(String(task.id), { title: v })}
                            placeholder="Título de la tarea"
                            className="text-[13px] font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] leading-snug line-clamp-2"
                            inputClassName="text-[13px]"
                        />
                    </div>
                </div>

                {/* Metadata row */}
                <div className="flex items-center justify-between gap-2">
                    {/* Left: date + priority */}
                    <div className="flex items-center gap-2 flex-wrap">
                        <InlineDatePicker
                            value={dueDateStr}
                            onChange={(date) => onUpdate?.(String(task.id), { due_date: date })}
                        />
                        <InlinePriorityPicker
                            value={task.priority ?? 'medium'}
                            onChange={(p) => onUpdate?.(String(task.id), { priority: p })}
                            size="sm"
                        />
                    </div>

                    {/* Right: comments + assignee avatar */}
                    <div className="flex items-center gap-2 shrink-0">
                        {commentCount > 0 && (
                            <span className="flex items-center gap-1 text-[10px] font-bold text-[hsl(var(--text-secondary))]">
                                <MessageSquare size={11} />
                                {commentCount}
                            </span>
                        )}
                        <InlineUserPicker
                            value={task.assignee_id ?? null}
                            onChange={(userId) => onUpdate?.(String(task.id), { assignee_id: userId })}
                        />
                        <DropdownMenu.Root open={menuOpen} onOpenChange={setMenuOpen}>
                            <DropdownMenu.Trigger asChild>
                                <button
                                    onClick={(e) => e.stopPropagation()}
                                    className="size-7 rounded-lg flex items-center justify-center text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-blue-50 dark:hover:bg-blue-500/10 transition-colors"
                                    aria-label="Opciones de tarea"
                                >
                                    <MoreHorizontal size={14} />
                                </button>
                            </DropdownMenu.Trigger>
                            <DropdownMenu.Portal>
                                <DropdownMenu.Content
                                    align="end"
                                    sideOffset={4}
                                    className="z-[500] min-w-[160px] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] rounded-md shadow-2xl border border-[hsl(var(--border))]/80 dark:border-white/10 p-1"
                                >
                                    <DropdownMenu.Item
                                        onClick={(e) => { e.stopPropagation(); onOpen(task); setMenuOpen(false); }}
                                        className="flex items-center gap-2 px-2.5 py-2 text-[12px] font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 rounded-lg cursor-pointer outline-none"
                                    >
                                        <Eye size={13} /> Ver detalle
                                    </DropdownMenu.Item>
                                    {onDelete && (
                                        <>
                                            <DropdownMenu.Separator className="h-px bg-[hsl(var(--border))] dark:bg-white/10 my-1" />
                                            <DropdownMenu.Item
                                                onClick={handleDelete}
                                                className="flex items-center gap-2 px-2.5 py-2 text-[12px] font-semibold text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10 rounded-lg cursor-pointer outline-none"
                                            >
                                                <Trash2 size={13} /> Eliminar
                                            </DropdownMenu.Item>
                                        </>
                                    )}
                                </DropdownMenu.Content>
                            </DropdownMenu.Portal>
                        </DropdownMenu.Root>
                    </div>
                </div>
            </div>
        </div>
    );
}
