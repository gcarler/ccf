"use client";

import React, { useState } from 'react';
import { 
    DndContext, 
    closestCorners,
    PointerSensor,
    useSensor,
    useSensors,
    DragEndEvent,
    DragOverlay,
    DragStartEvent,
    defaultDropAnimationSideEffects
} from '@dnd-kit/core';
import { DroppablePipelineColumn } from './DroppablePipelineColumn';
import { SortableLeadCard } from './SortableLeadCard';
import { PIPELINE_STAGES } from '@/app/plataforma/crm/pipeline/constants';

interface PipelineKanbanBoardProps {
    leads: any[];
    onLeadClick: (lead: any) => void;
    onDropLead: (leadId: string, stage: string) => void;
    onNewLead: (stage?: string) => void;
}

export function PipelineKanbanBoard({ leads, onLeadClick, onDropLead, onNewLead }: PipelineKanbanBoardProps) {
    const [activeLead, setActiveLead] = useState<any | null>(null);
    const [optimisticLeads, setOptimisticLeads] = useState<any[] | null>(null);

    const displayLeads = optimisticLeads || leads;

    const sensors = useSensors(
        useSensor(PointerSensor, {
            activationConstraint: {
                distance: 5,
            },
        })
    );

    const handleDragStart = (event: DragStartEvent) => {
        const { active } = event;
        const lead = leads.find(l => l.id.toString() === active.id.toString());
        setActiveLead(lead || null);
    };

    const handleDragEnd = (event: DragEndEvent) => {
        const { active, over } = event;
        
        setActiveLead(null);

        if (!over) return;

        const leadId = active.id as string;
        const overId = over.id as string;

        // Optimistic UI Update
        const targetStage = PIPELINE_STAGES.find(s => s.value === overId)?.value || 
                          leads.find(l => l.id.toString() === overId)?.stage;

        if (targetStage && targetStage !== activeLead?.stage) {
            const updatedLeads = leads.map(l => 
                l.id === leadId ? { ...l, stage: targetStage } : l
            );
            setOptimisticLeads(updatedLeads);
            onDropLead(leadId, targetStage);

            // Reset optimistic update after a short delay or when props update
            setTimeout(() => setOptimisticLeads(null), 1000);
        }
    };

    return (
        <DndContext
            sensors={sensors}
            collisionDetection={closestCorners}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
        >
            <div className="flex h-full gap-3 p-4 overflow-x-auto bg-transparent items-start scrollbar-thin pb-12">
                {PIPELINE_STAGES.map((stage) => (
                    <DroppablePipelineColumn
                        key={stage.value}
                        stage={stage}
                        leads={displayLeads.filter(l => l.stage === stage.value)}
                        onLeadClick={onLeadClick}
                        onNewLead={() => onNewLead(stage.value)}
                    />
                ))}
            </div>

            {/* Custom Drag Overlay for Ultra Premium Feel */}
            <DragOverlay dropAnimation={{
                sideEffects: defaultDropAnimationSideEffects({
                    styles: {
                        active: {
                            opacity: '0.4',
                        },
                    },
                }),
            }}>
                {activeLead ? (
                    <div className="rotate-2 scale-110 opacity-100 shadow-[0_32px_64px_-16px_rgba(0,0,0,0.3)] backdrop-blur-3xl ring-4 ring-blue-500/20 rounded-lg">
                        <SortableLeadCard 
                            lead={activeLead} 
                            stage={PIPELINE_STAGES.find(s => s.value === activeLead.stage)}
                            onClick={() => onLeadClick(activeLead)}
                            isDragging={true}
                        />
                    </div>
                ) : null}
            </DragOverlay>
        </DndContext>
    );
}
