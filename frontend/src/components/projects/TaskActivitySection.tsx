"use client";

import { useState, useRef, useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Check, ChevronDown, ChevronRight, Plus, X } from 'lucide-react';
import clsx from 'clsx';

export interface Activity {
    id: string;
    title: string;
    completed: boolean;
    assignee?: { name: string; color?: string };
    children?: Activity[];
}

export function toggleActivity(activities: Activity[], id: string): Activity[] {
    return activities.map(a => {
        if (a.id === id) return { ...a, completed: !a.completed };
        if (a.children) return { ...a, children: toggleActivity(a.children, id) };
        return a;
    });
}

export function addChild(activities: Activity[], parentId: string, newItem: Activity): Activity[] {
    return activities.map(a => {
        if (a.id === parentId) return { ...a, children: [...(a.children ?? []), newItem] };
        if (a.children) return { ...a, children: addChild(a.children, parentId, newItem) };
        return a;
    });
}

export function updateTitle(activities: Activity[], id: string, title: string): Activity[] {
    return activities.map(a => {
        if (a.id === id) return { ...a, title };
        if (a.children) return { ...a, children: updateTitle(a.children, id, title) };
        return a;
    });
}

function ActivityItem({
    activity,
    depth = 0,
    onToggle,
    onAddChild,
    onUpdateTitle,
    onDelete,
}: {
    activity: Activity;
    depth?: number;
    onToggle: (id: string) => void;
    onAddChild: (parentId: string) => void;
    onUpdateTitle: (id: string, title: string) => void;
    onDelete: (id: string) => void;
}) {
    const [expanded, setExpanded] = useState(depth === 0);
    const [editing, setEditing] = useState(false);
    const [titleVal, setTitleVal] = useState(activity.title);
    const hasChildren = (activity.children?.length ?? 0) > 0;
    const inputRef = useRef<HTMLInputElement>(null);
    const cancelEditRef = useRef(false);

    useEffect(() => { if (editing) inputRef.current?.focus(); }, [editing]);

    return (
        <div>
            <div
                className={clsx(
                    'group flex items-center gap-1.5 py-1.5 px-2 rounded-lg transition-colors hover:bg-[hsl(var(--surface-1))] relative',
                )}
                style={{ paddingLeft: depth * 20 + 8 }}
            >
                {depth > 0 && (
                    <div
                        className="absolute left-0 top-0 bottom-0 w-px bg-[hsl(var(--border))]"
                        style={{ left: depth * 20 - 4 }}
                    />
                )}

                {hasChildren ? (
                    <button
                        type="button"
                        onClick={() => setExpanded(v => !v)}
                        aria-expanded={expanded}
                        aria-label={`${expanded ? 'Contraer' : 'Expandir'} sub-actividades de ${activity.title}`}
                        className="size-4 flex items-center justify-center text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] transition-colors shrink-0"
                    >
                        {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                    </button>
                ) : <span aria-hidden="true" className="size-4 shrink-0" />}

                <button
                    type="button"
                    onClick={() => onToggle(activity.id)}
                    aria-pressed={activity.completed}
                    aria-label={activity.completed ? `Marcar como pendiente: ${activity.title}` : `Completar actividad: ${activity.title}`}
                    className={clsx(
                        'size-4 rounded border-2 flex items-center justify-center shrink-0 transition-all',
                        activity.completed
                            ? 'bg-[hsl(var(--success))] border-[hsl(var(--success))] text-[hsl(var(--primary-foreground))]'
                            : 'border-[hsl(var(--border))] hover:border-[hsl(var(--primary))]'
                    )}
                >
                    {activity.completed && <Check size={9} strokeWidth={3} />}
                </button>

                {editing ? (
                    <input
                        ref={inputRef}
                        aria-label={`Editar actividad: ${activity.title}`}
                        value={titleVal}
                        onChange={e => setTitleVal(e.target.value)}
                        onBlur={() => {
                            if (cancelEditRef.current) {
                                cancelEditRef.current = false;
                            } else {
                                onUpdateTitle(activity.id, titleVal);
                            }
                            setEditing(false);
                        }}
                        onKeyDown={e => {
                            if (e.key === 'Enter') {
                                e.preventDefault();
                                inputRef.current?.blur();
                            }
                            if (e.key === 'Escape') {
                                e.preventDefault();
                                cancelEditRef.current = true;
                                setTitleVal(activity.title);
                                inputRef.current?.blur();
                            }
                        }}
                        className="flex-1 text-sm bg-transparent outline-none border-b border-[hsl(var(--primary))] text-[hsl(var(--foreground))]"
                    />
                ) : (
                    <button
                        type="button"
                        onClick={() => setEditing(true)}
                        aria-label={`Editar actividad: ${activity.title}`}
                        className={clsx(
                            'flex-1 text-left text-sm font-medium cursor-text select-none truncate',
                            activity.completed
                                ? 'line-through text-[hsl(var(--muted-foreground))]'
                                : 'text-[hsl(var(--foreground))]'
                        )}
                    >
                        {activity.title}
                    </button>
                )}

                {activity.assignee && (
                    <div
                        title={activity.assignee.name}
                        className="size-5 rounded-full flex items-center justify-center font-semibold text-[hsl(var(--primary-foreground))] shrink-0"
                        style={{ backgroundColor: activity.assignee.color ?? 'hsl(var(--primary))' }}
                    >
                        {activity.assignee.name.charAt(0).toUpperCase()}
                    </div>
                )}

                <button
                    type="button"
                    onClick={() => { onAddChild(activity.id); setExpanded(true); }}
                    aria-label={`Añadir sub-actividad a ${activity.title}`}
                    className="size-4 rounded flex items-center justify-center text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary)/0.1)] opacity-100 md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100 transition-all"
                    title="Añadir sub-actividad"
                >
                    <Plus size={10} strokeWidth={2.5} />
                </button>

                <button
                    type="button"
                    onClick={() => onDelete(activity.id)}
                    aria-label={`Eliminar actividad: ${activity.title}`}
                    className="size-4 rounded flex items-center justify-center text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive)/0.1)] opacity-100 md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100 transition-all"
                    title="Eliminar actividad"
                >
                    <X size={10} strokeWidth={2.5} />
                </button>
            </div>

            <AnimatePresence initial={false}>
                {expanded && hasChildren && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.18 }}
                        className="overflow-hidden"
                    >
                        {activity.children!.map(child => (
                            <ActivityItem
                                key={child.id}
                                activity={child}
                                depth={depth + 1}
                                onToggle={onToggle}
                                onAddChild={onAddChild}
                                onUpdateTitle={onUpdateTitle}
                                onDelete={onDelete}
                            />
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

export default function TaskActivitySection({
    activities,
    newActivityTitle,
    onNewActivityTitleChange,
    onAddTopLevel,
    onToggle,
    onAddChild,
    onUpdateTitle,
    onDelete,
}: {
    activities: Activity[];
    newActivityTitle: string;
    onNewActivityTitleChange: (v: string) => void;
    onAddTopLevel: () => void;
    onToggle: (id: string) => void;
    onAddChild: (parentId: string) => void;
    onUpdateTitle: (id: string, title: string) => void;
    onDelete: (id: string) => void;
}) {
    return (
        <section className="px-4 py-3 border-b border-[hsl(var(--border))]">
            <div className="flex items-center justify-between mb-3">
                <h3 id="task-activities-heading" className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))] flex items-center gap-1.5">
                    <Check size={11} /> Actividades
                    <span className="px-1.5 py-0.5 bg-[hsl(var(--surface-2))] rounded text-[hsl(var(--muted-foreground))] font-bold text-2xs">
                        {activities.length}
                    </span>
                </h3>
            </div>

            <div className="space-y-0.5">
                {activities.map(a => (
                    <ActivityItem
                        key={a.id}
                        activity={a}
                        depth={0}
                        onToggle={onToggle}
                        onAddChild={onAddChild}
                        onUpdateTitle={onUpdateTitle}
                        onDelete={onDelete}
                    />
                ))}
            </div>

            <div className="flex items-center gap-2 mt-2 pl-2">
                <Plus size={13} className="text-[hsl(var(--muted-foreground))] shrink-0" />
                <input
                    type="text"
                    aria-label="Añadir actividad"
                    value={newActivityTitle}
                    onChange={e => onNewActivityTitleChange(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && onAddTopLevel()}
                    placeholder="Añadir actividad..."
                    className="flex-1 text-sm bg-transparent outline-none text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))]"
                />
                {newActivityTitle.trim() && (
                    <button
                        type="button"
                        aria-label="Añadir actividad"
                        onClick={onAddTopLevel}
                        className="px-2 py-1 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-lg text-2xs font-bold hover:bg-[hsl(var(--primary))] transition-all"
                    >
                        + Añadir
                    </button>
                )}
            </div>
        </section>
    );
}
