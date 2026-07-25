import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ProjectMasterView } from './ProjectMasterView';
import { SortableTaskCard } from './SortableTaskCard';
import type { ProjectRecord, ProjectTaskRecord } from '@/types/projects';

// Mock AuthContext to avoid real auth calls
vi.mock('@/context/AuthContext', () => ({
    useAuth: () => ({ token: 'mock-token', loading: false, user: null, isAuthenticated: true, login: vi.fn(), logout: vi.fn(), refreshUser: vi.fn() }),
}));

// Mock ProjectUpdateContext
vi.mock('@/context/ProjectUpdateContext', () => ({
    useProjectUpdate: () => ({ reloadProject: vi.fn(), updateProject: vi.fn(), updateTask: vi.fn() }),
}));

// Mock ToastContext
vi.mock('@/context/ToastContext', () => ({
    useToast: () => ({ addToast: vi.fn() }),
}));

// Mock inline editors to keep tests simple
vi.mock('@/components/ui/inline-editors/InlineTextInput', () => ({
    InlineTextInput: ({ value }: { value: string }) => <span data-testid="inline-text-input">{value}</span>,
}));

vi.mock('@/components/ui/inline-editors/InlineTextArea', () => ({
    InlineTextArea: ({ value }: { value: string }) => <span data-testid="inline-text-area">{value}</span>,
}));

vi.mock('@/components/ui/inline-editors/InlineProjectStatusPicker', () => ({
    InlineProjectStatusPicker: ({ value }: { value: string }) => <span data-testid="inline-status-picker">{value}</span>,
}));

vi.mock('@/components/ui/inline-editors/InlineDatePicker', () => ({
    InlineDatePicker: ({ value }: { value: string | null }) => <span data-testid="inline-date-picker">{value ?? 'no-date'}</span>,
}));

const mockProject: ProjectRecord = {
    id: '1',
    title: 'Proyecto Test',
    description: 'Descripción',
    status: 'planning',
    owner_id: null,
    color: '#2563eb',
    progress_percent: 0,
    milestones: [],
    created_at: '2024-01-01',
    updated_at: '2024-01-01',
};

const mockTask: ProjectTaskRecord = {
    id: 'task-1',
    title: 'Tarea de prueba',
    description: '',
    status: 'todo',
    priority: 'medium',
    due_date: null,
    assignee_id: null,
    project_id: '1',
    comments_count: 0,
    created_at: '2024-01-01',
    updated_at: '2024-01-01',
};

describe('Projects accessibility - interactive states', () => {
    it('ProjectMasterView uses correct heading hierarchy', () => {
        render(<ProjectMasterView project={mockProject} tasks={[]} />);

        // Page title should be h1
        const h1 = screen.getByRole('heading', { level: 1 });
        expect(h1).toBeInTheDocument();

        // Section heading for milestones should be h2, not h3
        const milestonesHeading = screen.getByRole('heading', { level: 2, name: /Hitos Estratégicos/i });
        expect(milestonesHeading).toBeInTheDocument();

        // Node card titles should render as h3 headings
        expect(screen.getByRole('heading', { level: 3, name: /Nodo de Nutrición/i })).toBeInTheDocument();
        expect(screen.getByRole('heading', { level: 3, name: /Nodo Digital/i })).toBeInTheDocument();
    });

    it('SortableTaskCard drag handle is a focusable button with aria-label', () => {
        render(<SortableTaskCard task={mockTask} onOpen={vi.fn()} />);

        const dragButton = screen.getByRole('button', { name: /Arrastrar tarea/i });
        expect(dragButton).toBeInTheDocument();
        expect(dragButton.tagName.toLowerCase()).toBe('button');
    });

    it('SortableTaskCard menu button has aria-label', () => {
        render(<SortableTaskCard task={mockTask} onOpen={vi.fn()} />);

        const menuButton = screen.getByRole('button', { name: /Opciones de tarea/i });
        expect(menuButton).toBeInTheDocument();
        expect(menuButton).toHaveAttribute('aria-label', 'Opciones de tarea');
    });
});
