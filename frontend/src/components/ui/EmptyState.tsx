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
            className="flex flex-col items-center justify-center p-12 text-center space-y-6"
        >
            <div className="size-20 rounded-[2.5rem] bg-slate-50 dark:bg-white/5 flex items-center justify-center text-slate-300 dark:text-slate-700">
                <Icon size={40} strokeWidth={1.5} />
            </div>
            
            <div className="space-y-2 max-w-xs">
                <h3 className="text-xl font-black text-slate-800 dark:text-white tracking-tight">{title}</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">{description}</p>
            </div>

            {onAction && (
                <button 
                    onClick={onAction}
                    className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-2xl font-black text-xs uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:scale-[1.02] active:scale-[0.98] transition-all"
                >
                    <Plus size={16} /> {actionLabel || 'Añadir Nuevo'}
                </button>
            )}
        </motion.div>
    );
}
