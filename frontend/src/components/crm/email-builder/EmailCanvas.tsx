/** EmailCanvas — canvas del editor con DnD. */
'use client';
import { useCallback, useState } from 'react';
import { DndContext, closestCenter, PointerSensor, useSensor, useSensors, type DragEndEvent } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { Plus } from 'lucide-react';
import type { BlockType } from './blockTypes';
import BlockWrapper from './BlockWrapper';
import BlockRenderer from './BlockRenderer';
import type { UseEmailBuilderReturn } from './useEmailBuilder';

interface Props { builder: UseEmailBuilderReturn; }

export default function EmailCanvas({ builder }: Props) {
  const { blocks, selectedId, selectBlock, addBlock, removeBlock, moveBlock, duplicateBlock, updateBlockProps } = builder;
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const { active, over } = event;
    if (!over) return;
    const activeId = String(active.id);
    const overId = String(over.id);
    if (String(active.id).startsWith('palette-')) {
      const blockType = active.data.current?.blockType as BlockType;
      if (blockType) { const overIndex = blocks.findIndex(b => b.id === overId); addBlock(blockType, overIndex >= 0 ? overIndex : undefined); }
      return;
    }
    if (activeId !== overId) moveBlock(activeId, overId);
  }, [blocks, addBlock, moveBlock]);

  return (
    <div className="flex-1 overflow-y-auto bg-[hsl(var(--surface-1))] dark:bg-white/[0.02] p-6" onClick={() => selectBlock(null)}>
      <div className="max-w-[600px] mx-auto">
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={blocks.map(b => b.id)} strategy={verticalListSortingStrategy}>
            <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden min-h-[400px]">
              {blocks.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-20 text-gray-400" onClick={(e) => e.stopPropagation()}>
                  <Plus size={32} className="mb-3 opacity-50" /><p className="text-sm font-medium">Arrastra bloques aqui</p>
                </div>
              ) : blocks.map(block => (
                <BlockWrapper key={block.id} block={block} isSelected={selectedId === block.id} onSelect={() => selectBlock(block.id)} onRemove={() => removeBlock(block.id)} onDuplicate={() => duplicateBlock(block.id)}>
                  <BlockRenderer block={block} isEditing={selectedId === block.id} onUpdate={(props) => updateBlockProps(block.id, props)} />
                </BlockWrapper>
              ))}
            </div>
          </SortableContext>
        </DndContext>
      </div>
    </div>
  );
}
