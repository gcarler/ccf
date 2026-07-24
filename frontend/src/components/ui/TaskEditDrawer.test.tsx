import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import TaskEditDrawer from './TaskEditDrawer';
import type { TaskDetail } from './TaskEditDrawer';

vi.mock('framer-motion', () => ({
    motion: {
        div: ({ children, ...props }: any) => <div {...filterMotionProps(props)}>{children}</div>,
        aside: ({ children, ...props }: any) => <aside {...filterMotionProps(props)}>{children}</aside>,
        p: ({ children, ...props }: any) => <p {...filterMotionProps(props)}>{children}</p>,
    },
    AnimatePresence: ({ children }: any) => <>{children}</>,
}));

function filterMotionProps(props: Record<string, any>): Record<string, any> {
    const skip = new Set(['initial', 'animate', 'exit', 'transition', 'whileHover', 'whileTap', 'layout']);
    const out: Record<string, any> = {};
    for (const [k, v] of Object.entries(props)) {
        if (!skip.has(k)) out[k] = v;
    }
    return out;
}

vi.mock('@/lib/http', () => ({
    apiFetch: vi.fn().mockResolvedValue({}),
}));

vi.mock('@/context/AuthContext', () => ({
    useAuth: () => ({ token: 'test-token', user: { id: '1' } }),
}));

const mockTask: TaskDetail = {
    id: 'task-1',
    title: 'Test Task',
    status: 'todo',
    priority: 'medium',
    due_date: '2026-08-01',
    project_id: 'proj-1',
    project_title: 'My Project',
    description: 'Some description',
};

describe('TaskEditDrawer', () => {
    beforeEach(() => {
        vi.spyOn(HTMLTextAreaElement.prototype, 'scrollHeight', 'get').mockReturnValue(50);
    });

    it('renders nothing when task is null', () => {
        const { container } = render(
            <TaskEditDrawer
                task={null}
                onClose={vi.fn()}
                onTaskUpdated={vi.fn()}
                onTaskDeleted={vi.fn()}
            />
        );
        expect(container.innerHTML).toBe('');
    });

    it('renders the drawer with task title when task is provided', () => {
        render(
            <TaskEditDrawer
                task={mockTask}
                onClose={vi.fn()}
                onTaskUpdated={vi.fn()}
                onTaskDeleted={vi.fn()}
            />
        );
        expect(screen.getByDisplayValue('Test Task')).toBeInTheDocument();
    });

    it('renders task metadata in the footer', () => {
        render(
            <TaskEditDrawer
                task={mockTask}
                onClose={vi.fn()}
                onTaskUpdated={vi.fn()}
                onTaskDeleted={vi.fn()}
            />
        );
        expect(screen.getAllByText('Media').length).toBeGreaterThan(0);
        expect(screen.getAllByText('Pendiente').length).toBeGreaterThan(0);
    });
});
