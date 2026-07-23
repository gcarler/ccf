"use client";

import React from 'react';
import { Ghost, Plus } from 'lucide-react';
import { motion } from 'framer-motion';
import { DSButton } from '@/design';

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
            <div aria-hidden="true" className="size-8 rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-primary))]">
                <Icon size={40} strokeWidth={1.5} />
            </div>
            
            <div className="space-y-2 max-w-xs">
                <h3 className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight">{title}</h3>
                <p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-medium">{description}</p>
            </div>

            {onAction && (
                <DSButton onClick={onAction} className="px-4 py-3 text-sm font-black rounded-lg shadow-lg shadow-primary hover:scale-[1.02] active:scale-[0.98]">
                    <Plus size={16} /> {actionLabel || 'Añadir Nuevo'}
                </DSButton>
            )}
        </motion.div>
    );
}
