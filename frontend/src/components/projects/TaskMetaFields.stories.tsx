import type { Meta, StoryObj } from '@storybook/react-webpack5';
import TaskMetaFields from './TaskMetaFields';
import { getPriorityOption } from '@/lib/projects/constants';
import type { ProjectTaskRecord } from '@/types/projects';

/** Metadatos de la tarea en el panel de detalle: asignación, fecha, prioridad, nodo y etiquetas. */
const meta: Meta<typeof TaskMetaFields> = {
    title: 'Projects/TaskMetaFields',
    component: TaskMetaFields,
    parameters: { layout: 'centered' },
};

export default meta;
type Story = StoryObj<typeof TaskMetaFields>;

const noop = () => {};

const task: ProjectTaskRecord = {
    id: 't1',
    project_id: 'p1',
    title: 'Diseñar material del retiro',
    status: 'in_progress',
    priority: 'high',
    due_date: '2026-10-15',
    node: 'nutrition',
    assignee_id: 'user-1',
    labels: ['diseño', 'comunicaciones'],
};

export const Default: Story = {
    args: {
        task,
        labels: ['diseño', 'comunicaciones'],
        onLabelsChange: noop,
        onAssigneeChange: noop,
        onPriorityCycle: noop,
        onNodeCycle: noop,
        priority: getPriorityOption('high'),
        token: null,
    },
};

export const SinFechaNiNodo: Story = {
    args: {
        task: { ...task, due_date: null, node: null, priority: 'low' },
        labels: [],
        onLabelsChange: noop,
        onAssigneeChange: noop,
        onPriorityCycle: noop,
        onNodeCycle: noop,
        priority: getPriorityOption('low'),
        token: null,
    },
};
