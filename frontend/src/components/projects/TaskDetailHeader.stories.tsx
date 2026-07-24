import type { Meta, StoryObj } from '@storybook/react-webpack5';
import TaskDetailHeader from './TaskDetailHeader';
import type { ProjectTaskRecord } from '@/types/projects';

const mockTask: ProjectTaskRecord = {
    id: 'task-1',
    project_id: 'proj-1',
    title: 'Diseñar landing page',
    description: '',
    status: 'todo',
    priority: 'medium',
    assignee_id: 'user-1',
    created_at: '2025-07-01T10:00:00Z',
};

const noop = () => {};

const meta: Meta<typeof TaskDetailHeader> = {
    title: 'Projects/TaskDetailHeader',
    component: TaskDetailHeader,
    args: {
        task: mockTask,
        projectTitle: 'Proyecto Campamento',
        title: mockTask.title,
        saving: false,
        uploading: false,
        starred: false,
        error: null,
        onClose: noop,
        onTitleChange: noop,
        onSave: noop,
        onStatusCycle: noop,
        onFileClick: noop,
        onStarToggle: noop,
        onExpandToggle: noop,
        onDeleteTask: noop,
        onVerRutaClick: noop,
    },
    parameters: { layout: 'centered' },
};

export default meta;
type Story = StoryObj<typeof TaskDetailHeader>;

export const Default: Story = {};

export const Saving: Story = {
    args: { saving: true },
};

export const WithError: Story = {
    args: { error: 'No se pudo guardar los cambios' },
};
