"use client";

import React from 'react';
import { useDroppable } from '@dnd-kit/core';
import { 
    SortableContext, 
    verticalListSortingStrategy 
} from '@dnd-kit/sortable';
import { UserPlus, MoreHorizontal } from 'lucide-react';
import clsx from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';
import { SortableLeadCard } from './SortableLeadCard';

const containerVariants = {
    hidden: { opacity: 0 },
    show: {
        opacity: 1,
        transition: {
            staggerChildren: 0.08
        }
    }
};

const itemVariants = {
    hidden: { opacity: 0, y: 15, scale: 0.98 },
    show: { 
        opacity: 1, 
        y: 0, 
        scale: 1,
        transition: {
            type: "spring",
            stiffness: 300,
            damping: 25
        }
    }
};

interface DroppablePipelineColumnProps {
    stage: any;
    leads: any[];
    onLeadClick: (lead: any) => void;
    onNewLead: () => void;
    allowEditing?: boolean;
}

export function DroppablePipelineColumn({ stage, leads, onLeadClick, onNewLead, allowEditing = true }: DroppablePipelineColumnProps) {
    const { setNodeRef, isOver } = useDroppable({
        id: stage.id || stage.value,
    });

    return (
        <div
            className={clsx(
                "flex-shrink-0 w-80 flex flex-col h-full rounded-md transition-all duration-500 ease-in-out",
                isOver ? "bg-blue-500/10 scale-[1.02] shadow-2xl" : "bg-transparent"
            )}
        >
            {/* Column Header */}
            <div className="flex items-center justify-between px-4 py-1.5 mb-2 group/header">
                <div className="flex items-center gap-3">
                    <div className={clsx("size-5 rounded-full flex items-center justify-center bg-[hsl(var(--bg-primary))] dark:bg-black/20 shadow-sm border border-[hsl(var(--border))] dark:border-white/10")}>
                        <div className={clsx("size-1.5 rounded-full animate-pulse", stage.dot || stage.color)} />
                    </div>
                    <div className="flex flex-col">
                        <h3 className="text-[10px] font-bold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] uppercase tracking-wide leading-tight">
                            {stage.label}
                        </h3>
                        <span className="text-[9px] font-bold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] uppercase">
                            {leads.length} {leads.length === 1 ? 'Prospecto' : 'Prospectos'}
                        </span>
                    </div>
                </div>
                
                <div className="flex items-center gap-1 opacity-0 group-hover/header:opacity-100 transition-all">
                    {allowEditing && (
                        <button
                            onClick={onNewLead}
                            className="size-7 rounded-md bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 flex items-center justify-center text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:border-blue-500/30 hover:shadow-lg transition-all"
                            aria-label="Agregar"
                        >
                            <UserPlus size={12} />
                        </button>
                    )}
                    <button className="size-7 rounded-md bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 flex items-center justify-center text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] transition-all" aria-label="Más opciones">
                        <MoreHorizontal size={12} />
                    </button>
                </div>
            </div>

            {/* Drop Zone & List Container */}
            <div 
                ref={setNodeRef}
                className={clsx(
                    "flex-1 flex flex-col p-3 rounded-md transition-all duration-300",
                    isOver ? "bg-white/40 dark:bg-white/5 backdrop-blur-md ring-2 ring-blue-500/20" : "bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]"
                )}
            >
                <motion.div 
                    variants={containerVariants}
                    initial="hidden"
                    animate="show"
                    className="flex flex-col gap-1 overflow-y-auto scrollbar-none pb-4"
                >
                    <SortableContext
                        id={stage.id || stage.value}
                        items={leads.map(l => l.id.toString())}
                        strategy={verticalListSortingStrategy}
                    >
                        <AnimatePresence mode='popLayout'>
                            {leads.map((lead) => (
                                <motion.div 
                                    key={lead.id} 
                                    variants={itemVariants}
                                    layout
                                >
                                    <SortableLeadCard
                                        lead={lead}
                                        stage={stage}
                                        onClick={() => onLeadClick(lead)}
                                    />
                                </motion.div>
                            ))}
                        </AnimatePresence>
                    </SortableContext>

                    {/* Empty State */}
                    {leads.length === 0 && (
                        <div className={clsx(
                            "flex flex-col items-center justify-center gap-3 py-1.5 px-4 rounded-lg border-2 border-dashed transition-all duration-500",
                            isOver 
                                ? "border-blue-500/50 bg-blue-500/5 scale-[0.98]" 
                                : "border-[hsl(var(--border))] dark:border-white/5"
                        )}>
                            <div className="p-4 rounded-lg bg-[hsl(var(--bg-primary))] dark:bg-white/5 shadow-sm border border-[hsl(var(--border))] dark:border-white/5">
                                {stage.emptyIcon ? <stage.emptyIcon size={24} className="text-[hsl(var(--text-secondary))]" /> : <UserPlus size={24} className="text-[hsl(var(--text-secondary))]" />}
                            </div>
                            <div className="text-center">
                                <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] uppercase tracking-wide leading-normal">
                                    {isOver ? '¡Suelta para asignar!' : `Sin ${stage.label.toLowerCase()}`}
                                </p>
                                {allowEditing && !isOver && (
                                    <button 
                                        onClick={onNewLead}
                                        className="mt-3 text-[10px] font-bold text-[hsl(var(--primary))] hover:text-[hsl(var(--primary))] underline"
                                    >
                                        Registrar uno ahora
                                    </button>
                                )}
                            </div>
                        </div>
                    )}
                </motion.div>

                {/* Footer Add Button */}
                {allowEditing && (
                    <button
                        onClick={onNewLead}
                        className="w-full mt-auto py-1.5 rounded-lg border border-dashed border-[hsl(var(--border))] dark:border-white/10 text-[10px] font-bold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:border-blue-500/30 hover:bg-[hsl(var(--bg-primary))] dark:hover:bg-white/5 transition-all flex items-center justify-center gap-2 group"
                    >
                        <div className="size-5 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center group-hover:bg-blue-50 transition-colors">
                            <UserPlus size={10} />
                        </div>
                        AGREGAR PROSPECTO
                    </button>
                )}
            </div>
        </div>
    );
}
