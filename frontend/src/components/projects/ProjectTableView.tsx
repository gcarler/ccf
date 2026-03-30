"use client";

import React from 'react';
import { 
    CheckCircle2, 
    Circle, 
    Clock, 
    AlertCircle,
    User,
    Calendar,
    Flag,
    MoreHorizontal
} from 'lucide-react';
import clsx from 'clsx';
import type { ProjectTaskRecord } from '@/types/projects';

export default function ProjectTableView({ tasks }: { tasks: ProjectTaskRecord[] }) {
    return (
        <div className="bg-white dark:bg-white/5 rounded-[2.5rem] border border-slate-100 dark:border-white/10 overflow-hidden shadow-sm">
            <table className="w-full text-left border-collapse">
                <thead>
                    <tr className="bg-slate-50/50 dark:bg-black/20 border-b border-slate-100 dark:border-white/5">
                        <th className="px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Tarea</th>
                        <th className="px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Estado</th>
                        <th className="px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Responsable</th>
                        <th className="px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Entrega</th>
                        <th className="px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Prioridad</th>
                        <th className="px-6 py-4"></th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                    {tasks.map((task) => (
                        <tr key={task.id} className="hover:bg-slate-50 dark:hover:bg-white/5 transition-colors group">
                            <td className="px-6 py-4">
                                <div className="flex items-center gap-3">
                                    <div className={clsx(
                                        "size-5 rounded-full flex items-center justify-center border-2",
                                        task.status === 'done' ? "bg-green-500 border-green-500 text-white" : "border-slate-200 dark:border-white/10"
                                    )}>
                                        {task.status === 'done' && <CheckCircle2 size={12} />}
                                    </div>
                                    <span className="text-[13px] font-bold text-slate-700 dark:text-slate-200">{task.title}</span>
                                </div>
                            </td>
                            <td className="px-6 py-4">
                                <span className={clsx(
                                    "px-2.5 py-1 rounded-lg text-[9px] font-black uppercase tracking-widest border",
                                    task.status === 'done' ? "bg-emerald-50 border-emerald-100 text-emerald-600" : "bg-blue-50 border-blue-100 text-blue-600"
                                )}>
                                    {task.status || 'TODO'}
                                </span>
                            </td>
                            <td className="px-6 py-4">
                                <div className="flex items-center gap-2">
                                    <div className="size-6 rounded-lg bg-slate-100 dark:bg-white/10 flex items-center justify-center">
                                        <User size={12} className="text-slate-400" />
                                    </div>
                                    <span className="text-[11px] font-medium text-slate-500">Sin asignar</span>
                                </div>
                            </td>
                            <td className="px-6 py-4 text-[11px] font-bold text-slate-400">
                                {task.due_date ? new Date(task.due_date).toLocaleDateString() : '--'}
                            </td>
                            <td className="px-6 py-4">
                                <div className="flex items-center gap-1.5">
                                    <Flag size={12} className={clsx(
                                        task.priority === 'high' ? 'text-rose-500' : 'text-slate-300'
                                    )} />
                                    <span className="text-[10px] font-black uppercase text-slate-400">{task.priority || 'Normal'}</span>
                                </div>
                            </td>
                            <td className="px-6 py-4 text-right">
                                <button className="p-1.5 text-slate-300 hover:text-slate-600 dark:hover:text-white transition-colors">
                                    <MoreHorizontal size={16} />
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
