import type { Meta, StoryObj } from '@storybook/react-webpack5';
import ProjectActivityFeed from './ProjectActivityFeed';
import type { ProjectActivityItem } from '@/types/projects';

/** Timeline de actividad del equipo en un proyecto. */
const meta: Meta<typeof ProjectActivityFeed> = {
    title: 'Projects/ProjectActivityFeed',
    component: ProjectActivityFeed,
    parameters: { layout: 'centered' },
};

export default meta;
type Story = StoryObj<typeof ProjectActivityFeed>;

const activities: ProjectActivityItem[] = [
    {
        id: 'a1',
        kind: 'task_created',
        project_id: 'p1',
        project_title: 'Campamento Juventud 2026',
        task_id: 't1',
        task_title: 'Reservar venue',
        description: 'Ana creó la tarea "Reservar venue" en Por Hacer.',
        created_at: '2026-10-02T14:32:00Z',
    },
    {
        id: 'a2',
        kind: 'status_changed',
        project_id: 'p1',
        project_title: 'Campamento Juventud 2026',
        task_id: 't2',
        task_title: 'Diseñar flyers',
        description: 'Carlos movió "Diseñar flyers" a En Progreso.',
        created_at: '2026-10-02T16:05:00Z',
    },
    {
        id: 'a3',
        kind: 'comment_added',
        project_id: 'p1',
        project_title: 'Campamento Juventud 2026',
        task_id: 't3',
        task_title: 'Coordinar transporte',
        description: 'María comentó: "El bus saldrá a las 6:00 am desde el templo".',
        created_at: '2026-10-03T09:12:00Z',
    },
    {
        id: 'a4',
        kind: 'milestone_completed',
        project_id: 'p1',
        project_title: 'Campamento Juventud 2026',
        description: 'Hito "Logística cerrada" alcanzado.',
        created_at: '2026-10-01T20:00:00Z',
    },
];

export const ConActividad: Story = {
    args: { activities },
};

export const Vacio: Story = {
    args: { activities: [] },
};

export const EnPanel: Story = {
    render: () => (
        <div className="h-[420px] w-80 border border-[hsl(var(--border))] rounded-lg overflow-hidden">
            <ProjectActivityFeed activities={activities} />
        </div>
    ),
};
