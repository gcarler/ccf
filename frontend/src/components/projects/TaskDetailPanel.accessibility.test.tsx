import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import type { ProjectTaskRecord } from '@/types/projects';
import TaskDetailPanel from './TaskDetailPanel';

vi.mock('@/context/AuthContext', () => ({
    useAuth: () => ({ token: null, loading: false }),
}));

vi.mock('@/lib/http', () => ({ apiFetch: vi.fn() }));
vi.mock('@/components/ConfirmActionDrawer', () => ({ default: () => null }));
vi.mock('./TaskMetaFields', () => ({ default: () => null }));
vi.mock('./TaskAttachmentSection', () => ({ default: () => null }));
vi.mock('./TaskSupplySection', () => ({ default: () => null }));
vi.mock('./TaskActivitySection', () => ({
    default: () => null,
    toggleActivity: vi.fn(),
    addChild: vi.fn(),
    updateTitle: vi.fn(),
}));
vi.mock('./TaskCommentSection', () => ({ default: () => null }));
vi.mock('./TaskTimeTrackingSection', () => ({ default: () => null }));

const task: ProjectTaskRecord = {
    id: 'task-1',
    project_id: 'project-1',
    title: 'Preparar encuentro',
    status: 'todo',
    priority: 'medium',
};

describe('TaskDetailPanel keyboard accessibility', () => {
    it('focuses the panel on open, closes with Escape, and restores trigger focus', async () => {
        function Harness() {
            const [selectedTask, setSelectedTask] = useState<ProjectTaskRecord | null>(null);
            return (
                <>
                    <button type="button" onClick={() => setSelectedTask(task)}>Abrir tarea</button>
                    <TaskDetailPanel task={selectedTask} onClose={() => setSelectedTask(null)} />
                </>
            );
        }

        const user = userEvent.setup();
        render(<Harness />);
        const trigger = screen.getByRole('button', { name: 'Abrir tarea' });
        await user.click(trigger);

        const panel = await screen.findByRole('complementary', { name: 'Detalle de tarea' });
        await waitFor(() => expect(panel).toHaveFocus());
        await user.keyboard('{Escape}');

        await waitFor(() => expect(screen.queryByRole('complementary', { name: 'Detalle de tarea' })).not.toBeInTheDocument());
        expect(trigger).toHaveFocus();
    });
});
