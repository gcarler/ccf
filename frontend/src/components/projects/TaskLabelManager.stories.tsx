import type { Meta, StoryObj } from '@storybook/react-webpack5';
import TaskLabelManager from './TaskLabelManager';
import type { ProjectTaskRecord } from '@/types/projects';

const mockTask: ProjectTaskRecord = {
    id: 'task-1',
    project_id: 'proj-1',
    title: 'Reunión pastoral',
    status: 'in_progress',
    priority: 'medium',
    created_at: '2025-07-01T10:00:00Z',
};

const noop = () => {};

const meta: Meta<typeof TaskLabelManager> = {
    title: 'Projects/TaskLabelManager',
    component: TaskLabelManager,
    args: {
        task: mockTask,
        onLabelsChange: noop,
        token: 'mock-token',
    },
    parameters: { layout: 'centered' },
};

export default meta;
type Story = StoryObj<typeof TaskLabelManager>;

export const NoLabels: Story = {
    args: { labels: [] },
};

export const WithLabels: Story = {
    args: { labels: ['Alabanza', 'Urgente', 'Pastoral', 'Diseño'] },
};
