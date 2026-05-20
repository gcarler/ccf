"use client";

import React from 'react';
import { DndContext, DragEndEvent, PointerSensor, closestCorners, useSensor, useSensors } from '@dnd-kit/core';
import { MemberPipelineColumn } from '@/components/crm/MemberPipeline';

interface PipelineColumn {
    id: string;
    title: string;
    color: string;
    members: any[];
}

interface CrmKanbanViewProps {
    columns: PipelineColumn[];
    onDragEnd: (event: DragEndEvent) => void;
    onOpenMember: (member: any) => void;
}

export default function CrmKanbanView({ columns, onDragEnd, onOpenMember }: CrmKanbanViewProps) {
    const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

    return (
        <DndContext sensors={sensors} collisionDetection={closestCorners} onDragEnd={onDragEnd}>
            <div className="flex h-full gap-4 p-4 overflow-x-auto bg-transparent items-start scrollbar-thin">
                {columns.map((col) => (
                    <MemberPipelineColumn key={col.id} {...col} onOpenMember={onOpenMember} />
                ))}
            </div>
        </DndContext>
    );
}
