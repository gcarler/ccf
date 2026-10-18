import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { ProjectKanbanBoard } from './ProjectKanbanBoard';
import { createMockProject, createMockTask } from '@/test-utils/factories';
import type { PhaseDef } from '@/context/ProjectUpdateContext';

// Mock contexts
vi.mock('@/context/AuthContext', () => ({
    useAuth: () => ({ token: 'mock-token', loading: false, user: null, isAuthenticated: true, login: vi.fn(), logout: vi.fn(), refreshUser: vi.fn() }),
    useOptionalAuth: () => ({ token: 'mock-token', loading: false, user: null, isAuthenticated: true, login: vi.fn(), logout: vi.fn(), refreshUser: vi.fn() }),
}));

vi.mock('@/lib/http', () => ({ apiFetch: vi.fn().mockResolvedValue([]) }));

const updateTask = vi.fn();
const deleteTask = vi.fn();
const createTask = vi.fn();

vi.mock('@/context/ProjectUpdateContext', () => ({
    useProjectUpdate: () => ({ updateTask, deleteTask, createTask }),
}));

const mockProject = createMockProject({
    id: 'proj-1',
    title: 'Proyecto Kanban',
    description: '',
    status: 'planning',
    owner_id: null,
    color: '#2563eb',
    progress_percent: 0,
    milestones: [],
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
});

const mockPhases: PhaseDef[] = [
    { slug: 'todo', name: 'Por hacer', color: '#94a3b8', order_index: 0 },
    { slug: 'in_progress', name: 'En progreso', color: '#3b82f6', order_index: 1 },
    { slug: 'completed', name: 'Completado', color: '#22c55e', order_index: 2 },
];

const mockTasks = [
    createMockTask({ id: 'task-1', project_id: 'proj-1', title: 'Tarea Todo', status: 'todo', priority: 'medium' }),
    createMockTask({ id: 'task-2', project_id: 'proj-1', title: 'Tarea En Progreso', status: 'in_progress', priority: 'high' }),
];

