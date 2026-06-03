"use client";

import React from 'react';
import { Ghost, Plus } from 'lucide-react';
import { motion } from 'framer-motion';

interface EmptyStateProps {
    title: string;
    description: string;
    icon?: any;
    onAction?: () => void;
    actionLabel?: string;
}

export default function EmptyState({
    title,
    description,
    icon: Icon = Ghost,
    onAction,
    actionLabel
}: EmptyStateProps) {
    return (
        <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center justify-center p-4 text-center space-y-3"
        >
            <div className="size-8 rounded-lg bg-slate-50 dark:bg-white/5 flex items-center justify-center text-slate-300 dark:text-slate-700">
                <Icon size={40} strokeWidth={1.5} />
            </div>
            
            <div className="space-y-2 max-w-xs">
                <h3 className="text-xl font-bold text-slate-800 dark:text-white tracking-tight">{title}</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">{description}</p>
            </div>

            {onAction && (
                <button 
                    onClick={onAction}
                    className="flex items-center gap-2 px-3 py-3 bg-[hsl(var(--primary))] text-white rounded-lg font-black text-xs uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:scale-[1.02] active:scale-[0.98] transition-all"
                >
                    <Plus size={16} /> {actionLabel || 'Añadir Nuevo'}
                </button>
            )}
        </motion.div>
    );
}
