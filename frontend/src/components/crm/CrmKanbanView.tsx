"use client";

import React from 'react';
import { DndContext, DragEndEvent, PointerSensor, closestCorners, useSensor, useSensors } from '@dnd-kit/core';
import { PersonaPipelineColumn } from '@/components/crm/PersonaPipeline';

interface PipelineColumn {
    id: string;
    title: string;
    color: string;
    personas: any[];
}

interface CrmKanbanViewProps {
    columns: PipelineColumn[];
    onDragEnd: (event: DragEndEvent) => void;
    onOpenPersona: (persona: any) => void;
}

export default function CrmKanbanView({ columns, onDragEnd, onOpenPersona }: CrmKanbanViewProps) {
    const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

    return (
        <DndContext sensors={sensors} collisionDetection={closestCorners} onDragEnd={onDragEnd}>
            <div className="flex h-full gap-4 p-4 overflow-x-auto bg-transparent items-start scrollbar-thin">
                {columns.map((col) => (
                    <PersonaPipelineColumn key={col.id} {...col} onOpenPersona={onOpenPersona} />
                ))}
            </div>
        </DndContext>
    );
}
