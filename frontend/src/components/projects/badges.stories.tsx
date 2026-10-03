import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { TaskStatusBadge, TaskPriorityBadge, ProjectStatusBadge, TaskNodeBadge } from './badges';

/**
 * Badges canónicos del módulo de Proyectos. Toda vista que renderice
 * estado/prioridad/nodo debe consumir estos componentes en lugar de
 * duplicar mapas de clases locales.
 */
const meta: Meta<typeof TaskStatusBadge> = {
    title: 'Projects/Badges',
    component: TaskStatusBadge,
    parameters: { layout: 'centered' },
};

export default meta;
type Story = StoryObj<typeof TaskStatusBadge>;

/** Estados canónicos de tarea en ambos temas. */
export const EstadosTarea: Story = {
    render: () => (
        <div className="flex flex-wrap items-center gap-3">
            <TaskStatusBadge value="todo" />
            <TaskStatusBadge value="in_progress" />
            <TaskStatusBadge value="review" />
            <TaskStatusBadge value="completed" />
            <TaskStatusBadge value="estado-desconocido" />
        </div>
    ),
};

/** Estado de tarea proveniente de una fase dinámica (color hex del proyecto). */
export const EstadoFaseDinamica: Story = {
    render: () => (
        <div className="flex flex-wrap items-center gap-3">
            <TaskStatusBadge value="revisio-pastoral" dotStyle={{ backgroundColor: '#f59e0b' }} />
            <TaskStatusBadge value="discipulado" dotStyle={{ backgroundColor: '#8b5cf6' }} />
        </div>
    ),
};

export const Prioridades: Story = {
    render: () => (
        <div className="flex flex-wrap items-center gap-3">
            <TaskPriorityBadge value="low" />
            <TaskPriorityBadge value="medium" />
            <TaskPriorityBadge value="high" />
            <TaskPriorityBadge value="urgent" />
        </div>
    ),
};

/** Ciclo de vida completo de un proyecto (5 estados canónicos). */
export const EstadosProyecto: Story = {
    render: () => (
        <div className="flex flex-wrap items-center gap-3">
            <ProjectStatusBadge value="planning" />
            <ProjectStatusBadge value="active" />
            <ProjectStatusBadge value="on_hold" />
            <ProjectStatusBadge value="completed" />
            <ProjectStatusBadge value="archived" />
        </div>
    ),
};

/** Label visual amigable en lugar del label canónico. */
export const EstadoProyectoConLabelCustom: Story = {
    render: () => (
        <div className="flex flex-wrap items-center gap-3">
            <ProjectStatusBadge value="active" label="En Marcha" />
            <ProjectStatusBadge value="completed" label="Alcanzado" />
        </div>
    ),
};

/** Nodos operativos del módulo (F2). */
export const NodosOperativos: Story = {
    render: () => (
        <div className="flex flex-wrap items-center gap-3">
            <TaskNodeBadge value="nutrition" />
            <TaskNodeBadge value="digital" />
            <TaskNodeBadge value={null} />
        </div>
    ),
};
