import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { DndContext } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { SortableTaskCard } from './SortableTaskCard';
import type { ProjectTaskRecord } from '@/types/projects';

/** Tarjeta de tarea ordenable del tablero Kanban. Requiere contexto de dnd-kit. */
const meta: Meta<typeof SortableTaskCard> = {
    title: 'Projects/SortableTaskCard',
    component: SortableTaskCard,
    decorators: [
        (Story) => (
            <DndContext>
                <SortableContext items={[]} strategy={verticalListSortingStrategy}>
                    <div className="w-72">
                        <Story />
                    </div>
                </SortableContext>
            </DndContext>
        ),
    ],
    parameters: { layout: 'centered' },
};

export default meta;
type Story = StoryObj<typeof SortableTaskCard>;

const noop = () => {};

const baseTask: ProjectTaskRecord = {
    id: 'task-1',
    project_id: 'proj-1',
    title: 'Diseñar material del retiro',
    status: 'in_progress',
    priority: 'high',
    due_date: '2026-10-15',
    comments_count: 3,
    assignee_id: 'user-1',
};

export const Default: Story = {
    args: { task: baseTask, onOpen: noop },
};

export const Urgente: Story = {
    args: {
        task: { ...baseTask, id: 'task-2', title: 'Coordinar transporte para el campamento', priority: 'urgent' },
        onOpen: noop,
    },
};

export const SinFechaNiComentarios: Story = {
    args: {
        task: {
            ...baseTask,
            id: 'task-3',
            title: 'Revisar presupuesto anual',
            status: 'todo',
            priority: 'low',
            due_date: null,
            comments_count: 0,
            assignee_id: null,
        },
        onOpen: noop,
    },
};
