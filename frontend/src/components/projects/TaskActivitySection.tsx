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

    useEffect(() => { if (editing) inputRef.current?.focus(); }, [editing]);

    return (
        <div>
            <div
                className={clsx(
                    'group flex items-center gap-1.5 py-1.5 px-2 rounded-lg transition-colors hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.04] relative',
                )}
                style={{ paddingLeft: depth * 20 + 8 }}
            >
                {depth > 0 && (
                    <div
                        className="absolute left-0 top-0 bottom-0 w-px bg-[hsl(var(--surface-3))] dark:bg-white/[0.08]"
                        style={{ left: depth * 20 - 4 }}
                    />
                )}

                <button
                    onClick={() => setExpanded(v => !v)}
                    className={clsx(
                        'size-4 flex items-center justify-center text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] transition-colors shrink-0',
                        !hasChildren && 'opacity-0 pointer-events-none'
                    )}
                >
                    {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                </button>

                <button
                    onClick={() => onToggle(activity.id)}
                    className={clsx(
                        'size-4 rounded border-2 flex items-center justify-center shrink-0 transition-all',
                        activity.completed
                            ? 'bg-[hsl(var(--success))] border-[hsl(var(--success)/100%)] text-white'
                            : 'border-[hsl(var(--border))] dark:border-[hsl(var(--border))] hover:border-[hsl(var(--info)/40%)]'
                    )}
                >
                    {activity.completed && <Check size={9} strokeWidth={3} />}
                </button>

                {editing ? (
                    <input
                        ref={inputRef}
                        value={titleVal}
                        onChange={e => setTitleVal(e.target.value)}
                        onBlur={() => { onUpdateTitle(activity.id, titleVal); setEditing(false); }}
                        onKeyDown={e => {
                            if (e.key === 'Enter') { onUpdateTitle(activity.id, titleVal); setEditing(false); }
                            if (e.key === 'Escape') { setTitleVal(activity.title); setEditing(false); }
                        }}
                        className="flex-1 text-[12px] bg-transparent outline-none border-b border-[hsl(var(--info)/40%)] text-[hsl(var(--text-primary))] dark:text-white"
                    />
                ) : (
                    <span
                        onDoubleClick={() => setEditing(true)}
                        className={clsx(
                            'flex-1 text-[12px] font-medium cursor-default select-none truncate',
                            activity.completed
                                ? 'line-through text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]'
                                : 'text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]'
                        )}
                    >
                        {activity.title}
                    </span>
                )}

                {activity.assignee && (
                    <div
                        title={activity.assignee.name}
                        className="size-5 rounded-full flex items-center justify-center font-semibold text-white shrink-0"
                        style={{ backgroundColor: activity.assignee.color ?? 'hsl(var(--primary))' }}
                    >
                        {activity.assignee.name.charAt(0).toUpperCase()}
                    </div>
                )}

                <button
                    onClick={() => { onAddChild(activity.id); setExpanded(true); }}
                    className="size-4 rounded flex items-center justify-center text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-info-soft dark:hover:bg-[hsl(var(--info))]/10 opacity-0 group-hover:opacity-100 transition-all"
                    title="Añadir sub-actividad"
                >
                    <Plus size={10} strokeWidth={2.5} />
                </button>

                <button
                    onClick={() => onDelete(activity.id)}
                    className="size-4 rounded flex items-center justify-center text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--danger))] hover:bg-danger-soft dark:hover:bg-[hsl(var(--danger))]/10 opacity-0 group-hover:opacity-100 transition-all"
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
        <section className="px-4 py-3 border-b border-[hsl(var(--border))] dark:border-white/[0.05]">
            <div className="flex items-center justify-between mb-3">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] flex items-center gap-1.5">
                    <Check size={11} /> Actividades
                    <span className="px-1.5 py-0.5 bg-[hsl(var(--surface-2))] dark:bg-white/[0.06] rounded text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-bold text-[9px]">
                        {activities.length}
                    </span>
                </p>
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
                <Plus size={13} className="text-[hsl(var(--text-secondary))] shrink-0" />
                <input
                    type="text"
                    value={newActivityTitle}
                    onChange={e => onNewActivityTitleChange(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && onAddTopLevel()}
                    placeholder="Añadir actividad..."
                    className="flex-1 text-[12px] bg-transparent outline-none text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] placeholder:text-[hsl(var(--text-secondary))] dark:placeholder:text-[hsl(var(--text-secondary))]"
                />
                {newActivityTitle.trim() && (
                    <button
                        onClick={onAddTopLevel}
                        className="px-2 py-1 bg-[hsl(var(--primary))] text-white rounded-lg text-[10px] font-bold hover:bg-[hsl(var(--primary))] transition-all"
                    >
                        + Añadir
                    </button>
                )}
            </div>
        </section>
    );
}
