import type { Meta, StoryObj } from '@storybook/react-webpack5';
import TaskActivitySection from './TaskActivitySection';
import type { Activity } from './TaskActivitySection';

const noop = () => {};

const meta: Meta<typeof TaskActivitySection> = {
    title: 'Projects/TaskActivitySection',
    component: TaskActivitySection,
    args: {
        newActivityTitle: '',
        onNewActivityTitleChange: noop,
        onAddTopLevel: noop,
        onToggle: noop,
        onAddChild: noop,
        onUpdateTitle: noop,
        onDelete: noop,
    },
    parameters: { layout: 'centered' },
};

export default meta;
type Story = StoryObj<typeof TaskActivitySection>;

export const Empty: Story = {
    args: { activities: [] },
};

const flatActivities: Activity[] = [
    { id: 'a1', title: 'Preparar materiales', completed: false },
    { id: 'a2', title: 'Enviar invitaciones', completed: true, assignee: { name: 'Ana' } },
    { id: 'a3', title: 'Configurar sonido', completed: false, assignee: { name: 'Luis', color: '#22c55e' } },
];

export const WithActivities: Story = {
    args: { activities: flatActivities },
};

const nestedActivities: Activity[] = [
    {
        id: 'a1',
        title: 'Preparar escenario',
        completed: false,
        assignee: { name: 'Carlos', color: '#8b5cf6' },
        children: [
            { id: 'a1-1', title: 'Montar tarima', completed: true },
            { id: 'a1-2', title: 'Instalar luces', completed: false, assignee: { name: 'Ana' } },
            {
                id: 'a1-3',
                title: 'Configurar proyector',
                completed: false,
                children: [
                    { id: 'a1-3-1', title: 'Probar señal HDMI', completed: false },
                    { id: 'a1-3-2', title: 'Ajustar imagen', completed: false },
                ],
            },
        ],
    },
    { id: 'a2', title: 'Coordinar equipo de alabanza', completed: false },
];

export const WithNestedActivities: Story = {
    args: { activities: nestedActivities },
};
