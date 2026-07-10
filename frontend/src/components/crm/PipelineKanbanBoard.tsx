"use client";

import React, { useState } from 'react';
import { 
    DndContext, 
    closestCorners,
    PointerSensor,
    TouchSensor,
    KeyboardSensor,
    useSensor,
    useSensors,
    DragEndEvent,
    DragOverlay,
    DragStartEvent,
    defaultDropAnimationSideEffects
} from '@dnd-kit/core';
import { sortableKeyboardCoordinates, arrayMove } from '@dnd-kit/sortable';
import { DroppablePipelineColumn } from './DroppablePipelineColumn';
import { SortableLeadCard } from './SortableLeadCard';
import { PIPELINE_STAGES } from '@/app/plataforma/crm/pipeline/constants';

interface PipelineKanbanBoardProps {
    leads: any[];
    onLeadClick: (lead: any) => void;
    onDropLead: (leadId: string, stage: string, reorderPayload: { id: string, sort_order: number, etapa_actual_id: string }[]) => void;
    onNewLead: (stage?: string) => void;
    allowEditing?: boolean;
}

export function PipelineKanbanBoard({ leads, onLeadClick, onDropLead, onNewLead, allowEditing = true }: PipelineKanbanBoardProps) {
    const [activeLead, setActiveLead] = useState<any | null>(null);

    const sortedLeads = React.useMemo(() => {
        return [...leads].sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
    }, [leads]);

    const sensors = useSensors(
        useSensor(PointerSensor, {
            activationConstraint: {
                distance: 8,
            },
        }),
        useSensor(TouchSensor, {
            activationConstraint: {
                delay: 250,
                tolerance: 5,
            },
        }),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    const handleDragStart = (event: DragStartEvent) => {
        const { active } = event;
        const lead = leads.find(l => l.id.toString() === active.id.toString());
        setActiveLead(lead || null);
    };

    const handleDragEnd = (event: DragEndEvent) => {
        if (!allowEditing) {
            setActiveLead(null);
            return;
        }
        const { active, over } = event;
        
        setActiveLead(null);

        if (!over) return;

        const leadId = active.id as string;
        const overId = over.id as string;

        // Find target stage
        const overStage = PIPELINE_STAGES.find(s => s.value === overId)?.value;
        const overLead = leads.find(l => l.id.toString() === overId);
        const targetStage = overStage || overLead?.stage;

        if (!targetStage) return;

        const activeLead = leads.find(l => l.id.toString() === leadId);
        if (!activeLead) return;

        const sourceStage = activeLead.stage;

        const getStageLeads = (stageValue: string) => {
            return leads
                .filter(l => l.stage === stageValue)
                .sort((a, b) => {
                    const valA = a.sort_order ?? 0;
                    const valB = b.sort_order ?? 0;
                    if (valA !== valB) return valA - valB;
                    return leads.indexOf(a) - leads.indexOf(b);
                });
        };

        if (sourceStage === targetStage) {
            const stageLeads = getStageLeads(targetStage);
            const activeIndex = stageLeads.findIndex(l => l.id.toString() === leadId);
            const overIndex = stageLeads.findIndex(l => l.id.toString() === overId);

            let newStageLeads = [...stageLeads];
            if (activeIndex !== -1 && overIndex !== -1 && activeIndex !== overIndex) {
                newStageLeads = arrayMove(stageLeads, activeIndex, overIndex);
            }
            const reorderPayload = newStageLeads.map((l, index) => ({
                id: l.id.toString(),
                sort_order: index,
                etapa_actual_id: targetStage
            }));

            onDropLead(leadId, targetStage, reorderPayload);
        } else {
            const sourceLeads = getStageLeads(sourceStage);
            const targetLeads = getStageLeads(targetStage);

            const overIndex = targetLeads.findIndex(l => l.id.toString() === overId);

            const newSourceLeads = sourceLeads.filter(l => l.id.toString() !== leadId);
            const newTargetLeads = [...targetLeads];

            if (overIndex !== -1) {
                newTargetLeads.splice(overIndex, 0, { ...activeLead, stage: targetStage });
            } else {
                newTargetLeads.push({ ...activeLead, stage: targetStage });
            }

            const targetPayload = newTargetLeads.map((l, index) => ({
                id: l.id.toString(),
                sort_order: index,
                etapa_actual_id: targetStage
            }));

            const sourcePayload = newSourceLeads.map((l, index) => ({
                id: l.id.toString(),
                sort_order: index,
                etapa_actual_id: sourceStage
            }));

            const reorderPayload = [...targetPayload, ...sourcePayload];

            onDropLead(leadId, targetStage, reorderPayload);
        }
    };

    const handleDragCancel = () => {
        setActiveLead(null);
    };

    return (
        <DndContext
            sensors={sensors}
            collisionDetection={closestCorners}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
            onDragCancel={handleDragCancel}
        >
            <div className="flex h-full gap-3 p-4 overflow-x-auto bg-transparent items-start scrollbar-thin pb-12">
                {PIPELINE_STAGES.map((stage) => (
                    <DroppablePipelineColumn
                        key={stage.value}
                        stage={stage}
                        leads={sortedLeads.filter(l => l.stage === stage.value)}
                        onLeadClick={onLeadClick}
                        onNewLead={() => allowEditing ? onNewLead(stage.value) : undefined}
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