describe('ProjectKanbanBoard', () => {
    it('renders all phase columns', () => {
        render(<ProjectKanbanBoard project={mockProject} tasks={mockTasks} phases={mockPhases} onOpenTask={vi.fn()} onAddTask={vi.fn()} />);

        mockPhases.forEach((phase) => {
            expect(screen.getByText(phase.name)).toBeInTheDocument();
        });
    });

    it('renders tasks in the correct columns', () => {
        render(<ProjectKanbanBoard project={mockProject} tasks={mockTasks} phases={mockPhases} onOpenTask={vi.fn()} onAddTask={vi.fn()} />);

        expect(screen.getByText('Tarea Todo')).toBeInTheDocument();
        expect(screen.getByText('Tarea En Progreso')).toBeInTheDocument();
    });

    it('shows empty state when no phases are provided', () => {
        render(<ProjectKanbanBoard project={mockProject} tasks={mockTasks} phases={[]} onOpenTask={vi.fn()} onAddTask={vi.fn()} />);

        expect(screen.getByText('No hay columnas para mostrar')).toBeInTheDocument();
    });

    it('has no critical accessibility violations with draggable task cards', async () => {
        const { container } = render(
            <ProjectKanbanBoard project={mockProject} tasks={mockTasks} phases={mockPhases} onOpenTask={vi.fn()} onAddTask={vi.fn()} />
        );

        expect((await axe(container)).violations).toEqual([]);
    });

    it('opens task details through an explicit accessible action', async () => {
        const onOpenTask = vi.fn();
        render(<ProjectKanbanBoard project={mockProject} tasks={mockTasks} phases={mockPhases} onOpenTask={onOpenTask} onAddTask={vi.fn()} />);

        await userEvent.click(screen.getByRole('button', { name: 'Abrir detalle de tarea Tarea Todo' }));
        expect(onOpenTask).toHaveBeenCalledWith(expect.objectContaining({ id: 'task-1' }));
    });

    it('does not open task details when editing or using inline metadata controls', async () => {
        const onOpenTask = vi.fn();
        render(<ProjectKanbanBoard project={mockProject} tasks={mockTasks} phases={mockPhases} onOpenTask={onOpenTask} onAddTask={vi.fn()} />);

        await userEvent.click(screen.getByText('Tarea Todo'));
        await userEvent.click(screen.getAllByRole('button', { name: 'Seleccionar fecha límite' })[0]);
        await userEvent.click(screen.getAllByRole('button', { name: 'Cambiar prioridad' })[0]);

        expect(onOpenTask).not.toHaveBeenCalled();
    });

    it('renders PMI flow and WIP summary metrics accurately', () => {
        const pmiTasks = [
            createMockTask({ id: 't1', project_id: 'proj-1', title: 'Pendiente normal', status: 'todo', priority: 'medium' }),
            createMockTask({ id: 't2', project_id: 'proj-1', title: 'En curso urgente', status: 'in_progress', priority: 'urgent' }),
            createMockTask({ id: 't3', project_id: 'proj-1', title: 'En curso vencida', status: 'in_progress', priority: 'low', due_date: '2020-01-01' }),
            createMockTask({ id: 't4', project_id: 'proj-1', title: 'Entregada', status: 'completed', priority: 'urgent' }),
        ];

        render(<ProjectKanbanBoard project={mockProject} tasks={pmiTasks} phases={mockPhases} onOpenTask={vi.fn()} onAddTask={vi.fn()} />);

        expect(screen.getByTestId('kanban-board-pmi-flow-bar')).toBeInTheDocument();
        expect(screen.getByTestId('kanban-board-pmi-wip')).toHaveTextContent('WIP Activo: 2');
        expect(screen.getByTestId('kanban-board-pmi-completion')).toHaveTextContent('Avance de Flujo: 25%');
        expect(screen.getByTestId('kanban-board-pmi-critical-count')).toHaveTextContent('Críticas / Vencidas: 2');
    });

    it('filters board tasks using PMI critical and unassigned RACI filters', async () => {
        const filterTasks = [
            createMockTask({
                id: 't-normal',
                project_id: 'proj-1',
                title: 'Tarea Normal Asignada',
                status: 'todo',
                priority: 'medium',
                assignee_id: 'user-1',
            }),
            createMockTask({
                id: 't-crit',
                project_id: 'proj-1',
                title: 'Tarea Crítica Asignada',
                status: 'in_progress',
                priority: 'urgent',
                assignee_id: 'user-1',
            }),
            createMockTask({
                id: 't-no-raci',
                project_id: 'proj-1',
                title: 'Tarea Sin Responsable',
                status: 'todo',
                priority: 'low',
                assignee_id: null,
            }),
        ];

        render(<ProjectKanbanBoard project={mockProject} tasks={filterTasks} phases={mockPhases} onOpenTask={vi.fn()} onAddTask={vi.fn()} />);

        expect(screen.getByText('Tarea Normal Asignada')).toBeInTheDocument();
        expect(screen.getByText('Tarea Crítica Asignada')).toBeInTheDocument();
        expect(screen.getByText('Tarea Sin Responsable')).toBeInTheDocument();

        await userEvent.click(screen.getByTestId('kanban-filter-critical'));
        expect(screen.queryByText('Tarea Normal Asignada')).not.toBeInTheDocument();
        expect(screen.getByText('Tarea Crítica Asignada')).toBeInTheDocument();
        expect(screen.queryByText('Tarea Sin Responsable')).not.toBeInTheDocument();

        await userEvent.click(screen.getByTestId('kanban-filter-unassigned'));
        expect(screen.queryByText('Tarea Normal Asignada')).not.toBeInTheDocument();
        expect(screen.queryByText('Tarea Crítica Asignada')).not.toBeInTheDocument();
        expect(screen.getByText('Tarea Sin Responsable')).toBeInTheDocument();

        await userEvent.click(screen.getByTestId('kanban-filter-all'));
        expect(screen.getByText('Tarea Normal Asignada')).toBeInTheDocument();
        expect(screen.getByText('Tarea Crítica Asignada')).toBeInTheDocument();
        expect(screen.getByText('Tarea Sin Responsable')).toBeInTheDocument();
    });
});

