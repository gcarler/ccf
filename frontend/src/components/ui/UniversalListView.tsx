"use client";

import React, { useState, useMemo } from "react";
import {List, Search, ChevronDown, ChevronRight, User, Calendar, CheckCircle2, Clock, AlertCircle, X} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import clsx from "clsx";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ListItem {
    id: string | number;
    title: string;
    description?: string;
    status?: string;
    priority?: "low" | "medium" | "high" | "urgent";
    assignee?: string;
    date?: string;
    tags?: string[];
    [key: string]: unknown;
}

export interface ListColumn<T = ListItem> {
    key: keyof T | string;
    label: string;
    render?: (item: T) => React.ReactNode;
    width?: string;
}

interface UniversalListViewProps {
    items: ListItem[];
    columns?: ListColumn[];
    onItemClick?: (item: ListItem) => void;
    onCreate?: () => void;
    onDelete?: (item: ListItem) => void;
    title?: string;
    searchable?: boolean;
    emptyMessage?: string;
    storageKey?: string;
    _moduleName?: string;
}

// ─── Priority Colors ──────────────────────────────────────────────────────────

const PRIORITY_STYLES: Record<string, string> = {
    low: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
    medium: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    high: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    urgent: "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400",
};

const STATUS_ICONS: Record<string, React.ElementType> = {
    pending: Clock,
    "in_progress": Clock,
    completed: CheckCircle2,
    resolved: CheckCircle2,
    open: AlertCircle,
};

// ─── Component ────────────────────────────────────────────────────────────────

