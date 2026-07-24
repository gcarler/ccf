import type { Meta, StoryObj } from '@storybook/react-webpack5';
import TaskSupplySection from './TaskSupplySection';
import type { ProjectTaskRecord, TaskSupplyRecord } from '@/types/projects';

const mockTask: ProjectTaskRecord = {
    id: 'task-1',
    project_id: 'proj-1',
    title: 'Organizar evento',
    status: 'in_progress',
    priority: 'high',
    created_at: '2025-07-01T10:00:00Z',
};

const mockSupplies: TaskSupplyRecord[] = [
    { id: 's1', task_id: 'task-1', item_name: 'Megáfono', quantity: 2, status: 'ready' },
    { id: 's2', task_id: 'task-1', item_name: 'Sillas plegables', quantity: 50, status: 'pending' },
    { id: 's3', task_id: 'task-1', item_name: 'Proyector', quantity: 1, status: 'unavailable' },
];

const noop = () => {};

const meta: Meta<typeof TaskSupplySection> = {
    title: 'Projects/TaskSupplySection',
    component: TaskSupplySection,
    args: {
        task: mockTask,
        token: 'mock-token',
        onSuppliesChange: noop,
        onActivityCreated: noop,
    },
    parameters: { layout: 'centered' },
};

export default meta;
type Story = StoryObj<typeof TaskSupplySection>;

export const Empty: Story = {
    args: { supplies: [] },
};

export const WithSupplies: Story = {
    args: { supplies: mockSupplies },
};
