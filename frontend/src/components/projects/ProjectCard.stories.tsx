import type { Meta, StoryObj } from '@storybook/react-webpack5';
import ProjectCard from './ProjectCard';
import type { ProjectRecord } from '@/types/projects';

const mockProject: ProjectRecord = {
    id: 'proj-1',
    title: 'Campamento Juventud 2025',
    description: 'Organización del campamento anual para jóvenes del grupo pastoral.',
    status: 'active',
    color: '#2563eb',
    owner_id: 'user-1',
    created_at: '2025-06-15T10:00:00Z',
    tasks: [
        { id: 't1', project_id: 'proj-1', title: 'Reservar venue', status: 'completed', priority: 'high', created_at: '2025-06-15T10:00:00Z' },
        { id: 't2', project_id: 'proj-1', title: 'Diseñar flyers', status: 'completed', priority: 'medium', created_at: '2025-06-16T10:00:00Z' },
        { id: 't3', project_id: 'proj-1', title: 'Coordinar transporte', status: 'in_progress', priority: 'high', created_at: '2025-06-17T10:00:00Z' },
        { id: 't4', project_id: 'proj-1', title: 'Preparar alimentos', status: 'todo', priority: 'medium', created_at: '2025-06-18T10:00:00Z' },
    ],
};

const noop = () => {};

const meta: Meta<typeof ProjectCard> = {
    title: 'Projects/ProjectCard',
    component: ProjectCard,
    args: {
        project: mockProject,
        index: 0,
        onUpdate: noop,
        onDelete: noop,
    },
    parameters: { layout: 'centered' },
};

export default meta;
type Story = StoryObj<typeof ProjectCard>;

export const Default: Story = {};

export const WithColor: Story = {
    args: {
        project: {
            ...mockProject,
            color: '#8b5cf6',
            title: 'Retiro Pastoral',
            description: 'Planificación del retiro para líderes ministeriales.',
        },
    },
};

export const Loading: Story = {
    args: {
        project: {
            ...mockProject,
            title: '',
            description: null,
            tasks: [],
        },
    },
};
