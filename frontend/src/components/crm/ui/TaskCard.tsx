'use client';

import React from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import { UserCircle, Calendar, CheckCircle2 } from 'lucide-react';
import { ConsolidationTask } from '@/types/crm';

const PRIORITY_STYLES: Record<string, string> = {
  high: 'bg-rose-50 text-rose-600 dark:bg-rose-900/20',
  medium: 'bg-amber-50 text-amber-600 dark:bg-amber-900/20',
  low: 'bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:bg-white/5',
};

interface TaskCardProps {
  task: ConsolidationTask;
  onStatusChange: (id: string, status: string) => void;
  allowEditing?: boolean;
}

export default function TaskCard({ task, onStatusChange, allowEditing = true }: TaskCardProps) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      whileHover={{ y: -2 }}
      onClick={() => window.location.href = `/plataforma/crm/tasks/${task.id}`}
      className="p-4 bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 shadow-sm hover:shadow-md transition-all cursor-pointer group"
    >
      <div className="flex items-start gap-3">
        {allowEditing ? (
          <button
            onClick={e => { e.stopPropagation(); onStatusChange(task.id, task.status === 'done' ? 'pending' : 'done'); }}
            className={clsx(
              "mt-0.5 size-5 rounded-full border-2 flex-shrink-0 transition-all",
              task.status === 'done'
                ? 'bg-emerald-500 border-emerald-500 text-white flex items-center justify-center'
                : 'border-[hsl(var(--border))] dark:border-white/20 group-hover:border-blue-400'
            )}
          >
            {task.status === 'done' && <CheckCircle2 size={12} strokeWidth={3} />}
          </button>
        ) : (
          <div
            className={clsx(
              "mt-0.5 size-5 rounded-full border-2 flex-shrink-0",
              task.status === 'done'
                ? 'bg-emerald-500 border-emerald-500'
                : 'border-[hsl(var(--border))] dark:border-white/20'
            )}
          />
        )}
        <div className="flex-1 min-w-0 space-y-2">
          <p className={clsx("text-xs font-bold leading-tight", task.status === 'done' && "line-through text-[hsl(var(--text-secondary))]")}>
            {task.title}
          </p>
          {task.persona_name && (
            <div className="flex items-center gap-1.5 text-[10px] text-[hsl(var(--text-secondary))] font-bold">
              <UserCircle size={11} /> {task.persona_name}
            </div>
          )}
          <div className="flex items-center gap-2">
            <span className={clsx("px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wide", PRIORITY_STYLES[task.priority])}>
              {task.priority}
            </span>
            <span className="text-[9px] font-bold text-[hsl(var(--text-secondary))] uppercase">{task.category}</span>
            {task.due_date && (
              <span className="flex items-center gap-0.5 text-[9px] font-bold text-[hsl(var(--text-secondary))]">
                <Calendar size={9} /> {new Date(task.due_date).toLocaleDateString()}
              </span>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
