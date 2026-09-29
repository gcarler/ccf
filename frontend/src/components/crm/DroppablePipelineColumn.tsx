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
                isOver ? "bg-[hsl(var(--info))]/10 scale-[1.02] shadow-2xl" : "bg-transparent"
            )}
        >
            {/* Column Header */}
            <div className="flex items-center justify-between px-4 py-1.5 mb-2 group/header">
                <div className="flex items-center gap-3">
                    <div className={clsx("size-5 rounded-full flex items-center justify-center bg-[hsl(var(--surface-1))] shadow-sm border border-[hsl(var(--border))]")}>
                        <div className={clsx("size-1.5 rounded-full animate-pulse", stage.dot || stage.color)} />
                    </div>
                    <div className="flex flex-col">
                        <h3 className="text-2xs font-bold text-[hsl(var(--muted-foreground))] uppercase tracking-wide leading-tight">
                            {stage.label}
                        </h3>
                        <span className="text-2xs font-bold text-[hsl(var(--muted-foreground))] uppercase">
                            {leads.length} {leads.length === 1 ? 'Prospecto' : 'Prospectos'}
                        </span>
                    </div>
                </div>

                <div className="flex items-center gap-1 opacity-0 group-hover/header:opacity-100 transition-all">
                    {allowEditing && (
                        <button
                            onClick={onNewLead}
                            className="size-7 rounded-md bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] flex items-center justify-center text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--primary))] hover:border-[hsl(var(--primary)/0.3)] hover:shadow-lg transition-all"
                            aria-label="Agregar"
                        >
                            <UserPlus size={12} />
                        </button>
                    )}
                    <button className="size-7 rounded-md bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] flex items-center justify-center text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] transition-all" aria-label="Más opciones">
                        <MoreHorizontal size={12} />
                    </button>
                </div>
            </div>

            {/* Drop Zone & List Container */}
            <div
                ref={setNodeRef}
                className={clsx(
                    "flex-1 flex flex-col p-3 rounded-md transition-all duration-300",
                    isOver ? "bg-[hsl(var(--surface-2))] ring-2 ring-[hsl(var(--primary)/0.2)]" : "bg-[hsl(var(--surface-1))]"
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
                                ? "border-[hsl(var(--primary)/0.5)] bg-[hsl(var(--primary)/0.05)] scale-[0.98]"
                                : "border-[hsl(var(--border))]"
                        )}>
                            <div className="p-4 rounded-lg bg-[hsl(var(--surface-1))] shadow-sm border border-[hsl(var(--border))]">
                                {stage.emptyIcon ? <stage.emptyIcon size={24} className="text-[hsl(var(--muted-foreground))]" /> : <UserPlus size={24} className="text-[hsl(var(--muted-foreground))]" />}
                            </div>
                            <div className="text-center">
                                <p className="text-2xs font-bold text-[hsl(var(--muted-foreground))] uppercase tracking-wide leading-normal">
                                    {isOver ? '¡Suelta para asignar!' : `Sin ${stage.label.toLowerCase()}`}
                                </p>
                                {allowEditing && !isOver && (
                                    <button
                                        onClick={onNewLead}
                                        className="mt-3 text-2xs font-bold text-[hsl(var(--primary))] hover:text-[hsl(var(--primary))] underline"
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
                        className="w-full mt-auto py-1.5 rounded-lg border border-dashed border-[hsl(var(--border))] text-2xs font-bold text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--primary))] hover:border-[hsl(var(--primary)/0.3)] hover:bg-[hsl(var(--surface-2))] transition-all flex items-center justify-center gap-2 group"
                    >
                        <div className="size-5 rounded-lg bg-[hsl(var(--surface-2))] flex items-center justify-center group-hover:bg-[hsl(var(--primary)/0.1)] transition-colors">
                            <UserPlus size={10} />
                        </div>
                        AGREGAR PROSPECTO
                    </button>
                )}
            </div>
        </div>
    );
}
