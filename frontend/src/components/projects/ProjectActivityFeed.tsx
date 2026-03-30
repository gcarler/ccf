"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { 
    Plus, 
    RefreshCcw, 
    MessageSquare, 
    CheckCircle2, 
    Clock,
    User,
    ArrowRight
} from 'lucide-react';
import clsx from 'clsx';
import type { ProjectActivityLog } from '@/types/projects';

interface Props {
    activities: ProjectActivityLog[];
}

export default function ProjectActivityFeed({ activities }: Props) {
    const sorted = [...activities].sort((a, b) => 
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] border-l border-slate-100 dark:border-white/5 w-80 shrink-0 overflow-hidden font-display">
            <header className="p-6 border-b border-slate-100 dark:border-white/5 flex items-center justify-between bg-slate-50/50 dark:bg-white/5">
                <div>
                    <h3 className="text-[11px] font-black uppercase tracking-[0.25em] text-slate-400">Actividad Reciente</h3>
                    <p className="text-[9px] font-bold text-blue-600 uppercase mt-1">Pulso del Equipo</p>
                </div>
                <div className="size-8 rounded-xl bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center text-blue-600">
                    <Clock size={14} />
                </div>
            </header>

            <div className="flex-1 overflow-y-auto scrollbar-hide p-6 space-y-8 relative">
                {/* Línea de conexión temporal */}
                <div className="absolute left-[2.25rem] top-8 bottom-8 w-[1px] bg-slate-100 dark:bg-white/5" />

                {sorted.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-40 text-center space-y-3 opacity-40">
                        <Clock size={24} />
                        <p className="text-[10px] font-black uppercase tracking-widest">Sin actividad aún</p>
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
                                "size-9 rounded-xl flex items-center justify-center z-10 shadow-sm transition-transform group-hover:scale-110",
                                getIconBg(log.action_type)
                            )}>
                                {getIcon(log.action_type)}
                            </div>
                            
                            <div className="flex-1 min-w-0 space-y-1">
                                <div className="flex items-center justify-between gap-2">
                                    <span className="text-[11px] font-black text-slate-900 dark:text-white truncate">
                                        {log.user_name || "Sistema"}
                                    </span>
                                    <span className="text-[9px] font-bold text-slate-400 whitespace-nowrap">
                                        {formatRelative(log.created_at)}
                                    </span>
                                </div>
                                <p className="text-[12px] font-medium text-slate-500 dark:text-slate-400 leading-snug">
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
        case 'task_created': return <Plus size={14} className="text-blue-600" />;
        case 'status_changed': return <RefreshCcw size={14} className="text-amber-600" />;
        case 'comment_added': return <MessageSquare size={14} className="text-indigo-600" />;
        default: return <ArrowRight size={14} className="text-slate-600" />;
    }
}

function getIconBg(type: string) {
    switch (type) {
        case 'project_created': return "bg-emerald-100 dark:bg-emerald-900/20";
        case 'task_created': return "bg-blue-100 dark:bg-blue-900/20";
        case 'status_changed': return "bg-amber-100 dark:bg-amber-900/20";
        case 'comment_added': return "bg-indigo-100 dark:bg-indigo-900/20";
        default: return "bg-slate-100 dark:bg-white/5";
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
