"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { 
    Plus, 
    RefreshCcw, 
    MessageSquare, 
    Clock,
    ArrowRight
} from 'lucide-react';
import clsx from 'clsx';
import type { ProjectActivityItem } from '@/types/projects';

interface Props {
    activities: ProjectActivityItem[];
}

export default function ProjectActivityFeed({ activities }: Props) {
    const sorted = [...activities].sort((a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] overflow-hidden font-display">
            <header className="p-3 border-b border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-between bg-[hsl(var(--surface-1))]/50 dark:bg-white/5">
                <div>
                    <h3 className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Actividad Reciente</h3>
                    <p className="text-[9px] font-medium text-[hsl(var(--primary))] uppercase mt-0.5">Pulso del Equipo</p>
                </div>
                <div className="size-7 rounded-md bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center text-[hsl(var(--primary))]">
                    <Clock size={12} />
                </div>
            </header>

            <div className="flex-1 overflow-y-auto scrollbar-hide p-3 space-y-4 relative">
                {/* Línea de conexión temporal */}
                <div className="absolute left-[2.25rem] top-8 bottom-8 w-[1px] bg-[hsl(var(--surface-2))] dark:bg-white/5" />

                {sorted.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-40 text-center space-y-3 opacity-40">
                        <Clock size={24} />
                        <p className="text-[10px] font-semibold uppercase tracking-wide">Sin actividad aún</p>
                    </div>
                ) : (
                    sorted.map((log, idx) => (
                        <motion.div
                            key={log.id}
                            initial={{ opacity: 0, x: 10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: idx * 0.05 }}
                            className="relative flex gap-4 group"
                        >
                            <div className={clsx(
                                "size-7 rounded-md flex items-center justify-center z-10 shadow-sm transition-transform group-hover:scale-110",
                                getIconBg(log.kind)
                            )}>
                                {getIcon(log.kind)}
                            </div>

                            <div className="flex-1 min-w-0 space-y-0.5">
                                <div className="flex items-center justify-between gap-2">
                                    <span className="text-[11px] font-bold text-[hsl(var(--text-primary))] dark:text-white truncate">
                                        {log.task_title || log.project_title || 'Sistema'}
                                    </span>
                                    <span className="text-[9px] font-medium text-[hsl(var(--text-secondary))] whitespace-nowrap">
                                        {formatRelative(log.created_at)}
                                    </span>
                                </div>
                                <p className="text-[12px] font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] leading-snug">
                                    {log.description}
                                </p>
                            </div>
                        </motion.div>
                    ))
                )}
            </div>
        </div>
    );
}

function getIcon(type: string) {
    switch (type) {
        case 'project_created': return <Plus size={14} className="text-emerald-600" />;
        case 'task_created': return <Plus size={14} className="text-[hsl(var(--primary))]" />;
        case 'status_changed': return <RefreshCcw size={14} className="text-amber-600" />;
        case 'comment_added': return <MessageSquare size={14} className="text-[hsl(var(--primary))]" />;
        default: return <ArrowRight size={14} className="text-[hsl(var(--text-secondary))]" />;
    }
}

function getIconBg(type: string) {
    switch (type) {
        case 'project_created': return "bg-emerald-100 dark:bg-emerald-900/20";
        case 'task_created': return "bg-blue-100 dark:bg-blue-900/20";
        case 'status_changed': return "bg-amber-100 dark:bg-amber-900/20";
        case 'comment_added': return "bg-blue-100 dark:bg-blue-900/20";
        default: return "bg-[hsl(var(--surface-2))] dark:bg-white/5";
    }
}

function formatRelative(date: string) {
    const now = new Date();
    const then = new Date(date);
    const diff = (now.getTime() - then.getTime()) / 1000;
    
    if (diff < 60) return 'Ahora';
    if (diff < 3600) return `${Math.floor(diff / 60)}m`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
    return then.toLocaleDateString(undefined, { day: '2-digit', month: 'short' });
}
