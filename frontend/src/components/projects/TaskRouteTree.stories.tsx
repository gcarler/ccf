import type { Meta, StoryObj } from '@storybook/react-webpack5';
import TaskRouteTree, { type RouteNode } from './TaskRouteTree';

/** Árbol de navegación jerárquico (workspace → portafolio → proyecto → tarea). */
const meta: Meta<typeof TaskRouteTree> = {
    title: 'Projects/TaskRouteTree',
    component: TaskRouteTree,
    parameters: { layout: 'centered' },
};

export default meta;
type Story = StoryObj<typeof TaskRouteTree>;

const tree: RouteNode[] = [
    {
        id: 'workspace',
        label: 'Workspace Proyectos',
        type: 'workspace',
        href: '/plataforma/projects',
        children: [
            {
                id: 'portfolio',
                label: 'Portafolio Ministerial',
                type: 'portfolio',
                children: [
                    {
                        id: 'proj-1',
                        label: 'Campamento Juventud 2026',
                        type: 'project',
                        href: '/plataforma/projects/proj-1',
                        children: [
                            { id: 't1', label: 'Reservar venue', type: 'task', active: true },
                            { id: 't2', label: 'Diseñar flyers', type: 'task' },
                            { id: 't3', label: 'Coordinar transporte', type: 'task' },
                        ],
                    },
                    {
                        id: 'proj-2',
                        label: 'Escuela de Liderazgo',
                        type: 'project',
                    },
                ],
            },
        ],
    },
];

const breadcrumb: Array<{ label: string; type: RouteNode['type'] }> = [
    { label: 'Workspace Proyectos', type: 'workspace' },
    { label: 'Portafolio Ministerial', type: 'portfolio' },
    { label: 'Campamento Juventud 2026', type: 'project' },
    { label: 'Reservar venue', type: 'task' },
];

export const Default: Story = {
    args: {
        breadcrumb,
        tree,
        activeId: 't1',
    },
};

const flatTree: RouteNode[] = [
    {
        id: 'workspace',
        label: 'Workspace Proyectos',
        type: 'workspace',
        children: [
            { id: 'proj-1', label: 'Campamento Juventud 2026', type: 'project' },
            { id: 'proj-2', label: 'Escuela de Liderazgo', type: 'project' },
        ],
    },
];

export const ArbolPlano: Story = {
    args: {
        breadcrumb: [{ label: 'Workspace Proyectos', type: 'workspace' }],
        tree: flatTree,
    },
};
