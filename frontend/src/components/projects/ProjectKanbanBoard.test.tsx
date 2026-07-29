import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ProjectKanbanBoard } from './ProjectKanbanBoard';
import { createMockProject, createMockTask } from '@/test-utils/factories';
import type { PhaseDef } from '@/context/ProjectUpdateContext';

// Mock contexts
vi.mock('@/context/AuthContext', () => ({
    useAuth: () => ({ token: 'mock-token', loading: false, user: null, isAuthenticated: true, login: vi.fn(), logout: vi.fn(), refreshUser: vi.fn() }),
}));

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

    it('calls onOpenTask when a task card is clicked', async () => {
        const onOpenTask = vi.fn();
        render(<ProjectKanbanBoard project={mockProject} tasks={mockTasks} phases={mockPhases} onOpenTask={onOpenTask} onAddTask={vi.fn()} />);

        // Click on the task card wrapper to avoid InlineTextInput button
        const card = screen.getByTestId('task-card-task-1');
        await userEvent.click(card);
        expect(onOpenTask).toHaveBeenCalledWith(expect.objectContaining({ id: 'task-1' }));
    });
});