export default function UniversalListView({
    items,
    columns,
    onItemClick,
    onCreate,
    onDelete,
    title = "Lista",
    searchable = true,
    emptyMessage = "No hay elementos para mostrar",
    storageKey,
    _moduleName,
}: UniversalListViewProps) {
    const [searchQuery, setSearchQuery] = useState("");
    const [expandedId, setExpandedId] = useState<string | number | null>(null);

    // Persist search
    const _storageSearchKey = storageKey ? `${storageKey}_search` : undefined;

    // _Filter items
    const filteredItems = useMemo(() => {
        if (!searchQuery) return items;
        const q = searchQuery.toLowerCase();
        return items.filter((item) =>
            item.title?.toLowerCase().includes(q) ||
            item.description?.toLowerCase().includes(q) ||
            item.tags?.some((t) => t.toLowerCase().includes(q))
        );
    }, [items, searchQuery]);

    // Toggle expand
    const toggleExpand = (id: string | number) => {
        setExpandedId(expandedId === id ? null : id);
    };

    // Default columns if none provided
    const _displayColumns = columns || [
        { key: "title", label: "Título" },
        { key: "status", label: "Estado" },
        { key: "priority", label: "Prioridad" },
        { key: "assignee", label: "Asignado" },
        { key: "date", label: "Fecha" },
    ];

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] rounded-lg border border-[hsl(var(--border-primary))] overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-[hsl(var(--border-primary))]">
                <div className="flex items-center gap-2">
                    <List size={16} className="text-[hsl(var(--text-secondary))]" />
                    <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] uppercase tracking-tight">
                        {title}
                    </h3>
                    <span className="text-[10px] font-bold text-[hsl(var(--text-secondary))] bg-[hsl(var(--bg-muted))] px-2 py-0.5 rounded-full">
                        {filteredItems.length}
                    </span>
                </div>
                <div className="flex items-center gap-2">
                    {searchable && (
                        <div className="relative">
                            <Search size={14} className="absolute left-2 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
                            <input
                                type="text"
                                placeholder="Buscar..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="pl-7 pr-3 py-1.5 text-xs rounded-md border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))] w-48"
                            />
                            {searchQuery && (
                                <button
                                    onClick={() => setSearchQuery("")}
                                    className="absolute right-1.5 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
                                >
                                    <X size={12} />
                                </button>
                            )}
                        </div>
                    )}
                    {onCreate && (
                        <button
                            onClick={onCreate}
                            className="px-3 py-1.5 text-xs font-bold bg-[hsl(var(--primary))] text-white rounded-md hover:opacity-90 transition-opacity"
                        >
                            + Nuevo
                        </button>
                    )}
                </div>
            </div>

            {/* List Items */}
            <div className="flex-1 overflow-y-auto">
                {filteredItems.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-12 px-4">
                        <List size={32} className="text-[hsl(var(--text-secondary))] mb-3" />
                        <p className="text-sm font-medium text-[hsl(var(--text-secondary))]">{emptyMessage}</p>
                    </div>
                ) : (
                    <div className="divide-y divide-[hsl(var(--border-primary))]">
                        <AnimatePresence>
                            {filteredItems.map((item, idx) => {
                                const isExpanded = expandedId === item.id;
                                const StatusIcon = item.status ? STATUS_ICONS[item.status] : null;

                                return (
                                    <motion.div
                                        key={item.id}
                                        initial={{ opacity: 0, y: 4 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0, y: -4 }}
                                        transition={{ delay: idx * 0.02 }}
                                        className="group"
                                    >
                                        {/* Main Row */}
                                        <div
                                            className={clsx(
                                                "flex items-center gap-3 px-4 py-3 cursor-pointer transition-colors",
                                                isExpanded
                                                    ? "bg-[hsl(var(--bg-muted))]"
                                                    : "hover:bg-[hsl(var(--bg-muted))]/50"
                                            )}
                                            onClick={() => {
                                                if (onItemClick) onItemClick(item);
                                                toggleExpand(item.id);
                                            }}
                                        >
                                            {/* Expand Icon */}
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    toggleExpand(item.id);
                                                }}
                                                className="text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
                                            >
                                                {isExpanded ? (
                                                    <ChevronDown size={14} />
                                                ) : (
                                                    <ChevronRight size={14} />
                                                )}
                                            </button>

                                            {/* Status Icon */}
                                            {StatusIcon && (
                                                <StatusIcon
                                                    size={14}
                                                    className={clsx(
                                                        "flex-shrink-0",
                                                        item.status === "completed" || item.status === "resolved"
                                                            ? "text-emerald-500"
                                                            : item.status === "open" || item.status === "urgent"
                                                            ? "text-rose-500"
                                                            : "text-[hsl(var(--text-secondary))]"
                                                    )}
                                                />
                                            )}

                                            {/* Title & Description */}
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm font-semibold text-[hsl(var(--text-primary))] truncate">
                                                    {item.title}
                                                </p>
                                                {item.description && !isExpanded && (
                                                    <p className="text-xs text-[hsl(var(--text-secondary))] truncate mt-0.5">
                                                        {item.description}
                                                    </p>
                                                )}
                                            </div>

                                            {/* Priority Badge */}
                                            {item.priority && (
                                                <span
                                                    className={clsx(
                                                        "px-2 py-0.5 rounded-full text-[10px] font-bold uppercase",
                                                        PRIORITY_STYLES[item.priority] || PRIORITY_STYLES.medium
                                                    )}
                                                >
                                                    {item.priority}
                                                </span>
                                            )}

                                            {/* Tags */}
                                            {item.tags && item.tags.length > 0 && (
                                                <div className="hidden md:flex items-center gap-1">
                                                    {item.tags.slice(0, 2).map((tag) => (
                                                        <span
                                                            key={tag}
                                                            className="px-1.5 py-0.5 text-[9px] font-bold rounded bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))]"
                                                        >
                                                            {tag}
                                                        </span>
                                                    ))}
                                                    {item.tags.length > 2 && (
                                                        <span className="text-[9px] text-[hsl(var(--text-secondary))]">
                                                            +{item.tags.length - 2}
                                                        </span>
                                                    )}
                                                </div>
                                            )}

                                            {/* Assignee */}
                                            {item.assignee && (
                                                <div className="hidden sm:flex items-center gap-1.5 text-xs text-[hsl(var(--text-secondary))]">
                                                    <User size={12} />
                                                    <span className="truncate max-w-[100px]">{item.assignee}</span>
                                                </div>
                                            )}

                                            {/* Date */}
                                            {item.date && (
                                                <div className="hidden sm:flex items-center gap-1 text-xs text-[hsl(var(--text-secondary))]">
                                                    <Calendar size={12} />
                                                    <span>{item.date}</span>
                                                </div>
                                            )}

                                            {/* Delete */}
                                            {onDelete && (
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        onDelete(item);
                                                    }}
                                                    className="opacity-0 group-hover:opacity-100 text-[hsl(var(--text-secondary))] hover:text-rose-500 transition-opacity"
                                                >
                                                    <X size={14} />
                                                </button>
                                            )}
                                        </div>

                                        {/* Expanded Content */}
                                        <AnimatePresence>
                                            {isExpanded && item.description && (
                                                <motion.div
                                                    initial={{ height: 0, opacity: 0 }}
                                                    animate={{ height: "auto", opacity: 1 }}
                                                    exit={{ height: 0, opacity: 0 }}
                                                    className="overflow-hidden"
                                                >
                                                    <div className="px-8 pb-3 pt-1 text-xs text-[hsl(var(--text-secondary))] leading-relaxed">
                                                        {item.description}
                                                    </div>
                                                </motion.div>
                                            )}
                                        </AnimatePresence>
                                    </motion.div>
                                );
                            })}
                        </AnimatePresence>
                    </div>
                )}
            </div>
        </div>
    );
}
