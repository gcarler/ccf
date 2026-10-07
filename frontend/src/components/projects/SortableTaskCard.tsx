"use client";

import { useState } from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { MessageSquare, GripVertical, MoreHorizontal, Trash2, Eye } from 'lucide-react';
import { InlinePriorityPicker, InlineDatePicker, InlineUserPicker, InlineTextInput } from '@/components/ui/inline-editors';
import { PROJECT_ASSIGNEE_CANDIDATES_ENDPOINT, TASK_TITLE_MAX_LENGTH } from '@/lib/projects/constants';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import ConfirmActionDrawer, { type ConfirmActionState } from '@/components/ConfirmActionDrawer';
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
    urgent: { label: PRIORITY_LABELS.urgent, color: 'text-[hsl(var(--destructive))]', bg: 'bg-[hsl(var(--destructive)/0.12)]' },
    high:   { label: PRIORITY_LABELS.high,   color: 'text-[hsl(var(--warning))]',     bg: 'bg-[hsl(var(--warning)/0.12)]' },
    medium: { label: PRIORITY_LABELS.medium, color: 'text-[hsl(var(--primary))]',     bg: 'bg-[hsl(var(--primary)/0.15)]' },
    low:    { label: PRIORITY_LABELS.low,    color: 'text-[hsl(var(--muted-foreground))]', bg: 'bg-[hsl(var(--surface-2))]' },
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
    const [confirmDelete, setConfirmDelete] = useState<ConfirmActionState>(null);
    const priority = PRIORITY_CONFIG[task.priority?.toLowerCase()] || PRIORITY_CONFIG.medium;

    const dueDateStr = task.due_date || undefined;
    const commentCount = task.comments_count ?? 0;

    const handleDelete = () => {
        setMenuOpen(false);
        const label = task.title || 'esta tarea';
        setConfirmDelete({
            title: 'Eliminar tarea',
            description: `¿Eliminar la tarea "${label}"? Esta acción no se puede deshacer.`,
            confirmLabel: 'Eliminar',
            destructive: true,
            onConfirm: async () => {
                await Promise.resolve(onDelete?.(String(task.id)));
            },
        });
    };

    return (
        <article
            ref={setNodeRef}
            data-testid={`task-card-${task.id}`}
            style={style}
            className={clsx(
                'bg-[hsl(var(--surface-1))] rounded-md shadow-sm border',
                'hover:shadow-md hover:border-[hsl(var(--primary))]',
                'transition-all duration-150 group/card relative overflow-hidden',
                isDragging
                    ? 'shadow-2xl border-[hsl(var(--primary))]'
                    : 'border-[hsl(var(--border))]'
            )}
        >
            {/* Priority accent line */}
            <div className={clsx('h-[3px] w-full', priority.color.replace('text-', 'bg-'))} />

            <div className="p-3.5 space-y-3">
                {/* Drag handle + Title */}
                <div className="flex items-start gap-2">
                    <button
                        type="button"
                        {...attributes}
                        {...listeners}
                        aria-label={`Arrastrar tarea ${task.title}`}
                        className="mt-0.5 opacity-0 group-hover/card:opacity-40 hover:opacity-100 cursor-grab active:cursor-grabbing transition-opacity shrink-0 p-0.5 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--primary))] focus-visible:ring-offset-2"
                        onClick={e => e.stopPropagation()}
                    >
                        <GripVertical size={14} className="text-[hsl(var(--muted-foreground))]" />
                    </button>
                    <div
                        className="flex-1 min-w-0"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <InlineTextInput
                            value={task.title}
                            onChange={(v) => onUpdate?.(String(task.id), { title: v })}
                            placeholder="Título de la tarea"
                            ariaLabel={`Título de la tarea ${task.title}`}
                            maxLength={TASK_TITLE_MAX_LENGTH}
                            className="text-base font-semibold text-[hsl(var(--foreground))] leading-snug line-clamp-2"
                            inputClassName="text-base"
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
                            <span className="flex items-center gap-1 text-2xs font-bold text-[hsl(var(--muted-foreground))]">
                                <MessageSquare size={11} />
                                {commentCount}
                            </span>
                        )}
                        <InlineUserPicker
                            endpoint={PROJECT_ASSIGNEE_CANDIDATES_ENDPOINT}
                            value={task.assignee_id ?? null}
                            onChange={(userId) => onUpdate?.(String(task.id), { assignee_id: userId })}
                        />
                        <button
                            type="button"
                            onClick={() => onOpen(task)}
                            aria-label={`Abrir detalle de tarea ${task.title}`}
                            className="size-8 rounded-lg flex items-center justify-center text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--primary))] hover:bg-[hsl(var(--surface-2))] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--primary))] focus-visible:ring-offset-2"
                        >
                            <Eye size={14} aria-hidden="true" />
                        </button>
                        <DropdownMenu.Root open={menuOpen} onOpenChange={setMenuOpen}>
                            <DropdownMenu.Trigger asChild>
                                <button
                                    onClick={(e) => e.stopPropagation()}
                                    className="size-7 rounded-lg flex items-center justify-center text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--primary))] hover:bg-[hsl(var(--surface-2))] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--primary))] focus-visible:ring-offset-2"
                                    aria-label="Opciones de tarea"
                                >
                                    <MoreHorizontal size={14} />
                                </button>
                            </DropdownMenu.Trigger>
                            <DropdownMenu.Portal>
                                <DropdownMenu.Content
                                    align="end"
                                    sideOffset={4}
                                    className="z-[500] min-w-[160px] bg-[hsl(var(--surface-1))] rounded-md shadow-2xl border border-[hsl(var(--border))] p-1"
                                >
                                    {onDelete && (
                                        <>
                                            <DropdownMenu.Separator className="h-px bg-[hsl(var(--border))] my-1" />
                                            <DropdownMenu.Item
                                                onClick={handleDelete}
                                                className="flex items-center gap-2 px-2.5 py-2 text-sm font-semibold text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive)/0.1)] rounded-lg cursor-pointer outline-none"
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
            <ConfirmActionDrawer action={confirmDelete} onClose={() => setConfirmDelete(null)} />
        </article>
    );
}
