import type { Meta, StoryObj } from '@storybook/react-webpack5';
import TaskCommentSection from './TaskCommentSection';
import type { ProjectTaskRecord } from '@/types/projects';

const mockTask: ProjectTaskRecord = {
    id: 'task-1',
    project_id: 'proj-1',
    title: 'Diseñar landing page',
    status: 'in_progress',
    priority: 'high',
    created_at: '2025-07-01T10:00:00Z',
};

const noop = () => {};

const meta: Meta<typeof TaskCommentSection> = {
    title: 'Projects/TaskCommentSection',
    component: TaskCommentSection,
    args: {
        task: mockTask,
        token: null,
        onDeleteComment: noop,
        onActivityCreated: noop,
    },
    parameters: { layout: 'centered' },
};

export default meta;
type Story = StoryObj<typeof TaskCommentSection>;

export const Default: Story = {
    args: { token: 'mock-token' },
};
