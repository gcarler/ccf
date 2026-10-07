import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ProjectMasterView } from './ProjectMasterView';
import { SortableTaskCard } from './SortableTaskCard';
import type { ProjectRecord, ProjectTaskRecord } from '@/types/projects';

// Mock next/navigation (ProjectMasterView monta drawers que usan useRouter)
vi.mock('next/navigation', () => ({
    useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
    usePathname: () => '/plataforma/proyectos',
    useParams: () => ({}),
}));

// Mock AuthContext to avoid real auth calls
vi.mock('@/context/AuthContext', () => ({
    useAuth: () => ({ token: 'mock-token', loading: false, user: null, isAuthenticated: true, login: vi.fn(), logout: vi.fn(), refreshUser: vi.fn() }),
}));

// Mock SidebarLayerContext (RightPanel lo consume internamente)
vi.mock('@/context/SidebarLayerContext', () => ({
    useSidebarLayers: () => ({
        layers: { RIGHT: false, S2: false },
        openLayer: vi.fn(),
        closeLayer: vi.fn(),
        toggleLayer: vi.fn(),
        closeTopLayer: vi.fn(),
        rightMode: 'overlay',
        setRightMode: vi.fn(),
        sidebarStack: [],
        stackDirection: 'forward',
        pushSidebarPanel: vi.fn(),
        popSidebarPanel: vi.fn(),
        resetSidebarStack: vi.fn(),
    }),
}));

// Mock ProjectUpdateContext
vi.mock('@/context/ProjectUpdateContext', () => ({
    useProjectUpdate: () => ({ reloadProject: vi.fn(), updateProject: vi.fn(), updateTask: vi.fn() }),
}));

// Mock ToastContext
vi.mock('@/context/ToastContext', () => ({
    useToast: () => ({ addToast: vi.fn() }),
}));

// Mock apiFetch so ProjectMasterView analytics fetch is inert in tests
vi.mock('@/lib/http', () => ({
    apiFetch: vi.fn().mockResolvedValue(null),
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
    it('ProjectMasterView only emits text tokens declared by the CCF theme', () => {
        const { container } = render(<ProjectMasterView project={mockProject} tasks={[]} />);

        expect(container.innerHTML).not.toMatch(/--(?:foreground|muted-foreground|destructive-foreground)\b/);
        expect(container.innerHTML).toContain('--text-primary');
        expect(container.innerHTML).toContain('--text-secondary');
    });

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

    it('ProjectMasterView uses the semantic warning token for high risk severity', () => {
        render(
            <ProjectMasterView
                project={{
                    ...mockProject,
                    risks_summary: {
                        project_id: '1',
                        total_risks: 1,
                        active_risks: 1,
                        mitigated_risks: 0,
                        occurred_risks: 0,
                        critical_count: 0,
                        high_count: 1,
                        medium_count: 0,
                        low_count: 0,
                        matrix_5x5: [],
                        by_category: {},
                    },
                }}
                tasks={[]}
            />,
        );

        expect(screen.getByText('Altos (10-14)')).toHaveClass(
            'text-[hsl(var(--warning-text))]',
        );
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
