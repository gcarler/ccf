import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { DndContext } from '@dnd-kit/core';
import { KanbanColumn } from './KanbanColumn';
import type { ProjectTaskRecord } from '@/types/projects';

/** Columna del tablero Kanban con quick-add y zona de drop. */
const meta: Meta<typeof KanbanColumn> = {
    title: 'Projects/KanbanColumn',
    component: KanbanColumn,
    decorators: [
        (Story) => (
            <DndContext>
                <div className="h-[480px] w-72 flex">
                    <Story />
                </div>
            </DndContext>
        ),
    ],
    parameters: { layout: 'centered' },
};

export default meta;
type Story = StoryObj<typeof KanbanColumn>;

const noop = () => {};

const tasks: ProjectTaskRecord[] = [
    { id: 't1', project_id: 'p1', title: 'Reservar venue del campamento', status: 'todo', priority: 'high', due_date: '2026-10-12' },
    { id: 't2', project_id: 'p1', title: 'Diseñar flyers de promoción', status: 'todo', priority: 'medium' },
    { id: 't3', project_id: 'p1', title: 'Confirmar cocineros voluntarios', status: 'todo', priority: 'low', comments_count: 2 },
];

export const ConTareas: Story = {
    args: {
        id: 'todo',
        name: 'Por Hacer',
        color: '#3b82f6',
        tasks,
        onOpenTask: noop,
        onAddTask: noop,
    },
};

export const ColumnaVacia: Story = {
    args: {
        id: 'review',
        name: 'En Revisión',
        color: '#f59e0b',
        tasks: [],
        onOpenTask: noop,
        onAddTask: noop,
    },
};
